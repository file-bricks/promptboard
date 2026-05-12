import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtWidgets

from settings_manager import SettingsManager


@pytest.fixture(autouse=True)
def isolated_qsettings(tmp_path, monkeypatch):
    # Force QSettings to a clean per-test directory.
    QtCore.QSettings.setDefaultFormat(QtCore.QSettings.IniFormat)
    QtCore.QSettings.setPath(
        QtCore.QSettings.IniFormat,
        QtCore.QSettings.UserScope,
        str(tmp_path),
    )
    QtCore.QSettings.setPath(
        QtCore.QSettings.IniFormat,
        QtCore.QSettings.SystemScope,
        str(tmp_path),
    )
    # Ensure a QApplication exists for QObject parenting.
    QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    yield


def test_theme_default_is_system_and_persists():
    settings = SettingsManager()
    assert settings.get_theme() == "system"
    settings.set_theme("dark")
    assert SettingsManager().get_theme() == "dark"


def test_theme_invalid_value_resets_to_default():
    settings = SettingsManager()
    settings.set_theme("hotpink")  # invalid -> falls back
    assert settings.get_theme() == "system"


def test_confirm_overwrite_round_trip():
    settings = SettingsManager()
    assert settings.get_confirm_overwrite() is False
    settings.set_confirm_overwrite(True)
    assert SettingsManager().get_confirm_overwrite() is True


def test_explorerpro_path_round_trip(tmp_path):
    settings = SettingsManager()
    default_path = settings.get_explorerpro_data_path()
    assert isinstance(default_path, Path)
    new_path = tmp_path / "explorerpro"
    settings.set_explorerpro_data_path(new_path)
    assert SettingsManager().get_explorerpro_data_path() == new_path


def test_materialize_path_round_trip(tmp_path):
    settings = SettingsManager()
    target = tmp_path / "exports"
    settings.set_materialize_path(target)
    assert SettingsManager().get_materialize_path() == target
