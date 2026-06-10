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

from i18n import set_language
from models import ItemType, LibraryItem
from promptboard import MainWindow, create_tray
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
        item_list=SimpleNamespace(count=lambda: 0),
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


def _make_fake_copy_window(item: LibraryItem):
    events: list[object] = []
    status_messages: list[str] = []

    clipboard_service = SimpleNamespace(
        copy_item=lambda current_item: events.append(("raw", current_item.id)),
        copy_item_markdown=lambda current_item: events.append(("markdown", current_item.id)),
    )

    def _copy_item_markdown(current_item: LibraryItem) -> None:
        events.append(("markdown", current_item.id))
        status_messages.append(f"Als Markdown kopiert: {current_item.name}")

    return SimpleNamespace(
        current_item_id=item.id,
        current_item=lambda: item,
        save_current_item=lambda: events.append("save"),
        clipboard_service=clipboard_service,
        _copy_item_markdown=_copy_item_markdown,
        status_label=SimpleNamespace(setText=lambda text: status_messages.append(text)),
        events=events,
        status_messages=status_messages,
    )


def test_copy_current_item_markdown_uses_markdown_status():
    item = LibraryItem(
        id="item-3",
        item_type=ItemType.WORKFLOW,
        name="Markdown Eintrag",
        content="## Hallo",
    )
    window = _make_fake_copy_window(item)

    MainWindow.copy_current_item_markdown(window)

    assert window.events == ["save", ("markdown", item.id)]
    assert window.status_messages == [f"Als Markdown kopiert: {item.name}"]


def test_copy_item_sets_cancelled_status_when_variable_prompt_is_aborted():
    item = LibraryItem(
        id="item-cancelled",
        item_type=ItemType.PROMPT,
        name="Abbruch",
        content="Hallo {{name}}",
    )
    status_messages: list[str] = []
    window = SimpleNamespace(
        clipboard_service=SimpleNamespace(copy_item=lambda current_item: False),
        status_label=SimpleNamespace(setText=lambda text: status_messages.append(text)),
    )

    MainWindow._copy_item(window, item)

    assert status_messages == ["Kopieren abgebrochen"]


def test_copy_item_markdown_sets_cancelled_status_when_variable_prompt_is_aborted():
    item = LibraryItem(
        id="item-markdown-cancelled",
        item_type=ItemType.SKILL,
        name="Markdown Abbruch",
        content="Hallo {{name}}",
    )
    status_messages: list[str] = []
    window = SimpleNamespace(
        clipboard_service=SimpleNamespace(copy_item_markdown=lambda current_item: False),
        status_label=SimpleNamespace(setText=lambda text: status_messages.append(text)),
    )

    MainWindow._copy_item_markdown(window, item)

    assert status_messages == ["Markdown-Kopie abgebrochen"]


def _select_item_rows(window: MainWindow, item_ids: set[str]) -> None:
    for row in range(window.item_list.count()):
        widget_item = window.item_list.item(row)
        if widget_item.data(QtCore.Qt.UserRole) in item_ids:
            widget_item.setSelected(True)


def test_materialize_current_item_batches_selected_rows(qapp_isolated, tmp_path):
    data_dir = tmp_path / "library"
    export_dir = tmp_path / "exports"

    settings = SettingsManager()
    settings.qs.setValue("paths/data", str(data_dir))
    settings.set_materialize_path(export_dir)
    settings.qs.sync()

    storage = Storage(data_dir)
    first = LibraryItem(
        id="item-a",
        item_type=ItemType.PROMPT,
        name="Erster Prompt",
        content="Alpha",
    )
    second = LibraryItem(
        id="item-b",
        item_type=ItemType.SKILL,
        name="Zweiter Skill",
        content="Beta",
    )
    storage.upsert_many([first, second])

    window = MainWindow(storage, settings)
    try:
        _select_item_rows(window, {first.id, second.id})
        for row in range(window.item_list.count()):
            widget_item = window.item_list.item(row)
            if widget_item.data(QtCore.Qt.UserRole) == first.id:
                window.item_list.setCurrentRow(row)
                break
        window.content_edit.setPlainText("Alpha geändert")

        window.materialize_current_item()

        first_target = export_dir / "ERSTER PROMPT.md"
        second_target = export_dir / "ZWEITER SKILL.md"
        assert first_target.exists()
        assert second_target.exists()
        assert "Alpha geändert" in first_target.read_text(encoding="utf-8")
        assert window.status_label.text().startswith("2 Einträge materialisiert")
        assert str(export_dir) in window.status_label.text()
    finally:
        window.close()


