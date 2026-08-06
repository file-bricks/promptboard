from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Optional

from models import ItemType, LibraryItem, gen_id, normalize_name, now_iso, parse_tags

logger = logging.getLogger(__name__)


def _load_json_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("ProfiPrompt %s konnte nicht gelesen werden: %s", path, exc)
        return {}
    return payload if isinstance(payload, dict) else {}


def _safe_key(value: Any, fallback: str) -> str:
    raw = str(value).strip() if value is not None else ""
    if not raw:
        raw = fallback
    key = re.sub(r"[^A-Za-z0-9._-]+", "_", raw).strip("_")
    return key or fallback


def _parse_timestamp(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _version_sort_key(version: dict[str, Any]) -> tuple[int, str, str, str]:
    raw_number = version.get("version_number", 0)
    try:
        version_number = int(raw_number)
    except (TypeError, ValueError):
        version_number = 0
    return (
        version_number,
        _parse_timestamp(version.get("updated_at", "")),
        _parse_timestamp(version.get("created_at", "")),
        str(version.get("id", "")),
    )


def _select_latest_version(prompt: dict[str, Any]) -> Optional[dict[str, Any]]:
    versions = prompt.get("versions", [])
    if not isinstance(versions, list) or not versions:
        return None
    valid_versions = [version for version in versions if isinstance(version, dict)]
    if not valid_versions:
        return None
    return max(valid_versions, key=_version_sort_key)


def _board_titles_by_prompt_id(boards: list[dict[str, Any]]) -> dict[str, list[str]]:
    titles_by_prompt_id: dict[str, list[str]] = {}
    seen_pairs: set[tuple[str, str]] = set()

    for board in boards:
        if not isinstance(board, dict):
            continue
        board_title = str(board.get("title", "")).strip()
        if not board_title:
            continue
        items = board.get("items", [])
        if not isinstance(items, list):
            continue

        for item in items:
            if not isinstance(item, dict):
                continue
            prompt_id = str(item.get("prompt_id", "")).strip()
            if not prompt_id:
                continue
            key = (prompt_id, board_title.casefold())
            if key in seen_pairs:
                continue
            seen_pairs.add(key)
            titles_by_prompt_id.setdefault(prompt_id, []).append(board_title)

    return titles_by_prompt_id


def _str_val(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback
    s = str(value).strip()
    return s if s else fallback


def _build_prompt_content(
    prompt: dict[str, Any],
    latest_version: Optional[dict[str, Any]],
    board_titles: list[str],
) -> str:
    purpose = _str_val(prompt.get("purpose"))
    prompt_text = ""
    version_label = ""
    version_result = ""

    if latest_version is not None:
        prompt_text = _str_val(latest_version.get("text"))
        version_number = latest_version.get("version_number")
        if version_number not in (None, ""):
            version_label = f"v{version_number}"
        version_result = _str_val(latest_version.get("result"))

    if not prompt_text:
        prompt_text = _str_val(prompt.get("text"))
    if not version_result:
        version_result = _str_val(prompt.get("last_result"))

    sections: list[str] = []
    if purpose:
        sections.extend(["## Zweck", purpose])

    sections.extend(["## Prompt", prompt_text or "-"])

    if version_result:
        sections.extend(["## Ergebnis", version_result])

    if board_titles:
        board_lines = "\n".join(f"- {title}" for title in board_titles)
        sections.extend(["## Boards", board_lines])

    if version_label:
        sections.extend(["## Version", version_label])

    return "\n\n".join(section for section in sections if section is not None).strip()


def _map_prompt(
    prompt: dict[str, Any],
    board_titles: list[str],
) -> LibraryItem:
    prompt_id = _str_val(prompt.get("id"))
    title = _str_val(prompt.get("title"), "IMPORTED PROMPT")
    latest_version = _select_latest_version(prompt)

    prompt_tags = parse_tags(prompt.get("tags"))
    version_tags = parse_tags(latest_version.get("tags") if latest_version else None)
    board_tags = [f"board:{title}" for title in board_titles]

    category = "ProfiPrompt Import"
    if len(board_titles) == 1:
        category = board_titles[0]
    elif len(board_titles) > 1:
        category = "ProfiPrompt Boards"

    created_at = _str_val(prompt.get("created_at"))
    updated_at = _str_val(prompt.get("updated_at"))
    if latest_version is not None:
        created_at = created_at or _str_val(latest_version.get("created_at"))
        updated_at = _str_val(latest_version.get("updated_at")) or updated_at

    return LibraryItem(
        id=f"profiprompt:prompt:{_safe_key(prompt_id, title)}",
        item_type=ItemType.PROMPT,
        name=normalize_name(title),
        content=_build_prompt_content(prompt, latest_version, board_titles),
        category=category,
        tags=parse_tags(prompt_tags + version_tags + board_tags),
        source="ProfiPrompt",
        created_at=created_at or now_iso(),
        updated_at=updated_at or now_iso(),
    )


def load_profiprompt_items(data_dir: Path) -> list[LibraryItem]:
    data_dir = Path(data_dir)
    prompts_file = data_dir / "prompts.json"
    if not prompts_file.exists():
        return []

    prompts_payload = _load_json_object(prompts_file)
    prompts = prompts_payload.get("prompts", [])
    if not isinstance(prompts, list) or not prompts:
        return []

    boards_payload = _load_json_object(data_dir / "boards.json")
    boards = boards_payload.get("boards", [])
    if not isinstance(boards, list):
        boards = []

    board_titles_by_prompt_id = _board_titles_by_prompt_id(boards)
    items: list[LibraryItem] = []
    for prompt in prompts:
        if not isinstance(prompt, dict):
            continue
        prompt_id = str(prompt.get("id", "")).strip()
        board_titles = board_titles_by_prompt_id.get(prompt_id, [])
        items.append(_map_prompt(prompt, board_titles))

    items.sort(key=lambda item: (item.updated_at, item.created_at, item.name), reverse=True)
    return items


def load_latest_profiprompt_item(data_dir: Path) -> Optional[LibraryItem]:
    prompt_items = [item for item in load_profiprompt_items(data_dir) if item.item_type == ItemType.PROMPT]
    if not prompt_items:
        return None
    return max(prompt_items, key=lambda item: (item.updated_at, item.created_at, item.name))
