"""Unit, UI-headless, and end-to-end tests for Stage 1b server synchronization."""
from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import sys
import threading
from typing import Any, Dict, List, Optional, Tuple
from urllib import error as urllib_error

import pytest

from i18n import set_language
from models import ItemType, LibraryItem
from profiprompt_adapter import load_profiprompt_export_payload
from promptboard import MainWindow
from settings_dialog import ConflictResolutionDialog, FirstCouplingDialog, SettingsDialog
from settings_manager import SettingsManager
from storage import Storage
from sync_backend import (
     FileSlotBackend,
     NullBackend,
     OfflineQueue,
     ServerBackend,
     SyncAuthError,
     SyncEngine,
     SyncTransportError,
     TokenStorage,
     create_sync_backend,
     make_object_key,
     validate_namespace,
     validate_server_url,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _load_real_server_classes():
    """Import ``prompt_sync_server`` from sibling checkout if not installed in site-packages."""
    candidates = []
    env_override = os.environ.get("PROMPT_SYNC_SERVER_PATH", "").strip()
    if env_override:
        candidates.append(Path(env_override))
    candidates.extend(
        [
            PROJECT_ROOT.parent / "prompt-sync-server",
            PROJECT_ROOT.parent.parent / "repos" / "prompt-sync-server",
        ]
    )
    for candidate in candidates:
        if (candidate / "prompt_sync_server" / "server.py").is_file():
            cand_str = str(candidate)
            if cand_str not in sys.path:
                sys.path.insert(0, cand_str)
            break

    pss_server = pytest.importorskip("prompt_sync_server.server")
    return pss_server.PromptSyncHTTPServer


@pytest.fixture
def live_sync_server(tmp_path):
    """Run the real ``prompt-sync-server`` in-process on ``127.0.0.1:0``."""
    PromptSyncHTTPServer = _load_real_server_classes()
    server_dir = tmp_path / "sync_server_data"
    srv = PromptSyncHTTPServer(
        bind="127.0.0.1",
        port=0,
        data_dir=server_dir,
        connection_timeout=5.0,
    )
    token, _record = srv.token_store.create_token(label="test-suite")
    ro_token, _ro_rec = srv.token_store.create_token(label="readonly-suite", read_only=True)
    thread = threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True)
    thread.start()
    try:
        yield {
            "server": srv,
            "base_url": srv.base_url,
            "token": token,
            "readonly_token": ro_token,
            "data_dir": server_dir,
        }
    finally:
        srv.shutdown()
        srv.server_close()
        thread.join(timeout=3.0)


def _make_settings_and_storage(
    root: Path,
    *,
    mode: str = "off",
    server_url: str = "",
    token: str = "",
    namespace: str = "promptboard",
) -> Tuple[SettingsManager, Storage]:
    data_dir = root / "data"
    token_file = root / "profile" / "sync_token.json"
    settings = SettingsManager()
    settings._cached_token_storage = TokenStorage(fallback_path=token_file)
    settings.qs.setValue("paths/data", str(data_dir))
    settings.set_sync_mode(mode)
    settings.set_sync_server_url(server_url)
    settings.set_sync_namespace(namespace)
    settings.set_sync_token(token)
    settings.qs.sync()
    storage = Storage(data_dir)
    return settings, storage


# ---------------------------------------------------------------------------
# Mode = off guarantees & transport validation
# ---------------------------------------------------------------------------


def test_mode_off_makes_no_network_calls(qapp, tmp_path, monkeypatch):
    def forbidden_urlopen(*args, **kwargs):
        raise AssertionError("urlopen must never be called when sync mode is off!")

    def forbidden_requester(*args, **kwargs):
        raise AssertionError("HTTP requester must never be called when sync mode is off!")

    monkeypatch.setattr("urllib.request.OpenerDirector.open", forbidden_urlopen)

    # Even if server URL and token are populated, mode="off" must remain strictly offline.
    settings, storage = _make_settings_and_storage(
        tmp_path,
        mode="off",
        server_url="http://127.0.0.1:8765",
        token="pss_example_secret_token",
    )
    assert settings.get_sync_mode() == "off"
    engine = SyncEngine(storage, settings, requester=forbidden_requester)
    assert isinstance(engine.build_backend(), NullBackend)

    window = MainWindow(storage, settings, sync_engine=engine)
    try:
        window.register_quit_hook(qapp)
        assert window.sync_on_start() is None
        window.create_item()
        window.content_edit.setPlainText("Strictly offline edit")
        window.save_current_item()
        assert not window.sync_debounce_timer.isActive()
        assert not window.sync_interval_timer.isActive()

        outcome = window.run_sync(interactive=False)
        assert outcome.ok is True
        assert outcome.mode == "off"

        status = engine.test_connection()
        assert status.ok is False

        window.on_about_to_quit()
        assert not (storage.data_dir / "sync_queue.json").exists()
    finally:
        window.close()


