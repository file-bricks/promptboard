"""Settings, first-coupling, and conflict-resolution dialogs for PromptBoard."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, List, Optional

from PySide6 import QtCore, QtGui, QtWidgets

from i18n import set_language as set_global_language
from i18n import tr
from logging_setup import default_log_dir
from settings_manager import SettingsManager
from storage import Storage
from sync_backend import (
    ConflictEntry,
    ConflictResolutionChoice,
    FirstCouplingChoice,
    SyncEngine,
    SyncOutcome,
    TargetChangeQueueChoice,
)


class _DialogWorkerSignals(QtCore.QObject):
    finished = QtCore.Signal(object)


class _DialogWorkerRunnable(QtCore.QRunnable):
    """Executes sync network calls on a QThreadPool worker thread."""

    def __init__(self, fn: Callable[[], Any]) -> None:
        super().__init__()
        self.setAutoDelete(True)
        self.signals = _DialogWorkerSignals()
        self._fn = fn

    def run(self) -> None:
        try:
            res = self._fn()
        except BaseException as exc:  # noqa: BLE001
            res = exc
        try:
            self.signals.finished.emit(res)
        except RuntimeError:
            pass


class ConfirmReplaceLibraryDialog(QtWidgets.QDialog):
    """Explicit second confirmation before replacing the local library with server state."""

    def __init__(
        self,
        remote_count: int,
        removed_local_count: int,
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.remote_count = max(0, int(remote_count))
        self.removed_local_count = max(0, int(removed_local_count))
        self.setWindowTitle(tr("dialog.sync_couple.confirm_title"))
        self.setModal(True)
        self.resize(460, 190)

        layout = QtWidgets.QVBoxLayout(self)
        self.body_label = QtWidgets.QLabel(
            tr(
                "dialog.sync_couple.confirm_body",
                count=self.remote_count,
                removed=self.removed_local_count,
            )
        )
        self.body_label.setWordWrap(True)
        layout.addWidget(self.body_label)
        layout.addStretch(1)

        btn_row = QtWidgets.QHBoxLayout()
        self.confirm_button = QtWidgets.QPushButton(tr("dialog.sync_couple.confirm_accept"))
        self.cancel_button = QtWidgets.QPushButton(tr("btn.cancel"))

        self.cancel_button.setDefault(True)
        self.cancel_button.setAutoDefault(True)
        self.confirm_button.setAutoDefault(False)

        btn_row.addStretch(1)
        btn_row.addWidget(self.confirm_button)
        btn_row.addWidget(self.cancel_button)
        layout.addLayout(btn_row)

        self.confirm_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)


class FirstCouplingDialog(QtWidgets.QDialog):
    """One-time confirmation shown when coupling to a non-empty sync server."""

    def __init__(
        self,
        remote_count: int,
        remote_rev: int,
        parent: Optional[QtWidgets.QWidget] = None,
        *,
        removed_local_count: int = 0,
        confirm_take_server: Optional[Callable[[int], bool]] = None,
    ) -> None:
        super().__init__(parent)
        self._choice: FirstCouplingChoice = "cancel"
        self.remote_count = max(0, int(remote_count))
        self.remote_rev = max(0, int(remote_rev))
        self.removed_local_count = max(0, int(removed_local_count))
        self._confirm_take_server = confirm_take_server
        self.setWindowTitle(tr("dialog.sync_couple.title"))
        self.setModal(True)
        self.resize(500, 220)

        layout = QtWidgets.QVBoxLayout(self)
        body_text = (
            f"{tr('dialog.sync_couple.body', count=self.remote_count, rev=self.remote_rev)}\n\n"
            f"{tr('dialog.sync_couple.removed_info', removed=self.removed_local_count)}"
        )
        self.body_label = QtWidgets.QLabel(body_text)
        self.body_label.setWordWrap(True)
        layout.addWidget(self.body_label)
        layout.addStretch(1)

        btn_row = QtWidgets.QHBoxLayout()
        self.merge_button = QtWidgets.QPushButton(tr("dialog.sync_couple.merge"))
        self.take_server_button = QtWidgets.QPushButton(tr("dialog.sync_couple.take_server"))
        self.cancel_button = QtWidgets.QPushButton(tr("btn.cancel"))

        self.merge_button.setDefault(True)
        self.merge_button.setAutoDefault(True)
        self.take_server_button.setAutoDefault(False)
        self.cancel_button.setAutoDefault(False)

        btn_row.addWidget(self.merge_button)
        btn_row.addWidget(self.take_server_button)
        btn_row.addStretch(1)
        btn_row.addWidget(self.cancel_button)
        layout.addLayout(btn_row)

        self.merge_button.clicked.connect(self._choose_merge)
        self.take_server_button.clicked.connect(self._choose_take_server)
        self.cancel_button.clicked.connect(self.reject)

    @property
    def choice(self) -> FirstCouplingChoice:
        return self._choice

    def _choose_merge(self) -> None:
        self._choice = "merge"
        self.accept()

    def _ask_second_confirmation(self) -> bool:
        if self._confirm_take_server is not None:
            return bool(self._confirm_take_server(self.removed_local_count))
        confirm_dlg = ConfirmReplaceLibraryDialog(
            remote_count=self.remote_count,
            removed_local_count=self.removed_local_count,
            parent=self,
        )
        return confirm_dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted

    def _choose_take_server(self) -> None:
        if not self._ask_second_confirmation():
            self._choice = "cancel"
            self.reject()
            return
        self._choice = "take_server"
        self.accept()


class TargetQueueChangeDialog(QtWidgets.QDialog):
    """Asks whether to keep (default) or discard the previous coupling target's offline queue."""

    def __init__(
        self,
        old_target: str,
        new_target: str,
        pending_count: int,
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._choice: TargetChangeQueueChoice = "keep"
        self.old_target = old_target
        self.new_target = new_target
        self.pending_count = max(0, int(pending_count))
        self.setWindowTitle(tr("dialog.sync_target_queue.title"))
        self.setModal(True)
        self.resize(500, 200)

        layout = QtWidgets.QVBoxLayout(self)
        self.body_label = QtWidgets.QLabel(
            tr(
                "dialog.sync_target_queue.body",
                old_target=old_target,
                new_target=new_target,
                count=self.pending_count,
            )
        )
        self.body_label.setWordWrap(True)
        layout.addWidget(self.body_label)
        layout.addStretch(1)

        btn_row = QtWidgets.QHBoxLayout()
        self.keep_button = QtWidgets.QPushButton(tr("dialog.sync_target_queue.keep"))
        self.discard_button = QtWidgets.QPushButton(tr("dialog.sync_target_queue.discard"))

        self.keep_button.setDefault(True)
        self.keep_button.setAutoDefault(True)
        self.discard_button.setAutoDefault(False)

        btn_row.addWidget(self.keep_button)
        btn_row.addStretch(1)
        btn_row.addWidget(self.discard_button)
        layout.addLayout(btn_row)

        self.keep_button.clicked.connect(self._choose_keep)
        self.discard_button.clicked.connect(self._choose_discard)

    @property
    def choice(self) -> TargetChangeQueueChoice:
        return self._choice

    def _choose_keep(self) -> None:
        self._choice = "keep"
        self.accept()

    def _choose_discard(self) -> None:
        self._choice = "discard"
        self.accept()


class ConflictResolutionDialog(QtWidgets.QDialog):
    """Three-way conflict resolution dialog (keep local default / keep as copy / take server)."""

    def __init__(
        self,
        sync_engine: SyncEngine,
        parent: Optional[QtWidgets.QWidget] = None,
        on_resolved: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__(parent)
        self.sync_engine = sync_engine
        self._on_resolved = on_resolved

        self.setWindowTitle(tr("dialog.sync_conflicts.title"))
        self.setModal(True)
        self.resize(680, 440)

        self._build_ui()
        self.reload_conflicts()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)

        self.intro_label = QtWidgets.QLabel(tr("dialog.sync_conflicts.intro"))
        self.intro_label.setWordWrap(True)
        layout.addWidget(self.intro_label)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)

        self.conflict_list = QtWidgets.QListWidget()
        self.conflict_list.setAccessibleName(tr("dialog.sync_conflicts.list_name"))
        splitter.addWidget(self.conflict_list)

        detail_widget = QtWidgets.QWidget()
        detail_layout = QtWidgets.QVBoxLayout(detail_widget)
        detail_layout.setContentsMargins(0, 0, 0, 0)

        self.local_header = QtWidgets.QLabel(tr("dialog.sync_conflicts.local_label"))
        self.local_preview = QtWidgets.QPlainTextEdit()
        self.local_preview.setReadOnly(True)
        self.local_preview.setAccessibleName(tr("dialog.sync_conflicts.local_label"))

        self.server_header = QtWidgets.QLabel(tr("dialog.sync_conflicts.server_label", rev=0))
        self.server_preview = QtWidgets.QPlainTextEdit()
        self.server_preview.setReadOnly(True)
        self.server_preview.setAccessibleName(tr("dialog.sync_conflicts.server_label", rev=0))

        detail_layout.addWidget(self.local_header)
        detail_layout.addWidget(self.local_preview, 1)
        detail_layout.addWidget(self.server_header)
        detail_layout.addWidget(self.server_preview, 1)
        splitter.addWidget(detail_widget)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        layout.addWidget(splitter, 1)

        actions_row = QtWidgets.QHBoxLayout()
        self.keep_local_button = QtWidgets.QPushButton(tr("dialog.sync_conflicts.keep_local"))
        self.keep_copy_button = QtWidgets.QPushButton(tr("dialog.sync_conflicts.keep_copy"))
        self.take_server_button = QtWidgets.QPushButton(tr("dialog.sync_conflicts.take_server"))
        self.close_button = QtWidgets.QPushButton(tr("btn.ok"))

        self.keep_local_button.setDefault(True)
        self.keep_local_button.setAutoDefault(True)

        actions_row.addWidget(self.keep_local_button)
        actions_row.addWidget(self.keep_copy_button)
        actions_row.addWidget(self.take_server_button)
        actions_row.addStretch(1)
        actions_row.addWidget(self.close_button)
        layout.addLayout(actions_row)

        self.conflict_list.currentRowChanged.connect(self._on_selection_changed)
        self.keep_local_button.clicked.connect(lambda: self.apply_resolution("keep_local"))
        self.keep_copy_button.clicked.connect(lambda: self.apply_resolution("keep_copy"))
        self.take_server_button.clicked.connect(lambda: self.apply_resolution("take_server"))
        self.close_button.clicked.connect(self.accept)

    @staticmethod
    def _format_preview(payload: Optional[dict], deleted: bool) -> str:
        if deleted or payload is None:
            return tr("dialog.sync_conflicts.deleted_marker")
        name = str(payload.get("name") or payload.get("title") or "")
        content = str(payload.get("content") or payload.get("text") or "")
        return f"{name}\n\n{content}".strip()

    def reload_conflicts(self) -> None:
        self._conflicts: List[ConflictEntry] = self.sync_engine.get_conflicts()
        self.conflict_list.clear()
        for entry in self._conflicts:
            stamp = f" ({entry.updated_at})" if entry.updated_at else ""
            item = QtWidgets.QListWidgetItem(
                f"{entry.title} [{entry.source} rev {entry.server_rev}]{stamp}"
            )
            item.setData(QtCore.Qt.ItemDataRole.UserRole, (entry.kind, entry.id))
            self.conflict_list.addItem(item)

        has_items = bool(self._conflicts)
        self.keep_local_button.setEnabled(has_items)
        self.keep_copy_button.setEnabled(has_items)
        self.take_server_button.setEnabled(has_items)

        if has_items:
            self.conflict_list.setCurrentRow(0)
        else:
            self.local_preview.clear()
            self.server_preview.clear()

    def _on_selection_changed(self, row: int) -> None:
        if row < 0 or row >= len(self._conflicts):
            self.local_preview.clear()
            self.server_preview.clear()
            return
        entry = self._conflicts[row]
        self.server_header.setText(tr("dialog.sync_conflicts.server_label", rev=entry.server_rev))
        self.local_preview.setPlainText(
            self._format_preview(entry.local_item, entry.local_op == "delete")
        )
        self.server_preview.setPlainText(
            self._format_preview(entry.server_item, entry.server_deleted)
        )

    def current_conflict(self) -> Optional[ConflictEntry]:
        row = self.conflict_list.currentRow()
        if 0 <= row < len(self._conflicts):
            return self._conflicts[row]
        return None

    def apply_resolution(self, choice: ConflictResolutionChoice) -> bool:
        entry = self.current_conflict()
        if entry is None:
            return False
        self.sync_engine.resolve_conflict(
            entry.id,
            choice,
            kind=entry.kind,
            copy_suffix=tr("sync.copy_suffix"),
        )
        if self._on_resolved is not None:
            self._on_resolved()
        self.reload_conflicts()
        if not self._conflicts:
            self.accept()
        return True