def test_copy_double_clicked_item_flushes_pending_editor_changes(qapp_isolated, tmp_path):
    data_dir = tmp_path / "library"

    settings = SettingsManager()
    settings.qs.setValue("paths/data", str(data_dir))
    settings.qs.sync()

    storage = Storage(data_dir)
    item = LibraryItem(
        id="copy-live-item",
        item_type=ItemType.PROMPT,
        name="Live Copy",
        content="ALT",
    )
    storage.upsert_item(item)

    window = MainWindow(storage, settings)
    try:
        copied: list[str] = []
        window.clipboard_service = SimpleNamespace(
            copy_item=lambda current_item: copied.append(current_item.content) or True,
            copy_item_markdown=lambda current_item: False,
        )

        window.item_list.setCurrentRow(0)
        window.content_edit.setPlainText("NEU")

        widget_item = window.item_list.item(0)
        window.copy_double_clicked_item(widget_item)

        assert copied == ["NEU"]
        assert storage.get_item(item.id).content == "NEU"
    finally:
        window.close()


def test_library_filter_controls_expose_translated_accessible_context(qapp_isolated, tmp_path):
    data_dir = tmp_path / "library"

    settings = SettingsManager()
    settings.qs.setValue("paths/data", str(data_dir))
    settings.qs.sync()

    storage = Storage(data_dir)
    window = MainWindow(storage, settings)
    try:
        # Default (DE)
        assert window.type_filter.accessibleName() == "Typfilter"
        assert window.type_filter.toolTip() == "Bibliothek nach Eintragstyp filtern"
        assert window.sort_combo.accessibleName() == "Sortierung"
        assert window.search_edit.accessibleName() == "Bibliothek durchsuchen"

        assert window.new_button.accessibleName() == "&Neuer Eintrag"
        assert window.new_button.toolTip() == "Erstellt einen neuen Bibliothekseintrag"
        assert window.delete_button.accessibleName() == "Eintrag löschen"
        assert window.delete_button.toolTip() == "Löscht den aktuell ausgewählten Eintrag"
        assert window.copy_button.accessibleName() == "&Kopieren"
        assert window.copy_button.toolTip() == "Kopiert den Inhalt in die Zwischenablage"
        assert window.materialize_button.accessibleName() == "&Materialisieren"
        assert window.materialize_button.toolTip() == "Schreibt den Eintrag als Markdown-Datei"

        assert window.type_combo.accessibleName() == "Typ"
        assert window.type_combo.toolTip() == "Wähle den Typ des Eintrags (z. B. PROMPT, SKILL, AGENT)"
        assert window.name_edit.accessibleName() == "Name"
        assert window.name_edit.toolTip() == "Gib den Namen des Eintrags ein"
        assert window.category_edit.accessibleName() == "Kategorie"
        assert window.category_edit.toolTip() == "Gib eine Kategorie zur Organisation des Eintrags ein"
        assert window.tags_edit.accessibleName() == "Tags"
        assert window.tags_edit.toolTip() == "Gib Tags ein, getrennt durch Kommata"
        assert window.source_edit.accessibleName() == "Quelle"
        assert window.source_edit.toolTip() == "Gib die Herkunft des Eintrags an (z. B. lokal, ProfiPrompt)"
        assert window.content_edit.accessibleName() == "Inhalt"
        assert window.content_edit.toolTip() == "Gib den Textinhalt des Eintrags ein"

        # Switch to English
        set_language("en")
        window.relabel_ui()

        assert window.type_filter.accessibleName() == "Type filter"
        assert window.type_filter.toolTip() == "Filter the library by entry type"
        assert window.sort_combo.accessibleName() == "Sort order"
        assert window.search_edit.accessibleName() == "Search library"
        assert (
            window.search_edit.accessibleDescription()
            == "Search the library by name, content, or category"
        )

        assert window.new_button.accessibleName() == "&New entry"
        assert window.new_button.toolTip() == "Create a new library entry"
        assert window.delete_button.accessibleName() == "Delete entry"
        assert window.delete_button.toolTip() == "Delete the currently selected entry"
        assert window.copy_button.accessibleName() == "&Copy"
        assert window.copy_button.toolTip() == "Copy the content to the clipboard"
        assert window.materialize_button.accessibleName() == "&Materialize"
        assert window.materialize_button.toolTip() == "Write the entry as a Markdown file"

        assert window.type_combo.accessibleName() == "Type"
        assert window.type_combo.toolTip() == "Select the type of the entry (e.g., PROMPT, SKILL, AGENT)"
        assert window.name_edit.accessibleName() == "Name"
        assert window.name_edit.toolTip() == "Enter the name of the entry"
        assert window.category_edit.accessibleName() == "Category"
        assert window.category_edit.toolTip() == "Enter a category to organize the entry"
        assert window.tags_edit.accessibleName() == "Tags"
        assert window.tags_edit.toolTip() == "Enter tags, separated by commas"
        assert window.source_edit.accessibleName() == "Source"
        assert window.source_edit.toolTip() == "Specify the origin of the entry (e.g., local, ProfiPrompt)"
        assert window.content_edit.accessibleName() == "Content"
        assert window.content_edit.toolTip() == "Enter the text content of the entry"
    finally:
        set_language("de")
        window.close()


