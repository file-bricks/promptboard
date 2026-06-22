from __future__ import annotations

import ctypes
import ctypes.wintypes
import logging
import sys
from dataclasses import dataclass
from typing import Callable, Optional

from PySide6 import QtCore

logger = logging.getLogger(__name__)

WM_HOTKEY = 0x0312
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008

HOTKEY_TOGGLE_VISIBILITY = 1
HOTKEY_QUICK_COPY = 2


@dataclass(frozen=True)
class HotkeySpec:
    hotkey_id: int
    name: str
    modifiers: int
    virtual_key: int

    def label(self, language: str = "de") -> str:
        mapping = {
            "de": {
                MOD_CONTROL: "Strg",
                MOD_ALT: "Alt",
                MOD_SHIFT: "Umschalt",
                MOD_WIN: "Win",
            },
            "en": {
                MOD_CONTROL: "Ctrl",
                MOD_ALT: "Alt",
                MOD_SHIFT: "Shift",
                MOD_WIN: "Win",
            },
        }
        parts = [
            text
            for flag, text in mapping.get(language, {}).items()
            if self.modifiers & flag
        ]
        parts.append(chr(self.virtual_key).upper())
        return "+".join(parts)


DEFAULT_HOTKEYS: tuple[HotkeySpec, ...] = (
    HotkeySpec(
        hotkey_id=HOTKEY_TOGGLE_VISIBILITY,
        name="toggle_visibility",
        modifiers=MOD_CONTROL | MOD_ALT | MOD_SHIFT,
        virtual_key=ord("P"),
    ),
    HotkeySpec(
        hotkey_id=HOTKEY_QUICK_COPY,
        name="quick_copy",
        modifiers=MOD_CONTROL | MOD_ALT | MOD_SHIFT,
        virtual_key=ord("C"),
    ),
)


class HotkeyBackend:
    supported = False

    def register(self, spec: HotkeySpec) -> bool:
        return False

    def unregister_all(self) -> None:
        return None

    def extract_hotkey_id(self, event_type, message) -> Optional[int]:
        return None


class DisabledHotkeyBackend(HotkeyBackend):
    supported = False


class WindowsHotkeyBackend(HotkeyBackend):
    supported = True

    def __init__(self) -> None:
        self._user32 = ctypes.WinDLL("user32", use_last_error=True)
        self._registered_ids: set[int] = set()

    def register(self, spec: HotkeySpec) -> bool:
        if self._user32.RegisterHotKey(None, spec.hotkey_id, spec.modifiers, spec.virtual_key):
            self._registered_ids.add(spec.hotkey_id)
            return True
        error = ctypes.get_last_error()
        logger.warning(
            "Hotkey %s konnte nicht registriert werden (id=%s, error=%s)",
            spec.name,
            spec.hotkey_id,
            error,
        )
        return False

    def unregister_all(self) -> None:
        for hotkey_id in list(self._registered_ids):
            if not self._user32.UnregisterHotKey(None, hotkey_id):
                error = ctypes.get_last_error()
                logger.warning(
                    "Hotkey-ID %s konnte nicht abgemeldet werden (error=%s)",
                    hotkey_id,
                    error,
                )
            self._registered_ids.discard(hotkey_id)

    def extract_hotkey_id(self, event_type, message) -> Optional[int]:
        event_name = event_type.decode() if isinstance(event_type, (bytes, bytearray)) else str(event_type)
        if event_name not in {"windows_generic_MSG", "windows_dispatcher_MSG"}:
            return None

        msg = ctypes.wintypes.MSG.from_address(int(message))
        if msg.message != WM_HOTKEY:
            return None
        return int(msg.wParam)


def create_hotkey_backend() -> HotkeyBackend:
    if sys.platform == "win32":
        return WindowsHotkeyBackend()
    return DisabledHotkeyBackend()


class PromptBoardHotkeys(QtCore.QAbstractNativeEventFilter):
    def __init__(
        self,
        on_toggle_visibility: Callable[[], None],
        on_quick_copy: Callable[[], None],
        backend: Optional[HotkeyBackend] = None,
    ) -> None:
        super().__init__()
        self._backend = backend or create_hotkey_backend()
        self._callbacks = {
            HOTKEY_TOGGLE_VISIBILITY: on_toggle_visibility,
            HOTKEY_QUICK_COPY: on_quick_copy,
        }
        self._started = False
        self._registered_ids: set[int] = set()
        self._app: Optional[QtCore.QCoreApplication] = None

    @property
    def supported(self) -> bool:
        return bool(self._backend.supported)

    @property
    def registered(self) -> bool:
        return len(self._registered_ids) == len(self.hotkeys) and bool(self._registered_ids)

    @property
    def hotkeys(self) -> tuple[HotkeySpec, ...]:
        return DEFAULT_HOTKEYS

    def start(self, app: QtCore.QCoreApplication) -> bool:
        if self._started:
            return self.registered
        self._started = True
        self._app = app
        if self.supported:
            app.installNativeEventFilter(self)
            for spec in self.hotkeys:
                if self._backend.register(spec):
                    self._registered_ids.add(spec.hotkey_id)
        return self.registered

    def stop(self) -> None:
        if self._app is not None and self.supported:
            self._app.removeNativeEventFilter(self)
        self._backend.unregister_all()
        self._registered_ids.clear()
        self._started = False
        self._app = None

    def nativeEventFilter(self, eventType, message):  # type: ignore[override]
        hotkey_id = self._backend.extract_hotkey_id(eventType, message)
        if hotkey_id is None:
            return False
        callback = self._callbacks.get(hotkey_id)
        if callback is None:
            return False
        # BUGSWEEP-38: callback() in try/except — eine ungefangene Exception (z.B. Storage-Fehler im
        # quick_copy-Hotkey) propagierte sonst durch Qts nativen C++-Event-Dispatch und kann je nach
        # PySide6-Abort-Verhalten die App terminieren statt nur den Hotkey zu schlucken.
        try:
            callback()
        except Exception:
            logger.exception("Hotkey-Callback fehlgeschlagen (id=%s)", hotkey_id)
        return True
