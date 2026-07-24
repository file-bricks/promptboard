"""Regression tests for U5: tray category -> entry -> copy navigation."""
from __future__ import annotations

from types import SimpleNamespace

from PySide6 import QtWidgets

from models import ItemType, LibraryItem
from promptboard import TRAY_MAX_ITEMS_PER_CATEGORY, MainWindow
from settings_manager import SettingsManager
from storage import Storage


def _window(qapp, tmp_path, items):
    data_dir = tmp_path / "library"
    settings = SettingsManager()
    settings.qs.setValue("paths/data", str(data_dir))
    settings.qs.sync()
    storage = Storage(data_dir)
    if items:
        storage.upsert_many(items)
    return MainWindow(storage, settings)


def _submenus(menu):
    return {
        action.text(): action.menu()
        for action in menu.actions()
        if action.menu() is not None
    }


def test_rebuild_tray_menu_groups_by_category(qapp, tmp_path):
    # LibraryItem uppercases names in __post_init__ (normalize_name).
    items = [
        LibraryItem(id="a", item_type=ItemType.PROMPT, name="Alpha", content="x", category="Arbeit"),
        LibraryItem(id="b", item_type=ItemType.PROMPT, name="Beta", content="y", category="Arbeit"),
        LibraryItem(id="c", item_type=ItemType.SKILL, name="Gamma", content="z", category="Privat"),
        LibraryItem(id="d", item_type=ItemType.PROMPT, name="Delta", content="w", category=""),
    ]
    window = _window(qapp, tmp_path, items)
    try:
        window.tray_menu = QtWidgets.QMenu(window)
        window.rebuild_tray_menu()
        subs = _submenus(window.tray_menu)
        assert "Arbeit" in subs
        assert "Privat" in subs
        assert "Ohne Kategorie" in subs  # empty category is grouped
        arbeit_names = [a.text() for a in subs["Arbeit"].actions() if not a.isSeparator()]
        assert arbeit_names == ["ALPHA", "BETA"]  # sorted by name
        # The entry carries its item id for the copy handler.
        assert subs["Arbeit"].actions()[0].data() == "a"
    finally:
        window.close()


def test_tray_entry_click_copies_item(qapp, tmp_path):
    items = [
        LibraryItem(
            id="copy-me", item_type=ItemType.PROMPT, name="Kopierziel",
            content="Inhalt", category="C",
        )
    ]
    window = _window(qapp, tmp_path, items)
    try:
        copied: list[str] = []
        window.clipboard_service = SimpleNamespace(
            copy_item=lambda item: copied.append(item.id) or True,
            copy_item_markdown=lambda item: False,
        )
        window.copy_item_from_tray("copy-me")
        assert copied == ["copy-me"]
        assert window.last_active_item_id == "copy-me"
    finally:
        window.close()


def test_tray_menu_caps_entries_per_category(qapp, tmp_path):
    items = [
        LibraryItem(
            id=f"n{i}", item_type=ItemType.PROMPT, name=f"Prompt {i:02d}",
            content="x", category="Big",
        )
        for i in range(TRAY_MAX_ITEMS_PER_CATEGORY + 5)
    ]
    window = _window(qapp, tmp_path, items)
    try:
        window.tray_menu = QtWidgets.QMenu(window)
        window.rebuild_tray_menu()
        big = _submenus(window.tray_menu)["Big"]
        entry_actions = [a for a in big.actions() if not a.isSeparator()]
        # 20 capped entries + 1 "more in board" action.
        assert len(entry_actions) == TRAY_MAX_ITEMS_PER_CATEGORY + 1
        assert entry_actions[-1].text() == "… mehr im Board"
    finally:
        window.close()