def test_create_item_uses_type_filter_template(qapp_isolated, tmp_path):
    data_dir = tmp_path / "library"

    settings = SettingsManager()
    settings.qs.setValue("paths/data", str(data_dir))
    settings.qs.sync()

    storage = Storage(data_dir)
    window = MainWindow(storage, settings)
    try:
        window.type_filter.setCurrentText(ItemType.SKILL.value)

        window.create_item()

        [created] = storage.load_items()
        assert created.item_type is ItemType.SKILL
        assert created.name == "NEUER SKILL 1"
        assert created.source == "lokal"
        assert created.content.startswith("Zweck:")
        assert "Ergebnis:" in created.content
    finally:
        window.close()


def test_create_item_uses_editor_type_when_filter_is_all(qapp_isolated, tmp_path):
    data_dir = tmp_path / "library"

    settings = SettingsManager()
    settings.qs.setValue("paths/data", str(data_dir))
    settings.qs.sync()

    storage = Storage(data_dir)
    window = MainWindow(storage, settings)
    try:
        window.type_combo.setCurrentText(ItemType.AGENT.value)

        window.create_item()

        [created] = storage.load_items()
        assert created.item_type is ItemType.AGENT
        assert created.name == "NEUER AGENT 1"
        assert created.content.startswith("Zweck:")
        assert "Werkzeuge:" in created.content
    finally:
        window.close()


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


def test_dirty_flag_prevents_save_without_changes(qapp_isolated, tmp_path):
    """Switching items without editing must not update updated_at."""
    data_dir = tmp_path / "library"
    settings = SettingsManager()
    settings.qs.setValue("paths/data", str(data_dir))
    settings.qs.sync()

    storage = Storage(data_dir)
    item_a = LibraryItem(
        id="item-a", item_type=ItemType.PROMPT, name="Alpha", content="AAA",
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
    )
    item_b = LibraryItem(
        id="item-b", item_type=ItemType.SKILL, name="Beta", content="BBB",
        created_at="2026-01-02T00:00:00+00:00",
        updated_at="2026-01-02T00:00:00+00:00",
    )
    storage.upsert_many([item_a, item_b])

    window = MainWindow(storage, settings)
    try:
        window.item_list.setCurrentRow(0)
        original_a = storage.get_item("item-a")
        original_b = storage.get_item("item-b")

        window.item_list.setCurrentRow(1)
        window.item_list.setCurrentRow(0)

        after_a = storage.get_item("item-a")
        after_b = storage.get_item("item-b")
        assert after_a.updated_at == original_a.updated_at
        assert after_b.updated_at == original_b.updated_at
    finally:
        window.close()


