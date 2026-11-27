"""Unit, UI-headless, and end-to-end tests for Stage 1b server synchronization."""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import stat
import sys
import threading
import time
from typing import Any, Dict, List, Optional, Tuple
from urllib import error as urllib_error

import pytest
from PySide6 import QtCore

from i18n import set_language
from models import ItemType, LibraryItem
from profiprompt_adapter import load_profiprompt_export_payload
from promptboard import MainWindow
from settings_dialog import (
    ConfirmReplaceLibraryDialog,
    ConflictResolutionDialog,
    FirstCouplingDialog,
    SettingsDialog,
    TargetQueueChangeDialog,
)
from settings_manager import SettingsManager
import storage as storage_mod
from storage import Storage
from sync_backend import (
     FileSlotBackend,
     NullBackend,
     OfflineQueue,
     REDIRECT_ERROR_MESSAGE,
     ServerBackend,
     SyncAuthError,
     SyncEngine,
     SyncTransportError,
     TokenStorage,
     _NoRedirectHandler,
     create_sync_backend,
     format_coupling_target,
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


class _DaemonThreadingHTTPServer(ThreadingHTTPServer):
    daemon_threads = True


def _start_http_server(
    handler_cls: type[BaseHTTPRequestHandler],
) -> Tuple[ThreadingHTTPServer, threading.Thread, str]:
    srv = _DaemonThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
    thread = threading.Thread(
        target=srv.serve_forever,
        kwargs={"poll_interval": 0.02},
        daemon=True,
    )
    thread.start()
    return srv, thread, f"http://127.0.0.1:{srv.server_address[1]}"


def _stop_http_server(
    srv: ThreadingHTTPServer,
    thread: threading.Thread,
    *,
    release_events: Tuple[threading.Event, ...] = (),
    timeout: float = 3.0,
) -> None:
    for ev in release_events:
        ev.set()
    srv.shutdown()
    srv.server_close()
    thread.join(timeout=timeout)


class _SignalRecorder:
    """Deterministic QSignalSpy-style helper backed by QEventLoop and QTimer."""

    def __init__(self, signal: Any) -> None:
        self._signal = signal
        self.emissions: List[Any] = []
        self.thread_ids: List[int] = []
        self._wait_loops: List[QtCore.QEventLoop] = []
        self._target_count: int = 1
        self._signal.connect(self._on_emit)

    def _on_emit(self, payload: Any = None) -> None:
        self.emissions.append(payload)
        self.thread_ids.append(threading.get_ident())
        if len(self.emissions) >= self._target_count:
            for loop in list(self._wait_loops):
                if loop.isRunning():
                    loop.quit()

    def wait(self, *, count: int = 1, timeout_ms: int = 3000) -> bool:
        self._target_count = max(1, int(count))
        if len(self.emissions) >= self._target_count:
            return True
        loop = QtCore.QEventLoop()
        self._wait_loops.append(loop)
        timer = QtCore.QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(loop.quit)
        timer.start(max(1, int(timeout_ms)))
        try:
            if len(self.emissions) < self._target_count:
                loop.exec()
        finally:
            timer.stop()
            if loop in self._wait_loops:
                self._wait_loops.remove(loop)
        return len(self.emissions) >= self._target_count

    def close(self) -> None:
        try:
            self._signal.disconnect(self._on_emit)
        except (RuntimeError, TypeError):
            pass


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
    status = backend.test_connection()
    assert status.ok is False
    pull_res = backend.pull()
    assert pull_res.offline is True
    push_res = backend.push([])
    assert push_res.queued_offline is True


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
        assert conflict_dlg.wait_for_background_push(3.0) is True
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


# ---------------------------------------------------------------------------
# Stage 1b review fix regressions (findings 1..6)
# ---------------------------------------------------------------------------


def test_redirect_blocked_no_token_leak_across_test_pull_and_push(tmp_path):
    """Finding 1: 3xx redirects are never followed and never leak Authorization headers."""
    assert _NoRedirectHandler().redirect_request(None, None, 302, "Found", {}, "http://127.0.0.1/") is None

    leaked_requests: List[Tuple[str, Optional[str]]] = []

    class CollectorHandler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            leaked_requests.append((self.path, self.headers.get("Authorization")))
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"namespaces": []}')

        def do_POST(self):  # noqa: N802
            leaked_requests.append((self.path, self.headers.get("Authorization")))
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"{}")

        def log_message(self, format, *args):  # noqa: A002
            return

    collector_srv, collector_thread, collector_base = _start_http_server(CollectorHandler)
    collector_url = f"{collector_base}/trap"

    redirect_code = {"status": 302}

    class RedirectingHandler(BaseHTTPRequestHandler):
        def _send_redirect(self):
            self.send_response(redirect_code["status"])
            self.send_header("Location", collector_url)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def do_GET(self):  # noqa: N802
            self._send_redirect()

        def do_POST(self):  # noqa: N802
            length = int(self.headers.get("Content-Length", "0") or 0)
            if length > 0:
                self.rfile.read(length)
            self._send_redirect()

        def log_message(self, format, *args):  # noqa: A002
            return

    redirect_srv, redirect_thread, redirect_base = _start_http_server(RedirectingHandler)

    try:
        settings, storage = _make_settings_and_storage(
            tmp_path,
            mode="server",
            server_url=redirect_base,
            token="pss_test_no_leak_secret",
        )
        engine = SyncEngine(storage, settings)

        for status_code in (301, 302, 307, 308):
            redirect_code["status"] = status_code
            conn = engine.test_connection()
            assert conn.ok is False
            assert REDIRECT_ERROR_MESSAGE in conn.detail

        out = engine.sync_once()
        assert out.ok is False
        assert REDIRECT_ERROR_MESSAGE in out.error

        backend = ServerBackend(server_url=redirect_base, token="pss_test_no_leak_secret")
        sample = LibraryItem(id="r-1", item_type=ItemType.PROMPT, name="REDIR", content="Body")
        mut = OfflineQueue(tmp_path / "rq").enqueue_upsert(sample, known_base_rev=0)[0]
        with pytest.raises(SyncTransportError, match=REDIRECT_ERROR_MESSAGE):
            backend.push([mut])

        assert leaked_requests == []
    finally:
        _stop_http_server(redirect_srv, redirect_thread)
        _stop_http_server(collector_srv, collector_thread)


