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
import hashlib
import ipaddress
import json
import logging
import os
from pathlib import Path
import re
import stat
import time
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request
import uuid

from models import LibraryItem, gen_id, item_from_dict, item_to_dict, now_iso
from storage import Storage, _atomic_replace_with_retry, atomic_write_json

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

NAMESPACE_RE = re.compile(r"\A[a-z0-9_-]{1,32}\Z")
KIND_RE = re.compile(r"\A[a-z0-9_-]{1,32}\Z")

TAILSCALE_IPV4_NET = ipaddress.ip_network("100.64.0.0/10")
TAILSCALE_IPV6_NET = ipaddress.ip_network("fd7a:115c:a1e0::/48")

FirstCouplingChoice = Literal["merge", "take_server", "cancel"]
ConflictResolutionChoice = Literal["keep_local", "keep_copy", "take_server"]
MutationOp = Literal["upsert", "delete"]


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

    tmp = target.parent / f".{target.name}.{os.getpid()}.{uuid.uuid4().hex[:8]}.tmp"
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

    def _active_keyring(self) -> Any:
        if self._keyring_override is not None:
            return self._keyring_override
        if os.environ.get("PROMPTBOARD_DISABLE_KEYRING", "").strip() in ("1", "true", "yes"):
            return None
        return _keyring_mod

    def get_token(self) -> str:
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

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "id": self.id,
            "kind": self.kind,
            "op": self.op,
            "base_rev": int(self.base_rev),
            "queued_at": self.queued_at,
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


def default_http_requester(
    method: str,
    url: str,
    headers: Dict[str, str],
    body: Optional[bytes],
    timeout: float,
) -> Tuple[int, Dict[str, str], bytes]:
    """Stdlib ``urllib.request`` transport. Bypasses system proxies for loopback/Tailscale."""
    parsed = urllib_parse.urlparse(url)
    host = parsed.hostname or ""
    if is_loopback_host(host) or is_tailscale_host(host):
        opener = urllib_request.build_opener(urllib_request.ProxyHandler({}))
    else:
        opener = urllib_request.build_opener()

    req_headers = dict(headers)
    if body is not None:
        req_headers.setdefault("Content-Length", str(len(body)))

    req = urllib_request.Request(url=url, data=body, headers=req_headers, method=method)
    try:
        with opener.open(req, timeout=timeout) as resp:
            status = int(getattr(resp, "status", resp.getcode()))
            resp_headers = {k.lower(): v for k, v in resp.headers.items()}
            raw = resp.read()
            return status, resp_headers, raw
    except urllib_error.HTTPError as exc:
        try:
            raw = exc.read()
            resp_headers = {k.lower(): v for k, v in exc.headers.items()} if exc.headers else {}
            return int(exc.code), resp_headers, raw
        finally:
            try:
                exc.close()
            except Exception:
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
        self.timeout = max(0.5, float(timeout))
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

        if status == 304:
            return PullResult(
                cursor=since_rev or 0,
                etag=resp_etag,
                not_modified=True,
            )
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


@dataclass
class SyncStateData:
    mode: str = DEFAULT_SYNC_MODE
    client_id: str = field(default_factory=lambda: f"pb-{uuid.uuid4().hex[:12]}")
    coupled_targets: List[str] = field(default_factory=list)
    library_rev: int = 0
    etag: str = ""
    item_revs: Dict[str, int] = field(default_factory=dict)
    item_hashes: Dict[str, str] = field(default_factory=dict)
    deleted_ids: List[str] = field(default_factory=list)
    conflicts: List[ConflictEntry] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": 1,
            "mode": self.mode,
            "client_id": self.client_id,
            "coupled_targets": list(self.coupled_targets),
            "library_rev": int(self.library_rev),
            "etag": self.etag,
            "item_revs": {str(k): int(v) for k, v in self.item_revs.items()},
            "item_hashes": {str(k): str(v) for k, v in self.item_hashes.items()},
            "deleted_ids": list(self.deleted_ids),
            "conflicts": [c.to_dict() for c in self.conflicts],
        }

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> SyncStateData:
        revs_raw = raw.get("item_revs")
        hashes_raw = raw.get("item_hashes")
        conflicts_raw = raw.get("conflicts")
        coupled_raw = raw.get("coupled_targets")
        deleted_raw = raw.get("deleted_ids")
        return cls(
            mode=str(raw.get("mode") or DEFAULT_SYNC_MODE),
            client_id=str(raw.get("client_id") or f"pb-{uuid.uuid4().hex[:12]}"),
            coupled_targets=(
                [str(x) for x in coupled_raw if isinstance(x, str)]
                if isinstance(coupled_raw, list)
                else []
            ),
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
        )


