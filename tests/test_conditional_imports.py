"""Regression tests for U3: File-menu import entries are conditional.

Import/export entries only appear when the source software is configured —
either auto-detected (its ``prompts.json`` exists) or explicitly enabled.
"""
from __future__ import annotations

from promptboard import MainWindow
from settings_manager import SettingsManager
from storage import Storage


def _settings(qapp, tmp_path):
    settings = SettingsManager()
    settings.qs.setValue("paths/data", str(tmp_path / "library"))
    settings.qs.sync()
    return settings


def _window(settings, tmp_path):
    storage = Storage(tmp_path / "library")
    return MainWindow(storage, settings)


# ---- SettingsManager detection --------------------------------------------

def test_profiprompt_autodetected_when_prompts_json_present(qapp, tmp_path):
    profi = tmp_path / "profi"
    profi.mkdir()
    (profi / "prompts.json").write_text("{}", encoding="utf-8")
    settings = _settings(qapp, tmp_path)
    settings.set_profiprompt_data_path(profi)
    assert settings.is_profiprompt_enabled() is True


def test_profiprompt_not_detected_without_prompts_json(qapp, tmp_path):
    profi = tmp_path / "profi"
    profi.mkdir()
    settings = _settings(qapp, tmp_path)
    settings.set_profiprompt_data_path(profi)
    assert settings.is_profiprompt_enabled() is False


def test_explicit_disable_overrides_detection(qapp, tmp_path):
    profi = tmp_path / "profi"
    profi.mkdir()
    (profi / "prompts.json").write_text("{}", encoding="utf-8")
    settings = _settings(qapp, tmp_path)
    settings.set_profiprompt_data_path(profi)
    settings.set_profiprompt_enabled(False)
    assert settings.is_profiprompt_enabled() is False


# ---- Menu construction -----------------------------------------------------

def test_menu_hides_imports_when_sources_disabled(qapp, tmp_path):
    settings = _settings(qapp, tmp_path)
    settings.set_profiprompt_enabled(False)
    settings.set_explorerpro_enabled(False)
    window = _window(settings, tmp_path)
    try:
        assert window.action_import_profiprompt is None
        assert window.action_import_explorerpro is None
        assert window.action_export_explorerpro is None
        texts = [a.text() for a in window.file_menu.actions() if not a.isSeparator()]
        assert any("Neu" in t or "New" in t for t in texts)
        assert any("Beenden" in t or "Quit" in t for t in texts)
    finally:
        window.close()


def test_menu_shows_profiprompt_only_when_enabled(qapp, tmp_path):
    settings = _settings(qapp, tmp_path)
    settings.set_profiprompt_enabled(True)
    settings.set_explorerpro_enabled(False)
    window = _window(settings, tmp_path)
    try:
        assert window.action_import_profiprompt is not None
        assert window.action_import_explorerpro is None
        assert window.action_export_explorerpro is None
    finally:
        window.close()


def test_menu_shows_explorerpro_import_and_export_when_enabled(qapp, tmp_path):
    settings = _settings(qapp, tmp_path)
    settings.set_profiprompt_enabled(False)
    settings.set_explorerpro_enabled(True)
    window = _window(settings, tmp_path)
    try:
        assert window.action_import_profiprompt is None
        assert window.action_import_explorerpro is not None
        assert window.action_export_explorerpro is not None
    finally:
        window.close()
