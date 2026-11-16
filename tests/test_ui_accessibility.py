from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtGui

from models import ItemType, LibraryItem
from promptboard import MainWindow
from settings_manager import SettingsManager
from storage import Storage


def test_menubar_actions_expose_standard_keyboard_shortcuts(qapp, tmp_path):
    storage = Storage(tmp_path)
    settings = SettingsManager()
    window = MainWindow(storage, settings)

    assert window.action_new.shortcut() == QtGui.QKeySequence.StandardKey.New
    assert window.action_quit.shortcut() == QtGui.QKeySequence.StandardKey.Quit
    assert window.action_open_settings.shortcut() == QtGui.QKeySequence.StandardKey.Preferences


def test_find_shortcut_focuses_search_edit(qapp, tmp_path):
    storage = Storage(tmp_path)
    settings = SettingsManager()
    window = MainWindow(storage, settings)
    window.show()
    qapp.processEvents()

    window.search_edit.setText("vorheriger text")
    window.item_list.setFocus()
    qapp.processEvents()
    assert not window.search_edit.hasFocus()

    window.focus_search()
    qapp.processEvents()
    assert window.search_edit.hasFocus()
    assert window.search_edit.selectedText() == "vorheriger text"


def test_search_edit_escape_clears_text_or_focuses_list(qapp, tmp_path):
    storage = Storage(tmp_path)
    settings = SettingsManager()
    window = MainWindow(storage, settings)
    window.show()
    qapp.processEvents()

    window.search_edit.setText("test query")
    window.search_edit.setFocus()
    qapp.processEvents()

    # Erste Betätigung von Escape: Suchtext wird geleert
    escape_ev = QtGui.QKeyEvent(
        QtCore.QEvent.Type.KeyPress,
        QtCore.Qt.Key.Key_Escape,
        QtCore.Qt.KeyboardModifier.NoModifier,
    )
    handled = window.eventFilter(window.search_edit, escape_ev)
    qapp.processEvents()
    assert handled is True
    assert window.search_edit.text() == ""

    # Zweite Betätigung von Escape: Fokus wandert zur Bibliotheksliste
    handled2 = window.eventFilter(window.search_edit, escape_ev)
    qapp.processEvents()
    assert handled2 is True
    assert window.item_list.hasFocus()


def test_search_edit_down_arrow_and_enter_transfers_focus_to_list(qapp, tmp_path):
    storage = Storage(tmp_path)
    item = LibraryItem(
        id="item-1",
        item_type=ItemType.PROMPT,
        name="Suchergebnis",
        content="Inhalt",
    )
    storage.upsert_item(item)
    settings = SettingsManager()
    window = MainWindow(storage, settings)
    window.show()
    qapp.processEvents()

    window.search_edit.setText("Such")
    window.search_edit.setFocus()
    qapp.processEvents()

    down_ev = QtGui.QKeyEvent(
        QtCore.QEvent.Type.KeyPress,
        QtCore.Qt.Key.Key_Down,
        QtCore.Qt.KeyboardModifier.NoModifier,
    )
    handled = window.eventFilter(window.search_edit, down_ev)
    qapp.processEvents()
    assert handled is True
    assert window.item_list.hasFocus()
    assert window.item_list.currentRow() == 0


def test_item_list_enter_key_triggers_copy(qapp, tmp_path, monkeypatch):
    storage = Storage(tmp_path)
    item = LibraryItem(
        id="item-copy",
        item_type=ItemType.SKILL,
        name="Kopier-Test",
        content="Zu kopierender Inhalt",
    )
    storage.upsert_item(item)
    settings = SettingsManager()
    window = MainWindow(storage, settings)

    copied: list[str] = []
    monkeypatch.setattr(window, "copy_current_item", lambda: copied.append(window.current_item_id))

    window.item_list.setCurrentRow(0)
    enter_ev = QtGui.QKeyEvent(
        QtCore.QEvent.Type.KeyPress,
        QtCore.Qt.Key.Key_Return,
        QtCore.Qt.KeyboardModifier.NoModifier,
    )
    handled = window.eventFilter(window.item_list, enter_ev)
    assert handled is True
    assert copied == [item.id]


def test_item_list_delete_key_triggers_delete(qapp, tmp_path, monkeypatch):
    storage = Storage(tmp_path)
    item = LibraryItem(
        id="item-del",
        item_type=ItemType.AGENT,
        name="Lösch-Test",
        content="Zu löschender Agent",
    )
    storage.upsert_item(item)
    settings = SettingsManager()
    window = MainWindow(storage, settings)

    deleted: list[str] = []
    monkeypatch.setattr(window, "delete_current_item", lambda: deleted.append(window.current_item_id))

    window.item_list.setCurrentRow(0)
    del_ev = QtGui.QKeyEvent(
        QtCore.QEvent.Type.KeyPress,
        QtCore.Qt.Key.Key_Delete,
        QtCore.Qt.KeyboardModifier.NoModifier,
    )
    handled = window.eventFilter(window.item_list, del_ev)
    assert handled is True
    assert deleted == [item.id]


def test_item_list_rich_tooltips_with_preview(qapp, tmp_path):
    storage = Storage(tmp_path)
    item = LibraryItem(
        id="item-rich",
        item_type=ItemType.PROMPT,
        name="Experten-Prompt",
        content="Erste Zeile des Prompts mit vielen nützlichen Hinweisen für Entwickler.\nZweite Zeile.",
        category="DevOps",
        tags=["python", "git"],
    )
    storage.upsert_item(item)
    settings = SettingsManager()
    window = MainWindow(storage, settings)

    assert window.item_list.count() == 1
    widget_item = window.item_list.item(0)
    tooltip = widget_item.toolTip()

    assert f"{item.name} ({item.item_type.value})" in tooltip
    assert "Kategorie: DevOps" in tooltip
    assert "Tags: python, git" in tooltip
    assert "Erste Zeile des Prompts" in tooltip


def test_form_labels_have_explicit_buddy_relationships(qapp, tmp_path):
    storage = Storage(tmp_path)
    settings = SettingsManager()
    window = MainWindow(storage, settings)

    assert window.type_label.buddy() == window.type_combo
    assert window.name_label.buddy() == window.name_edit
    assert window.category_label.buddy() == window.category_edit
    assert window.tags_label.buddy() == window.tags_edit
    assert window.source_label.buddy() == window.source_edit