def test_item_switch_does_not_crash_on_dangling_reference(qapp_isolated, tmp_path):
    """Switching between items must not cause RuntimeError from destroyed C++ objects."""
    data_dir = tmp_path / "library"
    settings = SettingsManager()
    settings.qs.setValue("paths/data", str(data_dir))
    settings.qs.sync()

    storage = Storage(data_dir)
    storage.upsert_many([
        LibraryItem(id="x1", item_type=ItemType.PROMPT, name="First", content="C1"),
        LibraryItem(id="x2", item_type=ItemType.SKILL, name="Second", content="C2"),
    ])

    window = MainWindow(storage, settings)
    try:
        window.item_list.setCurrentRow(0)
        first_id = window.current_item_id
        window.content_edit.setPlainText("Modified content")

        window.item_list.setCurrentRow(1)

        second_id = window.current_item_id
        assert second_id != first_id
        saved = storage.get_item(first_id)
        assert saved.content == "Modified content"
    finally:
        window.close()


def test_delete_does_not_blank_surviving_item(qapp_isolated, tmp_path):
    """Deleting one item must not blank the editor for the remaining item."""
    data_dir = tmp_path / "library"
    settings = SettingsManager()
    settings.qs.setValue("paths/data", str(data_dir))
    settings.qs.sync()

    storage = Storage(data_dir)
    storage.upsert_many([
        LibraryItem(id="del-1", item_type=ItemType.PROMPT, name="ToDelete", content="Gone"),
        LibraryItem(id="keep-1", item_type=ItemType.SKILL, name="ToKeep", content="Stay"),
    ])

    window = MainWindow(storage, settings)
    try:
        for row in range(window.item_list.count()):
            witem = window.item_list.item(row)
            if witem.data(QtCore.Qt.UserRole) == "del-1":
                window.item_list.setCurrentRow(row)
                break

        window._confirm_delete_item = lambda _item: True
        window.delete_current_item()

        assert len(storage.load_items()) == 1
        surviving = storage.get_item("keep-1")
        assert surviving is not None
        assert surviving.content == "Stay"
        assert window.content_edit.toPlainText() != ""
    finally:
        window.close()


def test_quick_copy_last_used_item_uses_persisted_recent_entry(qapp_isolated, tmp_path):
    data_dir = tmp_path / "library"
    settings = SettingsManager()
    settings.qs.setValue("paths/data", str(data_dir))
    settings.set_last_active_item_id("recent-item")
    settings.qs.sync()

    storage = Storage(data_dir)
    recent = LibraryItem(
        id="recent-item",
        item_type=ItemType.PROMPT,
        name="Letzter Eintrag",
        content="Hallo",
    )
    storage.upsert_item(recent)

    window = MainWindow(storage, settings)
    try:
        copied: list[str] = []
        window.clipboard_service = SimpleNamespace(
            copy_item=lambda current_item: copied.append(current_item.id) or True,
            copy_item_markdown=lambda current_item: False,
        )
        window.current_item_id = None

        window.quick_copy_last_used_item()

        assert copied == ["recent-item"]
        assert window.last_active_item_id == "recent-item"
    finally:
        window.close()


def test_toggle_visibility_from_hotkey_hides_and_shows_window(qapp_isolated, tmp_path):
    data_dir = tmp_path / "library"
    settings = SettingsManager()
    settings.qs.setValue("paths/data", str(data_dir))
    settings.qs.sync()

    storage = Storage(data_dir)
    window = MainWindow(storage, settings)
    try:
        window.show()
        assert window.isVisible()

        window.toggle_visibility_from_hotkey()
        assert not window.isVisible()

        window.toggle_visibility_from_hotkey()
        assert window.isVisible()
    finally:
        window.close()