class SettingsDialog(QtWidgets.QDialog):
    """Modal preferences dialog.

    Emits ``language_changed`` and ``theme_changed`` so the host
    window can react (relabel UI, apply new palette).
    """

    language_changed = QtCore.Signal(str)
    theme_changed = QtCore.Signal(str)

    def __init__(
        self,
        settings: SettingsManager,
        parent: Optional[QtWidgets.QWidget] = None,
        on_import_profiprompt: Optional[Callable[[], None]] = None,
        on_import_explorerpro: Optional[Callable[[], None]] = None,
        on_export_explorerpro: Optional[Callable[[], None]] = None,
        sync_engine: Optional[SyncEngine] = None,
        on_sync_now: Optional[Callable[[], Optional[SyncOutcome]]] = None,
        on_resolve_conflicts: Optional[Callable[[], None]] = None,
        on_sync_settings_changed: Optional[Callable[[], None]] = None,
        on_target_queue_change: Optional[
            Callable[[str, str, int], TargetChangeQueueChoice]
        ] = None,
    ) -> None:
        super().__init__(parent)
        self.settings = settings
        self._on_import_profiprompt = on_import_profiprompt
        self._on_import_explorerpro = on_import_explorerpro
        self._on_export_explorerpro = on_export_explorerpro
        self._sync_engine = sync_engine
        self._on_sync_now = on_sync_now
        self._on_resolve_conflicts = on_resolve_conflicts
        self._on_sync_settings_changed = on_sync_settings_changed
        self._on_target_queue_change = on_target_queue_change
        self._token_loaded = False
        self._token_dirty = False
        self._loading_token_ui = False
        self._worker_pool = QtCore.QThreadPool()
        self._worker_pool.setMaxThreadCount(1)
        self._active_runnables: set[_DialogWorkerRunnable] = set()

        self.setWindowTitle(tr("settings.title"))
        self.resize(640, 580)
        self.setModal(True)

        self._build_ui()
        self._connect_signals()
        self._refresh_sync_visibility_and_status()

    def _get_or_create_sync_engine(self) -> SyncEngine:
        if self._sync_engine is None:
            self._sync_engine = SyncEngine(Storage(self.settings.get_data_path()), self.settings)
        return self._sync_engine

    # ------------------------------------------------------------ UI

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)

        # Paths
        self.paths_group = QtWidgets.QGroupBox(tr("settings.group.paths"))
        self.paths_form = QtWidgets.QFormLayout(self.paths_group)

        self.materialize_path_edit = QtWidgets.QLineEdit(str(self.settings.get_materialize_path()))
        self.materialize_path_edit.setReadOnly(True)
        self.change_materialize_button = QtWidgets.QPushButton(tr("btn.change"))
        self.paths_form.addRow(
            tr("settings.path.materialize"),
            self._row(self.materialize_path_edit, self.change_materialize_button),
        )

        self.profiprompt_path_edit = QtWidgets.QLineEdit(str(self.settings.get_profiprompt_data_path()))
        self.profiprompt_path_edit.setReadOnly(True)
        self.change_profiprompt_button = QtWidgets.QPushButton(tr("btn.change"))
        self.paths_form.addRow(
            tr("settings.path.profiprompt"),
            self._row(self.profiprompt_path_edit, self.change_profiprompt_button),
        )

        self.explorerpro_path_edit = QtWidgets.QLineEdit(str(self.settings.get_explorerpro_data_path()))
        self.explorerpro_path_edit.setReadOnly(True)
        self.change_explorerpro_button = QtWidgets.QPushButton(tr("btn.change"))
        self.paths_form.addRow(
            tr("settings.path.explorerpro"),
            self._row(self.explorerpro_path_edit, self.change_explorerpro_button),
        )

        layout.addWidget(self.paths_group)

        # Import/Export
        self.io_group = QtWidgets.QGroupBox(tr("settings.group.io"))
        io_layout = QtWidgets.QVBoxLayout(self.io_group)

        toggles_row = QtWidgets.QHBoxLayout()
        self.profiprompt_enabled_check = QtWidgets.QCheckBox(
            tr("settings.imports.profiprompt_enabled")
        )
        self.profiprompt_enabled_check.setChecked(self.settings.is_profiprompt_enabled())
        self.explorerpro_enabled_check = QtWidgets.QCheckBox(
            tr("settings.imports.explorerpro_enabled")
        )
        self.explorerpro_enabled_check.setChecked(self.settings.is_explorerpro_enabled())
        toggles_row.addWidget(self.profiprompt_enabled_check)
        toggles_row.addWidget(self.explorerpro_enabled_check)
        io_layout.addLayout(toggles_row)

        buttons_row = QtWidgets.QHBoxLayout()
        self.import_profiprompt_button = QtWidgets.QPushButton(tr("settings.io.import_profiprompt"))
        self.import_explorerpro_button = QtWidgets.QPushButton(tr("settings.io.import_explorerpro"))
        self.export_explorerpro_button = QtWidgets.QPushButton(tr("settings.io.export_explorerpro"))
        buttons_row.addWidget(self.import_profiprompt_button)
        buttons_row.addWidget(self.import_explorerpro_button)
        buttons_row.addWidget(self.export_explorerpro_button)
        io_layout.addLayout(buttons_row)
        layout.addWidget(self.io_group)

        # Appearance
        self.view_group = QtWidgets.QGroupBox(tr("settings.group.view"))
        self.view_form = QtWidgets.QFormLayout(self.view_group)

        self.theme_combo = QtWidgets.QComboBox()
        for mode in SettingsManager.THEME_CHOICES:
            self.theme_combo.addItem(tr(f"theme.{mode}"), mode)
        current_theme = self.settings.get_theme()
        idx = self.theme_combo.findData(current_theme)
        if idx >= 0:
            self.theme_combo.setCurrentIndex(idx)
        self.view_form.addRow(tr("settings.view.theme"), self.theme_combo)

        self.language_combo = QtWidgets.QComboBox()
        for code in SettingsManager.LANGUAGE_CHOICES:
            self.language_combo.addItem(tr(f"lang.{code}"), code)
        current_lang = self.settings.get_language()
        idx = self.language_combo.findData(current_lang)
        if idx >= 0:
            self.language_combo.setCurrentIndex(idx)
        self.view_form.addRow(tr("settings.view.language"), self.language_combo)

        self.materialize_format_combo = QtWidgets.QComboBox()
        for fmt in SettingsManager.MATERIALIZE_FORMAT_CHOICES:
            self.materialize_format_combo.addItem(tr(f"materialize.format.{fmt}"), fmt)
        current_fmt = self.settings.get_materialize_format()
        fmt_idx = self.materialize_format_combo.findData(current_fmt)
        if fmt_idx >= 0:
            self.materialize_format_combo.setCurrentIndex(fmt_idx)
        self.view_form.addRow(
            tr("settings.view.materialize_format"), self.materialize_format_combo
        )

        self.confirm_overwrite_check = QtWidgets.QCheckBox(tr("settings.view.confirm_overwrite"))
        self.confirm_overwrite_check.setChecked(self.settings.get_confirm_overwrite())
        self.view_form.addRow("", self.confirm_overwrite_check)

        layout.addWidget(self.view_group)

        # Synchronization (Stage 1b)
        self.sync_group = QtWidgets.QGroupBox(tr("settings.group.sync"))
        sync_outer = QtWidgets.QVBoxLayout(self.sync_group)
        self.sync_top_form = QtWidgets.QFormLayout()

        self.sync_mode_combo = QtWidgets.QComboBox()
        for sync_mode in SettingsManager.UI_SYNC_MODE_CHOICES:
            self.sync_mode_combo.addItem(tr(f"sync.mode.{sync_mode}"), sync_mode)
        active_sync_mode = self.settings.get_sync_mode()
        sync_idx = self.sync_mode_combo.findData(active_sync_mode)
        if sync_idx >= 0:
            self.sync_mode_combo.setCurrentIndex(sync_idx)
        self.sync_top_form.addRow(tr("settings.sync.mode"), self.sync_mode_combo)

        self.sync_status_label = QtWidgets.QLabel(tr("sync.status.off"))
        self.sync_status_label.setWordWrap(True)
        self.sync_top_form.addRow(tr("settings.sync.status_label"), self.sync_status_label)
        sync_outer.addLayout(self.sync_top_form)

        self.sync_server_container = QtWidgets.QWidget()
        server_layout = QtWidgets.QVBoxLayout(self.sync_server_container)
        server_layout.setContentsMargins(0, 0, 0, 0)
        self.sync_server_form = QtWidgets.QFormLayout()

        self.sync_url_edit = QtWidgets.QLineEdit(self.settings.get_sync_server_url())
        self.sync_url_edit.setPlaceholderText("http://127.0.0.1:8765")
        self.sync_server_form.addRow(tr("settings.sync.server_url"), self.sync_url_edit)

        self.sync_namespace_edit = QtWidgets.QLineEdit(self.settings.get_sync_namespace())
        self.sync_namespace_edit.setPlaceholderText(SettingsManager.DEFAULT_SYNC_NAMESPACE)
        self.sync_server_form.addRow(tr("settings.sync.namespace"), self.sync_namespace_edit)

        self.sync_token_edit = QtWidgets.QLineEdit("")
        self.sync_token_edit.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.sync_token_edit.setPlaceholderText(tr("settings.sync.token.placeholder"))
        self.sync_token_edit.installEventFilter(self)
        self.sync_server_form.addRow(tr("settings.sync.token"), self.sync_token_edit)

        self.sync_interval_spin = QtWidgets.QSpinBox()
        self.sync_interval_spin.setRange(
            SettingsManager.MIN_SYNC_INTERVAL_SECONDS,
            SettingsManager.MAX_SYNC_INTERVAL_SECONDS,
        )
        self.sync_interval_spin.setValue(self.settings.get_sync_interval_seconds())
        self.sync_server_form.addRow(tr("settings.sync.interval"), self.sync_interval_spin)
        server_layout.addLayout(self.sync_server_form)

        sync_btn_row = QtWidgets.QHBoxLayout()
        self.test_connection_button = QtWidgets.QPushButton(tr("settings.sync.test_btn"))
        self.sync_now_button = QtWidgets.QPushButton(tr("settings.sync.sync_now_btn"))
        self.resolve_conflicts_button = QtWidgets.QPushButton(
            tr("settings.sync.conflicts_btn", count=0)
        )
        sync_btn_row.addWidget(self.test_connection_button)
        sync_btn_row.addWidget(self.sync_now_button)
        sync_btn_row.addWidget(self.resolve_conflicts_button)
        server_layout.addLayout(sync_btn_row)

        sync_outer.addWidget(self.sync_server_container)
        layout.addWidget(self.sync_group)

        # Info
        self.info_group = QtWidgets.QGroupBox(tr("settings.group.info"))
        self.info_form = QtWidgets.QFormLayout(self.info_group)
        self.info_form.addRow(tr("settings.info.data_dir"), QtWidgets.QLabel(str(self.settings.get_data_path())))
        self.info_form.addRow(tr("settings.info.log_file"), QtWidgets.QLabel(str(default_log_dir() / "promptboard.log")))
        layout.addWidget(self.info_group)

        layout.addStretch(1)

        # Close button
        button_row = QtWidgets.QHBoxLayout()
        button_row.addStretch(1)
        self.close_button = QtWidgets.QPushButton(tr("btn.ok"))
        button_row.addWidget(self.close_button)
        layout.addLayout(button_row)

        self._apply_accessibility()

    @staticmethod
    def _row(*widgets: QtWidgets.QWidget) -> QtWidgets.QWidget:
        wrapper = QtWidgets.QWidget()
        h = QtWidgets.QHBoxLayout(wrapper)
        h.setContentsMargins(0, 0, 0, 0)
        for w in widgets:
            h.addWidget(w, 1 if isinstance(w, QtWidgets.QLineEdit) else 0)
        return wrapper

    # ------------------------------------------------------------ signals

    def _connect_signals(self) -> None:
        self.change_materialize_button.clicked.connect(self.change_materialize_path)
        self.change_profiprompt_button.clicked.connect(self.change_profiprompt_path)
        self.change_explorerpro_button.clicked.connect(self.change_explorerpro_path)
        if self._on_import_profiprompt:
            self.import_profiprompt_button.clicked.connect(self._run_import_profiprompt)
        if self._on_import_explorerpro:
            self.import_explorerpro_button.clicked.connect(self._run_import_explorerpro)
        if self._on_export_explorerpro:
            self.export_explorerpro_button.clicked.connect(self._on_export_explorerpro)
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        self.language_combo.currentIndexChanged.connect(self._on_language_changed)
        self.materialize_format_combo.currentIndexChanged.connect(
            self._on_materialize_format_changed
        )
        self.confirm_overwrite_check.toggled.connect(self.settings.set_confirm_overwrite)
        self.profiprompt_enabled_check.toggled.connect(self.settings.set_profiprompt_enabled)
        self.explorerpro_enabled_check.toggled.connect(self.settings.set_explorerpro_enabled)

        self.sync_mode_combo.currentIndexChanged.connect(self._on_sync_mode_changed)
        self.sync_url_edit.editingFinished.connect(self._persist_sync_fields)
        self.sync_namespace_edit.editingFinished.connect(self._persist_sync_fields)
        self.sync_token_edit.textChanged.connect(self._on_sync_token_text_changed)
        self.sync_token_edit.editingFinished.connect(self._persist_sync_fields)
        self.sync_interval_spin.valueChanged.connect(self._on_sync_interval_changed)
        self.test_connection_button.clicked.connect(self.run_test_connection)
        self.sync_now_button.clicked.connect(self.run_sync_now)
        self.resolve_conflicts_button.clicked.connect(self.open_conflicts_dialog)
        self.close_button.clicked.connect(self._on_close_clicked)

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        super().showEvent(event)
        if (self.sync_mode_combo.currentData() or self.settings.get_sync_mode()) == "server":
            self._ensure_sync_token_loaded()
            self._refresh_sync_visibility_and_status()

    def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if (
            watched is self.sync_token_edit
            and event.type() == QtCore.QEvent.Type.FocusIn
            and (self.sync_mode_combo.currentData() or self.settings.get_sync_mode()) == "server"
        ):
            self._ensure_sync_token_loaded()
        return super().eventFilter(watched, event)

    def _on_sync_token_text_changed(self, _text: str) -> None:
        if self._loading_token_ui:
            return
        self._token_loaded = True
        self._token_dirty = True

    def _ensure_sync_token_loaded(self) -> None:
        mode = self.sync_mode_combo.currentData() or self.settings.get_sync_mode()
        if mode != "server" or self._token_loaded:
            return
        self._loading_token_ui = True
        try:
            self.sync_token_edit.setText(self.settings.get_sync_token())
            self._token_loaded = True
        finally:
            self._loading_token_ui = False

    def _prompt_target_queue_change(
        self,
        old_target: str,
        new_target: str,
        pending_count: int,
    ) -> TargetChangeQueueChoice:
        if self._on_target_queue_change is not None:
            return self._on_target_queue_change(old_target, new_target, pending_count)
        dlg = TargetQueueChangeDialog(old_target, new_target, pending_count, parent=self)
        dlg.exec()
        return dlg.choice

    def _run_in_worker_pool(self, fn: Callable[[], Any]) -> Any:
        loop = QtCore.QEventLoop(self)
        holder: dict[str, Any] = {}
        runnable = _DialogWorkerRunnable(fn)
        self._active_runnables.add(runnable)

        def _done(res: Any) -> None:
            self._active_runnables.discard(runnable)
            holder["res"] = res
            if loop.isRunning():
                loop.quit()

        runnable.signals.finished.connect(_done)
        self.finished.connect(loop.quit)
        try:
            self._worker_pool.start(runnable)
            if "res" not in holder:
                loop.exec()
        finally:
            try:
                self.finished.disconnect(loop.quit)
            except (RuntimeError, TypeError):
                pass
        res = holder.get("res")
        if isinstance(res, BaseException):
            raise res
        return res

    def _on_close_clicked(self) -> None:
        if (self.sync_mode_combo.currentData() or "off") == "server":
            self._persist_sync_fields()
        self.accept()

    def _persist_sync_fields(self) -> None:
        engine = self._get_or_create_sync_engine()
        new_url = self.sync_url_edit.text()
        new_ns = self.sync_namespace_edit.text()
        pending_change = engine.inspect_pending_target_change(
            new_url=new_url,
            new_namespace=new_ns,
        )
        self.settings.set_sync_server_url(new_url)
        self.settings.set_sync_namespace(new_ns)
        self.sync_namespace_edit.setText(self.settings.get_sync_namespace())
        if pending_change is not None:
            old_target, new_target, pending_count = pending_change
            q_choice = self._prompt_target_queue_change(old_target, new_target, pending_count)
            engine.apply_target_change(q_choice, new_target=new_target)
        if self._token_dirty:
            self.settings.set_sync_token(self.sync_token_edit.text())
            self._token_dirty = False
        self._notify_sync_settings_changed()
        self._refresh_sync_visibility_and_status()

    def _on_sync_mode_changed(self) -> None:
        mode = self.sync_mode_combo.currentData() or SettingsManager.DEFAULT_SYNC_MODE
        self.settings.set_sync_mode(mode)
        if mode == "server":
            self._ensure_sync_token_loaded()
            self._persist_sync_fields()
        else:
            self._notify_sync_settings_changed()
            self._refresh_sync_visibility_and_status()

    def _on_sync_interval_changed(self, value: int) -> None:
        self.settings.set_sync_interval_seconds(value)
        self._notify_sync_settings_changed()

    def _notify_sync_settings_changed(self) -> None:
        if self._on_sync_settings_changed is not None:
            self._on_sync_settings_changed()

    def _refresh_sync_visibility_and_status(self) -> None:
        mode = self.sync_mode_combo.currentData() or self.settings.get_sync_mode()
        is_server = mode == "server"
        self.sync_server_container.setVisible(is_server)

        focus_edit = (
            QtCore.Qt.FocusPolicy.StrongFocus if is_server else QtCore.Qt.FocusPolicy.NoFocus
        )
        for widget in (
            self.sync_url_edit,
            self.sync_namespace_edit,
            self.sync_token_edit,
            self.sync_interval_spin,
            self.test_connection_button,
            self.sync_now_button,
        ):
            widget.setFocusPolicy(focus_edit)

        if not is_server:
            self.sync_status_label.setText(tr("sync.status.off"))
            self.resolve_conflicts_button.setEnabled(False)
            self.resolve_conflicts_button.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
            return

        engine = self._get_or_create_sync_engine()
        conflicts = engine.get_conflicts()
        pending = engine.get_pending_count()
        lib_rev = engine.get_library_rev()

        conflict_count = len(conflicts)
        self.resolve_conflicts_button.setText(
            tr("settings.sync.conflicts_btn", count=conflict_count)
        )
        self.resolve_conflicts_button.setEnabled(conflict_count > 0)
        self.resolve_conflicts_button.setFocusPolicy(
            QtCore.Qt.FocusPolicy.StrongFocus
            if conflict_count > 0
            else QtCore.Qt.FocusPolicy.NoFocus
        )

        has_token = bool(self.sync_token_edit.text().strip()) if self._token_loaded else False
        if not self.sync_url_edit.text().strip() or not has_token:
            self.sync_status_label.setText(tr("sync.status.unconfigured"))
        elif conflict_count > 0:
            self.sync_status_label.setText(tr("sync.status.conflicts", count=conflict_count))
        elif pending > 0:
            self.sync_status_label.setText(tr("sync.status.offline_pending", count=pending))
        else:
            self.sync_status_label.setText(tr("sync.status.synced", rev=lib_rev))

    def run_test_connection(self) -> bool:
        self._ensure_sync_token_loaded()
        self._persist_sync_fields()
        engine = self._get_or_create_sync_engine()
        url = self.sync_url_edit.text()
        token = self.sync_token_edit.text()
        namespace = self.sync_namespace_edit.text()
        self.sync_status_label.setText(tr("sync.status.syncing"))
        self.test_connection_button.setEnabled(False)
        try:
            status = self._run_in_worker_pool(
                lambda: engine.test_connection(
                    mode="server",
                    server_url=url,
                    token=token,
                    namespace=namespace,
                )
            )
        finally:
            self.test_connection_button.setEnabled(True)
        if status is None:
            return False
        if status.ok:
            self.sync_status_label.setText(
                tr(
                    "sync.status.test_ok",
                    ms=status.latency_ms,
                    rev=status.library_rev if status.library_rev is not None else 0,
                )
            )
            return True
        self.sync_status_label.setText(tr("sync.status.test_failed", detail=status.detail))
        return False

    def run_sync_now(self) -> Optional[SyncOutcome]:
        self._ensure_sync_token_loaded()
        self._persist_sync_fields()
        self.sync_now_button.setEnabled(False)
        try:
            if self._on_sync_now is not None:
                outcome = self._on_sync_now()
            else:
                engine = self._get_or_create_sync_engine()
                outcome = self._run_in_worker_pool(engine.sync_once)
        finally:
            self.sync_now_button.setEnabled(True)
        self._refresh_sync_visibility_and_status()
        if outcome is not None and not outcome.ok and outcome.error:
            self.sync_status_label.setText(tr("sync.status.test_failed", detail=outcome.error))
        return outcome

    def open_conflicts_dialog(self) -> None:
        if self._on_resolve_conflicts is not None:
            self._on_resolve_conflicts()
        else:
            dlg = ConflictResolutionDialog(self._get_or_create_sync_engine(), parent=self)
            dlg.exec()
        self._refresh_sync_visibility_and_status()

    def _run_import_profiprompt(self) -> None:
        if self._on_import_profiprompt and self._on_import_profiprompt():
            self.accept()

    def _run_import_explorerpro(self) -> None:
        if self._on_import_explorerpro and self._on_import_explorerpro():
            self.accept()

    def _on_materialize_format_changed(self) -> None:
        fmt = (
            self.materialize_format_combo.currentData()
            or SettingsManager.DEFAULT_MATERIALIZE_FORMAT
        )
        self.settings.set_materialize_format(fmt)

    def _on_theme_changed(self) -> None:
        mode = self.theme_combo.currentData() or SettingsManager.DEFAULT_THEME
        self.settings.set_theme(mode)
        self.theme_changed.emit(mode)

    def _on_language_changed(self) -> None:
        code = self.language_combo.currentData() or SettingsManager.DEFAULT_LANGUAGE
        self.settings.set_language(code)
        set_global_language(code)
        self.relabel_ui()
        self.language_changed.emit(code)

    # ------------------------------------------------------------ path pickers

    def change_materialize_path(self) -> None:
        current = str(self.settings.get_materialize_path())
        new_path = QtWidgets.QFileDialog.getExistingDirectory(
            self, tr("dialog.choose_materialize_path"), current
        )
        if new_path:
            self.settings.set_materialize_path(Path(new_path))
            self.materialize_path_edit.setText(new_path)

    def change_profiprompt_path(self) -> None:
        current = str(self.settings.get_profiprompt_data_path())
        new_path = QtWidgets.QFileDialog.getExistingDirectory(
            self, tr("dialog.choose_profiprompt_path"), current
        )
        if new_path:
            self.settings.set_profiprompt_data_path(Path(new_path))
            self.profiprompt_path_edit.setText(new_path)

    def change_explorerpro_path(self) -> None:
        current = str(self.settings.get_explorerpro_data_path())
        new_path = QtWidgets.QFileDialog.getExistingDirectory(
            self, tr("dialog.choose_explorerpro_path"), current
        )
        if new_path:
            self.settings.set_explorerpro_data_path(Path(new_path))
            self.explorerpro_path_edit.setText(new_path)

    # ------------------------------------------------------------ accessibility & i18n

    def _apply_accessibility(self) -> None:
        self.paths_group.setAccessibleName(tr("settings.group.paths"))
        self.paths_group.setAccessibleDescription(tr("settings.group.paths.tooltip"))
        self.paths_group.setToolTip(tr("settings.group.paths.tooltip"))

        self.materialize_path_edit.setAccessibleName(tr("settings.path.materialize"))
        self.materialize_path_edit.setAccessibleDescription(tr("settings.path.materialize.tooltip"))
        self.materialize_path_edit.setToolTip(tr("settings.path.materialize.tooltip"))
        self.change_materialize_button.setAccessibleName(tr("settings.btn.change.materialize.tooltip"))
        self.change_materialize_button.setAccessibleDescription(tr("settings.btn.change.materialize.tooltip"))
        self.change_materialize_button.setToolTip(tr("settings.btn.change.materialize.tooltip"))

        self.profiprompt_path_edit.setAccessibleName(tr("settings.path.profiprompt"))
        self.profiprompt_path_edit.setAccessibleDescription(tr("settings.path.profiprompt.tooltip"))
        self.profiprompt_path_edit.setToolTip(tr("settings.path.profiprompt.tooltip"))
        self.change_profiprompt_button.setAccessibleName(tr("settings.btn.change.profiprompt.tooltip"))
        self.change_profiprompt_button.setAccessibleDescription(tr("settings.btn.change.profiprompt.tooltip"))
        self.change_profiprompt_button.setToolTip(tr("settings.btn.change.profiprompt.tooltip"))

        self.explorerpro_path_edit.setAccessibleName(tr("settings.path.explorerpro"))
        self.explorerpro_path_edit.setAccessibleDescription(tr("settings.path.explorerpro.tooltip"))
        self.explorerpro_path_edit.setToolTip(tr("settings.path.explorerpro.tooltip"))
        self.change_explorerpro_button.setAccessibleName(tr("settings.btn.change.explorerpro.tooltip"))
        self.change_explorerpro_button.setAccessibleDescription(tr("settings.btn.change.explorerpro.tooltip"))
        self.change_explorerpro_button.setToolTip(tr("settings.btn.change.explorerpro.tooltip"))

        self.io_group.setAccessibleName(tr("settings.group.io"))
        self.io_group.setAccessibleDescription(tr("settings.group.io.tooltip"))
        self.io_group.setToolTip(tr("settings.group.io.tooltip"))

        self.import_profiprompt_button.setAccessibleName(tr("settings.io.import_profiprompt"))
        self.import_profiprompt_button.setAccessibleDescription(tr("settings.io.import_profiprompt.tooltip"))
        self.import_profiprompt_button.setToolTip(tr("settings.io.import_profiprompt.tooltip"))

        self.import_explorerpro_button.setAccessibleName(tr("settings.io.import_explorerpro"))
        self.import_explorerpro_button.setAccessibleDescription(tr("settings.io.import_explorerpro.tooltip"))
        self.import_explorerpro_button.setToolTip(tr("settings.io.import_explorerpro.tooltip"))

        self.export_explorerpro_button.setAccessibleName(tr("settings.io.export_explorerpro"))
        self.export_explorerpro_button.setAccessibleDescription(tr("settings.io.export_explorerpro.tooltip"))
        self.export_explorerpro_button.setToolTip(tr("settings.io.export_explorerpro.tooltip"))

        self.profiprompt_enabled_check.setAccessibleName(tr("settings.imports.profiprompt_enabled"))
        self.profiprompt_enabled_check.setAccessibleDescription(tr("settings.imports.profiprompt_enabled.tooltip"))
        self.profiprompt_enabled_check.setToolTip(tr("settings.imports.profiprompt_enabled.tooltip"))

        self.explorerpro_enabled_check.setAccessibleName(tr("settings.imports.explorerpro_enabled"))
        self.explorerpro_enabled_check.setAccessibleDescription(tr("settings.imports.explorerpro_enabled.tooltip"))
        self.explorerpro_enabled_check.setToolTip(tr("settings.imports.explorerpro_enabled.tooltip"))

        self.view_group.setAccessibleName(tr("settings.group.view"))
        self.view_group.setAccessibleDescription(tr("settings.group.view.tooltip"))
        self.view_group.setToolTip(tr("settings.group.view.tooltip"))

        self.theme_combo.setAccessibleName(tr("settings.view.theme"))
        self.theme_combo.setAccessibleDescription(tr("settings.view.theme.tooltip"))
        self.theme_combo.setToolTip(tr("settings.view.theme.tooltip"))

        self.language_combo.setAccessibleName(tr("settings.view.language"))
        self.language_combo.setAccessibleDescription(tr("settings.view.language.tooltip"))
        self.language_combo.setToolTip(tr("settings.view.language.tooltip"))

        self.materialize_format_combo.setAccessibleName(tr("settings.view.materialize_format"))
        self.materialize_format_combo.setAccessibleDescription(tr("settings.view.materialize_format.tooltip"))
        self.materialize_format_combo.setToolTip(tr("settings.view.materialize_format.tooltip"))

        self.confirm_overwrite_check.setAccessibleName(tr("settings.view.confirm_overwrite"))
        self.confirm_overwrite_check.setAccessibleDescription(tr("settings.view.confirm_overwrite.tooltip"))
        self.confirm_overwrite_check.setToolTip(tr("settings.view.confirm_overwrite.tooltip"))

        self.sync_group.setAccessibleName(tr("settings.group.sync"))
        self.sync_group.setAccessibleDescription(tr("settings.group.sync.tooltip"))
        self.sync_group.setToolTip(tr("settings.group.sync.tooltip"))

        self.sync_mode_combo.setAccessibleName(tr("settings.sync.mode"))
        self.sync_mode_combo.setAccessibleDescription(tr("settings.sync.mode.tooltip"))
        self.sync_mode_combo.setToolTip(tr("settings.sync.mode.tooltip"))

        self.sync_url_edit.setAccessibleName(tr("settings.sync.server_url"))
        self.sync_url_edit.setAccessibleDescription(tr("settings.sync.server_url.tooltip"))
        self.sync_url_edit.setToolTip(tr("settings.sync.server_url.tooltip"))

        self.sync_namespace_edit.setAccessibleName(tr("settings.sync.namespace"))
        self.sync_namespace_edit.setAccessibleDescription(tr("settings.sync.namespace.tooltip"))
        self.sync_namespace_edit.setToolTip(tr("settings.sync.namespace.tooltip"))

        self.sync_token_edit.setAccessibleName(tr("settings.sync.token"))
        self.sync_token_edit.setAccessibleDescription(tr("settings.sync.token.tooltip"))
        self.sync_token_edit.setToolTip(tr("settings.sync.token.tooltip"))

        self.sync_interval_spin.setAccessibleName(tr("settings.sync.interval"))
        self.sync_interval_spin.setAccessibleDescription(tr("settings.sync.interval.tooltip"))
        self.sync_interval_spin.setToolTip(tr("settings.sync.interval.tooltip"))

        self.test_connection_button.setAccessibleName(tr("settings.sync.test_btn"))
        self.test_connection_button.setAccessibleDescription(tr("settings.sync.test_btn.tooltip"))
        self.test_connection_button.setToolTip(tr("settings.sync.test_btn.tooltip"))

        self.sync_now_button.setAccessibleName(tr("settings.sync.sync_now_btn"))
        self.sync_now_button.setAccessibleDescription(tr("settings.sync.sync_now_btn.tooltip"))
        self.sync_now_button.setToolTip(tr("settings.sync.sync_now_btn.tooltip"))

        self.resolve_conflicts_button.setAccessibleName(
            tr("settings.sync.conflicts_btn", count=len(self._get_or_create_sync_engine().get_conflicts()) if (self.sync_mode_combo.currentData() == "server") else 0)
        )
        self.resolve_conflicts_button.setAccessibleDescription(tr("settings.sync.conflicts_btn.tooltip"))
        self.resolve_conflicts_button.setToolTip(tr("settings.sync.conflicts_btn.tooltip"))

        self.info_group.setAccessibleName(tr("settings.group.info"))
        self.info_group.setAccessibleDescription(tr("settings.group.info.tooltip"))
        self.info_group.setToolTip(tr("settings.group.info.tooltip"))

        self.close_button.setAccessibleName(tr("settings.btn.close.name"))
        self.close_button.setAccessibleDescription(tr("settings.btn.close.tooltip"))
        self.close_button.setToolTip(tr("settings.btn.close.tooltip"))

    def relabel_ui(self) -> None:
        """Apply active language translations to dialog window elements dynamically."""
        self.setWindowTitle(tr("settings.title"))
        self.paths_group.setTitle(tr("settings.group.paths"))
        self.io_group.setTitle(tr("settings.group.io"))
        self.view_group.setTitle(tr("settings.group.view"))
        self.sync_group.setTitle(tr("settings.group.sync"))
        self.info_group.setTitle(tr("settings.group.info"))

        self.change_materialize_button.setText(tr("btn.change"))
        self.change_profiprompt_button.setText(tr("btn.change"))
        self.change_explorerpro_button.setText(tr("btn.change"))
        self.import_profiprompt_button.setText(tr("settings.io.import_profiprompt"))
        self.import_explorerpro_button.setText(tr("settings.io.import_explorerpro"))
        self.export_explorerpro_button.setText(tr("settings.io.export_explorerpro"))
        self.confirm_overwrite_check.setText(tr("settings.view.confirm_overwrite"))
        self.profiprompt_enabled_check.setText(tr("settings.imports.profiprompt_enabled"))
        self.explorerpro_enabled_check.setText(tr("settings.imports.explorerpro_enabled"))
        self.sync_token_edit.setPlaceholderText(tr("settings.sync.token.placeholder"))
        self.test_connection_button.setText(tr("settings.sync.test_btn"))
        self.sync_now_button.setText(tr("settings.sync.sync_now_btn"))
        self.close_button.setText(tr("btn.ok"))

        labels_paths = [
            tr("settings.path.materialize"),
            tr("settings.path.profiprompt"),
            tr("settings.path.explorerpro"),
        ]
        for i, text in enumerate(labels_paths):
            label_item = self.paths_form.itemAt(i, QtWidgets.QFormLayout.LabelRole)
            if label_item and isinstance(label_item.widget(), QtWidgets.QLabel):
                label_item.widget().setText(text)

        labels_view = [
            tr("settings.view.theme"),
            tr("settings.view.language"),
            tr("settings.view.materialize_format"),
        ]
        for i, text in enumerate(labels_view):
            label_item = self.view_form.itemAt(i, QtWidgets.QFormLayout.LabelRole)
            if label_item and isinstance(label_item.widget(), QtWidgets.QLabel):
                label_item.widget().setText(text)

        labels_sync_top = [
            tr("settings.sync.mode"),
            tr("settings.sync.status_label"),
        ]
        for i, text in enumerate(labels_sync_top):
            label_item = self.sync_top_form.itemAt(i, QtWidgets.QFormLayout.LabelRole)
            if label_item and isinstance(label_item.widget(), QtWidgets.QLabel):
                label_item.widget().setText(text)

        labels_sync_srv = [
            tr("settings.sync.server_url"),
            tr("settings.sync.namespace"),
            tr("settings.sync.token"),
            tr("settings.sync.interval"),
        ]
        for i, text in enumerate(labels_sync_srv):
            label_item = self.sync_server_form.itemAt(i, QtWidgets.QFormLayout.LabelRole)
            if label_item and isinstance(label_item.widget(), QtWidgets.QLabel):
                label_item.widget().setText(text)

        labels_info = [
            tr("settings.info.data_dir"),
            tr("settings.info.log_file"),
        ]
        for i, text in enumerate(labels_info):
            label_item = self.info_form.itemAt(i, QtWidgets.QFormLayout.LabelRole)
            if label_item and isinstance(label_item.widget(), QtWidgets.QLabel):
                label_item.widget().setText(text)

        for i in range(self.theme_combo.count()):
            mode = self.theme_combo.itemData(i)
            self.theme_combo.setItemText(i, tr(f"theme.{mode}"))

        for i in range(self.language_combo.count()):
            code = self.language_combo.itemData(i)
            self.language_combo.setItemText(i, tr(f"lang.{code}"))

        for i in range(self.materialize_format_combo.count()):
            fmt = self.materialize_format_combo.itemData(i)
            self.materialize_format_combo.setItemText(i, tr(f"materialize.format.{fmt}"))

        for i in range(self.sync_mode_combo.count()):
            sm = self.sync_mode_combo.itemData(i)
            self.sync_mode_combo.setItemText(i, tr(f"sync.mode.{sm}"))

        self._refresh_sync_visibility_and_status()
        self._apply_accessibility()
