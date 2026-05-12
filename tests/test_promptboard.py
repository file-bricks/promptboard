from __future__ import annotations

import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from models import ItemType, LibraryItem
from promptboard import MainWindow


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
