from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import List, Optional

from PySide6 import QtCore, QtGui, QtWidgets

from clipboard_service import ClipboardService
from explorerpro_adapter import export_to_explorerpro, load_explorerpro_items
from library_query import SORT_MODE_LABELS, query_items
from logging_setup import configure_logging, default_log_dir
from materializer import materialize_item
from models import ItemType, LibraryItem, gen_id, normalize_name, now_iso, parse_tags
from profiprompt_adapter import load_profiprompt_items
from settings_manager import SettingsManager
from storage import Storage
from theme import apply_theme

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ICON_PATH = PROJECT_ROOT / "PromptBoard.ico"
ICON_FALLBACK_PNG = PROJECT_ROOT / "PromptBoard.png"


def load_app_icon() -> QtGui.QIcon:
    """Return the PromptBoard icon if asset files are available, else fallback."""
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
        self._loading_ui = False

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
        self.tabs = QtWidgets.QTabWidget()
        self.tabs.addTab(self._build_library_tab(), "Bibliothek")
        self.tabs.addTab(self._build_settings_tab(), "Einstellungen")
        self.setCentralWidget(self.tabs)

        menu = self.menuBar()
        file_menu = menu.addMenu("Datei")
        file_menu.addAction("Neuer Eintrag", self.create_item)
        file_menu.addAction("Aus ProfiPrompt importieren", self.import_profiprompt_library)
        file_menu.addAction("Aus ExplorerPro importieren", self.import_explorerpro_library)
        file_menu.addAction("Nach ExplorerPro exportieren", self.export_to_explorerpro_library)
        file_menu.addSeparator()
        file_menu.addAction("Beenden", QtWidgets.QApplication.instance().quit)

    def _build_library_tab(self) -> QtWidgets.QWidget:
        root = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(root)

        left = QtWidgets.QVBoxLayout()
        filter_row = QtWidgets.QHBoxLayout()
        self.type_filter = QtWidgets.QComboBox()
        self.type_filter.addItem("ALLE")
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
        self.search_edit.setPlaceholderText("Suche nach Name, Inhalt oder Kategorie...")
        filter_row.addWidget(self.type_filter)
        filter_row.addWidget(self.sort_combo)
        filter_row.addWidget(self.search_edit)

        self.item_list = QtWidgets.QListWidget()
        self.item_list.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.item_list.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)

        button_row = QtWidgets.QHBoxLayout()
        self.new_button = QtWidgets.QPushButton("Neu")
        self.delete_button = QtWidgets.QPushButton("Löschen")
        self.copy_button = QtWidgets.QPushButton("Kopieren")
        self.materialize_button = QtWidgets.QPushButton("Materialisieren")
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
        self.source_edit.setPlaceholderText("z. B. lokal, ProfiPrompt, ExplorerPro")
        form.addRow("Typ", self.type_combo)
        form.addRow("Name", self.name_edit)
        form.addRow("Kategorie", self.category_edit)
        form.addRow("Tags", self.tags_edit)
        form.addRow("Quelle", self.source_edit)

        self.content_edit = QtWidgets.QPlainTextEdit()
        self.content_edit.setPlaceholderText("Inhalt des Eintrags...")

        self.status_label = QtWidgets.QLabel("Bereit")

        right.addLayout(form)
        right.addWidget(self.content_edit, 1)
        right.addWidget(self.status_label)

        layout.addLayout(left, 2)
        layout.addLayout(right, 3)
        return root

    def _build_settings_tab(self) -> QtWidgets.QWidget:
        root = QtWidgets.QWidget()
        outer = QtWidgets.QVBoxLayout(root)

        # Pfade
        path_group = QtWidgets.QGroupBox("Pfade")
        path_form = QtWidgets.QFormLayout(path_group)
        self.materialize_path_edit = QtWidgets.QLineEdit(str(self.settings.get_materialize_path()))
        self.materialize_path_edit.setReadOnly(True)
        materialize_row = QtWidgets.QHBoxLayout()
        materialize_row.addWidget(self.materialize_path_edit, 1)
        self.change_materialize_button = QtWidgets.QPushButton("Ändern...")
        materialize_row.addWidget(self.change_materialize_button)
        path_form.addRow("Materialisierung", self._wrap_layout(materialize_row))

        self.profiprompt_path_edit = QtWidgets.QLineEdit(str(self.settings.get_profiprompt_data_path()))
        self.profiprompt_path_edit.setReadOnly(True)
        profiprompt_row = QtWidgets.QHBoxLayout()
        profiprompt_row.addWidget(self.profiprompt_path_edit, 1)
        self.change_profiprompt_button = QtWidgets.QPushButton("Ändern...")
        profiprompt_row.addWidget(self.change_profiprompt_button)
        path_form.addRow("ProfiPrompt-Ordner", self._wrap_layout(profiprompt_row))

        self.explorerpro_path_edit = QtWidgets.QLineEdit(str(self.settings.get_explorerpro_data_path()))
        self.explorerpro_path_edit.setReadOnly(True)
        explorerpro_row = QtWidgets.QHBoxLayout()
        explorerpro_row.addWidget(self.explorerpro_path_edit, 1)
        self.change_explorerpro_button = QtWidgets.QPushButton("Ändern...")
        explorerpro_row.addWidget(self.change_explorerpro_button)
        path_form.addRow("ExplorerPro-Ordner", self._wrap_layout(explorerpro_row))

        outer.addWidget(path_group)

        # Import/Export
        io_group = QtWidgets.QGroupBox("Import / Export")
        io_layout = QtWidgets.QHBoxLayout(io_group)
        self.import_profiprompt_button = QtWidgets.QPushButton("Aus ProfiPrompt importieren")
        self.import_explorerpro_button = QtWidgets.QPushButton("Aus ExplorerPro importieren")
        self.export_explorerpro_button = QtWidgets.QPushButton("Nach ExplorerPro exportieren")
        io_layout.addWidget(self.import_profiprompt_button)
        io_layout.addWidget(self.import_explorerpro_button)
        io_layout.addWidget(self.export_explorerpro_button)
        outer.addWidget(io_group)

        # Ansicht
        view_group = QtWidgets.QGroupBox("Ansicht")
        view_form = QtWidgets.QFormLayout(view_group)
        self.theme_combo = QtWidgets.QComboBox()
        for mode in SettingsManager.THEME_CHOICES:
            self.theme_combo.addItem(mode.capitalize(), mode)
        current_theme = self.settings.get_theme()
        idx = self.theme_combo.findData(current_theme)
        if idx >= 0:
            self.theme_combo.setCurrentIndex(idx)
        view_form.addRow("Farbschema", self.theme_combo)

        self.confirm_overwrite_check = QtWidgets.QCheckBox(
            "Vor Überschreiben beim Materialisieren nachfragen"
        )
        self.confirm_overwrite_check.setChecked(self.settings.get_confirm_overwrite())
        view_form.addRow("Materialisierung", self.confirm_overwrite_check)

        outer.addWidget(view_group)

        # Info
        info_group = QtWidgets.QGroupBox("Info")
        info_layout = QtWidgets.QFormLayout(info_group)
        info_layout.addRow("Datenordner", QtWidgets.QLabel(str(self.settings.get_data_path())))
        info_layout.addRow("Logdatei", QtWidgets.QLabel(str(default_log_dir() / "promptboard.log")))
        outer.addWidget(info_group)

        outer.addStretch(1)
        return root

    @staticmethod
    def _wrap_layout(layout: QtWidgets.QLayout) -> QtWidgets.QWidget:
        wrapper = QtWidgets.QWidget()
        wrapper.setLayout(layout)
        return wrapper

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
        self.materialize_button.clicked.connect(self.materialize_current_item)

        # Editor auto-save
        self.type_combo.currentIndexChanged.connect(self.schedule_save)
        self.name_edit.textChanged.connect(self.schedule_save)
        self.category_edit.textChanged.connect(self.schedule_save)
        self.tags_edit.textChanged.connect(self.schedule_save)
        self.source_edit.textChanged.connect(self.schedule_save)
        self.content_edit.textChanged.connect(self.schedule_save)

        # Settings tab
        self.change_materialize_button.clicked.connect(self.change_materialize_path)
        self.change_profiprompt_button.clicked.connect(self.change_profiprompt_path)
        self.change_explorerpro_button.clicked.connect(self.change_explorerpro_path)
        self.import_profiprompt_button.clicked.connect(self.import_profiprompt_library)
        self.import_explorerpro_button.clicked.connect(self.import_explorerpro_library)
        self.export_explorerpro_button.clicked.connect(self.export_to_explorerpro_library)
        self.theme_combo.currentIndexChanged.connect(self.on_theme_changed)
        self.confirm_overwrite_check.toggled.connect(self.settings.set_confirm_overwrite)

    # ------------------------------------------------------------ helpers

    def all_items(self) -> List[LibraryItem]:
        try:
            return self.storage.load_items()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Fehler beim Laden der Bibliothek")
            self._show_error("Bibliothek konnte nicht geladen werden", exc)
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
        self.item_list.clear()
        for item in self.filtered_items():
            widget_item = QtWidgets.QListWidgetItem(f"{item.item_type.value} | {item.name}")
            widget_item.setData(QtCore.Qt.UserRole, item.id)
            self.item_list.addItem(widget_item)

        if selected_id:
            for row in range(self.item_list.count()):
                widget_item = self.item_list.item(row)
                if widget_item.data(QtCore.Qt.UserRole) == selected_id:
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
            self.status_label.setText(f"Bearbeite: {item.name}")
        finally:
            self._loading_ui = False

    def clear_editor(self) -> None:
        self._loading_ui = True
        try:
            self.type_combo.setCurrentText(ItemType.PROMPT.value)
            self.name_edit.clear()
            self.category_edit.clear()
            self.tags_edit.clear()
            self.source_edit.clear()
            self.content_edit.clear()
            self.status_label.setText("Bereit")
        finally:
            self._loading_ui = False

    def schedule_save(self) -> None:
        if self._loading_ui or self.current_item_id is None:
            return
        self.save_timer.start()

    def save_current_item(self) -> None:
        if self._loading_ui or self.current_item_id is None:
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
            self._show_error("Speichern fehlgeschlagen", exc)
            return
        self.status_label.setText(f"Automatisch gespeichert: {item.name}")
        self.current_item_id = item.id
        self.reload_list()

    def create_item(self) -> None:
        item = LibraryItem(
            id=gen_id(),
            item_type=ItemType.PROMPT,
            name=f"NEUER EINTRAG {len(self.all_items()) + 1}",
            content="",
            category="",
            tags=[],
            source="lokal",
        )
        try:
            self.storage.upsert_item(item)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Eintrag konnte nicht angelegt werden")
            self._show_error("Eintrag konnte nicht angelegt werden", exc)
            return
        self.current_item_id = item.id
        self.reload_list()
        self.status_label.setText("Neuer Eintrag erstellt")

    def on_sort_changed(self, *_args) -> None:
        self.settings.set_sort_mode(self.current_sort_mode())
        self.reload_list()

    def on_theme_changed(self, *_args) -> None:
        mode = self.theme_combo.currentData() or SettingsManager.DEFAULT_THEME
        self.settings.set_theme(mode)
        app = QtWidgets.QApplication.instance()
        if app is not None:
            apply_theme(app, mode)
            self.status_label.setText(f"Farbschema aktualisiert: {mode}")

    def current_item(self) -> Optional[LibraryItem]:
        if self.current_item_id is None:
            return None
        return self.storage.get_item(self.current_item_id)

    def delete_current_item(self) -> None:
        item = self.current_item()
        if item is None:
            return
        if not self._confirm_delete_item(item):
            self.status_label.setText(f"Löschen abgebrochen: {item.name}")
            return
        try:
            self.storage.delete_item(item.id)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Löschen fehlgeschlagen")
            self._show_error("Löschen fehlgeschlagen", exc)
            return
        self.current_item_id = None
        self.reload_list()
        self.clear_editor()
        self.status_label.setText(f"Gelöscht: {item.name}")

    def _confirm_delete_item(self, item: LibraryItem) -> bool:
        answer = QtWidgets.QMessageBox.question(
            self,
            "Eintrag löschen",
            f"Möchtest du den Eintrag '{item.name}' wirklich löschen?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )
        return answer == QtWidgets.QMessageBox.Yes

    def copy_current_item(self) -> None:
        self.save_current_item()
        item = self.current_item()
        if item is None:
            return
        self.clipboard_service.copy_item(item)
        self.status_label.setText(f"In Zwischenablage kopiert: {item.name}")

    def copy_double_clicked_item(self, widget_item: QtWidgets.QListWidgetItem) -> None:
        # Doppelklick = schneller Copy ohne Editor-Wechsel
        item_id = widget_item.data(QtCore.Qt.UserRole)
        item = self.storage.get_item(item_id) if item_id else None
        if item is None:
            return
        self.clipboard_service.copy_item(item)
        self.status_label.setText(f"In Zwischenablage kopiert: {item.name}")

    def materialize_current_item(self) -> None:
        self.save_current_item()
        item = self.current_item()
        if item is None:
            return
        self._materialize_item(item)

    def _materialize_item(self, item: LibraryItem) -> None:
        target_dir = self.settings.get_materialize_path()
        target_path = target_dir / f"{item.filename_stem()}.md"
        if self.settings.get_confirm_overwrite() and target_path.exists():
            answer = QtWidgets.QMessageBox.question(
                self,
                "Datei überschreiben?",
                f"'{target_path.name}' existiert bereits. Überschreiben?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No,
            )
            if answer != QtWidgets.QMessageBox.Yes:
                self.status_label.setText("Materialisierung abgebrochen")
                return
        try:
            target = materialize_item(item, target_dir)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Materialisierung fehlgeschlagen")
            self._show_error("Materialisierung fehlgeschlagen", exc)
            return
        self.status_label.setText(f"Materialisiert: {target}")

    # ------------------------------------------------------------ context menu

    def on_list_context_menu(self, pos: QtCore.QPoint) -> None:
        widget_item = self.item_list.itemAt(pos)
        if widget_item is None:
            return
        item_id = widget_item.data(QtCore.Qt.UserRole)
        item = self.storage.get_item(item_id) if item_id else None
        if item is None:
            return

        menu = QtWidgets.QMenu(self.item_list)
        copy_action = menu.addAction("Kopieren")
        materialize_action = menu.addAction("Materialisieren")
        menu.addSeparator()
        delete_action = menu.addAction("Löschen")
        chosen = menu.exec(self.item_list.mapToGlobal(pos))
        if chosen is None:
            return
        if chosen == copy_action:
            self.clipboard_service.copy_item(item)
            self.status_label.setText(f"In Zwischenablage kopiert: {item.name}")
        elif chosen == materialize_action:
            self._materialize_item(item)
        elif chosen == delete_action:
            self.current_item_id = item.id
            self.delete_current_item()

    # ------------------------------------------------------------ settings actions

    def change_materialize_path(self) -> None:
        current = str(self.settings.get_materialize_path())
        new_path = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Materialisierungspfad wählen", current
        )
        if new_path:
            self.settings.set_materialize_path(Path(new_path))
            self.materialize_path_edit.setText(new_path)
            self.status_label.setText(f"Neuer Materialisierungspfad: {new_path}")

    def change_profiprompt_path(self) -> None:
        current = str(self.settings.get_profiprompt_data_path())
        new_path = QtWidgets.QFileDialog.getExistingDirectory(
            self, "ProfiPrompt-Datenordner wählen", current
        )
        if new_path:
            self.settings.set_profiprompt_data_path(Path(new_path))
            self.profiprompt_path_edit.setText(new_path)
            self.status_label.setText(f"Neuer ProfiPrompt-Pfad: {new_path}")

    def change_explorerpro_path(self) -> None:
        current = str(self.settings.get_explorerpro_data_path())
        new_path = QtWidgets.QFileDialog.getExistingDirectory(
            self, "ExplorerPro-Datenordner wählen", current
        )
        if new_path:
            self.settings.set_explorerpro_data_path(Path(new_path))
            self.explorerpro_path_edit.setText(new_path)
            self.status_label.setText(f"Neuer ExplorerPro-Pfad: {new_path}")

    def import_profiprompt_library(self) -> None:
        try:
            imported_items = load_profiprompt_items(self.settings.get_profiprompt_data_path())
        except Exception as exc:  # noqa: BLE001
            logger.exception("ProfiPrompt-Import fehlgeschlagen")
            self._show_error("ProfiPrompt-Import fehlgeschlagen", exc)
            return
        if not imported_items:
            QtWidgets.QMessageBox.warning(
                self,
                "Import fehlgeschlagen",
                "Kein ProfiPrompt-`prompts.json` mit mindestens einem Prompt gefunden.",
            )
            return

        for item in imported_items:
            self.storage.upsert_item(item)

        latest_item = max(
            (item for item in imported_items if item.item_type == ItemType.PROMPT),
            key=lambda item: (item.updated_at, item.created_at, item.name),
            default=None,
        )
        if latest_item is None:
            latest_item = imported_items[0]

        self.current_item_id = latest_item.id
        self.reload_list()
        self.status_label.setText(
            f"Importiert aus ProfiPrompt: {len(imported_items)} Einträge"
        )

    def import_explorerpro_library(self) -> None:
        try:
            imported_items = load_explorerpro_items(self.settings.get_explorerpro_data_path())
        except Exception as exc:  # noqa: BLE001
            logger.exception("ExplorerPro-Import fehlgeschlagen")
            self._show_error("ExplorerPro-Import fehlgeschlagen", exc)
            return
        if not imported_items:
            QtWidgets.QMessageBox.warning(
                self,
                "Import fehlgeschlagen",
                "Kein ExplorerPro-`prompts.json` mit mindestens einem Prompt gefunden.",
            )
            return

        for item in imported_items:
            self.storage.upsert_item(item)

        self.current_item_id = imported_items[0].id
        self.reload_list()
        self.status_label.setText(
            f"Importiert aus ExplorerPro: {len(imported_items)} Einträge"
        )

    def export_to_explorerpro_library(self) -> None:
        self.save_current_item()
        items = self.all_items()
        prompt_items = [item for item in items if item.item_type == ItemType.PROMPT]
        if not prompt_items:
            QtWidgets.QMessageBox.information(
                self,
                "Export",
                "Es gibt keine PROMPT-Einträge zum Export nach ExplorerPro.",
            )
            return
        try:
            count = export_to_explorerpro(
                prompt_items, self.settings.get_explorerpro_data_path()
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("ExplorerPro-Export fehlgeschlagen")
            self._show_error("ExplorerPro-Export fehlgeschlagen", exc)
            return
        self.status_label.setText(f"Nach ExplorerPro exportiert: {count} Einträge")

    # ------------------------------------------------------------ misc

    def _show_error(self, title: str, exc: BaseException) -> None:
        QtWidgets.QMessageBox.warning(self, title, f"{title}:\n{exc}")

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self.save_current_item()
        if getattr(self, "tray_icon", None) and self.tray_icon.isVisible():
            self.hide()
            event.ignore()
            self.status_label.setText("Fenster in den Systemtray minimiert")
            return
        super().closeEvent(event)


def create_tray(window: MainWindow) -> QtWidgets.QSystemTrayIcon:
    app = QtWidgets.QApplication.instance()
    icon = load_app_icon()
    tray = QtWidgets.QSystemTrayIcon(icon, window)
    tray.setToolTip("PromptBoard")

    menu = QtWidgets.QMenu()
    menu.addAction("Öffnen", window.showNormal)
    menu.addAction("Verstecken", window.hide)
    menu.addSeparator()
    menu.addAction("Beenden", app.quit)
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
    apply_theme(app, settings.get_theme())
    storage = Storage(settings.get_data_path())
    window = MainWindow(storage, settings)
    create_tray(window)
    if not storage.load_items():
        window.create_item()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
