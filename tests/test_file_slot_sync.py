"""Stage 3 tests for FileSlotBackend, SyncEngine file mode, and SettingsDialog file UI."""
from __future__ import annotations

import json
from pathlib import Path

from models import ItemType, LibraryItem, item_to_dict, now_iso
from settings_dialog import SettingsDialog
from settings_manager import SettingsManager
from storage import Storage
from sync_backend import (
    FileSlotBackend,
    SyncEngine,
    is_cloud_conflict_filename,
    sanitize_host_slot,
)


def _make_item(item_id: str, name: str, content: str, *, category: str = "Sync") -> LibraryItem:
    ts = now_iso()
    return LibraryItem(
        id=item_id,
        item_type=ItemType.PROMPT,
        name=name,
        content=content,
        category=category,
        tags=["stage3"],
        source="PromptBoard",
        created_at=ts,
        updated_at=ts,
    )


def _make_settings(tmp_path: Path, name: str, sync_dir: Path, host_slot: str) -> SettingsManager:
    settings = SettingsManager()
    settings.qs.clear()
    settings.qs.setValue("paths/data", str(tmp_path / name))
    settings.set_sync_mode("file")
    settings.set_sync_file_dir(sync_dir)
    settings.set_sync_file_host_slot(host_slot)
    return settings


def test_cloud_conflict_filename_filter_and_host_sanitization():
    assert sanitize_host_slot("  My Host / 01  ") == "My-Host-01"
    assert sanitize_host_slot("///") == "LOCAL"

    assert is_cloud_conflict_filename("promptboard@PC1.json", expected_host="PC1") is False
    assert is_cloud_conflict_filename("profiprompt@MAC.json", expected_host="MAC") is False
    assert is_cloud_conflict_filename("profiprompt-browser@EDGE.json", expected_host="EDGE") is False

    # A7 conflict copies & temporary files must be ignored
    assert is_cloud_conflict_filename("promptboard@PC1-LAPTOP.json", expected_host="PC1") is True
    assert is_cloud_conflict_filename("promptboard@PC1 (conflicted copy).json") is True
    assert is_cloud_conflict_filename("promptboard@PC1.sync-conflict-20261126.json") is True
    assert is_cloud_conflict_filename("promptboard@PC1 (1).json") is True
    assert is_cloud_conflict_filename(".promptboard@PC1.tmp") is True
    assert is_cloud_conflict_filename("notes.txt") is True


def test_two_hosts_single_writer_sync_and_conflict_copy_ignored(tmp_path):
    sync_dir = tmp_path / "cloud_sync"
    sync_dir.mkdir()

    # Host A creates item A1 and syncs to its own slot
    settings_a = _make_settings(tmp_path, "host_a_data", sync_dir, "HOST-A")
    storage_a = Storage(settings_a.get_data_path())
    storage_a.save_items([_make_item("id-a1", "ALPHA", "Content from Host A")])
    engine_a = SyncEngine(storage_a, settings_a)

    conn = engine_a.test_connection()
    assert conn.ok is True
    res_a = engine_a.sync_once()
    assert res_a.ok is True
    assert res_a.mode == "file"
    assert res_a.pushed_count == 1

    slot_a_path = sync_dir / "promptboard" / "HOST-A" / "promptboard@HOST-A.json"
    assert slot_a_path.is_file()
    slot_a_doc = json.loads(slot_a_path.read_text(encoding="utf-8"))
    assert slot_a_doc["manifest"]["app"] == "promptboard"
    assert slot_a_doc["manifest"]["host"] == "HOST-A"
    assert slot_a_doc["manifest"]["item_count"] == 1
    assert len(slot_a_doc["items"]) == 1

    # Drop a simulated OneDrive conflict copy in HOST-A folder — must be ignored
    conflict_copy = sync_dir / "promptboard" / "HOST-A" / "promptboard@HOST-A-OTHERPC.json"
    conflict_copy.write_text(
        json.dumps({"items": [item_to_dict(_make_item("id-ghost", "GHOST", "Must not load"))]}),
        encoding="utf-8",
    )

    # Host B has item B1 and syncs -> pulls A1, ignores conflict copy, never modifies HOST-A's file
    settings_b = _make_settings(tmp_path, "host_b_data", sync_dir, "HOST-B")
    storage_b = Storage(settings_b.get_data_path())
    storage_b.save_items([_make_item("id-b1", "BETA", "Content from Host B")])
    engine_b = SyncEngine(storage_b, settings_b)

    discovered = engine_b.discover_file_slots()
    assert len(discovered) == 1
    assert discovered[0].slot_key == "promptboard:host-a"
    assert discovered[0].item_count == 1

    mtime_a_before = slot_a_path.stat().st_mtime_ns
    res_b = engine_b.sync_once()
    assert res_b.ok is True
    assert res_b.pulled_upserts == 1
    assert res_b.storage_changed is True
    assert slot_a_path.stat().st_mtime_ns == mtime_a_before

    ids_b = {it.id for it in storage_b.load_items()}
    assert ids_b == {"id-a1", "id-b1"}
    assert "id-ghost" not in ids_b

    slot_b_path = sync_dir / "promptboard" / "HOST-B" / "promptboard@HOST-B.json"
    assert slot_b_path.is_file()


