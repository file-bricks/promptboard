from __future__ import annotations

import logging
from pathlib import Path

from PySide6 import QtCore

from library_query import DEFAULT_SORT_MODE, coerce_sort_mode

logger = logging.getLogger(__name__)


def _ensure_dir(path: Path, fallback: Path) -> Path:
    """BUGSWEEP-38: Verzeichnis sicherstellen, bei OSError auf Default-Pfad ausweichen.

    Ein vom Nutzer gesetzter Pfad auf nicht-existentem Laufwerk / ohne Rechte / als Datei statt
    Ordner liess mkdir sonst ungefangen werfen -> harter Start-Crash ohne Hinweis.
    """
    try:
        path.mkdir(parents=True, exist_ok=True)
        return path
    except OSError as exc:
        logger.warning("Pfad %s nicht nutzbar (%s) -> Fallback %s", path, exc, fallback)
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


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
        return _ensure_dir(path, Path.home() / ".promptboard")

    def get_materialize_path(self) -> Path:
        raw = self.qs.value("paths/materialize", "", type=str)
        if not raw:
            default = Path.home() / "Desktop"
            self.qs.setValue("paths/materialize", str(default))
            self.qs.sync()
            raw = str(default)
        path = Path(raw)
        return _ensure_dir(path, Path.home() / "Desktop")

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

    # ---- Import-source availability (U3) --------------------------------
    # An import menu entry is only shown when its source software is
    # "configured": either explicitly enabled in settings, or auto-detected on
    # first run by the presence of its ``prompts.json``.

    def _detect_profiprompt(self) -> bool:
        return (self.get_profiprompt_data_path() / "prompts.json").exists()

    def _detect_explorerpro(self) -> bool:
        return (self.get_explorerpro_data_path() / "prompts.json").exists()

    def is_profiprompt_enabled(self) -> bool:
        key = "imports/profiprompt_enabled"
        if not self.qs.contains(key):
            detected = self._detect_profiprompt()
            self.qs.setValue(key, detected)
            self.qs.sync()
            return detected
        return bool(self.qs.value(key, False, type=bool))

    def set_profiprompt_enabled(self, value: bool) -> None:
        self.qs.setValue("imports/profiprompt_enabled", bool(value))
        self.qs.sync()

    def is_explorerpro_enabled(self) -> bool:
        key = "imports/explorerpro_enabled"
        if not self.qs.contains(key):
            detected = self._detect_explorerpro()
            self.qs.setValue(key, detected)
            self.qs.sync()
            return detected
        return bool(self.qs.value(key, False, type=bool))

    def set_explorerpro_enabled(self, value: bool) -> None:
        self.qs.setValue("imports/explorerpro_enabled", bool(value))
        self.qs.sync()

    THEME_CHOICES = ("system", "light", "dark", "vibrant")
    DEFAULT_THEME = "system"

    LANGUAGE_CHOICES = ("de", "en")
    DEFAULT_LANGUAGE = "de"

    def get_language(self) -> str:
        raw = self.qs.value("view/language", "", type=str)
        if raw not in self.LANGUAGE_CHOICES:
            self.qs.setValue("view/language", self.DEFAULT_LANGUAGE)
            self.qs.sync()
            return self.DEFAULT_LANGUAGE
        return raw

    def set_language(self, language: str) -> None:
        if language not in self.LANGUAGE_CHOICES:
            language = self.DEFAULT_LANGUAGE
        self.qs.setValue("view/language", language)
        self.qs.sync()

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

    MATERIALIZE_FORMAT_CHOICES = ("markdown", "txt")
    DEFAULT_MATERIALIZE_FORMAT = "markdown"

    def get_materialize_format(self) -> str:
        raw = self.qs.value("materialize/format", "", type=str)
        if raw not in self.MATERIALIZE_FORMAT_CHOICES:
            self.qs.setValue("materialize/format", self.DEFAULT_MATERIALIZE_FORMAT)
            self.qs.sync()
            return self.DEFAULT_MATERIALIZE_FORMAT
        return raw

    def set_materialize_format(self, value: str) -> None:
        if value not in self.MATERIALIZE_FORMAT_CHOICES:
            value = self.DEFAULT_MATERIALIZE_FORMAT
        self.qs.setValue("materialize/format", value)
        self.qs.sync()

    def get_confirm_overwrite(self) -> bool:
        raw = self.qs.value("materialize/confirm_overwrite", False, type=bool)
        return bool(raw)

    def set_confirm_overwrite(self, value: bool) -> None:
        self.qs.setValue("materialize/confirm_overwrite", bool(value))
        self.qs.sync()

    def get_last_active_item_id(self) -> str:
        return self.qs.value("session/last_active_item_id", "", type=str)

    def set_last_active_item_id(self, item_id: str) -> None:
        self.qs.setValue("session/last_active_item_id", str(item_id))
        self.qs.sync()

    def is_onboarding_shown(self) -> bool:
        return bool(self.qs.value("session/onboarding_shown", False, type=bool))

    def set_onboarding_shown(self, value: bool = True) -> None:
        self.qs.setValue("session/onboarding_shown", bool(value))
        self.qs.sync()