def test_first_coupling_take_server_backup_removed_count_and_second_confirmation(
    qapp, tmp_path, live_sync_server
):
    """Finding 2: 'take_server' shows removed count, requires 2nd confirmation, and backs up library.json."""
    base_url = live_sync_server["base_url"]
    token = live_sync_server["token"]

    # Seed server with 2 entries via client A.
    settings_a, storage_a = _make_settings_and_storage(
        tmp_path / "seed_a",
        mode="server",
        server_url=base_url,
        token=token,
    )
    storage_a.upsert_many(
        [
            LibraryItem(id="shared-1", item_type=ItemType.PROMPT, name="SHARED", content="Server shared"),
            LibraryItem(id="srv-only-1", item_type=ItemType.SKILL, name="SRV SKILL", content="Server skill"),
        ]
    )
    assert SyncEngine(storage_a, settings_a).sync_once().ok is True

    # Client B has 1 shared entry + 2 local-only entries that would be removed by take_server.
    settings_b, storage_b = _make_settings_and_storage(
        tmp_path / "client_b",
        mode="server",
        server_url=base_url,
        token=token,
    )
    storage_b.upsert_many(
        [
            LibraryItem(id="shared-1", item_type=ItemType.PROMPT, name="SHARED", content="Local shared"),
            LibraryItem(id="local-rm-1", item_type=ItemType.AGENT, name="LOCAL RM 1", content="Keep me safe 1"),
            LibraryItem(id="local-rm-2", item_type=ItemType.WORKFLOW, name="LOCAL RM 2", content="Keep me safe 2"),
        ]
    )
    library_bytes_before = storage_b.library_file.read_bytes()

    window = MainWindow(storage_b, settings_b)
    try:
        observed: Dict[str, Any] = {}

        def _drive_cancel_second_confirmation() -> None:
            active = qapp.activeModalWidget()
            if isinstance(active, FirstCouplingDialog):
                observed["first_default_merge"] = active.merge_button.isDefault()
                observed["first_removed_count"] = active.removed_local_count
                observed["first_body"] = active.body_label.text()
                QtCore.QTimer.singleShot(10, _drive_cancel_second_confirmation)
                active.take_server_button.click()
            elif isinstance(active, ConfirmReplaceLibraryDialog):
                observed["confirm_default_cancel"] = active.cancel_button.isDefault()
                observed["confirm_body"] = active.body_label.text()
                active.cancel_button.click()
            else:
                QtCore.QTimer.singleShot(10, _drive_cancel_second_confirmation)

        QtCore.QTimer.singleShot(10, _drive_cancel_second_confirmation)
        cancelled_outcome = window.run_sync(interactive=True)

        assert observed["first_default_merge"] is True
        assert observed["first_removed_count"] == 2
        assert "2" in observed["first_body"]
        assert observed["confirm_default_cancel"] is True
        assert "2" in observed["confirm_body"]
        assert cancelled_outcome.cancelled is True
        assert storage_b.library_file.read_bytes() == library_bytes_before
        assert list(storage_b.data_dir.glob("library.backup-*.json")) == []
        assert window.sync_engine.state_store.load().coupled_targets == []

        # Second run: accept both dialogs -> backup written atomically before replacement.
        def _drive_accept_second_confirmation() -> None:
            active = qapp.activeModalWidget()
            if isinstance(active, FirstCouplingDialog):
                QtCore.QTimer.singleShot(10, _drive_accept_second_confirmation)
                active.take_server_button.click()
            elif isinstance(active, ConfirmReplaceLibraryDialog):
                active.confirm_button.click()
            else:
                QtCore.QTimer.singleShot(10, _drive_accept_second_confirmation)

        QtCore.QTimer.singleShot(10, _drive_accept_second_confirmation)
        accepted_outcome = window.run_sync(interactive=True)

        assert accepted_outcome.ok is True
        backups = list(storage_b.data_dir.glob("library.backup-*.json"))
        assert len(backups) == 1
        assert list(storage_b.data_dir.glob("*.tmp")) == []

        backup_doc = json.loads(backups[0].read_text(encoding="utf-8"))
        backup_by_id = {entry["id"]: entry for entry in backup_doc["items"]}
        assert "local-rm-1" in backup_by_id
        assert "local-rm-2" in backup_by_id
        assert backup_by_id["local-rm-1"]["content"] == "Keep me safe 1"
        assert backup_by_id["local-rm-2"]["content"] == "Keep me safe 2"

        final_ids = {it.id for it in storage_b.load_items()}
        assert final_ids == {"shared-1", "srv-only-1"}
    finally:
        window.shutdown_sync_workers(timeout_ms=3000)
        window.close()
        qapp.processEvents()


def test_async_qthreadpool_worker_nonblocking_startup_and_bounded_quit_flush(qapp, tmp_path):
    """Finding 3: Network runs on QThreadPool/QRunnable via signals; startup never blocks show; quit flush <= 2.5 s."""
    gui_thread_id = threading.get_ident()
    worker_threads: List[int] = []
    get_entered = threading.Event()
    release_get = threading.Event()
    release_post = threading.Event()

    class SlowSyncHandler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            worker_threads.append(threading.get_ident())
            get_entered.set()
            release_get.wait(timeout=5.0)
            body = json.dumps(
                {
                    "namespace": "promptboard",
                    "library_rev": 1,
                    "items": [
                        {
                            "id": "async-1",
                            "kind": "item",
                            "rev": 1,
                            "updated_at": "2026-11-22T12:00:00Z",
                            "payload": {
                                "id": "async-1",
                                "item_type": "PROMPT",
                                "name": "ASYNC ITEM",
                                "content": "Pulled in background",
                            },
                        }
                    ],
                    "tombstones": [],
                }
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("ETag", '"rev-1"')
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):  # noqa: N802
            worker_threads.append(threading.get_ident())
            length = int(self.headers.get("Content-Length", "0") or 0)
            if length > 0:
                self.rfile.read(length)
            # Simulate an unresponsive/stalling server on push to test bounded quit flush.
            release_post.wait(timeout=15.0)
            try:
                self.send_response(503)
                self.end_headers()
            except OSError:
                pass

        def log_message(self, format, *args):  # noqa: A002
            return

    slow_srv, srv_thread, slow_url = _start_http_server(SlowSyncHandler)

    try:
        settings, storage = _make_settings_and_storage(
            tmp_path,
            mode="server",
            server_url=slow_url,
            token="pss_async_worker_token",
        )
        window = MainWindow(storage, settings)
        spy = _SignalRecorder(window.sync_finished)
        try:
            t0 = time.perf_counter()
            assert window.sync_on_start(interactive=False) is None
            window.show()
            startup_elapsed = time.perf_counter() - t0
            # Startup pull runs in QThreadPool while release_get is still held, never blocking window.show().
            assert startup_elapsed < 1.0
            assert window.isVisible()
            assert len(spy.emissions) == 0

            assert get_entered.wait(timeout=3.0), "Background startup GET did not start"
            release_get.set()
            assert spy.wait(count=1, timeout_ms=3000) is True

            assert len(spy.emissions) == 1
            assert spy.emissions[0].ok is True
            assert worker_threads and all(tid != gui_thread_id for tid in worker_threads)
            assert spy.thread_ids == [gui_thread_id]
            assert storage.get_item("async-1") is not None

            # Enqueue a local edit and verify bounded quit flush never hangs shutdown (>15s server stall).
            window.create_item()
            assert window.sync_engine.get_pending_count() == 1
            t_quit = time.perf_counter()
            window.on_about_to_quit()
            quit_elapsed = time.perf_counter() - t_quit
            assert quit_elapsed <= window.QUIT_FLUSH_MAX_WAIT_S
            assert window._sync_thread_pool.waitForDone(0) is True
            assert window.sync_engine.get_pending_count() == 1
        finally:
            spy.close()
            release_get.set()
            release_post.set()
            window.shutdown_sync_workers(timeout_ms=3000)
            window.close()
            qapp.processEvents()
    finally:
        _stop_http_server(
            slow_srv,
            srv_thread,
            release_events=(release_get, release_post),
        )


