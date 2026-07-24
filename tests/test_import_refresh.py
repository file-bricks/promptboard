"""Regression tests for U1: the library auto-refreshes after an import.

Users saw the status line confirm the import but the imported entries only
appeared after reopening. The import methods now refresh the list and return a
success flag; the settings dialog closes on success so the refreshed board is
visible immediately.
"""
from __future__ import annotations

import json

from PySide6 import QtWidgets

from promptboard import MainWindow
from settings_dialog import SettingsDialog
from settings_manager import SettingsManager
from storage import Storage


def _write_profiprompt(data_dir):
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "prompts.json").write_text(
        json.dumps(
            {
                "prompts": [
                    {
                        "id": f"p{i}",
                        "title": f"PROMPT {i}",
                        "purpose": "Test",
                        "versions": [
                            {
                                "version_number": 1,
                                "text": f"Body {i}",
                                "created_at": "2026-01-01T00:00:00Z",
                                "updated_at": "2026-01-02T00:00:00Z",
                            }
                        ],
                        "created_at": "2026-01-01T00:00:00Z",
                        "updated_at": "2026-01-02T00:00:00Z",
                    }
                    for i in range(3)
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (data_dir / "boards.json").write_text(
        json.dumps({"boards": []}), encoding="utf-8"
    )


def _window_with_profiprompt(qapp, tmp_path):
    profi = tmp_path / "profiprompt"
    _write_profiprompt(profi)
    settings = SettingsManager()
    settings.qs.setValue("paths/data", str(tmp_path / "library"))
    settings.qs.setValue("imports/profiprompt_data", str(profi))
    settings.qs.sync()
    storage = Storage(tmp_path / "library")
    return MainWindow(storage, settings)


def test_import_profiprompt_auto_refreshes_and_returns_true(qapp, tmp_path):
    window = _window_with_profiprompt(qapp, tmp_path)
    try:
        assert window.item_list.count() == 0
        result = window.import_profiprompt_library()
        assert result is True
        assert window.item_list.count() >= 3  # list refreshed immediately
    finally:
        window.close()


def test_import_profiprompt_returns_false_without_data(qapp, tmp_path, monkeypatch):
    empty = tmp_path / "empty"
    empty.mkdir()
    settings = SettingsManager()
    settings.qs.setValue("paths/data", str(tmp_path / "library"))
    settings.qs.setValue("imports/profiprompt_data", str(empty))
    settings.qs.sync()
    storage = Storage(tmp_path / "library")
    window = MainWindow(storage, settings)
    try:
        monkeypatch.setattr(
            QtWidgets.QMessageBox, "warning", staticmethod(lambda *a, **k: None)
        )
        assert window.import_profiprompt_library() is False
    finally:
        window.close()


def test_settings_dialog_closes_on_successful_import(qapp, tmp_path):
    settings = SettingsManager()
    settings.qs.setValue("paths/data", str(tmp_path / "library"))
    settings.qs.sync()
    accepted: list[bool] = []
    dialog = SettingsDialog(settings, on_import_profiprompt=lambda: True)
    try:
        dialog.accept = lambda: accepted.append(True)  # type: ignore[method-assign]
        dialog._run_import_profiprompt()
        assert accepted == [True]
    finally:
        dialog.close()


def test_settings_dialog_stays_open_on_failed_import(qapp, tmp_path):
    settings = SettingsManager()
    settings.qs.setValue("paths/data", str(tmp_path / "library"))
    settings.qs.sync()
    accepted: list[bool] = []
    dialog = SettingsDialog(settings, on_import_profiprompt=lambda: False)
    try:
        dialog.accept = lambda: accepted.append(True)  # type: ignore[method-assign]
        dialog._run_import_profiprompt()
        assert accepted == []
    finally:
        dialog.close()
