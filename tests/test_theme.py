import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Configure offscreen rendering before importing PySide6 widgets.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtGui, QtWidgets

import theme


@pytest.fixture
def qapp():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    yield app


def _palette_window_color(app: QtWidgets.QApplication) -> QtGui.QColor:
    return app.palette().color(QtGui.QPalette.Window)


def test_apply_dark_changes_window_role_to_dark_shade(qapp):
    theme.apply_theme(qapp, "dark")
    color = _palette_window_color(qapp)
    # Dark mode palette uses (45,45,48); accept anything sufficiently dark.
    assert color.lightness() < 80


def test_apply_light_changes_window_role_to_light_shade(qapp):
    theme.apply_theme(qapp, "light")
    color = _palette_window_color(qapp)
    assert color.lightness() > 200


def test_apply_system_restores_cached_palette(qapp):
    # First invocation caches whatever the QApplication currently has.
    theme.apply_theme(qapp, "system")
    baseline = QtGui.QColor(_palette_window_color(qapp))

    theme.apply_theme(qapp, "dark")
    assert _palette_window_color(qapp) != baseline

    theme.apply_theme(qapp, "system")
    assert _palette_window_color(qapp) == baseline


def test_invalid_mode_falls_back_to_system(qapp):
    theme.apply_theme(qapp, "system")
    baseline = QtGui.QColor(_palette_window_color(qapp))
    theme.apply_theme(qapp, "neon")
    assert _palette_window_color(qapp) == baseline
