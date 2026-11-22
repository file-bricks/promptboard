"""Synchronization backends, offline queue, state store, and three-way merge engine.

Stage 1b implements ``NullBackend`` (mode ``"off"``, zero network calls) and
``ServerBackend`` (mode ``"server"``, stdlib ``urllib.request`` against
``prompt-sync-server``), while keeping ``FileSlotBackend`` as a stub ready for
Stage 3. Runtime dependencies remain unchanged; ``keyring`` is optional and
import-guarded with an atomic ``0600`` file fallback in the user profile.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import http.client
import inspect
import ipaddress
import json
import logging
import os
from pathlib import Path
import re
import socket
import ssl
import stat
import threading
import time
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request
import uuid

from models import LibraryItem, gen_id, item_from_dict, item_to_dict, now_iso
from storage import (
    Storage,
    _atomic_replace_with_retry,
    atomic_write_json,
    atomic_write_text,
    make_unique_tmp_path,
)

logger = logging.getLogger(__name__)

try:
    import keyring as _keyring_mod  # type: ignore[import-not-found]
except Exception:  # pragma: no cover - optional extra
    _keyring_mod = None

SYNC_MODES = ("off", "server", "file")
DEFAULT_SYNC_MODE = "off"
DEFAULT_NAMESPACE = "promptboard"
DEFAULT_SCHEMA_VERSION = "promptboard-library-v1"
DEFAULT_KIND = "item"
DEFAULT_HTTP_TIMEOUT = 10.0
DEFAULT_SHUTDOWN_HTTP_TIMEOUT = 0.8

NAMESPACE_RE = re.compile(r"\A[a-z0-9_-]{1,32}\Z")
KIND_RE = re.compile(r"\A[a-z0-9_-]{1,32}\Z")

TAILSCALE_IPV4_NET = ipaddress.ip_network("100.64.0.0/10")
TAILSCALE_IPV6_NET = ipaddress.ip_network("fd7a:115c:a1e0::/48")

FirstCouplingChoice = Literal["merge", "take_server", "cancel"]
ConflictResolutionChoice = Literal["keep_local", "keep_copy", "take_server"]
TargetChangeQueueChoice = Literal["keep", "discard"]
MutationOp = Literal["upsert", "delete"]

REDIRECT_ERROR_MESSAGE = "server answered with a redirect; refusing to follow"
REDIRECT_STATUS_CODES = frozenset({300, 301, 302, 303, 305, 306, 307, 308})


class SyncError(Exception):
    """Base error for synchronization failures."""


class SyncTransportError(SyncError):
    """Raised when transport security rules or network calls fail."""


class SyncAuthError(SyncError):
    """Raised when the sync server rejects authentication or write permissions."""


def make_object_key(kind: str, item_id: str) -> str:
    clean_kind = (kind or DEFAULT_KIND).strip() or DEFAULT_KIND
    return f"{clean_kind}:{item_id}"


def split_object_key(obj_key: str) -> Tuple[str, str]:
    if ":" in obj_key:
        kind, item_id = obj_key.split(":", 1)
        return (kind or DEFAULT_KIND, item_id)
    return (DEFAULT_KIND, obj_key)


def validate_namespace(namespace: str) -> str:
    cleaned = (namespace or "").strip()
    if not cleaned:
        return DEFAULT_NAMESPACE
    if not NAMESPACE_RE.fullmatch(cleaned):
        raise ValueError(
            f"Invalid sync namespace '{namespace}'. Expected 1..32 chars matching [a-z0-9_-]."
        )
    return cleaned


def is_loopback_host(host: str) -> bool:
    normalized = (host or "").strip().lower()
    if not normalized:
        return False
    if normalized == "localhost":
        return True
    if normalized.startswith("[") and normalized.endswith("]"):
        normalized = normalized[1:-1]
    try:
        addr = ipaddress.ip_address(normalized)
    except ValueError:
        return False
    return bool(addr.is_loopback)


def is_tailscale_host(host: str) -> bool:
    normalized = (host or "").strip().lower()
    if normalized.startswith("[") and normalized.endswith("]"):
        normalized = normalized[1:-1]
    try:
        addr = ipaddress.ip_address(normalized)
    except ValueError:
        return False
    if isinstance(addr, ipaddress.IPv4Address):
        return addr in TAILSCALE_IPV4_NET
    return addr in TAILSCALE_IPV6_NET


def validate_server_url(raw_url: str) -> str:
    """Validate server base URL and enforce transport encryption rules.

    Plain ``http://`` is strictly limited to loopback (``127.0.0.1``, ``::1``,
    ``localhost``) and private Tailscale peer addresses (``100.64.0.0/10`` or
    ``fd7a:115c:a1e0::/48``). LAN, wildcard, and public targets require ``https://``.
    """
    cleaned = (raw_url or "").strip().rstrip("/")
    if not cleaned:
        raise SyncTransportError("Server URL must not be empty.")
    parsed = urllib_parse.urlparse(cleaned)
    scheme = (parsed.scheme or "").lower()
    if scheme not in ("http", "https"):
        raise SyncTransportError("Server URL must use http:// or https://.")
    host = parsed.hostname or ""
    if not host:
        raise SyncTransportError("Server URL is missing a hostname.")
    if parsed.username or parsed.password:
        raise SyncTransportError("Credentials must not be embedded in the server URL.")
    try:
        _ = parsed.port
    except ValueError as exc:
        raise SyncTransportError("Server URL contains an invalid port.") from exc

    if scheme == "http" and not (is_loopback_host(host) or is_tailscale_host(host)):
        raise SyncTransportError(
            "Plain HTTP is only permitted for loopback (127.0.0.1 / localhost) "
            "or Tailscale addresses (100.64.0.0/10). Use https:// for other hosts."
        )
    return cleaned


def canonical_item_hash(payload: Dict[str, Any]) -> str:
    """Compute a deterministic content hash for a PromptBoard item payload."""
    item = item_from_dict(payload)
    comparable = {
        "id": item.id,
        "item_type": item.item_type.value,
        "name": item.name,
        "content": item.content,
        "category": item.category,
        "tags": list(item.tags),
        "source": item.source,
    }
    encoded = json.dumps(comparable, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Token storage (optional keyring + 0600 file fallback in user profile)
# ---------------------------------------------------------------------------


def default_token_file_path() -> Path:
    """Return a local user-profile path outside cloud-synced folders."""
    if os.name == "nt":
        base_raw = os.environ.get("LOCALAPPDATA", "").strip()
        base = Path(base_raw) if base_raw else (Path.home() / "AppData" / "Local")
        return base / "PromptBoard" / "sync_token.json"
    xdg_raw = os.environ.get("XDG_CONFIG_HOME", "").strip()
    base = Path(xdg_raw) if xdg_raw else (Path.home() / ".config")
    return base / "promptboard" / "sync_token.json"


def _write_restricted_json(target: Path, data: Dict[str, Any]) -> None:
    """Atomically write UTF-8 JSON with owner-only (0600) permissions."""
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        try:
            os.chmod(target.parent, 0o700)
        except OSError:
            pass

    tmp = make_unique_tmp_path(target)
    encoded = (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(fd, encoded)
        os.fsync(fd)
    finally:
        os.close(fd)

    try:
        os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass

    try:
        _atomic_replace_with_retry(tmp, target)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass

    try:
        os.chmod(target, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass


class TokenStorage:
    """Stores the sync bearer token via optional OS keyring or a 0600 local file."""

    SERVICE_NAME = "PromptBoard"
    ACCOUNT_NAME = "sync_api_token"

    def __init__(
        self,
        fallback_path: Optional[Path] = None,
        *,
        keyring_backend: Any = None,
    ) -> None:
        self.fallback_path = Path(fallback_path) if fallback_path is not None else default_token_file_path()
        self._keyring_override = keyring_backend
        self._lock = threading.RLock()

    def _active_keyring(self) -> Any:
        if self._keyring_override is not None:
            return self._keyring_override
        if os.environ.get("PROMPTBOARD_DISABLE_KEYRING", "").strip() in ("1", "true", "yes"):
            return None
        return _keyring_mod

    def get_token(self) -> str:
        with self._lock:
            kr = self._active_keyring()
            if kr is not None:
                try:
                    secret = kr.get_password(self.SERVICE_NAME, self.ACCOUNT_NAME)
                    if isinstance(secret, str) and secret.strip():
                        return secret.strip()
                except Exception:
                    logger.debug("Keyring lookup unavailable; using local token file fallback.")

            if not self.fallback_path.is_file():
                return ""
            try:
                raw = json.loads(self.fallback_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                logger.warning("Could not read fallback sync token file.")
                return ""
            if isinstance(raw, dict):
                token = raw.get("token", "")
                return str(token).strip() if token is not None else ""
            return ""

    def set_token(self, token: str) -> None:
        with self._lock:
            cleaned = (token or "").strip()
            if not cleaned:
                self.clear_token()
                return

            kr = self._active_keyring()
            stored_in_keyring = False
            if kr is not None:
                try:
                    kr.set_password(self.SERVICE_NAME, self.ACCOUNT_NAME, cleaned)
                    stored_in_keyring = True
                except Exception:
                    logger.debug("Keyring write failed; persisting sync token in 0600 fallback file.")

            if stored_in_keyring:
                # Remove stale plaintext file if keyring succeeded.
                try:
                    self.fallback_path.unlink(missing_ok=True)
                except OSError:
                    pass
                return

            _write_restricted_json(self.fallback_path, {"version": 1, "token": cleaned})

    def clear_token(self) -> None:
        with self._lock:
            kr = self._active_keyring()
            if kr is not None:
                try:
                    kr.delete_password(self.SERVICE_NAME, self.ACCOUNT_NAME)
                except Exception:
                    pass
            try:
                self.fallback_path.unlink(missing_ok=True)
            except OSError:
                pass

    def __repr__(self) -> str:
        return f"TokenStorage(fallback_path={str(self.fallback_path)!r}, token='***')"


# ---------------------------------------------------------------------------
# Protocol dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConnectionStatus:
    ok: bool
    latency_ms: float
    detail: str
    library_rev: Optional[int] = None
    item_count: Optional[int] = None


@dataclass(frozen=True)
class RemoteItem:
    id: str
    kind: str
    rev: int
    updated_at: str
    payload: Dict[str, Any]


@dataclass(frozen=True)
class RemoteTombstone:
    id: str
    kind: str
    rev: int
    deleted_at: str


@dataclass
class SyncMutation:
    id: str
    kind: str
    op: MutationOp
    base_rev: int
    payload: Optional[Dict[str, Any]] = None
    queued_at: str = field(default_factory=now_iso)
    mutation_id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "id": self.id,
            "kind": self.kind,
            "op": self.op,
            "base_rev": int(self.base_rev),
            "queued_at": self.queued_at,
            "mutation_id": self.mutation_id,
        }
        if self.op == "upsert" and self.payload is not None:
            data["payload"] = dict(self.payload)
        return data

    def to_wire_dict(self) -> Dict[str, Any]:
        wire: Dict[str, Any] = {
            "id": self.id,
            "kind": self.kind,
            "op": self.op,
            "base_rev": int(self.base_rev),
        }
        if self.op == "upsert" and self.payload is not None:
            wire["payload"] = dict(self.payload)
        return wire

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SyncMutation:
        op_raw = str(data.get("op", "upsert"))
        op: MutationOp = "delete" if op_raw == "delete" else "upsert"
        raw_payload = data.get("payload")
        return cls(
            id=str(data.get("id", "")).strip(),
            kind=str(data.get("kind") or DEFAULT_KIND).strip() or DEFAULT_KIND,
            op=op,
            base_rev=max(0, int(data.get("base_rev", 0) or 0)),
            payload=dict(raw_payload) if isinstance(raw_payload, dict) else None,
            queued_at=str(data.get("queued_at") or now_iso()),
            mutation_id=str(data.get("mutation_id") or uuid.uuid4().hex),
        )


@dataclass
class ConflictEntry:
    id: str
    kind: str
    title: str
    source: str
    client_base_rev: int
    server_rev: int
    updated_at: str
    local_op: MutationOp = "upsert"
    local_item: Optional[Dict[str, Any]] = None
    server_item: Optional[Dict[str, Any]] = None
    server_deleted: bool = False

    @property
    def object_key(self) -> str:
        return make_object_key(self.kind, self.id)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "title": self.title,
            "source": self.source,
            "client_base_rev": int(self.client_base_rev),
            "server_rev": int(self.server_rev),
            "updated_at": self.updated_at,
            "local_op": self.local_op,
            "local_item": dict(self.local_item) if isinstance(self.local_item, dict) else None,
            "server_item": dict(self.server_item) if isinstance(self.server_item, dict) else None,
            "server_deleted": bool(self.server_deleted),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ConflictEntry:
        local_op_raw = str(data.get("local_op", "upsert"))
        local_op: MutationOp = "delete" if local_op_raw == "delete" else "upsert"
        local_item = data.get("local_item")
        server_item = data.get("server_item")
        return cls(
            id=str(data.get("id", "")).strip(),
            kind=str(data.get("kind") or DEFAULT_KIND).strip() or DEFAULT_KIND,
            title=str(data.get("title") or data.get("id") or ""),
            source=str(data.get("source") or "server"),
            client_base_rev=max(0, int(data.get("client_base_rev", 0) or 0)),
            server_rev=max(0, int(data.get("server_rev", 0) or 0)),
            updated_at=str(data.get("updated_at") or ""),
            local_op=local_op,
            local_item=dict(local_item) if isinstance(local_item, dict) else None,
            server_item=dict(server_item) if isinstance(server_item, dict) else None,
            server_deleted=bool(data.get("server_deleted", False)),
        )


@dataclass
class PullResult:
    upserts: List[RemoteItem] = field(default_factory=list)
    tombstones: List[RemoteTombstone] = field(default_factory=list)
    conflicts: List[ConflictEntry] = field(default_factory=list)
    cursor: int = 0
    etag: str = ""
    not_modified: bool = False
    reset_required: bool = False
    offline: bool = False
    error: str = ""


@dataclass
class PushResult:
    applied_revs: Dict[str, int] = field(default_factory=dict)
    conflicts: List[ConflictEntry] = field(default_factory=list)
    queued_offline: bool = False
    library_rev: Optional[int] = None
    etag: str = ""
    error: str = ""


@dataclass
class SyncOutcome:
    ok: bool
    mode: str
    library_rev: int = 0
    pulled_upserts: int = 0
    pulled_tombstones: int = 0
    pushed_count: int = 0
    pending_queue_count: int = 0
    conflict_count: int = 0
    offline: bool = False
    cancelled: bool = False
    storage_changed: bool = False
    error: str = ""
    backup_path: str = ""
    needs_first_coupling: bool = False
    remote_item_count: int = 0
    removed_local_count: int = 0
    needs_target_queue_prompt: bool = False
    old_target: str = ""
    new_target: str = ""
    old_target_pending_count: int = 0


# ---------------------------------------------------------------------------
# SyncBackend interface and implementations
# ---------------------------------------------------------------------------


class SyncBackend(ABC):
    """Transport abstraction shared by UI, triggers, and three-way merge engine."""

    mode: str = "off"

    @abstractmethod
    def pull(
        self,
        *,
        since_rev: Optional[int] = None,
        etag: Optional[str] = None,
    ) -> PullResult:
        """Pull remote changes since ``since_rev`` (or full state when ``None``)."""

    @abstractmethod
    def push(self, changes: List[SyncMutation]) -> PushResult:
        """Push local mutations with optimistic concurrency checks."""

    @abstractmethod
    def test_connection(self) -> ConnectionStatus:
        """Probe connectivity, authentication, latency, and remote revision."""


class NullBackend(SyncBackend):
    """No-op backend used when sync mode is ``"off"``. Performs zero I/O or network calls."""

    mode = "off"

    def pull(
        self,
        *,
        since_rev: Optional[int] = None,
        etag: Optional[str] = None,
    ) -> PullResult:
        return PullResult(cursor=since_rev or 0, etag=etag or "")

    def push(self, changes: List[SyncMutation]) -> PushResult:
        return PushResult()

    def test_connection(self) -> ConnectionStatus:
        return ConnectionStatus(
            ok=False,
            latency_ms=0.0,
            detail="Sync mode is off.",
            library_rev=None,
        )


class FileSlotBackend(SyncBackend):
    """Placeholder for Stage 3 file-slot synchronization."""

    mode = "file"

    def __init__(self, sync_dir: Optional[Path] = None, host_slot: str = "") -> None:
        self.sync_dir = Path(sync_dir) if sync_dir is not None else None
        self.host_slot = host_slot

    def pull(
        self,
        *,
        since_rev: Optional[int] = None,
        etag: Optional[str] = None,
    ) -> PullResult:
        raise NotImplementedError("FileSlotBackend is scheduled for Stage 3.")

    def push(self, changes: List[SyncMutation]) -> PushResult:
        raise NotImplementedError("FileSlotBackend is scheduled for Stage 3.")

    def test_connection(self) -> ConnectionStatus:
        raise NotImplementedError("FileSlotBackend is scheduled for Stage 3.")


HttpRequester = Callable[
    [str, str, Dict[str, str], Optional[bytes], float],
    Tuple[int, Dict[str, str], bytes],
]


class _NoRedirectHandler(urllib_request.HTTPRedirectHandler):
    """Refuses all 3xx redirects so Bearer tokens are never forwarded across origins or schemes."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_SOCKET_POLL_SLICE_S = 0.05