def test_server_url_and_namespace_validation():
    assert validate_server_url("http://127.0.0.1:8765/") == "http://127.0.0.1:8765"
    assert validate_server_url("http://localhost:9000") == "http://localhost:9000"
    assert validate_server_url("http://[::1]:8765") == "http://[::1]:8765"
    assert validate_server_url("http://100.64.10.20:8765") == "http://100.64.10.20:8765"
    assert validate_server_url("https://sync.example.test:8443/") == "https://sync.example.test:8443"

    for invalid in (
        "",
        "ftp://127.0.0.1:8765",
        "http://192.168.1.50:8765",
        "http://10.0.0.5:8765",
        "http://0.0.0.0:8765",
        "http://sync.example.test:8765",
        "https://token:secret@sync.example.test",
    ):
        with pytest.raises(SyncTransportError):
            validate_server_url(invalid)

    assert validate_namespace("") == "promptboard"
    assert validate_namespace("team_alpha-01") == "team_alpha-01"
    with pytest.raises(ValueError):
        validate_namespace("Invalid Uppercase!")


def test_file_slot_backend_stub_ready_for_stage3():
    backend = create_sync_backend("file")
    assert isinstance(backend, FileSlotBackend)
    with pytest.raises(NotImplementedError):
        backend.pull()
    with pytest.raises(NotImplementedError):
        backend.push([])
    with pytest.raises(NotImplementedError):
        backend.test_connection()


# ---------------------------------------------------------------------------
# Token storage (optional keyring + 0600 fallback file)
# ---------------------------------------------------------------------------


def test_token_storage_optional_keyring_and_0600_fallback(tmp_path):
    fallback = tmp_path / "local_profile" / "sync_token.json"

    # 1) Fallback file mode (no keyring)
    store_file = TokenStorage(fallback_path=fallback, keyring_backend=None)
    assert store_file.get_token() == ""
    store_file.set_token("pss_test_token_value")
    assert store_file.get_token() == "pss_test_token_value"
    assert fallback.is_file()
    assert "pss_test_token_value" not in repr(store_file)

    mode_bits = stat.S_IMODE(fallback.stat().st_mode)
    assert mode_bits & stat.S_IRUSR
    if os.name != "nt":
        assert mode_bits == 0o600

    # 2) Optional keyring backend takes precedence and removes plaintext fallback file
    keyring_mem: Dict[Tuple[str, str], str] = {}

    class FakeKeyring:
        def get_password(self, service: str, account: str) -> Optional[str]:
            return keyring_mem.get((service, account))

        def set_password(self, service: str, account: str, secret: str) -> None:
            keyring_mem[(service, account)] = secret

        def delete_password(self, service: str, account: str) -> None:
            keyring_mem.pop((service, account), None)

    store_kr = TokenStorage(fallback_path=fallback, keyring_backend=FakeKeyring())
    store_kr.set_token("pss_keyring_secret")
    assert store_kr.get_token() == "pss_keyring_secret"
    assert not fallback.exists()

    store_kr.clear_token()
    assert store_kr.get_token() == ""


def test_token_is_never_persisted_in_qsettings_ini(tmp_path):
    settings, _storage = _make_settings_and_storage(
        tmp_path,
        mode="server",
        server_url="http://127.0.0.1:8765",
        token="pss_super_secret_do_not_put_in_ini",
    )
    ini_path = Path(settings.qs.fileName())
    if ini_path.is_file():
        ini_text = ini_path.read_text(encoding="utf-8", errors="replace")
        assert "pss_super_secret_do_not_put_in_ini" not in ini_text
    assert settings.get_sync_token() == "pss_super_secret_do_not_put_in_ini"


# ---------------------------------------------------------------------------
# Offline queue compaction & atomic persistence
# ---------------------------------------------------------------------------


