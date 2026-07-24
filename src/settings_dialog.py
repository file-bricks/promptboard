"""Settings dialog for PromptBoard.

Replaces the dedicated "Einstellungen" tab — settings are now reached
via the Menübar ("Einstellungen → Einstellungen…") and shown as a
modal dialog.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from PySide6 import QtCore, QtWidgets

from i18n import set_language as set_global_language
from i18n import tr
from logging_setup import default_log_dir
from settings_manager import SettingsManager


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
    ) -> None:
        super().__init__(parent)
        self.settings = settings
        self._on_import_profiprompt = on_import_profiprompt
        self._on_import_explorerpro = on_import_explorerpro
        self._on_export_explorerpro = on_export_explorerpro

        self.setWindowTitle(tr("settings.title"))
        self.resize(620, 480)
        self.setModal(True)

        self._build_ui()
        self._connect_signals()

    # ------------------------------------------------------------ UI

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)

        # Pfade
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

        # Availability toggles decide which File-menu import entries show (U3).
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

        # Ansicht
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
        self.close_button.clicked.connect(self.accept)

    def _run_import_profiprompt(self) -> None:
        # Close the modal dialog on a successful import so the host window's
        # auto-refreshed library becomes visible immediately (U1).
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
        self.info_group.setTitle(tr("settings.group.info"))

        # Re-set buttons text
        self.change_materialize_button.setText(tr("btn.change"))
        self.change_profiprompt_button.setText(tr("btn.change"))
        self.change_explorerpro_button.setText(tr("btn.change"))
        self.import_profiprompt_button.setText(tr("settings.io.import_profiprompt"))
        self.import_explorerpro_button.setText(tr("settings.io.import_explorerpro"))
        self.export_explorerpro_button.setText(tr("settings.io.export_explorerpro"))
        self.confirm_overwrite_check.setText(tr("settings.view.confirm_overwrite"))
        self.profiprompt_enabled_check.setText(tr("settings.imports.profiprompt_enabled"))
        self.explorerpro_enabled_check.setText(tr("settings.imports.explorerpro_enabled"))
        self.close_button.setText(tr("btn.ok"))

        # Form labels re-labeling
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

        labels_info = [
            tr("settings.info.data_dir"),
            tr("settings.info.log_file"),
        ]
        for i, text in enumerate(labels_info):
            label_item = self.info_form.itemAt(i, QtWidgets.QFormLayout.LabelRole)
            if label_item and isinstance(label_item.widget(), QtWidgets.QLabel):
                label_item.widget().setText(text)

        # Combo boxes items
        for i in range(self.theme_combo.count()):
            mode = self.theme_combo.itemData(i)
            self.theme_combo.setItemText(i, tr(f"theme.{mode}"))

        for i in range(self.language_combo.count()):
            code = self.language_combo.itemData(i)
            self.language_combo.setItemText(i, tr(f"lang.{code}"))

        for i in range(self.materialize_format_combo.count()):
            fmt = self.materialize_format_combo.itemData(i)
            self.materialize_format_combo.setItemText(i, tr(f"materialize.format.{fmt}"))

        self._apply_accessibility()
