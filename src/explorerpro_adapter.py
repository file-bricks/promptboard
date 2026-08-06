"""Bidirectional adapter for the ExplorerPro Suite (prompts only).

ExplorerPro stores user data as JSON files under ``~/.explorerpro/``.
The relevant file for PromptBoard is ``prompts.json`` — a flat JSON
array of Prompt dataclass entries with the schema:

    {
        "id": str,                # e.g. "prompt_YYYYMMDDHHMMSSus"
        "title": str,
        "content": str,
        "category": str,
        "tags": list[str],
        "created": str,           # ISO timestamp
        "modified": str,          # ISO timestamp
        "favorite": bool,
        "use_count": int,
    }

We import these into PromptBoard ``LibraryItem`` entries with the
stable id schema ``explorerpro:prompt:<safe_key>``. On export we
write back to the same file, preserving entries that did not
originate from PromptBoard (round-trip safety).

App entries (``apps.json``) are intentionally **not** mapped — they
are not semantically equivalent to PromptBoard types.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Iterable, Optional

from models import ItemType, LibraryItem, normalize_name, now_iso, parse_tags
from storage import atomic_write_json

logger = logging.getLogger(__name__)

ID_PREFIX = "explorerpro:prompt:"
PROMPTS_FILENAME = "prompts.json"


def _load_json_array(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("ExplorerPro %s konnte nicht gelesen werden: %s", path, exc)
        return []
    if not isinstance(payload, list):
        logger.warning("ExplorerPro %s hat kein Array-Format.", path)
        return []
    return [entry for entry in payload if isinstance(entry, dict)]


def _str_val(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback
    s = str(value).strip()
    return s if s else fallback


def _safe_key(value: Any, fallback: str) -> str:
    raw = str(value).strip() if value is not None else ""
    if not raw:
        raw = fallback
    key = re.sub(r"[^A-Za-z0-9._-]+", "_", raw).strip("_")
    return key or fallback


def _make_item_id(entry: dict[str, Any]) -> str:
    raw_id = entry.get("id") or entry.get("title") or "imported"
    return f"{ID_PREFIX}{_safe_key(raw_id, 'imported')}"


def _map_prompt_to_item(entry: dict[str, Any]) -> LibraryItem:
    title = _str_val(entry.get("title"), "IMPORTIERTER PROMPT")
    content = _str_val(entry.get("content"))
    category = _str_val(entry.get("category"), "ExplorerPro Import")
    tags_raw = entry.get("tags")
    tags = parse_tags(tags_raw if isinstance(tags_raw, (list, str)) else [])
    if entry.get("favorite"):
        tags = parse_tags(tags + ["favorite"])
    created = _str_val(entry.get("created"), now_iso())
    modified = _str_val(entry.get("modified"), created)
    return LibraryItem(
        id=_make_item_id(entry),
        item_type=ItemType.PROMPT,
        name=normalize_name(title),
        content=content,
        category=category,
        tags=tags,
        source="ExplorerPro",
        created_at=created,
        updated_at=modified,
    )


def load_explorerpro_items(data_dir: Path) -> list[LibraryItem]:
    """Read ExplorerPro prompts.json and return a list of LibraryItems."""
    data_dir = Path(data_dir)
    prompts_file = data_dir / PROMPTS_FILENAME
    entries = _load_json_array(prompts_file)
    items = [_map_prompt_to_item(entry) for entry in entries]
    items.sort(
        key=lambda item: (item.updated_at, item.created_at, item.name),
        reverse=True,
    )
    return items


def _original_id_from_item(item: LibraryItem) -> Optional[str]:
    if not item.id.startswith(ID_PREFIX):
        return None
    raw = item.id[len(ID_PREFIX):]
    return raw or None


def _item_to_prompt_entry(
    item: LibraryItem,
    existing: dict[str, Any] | None,
) -> dict[str, Any]:
    """Map a PromptBoard LibraryItem to an ExplorerPro Prompt dict.

    Preserves untouched fields from the existing entry when available
    (favorite, use_count, original id).
    """
    base: dict[str, Any] = dict(existing) if existing else {}
    tags = [tag for tag in item.tags if tag.casefold() != "favorite"]
    favorite_from_tags = any(tag.casefold() == "favorite" for tag in item.tags)
    base["id"] = base.get("id") or _original_id_from_item(item) or _safe_key(
        item.name, "promptboard_export"
    )
    base["title"] = item.name
    base["content"] = item.content
    base["category"] = item.category or base.get("category", "")
    base["tags"] = tags
    base["created"] = base.get("created") or item.created_at
    base["modified"] = item.updated_at
    base["favorite"] = bool(base.get("favorite")) or favorite_from_tags
    base.setdefault("use_count", 0)
    return base


def export_to_explorerpro(
    items: Iterable[LibraryItem],
    data_dir: Path,
) -> int:
    """Write PromptBoard items back to ExplorerPro prompts.json.

    Round-trip safe:
    - Items with ``explorerpro:prompt:*`` IDs are written back to
      the same original ExplorerPro entry (matched by id-suffix).
    - Items without that prefix are appended as new ExplorerPro
      prompts (PROMPT type only — other PromptBoard types are
      skipped).
    - ExplorerPro entries that are NOT present in the input list
      are preserved untouched.

    Returns the count of items written back (matched + new).
    """
    data_dir = Path(data_dir)
    prompts_file = data_dir / PROMPTS_FILENAME
    existing_entries = _load_json_array(prompts_file)
    existing_by_id: dict[str, dict[str, Any]] = {
        str(entry.get("id", "")): entry for entry in existing_entries if entry.get("id")
    }

    written_count = 0
    seen_ids: set[str] = set()
    new_entries: list[dict[str, Any]] = []

    for item in items:
        if item.item_type != ItemType.PROMPT:
            continue
        original_id = _original_id_from_item(item)
        if original_id and original_id in existing_by_id:
            existing_entry = existing_by_id[original_id]
            updated = _item_to_prompt_entry(item, existing_entry)
            existing_by_id[original_id] = updated
            seen_ids.add(original_id)
            written_count += 1
        else:
            entry = _item_to_prompt_entry(item, None)
            new_entries.append(entry)
            written_count += 1

    # Rebuild the output array in original order, then append new entries.
    # BUGSWEEP-41: Einträge ohne 'id'-Feld dürfen nicht dedupliziert werden —
    # sie alle haben entry_id == "" und würden ab dem zweiten Eintrag durch
    # ``seen_existing``-Check fallen gelassen (silent data loss).
    output: list[dict[str, Any]] = []
    seen_existing: set[str] = set()
    for entry in existing_entries:
        entry_id = str(entry.get("id", ""))
        if not entry_id:
            # Kein ID → keine Deduplizierung möglich, Eintrag immer erhalten.
            output.append(entry)
            continue
        if entry_id in seen_existing:
            continue
        seen_existing.add(entry_id)
        output.append(existing_by_id.get(entry_id, entry))
    output.extend(new_entries)

    try:
        atomic_write_json(prompts_file, output)
    except OSError as exc:
        logger.error("Konnte %s nicht schreiben: %s", prompts_file, exc)
        raise
    logger.info("ExplorerPro-Export: %s Eintrag(e) nach %s geschrieben.", written_count, prompts_file)
    return written_count