def test_create_tray_skips_unavailable_system_tray(qapp_isolated, tmp_path, monkeypatch):
    data_dir = tmp_path / "library"
    settings = SettingsManager()
    settings.qs.setValue("paths/data", str(data_dir))
    settings.qs.sync()

    storage = Storage(data_dir)
    window = MainWindow(storage, settings)
    try:
        monkeypatch.setattr(
            QtWidgets.QSystemTrayIcon,
            "isSystemTrayAvailable",
            staticmethod(lambda: False),
        )

        tray = create_tray(window)

        assert tray is None
        assert window.tray_icon is None
    finally:
        window.close()


def test_settings_dialog_accessibility_and_live_relabeling(qapp_isolated, tmp_path):
    from src.settings_dialog import SettingsDialog
    data_dir = tmp_path / "library"
    settings = SettingsManager()
    settings.qs.setValue("paths/data", str(data_dir))
    settings.qs.sync()

    dialog = SettingsDialog(settings)
    try:
        # Default German assertions
        assert dialog.windowTitle() == "PromptBoard – Einstellungen"
        assert dialog.paths_group.title() == "Pfade"
        assert dialog.io_group.title() == "Import / Export"
        assert dialog.view_group.title() == "Ansicht"
        assert dialog.info_group.title() == "Info"

        assert dialog.materialize_path_edit.accessibleName() == "Materialisierung"
        assert dialog.materialize_path_edit.toolTip() == "Pfad, in den Markdown-Dateien geschrieben werden"
        assert dialog.change_materialize_button.accessibleName() == "Materialisierungspfad ändern"

        assert dialog.theme_combo.accessibleName() == "Farbschema"
        assert dialog.theme_combo.toolTip() == "Wähle das Farbschema"

        # Change language dynamically to English
        idx = dialog.language_combo.findData("en")
        assert idx >= 0
        dialog.language_combo.setCurrentIndex(idx)

        # Check English assertions after dynamic relabel
        assert dialog.windowTitle() == "PromptBoard — Settings"
        assert dialog.paths_group.title() == "Paths"
        assert dialog.io_group.title() == "Import / Export"
        assert dialog.view_group.title() == "Appearance"
        assert dialog.info_group.title() == "Info"

        assert dialog.materialize_path_edit.accessibleName() == "Materialization"
        assert dialog.materialize_path_edit.toolTip() == "Path where Markdown files are written"
        assert dialog.change_materialize_button.accessibleName() == "Change materialize path"

        assert dialog.theme_combo.accessibleName() == "Color theme"
        assert dialog.theme_combo.toolTip() == "Select the color theme"
    finally:
        set_language("de")
        dialog.close()


# --- Regression: Bug #1 — QMessageBox.StandardButton.Yes/No ---

def test_confirm_delete_uses_standard_button_enum():
    """Bug #1: QMessageBox.Yes/No deprecated in PySide6 6.4+; must use StandardButton."""
    import inspect
    import promptboard as pb_module
    src = inspect.getsource(pb_module.MainWindow._confirm_delete_item)
    assert "StandardButton.Yes" in src, "_confirm_delete_item muss StandardButton.Yes nutzen"
    assert "StandardButton.No" in src, "_confirm_delete_item muss StandardButton.No nutzen"
    assert "QMessageBox.Yes |" not in src, "_confirm_delete_item darf kein veraltetes QMessageBox.Yes| nutzen"


def test_materialize_overwrite_dialog_uses_standard_button_enum():
    """Bug #1 (2. Stelle): _materialize_items muss StandardButton.Yes/No nutzen."""
    import inspect
    import promptboard as pb_module
    src = inspect.getsource(pb_module.MainWindow._materialize_items)
    assert "StandardButton.Yes" in src, "_materialize_items muss StandardButton.Yes nutzen"
    assert "StandardButton.No" in src, "_materialize_items muss StandardButton.No nutzen"


# --- Regression: Bug #2 — QMenu parent in create_tray ---

def test_create_tray_menu_has_window_as_parent():
    """Bug #2: QMenu in create_tray ohne Parent wird nach Funktionsrückkehr GC'd.
    Qt's setContextMenu() übernimmt keine Ownership — Menu braucht einen Python-Parent.
    """
    import inspect
    import promptboard as pb_module
    src = inspect.getsource(pb_module.create_tray)
    assert "QtWidgets.QMenu(window)" in src, (
        "create_tray muss QMenu(window) erstellen, nicht QMenu() ohne Parent"
    )