def test_file_slot_import_modes_never_once_and_deleted_blocklist(tmp_path):
    sync_dir = tmp_path / "cloud_sync"
    # Pre-populate two foreign PromptBoard slots
    slot_never = sync_dir / "promptboard" / "PEER-NEVER" / "promptboard@PEER-NEVER.json"
    slot_never.parent.mkdir(parents=True)
    slot_never.write_text(
        json.dumps({"items": [item_to_dict(_make_item("n1", "NEVER ITEM", "Ignored"))]}),
        encoding="utf-8",
    )
    slot_once = sync_dir / "promptboard" / "PEER-ONCE" / "promptboard@PEER-ONCE.json"
    slot_once.parent.mkdir(parents=True)
    slot_once.write_text(
        json.dumps({"items": [item_to_dict(_make_item("o1", "ONCE ITEM", "Initial"))]}),
        encoding="utf-8",
    )

    settings = _make_settings(tmp_path, "local_data", sync_dir, "MY-HOST")
    settings.set_sync_file_slot_mode("promptboard:peer-never", "never")
    settings.set_sync_file_slot_mode("promptboard:peer-once", "once")
    storage = Storage(settings.get_data_path())
    engine = SyncEngine(storage, settings)

    first = engine.sync_once()
    assert first.ok is True
    assert {it.id for it in storage.load_items()} == {"o1"}

    # Update PEER-ONCE with a second item — must NOT be imported again because mode == "once"
    slot_once.write_text(
        json.dumps(
            {
                "items": [
                    item_to_dict(_make_item("o1", "ONCE ITEM", "Initial")),
                    item_to_dict(_make_item("o2", "SECOND ONCE", "Should stay skipped")),
                ]
            }
        ),
        encoding="utf-8",
    )
    second = engine.sync_once()
    assert second.ok is True
    assert {it.id for it in storage.load_items()} == {"o1"}

    # Delete o1 locally and switch PEER-ONCE to on_start -> o1 must stay deleted (blocklist)
    storage.save_items([])
    engine.enqueue_delete("o1")
    settings.set_sync_file_slot_mode("promptboard:peer-once", "on_start")
    third = engine.sync_once()
    assert third.ok is True
    ids_after_delete = {it.id for it in storage.load_items()}
    assert "o1" not in ids_after_delete
    assert "o2" in ids_after_delete


def test_file_slot_three_way_conflict_and_resolution(tmp_path):
    sync_dir = tmp_path / "cloud_sync"
    peer_path = sync_dir / "promptboard" / "PEER-1" / "promptboard@PEER-1.json"
    peer_path.parent.mkdir(parents=True)
    peer_path.write_text(
        json.dumps({"items": [item_to_dict(_make_item("shared-1", "SHARED", "v1"))]}),
        encoding="utf-8",
    )

    settings = _make_settings(tmp_path, "local_conflict", sync_dir, "MAIN-PC")
    storage = Storage(settings.get_data_path())
    engine = SyncEngine(storage, settings)

    # Initial sync establishes shared baseline
    assert engine.sync_once().ok is True
    assert storage.get_item("shared-1").content == "v1"

    # Both sides diverge concurrently
    local_edited = storage.get_item("shared-1")
    local_edited.content = "Local v2 edit"
    storage.upsert_item(local_edited)
    peer_path.write_text(
        json.dumps({"items": [item_to_dict(_make_item("shared-1", "SHARED", "Peer v2 edit"))]}),
        encoding="utf-8",
    )

    outcome = engine.sync_once()
    assert outcome.ok is True
    assert outcome.conflict_count == 1
    conflicts = engine.get_conflicts()
    assert len(conflicts) == 1
    assert conflicts[0].source == "file"
    # Local content was NOT silently overwritten
    assert storage.get_item("shared-1").content == "Local v2 edit"

    # Resolve with keep_copy -> original gets remote, copy preserves local edit
    copy_item = engine.resolve_conflict("shared-1", "keep_copy")
    assert copy_item is not None
    assert len(engine.get_conflicts()) == 0
    assert storage.get_item("shared-1").content == "Peer v2 edit"
    assert storage.get_item(copy_item.id).content == "Local v2 edit"


