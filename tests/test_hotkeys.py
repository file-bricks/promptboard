from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtWidgets

from hotkeys import DEFAULT_HOTKEYS, PromptBoardHotkeys


class FakeBackend:
    supported = True

    def __init__(self) -> None:
        self.registered = []
        self.unregistered = False

    def register(self, spec):
        self.registered.append(spec)
        return True

    def unregister_all(self):
        self.unregistered = True

    def extract_hotkey_id(self, event_type, message):
        if event_type == "dispatch":
            return message
        return None


class FakeApp:
    def __init__(self) -> None:
        self.installed = []
        self.removed = []

    def installNativeEventFilter(self, filter_obj):
        self.installed.append(filter_obj)

    def removeNativeEventFilter(self, filter_obj):
        self.removed.append(filter_obj)


def test_hotkeys_register_and_dispatch_callbacks():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    backend = FakeBackend()
    calls = []
    manager = PromptBoardHotkeys(
        on_toggle_visibility=lambda: calls.append("toggle"),
        on_quick_copy=lambda: calls.append("copy"),
        backend=backend,
    )

    fake_app = FakeApp()
    assert manager.start(fake_app) is True
    assert fake_app.installed == [manager]
    assert backend.registered == list(DEFAULT_HOTKEYS)

    assert manager.nativeEventFilter("dispatch", 2) is True
    assert calls == ["copy"]

    manager.stop()
    assert fake_app.removed == [manager]
    assert backend.unregistered is True


def test_hotkeys_can_be_started_twice_without_crashing():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    backend = FakeBackend()
    manager = PromptBoardHotkeys(
        on_toggle_visibility=lambda: None,
        on_quick_copy=lambda: None,
        backend=backend,
    )

    fake_app = FakeApp()
    assert manager.start(fake_app) is True
    assert manager.start(fake_app) is True
    assert fake_app.installed == [manager]
    assert backend.registered == list(DEFAULT_HOTKEYS)

    manager.stop()
