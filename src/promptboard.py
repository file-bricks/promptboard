from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import List, Optional

from PySide6 import QtCore, QtGui, QtWidgets

from clipboard_service import ClipboardService
from explorerpro_adapter import export_to_explorerpro, load_explorerpro_items
from hotkeys import PromptBoardHotkeys
from i18n import set_language as set_global_language
from i18n import tr
from item_templates import build_default_name, get_item_template
from library_query import SORT_MODE_LABELS, query_items
from logging_setup import configure_logging
from materializer import materialize_items
from models import ItemType, LibraryItem, gen_id, normalize_name, now_iso, parse_tags
from profiprompt_adapter import load_profiprompt_items
from settings_dialog import SettingsDialog
from settings_manager import SettingsManager
from storage import Storage
from theme import apply_theme

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ICON_PATH = PROJECT_ROOT / "PromptBoard.ico"
ICON_FALLBACK_PNG = PROJECT_ROOT / "PromptBoard.png"


def load_app_icon() -> QtGui.QIcon:
    if ICON_PATH.exists():
        return QtGui.QIcon(str(ICON_PATH))
    if ICON_FALLBACK_PNG.exists():
        return QtGui.QIcon(str(ICON_FALLBACK_PNG))
    app = QtWidgets.QApplication.instance()
    if app is not None:
        return app.style().standardIcon(QtWidgets.QStyle.SP_FileDialogContentsView)
    return QtGui.QIcon()


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, storage: Storage, settings: SettingsManager):
        super().__init__()
        self.storage = storage
        self.settings = settings
        self.clipboard_service = ClipboardService(QtWidgets.QApplication.instance())
        self.current_item_id: Optional[str] = None
        self.last_active_item_id: Optional[str] = self.settings.get_last_active_item_id() or None
        self._loading_ui = False
        self._dirty = False
        self.tray_icon: Optional[QtWidgets.QSystemTrayIcon] = None
        self.hotkeys: Optional[PromptBoardHotkeys] = None

        self.setWindowTitle("PromptBoard")
        self.setWindowIcon(load_app_icon())
        self.resize(1080, 680)

        self.save_timer = QtCore.QTimer(self)
        self.save_timer.setSingleShot(True)
        self.save_timer.setInterval(500)
        self.save_timer.timeout.connect(self.save_current_item)

        self._build_ui()
        self._connect_signals()
        self.reload_list()

    # ---------------------------------------------------------------- UI

    def _build_ui(self) -> None:
        self.setCentralWidget(self._build_library_widget())
        self._build_menubar()

    def _build_menubar(self) -> None:
        menubar = self.menuBar()
        menubar.clear()

        self.file_menu = menubar.addMenu(tr("menu.file"))
        self.action_new = self.file_menu.addAction(tr("menu.file.new"))
        self.action_new.triggered.connect(self.create_item)
        self.action_import_profiprompt = self.file_menu.addAction(tr("menu.file.import_profiprompt"))
        self.action_import_profiprompt.triggered.connect(self.import_profiprompt_library)
        self.action_import_explorerpro = self.file_menu.addAction(tr("menu.file.import_explorerpro"))
        self.action_import_explorerpro.triggered.connect(self.import_explorerpro_library)
        self.action_export_explorerpro = self.file_menu.addAction(tr("menu.file.export_explorerpro"))
        self.action_export_explorerpro.triggered.connect(self.export_to_explorerpro_library)
        self.file_menu.addSeparator()
        self.action_quit = self.file_menu.addAction(tr("menu.file.quit"))
        self.action_quit.triggered.connect(QtWidgets.QApplication.instance().quit)

        self.settings_menu = menubar.addMenu(tr("menu.settings"))
        self.action_open_settings = self.settings_menu.addAction(tr("menu.settings.open"))
        self.action_open_settings.triggered.connect(self.open_settings_dialog)

    def _build_library_widget(self) -> QtWidgets.QWidget:
        root = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(root)

        left = QtWidgets.QVBoxLayout()
        filter_row = QtWidgets.QHBoxLayout()
        self.type_filter = QtWidgets.QComboBox()
        self.type_filter.addItem(tr("filter.all"))
        for item_type in ItemType:
            self.type_filter.addItem(item_type.value)
        self.sort_combo = QtWidgets.QComboBox()
        for sort_mode, label in SORT_MODE_LABELS.items():
            self.sort_combo.addItem(label, sort_mode)
        current_sort_mode = self.settings.get_sort_mode()
        sort_index = self.sort_combo.findData(current_sort_mode)
        if sort_index >= 0:
            self.sort_combo.setCurrentIndex(sort_index)
        self.search_edit = QtWidgets.QLineEdit()
        self.search_edit.setPlaceholderText(tr("filter.search_placeholder"))
        filter_row.addWidget(self.type_filter)
        filter_row.addWidget(self.sort_combo)
        filter_row.addWidget(self.search_edit)

        self.item_list = QtWidgets.QListWidget()
        self.item_list.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.item_list.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)

        button_row = QtWidgets.QHBoxLayout()
        self.new_button = QtWidgets.QPushButton(tr("btn.new"))
        self.delete_button = QtWidgets.QPushButton(tr("btn.delete"))
        self.copy_button = QtWidgets.QToolButton()
        self.copy_button.setText(tr("btn.copy"))
        self.copy_button.setPopupMode(QtWidgets.QToolButton.MenuButtonPopup)
        self.copy_button_menu = QtWidgets.QMenu(self.copy_button)
        self.copy_markdown_action = self.copy_button_menu.addAction(tr("btn.copy_markdown"))
        self.copy_button.setMenu(self.copy_button_menu)
        self.materialize_button = QtWidgets.QToolButton()
        self.materialize_button.setText(tr("btn.materialize"))
        self.materialize_button.setPopupMode(QtWidgets.QToolButton.MenuButtonPopup)
        self.materialize_button_menu = QtWidgets.QMenu(self.materialize_button)
        self.materialize_current_action = self.materialize_button_menu.addAction(
            tr("btn.materialize_current")
        )
        self.materialize_selected_action = self.materialize_button_menu.addAction(
            tr("btn.materialize_selected")
        )
        self.materialize_button.setMenu(self.materialize_button_menu)
        button_row.addWidget(self.new_button)
        button_row.addWidget(self.delete_button)
        button_row.addWidget(self.copy_button)
        button_row.addWidget(self.materialize_button)

        left.addLayout(filter_row)
        left.addWidget(self.item_list)
        left.addLayout(button_row)

        right = QtWidgets.QVBoxLayout()
        form = QtWidgets.QFormLayout()
        self.type_combo = QtWidgets.QComboBox()
        for item_type in ItemType:
            self.type_combo.addItem(item_type.value)
        self.name_edit = QtWidgets.QLineEdit()
        self.category_edit = QtWidgets.QLineEdit()
        self.tags_edit = QtWidgets.QLineEdit()
        self.source_edit = QtWidgets.QLineEdit()
        self.source_edit.setPlaceholderText(tr("form.source_placeholder"))
        self.form_layout = form  # gespeichert für Re-Labeling bei Sprachwechsel
        form.addRow(tr("form.type"), self.type_combo)
        form.addRow(tr("form.name"), self.name_edit)
        form.addRow(tr("form.category"), self.category_edit)
        form.addRow(tr("form.tags"), self.tags_edit)
        form.addRow(tr("form.source"), self.source_edit)

        self.content_edit = QtWidgets.QPlainTextEdit()
        self.content_edit.setPlaceholderText(tr("form.content_placeholder"))

        self.status_label = QtWidgets.QLabel(tr("status.ready"))

        right.addLayout(form)
        right.addWidget(self.content_edit, 1)
        right.addWidget(self.status_label)

        layout.addLayout(left, 2)
        layout.addLayout(right, 3)
        return root

    def _connect_signals(self) -> None:
        self.item_list.currentItemChanged.connect(self.on_item_selected)
        self.item_list.customContextMenuRequested.connect(self.on_list_context_menu)
        self.item_list.itemDoubleClicked.connect(self.copy_double_clicked_item)
        self.type_filter.currentIndexChanged.connect(self.reload_list)
        self.sort_combo.currentIndexChanged.connect(self.on_sort_changed)
        self.search_edit.textChanged.connect(self.reload_list)
        self.new_button.clicked.connect(self.create_item)
        self.delete_button.clicked.connect(self.delete_current_item)
        self.copy_button.clicked.connect(self.copy_current_item)
        self.copy_markdown_action.triggered.connect(self.copy_current_item_markdown)
        self.materialize_button.clicked.connect(self.materialize_current_item)
        self.materialize_current_action.triggered.connect(self.materialize_current_item)
        self.materialize_selected_action.triggered.connect(self.materialize_selected_items)

        self.type_combo.currentIndexChanged.connect(self.schedule_save)
        self.name_edit.textChanged.connect(self.schedule_save)
        self.category_edit.textChanged.connect(self.schedule_save)
        self.tags_edit.textChanged.connect(self.schedule_save)
        self.source_edit.textChanged.connect(self.schedule_save)
        self.content_edit.textChanged.connect(self.schedule_save)

    # ------------------------------------------------------------ language

    def relabel_ui(self) -> None:
        """Apply the active language to all visible UI strings."""
        self._build_menubar()
        # Filter row
        self.type_filter.setItemText(0, tr("filter.all"))
        self.search_edit.setPlaceholderText(tr("filter.search_placeholder"))
        # Buttons
        self.new_button.setText(tr("btn.new"))
        self.delete_button.setText(tr("btn.delete"))
        self.copy_button.setText(tr("btn.copy"))
        self.copy_markdown_action.setText(tr("btn.copy_markdown"))
        self.materialize_button.setText(tr("btn.materialize"))
        self.materialize_current_action.setText(tr("btn.materialize_current"))
        self.materialize_selected_action.setText(tr("btn.materialize_selected"))
        # Form labels
        labels = [
            tr("form.type"),
            tr("form.name"),
            tr("form.category"),
            tr("form.tags"),
            tr("form.source"),
        ]
        for i, text in enumerate(labels):
            label_item = self.form_layout.itemAt(i, QtWidgets.QFormLayout.LabelRole)
            if label_item and isinstance(label_item.widget(), QtWidgets.QLabel):
                label_item.widget().setText(text)
        self.source_edit.setPlaceholderText(tr("form.source_placeholder"))
        self.content_edit.setPlaceholderText(tr("form.content_placeholder"))
        # Status (only re-translate if it's the default "Ready")
        # Active status messages remain as-is (already-formatted).

    # ------------------------------------------------------------ helpers

    def all_items(self) -> List[LibraryItem]:
        try:
            return self.storage.load_items()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Fehler beim Laden der Bibliothek")
            self._show_error(tr("error.library_load"), exc)
            return []

    def filtered_items(self) -> List[LibraryItem]:
        return query_items(
            self.all_items(),
            self.search_edit.text(),
            self.type_filter.currentText(),
            self.current_sort_mode(),
        )

    def current_sort_mode(self) -> str:
        sort_mode = self.sort_combo.currentData()
        if isinstance(sort_mode, str):
            return sort_mode
        return self.settings.get_sort_mode()

    def reload_list(self) -> None:
        selected_id = self.current_item_id
        # Re-entrancy guard: blockSignals so clear()/addItem() don't trigger
        # currentItemChanged → on_item_selected → save_current_item → reload_list.
        self.item_list.blockSignals(True)
        try:
            self.item_list.clear()
            for item in self.filtered_items():
                widget_item = QtWidgets.QListWidgetItem(self._item_display_text(item))
                widget_item.setData(QtCore.Qt.UserRole, item.id)
                self.item_list.addItem(widget_item)
        finally:
            self.item_list.blockSignals(False)

        if selected_id:
            row = self._find_list_row_by_id(selected_id)
            if row >= 0:
                self.item_list.setCurrentRow(row)
                return

        if self.item_list.count() and self.current_item_id is None:
            self.item_list.setCurrentRow(0)

    def on_item_selected(self, current: Optional[QtWidgets.QListWidgetItem], previous) -> None:
        if previous is not None:
            self.save_current_item()
        if current is None:
            self.current_item_id = None
            self.clear_editor()
            return

        self.current_item_id = current.data(QtCore.Qt.UserRole)
        item = self.storage.get_item(self.current_item_id)
        if item is not None:
            self._remember_active_item(item)
            self.load_item_into_editor(item)

    def load_item_into_editor(self, item: LibraryItem) -> None:
        self._loading_ui = True
        try:
            self.type_combo.setCurrentText(item.item_type.value)
            self.name_edit.setText(item.name)
            self.category_edit.setText(item.category)
            self.tags_edit.setText(", ".join(item.tags))
            self.source_edit.setText(item.source)
            self.content_edit.setPlainText(item.content)
            self.status_label.setText(tr("status.editing", name=item.name))
        finally:
            self._loading_ui = False
            self._dirty = False

    def clear_editor(self) -> None:
        self._loading_ui = True
        try:
            self.type_combo.setCurrentText(ItemType.PROMPT.value)
            self.name_edit.clear()
            self.category_edit.clear()
            self.tags_edit.clear()
            self.source_edit.clear()
            self.content_edit.clear()
            self.status_label.setText(tr("status.ready"))
        finally:
            self._loading_ui = False
            self._dirty = False

    def schedule_save(self) -> None:
        if self._loading_ui or self.current_item_id is None:
            return
        self._dirty = True
        self.save_timer.start()

    def save_current_item(self) -> None:
        if self._loading_ui or self.current_item_id is None:
            return
        if not self._dirty:
            return
        existing = self.storage.get_item(self.current_item_id)
        if existing is None:
            return

        raw_name = self.name_edit.text().strip()
        name = normalize_name(raw_name) if raw_name else existing.name
        item = LibraryItem(
            id=existing.id,
            item_type=ItemType.from_value(self.type_combo.currentText()),
            name=name,
            content=self.content_edit.toPlainText(),
            category=self.category_edit.text().strip(),
            tags=parse_tags(self.tags_edit.text()),
            source=self.source_edit.text().strip(),
            created_at=existing.created_at,
            updated_at=now_iso(),
        )
        try:
            self.storage.upsert_item(item)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Speichern fehlgeschlagen")
            self._show_error(tr("error.save_failed"), exc)
            return
        self._dirty = False
        self.status_label.setText(tr("status.autosaved", name=item.name))
        self.current_item_id = item.id
        self._remember_active_item(item)
        self._update_list_item_text(item)

    @staticmethod
    def _item_display_text(item: LibraryItem) -> str:
        return f"{item.item_type.value} | {item.name}"

    def _find_list_row_by_id(self, item_id: str) -> int:
        for row in range(self.item_list.count()):
            if self.item_list.item(row).data(QtCore.Qt.UserRole) == item_id:
                return row
        return -1

    def _update_list_item_text(self, item: LibraryItem) -> None:
        row = self._find_list_row_by_id(item.id)
        if row >= 0:
            self.item_list.item(row).setText(self._item_display_text(item))

    def _suggest_new_item_type(self) -> ItemType:
        filter_value = self.type_filter.currentText().strip()
        if filter_value and filter_value != tr("filter.all"):
            return ItemType.from_value(filter_value)
        current_value = self.type_combo.currentText().strip()
        if current_value:
            return ItemType.from_value(current_value)
        return ItemType.PROMPT

    def create_item(self) -> None:
        self.save_current_item()
        item_type = self._suggest_new_item_type()
        template = get_item_template(item_type)
        item = LibraryItem(
            id=gen_id(),
            item_type=item_type,
            name=build_default_name(item_type, self.item_list.count() + 1),
            content=template.content,
            category="",
            tags=[],
            source=template.source,
        )
        try:
            self.storage.upsert_item(item)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Eintrag konnte nicht angelegt werden")
            self._show_error(tr("error.create_failed"), exc)
            return
        self.current_item_id = item.id
        self.reload_list()
        self.status_label.setText(tr("status.created"))
        self._remember_active_item(item)

    def on_sort_changed(self, *_args) -> None:
        self.settings.set_sort_mode(self.current_sort_mode())
        self.reload_list()

    def open_settings_dialog(self) -> None:
        dialog = SettingsDialog(
            self.settings,
            parent=self,
            on_import_profiprompt=self.import_profiprompt_library,
            on_import_explorerpro=self.import_explorerpro_library,
            on_export_explorerpro=self.export_to_explorerpro_library,
        )
        dialog.theme_changed.connect(self._on_theme_changed)
        dialog.language_changed.connect(self._on_language_changed)
        dialog.exec()

    def _on_theme_changed(self, mode: str) -> None:
        app = QtWidgets.QApplication.instance()
        if app is not None:
            apply_theme(app, mode)
            self.status_label.setText(tr("status.theme_updated", mode=mode))

    def _on_language_changed(self, code: str) -> None:
        set_global_language(code)
        self.relabel_ui()
        self.status_label.setText(tr("status.language_updated", lang=tr(f"lang.{code}")))

    def current_item(self) -> Optional[LibraryItem]:
        if self.current_item_id is None:
            return None
        return self.storage.get_item(self.current_item_id)

    def delete_current_item(self) -> None:
        item = self.current_item()
        if item is None:
            return
        if not self._confirm_delete_item(item):
            self.status_label.setText(tr("status.delete_cancelled", name=item.name))
            return
        try:
            self.storage.delete_item(item.id)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Löschen fehlgeschlagen")
            self._show_error(tr("error.delete_failed"), exc)
            return
        self.current_item_id = None
        self.reload_list()
        if self.item_list.count() == 0:
            self.clear_editor()
        self.status_label.setText(tr("status.deleted", name=item.name))

    def _confirm_delete_item(self, item: LibraryItem) -> bool:
        answer = QtWidgets.QMessageBox.question(
            self,
            tr("dialog.delete.title"),
            tr("dialog.delete.body", name=item.name),
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )
        return answer == QtWidgets.QMessageBox.Yes

    def copy_current_item(self) -> None:
        self.save_current_item()
        item = self.current_item()
        if item is None:
            return
        self._copy_item(item)

    def copy_current_item_markdown(self) -> None:
        self.save_current_item()
        item = self.current_item()
        if item is None:
            return
        self._copy_item_markdown(item)

    def _copy_item(self, item: LibraryItem, notify_message: Optional[str] = None) -> bool:
        remember = getattr(self, "_remember_active_item", None)
        if callable(remember):
            remember(item)
        if self.clipboard_service.copy_item(item):
            self.status_label.setText(tr("status.copied", name=item.name))
            if notify_message:
                self._announce_status(notify_message)
            return True
        else:
            self.status_label.setText(tr("status.copy_cancelled"))
            return False

    def _copy_item_markdown(self, item: LibraryItem) -> bool:
        remember = getattr(self, "_remember_active_item", None)
        if callable(remember):
            remember(item)
        if self.clipboard_service.copy_item_markdown(item):
            self.status_label.setText(tr("status.copied_markdown", name=item.name))
            return True
        else:
            self.status_label.setText(tr("status.copy_markdown_cancelled"))
            return False

    def copy_double_clicked_item(self, widget_item: QtWidgets.QListWidgetItem) -> None:
        item_id = widget_item.data(QtCore.Qt.UserRole)
        item = self.storage.get_item(item_id) if item_id else None
        if item is None:
            return
        self._copy_item(item)

    def selected_items(self) -> list[LibraryItem]:
        selected_rows = {
            self.item_list.row(widget_item) for widget_item in self.item_list.selectedItems()
        }
        items: list[LibraryItem] = []
        for row in range(self.item_list.count()):
            if row not in selected_rows:
                continue
            widget_item = self.item_list.item(row)
            item_id = widget_item.data(QtCore.Qt.UserRole)
            item = self.storage.get_item(item_id) if item_id else None
            if item is not None:
                items.append(item)
        return items

    def materialize_current_item(self) -> None:
        self.save_current_item()
        selected = self.selected_items()
        if len(selected) > 1:
            self._materialize_items(selected)
            return
        item = self.current_item()
        if item is None:
            return
        self._materialize_item(item)

    def materialize_selected_items(self) -> None:
        self.save_current_item()
        selected = self.selected_items()
        if not selected:
            return
        self._materialize_items(selected)

    def _materialize_item(self, item: LibraryItem) -> None:
        self._materialize_items([item])

    def _materialize_items(self, items: list[LibraryItem]) -> None:
        if not items:
            return
        target_dir = self.settings.get_materialize_path()
        items_to_write: list[LibraryItem] = []
        for item in items:
            target_path = target_dir / f"{item.filename_stem()}.md"
            if self.settings.get_confirm_overwrite() and target_path.exists():
                answer = QtWidgets.QMessageBox.question(
                    self,
                    tr("dialog.overwrite.title"),
                    tr("dialog.overwrite.body", name=target_path.name),
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                    QtWidgets.QMessageBox.No,
                )
                if answer != QtWidgets.QMessageBox.Yes:
                    continue
            items_to_write.append(item)

        if not items_to_write:
            self.status_label.setText(tr("status.materialize_cancelled"))
            return

        try:
            targets = materialize_items(items_to_write, target_dir)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Materialisierung fehlgeschlagen")
            self._show_error(tr("error.materialize_failed"), exc)
            return
        if len(targets) == 1:
            self.status_label.setText(tr("status.materialized", target=targets[0]))
        else:
            self.status_label.setText(
                tr("status.materialized_batch", count=len(targets), target=target_dir)
            )

    # ------------------------------------------------------------ context menu

    def on_list_context_menu(self, pos: QtCore.QPoint) -> None:
        widget_item = self.item_list.itemAt(pos)
        item: Optional[LibraryItem] = None
        if widget_item is not None:
            item_id = widget_item.data(QtCore.Qt.UserRole)
            item = self.storage.get_item(item_id) if item_id else None

        menu = QtWidgets.QMenu(self.item_list)
        new_action = menu.addAction(tr("btn.new"))

        copy_action = None
        copy_markdown_action = None
        materialize_action = None
        materialize_selected_action = None
        delete_action = None

        if item is not None:
            menu.addSeparator()
            copy_action = menu.addAction(tr("btn.copy"))
            copy_markdown_action = menu.addAction(tr("btn.copy_markdown"))
            materialize_action = menu.addAction(tr("btn.materialize"))
            selected_items = self.selected_items()
            if widget_item.isSelected() and len(selected_items) > 1:
                materialize_selected_action = menu.addAction(tr("btn.materialize_selected"))
            menu.addSeparator()
            delete_action = menu.addAction(tr("btn.delete"))

        chosen = menu.exec(self.item_list.mapToGlobal(pos))
        if chosen is None:
            return
        if chosen == new_action:
            self.create_item()
        elif chosen == copy_action:
            self._copy_item(item)
        elif chosen == copy_markdown_action:
            self._copy_item_markdown(item)
        elif chosen == materialize_action:
            self._materialize_item(item)
        elif chosen == materialize_selected_action:
            self.materialize_selected_items()
        elif chosen == delete_action:
            self.current_item_id = item.id
            self.delete_current_item()

    # ------------------------------------------------------------ import/export

    def import_profiprompt_library(self) -> None:
        # Save any pending edits before swapping out the library state.
        self.save_current_item()
        try:
            imported_items = load_profiprompt_items(self.settings.get_profiprompt_data_path())
        except Exception as exc:  # noqa: BLE001
            logger.exception("ProfiPrompt-Import fehlgeschlagen")
            self._show_error(tr("error.profiprompt_failed"), exc)
            return
        if not imported_items:
            QtWidgets.QMessageBox.warning(
                self,
                tr("dialog.import_failed.title"),
                tr("dialog.import_failed.profiprompt"),
            )
            return

        try:
            self.storage.upsert_many(imported_items)
        except Exception as exc:  # noqa: BLE001
            logger.exception("ProfiPrompt-Import: Speichern fehlgeschlagen")
            self._show_error(tr("error.profiprompt_failed"), exc)
            return

        latest_item = max(
            (item for item in imported_items if item.item_type == ItemType.PROMPT),
            key=lambda item: (item.updated_at, item.created_at, item.name),
            default=None,
        )
        if latest_item is None:
            latest_item = imported_items[0]

        # Set current id AFTER the reload to avoid races with the
        # currentItemChanged signal during list rebuild.
        self.current_item_id = None
        self.reload_list()
        self._select_item_by_id(latest_item.id)
        self.status_label.setText(tr("status.imported_profiprompt", count=len(imported_items)))

    def import_explorerpro_library(self) -> None:
        self.save_current_item()
        try:
            imported_items = load_explorerpro_items(self.settings.get_explorerpro_data_path())
        except Exception as exc:  # noqa: BLE001
            logger.exception("ExplorerPro-Import fehlgeschlagen")
            self._show_error(tr("error.explorerpro_import_failed"), exc)
            return
        if not imported_items:
            QtWidgets.QMessageBox.warning(
                self,
                tr("dialog.import_failed.title"),
                tr("dialog.import_failed.explorerpro"),
            )
            return

        try:
            self.storage.upsert_many(imported_items)
        except Exception as exc:  # noqa: BLE001
            logger.exception("ExplorerPro-Import: Speichern fehlgeschlagen")
            self._show_error(tr("error.explorerpro_import_failed"), exc)
            return

        self.current_item_id = None
        self.reload_list()
        self._select_item_by_id(imported_items[0].id)
        self.status_label.setText(tr("status.imported_explorerpro", count=len(imported_items)))

    def _select_item_by_id(self, item_id: str) -> None:
        row = self._find_list_row_by_id(item_id)
        if row >= 0:
            self.item_list.setCurrentRow(row)

    def _remember_active_item(self, item: LibraryItem) -> None:
        self.last_active_item_id = item.id
        self.settings.set_last_active_item_id(item.id)

    def toggle_visibility_from_hotkey(self) -> None:
        if self.isVisible() and not self.isMinimized():
            self.hide()
            self._announce_status(tr("status.hotkeys_toggle_hidden"))
            return
        self.showNormal()
        self.raise_()
        self.activateWindow()
        self._announce_status(tr("status.hotkeys_toggle_shown"))

    def quick_copy_last_used_item(self) -> None:
        item = self.current_item()
        if item is None and self.last_active_item_id:
            item = self.storage.get_item(self.last_active_item_id)
        if item is None:
            items = self.all_items()
            item = items[0] if items else None
        if item is None:
            self._announce_status(tr("status.hotkeys_no_recent_item"))
            return
        self._copy_item(item, notify_message=tr("status.hotkeys_quick_copy", name=item.name))

    def _announce_status(self, text: str) -> None:
        self.status_label.setText(text)
        if self.tray_icon is not None:
            self.tray_icon.showMessage(
                "PromptBoard",
                text,
                QtWidgets.QSystemTrayIcon.Information,
                2500,
            )

    def export_to_explorerpro_library(self) -> None:
        self.save_current_item()
        items = self.all_items()
        prompt_items = [item for item in items if item.item_type == ItemType.PROMPT]
        if not prompt_items:
            QtWidgets.QMessageBox.information(
                self,
                tr("dialog.export_empty.title"),
                tr("dialog.export_empty.body"),
            )
            return
        try:
            count = export_to_explorerpro(prompt_items, self.settings.get_explorerpro_data_path())
        except Exception as exc:  # noqa: BLE001
            logger.exception("ExplorerPro-Export fehlgeschlagen")
            self._show_error(tr("error.explorerpro_export_failed"), exc)
            return
        self.status_label.setText(tr("status.exported_explorerpro", count=count))

    # ------------------------------------------------------------ misc

    def _show_error(self, title: str, exc: BaseException) -> None:
        QtWidgets.QMessageBox.warning(self, title, f"{title}:\n{exc}")

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self.save_current_item()
        if getattr(self, "tray_icon", None) and self.tray_icon.isVisible():
            self.hide()
            event.ignore()
            self.status_label.setText(tr("status.minimized_to_tray"))
            return
        super().closeEvent(event)


