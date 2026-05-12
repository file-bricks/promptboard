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
        paths_group = QtWidgets.QGroupBox(tr("settings.group.paths"))
        paths_form = QtWidgets.QFormLayout(paths_group)

        self.materialize_path_edit = QtWidgets.QLineEdit(str(self.settings.get_materialize_path()))
        self.materialize_path_edit.setReadOnly(True)
        self.change_materialize_button = QtWidgets.QPushButton(tr("btn.change"))
        paths_form.addRow(
            tr("settings.path.materialize"),
            self._row(self.materialize_path_edit, self.change_materialize_button),
        )

        self.profiprompt_path_edit = QtWidgets.QLineEdit(str(self.settings.get_profiprompt_data_path()))
        self.profiprompt_path_edit.setReadOnly(True)
        self.change_profiprompt_button = QtWidgets.QPushButton(tr("btn.change"))
        paths_form.addRow(
            tr("settings.path.profiprompt"),
            self._row(self.profiprompt_path_edit, self.change_profiprompt_button),
        )

        self.explorerpro_path_edit = QtWidgets.QLineEdit(str(self.settings.get_explorerpro_data_path()))
        self.explorerpro_path_edit.setReadOnly(True)
        self.change_explorerpro_button = QtWidgets.QPushButton(tr("btn.change"))
        paths_form.addRow(
            tr("settings.path.explorerpro"),
            self._row(self.explorerpro_path_edit, self.change_explorerpro_button),
        )

        layout.addWidget(paths_group)

        # Import/Export
        io_group = QtWidgets.QGroupBox(tr("settings.group.io"))
        io_layout = QtWidgets.QHBoxLayout(io_group)
        self.import_profiprompt_button = QtWidgets.QPushButton(tr("settings.io.import_profiprompt"))
        self.import_explorerpro_button = QtWidgets.QPushButton(tr("settings.io.import_explorerpro"))
        self.export_explorerpro_button = QtWidgets.QPushButton(tr("settings.io.export_explorerpro"))
        io_layout.addWidget(self.import_profiprompt_button)
        io_layout.addWidget(self.import_explorerpro_button)
        io_layout.addWidget(self.export_explorerpro_button)
        layout.addWidget(io_group)

        # Ansicht
        view_group = QtWidgets.QGroupBox(tr("settings.group.view"))
        view_form = QtWidgets.QFormLayout(view_group)

        self.theme_combo = QtWidgets.QComboBox()
        for mode in SettingsManager.THEME_CHOICES:
            self.theme_combo.addItem(tr(f"theme.{mode}"), mode)
        current_theme = self.settings.get_theme()
        idx = self.theme_combo.findData(current_theme)
        if idx >= 0:
            self.theme_combo.setCurrentIndex(idx)
        view_form.addRow(tr("settings.view.theme"), self.theme_combo)

        self.language_combo = QtWidgets.QComboBox()
        for code in SettingsManager.LANGUAGE_CHOICES:
            self.language_combo.addItem(tr(f"lang.{code}"), code)
        current_lang = self.settings.get_language()
        idx = self.language_combo.findData(current_lang)
        if idx >= 0:
            self.language_combo.setCurrentIndex(idx)
        view_form.addRow(tr("settings.view.language"), self.language_combo)

        self.confirm_overwrite_check = QtWidgets.QCheckBox(tr("settings.view.confirm_overwrite"))
        self.confirm_overwrite_check.setChecked(self.settings.get_confirm_overwrite())
        view_form.addRow("", self.confirm_overwrite_check)

        layout.addWidget(view_group)

        # Info
        info_group = QtWidgets.QGroupBox(tr("settings.group.info"))
        info_form = QtWidgets.QFormLayout(info_group)
        info_form.addRow(tr("settings.info.data_dir"), QtWidgets.QLabel(str(self.settings.get_data_path())))
        info_form.addRow(tr("settings.info.log_file"), QtWidgets.QLabel(str(default_log_dir() / "promptboard.log")))
        layout.addWidget(info_group)

        layout.addStretch(1)

        # Close button
        button_row = QtWidgets.QHBoxLayout()
        button_row.addStretch(1)
        self.close_button = QtWidgets.QPushButton(tr("btn.ok"))
        button_row.addWidget(self.close_button)
        layout.addLayout(button_row)

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
            self.import_profiprompt_button.clicked.connect(self._on_import_profiprompt)
        if self._on_import_explorerpro:
            self.import_explorerpro_button.clicked.connect(self._on_import_explorerpro)
        if self._on_export_explorerpro:
            self.export_explorerpro_button.clicked.connect(self._on_export_explorerpro)
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        self.language_combo.currentIndexChanged.connect(self._on_language_changed)
        self.confirm_overwrite_check.toggled.connect(self.settings.set_confirm_overwrite)
        self.close_button.clicked.connect(self.accept)

    def _on_theme_changed(self) -> None:
        mode = self.theme_combo.currentData() or SettingsManager.DEFAULT_THEME
        self.settings.set_theme(mode)
        self.theme_changed.emit(mode)

    def _on_language_changed(self) -> None:
        code = self.language_combo.currentData() or SettingsManager.DEFAULT_LANGUAGE
        self.settings.set_language(code)
        set_global_language(code)
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
