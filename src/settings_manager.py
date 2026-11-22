from __future__ import annotations

import logging
import sys
import uuid
from pathlib import Path

from PySide6 import QtCore

from library_query import DEFAULT_SORT_MODE, coerce_sort_mode
from sync_backend import (
     DEFAULT_NAMESPACE,
     DEFAULT_SYNC_MODE,
     SYNC_MODES,
     TokenStorage,
     validate_namespace,
)

logger = logging.getLogger(__name__)

_FOLDERID_DESKTOP_BYTES = uuid.UUID("{B4BFCC3A-DB2C-424C-B029-7FE99A87C641}").bytes_le


def _known_desktop_folder() -> Path:
    """Resolve the active OS Desktop directory (supports OneDrive Known Folder Move).

    Falls back to ``Path.home() / "Desktop"`` on non-Windows platforms or if
    ``SHGetKnownFolderPath`` is unavailable or returns an empty/unusable path.
    """
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            shell32 = ctypes.windll.shell32
            ole32 = ctypes.windll.ole32
            p_path = wintypes.LPWSTR()
            hr = shell32.SHGetKnownFolderPath(
                ctypes.create_string_buffer(_FOLDERID_DESKTOP_BYTES, 16),
                0,
                None,
                ctypes.byref(p_path),
            )
            if hr == 0 and p_path.value:
                resolved = Path(p_path.value)
                ole32.CoTaskMemFree(p_path)
                return resolved
            if p_path:
                ole32.CoTaskMemFree(p_path)
        except Exception:  # noqa: BLE001 — headless/sandboxed hosts fall back safely
            pass
    return Path.home() / "Desktop"


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
        desktop_default = _known_desktop_folder()
        if not raw:
            self.qs.setValue("paths/materialize", str(desktop_default))
            self.qs.sync()
            raw = str(desktop_default)
        path = Path(raw)
        return _ensure_dir(path, desktop_default)

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

    # ---- Synchronization settings (Stage 1b) ----------------------------

    SYNC_MODE_CHOICES = SYNC_MODES
    UI_SYNC_MODE_CHOICES = ("off", "server")
    DEFAULT_SYNC_MODE = DEFAULT_SYNC_MODE
    DEFAULT_SYNC_NAMESPACE = DEFAULT_NAMESPACE
    DEFAULT_SYNC_INTERVAL_SECONDS = 300
    MIN_SYNC_INTERVAL_SECONDS = 15
    MAX_SYNC_INTERVAL_SECONDS = 86400

    def _token_storage(self) -> TokenStorage:
        existing = getattr(self, "_cached_token_storage", None)
        if existing is None:
            existing = TokenStorage()
            self._cached_token_storage = existing
        return existing

    def get_sync_mode(self) -> str:
        raw = self.qs.value("sync/mode", "", type=str)
        if raw not in self.SYNC_MODE_CHOICES:
            if raw:
                self.qs.setValue("sync/mode", self.DEFAULT_SYNC_MODE)
                self.qs.sync()
            return self.DEFAULT_SYNC_MODE
        return raw

    def set_sync_mode(self, mode: str) -> None:
        cleaned = (mode or "").strip().lower()
        if cleaned not in self.SYNC_MODE_CHOICES:
            cleaned = self.DEFAULT_SYNC_MODE
        self.qs.setValue("sync/mode", cleaned)
        self.qs.sync()

    def get_sync_server_url(self) -> str:
        raw = self.qs.value("sync/server_url", "", type=str)
        return (raw or "").strip()

    def set_sync_server_url(self, url: str) -> None:
        self.qs.setValue("sync/server_url", (url or "").strip())
        self.qs.sync()

    def get_sync_namespace(self) -> str:
        raw = self.qs.value("sync/namespace", "", type=str)
        try:
            return validate_namespace(raw)
        except ValueError:
            self.qs.setValue("sync/namespace", self.DEFAULT_SYNC_NAMESPACE)
            self.qs.sync()
            return self.DEFAULT_SYNC_NAMESPACE

    def set_sync_namespace(self, namespace: str) -> None:
        try:
            valid = validate_namespace(namespace)
        except ValueError:
            valid = self.DEFAULT_SYNC_NAMESPACE
        self.qs.setValue("sync/namespace", valid)
        self.qs.sync()

    def get_sync_interval_seconds(self) -> int:
        raw = self.qs.value("sync/interval_seconds", self.DEFAULT_SYNC_INTERVAL_SECONDS)
        try:
            val = int(raw)
        except (TypeError, ValueError):
            val = self.DEFAULT_SYNC_INTERVAL_SECONDS
        clamped = max(self.MIN_SYNC_INTERVAL_SECONDS, min(self.MAX_SYNC_INTERVAL_SECONDS, val))
        if clamped != val:
            self.qs.setValue("sync/interval_seconds", clamped)
            self.qs.sync()
        return clamped

    def set_sync_interval_seconds(self, seconds: int) -> None:
        try:
            val = int(seconds)
        except (TypeError, ValueError):
            val = self.DEFAULT_SYNC_INTERVAL_SECONDS
        clamped = max(self.MIN_SYNC_INTERVAL_SECONDS, min(self.MAX_SYNC_INTERVAL_SECONDS, val))
        self.qs.setValue("sync/interval_seconds", clamped)
        self.qs.sync()

    def get_sync_token(self) -> str:
        return self._token_storage().get_token()

    def set_sync_token(self, token: str) -> None:
        self._token_storage().set_token(token)