def test_offline_queue_compaction_retains_original_base_rev(tmp_path):
    queue = OfflineQueue(tmp_path)
    item_v1 = LibraryItem(id="p1", item_type=ItemType.PROMPT, name="FIRST", content="Draft 1")
    item_v2 = LibraryItem(id="p1", item_type=ItemType.PROMPT, name="FIRST", content="Draft 2")

    # Upsert on rev=3 followed by second edit keeps base_rev=3 and updates payload.
    queue.enqueue_upsert(item_v1, known_base_rev=3)
    queue.enqueue_upsert(item_v2, known_base_rev=99)
    queued = queue.load_all()
    assert len(queued) == 1
    assert queued[0].op == "upsert"
    assert queued[0].base_rev == 3
    assert queued[0].payload["content"] == "Draft 2"

    # Deleting that item compacts to a delete mutation keeping original base_rev=3.
    queue.enqueue_delete("p1", known_base_rev=99)
    queued = queue.load_all()
    assert len(queued) == 1
    assert queued[0].op == "delete"
    assert queued[0].base_rev == 3
    assert queued[0].payload is None

    # Item created offline (base_rev=0) and deleted before sync vanishes completely.
    ephemeral = LibraryItem(id="temp-1", item_type=ItemType.SKILL, name="TEMP", content="X")
    queue.enqueue_upsert(ephemeral, known_base_rev=0)
    assert len(queue.load_all()) == 2
    queue.enqueue_delete("temp-1", known_base_rev=0)
    remaining_ids = [m.id for m in queue.load_all()]
    assert remaining_ids == ["p1"]
    assert list(tmp_path.glob("*.tmp")) == []


def test_offline_queue_preserved_on_network_failure_and_flushed_on_reconnect(tmp_path):
    online = {"up": False}
    pushed_batches: List[Any] = []

    def fake_requester(method: str, url: str, headers: Dict[str, str], body: Optional[bytes], timeout: float):
        if not online["up"]:
            raise urllib_error.URLError("simulated offline")
        if method == "GET" and url.endswith("/changes"):
            return 200, {"etag": '"rev-0"'}, json.dumps(
                {"namespace": "promptboard", "library_rev": 0, "items": [], "tombstones": []}
            ).encode("utf-8")
        if method == "GET" and "/changes?since_rev=" in url:
            return 304, {"etag": '"rev-1"'}, b""
        if method == "POST" and url.endswith("/push"):
            doc = json.loads(body.decode("utf-8"))
            pushed_batches.append(doc)
            return 200, {"etag": '"rev-1"'}, json.dumps(
                {
                    "namespace": "promptboard",
                    "library_rev": 1,
                    "applied": [{"id": m["id"], "kind": m["kind"], "op": m["op"], "rev": 1} for m in doc["mutations"]],
                    "conflicts": [],
                }
            ).encode("utf-8")
        raise AssertionError(f"Unexpected request: {method} {url}")

    settings, storage = _make_settings_and_storage(
        tmp_path,
        mode="server",
        server_url="http://127.0.0.1:8765",
        token="pss_fake_token",
    )
    engine = SyncEngine(storage, settings, requester=fake_requester)

    item = LibraryItem(id="off-1", item_type=ItemType.PROMPT, name="OFFLINE", content="Saved locally")
    storage.upsert_item(item)
    engine.enqueue_upsert(item)

    offline_outcome = engine.sync_once()
    assert offline_outcome.ok is False
    assert offline_outcome.offline is True
    assert engine.get_pending_count() == 1

    # Reconnect: queue flushes automatically
    online["up"] = True
    online_outcome = engine.sync_once()
    assert online_outcome.ok is True
    assert engine.get_pending_count() == 0
    assert len(pushed_batches) == 1
    assert engine.state_store.load().item_revs[make_object_key("item", "off-1")] == 1


# ---------------------------------------------------------------------------
# Settings dialog, headless UI, debounce & idempotent quit guard
# ---------------------------------------------------------------------------