def test_settings_dialog_reads_token_only_when_server_mode_and_shown_or_used(qapp, tmp_path):
    """Finding 4: Keyring/token storage is never queried in mode='off' or before sync UI is shown/used."""
    calls = {"get": 0, "set": 0, "delete": 0}
    vault = {"secret": "pss_stored_in_keyring"}

    class CountingKeyring:
        def get_password(self, service: str, account: str) -> Optional[str]:
            calls["get"] += 1
            return vault.get("secret")

        def set_password(self, service: str, account: str, secret: str) -> None:
            calls["set"] += 1
            vault["secret"] = secret

        def delete_password(self, service: str, account: str) -> None:
            calls["delete"] += 1
            vault.pop("secret", None)

    settings = SettingsManager()
    settings._cached_token_storage = TokenStorage(
        fallback_path=tmp_path / "fallback_token.json",
        keyring_backend=CountingKeyring(),
    )
    settings.qs.setValue("paths/data", str(tmp_path / "data"))
    settings.set_sync_mode("off")
    settings.set_sync_server_url("http://127.0.0.1:8765")
    settings.qs.sync()

    # 1) Mode = off: construct, show, relabel, and close -> zero keyring reads or writes!
    dlg_off = SettingsDialog(settings)
    try:
        dlg_off.show()
        qapp.processEvents()
        assert calls == {"get": 0, "set": 0, "delete": 0}
        dlg_off.close_button.click()
        assert calls == {"get": 0, "set": 0, "delete": 0}
        assert vault["secret"] == "pss_stored_in_keyring"
    finally:
        dlg_off.close()

    # 2) Mode = server: constructing hidden dialog does not read; showing sync UI reads once.
    settings.set_sync_mode("server")
    dlg_srv = SettingsDialog(settings)
    try:
        assert calls["get"] == 0
        dlg_srv.show()
        qapp.processEvents()
        assert calls["get"] == 1
        assert dlg_srv.sync_token_edit.text() == "pss_stored_in_keyring"
        dlg_srv.close_button.click()
        assert calls["set"] == 0
        assert calls["delete"] == 0
    finally:
        dlg_srv.close()

    # 3) Switching from mode='off' to mode='server' in UI loads existing token without wiping it.
    settings.set_sync_mode("off")
    calls["get"] = 0
    dlg_switch = SettingsDialog(settings)
    try:
        assert calls["get"] == 0
        srv_idx = dlg_switch.sync_mode_combo.findData("server")
        dlg_switch.sync_mode_combo.setCurrentIndex(srv_idx)
        assert calls["get"] == 1
        assert dlg_switch.sync_token_edit.text() == "pss_stored_in_keyring"
        assert calls["delete"] == 0
        assert vault["secret"] == "pss_stored_in_keyring"
    finally:
        dlg_switch.close()


def test_target_change_keeps_or_discards_bound_queue_without_sending_to_new_target(
    qapp, tmp_path, live_sync_server
):
    """Finding 5: Offline queue stays bound to its target; target change prompts keep (default) or discard."""
    base_url = live_sync_server["base_url"]
    token = live_sync_server["token"]

    settings, storage = _make_settings_and_storage(
        tmp_path / "node",
        mode="server",
        server_url=base_url,
        token=token,
        namespace="ns_alpha",
    )
    engine = SyncEngine(storage, settings)
    target_alpha = format_coupling_target(base_url, "ns_alpha")
    target_beta = format_coupling_target(base_url, "ns_beta")

    item_del = LibraryItem(id="del-alpha", item_type=ItemType.PROMPT, name="DEL ALPHA", content="Alpha")
    item_keep = LibraryItem(id="keep-alpha", item_type=ItemType.PROMPT, name="KEEP ALPHA", content="Stay")
    storage.upsert_many([item_del, item_keep])
    assert engine.sync_once().ok is True

    # Delete item_del locally before syncing (pending delete bound to ns_alpha).
    storage.delete_item("del-alpha")
    engine.enqueue_delete("del-alpha")
    assert engine.get_pending_count(target=target_alpha) == 1

    # Verify TargetQueueChangeDialog defaults to "keep".
    tq_dlg = TargetQueueChangeDialog(target_alpha, target_beta, pending_count=1)
    try:
        assert tq_dlg.keep_button.isDefault() is True
        tq_dlg.keep_button.click()
        assert tq_dlg.choice == "keep"
    finally:
        tq_dlg.close()

    # Switch to ns_beta in SettingsDialog accepting default "keep".
    prompted: List[Tuple[str, str, int]] = []

    def _choose_keep(old_t: str, new_t: str, count: int):
        prompted.append((old_t, new_t, count))
        return "keep"

    dlg = SettingsDialog(settings, sync_engine=engine, on_target_queue_change=_choose_keep)
    try:
        dlg.show()
        qapp.processEvents()
        dlg.sync_namespace_edit.setText("ns_beta")
        dlg.close_button.click()
    finally:
        dlg.close()

    assert prompted == [(target_alpha, target_beta, 1)]
    # Old queue is preserved under target_alpha; target_beta has 0 pending deletes.
    assert engine.get_pending_count(target=target_alpha) == 1
    assert engine.get_pending_count(target=target_beta) == 0

    # Syncing with ns_beta must NOT send del-alpha delete to ns_beta; ns_alpha still has del-alpha on server.
    out_beta = engine.sync_once()
    assert out_beta.ok is True
    assert engine.get_pending_count(target=target_alpha) == 1

    probe_alpha = ServerBackend(server_url=base_url, token=token, namespace="ns_alpha")
    alpha_remote_ids = {it.id for it in probe_alpha.pull(since_rev=None).upserts}
    assert "del-alpha" in alpha_remote_ids

    # Switching back to ns_alpha restores and flushes the preserved delete to ns_alpha!
    settings.set_sync_namespace("ns_alpha")
    out_alpha_back = engine.sync_once()
    assert out_alpha_back.ok is True
    assert engine.get_pending_count(target=target_alpha) == 0
    alpha_remote_ids_after = {it.id for it in probe_alpha.pull(since_rev=None).upserts}
    assert "del-alpha" not in alpha_remote_ids_after

    # Explicit "discard" on target change drops the old queue cleanly.
    storage.delete_item("keep-alpha")
    engine.enqueue_delete("keep-alpha")
    assert engine.get_pending_count(target=target_alpha) == 1

    settings.set_sync_namespace("ns_beta")
    out_discard = engine.sync_once(on_target_change_queue=lambda _o, _n, _c: "discard")
    assert out_discard.ok is True
    assert engine.get_pending_count(target=target_alpha) == 0


def test_about_to_quit_signal_fires_twice_guard_and_offline_queue_atomic_crash(
    qapp, tmp_path, monkeypatch
):
    """Finding 6: _quit_sync_done guards double aboutToQuit emission; OfflineQueue survives pre-replace crash."""
    # Part A: Emit real qapp.aboutToQuit twice while flush fails offline (so queue stays non-empty!).
    push_attempts = {"count": 0}

    def failing_requester(method: str, url: str, headers: Dict[str, str], body: Optional[bytes], timeout: float):
        if method == "POST" and url.endswith("/push"):
            push_attempts["count"] += 1
        raise urllib_error.URLError("simulated offline during quit")

    settings, storage = _make_settings_and_storage(
        tmp_path / "quit_guard",
        mode="server",
        server_url="http://127.0.0.1:8765",
        token="pss_quit_twice_token",
    )
    engine = SyncEngine(storage, settings, requester=failing_requester)
    window = MainWindow(storage, settings, sync_engine=engine)
    try:
        assert window.register_quit_hook(qapp) is True
        window.create_item()
        assert engine.get_pending_count() == 1

        qapp.aboutToQuit.emit()
        qapp.aboutToQuit.emit()

        # Even though pending_count is still 1 after the first failed flush, _quit_sync_done stops the 2nd!
        assert push_attempts["count"] == 1
        assert engine.get_pending_count() == 1
    finally:
        try:
            qapp.aboutToQuit.disconnect(window.on_about_to_quit)
        except (RuntimeError, TypeError):
            pass
        window.close()

    # Part B: Simulate crash between writing tmp file and os.replace in OfflineQueue.
    q_dir = tmp_path / "atomic_queue"
    queue = OfflineQueue(q_dir)
    first_item = LibraryItem(id="safe-1", item_type=ItemType.PROMPT, name="SAFE", content="Original v1")
    queue.enqueue_upsert(first_item, known_base_rev=2)
    bytes_before = queue.path.read_bytes()

    real_replace = storage_mod._atomic_replace_with_retry
    crash_state = {"tmp_seen": False}

    def crashing_replace(tmp: Path, target: Path) -> None:
        assert tmp.is_file()
        assert tmp.stat().st_size > 0
        crash_state["tmp_seen"] = True
        # Copy a stray tmp artifact to simulate hard power loss where cleanup also never ran.
        abandoned = tmp.parent / f"{tmp.name}.abandoned"
        abandoned.write_bytes(tmp.read_bytes())
        raise RuntimeError("Simulated crash between tmp write/fsync and replace")

    monkeypatch.setattr(storage_mod, "_atomic_replace_with_retry", crashing_replace)
    second_item = LibraryItem(id="crash-2", item_type=ItemType.SKILL, name="CRASH", content="Uncommitted")
    with pytest.raises(RuntimeError, match="Simulated crash"):
        queue.enqueue_upsert(second_item, known_base_rev=0)

    assert crash_state["tmp_seen"] is True
    assert queue.path.read_bytes() == bytes_before

    recovered = OfflineQueue(q_dir).load_all()
    assert len(recovered) == 1
    assert recovered[0].id == "safe-1"
    assert recovered[0].base_rev == 2
    assert recovered[0].payload["content"] == "Original v1"

    # Restore real atomic replace and verify queue continues working cleanly.
    monkeypatch.setattr(storage_mod, "_atomic_replace_with_retry", real_replace)
    queue.enqueue_upsert(second_item, known_base_rev=0)
    assert [m.id for m in OfflineQueue(q_dir).load_all()] == ["safe-1", "crash-2"]