# --- Regression: Bug #3 — i18n copy-paste: Spanish tooltip nicht übersetzt ---

def test_explorerpro_change_tooltip_spanish_is_not_english():
    """Bug #3: 'settings.btn.change.explorerpro.tooltip' enthielt englischen Text im
    Spanisch-Slot ('Change ExplorerPro path' statt 'Cambiar ruta de ExplorerPro').
    """
    from i18n import tr
    spanish = tr("settings.btn.change.explorerpro.tooltip", lang="es")
    english = tr("settings.btn.change.explorerpro.tooltip", lang="en")
    assert spanish != english, (
        "Spanische Übersetzung darf nicht mit englischer identisch sein"
    )
    assert "Cambiar" in spanish, (
        f"Spanische Übersetzung erwartet 'Cambiar', bekommen: {spanish!r}"
    )


# --- Regression: Bug #4 — item_templates KeyError bei Nicht-DE/EN-Sprachen ---

def test_get_item_template_fallback_for_unsupported_languages():
    """Bug #4: get_item_template() wirft KeyError für Sprachen ohne eigenen
    Template-Eintrag (es, zh, ja, ru). Fallback auf DEFAULT_LANGUAGE nötig.
    """
    from item_templates import get_item_template
    from models import ItemType
    for lang in ("es", "zh", "ja", "ru"):
        for item_type in ItemType:
            try:
                tmpl = get_item_template(item_type, language=lang)
            except KeyError as exc:
                raise AssertionError(
                    f"get_item_template({item_type!r}, lang={lang!r}) wirft KeyError: {exc}"
                )
            assert tmpl is not None, (
                f"get_item_template({item_type!r}, lang={lang!r}) gab None zurück"
            )


# --- Regression: Bug #5 — profiprompt_adapter._load_json_object fängt kein OSError ---

# --- Regression: Bug #6 — QSystemTrayIcon deprecated enum access ---

def test_announce_status_uses_message_icon_enum():
    """Bug #6: _announce_status nutzte QSystemTrayIcon.Information statt
    QSystemTrayIcon.MessageIcon.Information (deprecated in PySide6 6.4+).
    """
    import inspect
    import promptboard as pb_module
    src = inspect.getsource(pb_module.MainWindow._announce_status)
    assert "QSystemTrayIcon.Information" not in src, (
        "_announce_status darf nicht QSystemTrayIcon.Information nutzen"
    )
    assert "MessageIcon.Information" in src, (
        "_announce_status muss MessageIcon.Information nutzen"
    )


def test_create_tray_uses_activation_reason_enum():
    """Bug #6: create_tray nutzte QSystemTrayIcon.Trigger statt
    QSystemTrayIcon.ActivationReason.Trigger (deprecated in PySide6 6.4+).
    """
    import inspect
    import promptboard as pb_module
    src = inspect.getsource(pb_module.create_tray)
    assert "ActivationReason.Trigger" in src, (
        "create_tray muss QSystemTrayIcon.ActivationReason.Trigger nutzen"
    )


def test_profiprompt_load_json_object_handles_os_error(tmp_path):
    """Bug #5: _load_json_object fing nur JSONDecodeError, nicht OSError.
    Auf Windows/OneDrive-Lockings würde ein OSError unbehandelt durch landen.
    """
    import sys
    sys.path.insert(0, str(tmp_path.parent.parent / "src"))
    from profiprompt_adapter import _load_json_object
    locked_path = tmp_path / "unreadable.json"
    locked_path.write_text("{}", encoding="utf-8")
    if hasattr(locked_path, "chmod"):
        try:
            locked_path.chmod(0o000)
            result = _load_json_object(locked_path)
            assert result == {}, "Soll {} zurückgeben statt Exception bei OS-Fehler"
        except PermissionError:
            pass  # Windows: chmod funktioniert nicht immer aus Tests
        finally:
            try:
                locked_path.chmod(0o644)
            except Exception:
                pass