def test_settings_dialog_sync_ui_and_test_connection_button(qapp, tmp_path):
    def fake_requester(method: str, url: str, headers: Dict[str, str], body: Optional[bytes], timeout: float):
        assert headers.get("Authorization") == "Bearer pss_ui_token"
        return 200, {}, json.dumps(
            {
                "namespaces": [
                    {
                        "name": "promptboard",
                        "schema_version": "promptboard-library-v1",
                        "library_rev": 7,
                        "item_count": 3,
                    }
                ]
            }
        ).encode("utf-8")

    settings, storage = _make_settings_and_storage(tmp_path, mode="off")
    engine = SyncEngine(storage, settings, requester=fake_requester)
    dialog = SettingsDialog(settings, sync_engine=engine)
    try:
        assert dialog.sync_server_container.isHidden()
        assert dialog.test_connection_button.text() == "Verbindung testen"

        srv_idx = dialog.sync_mode_combo.findData("server")
        dialog.sync_mode_combo.setCurrentIndex(srv_idx)
        assert not dialog.sync_server_container.isHidden()
        assert settings.get_sync_mode() == "server"

        dialog.sync_url_edit.setText("http://127.0.0.1:8765")
        dialog.sync_token_edit.setText("pss_ui_token")
        dialog.sync_interval_spin.setValue(120)

        assert dialog.run_test_connection() is True
        assert "Rev. 7" in dialog.sync_status_label.text()
        assert settings.get_sync_interval_seconds() == 120

        # Live relabel to English
        en_idx = dialog.language_combo.findData("en")
        dialog.language_combo.setCurrentIndex(en_idx)
        assert dialog.test_connection_button.text() == "Test connection"
    finally:
        set_language("de")
        dialog.close()


def test_quit_hook_idempotent_guard_and_debounce_trigger(qapp, tmp_path):
    push_calls = {"count": 0}

    def fake_requester(method: str, url: str, headers: Dict[str, str], body: Optional[bytes], timeout: float):
        if method == "POST" and url.endswith("/push"):
            push_calls["count"] += 1
            doc = json.loads(body.decode("utf-8"))
            return 200, {"etag": '"rev-1"'}, json.dumps(
                {
                    "namespace": "promptboard",
                    "library_rev": 1,
                    "applied": [{"id": m["id"], "kind": m["kind"], "op": m["op"], "rev": 1} for m in doc["mutations"]],
                    "conflicts": [],
                }
            ).encode("utf-8")
        return 200, {"etag": '"rev-0"'}, json.dumps(
            {"namespace": "promptboard", "library_rev": 0, "items": [], "tombstones": []}
        ).encode("utf-8")

    settings, storage = _make_settings_and_storage(
        tmp_path,
        mode="server",
        server_url="http://127.0.0.1:8765",
        token="pss_quit_token",
    )
    engine = SyncEngine(storage, settings, requester=fake_requester)
    window = MainWindow(storage, settings, sync_engine=engine)
    try:
        # Registering quit hook multiple times only attaches once.
        assert window.register_quit_hook(qapp) is True
        assert window.register_quit_hook(qapp) is False

        window.create_item()
        assert window.sync_debounce_timer.isActive()
        assert engine.get_pending_count() == 1

        # Calling on_about_to_quit twice flushes pending mutations at most once.
        window.on_about_to_quit()
        window.on_about_to_quit()
        assert push_calls["count"] == 1
        assert engine.get_pending_count() == 0
    finally:
        qapp.aboutToQuit.disconnect(window.on_about_to_quit)
        window.close()


# ---------------------------------------------------------------------------
# End-to-end tests against real prompt-sync-server on 127.0.0.1:0
# ---------------------------------------------------------------------------


def test_e2e_first_coupling_dialog_merge_default_and_one_time_behavior(qapp, tmp_path, live_sync_server):
    base_url = live_sync_server["base_url"]
    token = live_sync_server["token"]

    # Seed server via client A
    settings_a, storage_a = _make_settings_and_storage(
        tmp_path / "client_a",
        mode="server",
        server_url=base_url,
        token=token,
    )
    storage_a.upsert_many(
        [
            LibraryItem(id="shared-id", item_type=ItemType.PROMPT, name="SHARED", content="Server version"),
            LibraryItem(id="srv-only", item_type=ItemType.SKILL, name="SERVER SKILL", content="From server"),
        ]
    )
    engine_a = SyncEngine(storage_a, settings_a)
    res_a = engine_a.sync_once()
    assert res_a.ok is True
    assert res_a.pushed_count == 2

    # Client B already has local items: one non-conflicting + one with same ID and different content.
    settings_b, storage_b = _make_settings_and_storage(
        tmp_path / "client_b",
        mode="server",
        server_url=base_url,
        token=token,
    )
    storage_b.upsert_many(
        [
            LibraryItem(id="shared-id", item_type=ItemType.PROMPT, name="SHARED", content="Local version"),
            LibraryItem(id="local-only", item_type=ItemType.AGENT, name="LOCAL AGENT", content="From B"),
        ]
    )
    engine_b = SyncEngine(storage_b, settings_b)

    # Verify FirstCouplingDialog defaults to non-destructive "merge".
    dlg = FirstCouplingDialog(remote_count=2, remote_rev=2)
    try:
        assert dlg.merge_button.isDefault() is True
        dlg.merge_button.click()
        assert dlg.choice == "merge"
    finally:
        dlg.close()

    coupling_prompts: List[Tuple[int, int]] = []

    def record_coupling(count: int, rev: int):
        coupling_prompts.append((count, rev))
        return "merge"

    res_b1 = engine_b.sync_once(on_first_coupling=record_coupling)
    assert res_b1.ok is True
    assert coupling_prompts == [(2, 2)]
    assert res_b1.conflict_count == 1

    # Local version was NOT overwritten; server-only item was added; local-only item was pushed!
    assert storage_b.get_item("shared-id").content == "Local version"
    assert storage_b.get_item("srv-only").content == "From server"
    assert storage_b.get_item("local-only").content == "From B"

    # Subsequent sync must NOT prompt again.
    res_b2 = engine_b.sync_once(on_first_coupling=record_coupling)
    assert res_b2.ok is True
    assert len(coupling_prompts) == 1

    # Client A pulls Client B's local-only item.
    engine_a.sync_once()
    assert storage_a.get_item("local-only") is not None


