"""Theme/palette switching for PromptBoard.

Three modes:
- ``system``: do nothing, let Qt follow the OS default
- ``light``: explicit light palette
- ``dark``: explicit dark palette

Implementation uses ``QPalette`` overrides only — no external theme
packages — so PromptBoard stays a single-dependency app.
"""
from __future__ import annotations

import logging
from typing import Literal

from PySide6 import QtCore, QtGui, QtWidgets

logger = logging.getLogger(__name__)

ThemeMode = Literal["system", "light", "dark"]
VALID_MODES: tuple[ThemeMode, ...] = ("system", "light", "dark")


def _dark_palette() -> QtGui.QPalette:
    palette = QtGui.QPalette()
    role = QtGui.QPalette
    palette.setColor(role.Window, QtGui.QColor(45, 45, 48))
    palette.setColor(role.WindowText, QtGui.QColor(220, 220, 220))
    palette.setColor(role.Base, QtGui.QColor(30, 30, 30))
    palette.setColor(role.AlternateBase, QtGui.QColor(45, 45, 48))
    palette.setColor(role.ToolTipBase, QtGui.QColor(45, 45, 48))
    palette.setColor(role.ToolTipText, QtGui.QColor(220, 220, 220))
    palette.setColor(role.Text, QtGui.QColor(220, 220, 220))
    palette.setColor(role.Button, QtGui.QColor(60, 60, 64))
    palette.setColor(role.ButtonText, QtGui.QColor(220, 220, 220))
    palette.setColor(role.BrightText, QtCore.Qt.red)
    palette.setColor(role.Link, QtGui.QColor(100, 170, 240))
    palette.setColor(role.Highlight, QtGui.QColor(60, 110, 170))
    palette.setColor(role.HighlightedText, QtGui.QColor(255, 255, 255))
    palette.setColor(role.PlaceholderText, QtGui.QColor(140, 140, 140))
    palette.setColor(role.Disabled, role.WindowText, QtGui.QColor(120, 120, 120))
    palette.setColor(role.Disabled, role.Text, QtGui.QColor(120, 120, 120))
    palette.setColor(role.Disabled, role.ButtonText, QtGui.QColor(120, 120, 120))
    return palette


def _light_palette() -> QtGui.QPalette:
    palette = QtGui.QPalette()
    role = QtGui.QPalette
    palette.setColor(role.Window, QtGui.QColor(250, 250, 250))
    palette.setColor(role.WindowText, QtGui.QColor(20, 20, 20))
    palette.setColor(role.Base, QtGui.QColor(255, 255, 255))
    palette.setColor(role.AlternateBase, QtGui.QColor(240, 240, 240))
    palette.setColor(role.ToolTipBase, QtGui.QColor(255, 255, 220))
    palette.setColor(role.ToolTipText, QtGui.QColor(20, 20, 20))
    palette.setColor(role.Text, QtGui.QColor(20, 20, 20))
    palette.setColor(role.Button, QtGui.QColor(240, 240, 240))
    palette.setColor(role.ButtonText, QtGui.QColor(20, 20, 20))
    palette.setColor(role.Highlight, QtGui.QColor(38, 110, 200))
    palette.setColor(role.HighlightedText, QtGui.QColor(255, 255, 255))
    palette.setColor(role.PlaceholderText, QtGui.QColor(140, 140, 140))
    return palette


_SYSTEM_PALETTE_CACHE: QtGui.QPalette | None = None


def apply_theme(app: QtWidgets.QApplication, mode: str) -> None:
    """Apply the named theme to a running QApplication.

    Stores the original system palette on first call so ``system``
    mode can restore it even after switching to light/dark.
    """
    global _SYSTEM_PALETTE_CACHE
    if _SYSTEM_PALETTE_CACHE is None:
        _SYSTEM_PALETTE_CACHE = QtGui.QPalette(app.palette())

    if mode not in VALID_MODES:
        logger.warning("Ungültiger Theme-Modus '%s', verwende 'system'.", mode)
        mode = "system"

    if mode == "dark":
        app.setStyle("Fusion")
        app.setPalette(_dark_palette())
    elif mode == "light":
        app.setStyle("Fusion")
        app.setPalette(_light_palette())
    else:  # system
        app.setPalette(_SYSTEM_PALETTE_CACHE)
    logger.debug("Theme angewendet: %s", mode)