# ---------------------------------------------------------------------------
# Stage 1b review round 2 regressions (B1 lost update & B2 GUI freeze)
# ---------------------------------------------------------------------------


def _run_concurrent_upsert_in_storage_window(
    storage: Storage,
    user_item: LibraryItem,
    run_target_op,
    *,
    arm_event: Optional[threading.Event] = None,
    upsert_done_event: Optional[threading.Event] = None,
) -> Dict[str, bool]:
    """Deterministically trigger ``storage.upsert_item(user_item)`` on a 2nd thread inside ``load_items..save_items``.

    Uses pure ``threading.Event`` synchronisation (zero ``time.sleep`` calls):
    - When the target operation calls ``load_items()`` (once ``arm_event`` is set, if given),
      ``window_entered`` wakes Thread 2.
    - Thread 2 probes ``storage._lock.acquire(blocking=False)`` to verify ``Storage._lock`` is
      held by Thread 1, signals ``probe_ready`` so Thread 1 can proceed to ``save_items()``,
      and immediately executes ``storage.upsert_item(user_item)``.
    - If ``Storage._lock`` were NOT held, Thread 2 would complete ``upsert_item`` before
      signalling ``probe_ready``, causing Thread 1's subsequent ``save_items()`` to overwrite it.
    """
    window_entered = threading.Event()
    probe_ready = threading.Event()
    in_window = threading.Event()
    save_finished = threading.Event()
    observations = {
        "window_hit": False,
        "lock_held_in_window": False,
    }

    orig_load = storage.load_items
    orig_save = storage.save_items
    worker_tid_box: Dict[str, Optional[int]] = {"tid": None}

    def hooked_load_items():
        items = orig_load()
        if (
            threading.get_ident() == worker_tid_box["tid"]
            and (arm_event is None or arm_event.is_set())
            and not window_entered.is_set()
        ):
            observations["window_hit"] = True
            in_window.set()
            window_entered.set()
            assert probe_ready.wait(timeout=5.0), "Timed out waiting for concurrent upsert thread"
        return items

    def hooked_save_items(items):
        try:
            return orig_save(items)
        finally:
            if threading.get_ident() == worker_tid_box["tid"] and window_entered.is_set():
                in_window.clear()
                save_finished.set()

    storage.load_items = hooked_load_items  # type: ignore[method-assign]
    storage.save_items = hooked_save_items  # type: ignore[method-assign]

    errors: List[BaseException] = []

    def thread1_main():
        worker_tid_box["tid"] = threading.get_ident()
        try:
            run_target_op()
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)
            window_entered.set()

    def thread2_concurrent_gui_save():
        try:
            assert window_entered.wait(timeout=5.0), "Target load_items..save_items window never opened"
            if errors:
                probe_ready.set()
                return
            can_steal = storage._lock.acquire(blocking=False)
            if can_steal:
                storage._lock.release()
                storage.upsert_item(user_item)
                if upsert_done_event is not None:
                    upsert_done_event.set()
                probe_ready.set()
            else:
                observations["lock_held_in_window"] = True
                probe_ready.set()
                storage.upsert_item(user_item)
                if upsert_done_event is not None:
                    upsert_done_event.set()
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)
            if upsert_done_event is not None:
                upsert_done_event.set()
            probe_ready.set()

    try:
        t1 = threading.Thread(target=thread1_main)
        t2 = threading.Thread(target=thread2_concurrent_gui_save)
        t1.start()
        t2.start()
        t1.join(timeout=5.0)
        t2.join(timeout=5.0)
        assert not t1.is_alive(), "Thread 1 deadlocked"
        assert not t2.is_alive(), "Thread 2 deadlocked"
        if errors:
            raise errors[0]
        observations["in_window_cleared"] = not in_window.is_set()
        observations["save_finished"] = save_finished.is_set()
        return observations
    finally:
        storage.load_items = orig_load  # type: ignore[method-assign]
        storage.save_items = orig_save  # type: ignore[method-assign]


def test_b1_reconcile_pull_holds_storage_lock_and_preserves_concurrent_upsert(tmp_path):
    """B1 path 1 (_reconcile_pull): concurrent GUI upsert_item inside load..save survives; no I/O under lock."""
    pull_fetched = threading.Event()
    network_under_storage_lock = {"violation": False}
    settings_holder: Dict[str, Storage] = {}

    def probe_lock_held_from_other_thread(storage_obj: Storage) -> bool:
        held = {"value": False}

        def _check():
            if storage_obj._lock.acquire(blocking=False):
                storage_obj._lock.release()
            else:
                held["value"] = True

        probe_t = threading.Thread(target=_check)
        probe_t.start()
        probe_t.join(timeout=2.0)
        return held["value"]

    step = {"phase": "couple"}

    def fake_requester(method: str, url: str, headers: Dict[str, str], body: Optional[bytes], timeout: float):
        st_obj = settings_holder["storage"]
        if probe_lock_held_from_other_thread(st_obj):
            network_under_storage_lock["violation"] = True

        if step["phase"] == "couple":
            if method == "GET":
                return 200, {"etag": '"rev-1"'}, json.dumps(
                    {
                        "namespace": "promptboard",
                        "library_rev": 1,
                        "items": [
                            {
                                "id": "seed-1",
                                "kind": "item",
                                "rev": 1,
                                "updated_at": "2026-11-22T12:00:00Z",
                                "payload": {
                                    "id": "seed-1",
                                    "item_type": "PROMPT",
                                    "name": "SEED",
                                    "content": "Initial",
                                },
                            }
                        ],
                        "tombstones": [],
                    }
                ).encode("utf-8")
            raise AssertionError(f"Unexpected request during coupling: {method} {url}")

        if method == "GET" and "/changes?since_rev=1" in url:
            pull_fetched.set()
            return 200, {"etag": '"rev-2"'}, json.dumps(
                {
                    "namespace": "promptboard",
                    "library_rev": 2,
                    "items": [
                        {
                            "id": "remote-new",
                            "kind": "item",
                            "rev": 2,
                            "updated_at": "2026-11-22T12:05:00Z",
                            "payload": {
                                "id": "remote-new",
                                "item_type": "SKILL",
                                "name": "REMOTE SKILL",
                                "content": "From server rev 2",
                            },
                        }
                    ],
                    "tombstones": [],
                }
            ).encode("utf-8")
        raise AssertionError(f"Unexpected request: {method} {url}")

    settings, storage = _make_settings_and_storage(
        tmp_path,
        mode="server",
        server_url="http://127.0.0.1:8765",
        token="pss_b1_reconcile",
    )
    settings_holder["storage"] = storage
    engine = SyncEngine(storage, settings, requester=fake_requester)
    assert engine.sync_once().ok is True

    step["phase"] = "steady_pull"
    gui_saved = LibraryItem(
        id="gui-concurrent-reconcile",
        item_type=ItemType.PROMPT,
        name="GUI CONCURRENT",
        content="Must survive _reconcile_pull",
    )
    outcomes: List[Any] = []
    obs = _run_concurrent_upsert_in_storage_window(
        storage,
        gui_saved,
        lambda: outcomes.append(engine.sync_once()),
        arm_event=pull_fetched,
    )

    assert obs["window_hit"] is True
    assert obs["lock_held_in_window"] is True
    assert obs["save_finished"] is True
    assert network_under_storage_lock["violation"] is False
    assert outcomes and outcomes[0].ok is True
    assert storage.get_item("remote-new") is not None
    surviving = storage.get_item("gui-concurrent-reconcile")
    assert surviving is not None
    assert surviving.content == "Must survive _reconcile_pull"


