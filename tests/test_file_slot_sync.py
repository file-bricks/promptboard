"""Stage 3 tests for FileSlotBackend, SyncEngine file mode, and SettingsDialog file UI."""
from __future__ import annotations

import json
import os
from pathlib import Path
from PySide6 import QtCore
import pytest

from models import ItemType, LibraryItem, item_from_dict, item_to_dict, now_iso
from settings_dialog import SettingsDialog
from settings_manager import SettingsManager
from storage import Storage
import sync_backend
from sync_backend import (
    FileSlotBackend,
    SyncEngine,
    SyncTransportError,
    format_coupling_target,
    format_file_coupling_target,
    is_cloud_conflict_filename,
    make_object_key,
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
    settings.qs = QtCore.QSettings(
        str(tmp_path / f"{name}.qsettings.ini"),
        QtCore.QSettings.Format.IniFormat,
    )
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

    # Conflict copies & temporary files must be ignored
    assert is_cloud_conflict_filename("promptboard@PC1-PEER.json", expected_host="PC1") is True
    assert is_cloud_conflict_filename("promptboard@PC1 (conflicted copy).json") is True
    assert is_cloud_conflict_filename("promptboard@PC1_conflict-20261126-120000.json") is True
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

    # Drop a simulated cloud conflict copy in HOST-A folder — must be ignored
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

    pp_slot = sync_dir / "profiprompt" / "PEER-WORKSTATION" / "profiprompt@PEER-WORKSTATION.json"
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

    br_slot = sync_dir / "profiprompt-browser" / "BROWSER-A" / "profiprompt-browser@BROWSER-A.json"
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

    settings = _make_settings(tmp_path, "pb_cross", sync_dir, "HOST-LOCAL")
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
    peer_slot = sync_dir / "promptboard" / "NODE-SYNC" / "promptboard@NODE-SYNC.json"
    peer_slot.parent.mkdir(parents=True)
    peer_slot.write_text(
        json.dumps({"items": [item_to_dict(_make_item("m1", "NODE PROMPT", "Hello"))]}),
        encoding="utf-8",
    )

    settings = _make_settings(tmp_path, "ui_data", sync_dir, "HOST-1")
    storage = Storage(settings.get_data_path())
    engine = SyncEngine(storage, settings)

    dlg = SettingsDialog(settings, sync_engine=engine)
    try:
        assert dlg.sync_mode_combo.findData("file") >= 0
        assert dlg.sync_mode_combo.currentData() == "file"
        assert dlg.sync_file_container.isHidden() is False
        assert dlg.sync_server_container.isHidden() is True
        assert dlg.sync_file_slots_table.rowCount() == 1
        assert dlg.sync_file_slots_table.item(0, 0).text() == "NODE-SYNC"
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


def test_file_slot_symlink_containment_and_own_slot_guard(tmp_path, monkeypatch):
    sync_dir = tmp_path / "cloud_sync"
    sync_dir.mkdir()
    outside_secret = tmp_path / "secret_outside.json"
    outside_secret.write_text(
        json.dumps({"items": [item_to_dict(_make_item("sec-1", "SECRET", "Leak"))]}),
        encoding="utf-8",
    )

    peer_dir = sync_dir / "promptboard" / "PEER-SYM"
    peer_dir.mkdir(parents=True)
    peer_link = peer_dir / "promptboard@PEER-SYM.json"

    symlink_created = False
    try:
        os.symlink(outside_secret, peer_link)
        symlink_created = True
    except OSError:
        # Windows without Developer Mode / elevated symlink privilege: simulate symlink detection via helper hook
        peer_link.write_text(outside_secret.read_text(encoding="utf-8"), encoding="utf-8")
        orig_check = sync_backend._is_symlink_or_junction
        monkeypatch.setattr(
            sync_backend,
            "_is_symlink_or_junction",
            lambda p: True if Path(p).name == "promptboard@PEER-SYM.json" else orig_check(p),
        )

    backend = FileSlotBackend(sync_dir=sync_dir, host_slot="HOST-SAFE")
    assert backend.discover_slots() == []
    pull_res = backend.pull()
    assert pull_res.offline is False
    assert pull_res.upserts == []

    # Own slot symlink/junction protection
    own_dir = backend.own_slot_dir()
    own_dir.mkdir(parents=True, exist_ok=True)
    own_path = backend.own_slot_path()
    outside_target = tmp_path / "outside_write_target.json"
    if symlink_created:
        os.symlink(outside_target, own_path)
    else:
        monkeypatch.setattr(
            sync_backend,
            "_is_symlink_or_junction",
            lambda p: Path(p).name == own_path.name,
        )

    with pytest.raises(SyncTransportError):
        backend.write_own_slot([_make_item("x1", "SAFE", "No escape")])
    assert not outside_target.exists()
    assert backend.test_connection().ok is False
    assert backend.push([], all_items=[_make_item("x1", "SAFE", "No escape")]).queued_offline is True


def test_file_slot_target_switch_persists_active_target_and_isolates_server_snapshot(tmp_path):
    sync_dir = tmp_path / "cloud_sync"
    peer_slot = sync_dir / "promptboard" / "PEER-SW" / "promptboard@PEER-SW.json"
    peer_slot.parent.mkdir(parents=True)
    peer_slot.write_text(
        json.dumps({"items": [item_to_dict(_make_item("shared-1", "SHARED", "Peer version"))]}),
        encoding="utf-8",
    )

    settings = _make_settings(tmp_path, "switch_data", sync_dir, "HOST-SW")
    server_url = "http://127.0.0.1:8765"
    server_target = format_coupling_target(server_url, "promptboard")
    file_target = format_file_coupling_target(str(sync_dir), "HOST-SW")

    settings.set_sync_mode("server")
    settings.set_sync_server_url(server_url)
    settings.set_sync_namespace("promptboard")
    storage = Storage(settings.get_data_path())
    storage.save_items([_make_item("shared-1", "SHARED", "Local edited")])

    engine = SyncEngine(storage, settings)
    srv_state = engine.state_store.load()
    srv_state.mode = "server"
    srv_state.active_target = server_target
    srv_state.coupled_targets = [server_target]
    srv_state.library_rev = 42
    srv_state.item_revs = {make_object_key("item", "shared-1"): 42}
    srv_state.item_hashes = {make_object_key("item", "shared-1"): "old-server-hash"}
    engine.state_store.save(srv_state)

    # Switch to file mode and sync
    settings.set_sync_mode("file")
    outcome = engine.sync_once()
    assert outcome.ok is True
    assert outcome.conflict_count == 1

    post_state = engine.state_store.load()
    assert post_state.mode == "file"
    assert post_state.active_target == file_target
    assert file_target in post_state.coupled_targets
    assert server_target in post_state.target_snapshots
    assert post_state.target_snapshots[server_target]["library_rev"] == 42
    assert post_state.library_rev == 0
    assert post_state.item_revs == {}

    # Conflict resolution pushes cleanly to own file slot because active_target was persisted
    engine.resolve_conflict("shared-1", "keep_local")
    assert engine.get_conflicts() == []
    own_doc = json.loads(
        (sync_dir / "promptboard" / "HOST-SW" / "promptboard@HOST-SW.json").read_text(encoding="utf-8")
    )
    assert own_doc["items"][0]["content"] == "Local edited"


def test_file_slot_size_cap_flat_host_check_and_malformed_item_isolation(tmp_path, monkeypatch):
    sync_dir = tmp_path / "cloud_sync"
    sync_dir.mkdir()

    # 1) Valid structured slot with malformed scalar fields mixed alongside a clean item
    bad_peer = sync_dir / "promptboard" / "PEER-MIXED" / "promptboard@PEER-MIXED.json"
    bad_peer.parent.mkdir(parents=True)
    bad_peer.write_text(
        json.dumps(
            {
                "manifest": {"app": "promptboard", "host": "PEER-MIXED", "item_count": True},
                "items": [
                    {"id": 100, "name": "NUMERIC ID AND CAT", "content": "OK", "category": 456, "source": 789, "tags": {"x": 1}},
                    {"id": ["invalid-list"], "name": "SKIPPED"},
                    item_to_dict(_make_item("good-1", "GOOD", "Still imports")),
                ],
            }
        ),
        encoding="utf-8",
    )

    # Direct item_from_dict regression guard for malformed non-string scalar fields
    coerced = item_from_dict({"id": 77, "name": "TEST", "content": "C", "category": 123, "source": False})
    assert coerced.id == "77"
    assert coerced.category == "123"

    # 2) Flat file whose manifest.host mismatches filename host (unsuffixed conflict copy)
    flat_mismatch = sync_dir / "promptboard@HOST-BADCOPY.json"
    flat_mismatch.write_text(
        json.dumps(
            {
                "manifest": {"app": "promptboard", "host": "HOST"},
                "items": [item_to_dict(_make_item("ghost-flat", "GHOST", "Must skip"))],
            }
        ),
        encoding="utf-8",
    )

    # 3) Oversized file slot exceeding limit
    monkeypatch.setattr(sync_backend, "MAX_SLOT_FILE_BYTES", 512)
    oversized = sync_dir / "promptboard" / "PEER-HUGE" / "promptboard@PEER-HUGE.json"
    oversized.parent.mkdir(parents=True)
    oversized.write_text(
        json.dumps({"items": [item_to_dict(_make_item("huge-1", "HUGE", "X" * 2048))]}),
        encoding="utf-8",
    )

    settings = _make_settings(tmp_path, "mixed_data", sync_dir, "HOST-MAIN")
    storage = Storage(settings.get_data_path())
    engine = SyncEngine(storage, settings)

    discovered = engine.discover_file_slots()
    assert [s.slot_key for s in discovered] == ["promptboard:peer-mixed"]
    assert discovered[0].item_count == 3  # bool manifest item_count=True ignored safely

    outcome = engine.sync_once()
    assert outcome.ok is True
    loaded = {it.id: it for it in storage.load_items()}
    assert "good-1" in loaded
    assert "100" in loaded
    assert loaded["100"].category == "456"
    assert "ghost-flat" not in loaded
    assert "huge-1" not in loaded


def test_file_slot_tombstone_propagation_and_conflict_protection(tmp_path):
    sync_dir = tmp_path / "cloud_sync"
    sync_dir.mkdir()

    settings_a = _make_settings(tmp_path, "host_a", sync_dir, "HOST-A")
    storage_a = Storage(settings_a.get_data_path())
    storage_a.save_items(
        [
            _make_item("del-clean", "DEL CLEAN", "Shared v1"),
            _make_item("del-dirty", "DEL DIRTY", "Shared v1"),
            _make_item("del-take", "DEL TAKE", "Shared v1"),
        ]
    )
    engine_a = SyncEngine(storage_a, settings_a)
    assert engine_a.sync_once().ok is True

    settings_b = _make_settings(tmp_path, "host_b", sync_dir, "HOST-B")
    storage_b = Storage(settings_b.get_data_path())
    engine_b = SyncEngine(storage_b, settings_b)
    assert engine_b.sync_once().pulled_upserts == 3

    # Host A deletes all three items and writes manifest.deleted_ids
    storage_a.save_items([])
    engine_a.enqueue_delete("del-clean")
    engine_a.enqueue_delete("del-dirty")
    engine_a.enqueue_delete("del-take")
    assert engine_a.sync_once().ok is True

    # Host B leaves del-clean untouched, edits del-dirty & del-take locally
    dirty = storage_b.get_item("del-dirty")
    dirty.content = "Important local work on B"
    storage_b.upsert_item(dirty)
    take = storage_b.get_item("del-take")
    take.content = "Disposable edit on B"
    storage_b.upsert_item(take)

    out_b = engine_b.sync_once()
    assert out_b.ok is True
    assert out_b.pulled_tombstones == 1
    assert out_b.conflict_count == 2
    assert storage_b.get_item("del-clean") is None
    assert storage_b.get_item("del-dirty") is not None
    assert all(c.server_deleted is True for c in engine_b.get_conflicts())

    # Keep local on del-dirty, accept remote deletion on del-take
    engine_b.resolve_conflict("del-dirty", "keep_local")
    engine_b.resolve_conflict("del-take", "take_server")
    assert engine_b.get_conflicts() == []
    assert storage_b.get_item("del-take") is None

    # A stale 3rd peer still advertising del-clean must NOT resurrect it after Host B recorded the tombstone
    stale_c = sync_dir / "promptboard" / "HOST-C" / "promptboard@HOST-C.json"
    stale_c.parent.mkdir(parents=True)
    stale_c.write_text(
        json.dumps(
            {
                "manifest": {"app": "promptboard", "host": "HOST-C", "updated_at": "2020-01-01T00:00:00Z"},
                "items": [item_to_dict(_make_item("del-clean", "DEL CLEAN", "Stale ghost"))],
            }
        ),
        encoding="utf-8",
    )

    out_b2 = engine_b.sync_once()
    assert out_b2.ok is True
    assert out_b2.conflict_count == 0
    assert storage_b.get_item("del-dirty") is not None
    assert storage_b.get_item("del-clean") is None
    assert storage_b.get_item("del-take") is None


def test_file_slot_flush_and_sync_do_not_hold_locks_during_push(tmp_path, monkeypatch):
    sync_dir = tmp_path / "cloud_sync"
    settings = _make_settings(tmp_path, "lock_data", sync_dir, "HOST-LOCK")
    storage = Storage(settings.get_data_path())
    storage.save_items([_make_item("l1", "LOCK CHECK", "Body")])
    engine = SyncEngine(storage, settings)

    lock_held_during_push: list[bool] = []
    orig_write = FileSlotBackend.write_own_slot

    def wrapped_write(self, items, *, deleted_ids=None):
        acquired = engine._state_lock.acquire(blocking=False)
        if acquired:
            engine._state_lock.release()
        lock_held_during_push.append(not acquired)
        return orig_write(self, items, deleted_ids=deleted_ids)

    monkeypatch.setattr(FileSlotBackend, "write_own_slot", wrapped_write)
    assert engine.flush_pending().queued_offline is False
    assert lock_held_during_push == [False]
    state = engine.state_store.load()
    assert make_object_key("item", "l1") in state.item_hashes
    assert engine.sync_once().ok is True
    assert lock_held_during_push == [False, False]
