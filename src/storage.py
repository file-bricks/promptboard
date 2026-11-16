from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import stat
import threading
import time
from typing import Any, List, Optional
import uuid

from models import LibraryItem, item_from_dict, item_to_dict

logger = logging.getLogger(__name__)


def _atomic_replace_with_retry(tmp: Path, target: Path) -> None:
    """Replace target with tmp atomically, handling Windows read-only bits and transient locks."""
    original_mode: Optional[int] = None
    if target.exists():
        if target.is_dir():
            raise IsADirectoryError(f"Zielpfad ist ein Verzeichnis: {target}")
        try:
            st_mode = target.stat().st_mode
            if not (st_mode & stat.S_IWRITE):
                original_mode = st_mode
                os.chmod(target, st_mode | stat.S_IWRITE)
        except OSError:
            original_mode = None

    last_exc: Optional[OSError] = None
    for attempt in range(8):
        try:
            os.replace(tmp, target)
            return
        except PermissionError as exc:
            if target.exists() and target.is_dir():
                raise IsADirectoryError(f"Zielpfad ist ein Verzeichnis: {target}") from exc
            last_exc = exc
            winerr = getattr(exc, "winerror", None)
            if winerr not in (None, 5, 32) or attempt == 7:
                break
            time.sleep(min(0.01 * (2**attempt), 0.2))
        except OSError as exc:
            last_exc = exc
            break

    if original_mode is not None and target.exists():
        try:
            os.chmod(target, original_mode)
        except OSError:
            pass
    if last_exc is not None:
        raise last_exc


def atomic_write_text(target: Path, content: str, *, encoding: str = "utf-8") -> None:
    """Write text to target atomically via unique temp file, fsync, and os.replace."""
    target = Path(target)
    if target.exists() and target.is_dir():
        raise IsADirectoryError(f"Zielpfad ist ein Verzeichnis: {target}")
    if target.parent.exists() and not target.parent.is_dir():
        raise NotADirectoryError(f"Übergeordneter Pfad ist kein Verzeichnis: {target.parent}")
    target.parent.mkdir(parents=True, exist_ok=True)

    tmp = target.parent / f".{target.name}.{os.getpid()}.{uuid.uuid4().hex[:8]}.tmp"
    try:
        with open(tmp, "w", encoding=encoding) as fh:
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())
        _atomic_replace_with_retry(tmp, target)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


def atomic_write_json(target: Path, data: Any, *, indent: int = 2) -> None:
    """Write JSON-serialisable data to target atomically via temp + fsync + os.replace.

    Reusable by adapters and other storage layers to keep a single
    write idiom across the codebase.
    """
    target = Path(target)
    if target.exists() and target.is_dir():
        raise IsADirectoryError(f"Zielpfad ist ein Verzeichnis: {target}")
    payload = json.dumps(data, ensure_ascii=False, indent=indent)
    atomic_write_text(target, payload, encoding="utf-8")


class Storage:
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.library_file = self.data_dir / "library.json"
        self._lock = threading.RLock()
        self._ensure_file()

    def _ensure_file(self) -> None:
        if self.library_file.exists():
            if self.library_file.is_dir():
                raise IsADirectoryError(f"library.json ist ein Verzeichnis: {self.library_file}")
            return
        try:
            atomic_write_json(self.library_file, {"items": []})
        except OSError as exc:
            logger.error("Konnte library.json nicht initialisieren: %s", exc)
            raise

    def load_items(self) -> List[LibraryItem]:
        if self.library_file.exists() and self.library_file.is_dir():
            raise IsADirectoryError(f"library.json ist ein Verzeichnis: {self.library_file}")
        try:
            data = json.loads(self.library_file.read_text(encoding="utf-8-sig"))
        except FileNotFoundError:
            logger.warning("library.json fehlt, gebe leere Liste zurück.")
            return []
        except json.JSONDecodeError as exc:
            logger.error("library.json ist korrupt: %s", exc)
            raise

        if not isinstance(data, dict):
            logger.error("library.json hat kein JSON-Objekt-Wurzelformat.")
            raise ValueError("library.json muss ein JSON-Objekt mit dem Feld 'items' sein.")

        raw_items = data.get("items", [])
        if raw_items is None:
            raw_items = []
        elif not isinstance(raw_items, list):
            logger.error("library.json Feld 'items' ist keine Liste.")
            raise ValueError("library.json Feld 'items' muss eine Liste oder null sein.")

        loaded: List[LibraryItem] = []
        for entry in raw_items:
            if entry is None:
                continue
            if not isinstance(entry, dict):
                logger.error("Ungültiger Eintragstyp in library.json 'items': %r", type(entry))
                raise ValueError("Einträge in library.json 'items' müssen JSON-Objekte sein.")
            loaded.append(item_from_dict(entry))
        return loaded

    def get_item(self, item_id: str) -> Optional[LibraryItem]:
        return next((item for item in self.load_items() if item.id == item_id), None)

    def _atomic_write(self, target: Path, data: dict) -> None:
        # Backwards-compatible wrapper used by tests; delegates to module helper.
        atomic_write_json(target, data)

    def save_items(self, items: List[LibraryItem]) -> None:
        payload = {"items": [item_to_dict(item) for item in items]}
        with self._lock:
            try:
                atomic_write_json(self.library_file, payload)
            except OSError as exc:
                logger.error("Konnte library.json nicht speichern: %s", exc)
                raise

    def upsert_item(self, item: LibraryItem) -> None:
        with self._lock:
            items = self.load_items()
            index = next((idx for idx, existing in enumerate(items) if existing.id == item.id), -1)
            if index >= 0:
                items[index] = item
            else:
                items.append(item)
            self.save_items(items)

    def upsert_many(self, new_items: List[LibraryItem]) -> int:
        """Batch upsert: one load + one save, regardless of how many items.

        Returns the number of items that were either added or updated.
        """
        if not new_items:
            return 0
        with self._lock:
            existing = self.load_items()
            index_by_id = {item.id: idx for idx, item in enumerate(existing)}
            touched = 0
            for item in new_items:
                idx = index_by_id.get(item.id, -1)
                if idx >= 0:
                    existing[idx] = item
                else:
                    index_by_id[item.id] = len(existing)
                    existing.append(item)
                touched += 1
            self.save_items(existing)
            return touched

    def delete_item(self, item_id: str) -> None:
        with self._lock:
            items = [item for item in self.load_items() if item.id != item_id]
            self.save_items(items)
