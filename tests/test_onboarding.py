"""Regression tests for U6: one-time first-run onboarding hint."""
from __future__ import annotations

from PySide6 import QtWidgets

from promptboard import MainWindow
from settings_manager import SettingsManager
from storage import Storage


def _window(qapp, tmp_path):
    settings = SettingsManager()
    settings.qs.setValue("paths/data", str(tmp_path / "library"))
    settings.qs.sync()
    storage = Storage(tmp_path / "library")
    return MainWindow(storage, settings)


def test_onboarding_shown_only_once(qapp, tmp_path, monkeypatch):
    calls: list[int] = []
    monkeypatch.setattr(
        QtWidgets.QMessageBox, "information", staticmethod(lambda *a, **k: calls.append(1))
    )
    window = _window(qapp, tmp_path)
    try:
        assert window.maybe_show_onboarding() is True
        assert calls == [1]
        # The flag is now persisted; the hint does not reappear.
        assert window.maybe_show_onboarding() is False
        assert calls == [1]
    finally:
        window.close()


def test_onboarding_flag_persists(qapp, tmp_path, monkeypatch):
    monkeypatch.setattr(
        QtWidgets.QMessageBox, "information", staticmethod(lambda *a, **k: None)
    )
    window = _window(qapp, tmp_path)
    try:
        window.maybe_show_onboarding()
        assert SettingsManager().is_onboarding_shown() is True
    finally:
        window.close()
