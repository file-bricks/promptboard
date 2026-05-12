from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path
from typing import Any, List, Optional

from models import LibraryItem, item_from_dict, item_to_dict

logger = logging.getLogger(__name__)


def atomic_write_json(target: Path, data: Any, *, indent: int = 2) -> None:
    """Write JSON-serialisable data to target atomically via temp + os.replace.

    Reusable by adapters and other storage layers to keep a single
    write idiom across the codebase.
    """
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(
        json.dumps(data, ensure_ascii=False, indent=indent),
        encoding="utf-8",
    )
    os.replace(tmp, target)


class Storage:
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.library_file = self.data_dir / "library.json"
        self._lock = threading.Lock()
        self._ensure_file()

    def _ensure_file(self) -> None:
        if not self.library_file.exists():
            try:
                self.library_file.write_text(
                    json.dumps({"items": []}, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            except OSError as exc:
                logger.error("Konnte library.json nicht initialisieren: %s", exc)
                raise

    def load_items(self) -> List[LibraryItem]:
        try:
            data = json.loads(self.library_file.read_text(encoding="utf-8"))
        except FileNotFoundError:
            logger.warning("library.json fehlt, gebe leere Liste zurück.")
            return []
        except json.JSONDecodeError as exc:
            logger.error("library.json ist korrupt: %s", exc)
            raise
        return [item_from_dict(item) for item in data.get("items", [])]

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
        items = self.load_items()
        index = next((idx for idx, existing in enumerate(items) if existing.id == item.id), -1)
        if index >= 0:
            items[index] = item
        else:
            items.append(item)
        self.save_items(items)

    def delete_item(self, item_id: str) -> None:
        items = [item for item in self.load_items() if item.id != item_id]
        self.save_items(items)