def test_b1_take_server_holds_storage_lock_and_preserves_concurrent_upsert(tmp_path):
    """B1 path 2 (take_server): concurrent GUI upsert_item inside load..save survives; no I/O under lock."""
    pull_fetched = threading.Event()
    network_under_storage_lock = {"violation": False}
    storage_ref: Dict[str, Storage] = {}

    def fake_requester(method: str, url: str, headers: Dict[str, str], body: Optional[bytes], timeout: float):
        st_obj = storage_ref["storage"]

        def _check_lock():
            if st_obj._lock.acquire(blocking=False):
                st_obj._lock.release()
            else:
                network_under_storage_lock["violation"] = True

        probe = threading.Thread(target=_check_lock)
        probe.start()
        probe.join(timeout=2.0)

        assert method == "GET"
        pull_fetched.set()
        return 200, {"etag": '"rev-3"'}, json.dumps(
            {
                "namespace": "promptboard",
                "library_rev": 3,
                "items": [
                    {
                        "id": "srv-adopted",
                        "kind": "item",
                        "rev": 3,
                        "updated_at": "2026-11-22T13:00:00Z",
                        "payload": {
                            "id": "srv-adopted",
                            "item_type": "PROMPT",
                            "name": "ADOPTED",
                            "content": "Canonical server item",
                        },
                    }
                ],
                "tombstones": [],
            }
        ).encode("utf-8")

    settings, storage = _make_settings_and_storage(
        tmp_path,
        mode="server",
        server_url="http://127.0.0.1:8765",
        token="pss_b1_take_server",
    )
    storage_ref["storage"] = storage
    pre_existing = LibraryItem(
        id="pre-local-only",
        item_type=ItemType.AGENT,
        name="PRE LOCAL",
        content="Backed up before take_server",
    )
    storage.upsert_item(pre_existing)
    engine = SyncEngine(storage, settings, requester=fake_requester)

    gui_saved = LibraryItem(
        id="gui-concurrent-take-server",
        item_type=ItemType.PROMPT,
        name="LIVE GUI EDIT",
        content="Must survive take_server window",
    )
    outcomes: List[Any] = []
    obs = _run_concurrent_upsert_in_storage_window(
        storage,
        gui_saved,
        lambda: outcomes.append(engine.sync_once(first_coupling_choice="take_server")),
        arm_event=pull_fetched,
    )

    assert obs["window_hit"] is True
    assert obs["lock_held_in_window"] is True
    assert obs["save_finished"] is True
    assert network_under_storage_lock["violation"] is False
    assert outcomes and outcomes[0].ok is True

    backups = list(storage.data_dir.glob("library.backup-*.json"))
    assert len(backups) == 1
    backup_ids = {entry["id"] for entry in json.loads(backups[0].read_text(encoding="utf-8"))["items"]}
    assert "pre-local-only" in backup_ids

    assert storage.get_item("srv-adopted") is not None
    surviving = storage.get_item("gui-concurrent-take-server")
    assert surviving is not None
    assert surviving.content == "Must survive take_server window"


@pytest.mark.parametrize("resolution", ["keep_copy", "keep_local", "take_server"])
def test_b1_resolve_conflict_holds_storage_lock_and_preserves_concurrent_upsert(
    tmp_path, resolution
):
    """B1 path 3 (resolve_conflict): concurrent upsert_item inside load..save survives; push runs unlocked."""
    network_under_storage_lock = {"violation": False}
    upsert_completed = threading.Event()
    push_count = {"n": 0}
    storage_ref: Dict[str, Storage] = {}

    def fake_requester(method: str, url: str, headers: Dict[str, str], body: Optional[bytes], timeout: float):
        st_obj = storage_ref["storage"]
        # While Thread 1 is paused here inside HTTP push, Thread 2 must be able to acquire
        # Storage._lock and finish upsert_item (which would deadlock if Thread 1 still held it).
        if not upsert_completed.wait(timeout=2.0):
            network_under_storage_lock["violation"] = True
        else:
            def _check_lock():
                if st_obj._lock.acquire(blocking=False):
                    st_obj._lock.release()
                else:
                    network_under_storage_lock["violation"] = True

            probe = threading.Thread(target=_check_lock)
            probe.start()
            probe.join(timeout=2.0)

        assert method == "POST" and url.endswith("/push")
        push_count["n"] += 1
        doc = json.loads(body.decode("utf-8"))
        return 200, {"etag": '"rev-5"'}, json.dumps(
            {
                "namespace": "promptboard",
                "library_rev": 5,
                "applied": [
                    {"id": m["id"], "kind": m["kind"], "op": m["op"], "rev": 5}
                    for m in doc["mutations"]
                ],
                "conflicts": [],
            }
        ).encode("utf-8")

    settings, storage = _make_settings_and_storage(
        tmp_path,
        mode="server",
        server_url="http://127.0.0.1:8765",
        token="pss_b1_resolve",
    )
    storage_ref["storage"] = storage
    local_conflict_item = LibraryItem(
        id="conf-item",
        item_type=ItemType.PROMPT,
        name="CONFLICTED",
        content="Local conflict draft",
    )
    server_conflict_item = LibraryItem(
        id="conf-item",
        item_type=ItemType.PROMPT,
        name="CONFLICTED",
        content="Server conflict version",
    )
    storage.upsert_item(local_conflict_item)

    engine = SyncEngine(storage, settings, requester=fake_requester)
    target_id = engine.target_coupling_id()
    state = engine.state_store.load()
    state.active_target = target_id
    state.coupled_targets = [target_id]
    state.library_rev = 4
    from sync_backend import ConflictEntry
    from models import item_to_dict

    state.conflicts = [
        ConflictEntry(
            id="conf-item",
            kind="item",
            title="CONFLICTED",
            source="server",
            client_base_rev=1,
            server_rev=4,
            updated_at="2026-11-22T14:00:00Z",
            local_op="upsert",
            local_item=item_to_dict(local_conflict_item),
            server_item=item_to_dict(server_conflict_item),
            server_deleted=False,
        )
    ]
    engine.state_store.save(state)

    gui_saved = LibraryItem(
        id=f"gui-concurrent-{resolution}",
        item_type=ItemType.WORKFLOW,
        name="CONCURRENT WORKFLOW",
        content=f"Must survive resolve_conflict({resolution})",
    )
    resolved_copy: List[Optional[LibraryItem]] = []
    obs = _run_concurrent_upsert_in_storage_window(
        storage,
        gui_saved,
        lambda: resolved_copy.append(engine.resolve_conflict("conf-item", resolution)),
        upsert_done_event=upsert_completed,
    )

    assert obs["window_hit"] is True
    assert obs["lock_held_in_window"] is True
    assert obs["save_finished"] is True
    assert network_under_storage_lock["violation"] is False
    assert engine.get_conflicts() == []

    surviving = storage.get_item(gui_saved.id)
    assert surviving is not None
    assert surviving.content == f"Must survive resolve_conflict({resolution})"

    resolved_main = storage.get_item("conf-item")
    assert resolved_main is not None
    if resolution == "keep_local":
        assert resolved_main.content == "Local conflict draft"
        assert push_count["n"] == 1
    elif resolution == "keep_copy":
        assert resolved_main.content == "Server conflict version"
        assert resolved_copy[0] is not None
        assert storage.get_item(resolved_copy[0].id) is not None
        assert push_count["n"] == 1
    else:
        assert resolved_main.content == "Server conflict version"


