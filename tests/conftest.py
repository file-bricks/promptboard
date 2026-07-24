"""Shared pytest fixtures for PromptBoard.

Central isolation so no test writes into the real user QSettings or the real
user home. PromptBoard persists its settings via ``QSettings`` (IniFormat,
UserScope) and derives data/materialize/log paths from ``Path.home()``; without
this fixture the test run would pollute the developer's real profile.
"""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtWidgets  # noqa: E402


@pytest.fixture(autouse=True)
def isolated_appdata(tmp_path, monkeypatch):
    """Redirect the user home and QSettings storage into a per-test temp dir."""
    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)
    for var in ("HOME", "USERPROFILE"):
        monkeypatch.setenv(var, str(home))
    monkeypatch.setenv("APPDATA", str(home / "AppData" / "Roaming"))
    monkeypatch.setenv("LOCALAPPDATA", str(home / "AppData" / "Local"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / ".config"))

    QtCore.QSettings.setDefaultFormat(QtCore.QSettings.IniFormat)
    QtCore.QSettings.setPath(
        QtCore.QSettings.IniFormat,
        QtCore.QSettings.UserScope,
        str(tmp_path / "qsettings"),
    )
    QtCore.QSettings.setPath(
        QtCore.QSettings.IniFormat,
        QtCore.QSettings.SystemScope,
        str(tmp_path / "qsettings_system"),
    )
    yield


@pytest.fixture
def qapp():
    """A shared QApplication instance for widget-level tests."""
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    yield app
