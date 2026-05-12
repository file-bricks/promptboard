from __future__ import annotations

from pathlib import Path

from PySide6 import QtCore

from library_query import DEFAULT_SORT_MODE, coerce_sort_mode


class SettingsManager(QtCore.QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.qs = QtCore.QSettings(
            QtCore.QSettings.IniFormat,
            QtCore.QSettings.UserScope,
            "PromptBoard",
            "PromptBoard",
        )

    def get_data_path(self) -> Path:
        raw = self.qs.value("paths/data", "", type=str)
        if not raw:
            default = Path.home() / ".promptboard"
            self.qs.setValue("paths/data", str(default))
            self.qs.sync()
            raw = str(default)
        path = Path(raw)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_materialize_path(self) -> Path:
        raw = self.qs.value("paths/materialize", "", type=str)
        if not raw:
            default = Path.home() / "Desktop"
            self.qs.setValue("paths/materialize", str(default))
            self.qs.sync()
            raw = str(default)
        path = Path(raw)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def set_materialize_path(self, path: Path) -> None:
        self.qs.setValue("paths/materialize", str(Path(path)))
        self.qs.sync()

    def get_sort_mode(self) -> str:
        raw = self.qs.value("view/sort_mode", "", type=str)
        sort_mode = coerce_sort_mode(raw)
        if raw != sort_mode:
            self.qs.setValue("view/sort_mode", DEFAULT_SORT_MODE)
            self.qs.sync()
        return sort_mode

    def set_sort_mode(self, sort_mode: str) -> None:
        self.qs.setValue("view/sort_mode", coerce_sort_mode(sort_mode))
        self.qs.sync()

    def get_profiprompt_data_path(self) -> Path:
        raw = self.qs.value("imports/profiprompt_data", "", type=str)
        if not raw:
            default = Path.home() / ".prompt_manager"
            self.qs.setValue("imports/profiprompt_data", str(default))
            self.qs.sync()
            raw = str(default)
        return Path(raw)

    def set_profiprompt_data_path(self, path: Path) -> None:
        self.qs.setValue("imports/profiprompt_data", str(Path(path)))
        self.qs.sync()

    def get_explorerpro_data_path(self) -> Path:
        raw = self.qs.value("imports/explorerpro_data", "", type=str)
        if not raw:
            default = Path.home() / ".explorerpro"
            self.qs.setValue("imports/explorerpro_data", str(default))
            self.qs.sync()
            raw = str(default)
        return Path(raw)

    def set_explorerpro_data_path(self, path: Path) -> None:
        self.qs.setValue("imports/explorerpro_data", str(Path(path)))
        self.qs.sync()

    THEME_CHOICES = ("system", "light", "dark")
    DEFAULT_THEME = "system"

    def get_theme(self) -> str:
        raw = self.qs.value("view/theme", "", type=str)
        if raw not in self.THEME_CHOICES:
            self.qs.setValue("view/theme", self.DEFAULT_THEME)
            self.qs.sync()
            return self.DEFAULT_THEME
        return raw

    def set_theme(self, theme: str) -> None:
        if theme not in self.THEME_CHOICES:
            theme = self.DEFAULT_THEME
        self.qs.setValue("view/theme", theme)
        self.qs.sync()

    def get_confirm_overwrite(self) -> bool:
        raw = self.qs.value("materialize/confirm_overwrite", False, type=bool)
        return bool(raw)

    def set_confirm_overwrite(self, value: bool) -> None:
        self.qs.setValue("materialize/confirm_overwrite", bool(value))
        self.qs.sync()