def test_b2_hanging_server_never_blocks_enqueue_target_change_or_bounded_quit(qapp, tmp_path):
    """B2: While a sync request hangs on 127.0.0.1, enqueue_*, target change (<1s) and quit (<=2.5s) stay fast."""
    first_request_hanging = threading.Event()
    release_server_hang = threading.Event()

    class NeverAnsweringHandler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            first_request_hanging.set()
            release_server_hang.wait(timeout=15.0)
            try:
                self.send_response(503)
                self.end_headers()
            except OSError:
                pass

        def do_POST(self):  # noqa: N802
            length = int(self.headers.get("Content-Length", "0") or 0)
            if length > 0:
                self.rfile.read(length)
            first_request_hanging.set()
            release_server_hang.wait(timeout=15.0)
            try:
                self.send_response(503)
                self.end_headers()
            except OSError:
                pass

        def log_message(self, format, *args):  # noqa: A002
            return

    hanging_srv, srv_thread, hanging_url = _start_http_server(NeverAnsweringHandler)

    try:
        settings, storage = _make_settings_and_storage(
            tmp_path,
            mode="server",
            server_url=hanging_url,
            token="pss_hanging_token",
            namespace="ns_primary",
        )
        seed_delete = LibraryItem(
            id="to-delete",
            item_type=ItemType.PROMPT,
            name="DELETE ME",
            content="Seeded item",
        )
        storage.upsert_item(seed_delete)
        engine = SyncEngine(storage, settings)
        primary_target = format_coupling_target(hanging_url, "ns_primary")
        secondary_target = format_coupling_target(hanging_url, "ns_secondary")
        init_state = engine.state_store.load()
        init_state.active_target = primary_target
        init_state.coupled_targets = [primary_target]
        init_state.item_revs[make_object_key("item", "to-delete")] = 1
        engine.state_store.save(init_state)

        window = MainWindow(storage, settings, sync_engine=engine)
        try:
            # Start background sync_once() which hangs inside HTTP GET (10 s timeout).
            assert window.sync_on_start(interactive=False) is None
            assert first_request_hanging.wait(timeout=3.0), "Background sync request did not start"

            # 1) enqueue_upsert must return in < 1 s while sync_once is hanging in I/O.
            up_item = LibraryItem(
                id="fast-upsert",
                item_type=ItemType.PROMPT,
                name="FAST UPSERT",
                content="No freeze on save",
            )
            t0 = time.perf_counter()
            engine.enqueue_upsert(up_item)
            upsert_elapsed = time.perf_counter() - t0
            assert upsert_elapsed < 1.0

            # 2) enqueue_delete must return in < 1 s while sync_once is hanging in I/O.
            t0 = time.perf_counter()
            engine.enqueue_delete("to-delete")
            delete_elapsed = time.perf_counter() - t0
            assert delete_elapsed < 1.0
            assert engine.get_pending_count(target=primary_target) == 2

            # 3) inspect_pending_target_change & apply_target_change must each return in < 1 s.
            t0 = time.perf_counter()
            pending_info = engine.inspect_pending_target_change(
                new_url=hanging_url,
                new_namespace="ns_secondary",
            )
            inspect_elapsed = time.perf_counter() - t0
            assert inspect_elapsed < 1.0
            assert pending_info == (primary_target, secondary_target, 2)

            t0 = time.perf_counter()
            engine.apply_target_change("keep", new_target=secondary_target)
            apply_elapsed = time.perf_counter() - t0
            assert apply_elapsed < 1.0
            assert engine.get_pending_count(target=primary_target) == 2
            assert engine.get_pending_count(target=secondary_target) == 0

            # Switch back to primary_target via SettingsDialog UI while request is still hanging.
            dlg = SettingsDialog(
                settings,
                sync_engine=engine,
                on_target_queue_change=lambda *_args: "keep",
            )
            try:
                t0 = time.perf_counter()
                dlg.sync_namespace_edit.setText("ns_primary")
                dlg._persist_sync_fields()
                dlg_elapsed = time.perf_counter() - t0
                assert dlg_elapsed < 1.0
            finally:
                dlg.shutdown_workers(timeout_ms=2000)
                dlg.close()

            # 4) Quit path with a dirty GUI item + hanging request must finish within the 2.5 s bound.
            window.create_item()
            dirty_id = window.current_item_id
            assert dirty_id is not None
            window.content_edit.setPlainText("Dirty editor text saved on quit")
            assert window._dirty is True

            t_quit = time.perf_counter()
            window.on_about_to_quit()
            quit_elapsed = time.perf_counter() - t_quit
            assert quit_elapsed <= window.QUIT_FLUSH_MAX_WAIT_S
            assert window._sync_thread_pool.waitForDone(0) is True
            saved_on_quit = storage.get_item(dirty_id)
            assert saved_on_quit is not None
            assert saved_on_quit.content == "Dirty editor text saved on quit"
            assert engine.get_pending_count(target=primary_target) >= 3
        finally:
            release_server_hang.set()
            assert window.shutdown_sync_workers(timeout_ms=3000) is True
            window.close()
            qapp.processEvents()
    finally:
        _stop_http_server(
            hanging_srv,
            srv_thread,
            release_events=(release_server_hang,),
        )


# ---------------------------------------------------------------------------
# Stage 1b follow-up regressions (PR #7 review: non-blocking conflict UI & quit pool drain)
# ---------------------------------------------------------------------------


