"""Regression tests for U4: window/tray icon resolution.

The window title bar and the tray icon both load ``PromptBoard.ico`` via
``load_app_icon``. In a frozen PyInstaller build the bundled icon lives under
``sys._MEIPASS``; resolving it from ``__file__`` misses it and Qt falls back to
a generic icon. ``_resource_base`` must be frozen-aware.
"""
from __future__ import annotations

import promptboard


def test_resource_base_uses_project_root_in_source_mode():
    assert promptboard._resource_base() == promptboard.PROJECT_ROOT


def test_icon_paths_point_at_the_skateboard_assets():
    assert promptboard.ICON_PATH.name == "PromptBoard.ico"
    assert promptboard.ICON_FALLBACK_PNG.name == "PromptBoard.png"
    # The canonical skateboard assets must exist in the checkout.
    assert (promptboard.PROJECT_ROOT / "PromptBoard.ico").exists()
    assert (promptboard.PROJECT_ROOT / "PromptBoard.png").exists()


def test_resource_base_uses_meipass_when_frozen(monkeypatch, tmp_path):
    monkeypatch.setattr(promptboard.sys, "frozen", True, raising=False)
    monkeypatch.setattr(promptboard.sys, "_MEIPASS", str(tmp_path), raising=False)
    assert promptboard._resource_base() == tmp_path


def test_resource_base_falls_back_to_executable_dir_without_meipass(monkeypatch, tmp_path):
    exe = tmp_path / "PromptBoard.exe"
    exe.write_bytes(b"")
    monkeypatch.setattr(promptboard.sys, "frozen", True, raising=False)
    monkeypatch.delattr(promptboard.sys, "_MEIPASS", raising=False)
    monkeypatch.setattr(promptboard.sys, "executable", str(exe), raising=False)
    assert promptboard._resource_base() == tmp_path
