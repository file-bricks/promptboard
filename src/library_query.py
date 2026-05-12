from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, List

from models import LibraryItem

SORT_MODE_UPDATED_DESC = "updated_desc"
SORT_MODE_NAME_ASC = "name_asc"
SORT_MODE_TYPE_NAME = "type_name"

DEFAULT_SORT_MODE = SORT_MODE_UPDATED_DESC

SORT_MODE_LABELS = {
    SORT_MODE_UPDATED_DESC: "Zuletzt geändert",
    SORT_MODE_NAME_ASC: "Name A-Z",
    SORT_MODE_TYPE_NAME: "Typ, Name",
}


def coerce_sort_mode(raw: str | None) -> str:
    if raw in SORT_MODE_LABELS:
        return str(raw)
    return DEFAULT_SORT_MODE


def _parse_iso_datetime(raw: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _search_terms(search_text: str) -> List[str]:
    return [term.casefold() for term in search_text.split() if term.strip()]


def _item_haystack(item: LibraryItem) -> str:
    return " ".join(
        [item.name, item.content, item.category, item.source, " ".join(item.tags)]
    ).casefold()


def item_matches_search(item: LibraryItem, search_text: str) -> bool:
    terms = _search_terms(search_text)
    if not terms:
        return True

    haystack = _item_haystack(item)
    return all(term in haystack for term in terms)


def sort_items(items: Iterable[LibraryItem], sort_mode: str | None) -> List[LibraryItem]:
    resolved = coerce_sort_mode(sort_mode)

    if resolved == SORT_MODE_NAME_ASC:
        return sorted(
            items,
            key=lambda item: (item.name.casefold(), item.item_type.value, item.id),
        )

    if resolved == SORT_MODE_TYPE_NAME:
        return sorted(
            items,
            key=lambda item: (
                item.item_type.value,
                item.name.casefold(),
                item.id,
            ),
        )

    return sorted(
        items,
        key=lambda item: (
            _parse_iso_datetime(item.updated_at),
            _parse_iso_datetime(item.created_at),
            item.name.casefold(),
            item.id,
        ),
        reverse=True,
    )


def query_items(
    items: Iterable[LibraryItem],
    search_text: str,
    item_type_filter: str,
    sort_mode: str | None,
) -> List[LibraryItem]:
    filtered: List[LibraryItem] = []
    for item in items:
        if item_type_filter != "ALLE" and item.item_type.value != item_type_filter:
            continue
        if not item_matches_search(item, search_text):
            continue
        filtered.append(item)
    return sort_items(filtered, sort_mode)