def test_file_slot_cross_app_profiprompt_and_browser_readonly_import(tmp_path):
    sync_dir = tmp_path / "cloud_sync"

    pp_slot = sync_dir / "profiprompt" / "WORKSTATION" / "profiprompt@WORKSTATION.json"
    pp_slot.parent.mkdir(parents=True)
    pp_slot.write_text(
        json.dumps(
            {
                "manifest": {"app": "profiprompt", "item_count": 1},
                "prompts": [
                    {
                        "id": "pp-42",
                        "title": "Code Review",
                        "purpose": "Review pull requests",
                        "tags": ["dev"],
                        "versions": [{"id": "v1", "version_number": 1, "text": "Review this diff."}],
                    }
                ],
                "boards": [{"id": "b1", "title": "Engineering", "items": [{"prompt_id": "pp-42"}]}],
            }
        ),
        encoding="utf-8",
    )

    br_slot = sync_dir / "profiprompt-browser" / "EDGE-WORK" / "profiprompt-browser@EDGE-WORK.json"
    br_slot.parent.mkdir(parents=True)
    br_slot.write_text(
        json.dumps(
            {
                "manifest": {"app": "profiprompt-browser", "item_count": 1},
                "prompts": [
                    {
                        "id": "br-7",
                        "title": "Quick Summary",
                        "text": "Summarize in 3 bullets.",
                        "tags": ["browser"],
                    }
                ],
                "boards": [],
            }
        ),
        encoding="utf-8",
    )

    settings = _make_settings(tmp_path, "pb_cross", sync_dir, "ASUS-HOST")
    storage = Storage(settings.get_data_path())
    engine = SyncEngine(storage, settings)

    slots = engine.discover_file_slots()
    apps_found = {s.app for s in slots}
    assert apps_found == {"profiprompt", "profiprompt-browser"}

    pp_mtime = pp_slot.stat().st_mtime_ns
    br_mtime = br_slot.stat().st_mtime_ns
    outcome = engine.sync_once()
    assert outcome.ok is True
    assert outcome.pulled_upserts == 2
    assert pp_slot.stat().st_mtime_ns == pp_mtime
    assert br_slot.stat().st_mtime_ns == br_mtime

    loaded = {it.id: it for it in storage.load_items()}
    assert "profiprompt:prompt:pp-42" in loaded
    assert "profiprompt:prompt:br-7" in loaded
    assert loaded["profiprompt:prompt:pp-42"].category == "Engineering"


def test_settings_dialog_file_mode_ui_and_slot_table(qapp, tmp_path):
    sync_dir = tmp_path / "cloud_sync"
    peer_slot = sync_dir / "promptboard" / "MAC-STUDIO" / "promptboard@MAC-STUDIO.json"
    peer_slot.parent.mkdir(parents=True)
    peer_slot.write_text(
        json.dumps({"items": [item_to_dict(_make_item("m1", "MAC PROMPT", "Hello"))]}),
        encoding="utf-8",
    )

    settings = _make_settings(tmp_path, "ui_data", sync_dir, "LAPTOP-1")
    storage = Storage(settings.get_data_path())
    engine = SyncEngine(storage, settings)

    dlg = SettingsDialog(settings, sync_engine=engine)
    try:
        assert dlg.sync_mode_combo.findData("file") >= 0
        assert dlg.sync_mode_combo.currentData() == "file"
        assert dlg.sync_file_container.isHidden() is False
        assert dlg.sync_server_container.isHidden() is True
        assert dlg.sync_file_slots_table.rowCount() == 1
        assert dlg.sync_file_slots_table.item(0, 0).text() == "MAC-STUDIO"
        assert dlg.run_test_file_connection() is True
        outcome = dlg.run_sync_now()
        assert outcome is not None
        assert outcome.ok is True
        assert len(storage.load_items()) == 1
    finally:
        dlg.close()


def test_file_slot_backend_direct_push_incremental(tmp_path):
    sync_dir = tmp_path / "direct_push"
    backend = FileSlotBackend(sync_dir=sync_dir, host_slot="DIRECT-1")
    status = backend.test_connection()
    assert status.ok is True
    item = _make_item("d1", "DIRECT", "Body")
    backend.write_own_slot([item], deleted_ids=["old-1"])
    doc = json.loads(backend.own_slot_path().read_text(encoding="utf-8"))
    assert doc["manifest"]["deleted_ids"] == ["old-1"]
    assert doc["items"][0]["id"] == "d1"
