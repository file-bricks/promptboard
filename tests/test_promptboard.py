from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6 import QtCore, QtWidgets

from models import ItemType, LibraryItem
from promptboard import MainWindow
from settings_manager import SettingsManager
from storage import Storage


def _make_fake_delete_window(item: LibraryItem, confirm_result: bool):
    events: list[object] = []
    status_messages: list[str] = []

    storage = SimpleNamespace(
        delete_item=lambda item_id: events.append(("delete", item_id))
    )

    return SimpleNamespace(
        current_item_id=item.id,
        storage=storage,
        current_item=lambda: item,
        _confirm_delete_item=lambda current_item: confirm_result,
        reload_list=lambda: events.append("reload"),
        clear_editor=lambda: events.append("clear"),
        status_label=SimpleNamespace(setText=lambda text: status_messages.append(text)),
        events=events,
        status_messages=status_messages,
    )


def test_delete_current_item_requires_confirmation():
    item = LibraryItem(
        id="item-1",
        item_type=ItemType.PROMPT,
        name="Gefährlicher Eintrag",
        content="Inhalt",
    )
    window = _make_fake_delete_window(item, confirm_result=False)

    MainWindow.delete_current_item(window)

    assert window.current_item_id == item.id
    assert window.events == []
    assert window.status_messages == [f"Löschen abgebrochen: {item.name}"]


def test_delete_current_item_deletes_after_confirmation():
    item = LibraryItem(
        id="item-2",
        item_type=ItemType.SKILL,
        name="Sicherer Eintrag",
        content="Inhalt",
    )
    window = _make_fake_delete_window(item, confirm_result=True)

    MainWindow.delete_current_item(window)

    assert window.current_item_id is None
    assert window.events == [("delete", item.id), "reload", "clear"]
    assert window.status_messages == [f"Gelöscht: {item.name}"]


# ---------------------------------------------------------------- integration


@pytest.fixture
def qapp_isolated(tmp_path, monkeypatch):
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
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    yield app


def _write_profiprompt_payload(data_dir: Path) -> None:
    """Tiny ProfiPrompt fixture with three prompts."""
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "prompts.json").write_text(
        json.dumps(
            {
                "prompts": [
                    {
                        "id": f"prompt-{i}",
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
        json.dumps({"boards": []}, ensure_ascii=False), encoding="utf-8"
    )


def test_import_profiprompt_does_not_recurse_or_crash(qapp_isolated, tmp_path):
    """Regression test for the v1.1.0 crash: signal recursion in reload_list.

    Verifies that importing several prompts does not loop the
    currentItemChanged → save_current_item → reload_list chain and
    keeps current_item_id pointing at the latest imported prompt.
    """
    data_dir = tmp_path / "library"
    profi_dir = tmp_path / "profiprompt"
    _write_profiprompt_payload(profi_dir)

    settings = SettingsManager()
    settings.qs.setValue("paths/data", str(data_dir))
    settings.qs.setValue("imports/profiprompt_data", str(profi_dir))
    settings.qs.sync()

    storage = Storage(data_dir)
    window = MainWindow(storage, settings)
    try:
        reload_calls = {"count": 0}
        original_reload = window.reload_list

        def counted_reload():
            reload_calls["count"] += 1
            original_reload()

        window.reload_list = counted_reload  # type: ignore[method-assign]

        window.import_profiprompt_library()

        # The import should trigger reload_list at most a few times
        # (definitely not >100 like an infinite recursion would).
        assert reload_calls["count"] < 10
        # All three prompts should be in the library now.
        assert len(storage.load_items()) >= 3
        # current_item_id is now the latest imported prompt.
        assert window.current_item_id is not None
        assert window.current_item_id.startswith("profiprompt:prompt:")
    finally:
        window.close()