def test_followup1_conflict_resolution_dialog_never_blocks_gui_on_hanging_server(qapp, tmp_path):
    """Follow-up 1: ConflictResolutionDialog.apply_resolution returns in < 1 s and pushes via worker."""
    gui_tid = threading.get_ident()
    push_started = threading.Event()
    standalone_push_started = threading.Event()
    release_hang = threading.Event()
    worker_tids: List[int] = []
    worker_lock = threading.Lock()

    class HangingPushHandler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            with worker_lock:
                worker_tids.append(threading.get_ident())
            release_hang.wait(timeout=15.0)
            try:
                self.send_response(503)
                self.end_headers()
            except OSError:
                pass

        def do_POST(self):  # noqa: N802
            with worker_lock:
                worker_tids.append(threading.get_ident())
            length = int(self.headers.get("Content-Length", "0") or 0)
            if length > 0:
                self.rfile.read(length)
            if "/ns_standalone/" in self.path:
                standalone_push_started.set()
            else:
                push_started.set()
            release_hang.wait(timeout=15.0)
            try:
                self.send_response(503)
                self.end_headers()
            except OSError:
                pass

        def log_message(self, format, *args):  # noqa: A002
            return

    hanging_srv, srv_thread, hanging_url = _start_http_server(HangingPushHandler)

    try:
        from models import item_to_dict
        from sync_backend import ConflictEntry

        # 1) MainWindow + ConflictResolutionDialog path (hands push to MainWindow.start_sync / QThreadPool)
        settings, storage = _make_settings_and_storage(
            tmp_path / "win_case",
            mode="server",
            server_url=hanging_url,
            token="pss_followup1_token",
            namespace="promptboard",
        )
        local_1 = LibraryItem(id="c-1", item_type=ItemType.PROMPT, name="CONF ONE", content="Local v2")
        server_1 = LibraryItem(id="c-1", item_type=ItemType.PROMPT, name="CONF ONE", content="Server v2")
        local_2 = LibraryItem(id="c-2", item_type=ItemType.SKILL, name="CONF TWO", content="Local copy v2")
        server_2 = LibraryItem(id="c-2", item_type=ItemType.SKILL, name="CONF TWO", content="Server canonical v2")
        storage.upsert_many([local_1, local_2])

        engine = SyncEngine(storage, settings)
        target_id = engine.target_coupling_id()
        state = engine.state_store.load()
        state.active_target = target_id
        state.coupled_targets = [target_id]
        state.library_rev = 3
        state.conflicts = [
            ConflictEntry(
                id="c-1",
                kind="item",
                title="CONF ONE",
                source="server",
                client_base_rev=1,
                server_rev=3,
                updated_at="2026-11-22T18:00:00Z",
                local_op="upsert",
                local_item=item_to_dict(local_1),
                server_item=item_to_dict(server_1),
                server_deleted=False,
            ),
            ConflictEntry(
                id="c-2",
                kind="item",
                title="CONF TWO",
                source="server",
                client_base_rev=1,
                server_rev=3,
                updated_at="2026-11-22T18:01:00Z",
                local_op="upsert",
                local_item=item_to_dict(local_2),
                server_item=item_to_dict(server_2),
                server_deleted=False,
            ),
        ]
        engine.state_store.save(state)

        window = MainWindow(storage, settings, sync_engine=engine)
        dlg = ConflictResolutionDialog(
            engine,
            parent=window,
            on_resolved=window._refresh_after_sync_change,
            on_push_requested=lambda: window.start_sync(interactive=False),
        )
        try:
            t0 = time.perf_counter()
            assert dlg.apply_resolution("keep_local") is True
            elapsed_first = time.perf_counter() - t0
            assert elapsed_first < 1.0
            assert len(engine.get_conflicts()) == 1
            assert storage.get_item("c-1").content == "Local v2"
            assert engine.get_pending_count(target=target_id) == 1

            # Worker thread picks up the queued push and attempts HTTP POST off the GUI thread.
            assert push_started.wait(timeout=3.0), "Worker did not attempt push"
            with worker_lock:
                assert worker_tids and all(tid != gui_tid for tid in worker_tids)

            # Second click while worker is still blocked on 127.0.0.1 also returns in < 1 s.
            t1 = time.perf_counter()
            assert dlg.apply_resolution("keep_copy") is True
            elapsed_second = time.perf_counter() - t1
            assert elapsed_second < 1.0
            assert engine.get_conflicts() == []
            assert storage.get_item("c-2").content == "Server canonical v2"
            assert len(storage.load_items()) == 3
            assert engine.get_pending_count(target=target_id) == 2
            assert window._sync_rerun_requested is True
        finally:
            assert dlg.shutdown_workers(timeout_s=3.0) is True
            dlg.close()
            window.on_about_to_quit()
            assert window.shutdown_sync_workers(timeout_ms=3000) is True
            window.close()
            qapp.processEvents()

        # 2) Standalone ConflictResolutionDialog (no MainWindow) returns in < 1 s and signals worker completion.
        settings_s, storage_s = _make_settings_and_storage(
            tmp_path / "standalone_case",
            mode="server",
            server_url=hanging_url,
            token="pss_followup1_standalone",
            namespace="ns_standalone",
        )
        storage_s.upsert_item(local_1)
        engine_s = SyncEngine(storage_s, settings_s)
        target_s = engine_s.target_coupling_id()
        st_s = engine_s.state_store.load()
        st_s.active_target = target_s
        st_s.coupled_targets = [target_s]
        st_s.library_rev = 2
        st_s.conflicts = [
            ConflictEntry(
                id="c-1",
                kind="item",
                title="CONF ONE",
                source="server",
                client_base_rev=1,
                server_rev=2,
                updated_at="2026-11-22T18:05:00Z",
                local_op="upsert",
                local_item=item_to_dict(local_1),
                server_item=item_to_dict(server_1),
                server_deleted=False,
            )
        ]
        engine_s.state_store.save(st_s)

        dlg_s = ConflictResolutionDialog(engine_s)
        standalone_spy = _SignalRecorder(dlg_s.background_push_finished)
        try:
            t_s = time.perf_counter()
            assert dlg_s.apply_resolution("keep_local") is True
            assert (time.perf_counter() - t_s) < 1.0
            assert engine_s.get_pending_count(target=target_s) == 1
            assert standalone_push_started.wait(timeout=3.0), "Standalone worker did not attempt push"

            engine_s.begin_shutdown()
            assert standalone_spy.wait(count=1, timeout_ms=3000) is True
            assert dlg_s.wait_for_background_push(3.0) is True
        finally:
            standalone_spy.close()
            assert dlg_s.shutdown_workers(timeout_s=3.0) is True
            dlg_s.close()
            qapp.processEvents()
    finally:
        _stop_http_server(
            hanging_srv,
            srv_thread,
            release_events=(release_hang,),
        )