def create_tray(window: MainWindow) -> QtWidgets.QSystemTrayIcon:
    app = QtWidgets.QApplication.instance()
    icon = load_app_icon()
    tray = QtWidgets.QSystemTrayIcon(icon, window)
    tray.setToolTip("PromptBoard")

    menu = QtWidgets.QMenu()
    menu.addAction(tr("tray.open"), window.showNormal)
    menu.addAction(tr("tray.hide"), window.hide)
    menu.addSeparator()
    menu.addAction(tr("tray.quit"), app.quit)
    tray.setContextMenu(menu)
    tray.activated.connect(
        lambda reason: window.showNormal()
        if reason == QtWidgets.QSystemTrayIcon.Trigger
        else None
    )
    tray.show()
    window.tray_icon = tray
    return tray


def main() -> int:
    configure_logging()
    logger.info("PromptBoard startet")
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("PromptBoard")
    app.setWindowIcon(load_app_icon())
    settings = SettingsManager()
    set_global_language(settings.get_language())
    apply_theme(app, settings.get_theme())
    storage = Storage(settings.get_data_path())
    window = MainWindow(storage, settings)
    create_tray(window)
    hotkeys = PromptBoardHotkeys(
        on_toggle_visibility=window.toggle_visibility_from_hotkey,
        on_quick_copy=window.quick_copy_last_used_item,
    )
    hotkeys.start(app)
    window.hotkeys = hotkeys
    if hotkeys.supported and hotkeys.registered:
        window._announce_status(
            tr(
                "status.hotkeys_enabled",
                show=hotkeys.hotkeys[0].label(settings.get_language()),
                copy=hotkeys.hotkeys[1].label(settings.get_language()),
            )
        )
    else:
        window.status_label.setText(tr("status.hotkeys_unavailable"))
    app.aboutToQuit.connect(hotkeys.stop)
    if not storage.load_items():
        window.create_item()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