class SyncStateStore:
    """Atomic reader/writer for ``sync_state.json`` inside the app data directory."""

    FILENAME = "sync_state.json"

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = Path(data_dir)
        self.path = self.data_dir / self.FILENAME

    def load(self) -> SyncStateData:
        if not self.path.is_file():
            return SyncStateData()
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Could not parse sync_state.json (%s); starting with fresh state.", exc)
            return SyncStateData()
        if not isinstance(raw, dict):
            return SyncStateData()
        return SyncStateData.from_dict(raw)

    def save(self, state: SyncStateData) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self.path, state.to_dict())


class OfflineQueue:
    """Compacting offline mutation queue stored atomically in ``sync_queue.json``."""

    FILENAME = "sync_queue.json"

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = Path(data_dir)
        self.path = self.data_dir / self.FILENAME

    def load_all(self) -> List[SyncMutation]:
        if not self.path.is_file():
            return []
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Could not parse sync_queue.json (%s); resetting queue.", exc)
            return []
        entries = raw.get("mutations", []) if isinstance(raw, dict) else []
        if not isinstance(entries, list):
            return []
        loaded: List[SyncMutation] = []
        for entry in entries:
            if isinstance(entry, dict) and entry.get("id"):
                loaded.append(SyncMutation.from_dict(entry))
        return loaded

    def save_all(self, mutations: List[SyncMutation]) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_json(
            self.path,
            {
                "schema_version": 1,
                "mutations": [m.to_dict() for m in mutations],
            },
        )

    def enqueue_upsert(
        self,
        item: LibraryItem,
        *,
        known_base_rev: int,
        kind: str = DEFAULT_KIND,
    ) -> List[SyncMutation]:
        mutations = self.load_all()
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
                self.save_all(mutations)
                return mutations

        mutations.append(
            SyncMutation(
                id=item.id,
                kind=kind,
                op="upsert",
                base_rev=max(0, int(known_base_rev)),
                payload=payload,
            )
        )
        self.save_all(mutations)
        return mutations

    def enqueue_delete(
        self,
        item_id: str,
        *,
        known_base_rev: int,
        kind: str = DEFAULT_KIND,
    ) -> List[SyncMutation]:
        mutations = self.load_all()
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
                self.save_all(mutations)
                return mutations

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
            self.save_all(mutations)
        return mutations

    def remove_keys(self, keys: set[str]) -> List[SyncMutation]:
        if not keys:
            return self.load_all()
        remaining = [
            m for m in self.load_all() if make_object_key(m.kind, m.id) not in keys
        ]
        self.save_all(remaining)
        return remaining

    def clear(self) -> None:
        if self.path.exists():
            self.save_all([])


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
    """Coordinates ``Storage``, ``SyncStateStore``, ``OfflineQueue``, and ``SyncBackend``."""

    def __init__(
        self,
        storage: Storage,
        settings: Any,
        *,
        requester: Optional[HttpRequester] = None,
    ) -> None:
        self.storage = storage
        self.settings = settings
        self.state_store = SyncStateStore(storage.data_dir)
        self.queue = OfflineQueue(storage.data_dir)
        self._requester = requester

    def current_mode(self) -> str:
        raw = self.settings.get_sync_mode()
        return raw if raw in SYNC_MODES else DEFAULT_SYNC_MODE

    def is_configured(self) -> bool:
        if self.current_mode() != "server":
            return False
        return bool(self.settings.get_sync_server_url().strip() and self.settings.get_sync_token().strip())

    def target_coupling_id(self) -> str:
        raw_url = self.settings.get_sync_server_url().strip().rstrip("/")
        ns = self.settings.get_sync_namespace()
        return f"{raw_url}|{ns}"

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

    def get_pending_count(self) -> int:
        return len(self.queue.load_all())

    def get_library_rev(self) -> int:
        return self.state_store.load().library_rev

    def enqueue_upsert(self, item: LibraryItem, *, kind: str = DEFAULT_KIND) -> None:
        if self.current_mode() != "server":
            return
        state = self.state_store.load()
        key = make_object_key(kind, item.id)
        base_rev = state.item_revs.get(key, 0)
        self.queue.enqueue_upsert(item, known_base_rev=base_rev, kind=kind)

    def enqueue_delete(self, item_id: str, *, kind: str = DEFAULT_KIND) -> None:
        if self.current_mode() != "server":
            return
        state = self.state_store.load()
        key = make_object_key(kind, item_id)
        base_rev = state.item_revs.get(key, 0)
        self.queue.enqueue_delete(item_id, known_base_rev=base_rev, kind=kind)

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
    ) -> None:
        """Queue items added or modified locally outside live editor hooks (e.g., while mode was off)."""
        queued_keys = {make_object_key(m.kind, m.id) for m in self.queue.load_all()}
        conflict_keys = {c.object_key for c in state.conflicts}

        for item_id, item in local_by_id.items():
            key = make_object_key(DEFAULT_KIND, item_id)
            if key in queued_keys or key in conflict_keys:
                continue
            current_hash = canonical_item_hash(item_to_dict(item))
            recorded_hash = state.item_hashes.get(key)
            if key not in state.item_revs:
                self.queue.enqueue_upsert(item, known_base_rev=0, kind=DEFAULT_KIND)
            elif recorded_hash and current_hash != recorded_hash:
                self.queue.enqueue_upsert(
                    item,
                    known_base_rev=state.item_revs.get(key, 0),
                    kind=DEFAULT_KIND,
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
        full_snapshot: bool = False,
    ) -> Tuple[int, int, bool]:
        """Apply remote upserts and tombstones using three-way conflict detection."""
        local_items = self.storage.load_items()
        local_by_id: Dict[str, LibraryItem] = {item.id: item for item in local_items}
        queued_by_key = {make_object_key(m.kind, m.id): m for m in self.queue.load_all()}
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
            self.queue.remove_keys(keys_to_unqueue)

        if storage_changed:
            self.storage.save_items(list(local_by_id.values()))

        state.library_rev = pull_res.cursor
        state.etag = pull_res.etag
        return applied_upserts, applied_tombstones, storage_changed

    def _push_pending_queue(
        self,
        backend: ServerBackend,
        state: SyncStateData,
        *,
        timeout: Optional[float] = None,
    ) -> Tuple[int, bool, str]:
        pending = self.queue.load_all()
        if not pending:
            return 0, False, ""

        push_res = backend.push(pending, timeout=timeout)
        if push_res.queued_offline:
            return 0, True, push_res.error

        resolved_keys: set[str] = set()
        pending_by_key = {make_object_key(m.kind, m.id): m for m in pending}

        for key, new_rev in push_res.applied_revs.items():
            resolved_keys.add(key)
            mut = pending_by_key.get(key)
            if mut is not None and mut.op == "delete":
                state.item_revs.pop(key, None)
                state.item_hashes.pop(key, None)
            else:
                state.item_revs[key] = new_rev
                if mut is not None and mut.payload is not None:
                    state.item_hashes[key] = canonical_item_hash(mut.payload)

        for conf in push_res.conflicts:
            resolved_keys.add(conf.object_key)
            if conf.local_op == "delete" and conf.server_deleted:
                state.item_revs.pop(conf.object_key, None)
                state.item_hashes.pop(conf.object_key, None)
                continue
            if (
                conf.local_op == "upsert"
                and not conf.server_deleted
                and conf.local_item is not None
                and conf.server_item is not None
                and canonical_item_hash(conf.local_item) == canonical_item_hash(conf.server_item)
            ):
                state.item_revs[conf.object_key] = conf.server_rev
                state.item_hashes[conf.object_key] = canonical_item_hash(conf.server_item)
                continue
            self._upsert_conflict(state.conflicts, conf)

        self.queue.remove_keys(resolved_keys)
        if push_res.library_rev is not None and push_res.library_rev > state.library_rev:
            state.library_rev = push_res.library_rev
            state.etag = push_res.etag
        return len(push_res.applied_revs), False, push_res.error

    def sync_once(
        self,
        *,
        on_first_coupling: Optional[Callable[[int, int], FirstCouplingChoice]] = None,
    ) -> SyncOutcome:
        """Execute a complete sync cycle. Makes zero network calls when mode is ``"off"``."""
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

        state = self.state_store.load()
        state.mode = mode
        coupling_id = self.target_coupling_id()
        is_coupled = coupling_id in state.coupled_targets

        # Switching to a different server/namespace resets per-server cursor metadata cleanly.
        if not is_coupled and state.coupled_targets:
            state.library_rev = 0
            state.etag = ""
            state.item_revs.clear()
            state.item_hashes.clear()
            self.queue.clear()

        try:
            backend = self.build_backend(client_id=state.client_id)
            assert isinstance(backend, ServerBackend)

            # Step 1: First-time coupling handling if not yet coupled to this target.
            if not is_coupled:
                initial_pull = backend.pull(since_rev=None)
                if initial_pull.offline:
                    self.state_store.save(state)
                    return SyncOutcome(
                        ok=False,
                        mode=mode,
                        library_rev=state.library_rev,
                        pending_queue_count=self.get_pending_count(),
                        conflict_count=len(state.conflicts),
                        offline=True,
                        error=initial_pull.error,
                    )

                remote_count = len(initial_pull.upserts)
                choice: FirstCouplingChoice = "merge"
                if remote_count > 0 and on_first_coupling is not None:
                    choice = on_first_coupling(remote_count, initial_pull.cursor)

                if choice == "cancel":
                    return SyncOutcome(
                        ok=False,
                        mode=mode,
                        cancelled=True,
                        pending_queue_count=self.get_pending_count(),
                        conflict_count=len(state.conflicts),
                    )

                if choice == "take_server":
                    self.queue.clear()
                    state.conflicts.clear()
                    state.item_revs.clear()
                    state.item_hashes.clear()
                    adopted_items: List[LibraryItem] = []
                    for remote in initial_pull.upserts:
                        key = make_object_key(remote.kind, remote.id)
                        state.item_revs[key] = remote.rev
                        if remote.kind == DEFAULT_KIND:
                            lib_item = item_from_dict(remote.payload)
                            adopted_items.append(lib_item)
                            state.item_hashes[key] = canonical_item_hash(item_to_dict(lib_item))
                    self.storage.save_items(adopted_items)
                    state.library_rev = initial_pull.cursor
                    state.etag = initial_pull.etag
                    state.coupled_targets.append(coupling_id)
                    self.state_store.save(state)
                    return SyncOutcome(
                        ok=True,
                        mode=mode,
                        library_rev=state.library_rev,
                        pulled_upserts=len(adopted_items),
                        storage_changed=True,
                    )

                # Default non-destructive "merge": queue all local items first so shared IDs
                # with differing payloads surface in the conflict list instead of being overwritten.
                local_items = {it.id: it for it in self.storage.load_items()}
                self._detect_unqueued_local_changes(state, local_items)
                upserts_applied, tombs_applied, changed = self._reconcile_pull(
                    initial_pull,
                    state,
                    full_snapshot=False,
                )
                pushed_count, offline_push, push_err = self._push_pending_queue(backend, state)
                if not offline_push:
                    state.coupled_targets.append(coupling_id)
                self.state_store.save(state)
                return SyncOutcome(
                    ok=not offline_push,
                    mode=mode,
                    library_rev=state.library_rev,
                    pulled_upserts=upserts_applied,
                    pulled_tombstones=tombs_applied,
                    pushed_count=pushed_count,
                    pending_queue_count=self.get_pending_count(),
                    conflict_count=len(state.conflicts),
                    offline=offline_push,
                    storage_changed=changed,
                    error=push_err,
                )

            # Step 2: Coupled steady-state sync (detect untracked local edits -> push queue -> pull delta).
            local_by_id = {it.id: it for it in self.storage.load_items()}
            self._detect_unqueued_local_changes(state, local_by_id)

            pushed_count, offline_push, push_err = self._push_pending_queue(backend, state)
            if offline_push:
                self.state_store.save(state)
                return SyncOutcome(
                    ok=False,
                    mode=mode,
                    library_rev=state.library_rev,
                    pushed_count=pushed_count,
                    pending_queue_count=self.get_pending_count(),
                    conflict_count=len(state.conflicts),
                    offline=True,
                    error=push_err,
                )

            pull_res = backend.pull(since_rev=state.library_rev, etag=state.etag or None)
            full_snapshot = False
            if pull_res.reset_required:
                pull_res = backend.pull(since_rev=None)
                full_snapshot = True

            if pull_res.offline:
                self.state_store.save(state)
                return SyncOutcome(
                    ok=False,
                    mode=mode,
                    library_rev=state.library_rev,
                    pushed_count=pushed_count,
                    pending_queue_count=self.get_pending_count(),
                    conflict_count=len(state.conflicts),
                    offline=True,
                    error=pull_res.error,
                )

            upserts_applied = 0
            tombs_applied = 0
            changed = False
            if not pull_res.not_modified:
                upserts_applied, tombs_applied, changed = self._reconcile_pull(
                    pull_res,
                    state,
                    full_snapshot=full_snapshot,
                )

            self.state_store.save(state)
            return SyncOutcome(
                ok=True,
                mode=mode,
                library_rev=state.library_rev,
                pulled_upserts=upserts_applied,
                pulled_tombstones=tombs_applied,
                pushed_count=pushed_count,
                pending_queue_count=self.get_pending_count(),
                conflict_count=len(state.conflicts),
                storage_changed=changed,
            )
        except SyncError as exc:
            self.state_store.save(state)
            return SyncOutcome(
                ok=False,
                mode=mode,
                library_rev=state.library_rev,
                pending_queue_count=self.get_pending_count(),
                conflict_count=len(state.conflicts),
                error=str(exc),
            )

    def flush_pending(self, *, timeout: float = 2.0) -> PushResult:
        """Best-effort push of pending queue mutations (used on application quit)."""
        if self.current_mode() != "server" or not self.is_configured():
            return PushResult()
        pending = self.queue.load_all()
        if not pending:
            return PushResult()
        state = self.state_store.load()
        try:
            backend = self.build_backend(client_id=state.client_id)
            assert isinstance(backend, ServerBackend)
            pushed_count, offline, err = self._push_pending_queue(
                backend,
                state,
                timeout=timeout,
            )
            self.state_store.save(state)
            return PushResult(
                applied_revs={} if pushed_count == 0 else {"_count": pushed_count},
                conflicts=list(state.conflicts),
                queued_offline=offline,
                library_rev=state.library_rev,
                error=err,
            )
        except SyncError as exc:
            return PushResult(queued_offline=True, error=str(exc))

    def resolve_conflict(
        self,
        item_id: str,
        resolution: ConflictResolutionChoice,
        *,
        kind: str = DEFAULT_KIND,
        copy_suffix: str = "LOCAL COPY",
    ) -> Optional[LibraryItem]:
        """Resolve a recorded three-way conflict and synchronize the chosen outcome."""
        state = self.state_store.load()
        target_key = make_object_key(kind, item_id)
        conflict = next((c for c in state.conflicts if c.object_key == target_key), None)
        if conflict is None:
            return None

        state.conflicts = [c for c in state.conflicts if c.object_key != target_key]
        created_copy: Optional[LibraryItem] = None

        if resolution == "keep_local":
            if conflict.local_op == "delete" or conflict.local_item is None:
                self.storage.delete_item(conflict.id)
                self.queue.remove_keys({target_key})
                if conflict.server_rev > 0 and not conflict.server_deleted:
                    self.queue.enqueue_delete(
                        conflict.id,
                        known_base_rev=conflict.server_rev,
                        kind=conflict.kind,
                    )
                else:
                    state.item_revs.pop(target_key, None)
                    state.item_hashes.pop(target_key, None)
            else:
                local_obj = item_from_dict(conflict.local_item)
                local_obj.updated_at = now_iso()
                self.storage.upsert_item(local_obj)
                state.item_revs[target_key] = conflict.server_rev
                self.queue.remove_keys({target_key})
                self.queue.enqueue_upsert(
                    local_obj,
                    known_base_rev=conflict.server_rev,
                    kind=conflict.kind,
                )

        elif resolution == "keep_copy":
            # 1) Apply canonical server version to the original ID.
            self.queue.remove_keys({target_key})
            if conflict.server_deleted or conflict.server_item is None:
                self.storage.delete_item(conflict.id)
                state.item_revs.pop(target_key, None)
                state.item_hashes.pop(target_key, None)
            else:
                srv_obj = item_from_dict(conflict.server_item)
                self.storage.upsert_item(srv_obj)
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
                self.storage.upsert_item(created_copy)
                self.queue.enqueue_upsert(created_copy, known_base_rev=0, kind=DEFAULT_KIND)

        elif resolution == "take_server":
            self.queue.remove_keys({target_key})
            if conflict.server_deleted or conflict.server_item is None:
                self.storage.delete_item(conflict.id)
                state.item_revs.pop(target_key, None)
                state.item_hashes.pop(target_key, None)
            else:
                srv_obj = item_from_dict(conflict.server_item)
                self.storage.upsert_item(srv_obj)
                state.item_revs[target_key] = conflict.server_rev
                state.item_hashes[target_key] = canonical_item_hash(item_to_dict(srv_obj))
        else:
            raise ValueError(f"Unsupported conflict resolution '{resolution}'.")

        self.state_store.save(state)
        if self.current_mode() == "server" and self.is_configured() and self.queue.load_all():
            try:
                backend = self.build_backend(client_id=state.client_id)
                assert isinstance(backend, ServerBackend)
                self._push_pending_queue(backend, state)
                self.state_store.save(state)
            except SyncError:
                pass
        return created_copy