def test_followup2_quit_aborts_running_sync_uses_short_timeout_and_idles_pool_within_bound(
    qapp, tmp_path
):
    """Follow-up 2: With a hanging server and a running sync, quit finishes and QThreadPool is idle within bound."""
    get_in_flight_a = threading.Event()
    get_in_flight_b = threading.Event()
    post_in_flight_b = threading.Event()
    release_hang = threading.Event()

    class HangingQuitHandler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            if "/ns_a/" in self.path:
                get_in_flight_a.set()
            else:
                get_in_flight_b.set()
            release_hang.wait(timeout=15.0)
            try:
                self.send_response(503)
                self.end_headers()
            except OSError:
                pass

        def do_POST(self):  # noqa: N802
            length = int(self.headers.get("Content-Length", "0") or 0)
            if length > 0:
                self.rfile.read(length)
            post_in_flight_b.set()
            release_hang.wait(timeout=15.0)
            try:
                self.send_response(503)
                self.end_headers()
            except OSError:
                pass

        def log_message(self, format, *args):  # noqa: A002
            return

    hanging_srv, srv_thread, hanging_url = _start_http_server(HangingQuitHandler)

    try:
        from sync_backend import default_http_requester

        # Case A: Running sync (10 s timeout on 15 s hanging server) + no pending edits -> aborts & idles fast.
        settings_a, storage_a = _make_settings_and_storage(
            tmp_path / "quit_idle_a",
            mode="server",
            server_url=hanging_url,
            token="pss_followup2_a",
            namespace="ns_a",
        )
        engine_a = SyncEngine(storage_a, settings_a)
        window_a = MainWindow(storage_a, settings_a, sync_engine=engine_a)
        try:
            assert window_a.sync_on_start(interactive=False) is None
            assert get_in_flight_a.wait(timeout=3.0), "Sync GET did not start"
            assert window_a._sync_thread_pool.activeThreadCount() >= 1

            t0 = time.perf_counter()
            window_a.on_about_to_quit()
            quit_elapsed_a = time.perf_counter() - t0

            assert engine_a.is_cancelled() is True
            assert quit_elapsed_a <= window_a.QUIT_FLUSH_MAX_WAIT_S
            # Before release_hang is set, the pool must ALREADY be completely idle!
            assert window_a._sync_thread_pool.waitForDone(0) is True
            assert window_a._sync_thread_pool.activeThreadCount() == 0
        finally:
            assert window_a.shutdown_sync_workers(timeout_ms=3000) is True
            window_a.close()
            qapp.processEvents()

        # Case B: Running sync + dirty pending edit -> aborts GET, runs post-quit flush with <= 1 s timeout,
        # finishes and leaves QThreadPool completely idle within the 2.5 s quit bound.
        observed_post_quit_timeouts: List[float] = []
        quit_started = threading.Event()

        settings_b, storage_b = _make_settings_and_storage(
            tmp_path / "quit_idle_b",
            mode="server",
            server_url=hanging_url,
            token="pss_followup2_b",
            namespace="ns_b",
        )
        engine_b = SyncEngine(storage_b, settings_b)
        target_b = engine_b.target_coupling_id()
        st_b = engine_b.state_store.load()
        st_b.active_target = target_b
        st_b.coupled_targets = [target_b]
        engine_b.state_store.save(st_b)

        def observing_requester(
            method: str,
            url: str,
            headers: Dict[str, str],
            body: Optional[bytes],
            timeout: float,
        ):
            if quit_started.is_set():
                observed_post_quit_timeouts.append(timeout)
            return default_http_requester(
                method,
                url,
                headers,
                body,
                timeout,
                abort_controller=engine_b._abort_controller,
            )

        engine_b._custom_requester = observing_requester
        window_b = MainWindow(storage_b, settings_b, sync_engine=engine_b)
        try:
            assert window_b.sync_on_start(interactive=False) is None
            assert get_in_flight_b.wait(timeout=3.0), "Steady-state GET did not start"
            assert window_b._sync_thread_pool.activeThreadCount() >= 1

            window_b.create_item()
            window_b.content_edit.setPlainText("Unsaved quit edit")
            quit_started.set()

            t1 = time.perf_counter()
            window_b.on_about_to_quit()
            quit_elapsed_b = time.perf_counter() - t1

            assert post_in_flight_b.wait(timeout=1.0) is True
            assert observed_post_quit_timeouts
            assert all(t <= 1.0 for t in observed_post_quit_timeouts)
            assert quit_elapsed_b <= window_b.QUIT_FLUSH_MAX_WAIT_S
            assert window_b._sync_thread_pool.waitForDone(0) is True
            assert window_b._sync_thread_pool.activeThreadCount() == 0
            assert engine_b.get_pending_count(target=target_b) >= 1
        finally:
            assert window_b.shutdown_sync_workers(timeout_ms=3000) is True
            window_b.close()
            qapp.processEvents()
    finally:
        _stop_http_server(
            hanging_srv,
            srv_thread,
            release_events=(release_hang,),
        )


def test_foreign_thread_abort_uses_shutdown_only_and_closes_on_owning_worker_thread(monkeypatch):
    """Fix 1: Foreign thread calls shutdown(SHUT_RDWR) only; socket close happens exclusively on worker."""
    import socket as socket_mod
    from sync_backend import _RequestAbortController, default_http_requester

    req_in_flight = threading.Event()
    release_hang = threading.Event()

    class SilentHoldHandler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            req_in_flight.set()
            release_hang.wait(timeout=10.0)

        def log_message(self, format, *args):  # noqa: A002
            return

    srv, srv_thread, base_url = _start_http_server(SilentHoldHandler)
    controller = _RequestAbortController()
    main_tid = threading.get_ident()
    worker_tid_box: Dict[str, int] = {}
    shutdown_tids: List[int] = []
    close_tids: List[int] = []
    tracked_ids: set[int] = set()
    event_lock = threading.Lock()

    orig_register = controller.register_socket
    orig_shutdown = socket_mod.socket.shutdown
    orig_close = socket_mod.socket.close
    orig_real_close = socket_mod.socket._real_close

    def hooked_register(sock: Any, epoch: int) -> None:
        with event_lock:
            tracked_ids.add(id(sock))
        orig_register(sock, epoch)

    def hooked_shutdown(self: socket_mod.socket, how: int) -> None:
        if id(self) in tracked_ids:
            with event_lock:
                shutdown_tids.append(threading.get_ident())
        return orig_shutdown(self, how)

    def hooked_close(self: socket_mod.socket) -> None:
        if id(self) in tracked_ids:
            with event_lock:
                close_tids.append(threading.get_ident())
        return orig_close(self)

    def hooked_real_close(self: socket_mod.socket) -> None:
        if id(self) in tracked_ids:
            with event_lock:
                close_tids.append(threading.get_ident())
        return orig_real_close(self)

    monkeypatch.setattr(controller, "register_socket", hooked_register)
    monkeypatch.setattr(socket_mod.socket, "shutdown", hooked_shutdown)
    monkeypatch.setattr(socket_mod.socket, "close", hooked_close)
    monkeypatch.setattr(socket_mod.socket, "_real_close", hooked_real_close)

    worker_errors: List[BaseException] = []

    def _worker() -> None:
        worker_tid_box["tid"] = threading.get_ident()
        try:
            default_http_requester(
                "GET",
                f"{base_url}/v1/libraries",
                {},
                None,
                10.0,
                abort_controller=controller,
            )
        except BaseException as exc:  # noqa: BLE001
            worker_errors.append(exc)

    worker_thread = threading.Thread(target=_worker)
    try:
        worker_thread.start()
        assert req_in_flight.wait(timeout=3.0), "Worker request never reached server"
        controller.abort_all()
        worker_thread.join(timeout=2.0)
        assert not worker_thread.is_alive(), "Worker thread did not abort promptly"
        assert worker_errors, "Aborted request should raise transport error"
        worker_tid = worker_tid_box["tid"]
        assert worker_tid != main_tid
        assert main_tid in shutdown_tids
        assert close_tids, "Tracked socket must be closed by owning worker thread"
        assert set(close_tids) == {worker_tid}
    finally:
        _stop_http_server(srv, srv_thread, release_events=(release_hang,))
        worker_thread.join(timeout=2.0)


def test_concurrent_worker_atomic_writes_use_unique_temp_files(tmp_path, monkeypatch):
    """Fix 4: Concurrent atomic writes from multiple threads never share temp filenames."""
    real_replace = storage_mod._atomic_replace_with_retry
    seen_tmps: List[Path] = []
    seen_lock = threading.Lock()
    barrier = threading.Barrier(6)

    def recording_replace(tmp: Path, target: Path) -> None:
        with seen_lock:
            seen_tmps.append(tmp)
        return real_replace(tmp, target)

    monkeypatch.setattr(storage_mod, "_atomic_replace_with_retry", recording_replace)
    target_file = tmp_path / "shared_state.json"
    errors: List[BaseException] = []

    def _writer(thread_idx: int) -> None:
        try:
            barrier.wait(timeout=5.0)
            for step in range(5):
                storage_mod.atomic_write_json(
                    target_file,
                    {"writer": thread_idx, "step": step},
                )
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=_writer, args=(i,)) for i in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5.0)
        assert not t.is_alive()

    assert errors == []
    assert len(seen_tmps) == 30
    assert len(set(seen_tmps)) == 30
    assert list(tmp_path.glob("*.tmp")) == []
    final_doc = json.loads(target_file.read_text(encoding="utf-8"))
    assert "writer" in final_doc and "step" in final_doc