def _shutdown_socket(sock: Any) -> None:
    """Interrupt blocking socket I/O via ``shutdown(SHUT_RDWR)`` without closing its fd.

    Safe to invoke from a foreign thread: the actual ``close()`` happens exclusively
    in the owning worker thread's ``finally`` block so the file descriptor can never
    be recycled while the worker still uses it.
    """
    if sock is None:
        return
    try:
        if isinstance(sock, ssl.SSLSocket):
            socket.socket.shutdown(sock, socket.SHUT_RDWR)
        else:
            sock.shutdown(socket.SHUT_RDWR)
    except OSError:
        pass


class _RequestAbortController:
    """Tracks in-flight HTTP sockets by epoch so shutdown can abort active network I/O."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._epoch: int = 0
        self._sockets: Dict[int, Tuple[int, Any]] = {}

    def current_epoch(self) -> int:
        with self._lock:
            return self._epoch

    def is_epoch_aborted(self, request_epoch: int) -> bool:
        with self._lock:
            return request_epoch < self._epoch

    def register_socket(self, sock: Any, request_epoch: int) -> None:
        if sock is None:
            return
        abort_now = False
        with self._lock:
            if request_epoch < self._epoch:
                abort_now = True
            else:
                self._sockets[id(sock)] = (request_epoch, sock)
        if abort_now:
            _shutdown_socket(sock)
            raise OSError("HTTP request aborted during shutdown.")

    def unregister_socket(self, sock: Any) -> None:
        if sock is None:
            return
        with self._lock:
            self._sockets.pop(id(sock), None)

    def abort_all(self) -> int:
        with self._lock:
            self._epoch += 1
            sockets = [sock for _ep, sock in self._sockets.values()]
            self._sockets.clear()
            epoch = self._epoch
        for sock in sockets:
            _shutdown_socket(sock)
        return epoch


def _open_tracked_tcp_socket(
    address: Tuple[str, int],
    timeout: Any = socket._GLOBAL_DEFAULT_TIMEOUT,
    source_address: Optional[Tuple[str, int]] = None,
    *,
    abort_controller: Optional[_RequestAbortController] = None,
    request_epoch: int = 0,
    tracked_sockets: Optional[List[Any]] = None,
    deadline: Optional[float] = None,
) -> socket.socket:
    host, port = address
    if abort_controller is not None and abort_controller.is_epoch_aborted(request_epoch):
        raise OSError("HTTP request aborted during shutdown.")
    err: Optional[OSError] = None
    infos = socket.getaddrinfo(host, port, 0, socket.SOCK_STREAM)
    if not infos:
        raise OSError("getaddrinfo returns an empty list")
    for af, socktype, proto, _canonname, sa in infos:
        sock: Optional[socket.socket] = None
        try:
            if abort_controller is not None and abort_controller.is_epoch_aborted(request_epoch):
                raise OSError("HTTP request aborted during shutdown.")
            sock = socket.socket(af, socktype, proto)
            if tracked_sockets is not None:
                tracked_sockets.append(sock)
            if abort_controller is not None:
                abort_controller.register_socket(sock, request_epoch)
            eff_timeout = timeout
            if deadline is not None:
                rem = deadline - time.monotonic()
                if rem <= 0:
                    raise TimeoutError("timed out")
                eff_timeout = rem if eff_timeout is socket._GLOBAL_DEFAULT_TIMEOUT else min(float(eff_timeout), rem)
            if eff_timeout is not socket._GLOBAL_DEFAULT_TIMEOUT:
                sock.settimeout(eff_timeout)
            if source_address:
                sock.bind(source_address)
            sock.connect(sa)
            return sock
        except OSError as exc:
            err = exc
            if sock is not None:
                if abort_controller is not None:
                    abort_controller.unregister_socket(sock)
                try:
                    sock.close()
                except OSError:
                    pass
    if err is not None:
        raise err
    raise OSError("Failed to establish TCP connection.")


def _install_abortable_reader(
    response: http.client.HTTPResponse,
    sock: Any,
    *,
    deadline: float,
    abort_controller: Optional[_RequestAbortController],
    request_epoch: int,
) -> None:
    """Wrap ``response.fp.raw.readinto`` on the owning worker thread with short poll slices.

    Ensures ``abort_all()`` (``shutdown(SHUT_RDWR)`` + epoch bump) wakes blocked reads
    promptly on every platform (including Windows/macOS ``select``/``poll``) without ever
    closing the socket descriptor from a foreign thread.
    """
    fp = getattr(response, "fp", None)
    raw = getattr(fp, "raw", None)
    if raw is None or sock is None:
        return

    def _sliced_readinto(buf: Any) -> Optional[int]:
        raw._checkClosed()
        raw._checkReadable()
        if getattr(raw, "_timeout_occurred", False):
            raise OSError("cannot read from timed out object")
        while True:
            if abort_controller is not None and abort_controller.is_epoch_aborted(request_epoch):
                raise OSError("HTTP request aborted during shutdown.")
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raw._timeout_occurred = True
                raise TimeoutError("timed out")
            try:
                sock.settimeout(min(_SOCKET_POLL_SLICE_S, remaining))
                n = sock.recv_into(buf)
                if n == 0 and abort_controller is not None and abort_controller.is_epoch_aborted(request_epoch):
                    raise OSError("HTTP request aborted during shutdown.")
                return n
            except TimeoutError:
                if abort_controller is not None and abort_controller.is_epoch_aborted(request_epoch):
                    raise OSError("HTTP request aborted during shutdown.")
                if time.monotonic() >= deadline:
                    raw._timeout_occurred = True
                    raise
                continue
            except InterruptedError:
                continue

    raw.readinto = _sliced_readinto


class _AbortableHTTPConnection(http.client.HTTPConnection):
    def __init__(
        self,
        *args: Any,
        abort_controller: Optional[_RequestAbortController] = None,
        request_epoch: int = 0,
        tracked_sockets: Optional[List[Any]] = None,
        deadline: float = 0.0,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._abort_controller = abort_controller
        self._request_epoch = request_epoch
        self._tracked_sockets = tracked_sockets
        self._deadline = deadline
        self._create_connection = self._create_tracked_connection
        self.response_class = self._make_response

    def _make_response(self, sock: Any, *args: Any, **kwargs: Any) -> http.client.HTTPResponse:
        resp = http.client.HTTPResponse(sock, *args, **kwargs)
        _install_abortable_reader(
            resp,
            sock,
            deadline=self._deadline,
            abort_controller=self._abort_controller,
            request_epoch=self._request_epoch,
        )
        return resp

    def _create_tracked_connection(
        self,
        address: Tuple[str, int],
        timeout: Any = socket._GLOBAL_DEFAULT_TIMEOUT,
        source_address: Optional[Tuple[str, int]] = None,
    ) -> socket.socket:
        return _open_tracked_tcp_socket(
            address,
            timeout,
            source_address,
            abort_controller=self._abort_controller,
            request_epoch=self._request_epoch,
            tracked_sockets=self._tracked_sockets,
            deadline=self._deadline if self._deadline > 0 else None,
        )


class _AbortableHTTPSConnection(http.client.HTTPSConnection):
    def __init__(
        self,
        *args: Any,
        abort_controller: Optional[_RequestAbortController] = None,
        request_epoch: int = 0,
        tracked_sockets: Optional[List[Any]] = None,
        deadline: float = 0.0,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._abort_controller = abort_controller
        self._request_epoch = request_epoch
        self._tracked_sockets = tracked_sockets
        self._deadline = deadline
        self._create_connection = self._create_tracked_connection
        self.response_class = self._make_response

    def _make_response(self, sock: Any, *args: Any, **kwargs: Any) -> http.client.HTTPResponse:
        resp = http.client.HTTPResponse(sock, *args, **kwargs)
        _install_abortable_reader(
            resp,
            sock,
            deadline=self._deadline,
            abort_controller=self._abort_controller,
            request_epoch=self._request_epoch,
        )
        return resp

    def _create_tracked_connection(
        self,
        address: Tuple[str, int],
        timeout: Any = socket._GLOBAL_DEFAULT_TIMEOUT,
        source_address: Optional[Tuple[str, int]] = None,
    ) -> socket.socket:
        return _open_tracked_tcp_socket(
            address,
            timeout,
            source_address,
            abort_controller=self._abort_controller,
            request_epoch=self._request_epoch,
            tracked_sockets=self._tracked_sockets,
            deadline=self._deadline if self._deadline > 0 else None,
        )

    def connect(self) -> None:
        raw_before_tls: Optional[Any] = None
        orig_create = self._create_connection

        def _capture_raw(*c_args: Any, **c_kwargs: Any) -> socket.socket:
            nonlocal raw_before_tls
            raw_before_tls = orig_create(*c_args, **c_kwargs)
            return raw_before_tls

        self._create_connection = _capture_raw
        try:
            super().connect()
        finally:
            self._create_connection = orig_create
            if raw_before_tls is not None and raw_before_tls is not self.sock:
                if self._abort_controller is not None:
                    self._abort_controller.unregister_socket(raw_before_tls)
        if self.sock is not None:
            if self._tracked_sockets is not None:
                self._tracked_sockets.append(self.sock)
            if self._abort_controller is not None:
                self._abort_controller.register_socket(self.sock, self._request_epoch)


class _AbortableHTTPHandler(urllib_request.HTTPHandler):
    def __init__(
        self,
        abort_controller: Optional[_RequestAbortController],
        request_epoch: int,
        tracked_sockets: List[Any],
        deadline: float,
    ) -> None:
        super().__init__()
        self._abort_controller = abort_controller
        self._request_epoch = request_epoch
        self._tracked_sockets = tracked_sockets
        self._deadline = deadline

    def http_open(self, req: urllib_request.Request) -> Any:
        return self.do_open(
            _AbortableHTTPConnection,
            req,
            abort_controller=self._abort_controller,
            request_epoch=self._request_epoch,
            tracked_sockets=self._tracked_sockets,
            deadline=self._deadline,
        )


class _AbortableHTTPSHandler(urllib_request.HTTPSHandler):
    def __init__(
        self,
        abort_controller: Optional[_RequestAbortController],
        request_epoch: int,
        tracked_sockets: List[Any],
        deadline: float,
        context: Optional[ssl.SSLContext] = None,
    ) -> None:
        super().__init__(context=context)
        self._abort_controller = abort_controller
        self._request_epoch = request_epoch
        self._tracked_sockets = tracked_sockets
        self._deadline = deadline

    def https_open(self, req: urllib_request.Request) -> Any:
        return self.do_open(
            _AbortableHTTPSConnection,
            req,
            context=self._context,
            abort_controller=self._abort_controller,
            request_epoch=self._request_epoch,
            tracked_sockets=self._tracked_sockets,
            deadline=self._deadline,
        )


def _read_stream_with_deadline(
    stream: Any,
    deadline: float,
    chunk_size: int = 65536,
    *,
    abort_controller: Optional[_RequestAbortController] = None,
    request_epoch: int = 0,
) -> bytes:
    chunks: List[bytes] = []
    while True:
        if abort_controller is not None and abort_controller.is_epoch_aborted(request_epoch):
            raise OSError("HTTP response read aborted during shutdown.")
        if time.monotonic() > deadline:
            raise TimeoutError("HTTP response read exceeded deadline.")
        piece = stream.read(chunk_size)
        if not piece:
            break
        chunks.append(piece)
    return b"".join(chunks)


def default_http_requester(
    method: str,
    url: str,
    headers: Dict[str, str],
    body: Optional[bytes],
    timeout: float,
    *,
    abort_controller: Optional[_RequestAbortController] = None,
) -> Tuple[int, Dict[str, str], bytes]:
    """Stdlib ``urllib.request`` transport. Disables redirects and supports socket abort."""
    request_epoch = abort_controller.current_epoch() if abort_controller is not None else 0
    if abort_controller is not None and abort_controller.is_epoch_aborted(request_epoch):
        raise urllib_error.URLError("HTTP request aborted during shutdown.")

    bounded_timeout = max(0.2, float(timeout))
    deadline = time.monotonic() + bounded_timeout

    tracked_sockets: List[Any] = []
    http_handler = _AbortableHTTPHandler(
        abort_controller, request_epoch, tracked_sockets, deadline
    )
    https_handler = _AbortableHTTPSHandler(
        abort_controller, request_epoch, tracked_sockets, deadline
    )

    parsed = urllib_parse.urlparse(url)
    host = parsed.hostname or ""
    if is_loopback_host(host) or is_tailscale_host(host):
        opener = urllib_request.build_opener(
            urllib_request.ProxyHandler({}),
            _NoRedirectHandler(),
            http_handler,
            https_handler,
        )
    else:
        opener = urllib_request.build_opener(
            _NoRedirectHandler(),
            http_handler,
            https_handler,
        )

    req_headers = dict(headers)
    if body is not None:
        req_headers.setdefault("Content-Length", str(len(body)))

    req = urllib_request.Request(url=url, data=body, headers=req_headers, method=method)
    try:
        with opener.open(req, timeout=bounded_timeout) as resp:
            status = int(getattr(resp, "status", resp.getcode()))
            resp_headers = {k.lower(): v for k, v in resp.headers.items()}
            raw = _read_stream_with_deadline(
                resp,
                deadline,
                abort_controller=abort_controller,
                request_epoch=request_epoch,
            )
            return status, resp_headers, raw
    except urllib_error.HTTPError as exc:
        try:
            raw = _read_stream_with_deadline(
                exc,
                deadline,
                abort_controller=abort_controller,
                request_epoch=request_epoch,
            )
            resp_headers = {k.lower(): v for k, v in exc.headers.items()} if exc.headers else {}
            return int(exc.code), resp_headers, raw
        finally:
            try:
                exc.close()
            except Exception:
                pass
    except http.client.HTTPException as exc:
        raise urllib_error.URLError(f"HTTP connection aborted: {exc}") from exc
    finally:
        for sock in tracked_sockets:
            if abort_controller is not None:
                abort_controller.unregister_socket(sock)
            try:
                sock.close()
            except OSError:
                pass


def _extract_title_from_payload(payload: Optional[Dict[str, Any]], fallback_id: str) -> str:
    if isinstance(payload, dict):
        for key in ("name", "title"):
            val = payload.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
    return fallback_id


class ServerBackend(SyncBackend):
    """REST client for ``prompt-sync-server`` using stdlib ``urllib.request``."""

    mode = "server"

    def __init__(
        self,
        server_url: str,
        token: str,
        *,
        namespace: str = DEFAULT_NAMESPACE,
        client_id: str = "promptboard-client",
        schema_version: str = DEFAULT_SCHEMA_VERSION,
        timeout: float = DEFAULT_HTTP_TIMEOUT,
        requester: Optional[HttpRequester] = None,
    ) -> None:
        self.raw_server_url = (server_url or "").strip()
        self._token = (token or "").strip()
        self.namespace = validate_namespace(namespace)
        self.client_id = (client_id or "promptboard-client").strip()
        self.schema_version = schema_version
        self.timeout = max(0.2, float(timeout))
        self._requester: HttpRequester = requester or default_http_requester

    def __repr__(self) -> str:
        return (
            f"ServerBackend(server_url={self.raw_server_url!r}, "
            f"namespace={self.namespace!r}, token='***')"
        )

    def _validated_base_url(self) -> str:
        url = validate_server_url(self.raw_server_url)
        if not self._token:
            raise SyncAuthError("API token is required for server synchronization.")
        return url

    def _auth_headers(self, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/json",
        }
        if extra:
            headers.update(extra)
        return headers

    @staticmethod
    def _decode_json(raw: bytes) -> Dict[str, Any]:
        if not raw:
            return {}
        decoded = json.loads(raw.decode("utf-8"))
        return decoded if isinstance(decoded, dict) else {}

    def test_connection(self) -> ConnectionStatus:
        t0 = time.perf_counter()
        try:
            base_url = self._validated_base_url()
        except SyncError as exc:
            return ConnectionStatus(ok=False, latency_ms=0.0, detail=str(exc), library_rev=None)

        url = f"{base_url}/v1/libraries"
        try:
            status, _headers, raw = self._requester(
                "GET", url, self._auth_headers(), None, self.timeout
            )
            elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 1)
        except (urllib_error.URLError, TimeoutError, ConnectionError, OSError) as exc:
            elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 1)
            return ConnectionStatus(
                ok=False,
                latency_ms=elapsed_ms,
                detail=f"Unreachable: {exc}",
                library_rev=None,
            )

        if status in REDIRECT_STATUS_CODES or (300 <= status < 400):
            return ConnectionStatus(
                ok=False,
                latency_ms=elapsed_ms,
                detail=f"HTTP {status}: {REDIRECT_ERROR_MESSAGE}",
                library_rev=None,
            )
        if status in (401, 403):
            return ConnectionStatus(
                ok=False,
                latency_ms=elapsed_ms,
                detail=f"Authentication failed (HTTP {status}).",
                library_rev=None,
            )
        if status != 200:
            return ConnectionStatus(
                ok=False,
                latency_ms=elapsed_ms,
                detail=f"Unexpected status HTTP {status}.",
                library_rev=None,
            )

        try:
            payload = self._decode_json(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            return ConnectionStatus(
                ok=False,
                latency_ms=elapsed_ms,
                detail=f"Invalid JSON response: {exc}",
                library_rev=None,
            )

        lib_rev = 0
        item_count = 0
        namespaces = payload.get("namespaces", [])
        if isinstance(namespaces, list):
            for entry in namespaces:
                if isinstance(entry, dict) and entry.get("name") == self.namespace:
                    lib_rev = int(entry.get("library_rev", 0) or 0)
                    item_count = int(entry.get("item_count", 0) or 0)
                    break

        return ConnectionStatus(
            ok=True,
            latency_ms=elapsed_ms,
            detail="OK",
            library_rev=lib_rev,
            item_count=item_count,
        )

    def pull(
        self,
        *,
        since_rev: Optional[int] = None,
        etag: Optional[str] = None,
    ) -> PullResult:
        base_url = self._validated_base_url()
        ns_quoted = urllib_parse.quote(self.namespace, safe="")
        url = f"{base_url}/v1/libraries/{ns_quoted}/changes"
        if since_rev is not None:
            url = f"{url}?since_rev={int(since_rev)}"

        extra_headers: Dict[str, str] = {}
        if etag and since_rev is not None:
            extra_headers["If-None-Match"] = etag

        try:
            status, resp_headers, raw = self._requester(
                "GET",
                url,
                self._auth_headers(extra_headers),
                None,
                self.timeout,
            )
        except (urllib_error.URLError, TimeoutError, ConnectionError, OSError) as exc:
            return PullResult(
                cursor=since_rev or 0,
                etag=etag or "",
                offline=True,
                error=str(exc),
            )

        resp_etag = resp_headers.get("etag", "") or (etag or "")

        if status == 304 and since_rev is not None and "location" not in resp_headers:
            return PullResult(
                cursor=since_rev or 0,
                etag=resp_etag,
                not_modified=True,
            )
        if status in REDIRECT_STATUS_CODES or (300 <= status < 400):
            raise SyncTransportError(f"HTTP {status}: {REDIRECT_ERROR_MESSAGE}")
        if status == 410:
            body = self._decode_json(raw)
            return PullResult(
                cursor=int(body.get("library_rev", 0) or 0),
                etag=resp_etag,
                reset_required=True,
            )
        if status in (401, 403):
            raise SyncAuthError(f"Server rejected pull authentication (HTTP {status}).")
        if status >= 500:
            return PullResult(
                cursor=since_rev or 0,
                etag=etag or "",
                offline=True,
                error=f"Server error HTTP {status}.",
            )
        if status != 200:
            raise SyncTransportError(f"Unexpected pull response HTTP {status}.")

        body = self._decode_json(raw)
        lib_rev = int(body.get("library_rev", 0) or 0)
        if not resp_etag:
            resp_etag = f'"rev-{lib_rev}"'

        upserts: List[RemoteItem] = []
        for entry in body.get("items", []) or []:
            if not isinstance(entry, dict):
                continue
            item_payload = entry.get("payload")
            if not isinstance(item_payload, dict):
                continue
            obj_id = str(entry.get("id", "")).strip()
            if not obj_id:
                continue
            upserts.append(
                RemoteItem(
                    id=obj_id,
                    kind=str(entry.get("kind") or DEFAULT_KIND).strip() or DEFAULT_KIND,
                    rev=int(entry.get("rev", 0) or 0),
                    updated_at=str(entry.get("updated_at") or ""),
                    payload=dict(item_payload),
                )
            )

        tombstones: List[RemoteTombstone] = []
        for entry in body.get("tombstones", []) or []:
            if not isinstance(entry, dict):
                continue
            obj_id = str(entry.get("id", "")).strip()
            if not obj_id:
                continue
            tombstones.append(
                RemoteTombstone(
                    id=obj_id,
                    kind=str(entry.get("kind") or DEFAULT_KIND).strip() or DEFAULT_KIND,
                    rev=int(entry.get("rev", 0) or 0),
                    deleted_at=str(entry.get("deleted_at") or ""),
                )
            )

        return PullResult(
            upserts=upserts,
            tombstones=tombstones,
            cursor=lib_rev,
            etag=resp_etag,
        )

    def push(
        self,
        changes: List[SyncMutation],
        *,
        idempotency_key: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> PushResult:
        if not changes:
            return PushResult()

        base_url = self._validated_base_url()
        ns_quoted = urllib_parse.quote(self.namespace, safe="")
        url = f"{base_url}/v1/libraries/{ns_quoted}/push"
        idem = idempotency_key or f"pb-{uuid.uuid4().hex}"

        mutation_by_key = {make_object_key(m.kind, m.id): m for m in changes}
        request_doc = {
            "client_id": self.client_id,
            "schema_version": self.schema_version,
            "mutations": [m.to_wire_dict() for m in changes],
        }
        encoded = json.dumps(request_doc, ensure_ascii=False).encode("utf-8")
        headers = self._auth_headers(
            {
                "Content-Type": "application/json; charset=utf-8",
                "Idempotency-Key": idem,
            }
        )

        effective_timeout = timeout if timeout is not None else self.timeout
        try:
            status, resp_headers, raw = self._requester(
                "POST",
                url,
                headers,
                encoded,
                effective_timeout,
            )
        except (urllib_error.URLError, TimeoutError, ConnectionError, OSError) as exc:
            return PushResult(queued_offline=True, error=str(exc))

        if status in REDIRECT_STATUS_CODES or (300 <= status < 400):
            raise SyncTransportError(f"HTTP {status}: {REDIRECT_ERROR_MESSAGE}")
        if status in (401, 403):
            raise SyncAuthError(f"Server rejected push authentication/permission (HTTP {status}).")
        if status >= 500:
            return PushResult(queued_offline=True, error=f"Server error HTTP {status}.")
        if status not in (200, 409):
            raise SyncTransportError(f"Unexpected push response HTTP {status}.")

        body = self._decode_json(raw)
        lib_rev = int(body.get("library_rev", 0) or 0)
        resp_etag = resp_headers.get("etag", "") or f'"rev-{lib_rev}"'

        applied_revs: Dict[str, int] = {}
        for app_entry in body.get("applied", []) or []:
            if not isinstance(app_entry, dict):
                continue
            obj_id = str(app_entry.get("id", "")).strip()
            kind = str(app_entry.get("kind") or DEFAULT_KIND).strip() or DEFAULT_KIND
            if obj_id:
                applied_revs[make_object_key(kind, obj_id)] = int(app_entry.get("rev", 0) or 0)

        conflicts: List[ConflictEntry] = []
        for conf in body.get("conflicts", []) or []:
            if not isinstance(conf, dict):
                continue
            obj_id = str(conf.get("id", "")).strip()
            if not obj_id:
                continue
            kind = str(conf.get("kind") or DEFAULT_KIND).strip() or DEFAULT_KIND
            key = make_object_key(kind, obj_id)
            local_mut = mutation_by_key.get(key)
            server_obj = conf.get("server_item")
            server_deleted = False
            server_payload: Optional[Dict[str, Any]] = None
            updated_at = ""
            if isinstance(server_obj, dict):
                server_deleted = bool(server_obj.get("deleted", False))
                updated_at = str(server_obj.get("deleted_at") or server_obj.get("updated_at") or "")
                raw_srv_payload = server_obj.get("payload")
                if isinstance(raw_srv_payload, dict) and not server_deleted:
                    server_payload = dict(raw_srv_payload)

            local_payload = local_mut.payload if local_mut is not None else None
            title = _extract_title_from_payload(
                local_payload or server_payload,
                fallback_id=obj_id,
            )
            conflicts.append(
                ConflictEntry(
                    id=obj_id,
                    kind=kind,
                    title=title,
                    source="server",
                    client_base_rev=int(conf.get("client_base_rev", 0) or 0),
                    server_rev=int(conf.get("server_rev", 0) or 0),
                    updated_at=updated_at,
                    local_op=local_mut.op if local_mut is not None else "upsert",
                    local_item=dict(local_payload) if isinstance(local_payload, dict) else None,
                    server_item=server_payload,
                    server_deleted=server_deleted,
                )
            )

        return PushResult(
            applied_revs=applied_revs,
            conflicts=conflicts,
            queued_offline=False,
            library_rev=lib_rev,
            etag=resp_etag,
        )


# ---------------------------------------------------------------------------
# Local sync state & offline queue persistence (atomic JSON in app data_dir)
# ---------------------------------------------------------------------------


def format_coupling_target(server_url: str, namespace: str) -> str:
    raw_url = (server_url or "").strip().rstrip("/")
    try:
        ns = validate_namespace(namespace)
    except ValueError:
        ns = (namespace or "").strip() or DEFAULT_NAMESPACE
    return f"{raw_url}|{ns}"


def _invoke_first_coupling_callback(
    callback: Callable[..., FirstCouplingChoice],
    remote_count: int,
    remote_rev: int,
    removed_local_count: int,
) -> FirstCouplingChoice:
    try:
        sig = inspect.signature(callback)
        params = list(sig.parameters.values())
        accepts_varargs = any(p.kind == inspect.Parameter.VAR_POSITIONAL for p in params)
        positional_params = [
            p
            for p in params
            if p.kind
            in (
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
            )
        ]
        if accepts_varargs or len(positional_params) >= 3:
            return callback(remote_count, remote_rev, removed_local_count)
    except (TypeError, ValueError):
        pass
    return callback(remote_count, remote_rev)


@dataclass
class SyncStateData:
    mode: str = DEFAULT_SYNC_MODE
    client_id: str = field(default_factory=lambda: f"pb-{uuid.uuid4().hex[:12]}")
    active_target: str = ""
    coupled_targets: List[str] = field(default_factory=list)
    library_rev: int = 0
    etag: str = ""
    item_revs: Dict[str, int] = field(default_factory=dict)
    item_hashes: Dict[str, str] = field(default_factory=dict)
    deleted_ids: List[str] = field(default_factory=list)
    conflicts: List[ConflictEntry] = field(default_factory=list)
    target_snapshots: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": 2,
            "mode": self.mode,
            "client_id": self.client_id,
            "active_target": self.active_target,
            "coupled_targets": list(self.coupled_targets),
            "library_rev": int(self.library_rev),
            "etag": self.etag,
            "item_revs": {str(k): int(v) for k, v in self.item_revs.items()},
            "item_hashes": {str(k): str(v) for k, v in self.item_hashes.items()},
            "deleted_ids": list(self.deleted_ids),
            "conflicts": [c.to_dict() for c in self.conflicts],
            "target_snapshots": dict(self.target_snapshots),
        }

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> SyncStateData:
        revs_raw = raw.get("item_revs")
        hashes_raw = raw.get("item_hashes")
        conflicts_raw = raw.get("conflicts")
        coupled_raw = raw.get("coupled_targets")
        deleted_raw = raw.get("deleted_ids")
        snapshots_raw = raw.get("target_snapshots")
        coupled_list = (
            [str(x) for x in coupled_raw if isinstance(x, str)]
            if isinstance(coupled_raw, list)
            else []
        )
        active_target = str(raw.get("active_target") or "")
        if not active_target and len(coupled_list) == 1:
            active_target = coupled_list[0]
        return cls(
            mode=str(raw.get("mode") or DEFAULT_SYNC_MODE),
            client_id=str(raw.get("client_id") or f"pb-{uuid.uuid4().hex[:12]}"),
            active_target=active_target,
            coupled_targets=coupled_list,
            library_rev=max(0, int(raw.get("library_rev", 0) or 0)),
            etag=str(raw.get("etag") or ""),
            item_revs=(
                {
                    (k if ":" in str(k) else make_object_key(DEFAULT_KIND, str(k))): int(v)
                    for k, v in revs_raw.items()
                    if v is not None
                }
                if isinstance(revs_raw, dict)
                else {}
            ),
            item_hashes=(
                {
                    (k if ":" in str(k) else make_object_key(DEFAULT_KIND, str(k))): str(v)
                    for k, v in hashes_raw.items()
                    if isinstance(v, str)
                }
                if isinstance(hashes_raw, dict)
                else {}
            ),
            deleted_ids=(
                [str(x) for x in deleted_raw if isinstance(x, str)]
                if isinstance(deleted_raw, list)
                else []
            ),
            conflicts=(
                [ConflictEntry.from_dict(c) for c in conflicts_raw if isinstance(c, dict)]
                if isinstance(conflicts_raw, list)
                else []
            ),
            target_snapshots=(
                {str(k): dict(v) for k, v in snapshots_raw.items() if isinstance(v, dict)}
                if isinstance(snapshots_raw, dict)
                else {}
            ),
        )


class SyncStateStore:
    """Atomic reader/writer for ``sync_state.json`` inside the app data directory."""

    FILENAME = "sync_state.json"

    def __init__(
        self,
        data_dir: Path,
        *,
        lock: Optional[threading.RLock] = None,
    ) -> None:
        self.data_dir = Path(data_dir)
        self.path = self.data_dir / self.FILENAME
        self._lock = lock if lock is not None else threading.RLock()

    def load(self) -> SyncStateData:
        with self._lock:
            if not self.path.is_file():
                return SyncStateData()
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                logger.warning(
                    "Could not parse sync_state.json (%s); starting with fresh state.", exc
                )
                return SyncStateData()
            if not isinstance(raw, dict):
                return SyncStateData()
            return SyncStateData.from_dict(raw)

    def save(self, state: SyncStateData) -> None:
        with self._lock:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            atomic_write_json(self.path, state.to_dict())


class OfflineQueue:
    """Compacting target-bound offline mutation queue stored atomically in ``sync_queue.json``."""

    FILENAME = "sync_queue.json"

    def __init__(
        self,
        data_dir: Path,
        *,
        lock: Optional[threading.RLock] = None,
    ) -> None:
        self.data_dir = Path(data_dir)
        self.path = self.data_dir / self.FILENAME
        self._lock = lock if lock is not None else threading.RLock()

    def _read_store(self) -> Tuple[str, Dict[str, List[SyncMutation]]]:
        if not self.path.is_file():
            return "", {}
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Could not parse sync_queue.json (%s); resetting queue.", exc)
            return "", {}
        if not isinstance(raw, dict):
            return "", {}

        active_target = str(raw.get("active_target") or "")
        queues_by_target: Dict[str, List[SyncMutation]] = {}
        raw_map = raw.get("queues_by_target")
        if isinstance(raw_map, dict):
            for tgt, entries in raw_map.items():
                if not isinstance(entries, list):
                    continue
                parsed: List[SyncMutation] = []
                for entry in entries:
                    if isinstance(entry, dict) and entry.get("id"):
                        parsed.append(SyncMutation.from_dict(entry))
                if parsed:
                    queues_by_target[str(tgt)] = parsed
            return active_target, queues_by_target

        # Legacy v1 migration: top-level ``mutations`` list.
        entries = raw.get("mutations", [])
        if isinstance(entries, list):
            parsed = [
                SyncMutation.from_dict(entry)
                for entry in entries
                if isinstance(entry, dict) and entry.get("id")
            ]
            if parsed:
                queues_by_target[active_target] = parsed
        return active_target, queues_by_target

    def _write_store(
        self,
        active_target: str,
        queues_by_target: Dict[str, List[SyncMutation]],
    ) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        serialized_map = {
            str(tgt): [m.to_dict() for m in muts]
            for tgt, muts in queues_by_target.items()
            if muts
        }
        active_list = serialized_map.get(active_target, [])
        atomic_write_json(
            self.path,
            {
                "schema_version": 2,
                "active_target": active_target,
                "mutations": active_list,
                "queues_by_target": serialized_map,
            },
        )

    def set_active_target(self, target: str) -> None:
        with self._lock:
            active_target, queues = self._read_store()
            if active_target == target and not (not self.path.exists() and not queues):
                if self.path.exists():
                    return
                return
            if queues or self.path.exists():
                self._write_store(target, queues)

    def pending_targets(self) -> Dict[str, int]:
        with self._lock:
            _active, queues = self._read_store()
            return {tgt: len(muts) for tgt, muts in queues.items() if muts}

    def load_all(self, *, target: Optional[str] = None) -> List[SyncMutation]:
        with self._lock:
            active_target, queues = self._read_store()
            eff_target = active_target if target is None else target
            return list(queues.get(eff_target, []))

    def save_all(
        self,
        mutations: List[SyncMutation],
        *,
        target: Optional[str] = None,
    ) -> None:
        with self._lock:
            active_target, queues = self._read_store()
            eff_target = active_target if target is None else target
            if target is not None:
                active_target = target
            if mutations:
                queues[eff_target] = list(mutations)
            else:
                queues.pop(eff_target, None)
            self._write_store(active_target, queues)

    def enqueue_upsert(
        self,
        item: LibraryItem,
        *,
        known_base_rev: int,
        kind: str = DEFAULT_KIND,
        target: Optional[str] = None,
    ) -> List[SyncMutation]:
        with self._lock:
            active_target, queues = self._read_store()
            eff_target = active_target if target is None else target
            if target is not None:
                active_target = target
            mutations = list(queues.get(eff_target, []))
            target_key = make_object_key(kind, item.id)
            payload = item_to_dict(item)
            for idx, existing in enumerate(mutations):
                if make_object_key(existing.kind, existing.id) == target_key:
                    mutations[idx] = SyncMutation(
                        id=item.id,
                        kind=kind,
                        op="upsert",
                        base_rev=existing.base_rev,
                        payload=payload,
                    )
                    queues[eff_target] = mutations
                    self._write_store(active_target, queues)
                    return list(mutations)

            mutations.append(
                SyncMutation(
                    id=item.id,
                    kind=kind,
                    op="upsert",
                    base_rev=max(0, int(known_base_rev)),
                    payload=payload,
                )
            )
            queues[eff_target] = mutations
            self._write_store(active_target, queues)
            return list(mutations)

    def enqueue_delete(
        self,
        item_id: str,
        *,
        known_base_rev: int,
        kind: str = DEFAULT_KIND,
        target: Optional[str] = None,
    ) -> List[SyncMutation]:
        with self._lock:
            active_target, queues = self._read_store()
            eff_target = active_target if target is None else target
            if target is not None:
                active_target = target
            mutations = list(queues.get(eff_target, []))
            target_key = make_object_key(kind, item_id)
            for idx, existing in enumerate(mutations):
                if make_object_key(existing.kind, existing.id) == target_key:
                    if existing.base_rev == 0:
                        # Item was created offline and deleted before ever reaching the server.
                        del mutations[idx]
                    else:
                        mutations[idx] = SyncMutation(
                            id=item_id,
                            kind=kind,
                            op="delete",
                            base_rev=existing.base_rev,
                            payload=None,
                        )
                    if mutations:
                        queues[eff_target] = mutations
                    else:
                        queues.pop(eff_target, None)
                    self._write_store(active_target, queues)
                    return list(mutations)

            if known_base_rev > 0:
                mutations.append(
                    SyncMutation(
                        id=item_id,
                        kind=kind,
                        op="delete",
                        base_rev=int(known_base_rev),
                        payload=None,
                    )
                )
                queues[eff_target] = mutations
                self._write_store(active_target, queues)
            return list(mutations)

    def remove_keys(
        self,
        keys: set[str],
        *,
        target: Optional[str] = None,
        expected_mutation_ids: Optional[Dict[str, str]] = None,
        applied_revs: Optional[Dict[str, int]] = None,
    ) -> List[SyncMutation]:
        with self._lock:
            active_target, queues = self._read_store()
            eff_target = active_target if target is None else target
            current = list(queues.get(eff_target, []))
            if not keys:
                return current
            remaining: List[SyncMutation] = []
            for m in current:
                obj_key = make_object_key(m.kind, m.id)
                if obj_key not in keys:
                    remaining.append(m)
                    continue
                if (
                    expected_mutation_ids is not None
                    and obj_key in expected_mutation_ids
                    and m.mutation_id != expected_mutation_ids[obj_key]
                ):
                    # A newer edit arrived while the previous mutation was in flight.
                    if applied_revs is not None and obj_key in applied_revs:
                        m = SyncMutation(
                            id=m.id,
                            kind=m.kind,
                            op=m.op,
                            base_rev=max(0, int(applied_revs[obj_key])),
                            payload=dict(m.payload) if isinstance(m.payload, dict) else None,
                            queued_at=m.queued_at,
                            mutation_id=m.mutation_id,
                        )
                    remaining.append(m)
            if remaining:
                queues[eff_target] = remaining
            else:
                queues.pop(eff_target, None)
            self._write_store(active_target, queues)
            return list(remaining)

    def clear(self, *, target: Optional[str] = None) -> None:
        with self._lock:
            if not self.path.exists():
                return
            if target is None:
                self._write_store("", {})
                return
            active_target, queues = self._read_store()
            queues.pop(target, None)
            self._write_store(active_target, queues)


# ---------------------------------------------------------------------------
# Three-way merge & synchronization engine
# ---------------------------------------------------------------------------


def create_sync_backend(
    mode: str,
    *,
    server_url: str = "",
    token: str = "",
    namespace: str = DEFAULT_NAMESPACE,
    client_id: str = "promptboard-client",
    requester: Optional[HttpRequester] = None,
) -> SyncBackend:
    normalized = (mode or DEFAULT_SYNC_MODE).strip().lower()
    if normalized == "off" or not normalized:
        return NullBackend()
    if normalized == "server":
        return ServerBackend(
            server_url=server_url,
            token=token,
            namespace=namespace,
            client_id=client_id,
            requester=requester,
        )
    if normalized == "file":
        return FileSlotBackend()
    return NullBackend()


class SyncEngine:
    """Coordinates ``Storage``, ``SyncStateStore``, ``OfflineQueue``, and ``SyncBackend``.

    Lock hierarchy (acquired strictly in this order, never held across network I/O
    or interactive callbacks):
      1. ``_engine_lock`` — local snapshot/apply coordination in sync/flush/resolve
      2. ``storage._lock`` — atomic read-modify-write across ``load_items``..``save_items``
      3. ``_state_lock`` — ``SyncStateStore`` & active-target metadata transitions
      4. ``queue._lock`` — ``OfflineQueue`` compaction and persistence
    """

    def __init__(
        self,
        storage: Storage,
        settings: Any,
        *,
        requester: Optional[HttpRequester] = None,
    ) -> None:
        self.storage = storage
        self.settings = settings
        self._state_lock = threading.RLock()
        self.state_store = SyncStateStore(storage.data_dir, lock=self._state_lock)
        self.queue = OfflineQueue(storage.data_dir)
        self._custom_requester = requester
        self._abort_controller = _RequestAbortController()
        self._cancel_event = threading.Event()
        self._shutting_down = False
        self._shutdown_timeout = DEFAULT_SHUTDOWN_HTTP_TIMEOUT
        self._requester: HttpRequester = self._dispatch_http_request
        self._engine_lock = threading.RLock()

    @property
    def cancel_event(self) -> threading.Event:
        return self._cancel_event

    def is_cancelled(self) -> bool:
        return self._cancel_event.is_set()

    def begin_shutdown(
        self,
        *,
        request_timeout: float = DEFAULT_SHUTDOWN_HTTP_TIMEOUT,
    ) -> None:
        """Signal workers to cancel, clamp future request timeouts (<= 1 s), and abort active sockets."""
        self._shutdown_timeout = min(1.0, max(0.2, float(request_timeout)))
        self._shutting_down = True
        self._cancel_event.set()
        self._abort_controller.abort_all()

    def abort_active_requests(self) -> None:
        """Abort currently running HTTP request sockets via ``shutdown(SHUT_RDWR)``."""
        self._abort_controller.abort_all()

    def _dispatch_http_request(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        body: Optional[bytes],
        timeout: float,
    ) -> Tuple[int, Dict[str, str], bytes]:
        effective_timeout = float(timeout)
        if self._shutting_down:
            effective_timeout = min(effective_timeout, self._shutdown_timeout)
        if self._custom_requester is not None:
            return self._custom_requester(method, url, headers, body, effective_timeout)
        return default_http_requester(
            method,
            url,
            headers,
            body,
            effective_timeout,
            abort_controller=self._abort_controller,
        )

    def current_mode(self) -> str:
        raw = self.settings.get_sync_mode()
        return raw if raw in SYNC_MODES else DEFAULT_SYNC_MODE

    def is_configured(self) -> bool:
        if self.current_mode() != "server":
            return False
        return bool(
            self.settings.get_sync_server_url().strip() and self.settings.get_sync_token().strip()
        )

    def target_coupling_id(self) -> str:
        return format_coupling_target(
            self.settings.get_sync_server_url(),
            self.settings.get_sync_namespace(),
        )

    def _effective_queue_target(self, state: Optional[SyncStateData] = None) -> Optional[str]:
        raw_url = self.settings.get_sync_server_url().strip()
        if raw_url:
            return self.target_coupling_id()
        loaded = state if state is not None else self.state_store.load()
        if loaded.active_target:
            return loaded.active_target
        return None

    @staticmethod
    def _snapshot_from_state(state: SyncStateData) -> Dict[str, Any]:
        return {
            "library_rev": int(state.library_rev),
            "etag": state.etag,
            "item_revs": dict(state.item_revs),
            "item_hashes": dict(state.item_hashes),
            "conflicts": [c.to_dict() for c in state.conflicts],
        }

    @staticmethod
    def _restore_snapshot_into_state(
        state: SyncStateData,
        snapshot: Optional[Dict[str, Any]],
    ) -> None:
        if not isinstance(snapshot, dict):
            state.library_rev = 0
            state.etag = ""
            state.item_revs = {}
            state.item_hashes = {}
            state.conflicts = []
            return
        state.library_rev = max(0, int(snapshot.get("library_rev", 0) or 0))
        state.etag = str(snapshot.get("etag") or "")
        revs_raw = snapshot.get("item_revs")
        hashes_raw = snapshot.get("item_hashes")
        conflicts_raw = snapshot.get("conflicts")
        state.item_revs = (
            {str(k): int(v) for k, v in revs_raw.items() if v is not None}
            if isinstance(revs_raw, dict)
            else {}
        )
        state.item_hashes = (
            {str(k): str(v) for k, v in hashes_raw.items() if isinstance(v, str)}
            if isinstance(hashes_raw, dict)
            else {}
        )
        state.conflicts = (
            [ConflictEntry.from_dict(c) for c in conflicts_raw if isinstance(c, dict)]
            if isinstance(conflicts_raw, list)
            else []
        )

    def _resolve_previous_target(self, state: SyncStateData, new_target: str) -> str:
        if state.active_target and state.active_target != new_target:
            return state.active_target
        # Fallback if legacy state had no active_target recorded yet.
        pending_map = self.queue.pending_targets()
        for tgt in pending_map:
            if tgt and tgt != new_target:
                return tgt
        return ""

    def inspect_pending_target_change(
        self,
        *,
        new_url: Optional[str] = None,
        new_namespace: Optional[str] = None,
    ) -> Optional[Tuple[str, str, int]]:
        """Return ``(old_target, new_target, pending_count)`` when switching away from a non-empty queue."""
        with self._state_lock:
            eff_url = new_url if new_url is not None else self.settings.get_sync_server_url()
            if not (eff_url or "").strip():
                return None
            eff_ns = (
                new_namespace
                if new_namespace is not None
                else self.settings.get_sync_namespace()
            )
            new_target = format_coupling_target(eff_url, eff_ns)
            state = self.state_store.load()
            old_target = self._resolve_previous_target(state, new_target)
            if not old_target or old_target == new_target:
                return None
            pending_count = len(self.queue.load_all(target=old_target))
            if pending_count <= 0:
                return None
            return (old_target, new_target, pending_count)

    def apply_target_change(
        self,
        choice: TargetChangeQueueChoice = "keep",
        *,
        new_target: Optional[str] = None,
    ) -> None:
        """Switch active coupling target while preserving or discarding the previous target's queue."""
        with self._state_lock:
            resolved_new = new_target if new_target is not None else self.target_coupling_id()
            state = self.state_store.load()
            old_target = self._resolve_previous_target(state, resolved_new)
            if old_target and old_target != resolved_new:
                state.target_snapshots[old_target] = self._snapshot_from_state(state)
                if choice == "discard":
                    self.queue.clear(target=old_target)
                self._restore_snapshot_into_state(
                    state,
                    state.target_snapshots.get(resolved_new),
                )
            state.active_target = resolved_new
            self.state_store.save(state)
            self.queue.set_active_target(resolved_new)

    def _write_library_backup(self, current_items: List[LibraryItem]) -> Path:
        """Write an atomic timestamped backup of ``library.json`` next to it before destructive replace."""
        lib_file = self.storage.library_file
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup_path = lib_file.parent / f"library.backup-{stamp}.json"
        counter = 1
        while backup_path.exists():
            backup_path = lib_file.parent / f"library.backup-{stamp}-{counter}.json"
            counter += 1

        if lib_file.is_file():
            raw_content = lib_file.read_text(encoding="utf-8-sig")
            atomic_write_text(backup_path, raw_content, encoding="utf-8")
        else:
            atomic_write_json(
                backup_path,
                {"items": [item_to_dict(it) for it in current_items]},
            )
        return backup_path

    def build_backend(self, *, client_id: Optional[str] = None) -> SyncBackend:
        mode = self.current_mode()
        if mode == "off":
            return NullBackend()
        resolved_client_id = client_id or self.state_store.load().client_id
        return create_sync_backend(
            mode,
            server_url=self.settings.get_sync_server_url(),
            token=self.settings.get_sync_token(),
            namespace=self.settings.get_sync_namespace(),
            client_id=resolved_client_id,
            requester=self._requester,
        )

    def test_connection(
        self,
        *,
        mode: Optional[str] = None,
        server_url: Optional[str] = None,
        token: Optional[str] = None,
        namespace: Optional[str] = None,
    ) -> ConnectionStatus:
        effective_mode = mode if mode is not None else self.current_mode()
        if effective_mode == "off":
            return NullBackend().test_connection()
        state = self.state_store.load()
        try:
            backend = create_sync_backend(
                effective_mode,
                server_url=server_url if server_url is not None else self.settings.get_sync_server_url(),
                token=token if token is not None else self.settings.get_sync_token(),
                namespace=namespace if namespace is not None else self.settings.get_sync_namespace(),
                client_id=state.client_id,
                requester=self._requester,
            )
        except ValueError as exc:
            return ConnectionStatus(ok=False, latency_ms=0.0, detail=str(exc), library_rev=None)
        return backend.test_connection()

    def get_conflicts(self) -> List[ConflictEntry]:
        return list(self.state_store.load().conflicts)

    def get_pending_count(self, *, target: Optional[str] = None) -> int:
        eff_target = target if target is not None else self._effective_queue_target()
        return len(self.queue.load_all(target=eff_target))

    def get_library_rev(self) -> int:
        return self.state_store.load().library_rev

    def _base_rev_for_target(self, state: SyncStateData, target: Optional[str], key: str) -> int:
        if not target or not state.active_target or state.active_target == target:
            return state.item_revs.get(key, 0)
        snap = state.target_snapshots.get(target)
        if isinstance(snap, dict) and isinstance(snap.get("item_revs"), dict):
            return int(snap["item_revs"].get(key, 0) or 0)
        return 0

    def enqueue_upsert(self, item: LibraryItem, *, kind: str = DEFAULT_KIND) -> None:
        if self.current_mode() != "server":
            return
        with self._state_lock:
            state = self.state_store.load()
            target = self._effective_queue_target(state)
            if target and not state.active_target:
                state.active_target = target
                self.state_store.save(state)
            key = make_object_key(kind, item.id)
            base_rev = self._base_rev_for_target(state, target, key)
            self.queue.enqueue_upsert(item, known_base_rev=base_rev, kind=kind, target=target)

    def enqueue_delete(self, item_id: str, *, kind: str = DEFAULT_KIND) -> None:
        if self.current_mode() != "server":
            return
        with self._state_lock:
            state = self.state_store.load()
            target = self._effective_queue_target(state)
            if target and not state.active_target:
                state.active_target = target
                self.state_store.save(state)
            key = make_object_key(kind, item_id)
            base_rev = self._base_rev_for_target(state, target, key)
            self.queue.enqueue_delete(item_id, known_base_rev=base_rev, kind=kind, target=target)

    @staticmethod
    def _upsert_conflict(conflicts: List[ConflictEntry], new_entry: ConflictEntry) -> None:
        for idx, existing in enumerate(conflicts):
            if existing.object_key == new_entry.object_key:
                conflicts[idx] = new_entry
                return
        conflicts.append(new_entry)

    def _detect_unqueued_local_changes(
        self,
        state: SyncStateData,
        local_by_id: Dict[str, LibraryItem],
        *,
        target: str,
    ) -> None:
        """Queue items added or modified locally outside live editor hooks (e.g., while mode was off)."""
        queued_keys = {make_object_key(m.kind, m.id) for m in self.queue.load_all(target=target)}
        conflict_keys = {c.object_key for c in state.conflicts}

        for item_id, item in local_by_id.items():
            key = make_object_key(DEFAULT_KIND, item_id)
            if key in queued_keys or key in conflict_keys:
                continue
            current_hash = canonical_item_hash(item_to_dict(item))
            recorded_hash = state.item_hashes.get(key)
            if key not in state.item_revs:
                self.queue.enqueue_upsert(
                    item, known_base_rev=0, kind=DEFAULT_KIND, target=target
                )
            elif recorded_hash and current_hash != recorded_hash:
                self.queue.enqueue_upsert(
                    item,
                    known_base_rev=state.item_revs.get(key, 0),
                    kind=DEFAULT_KIND,
                    target=target,
                )

    def _is_locally_modified(
        self,
        key: str,
        local_item: Optional[LibraryItem],
        state: SyncStateData,
        queued_by_key: Dict[str, SyncMutation],
    ) -> bool:
        if key in queued_by_key:
            return True
        if local_item is None:
            return False
        recorded_hash = state.item_hashes.get(key)
        if not recorded_hash:
            return True
        return canonical_item_hash(item_to_dict(local_item)) != recorded_hash

    def _reconcile_pull(
        self,
        pull_res: PullResult,
        state: SyncStateData,
        *,
        target: str,
        full_snapshot: bool = False,
    ) -> Tuple[int, int, bool]:
        """Apply remote upserts and tombstones using three-way conflict detection.

        Holds ``self.storage._lock`` continuously from ``load_items`` through
        ``save_items`` with zero network I/O inside the critical section.
        """
        with self.storage._lock:
            local_items = self.storage.load_items()
            local_by_id: Dict[str, LibraryItem] = {item.id: item for item in local_items}
            queued_by_key = {
                make_object_key(m.kind, m.id): m for m in self.queue.load_all(target=target)
            }
            keys_to_unqueue: set[str] = set()
            storage_changed = False
            applied_upserts = 0
            applied_tombstones = 0

            seen_remote_keys: set[str] = set()

            for remote in pull_res.upserts:
                key = make_object_key(remote.kind, remote.id)
                seen_remote_keys.add(key)
                if remote.kind != DEFAULT_KIND:
                    state.item_revs[key] = remote.rev
                    continue

                remote_item = item_from_dict(remote.payload)
                remote_dict = item_to_dict(remote_item)
                remote_hash = canonical_item_hash(remote_dict)

                local_existing = local_by_id.get(remote.id)
                queued_mut = queued_by_key.get(key)
                locally_dirty = self._is_locally_modified(key, local_existing, state, queued_by_key)

                if not locally_dirty:
                    local_by_id[remote.id] = remote_item
                    state.item_revs[key] = remote.rev
                    state.item_hashes[key] = remote_hash
                    storage_changed = True
                    applied_upserts += 1
                    continue

                # Local has uncommitted edits or a pending delete.
                if local_existing is not None and (queued_mut is None or queued_mut.op == "upsert"):
                    local_dict = item_to_dict(local_existing)
                    if canonical_item_hash(local_dict) == remote_hash:
                        # Convergent edit: identical content on both sides.
                        state.item_revs[key] = remote.rev
                        state.item_hashes[key] = remote_hash
                        keys_to_unqueue.add(key)
                        continue
                    self._upsert_conflict(
                        state.conflicts,
                        ConflictEntry(
                            id=remote.id,
                            kind=remote.kind,
                            title=local_existing.name or remote_item.name,
                            source="server",
                            client_base_rev=state.item_revs.get(key, 0),
                            server_rev=remote.rev,
                            updated_at=remote.updated_at,
                            local_op="upsert",
                            local_item=local_dict,
                            server_item=remote_dict,
                            server_deleted=False,
                        ),
                    )
                    keys_to_unqueue.add(key)
                else:
                    # Local deleted the item while server updated it.
                    self._upsert_conflict(
                        state.conflicts,
                        ConflictEntry(
                            id=remote.id,
                            kind=remote.kind,
                            title=remote_item.name,
                            source="server",
                            client_base_rev=state.item_revs.get(key, 0),
                            server_rev=remote.rev,
                            updated_at=remote.updated_at,
                            local_op="delete",
                            local_item=None,
                            server_item=remote_dict,
                            server_deleted=False,
                        ),
                    )
                    keys_to_unqueue.add(key)

            for tomb in pull_res.tombstones:
                key = make_object_key(tomb.kind, tomb.id)
                seen_remote_keys.add(key)
                if tomb.kind != DEFAULT_KIND:
                    state.item_revs.pop(key, None)
                    state.item_hashes.pop(key, None)
                    continue

                local_existing = local_by_id.get(tomb.id)
                queued_mut = queued_by_key.get(key)
                if local_existing is None:
                    state.item_revs.pop(key, None)
                    state.item_hashes.pop(key, None)
                    keys_to_unqueue.add(key)
                    continue

                locally_dirty = self._is_locally_modified(key, local_existing, state, queued_by_key)
                if not locally_dirty or (queued_mut is not None and queued_mut.op == "delete"):
                    local_by_id.pop(tomb.id, None)
                    state.item_revs.pop(key, None)
                    state.item_hashes.pop(key, None)
                    keys_to_unqueue.add(key)
                    storage_changed = True
                    applied_tombstones += 1
                else:
                    # Server deleted the object, but local modified it since base_rev -> conflict!
                    self._upsert_conflict(
                        state.conflicts,
                        ConflictEntry(
                            id=tomb.id,
                            kind=tomb.kind,
                            title=local_existing.name,
                            source="server",
                            client_base_rev=state.item_revs.get(key, 0),
                            server_rev=tomb.rev,
                            updated_at=tomb.deleted_at,
                            local_op="upsert",
                            local_item=item_to_dict(local_existing),
                            server_item=None,
                            server_deleted=True,
                        ),
                    )
                    keys_to_unqueue.add(key)

            if full_snapshot:
                # Reconcile previously tracked items whose tombstones were compacted away (410 reset).
                for tracked_key in list(state.item_revs.keys()):
                    kind, obj_id = split_object_key(tracked_key)
                    if kind != DEFAULT_KIND or tracked_key in seen_remote_keys:
                        continue
                    local_existing = local_by_id.get(obj_id)
                    if local_existing is None:
                        state.item_revs.pop(tracked_key, None)
                        state.item_hashes.pop(tracked_key, None)
                        continue
                    if not self._is_locally_modified(tracked_key, local_existing, state, queued_by_key):
                        local_by_id.pop(obj_id, None)
                        state.item_revs.pop(tracked_key, None)
                        state.item_hashes.pop(tracked_key, None)
                        storage_changed = True
                        applied_tombstones += 1
                    else:
                        self._upsert_conflict(
                            state.conflicts,
                            ConflictEntry(
                                id=obj_id,
                                kind=kind,
                                title=local_existing.name,
                                source="server",
                                client_base_rev=state.item_revs.get(tracked_key, 0),
                                server_rev=0,
                                updated_at=now_iso(),
                                local_op="upsert",
                                local_item=item_to_dict(local_existing),
                                server_item=None,
                                server_deleted=True,
                            ),
                        )
                        keys_to_unqueue.add(tracked_key)

            if keys_to_unqueue:
                expected_ids = {
                    k: queued_by_key[k].mutation_id for k in keys_to_unqueue if k in queued_by_key
                }
                self.queue.remove_keys(
                    keys_to_unqueue,
                    target=target,
                    expected_mutation_ids=expected_ids,
                )

            if storage_changed:
                self.storage.save_items(list(local_by_id.values()))

            state.library_rev = pull_res.cursor
            state.etag = pull_res.etag
            return applied_upserts, applied_tombstones, storage_changed

    def _apply_push_result(
        self,
        pending_sent: List[SyncMutation],
        push_res: PushResult,
        state: SyncStateData,
        *,
        target: str,
        target_switched: bool = False,
    ) -> int:
        """Apply a completed network ``PushResult`` to ``state`` and ``OfflineQueue`` under lock."""
        resolved_keys: set[str] = set()
        pending_by_key = {make_object_key(m.kind, m.id): m for m in pending_sent}
        expected_ids = {k: m.mutation_id for k, m in pending_by_key.items()}

        if not target_switched:
            item_revs = state.item_revs
            item_hashes = state.item_hashes
            conflicts = state.conflicts
            snap: Dict[str, Any] = {}
        else:
            snap = dict(state.target_snapshots.get(target) or {})
            raw_revs = snap.get("item_revs")
            raw_hashes = snap.get("item_hashes")
            raw_confs = snap.get("conflicts")
            item_revs = (
                {str(k): int(v) for k, v in raw_revs.items() if v is not None}
                if isinstance(raw_revs, dict)
                else {}
            )
            item_hashes = (
                {str(k): str(v) for k, v in raw_hashes.items() if isinstance(v, str)}
                if isinstance(raw_hashes, dict)
                else {}
            )
            conflicts = (
                [ConflictEntry.from_dict(c) for c in raw_confs if isinstance(c, dict)]
                if isinstance(raw_confs, list)
                else []
            )

        for key, new_rev in push_res.applied_revs.items():
            resolved_keys.add(key)
            mut = pending_by_key.get(key)
            if mut is not None and mut.op == "delete":
                item_revs.pop(key, None)
                item_hashes.pop(key, None)
            else:
                item_revs[key] = new_rev
                if mut is not None and mut.payload is not None:
                    item_hashes[key] = canonical_item_hash(mut.payload)

        for conf in push_res.conflicts:
            resolved_keys.add(conf.object_key)
            if conf.local_op == "delete" and conf.server_deleted:
                item_revs.pop(conf.object_key, None)
                item_hashes.pop(conf.object_key, None)
                continue
            if (
                conf.local_op == "upsert"
                and not conf.server_deleted
                and conf.local_item is not None
                and conf.server_item is not None
                and canonical_item_hash(conf.local_item) == canonical_item_hash(conf.server_item)
            ):
                item_revs[conf.object_key] = conf.server_rev
                item_hashes[conf.object_key] = canonical_item_hash(conf.server_item)
                continue
            self._upsert_conflict(conflicts, conf)

        self.queue.remove_keys(
            resolved_keys,
            target=target,
            expected_mutation_ids=expected_ids,
            applied_revs=push_res.applied_revs,
        )

        if not target_switched:
            if push_res.library_rev is not None and push_res.library_rev > state.library_rev:
                state.library_rev = push_res.library_rev
                state.etag = push_res.etag
        else:
            snap_rev = max(0, int(snap.get("library_rev", 0) or 0))
            snap_etag = str(snap.get("etag") or "")
            if push_res.library_rev is not None and push_res.library_rev > snap_rev:
                snap_rev = push_res.library_rev
                snap_etag = push_res.etag
            state.target_snapshots[target] = {
                "library_rev": snap_rev,
                "etag": snap_etag,
                "item_revs": item_revs,
                "item_hashes": item_hashes,
                "conflicts": [c.to_dict() for c in conflicts],
            }

        return len(push_res.applied_revs)

    @staticmethod
    def _upsert_in_item_list(items: List[LibraryItem], new_item: LibraryItem) -> None:
        idx = next((i for i, existing in enumerate(items) if existing.id == new_item.id), -1)
        if idx >= 0:
            items[idx] = new_item
        else:
            items.append(new_item)

    def _record_sync_error_outcome(
        self,
        *,
        mode: str,
        coupling_id: str,
        error_msg: str,
    ) -> SyncOutcome:
        with self._engine_lock, self._state_lock:
            live_state = self.state_store.load()
            if not (live_state.active_target and live_state.active_target != coupling_id):
                live_state.target_snapshots[coupling_id] = self._snapshot_from_state(live_state)
                self.state_store.save(live_state)
            return SyncOutcome(
                ok=False,
                mode=mode,
                library_rev=live_state.library_rev,
                pending_queue_count=self.get_pending_count(target=coupling_id),
                conflict_count=len(live_state.conflicts),
                error=error_msg,
            )

    def sync_once(
        self,
        *,
        on_first_coupling: Optional[Callable[..., FirstCouplingChoice]] = None,
        on_target_change_queue: Optional[
            Callable[[str, str, int], TargetChangeQueueChoice]
        ] = None,
        defer_first_coupling_prompt: bool = False,
        first_coupling_choice: Optional[FirstCouplingChoice] = None,
        defer_target_change_prompt: bool = False,
        target_change_choice: Optional[TargetChangeQueueChoice] = None,
    ) -> SyncOutcome:
        """Execute a complete sync cycle without holding any lock across network I/O."""
        mode = self.current_mode()
        if mode == "off":
            return SyncOutcome(ok=True, mode="off")
        if mode == "file":
            raise NotImplementedError("FileSlotBackend is scheduled for Stage 3.")
        if not self.is_configured():
            return SyncOutcome(
                ok=False,
                mode=mode,
                pending_queue_count=self.get_pending_count(),
                conflict_count=len(self.get_conflicts()),
                error="Sync server URL and API token are required.",
            )
        if self.is_cancelled():
            return SyncOutcome(ok=False, mode=mode, cancelled=True)

        coupling_id = self.target_coupling_id()

        # Step 0: Snapshot/resolve target binding under lock; ask prompt callback outside locks.
        prompt_target_args: Optional[Tuple[str, str, int]] = None
        with self._engine_lock, self._state_lock:
            state = self.state_store.load()
            old_target = self._resolve_previous_target(state, coupling_id)
            if old_target and old_target != coupling_id:
                old_pending = self.queue.load_all(target=old_target)
                if old_pending and defer_target_change_prompt and target_change_choice is None:
                    return SyncOutcome(
                        ok=False,
                        mode=mode,
                        needs_target_queue_prompt=True,
                        old_target=old_target,
                        new_target=coupling_id,
                        old_target_pending_count=len(old_pending),
                    )
                if (
                    target_change_choice is None
                    and old_pending
                    and on_target_change_queue is not None
                ):
                    prompt_target_args = (old_target, coupling_id, len(old_pending))

        resolved_target_choice: Optional[TargetChangeQueueChoice] = target_change_choice
        if prompt_target_args is not None and on_target_change_queue is not None:
            resolved_target_choice = on_target_change_queue(*prompt_target_args)

        try:
            with self._engine_lock, self._state_lock:
                state = self.state_store.load()
                state.mode = mode
                old_target = self._resolve_previous_target(state, coupling_id)
                if old_target and old_target != coupling_id:
                    q_choice: TargetChangeQueueChoice = (
                        resolved_target_choice if resolved_target_choice is not None else "keep"
                    )
                    state.target_snapshots[old_target] = self._snapshot_from_state(state)
                    if q_choice == "discard":
                        self.queue.clear(target=old_target)
                    self._restore_snapshot_into_state(
                        state,
                        state.target_snapshots.get(coupling_id),
                    )
                state.active_target = coupling_id
                self.queue.set_active_target(coupling_id)
                self.state_store.save(state)
                is_coupled = coupling_id in state.coupled_targets
                backend = self.build_backend(client_id=state.client_id)
                assert isinstance(backend, ServerBackend)

            # Step 1: First-time coupling handling if not yet coupled to this target.
            if not is_coupled:
                if self.is_cancelled():
                    return SyncOutcome(ok=False, mode=mode, cancelled=True)
                initial_pull = backend.pull(since_rev=None)
                if self.is_cancelled():
                    return SyncOutcome(
                        ok=False,
                        mode=mode,
                        offline=initial_pull.offline,
                        cancelled=True,
                        error=initial_pull.error,
                    )
                if initial_pull.offline:
                    with self._engine_lock, self._state_lock:
                        live_state = self.state_store.load()
                        if not (live_state.active_target and live_state.active_target != coupling_id):
                            self.state_store.save(live_state)
                        return SyncOutcome(
                            ok=False,
                            mode=mode,
                            library_rev=live_state.library_rev,
                            pending_queue_count=self.get_pending_count(target=coupling_id),
                            conflict_count=len(live_state.conflicts),
                            offline=True,
                            error=initial_pull.error,
                        )

                remote_count = len(initial_pull.upserts)
                choice: FirstCouplingChoice = "merge"
                if first_coupling_choice is not None:
                    choice = first_coupling_choice
                elif remote_count > 0 and (
                    defer_first_coupling_prompt or on_first_coupling is not None
                ):
                    with self.storage._lock:
                        preview_local_items = self.storage.load_items()
                    remote_item_ids = {
                        r.id for r in initial_pull.upserts if r.kind == DEFAULT_KIND
                    }
                    removed_local_count = sum(
                        1 for it in preview_local_items if it.id not in remote_item_ids
                    )
                    if defer_first_coupling_prompt:
                        return SyncOutcome(
                            ok=False,
                            mode=mode,
                            library_rev=initial_pull.cursor,
                            needs_first_coupling=True,
                            remote_item_count=remote_count,
                            removed_local_count=removed_local_count,
                        )
                    assert on_first_coupling is not None
                    choice = _invoke_first_coupling_callback(
                        on_first_coupling,
                        remote_count,
                        initial_pull.cursor,
                        removed_local_count,
                    )

                if choice == "cancel":
                    with self._state_lock:
                        live_state = self.state_store.load()
                        return SyncOutcome(
                            ok=False,
                            mode=mode,
                            cancelled=True,
                            pending_queue_count=self.get_pending_count(target=coupling_id),
                            conflict_count=len(live_state.conflicts),
                        )

                if choice == "take_server":
                    adopted_items: List[LibraryItem] = []
                    new_revs: Dict[str, int] = {}
                    new_hashes: Dict[str, str] = {}
                    for remote in initial_pull.upserts:
                        key = make_object_key(remote.kind, remote.id)
                        new_revs[key] = remote.rev
                        if remote.kind == DEFAULT_KIND:
                            lib_item = item_from_dict(remote.payload)
                            adopted_items.append(lib_item)
                            new_hashes[key] = canonical_item_hash(item_to_dict(lib_item))

                    with self._engine_lock, self.storage._lock, self._state_lock:
                        live_state = self.state_store.load()
                        if (
                            live_state.active_target and live_state.active_target != coupling_id
                        ) or self.current_mode() != "server":
                            return SyncOutcome(
                                ok=False, mode=self.current_mode(), cancelled=True
                            )
                        current_local_items = self.storage.load_items()
                        backup_path = self._write_library_backup(current_local_items)
                        self.queue.clear(target=coupling_id)
                        live_state.conflicts.clear()
                        live_state.item_revs = new_revs
                        live_state.item_hashes = new_hashes
                        self.storage.save_items(adopted_items)
                        live_state.library_rev = initial_pull.cursor
                        live_state.etag = initial_pull.etag
                        if coupling_id not in live_state.coupled_targets:
                            live_state.coupled_targets.append(coupling_id)
                        live_state.target_snapshots[coupling_id] = self._snapshot_from_state(
                            live_state
                        )
                        self.state_store.save(live_state)
                        final_rev = live_state.library_rev

                    return SyncOutcome(
                        ok=True,
                        mode=mode,
                        library_rev=final_rev,
                        pulled_upserts=len(adopted_items),
                        storage_changed=True,
                        backup_path=str(backup_path),
                    )

                # Default non-destructive "merge": reconcile local+remote under lock, then push outside lock.
                with self._engine_lock, self.storage._lock, self._state_lock:
                    live_state = self.state_store.load()
                    if (
                        live_state.active_target and live_state.active_target != coupling_id
                    ) or self.current_mode() != "server":
                        return SyncOutcome(ok=False, mode=self.current_mode(), cancelled=True)
                    local_items = {it.id: it for it in self.storage.load_items()}
                    self._detect_unqueued_local_changes(
                        live_state, local_items, target=coupling_id
                    )
                    upserts_applied, tombs_applied, changed = self._reconcile_pull(
                        initial_pull,
                        live_state,
                        target=coupling_id,
                        full_snapshot=False,
                    )
                    live_state.target_snapshots[coupling_id] = self._snapshot_from_state(
                        live_state
                    )
                    self.state_store.save(live_state)
                    pending_to_push = self.queue.load_all(target=coupling_id)

                if self.is_cancelled():
                    return SyncOutcome(
                        ok=False,
                        mode=mode,
                        pulled_upserts=upserts_applied,
                        pulled_tombstones=tombs_applied,
                        pending_queue_count=self.get_pending_count(target=coupling_id),
                        conflict_count=len(self.get_conflicts()),
                        cancelled=True,
                        storage_changed=changed,
                    )

                push_res = backend.push(pending_to_push) if pending_to_push else PushResult()

                with self._engine_lock, self._state_lock:
                    live_state = self.state_store.load()
                    target_switched = bool(
                        live_state.active_target and live_state.active_target != coupling_id
                    )
                    pushed_count = 0
                    offline_push = push_res.queued_offline
                    push_err = push_res.error
                    if pending_to_push and not offline_push:
                        pushed_count = self._apply_push_result(
                            pending_to_push,
                            push_res,
                            live_state,
                            target=coupling_id,
                            target_switched=target_switched,
                        )
                    if not offline_push and not target_switched:
                        if coupling_id not in live_state.coupled_targets:
                            live_state.coupled_targets.append(coupling_id)
                        live_state.target_snapshots[coupling_id] = self._snapshot_from_state(
                            live_state
                        )
                    self.state_store.save(live_state)
                    return SyncOutcome(
                        ok=not offline_push,
                        mode=mode,
                        library_rev=live_state.library_rev,
                        pulled_upserts=upserts_applied,
                        pulled_tombstones=tombs_applied,
                        pushed_count=pushed_count,
                        pending_queue_count=self.get_pending_count(target=coupling_id),
                        conflict_count=len(live_state.conflicts),
                        offline=offline_push,
                        storage_changed=changed,
                        error=push_err,
                    )

            # Step 2: Coupled steady-state sync (snapshot queue -> unlocked push -> unlocked pull -> locked merge).
            with self._engine_lock, self.storage._lock, self._state_lock:
                live_state = self.state_store.load()
                if (
                    live_state.active_target and live_state.active_target != coupling_id
                ) or self.current_mode() != "server":
                    return SyncOutcome(ok=False, mode=self.current_mode(), cancelled=True)
                local_by_id = {it.id: it for it in self.storage.load_items()}
                self._detect_unqueued_local_changes(live_state, local_by_id, target=coupling_id)
                pending_to_push = self.queue.load_all(target=coupling_id)

            pushed_count = 0
            if pending_to_push:
                if self.is_cancelled():
                    return SyncOutcome(
                        ok=False,
                        mode=mode,
                        pending_queue_count=self.get_pending_count(target=coupling_id),
                        conflict_count=len(self.get_conflicts()),
                        cancelled=True,
                    )
                push_res = backend.push(pending_to_push)
                with self._engine_lock, self._state_lock:
                    live_state = self.state_store.load()
                    target_switched = bool(
                        live_state.active_target and live_state.active_target != coupling_id
                    )
                    if push_res.queued_offline:
                        if not target_switched:
                            live_state.target_snapshots[coupling_id] = (
                                self._snapshot_from_state(live_state)
                            )
                            self.state_store.save(live_state)
                        return SyncOutcome(
                            ok=False,
                            mode=mode,
                            library_rev=live_state.library_rev,
                            pushed_count=0,
                            pending_queue_count=self.get_pending_count(target=coupling_id),
                            conflict_count=len(live_state.conflicts),
                            offline=True,
                            cancelled=self.is_cancelled(),
                            error=push_res.error,
                        )
                    pushed_count = self._apply_push_result(
                        pending_to_push,
                        push_res,
                        live_state,
                        target=coupling_id,
                        target_switched=target_switched,
                    )
                    if not target_switched:
                        live_state.target_snapshots[coupling_id] = self._snapshot_from_state(
                            live_state
                        )
                    self.state_store.save(live_state)
                    if (
                        target_switched
                        or self.current_mode() != "server"
                        or self.is_cancelled()
                    ):
                        return SyncOutcome(
                            ok=False,
                            mode=self.current_mode(),
                            library_rev=live_state.library_rev,
                            pushed_count=pushed_count,
                            pending_queue_count=self.get_pending_count(target=coupling_id),
                            conflict_count=len(live_state.conflicts),
                            cancelled=True,
                        )
                    pull_since_rev = live_state.library_rev
                    pull_etag = live_state.etag or None
            else:
                with self._state_lock:
                    live_state = self.state_store.load()
                    if (
                        live_state.active_target and live_state.active_target != coupling_id
                    ) or self.current_mode() != "server":
                        return SyncOutcome(ok=False, mode=self.current_mode(), cancelled=True)
                    pull_since_rev = live_state.library_rev
                    pull_etag = live_state.etag or None

            if self.is_cancelled():
                return SyncOutcome(
                    ok=False,
                    mode=mode,
                    pushed_count=pushed_count,
                    cancelled=True,
                )

            pull_res = backend.pull(since_rev=pull_since_rev, etag=pull_etag)
            if self.is_cancelled():
                return SyncOutcome(
                    ok=False,
                    mode=mode,
                    pushed_count=pushed_count,
                    offline=pull_res.offline,
                    cancelled=True,
                    error=pull_res.error,
                )
            full_snapshot = False
            if pull_res.reset_required:
                pull_res = backend.pull(since_rev=None)
                if self.is_cancelled():
                    return SyncOutcome(
                        ok=False,
                        mode=mode,
                        pushed_count=pushed_count,
                        offline=pull_res.offline,
                        cancelled=True,
                        error=pull_res.error,
                    )
                full_snapshot = True

            if pull_res.offline:
                with self._engine_lock, self._state_lock:
                    live_state = self.state_store.load()
                    if not (
                        live_state.active_target and live_state.active_target != coupling_id
                    ):
                        live_state.target_snapshots[coupling_id] = self._snapshot_from_state(
                            live_state
                        )
                        self.state_store.save(live_state)
                    return SyncOutcome(
                        ok=False,
                        mode=mode,
                        library_rev=live_state.library_rev,
                        pushed_count=pushed_count,
                        pending_queue_count=self.get_pending_count(target=coupling_id),
                        conflict_count=len(live_state.conflicts),
                        offline=True,
                        error=pull_res.error,
                    )

            with self._engine_lock, self.storage._lock, self._state_lock:
                live_state = self.state_store.load()
                if (
                    live_state.active_target and live_state.active_target != coupling_id
                ) or self.current_mode() != "server":
                    return SyncOutcome(ok=False, mode=self.current_mode(), cancelled=True)
                upserts_applied = 0
                tombs_applied = 0
                changed = False
                if not pull_res.not_modified:
                    upserts_applied, tombs_applied, changed = self._reconcile_pull(
                        pull_res,
                        live_state,
                        target=coupling_id,
                        full_snapshot=full_snapshot,
                    )
                live_state.target_snapshots[coupling_id] = self._snapshot_from_state(live_state)
                self.state_store.save(live_state)
                return SyncOutcome(
                    ok=True,
                    mode=mode,
                    library_rev=live_state.library_rev,
                    pulled_upserts=upserts_applied,
                    pulled_tombstones=tombs_applied,
                    pushed_count=pushed_count,
                    pending_queue_count=self.get_pending_count(target=coupling_id),
                    conflict_count=len(live_state.conflicts),
                    storage_changed=changed,
                )
        except SyncError as exc:
            return self._record_sync_error_outcome(
                mode=mode,
                coupling_id=coupling_id,
                error_msg=str(exc),
            )

    def flush_pending(self, *, timeout: float = 2.0) -> PushResult:
        """Best-effort push of pending queue mutations for the active target without holding locks across I/O."""
        if self.current_mode() != "server" or not self.is_configured():
            return PushResult()
        with self._engine_lock, self._state_lock:
            coupling_id = self.target_coupling_id()
            state = self.state_store.load()
            pending = self.queue.load_all(target=coupling_id)
            if not pending:
                return PushResult()
            try:
                backend = self.build_backend(client_id=state.client_id)
                assert isinstance(backend, ServerBackend)
            except SyncError as exc:
                return PushResult(queued_offline=True, error=str(exc))

        try:
            push_res = backend.push(pending, timeout=timeout)
        except SyncError as exc:
            return PushResult(queued_offline=True, error=str(exc))

        if push_res.queued_offline:
            return push_res

        with self._engine_lock, self._state_lock:
            live_state = self.state_store.load()
            target_switched = bool(
                live_state.active_target and live_state.active_target != coupling_id
            )
            pushed_count = self._apply_push_result(
                pending,
                push_res,
                live_state,
                target=coupling_id,
                target_switched=target_switched,
            )
            if not target_switched:
                live_state.target_snapshots[coupling_id] = self._snapshot_from_state(live_state)
            self.state_store.save(live_state)
            return PushResult(
                applied_revs={} if pushed_count == 0 else {"_count": pushed_count},
                conflicts=list(live_state.conflicts),
                queued_offline=False,
                library_rev=live_state.library_rev,
                error=push_res.error,
            )

    def resolve_conflict(
        self,
        item_id: str,
        resolution: ConflictResolutionChoice,
        *,
        kind: str = DEFAULT_KIND,
        copy_suffix: str = "LOCAL COPY",
        push: bool = True,
    ) -> Optional[LibraryItem]:
        """Resolve a recorded three-way conflict atomically under ``storage._lock``, then optionally push unlocked."""
        pending_to_push: List[SyncMutation] = []
        backend: Optional[SyncBackend] = None
        eff_target: Optional[str] = None

        with self._engine_lock, self.storage._lock, self._state_lock:
            state = self.state_store.load()
            eff_target = state.active_target or self._effective_queue_target(state)
            target_key = make_object_key(kind, item_id)
            conflict = next((c for c in state.conflicts if c.object_key == target_key), None)
            if conflict is None:
                return None

            state.conflicts = [c for c in state.conflicts if c.object_key != target_key]
            created_copy: Optional[LibraryItem] = None
            items = self.storage.load_items()

            if resolution == "keep_local":
                if conflict.local_op == "delete" or conflict.local_item is None:
                    items = [it for it in items if it.id != conflict.id]
                    self.queue.remove_keys({target_key}, target=eff_target)
                    if conflict.server_rev > 0 and not conflict.server_deleted:
                        self.queue.enqueue_delete(
                            conflict.id,
                            known_base_rev=conflict.server_rev,
                            kind=conflict.kind,
                            target=eff_target,
                        )
                    else:
                        state.item_revs.pop(target_key, None)
                        state.item_hashes.pop(target_key, None)
                else:
                    local_obj = item_from_dict(conflict.local_item)
                    local_obj.updated_at = now_iso()
                    self._upsert_in_item_list(items, local_obj)
                    state.item_revs[target_key] = conflict.server_rev
                    self.queue.remove_keys({target_key}, target=eff_target)
                    self.queue.enqueue_upsert(
                        local_obj,
                        known_base_rev=conflict.server_rev,
                        kind=conflict.kind,
                        target=eff_target,
                    )

            elif resolution == "keep_copy":
                # 1) Apply canonical server version to the original ID.
                self.queue.remove_keys({target_key}, target=eff_target)
                if conflict.server_deleted or conflict.server_item is None:
                    items = [it for it in items if it.id != conflict.id]
                    state.item_revs.pop(target_key, None)
                    state.item_hashes.pop(target_key, None)
                else:
                    srv_obj = item_from_dict(conflict.server_item)
                    self._upsert_in_item_list(items, srv_obj)
                    state.item_revs[target_key] = conflict.server_rev
                    state.item_hashes[target_key] = canonical_item_hash(item_to_dict(srv_obj))

                # 2) Preserve local content as a new independent LibraryItem.
                if conflict.local_item is not None:
                    src_local = item_from_dict(conflict.local_item)
                    ts = now_iso()
                    created_copy = LibraryItem(
                        id=gen_id(),
                        item_type=src_local.item_type,
                        name=f"{src_local.name} ({copy_suffix})",
                        content=src_local.content,
                        category=src_local.category,
                        tags=list(src_local.tags),
                        source=src_local.source,
                        created_at=ts,
                        updated_at=ts,
                    )
                    self._upsert_in_item_list(items, created_copy)
                    self.queue.enqueue_upsert(
                        created_copy,
                        known_base_rev=0,
                        kind=DEFAULT_KIND,
                        target=eff_target,
                    )

            elif resolution == "take_server":
                self.queue.remove_keys({target_key}, target=eff_target)
                if conflict.server_deleted or conflict.server_item is None:
                    items = [it for it in items if it.id != conflict.id]
                    state.item_revs.pop(target_key, None)
                    state.item_hashes.pop(target_key, None)
                else:
                    srv_obj = item_from_dict(conflict.server_item)
                    self._upsert_in_item_list(items, srv_obj)
                    state.item_revs[target_key] = conflict.server_rev
                    state.item_hashes[target_key] = canonical_item_hash(item_to_dict(srv_obj))
            else:
                raise ValueError(f"Unsupported conflict resolution '{resolution}'.")

            self.storage.save_items(items)
            if eff_target:
                state.target_snapshots[eff_target] = self._snapshot_from_state(state)
            self.state_store.save(state)

            if (
                push
                and not self.is_cancelled()
                and eff_target
                and self.current_mode() == "server"
                and self.is_configured()
                and eff_target == self.target_coupling_id()
            ):
                pending_to_push = self.queue.load_all(target=eff_target)
                if pending_to_push:
                    try:
                        backend = self.build_backend(client_id=state.client_id)
                    except SyncError:
                        backend = None

        if push and not self.is_cancelled() and pending_to_push and isinstance(backend, ServerBackend) and eff_target:
            try:
                push_res = backend.push(pending_to_push)
                if not push_res.queued_offline:
                    with self._engine_lock, self._state_lock:
                        live_state = self.state_store.load()
                        target_switched = bool(
                            live_state.active_target and live_state.active_target != eff_target
                        )
                        self._apply_push_result(
                            pending_to_push,
                            push_res,
                            live_state,
                            target=eff_target,
                            target_switched=target_switched,
                        )
                        if not target_switched:
                            live_state.target_snapshots[eff_target] = self._snapshot_from_state(
                                live_state
                            )
                        self.state_store.save(live_state)
            except SyncError:
                pass
        return created_copy