def test_e2e_push_pull_409_conflict_resolutions_tombstones_and_410(qapp, tmp_path, live_sync_server):
    base_url = live_sync_server["base_url"]
    token = live_sync_server["token"]
    ro_token = live_sync_server["readonly_token"]
    srv = live_sync_server["server"]

    settings_a, storage_a = _make_settings_and_storage(
        tmp_path / "node_a",
        mode="server",
        server_url=base_url,
        token=token,
    )
    settings_b, storage_b = _make_settings_and_storage(
        tmp_path / "node_b",
        mode="server",
        server_url=base_url,
        token=token,
    )
    engine_a = SyncEngine(storage_a, settings_a)
    engine_b = SyncEngine(storage_b, settings_b)

    # 1) Initial push from A -> pull into B -> ETag 304 fast-path on second pull
    p1 = LibraryItem(id="item-1", item_type=ItemType.PROMPT, name="CODE REVIEW", content="v1 canonical")
    storage_a.upsert_item(p1)
    engine_a.enqueue_upsert(p1)
    out_a1 = engine_a.sync_once()
    assert out_a1.ok is True
    assert out_a1.library_rev == 1

    out_b1 = engine_b.sync_once()
    assert out_b1.ok is True
    assert storage_b.get_item("item-1").content == "v1 canonical"

    out_b_noop = engine_b.sync_once()
    assert out_b_noop.ok is True
    assert out_b_noop.pulled_upserts == 0
    assert out_b_noop.storage_changed is False

    # 2) Concurrent edits -> 409 Conflict -> resolve via ConflictResolutionDialog ("keep_copy")
    p1_a2 = LibraryItem(id="item-1", item_type=ItemType.PROMPT, name="CODE REVIEW", content="v2 from A")
    storage_a.upsert_item(p1_a2)
    engine_a.enqueue_upsert(p1_a2)
    assert engine_a.sync_once().ok is True

    p1_b_stale = LibraryItem(id="item-1", item_type=ItemType.PROMPT, name="CODE REVIEW", content="v2 local B")
    storage_b.upsert_item(p1_b_stale)
    engine_b.enqueue_upsert(p1_b_stale)
    out_b_conflict = engine_b.sync_once()
    assert out_b_conflict.conflict_count == 1
    assert storage_b.get_item("item-1").content == "v2 local B"

    conflict_dlg = ConflictResolutionDialog(engine_b)
    try:
        assert conflict_dlg.keep_local_button.isDefault() is True
        assert conflict_dlg.conflict_list.count() == 1
        assert conflict_dlg.apply_resolution("keep_copy") is True
    finally:
        conflict_dlg.close()

    assert engine_b.get_conflicts() == []
    assert storage_b.get_item("item-1").content == "v2 from A"
    b_items = storage_b.load_items()
    assert len(b_items) == 2
    copy_item = next(it for it in b_items if it.id != "item-1")
    assert copy_item.content == "v2 local B"
    assert "KOPIE" in copy_item.name or "COPY" in copy_item.name

    # Pull new copy onto A
    assert engine_a.sync_once().ok is True
    assert storage_a.get_item(copy_item.id) is not None

    # 3) Second 409 conflict resolved with default "keep_local"
    p1_a3 = LibraryItem(id="item-1", item_type=ItemType.PROMPT, name="CODE REVIEW", content="v3 from A")
    storage_a.upsert_item(p1_a3)
    engine_a.enqueue_upsert(p1_a3)
    assert engine_a.sync_once().ok is True

    p1_b3 = LibraryItem(id="item-1", item_type=ItemType.PROMPT, name="CODE REVIEW", content="v3 local B wins")
    storage_b.upsert_item(p1_b3)
    engine_b.enqueue_upsert(p1_b3)
    assert engine_b.sync_once().conflict_count == 1
    engine_b.resolve_conflict("item-1", "keep_local")
    assert engine_b.get_conflicts() == []
    assert engine_a.sync_once().ok is True
    assert storage_a.get_item("item-1").content == "v3 local B wins"

    # 4) Clean tombstone replication vs. locally edited tombstone conflict ("take_server")
    storage_a.delete_item(copy_item.id)
    engine_a.enqueue_delete(copy_item.id)
    assert engine_a.sync_once().ok is True

    assert engine_b.sync_once().ok is True
    assert storage_b.get_item(copy_item.id) is None

    # Delete item-1 on A while B has edited item-1 locally -> conflict instead of silent loss!
    storage_a.delete_item("item-1")
    engine_a.enqueue_delete("item-1")
    assert engine_a.sync_once().ok is True

    p1_b_dirty = LibraryItem(id="item-1", item_type=ItemType.PROMPT, name="CODE REVIEW", content="Unsaved B work")
    storage_b.upsert_item(p1_b_dirty)
    engine_b.enqueue_upsert(p1_b_dirty)
    out_tomb_conflict = engine_b.sync_once()
    assert out_tomb_conflict.conflict_count == 1
    assert engine_b.get_conflicts()[0].server_deleted is True
    assert storage_b.get_item("item-1") is not None

    # Choosing "take_server" accepts the remote deletion cleanly.
    engine_b.resolve_conflict("item-1", "take_server")
    assert storage_b.get_item("item-1") is None
    assert engine_b.get_conflicts() == []

    # 5) 410 Gone cursor compaction recovery
    fresh_item = LibraryItem(id="item-fresh", item_type=ItemType.WORKFLOW, name="FRESH", content="Survived reset")
    storage_a.upsert_item(fresh_item)
    engine_a.enqueue_upsert(fresh_item)
    assert engine_a.sync_once().ok is True

    # Simulate tombstone compaction advancing min_retained_rev past B's stale cursor
    handle = srv.store._get_handle("promptboard", create_if_missing=False)
    with handle.lock:
        handle.conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES ('min_retained_rev', ?);",
            (str(engine_a.get_library_rev()),),
        )
        handle.conn.commit()

    stale_state = engine_b.state_store.load()
    stale_state.library_rev = 1
    engine_b.state_store.save(stale_state)

    out_reset = engine_b.sync_once()
    assert out_reset.ok is True
    assert storage_b.get_item("item-fresh") is not None

    # 6) Read-only token is rejected on push with SyncAuthError (HTTP 403)
    ro_backend = ServerBackend(server_url=base_url, token=ro_token, namespace="promptboard")
    assert ro_backend.test_connection().ok is True
    with pytest.raises(SyncAuthError):
        ro_backend.push(
            [
                OfflineQueue(tmp_path / "ro_q").enqueue_upsert(
                    fresh_item, known_base_rev=0
                )[0]
            ]
        )


def test_profiprompt_export_payload_read_only_mapping():
    export_doc = {
        "schema_version": "profiprompt-library-v1",
        "prompts": [
            {
                "id": "pp-1",
                "title": "Architecture Check",
                "purpose": "Review boundaries",
                "text": "Inspect module coupling.",
                "tags": ["arch"],
                "versions": [],
                "updated_at": "2026-11-22T10:00:00Z",
            }
        ],
        "boards": [
            {
                "id": "b-1",
                "title": "Engineering",
                "items": [{"prompt_id": "pp-1"}],
            }
        ],
    }
    mapped = load_profiprompt_export_payload(export_doc)
    assert len(mapped) == 1
    assert mapped[0].id == "profiprompt:prompt:pp-1"
    assert mapped[0].category == "Engineering"
    assert "Inspect module coupling." in mapped[0].content
