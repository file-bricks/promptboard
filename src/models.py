from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Iterable, List
import uuid


class ItemType(str, Enum):
    PROMPT = "PROMPT"
    SKILL = "SKILL"
    WORKFLOW = "WORKFLOW"
    ROLLE = "ROLLE"
    AGENT = "AGENT"

    @classmethod
    def from_value(cls, value: str | ItemType) -> ItemType:
        if isinstance(value, cls):
            return value
        normalized = str(value).strip().upper().replace("-", "_").replace(" ", "_")
        if normalized == "ROLE":
            normalized = "ROLLE"
        try:
            return cls(normalized)
        except ValueError:
            return cls.PROMPT

    @classmethod
    def choices(cls) -> List[str]:
        return [item.value for item in cls]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def gen_id() -> str:
    return uuid.uuid4().hex


def normalize_name(name: str) -> str:
    return " ".join(name.split()).upper()


def parse_tags(raw: str | Iterable[str]) -> List[str]:
    if isinstance(raw, str):
        values = raw.split(",")
    else:
        values = raw
    tags: List[str] = []
    seen: set[str] = set()
    for value in values:
        tag = str(value).strip()
        if not tag:
            continue
        key = tag.casefold()
        if key in seen:
            continue
        seen.add(key)
        tags.append(tag)
    return tags


def sanitize_filename(name: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", name.strip())
    cleaned = cleaned.rstrip(". ")
    return cleaned or "PROMPTBOARD_EINTRAG"


@dataclass
class LibraryItem:
    id: str
    item_type: ItemType
    name: str
    content: str
    category: str = ""
    tags: List[str] = field(default_factory=list)
    source: str = ""
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)

    def __post_init__(self) -> None:
        self.item_type = ItemType.from_value(self.item_type)
        self.name = normalize_name(self.name)
        self.category = self.category.strip()
        self.source = self.source.strip()
        self.tags = parse_tags(self.tags)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "item_type": self.item_type.value,
            "name": self.name,
            "content": self.content,
            "category": self.category,
            "tags": list(self.tags),
            "source": self.source,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def filename_stem(self) -> str:
        return sanitize_filename(self.name)


def item_to_dict(item: LibraryItem) -> Dict[str, Any]:
    return item.to_dict()


def item_from_dict(data: Dict[str, Any]) -> LibraryItem:
    return LibraryItem(
        id=data["id"],
        item_type=ItemType.from_value(data.get("item_type", ItemType.PROMPT.value)),
        name=data.get("name", ""),
        content=data.get("content", ""),
        category=data.get("category", ""),
        tags=data.get("tags", []),
        source=data.get("source", ""),
        created_at=data.get("created_at", now_iso()),
        updated_at=data.get("updated_at", now_iso()),
    )
