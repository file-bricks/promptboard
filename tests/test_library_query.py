import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from library_query import (
    DEFAULT_SORT_MODE,
    SORT_MODE_NAME_ASC,
    SORT_MODE_TYPE_NAME,
    SORT_MODE_UPDATED_DESC,
    coerce_sort_mode,
    query_items,
)
from models import ItemType, LibraryItem


def make_item(
    item_id: str,
    item_type: ItemType,
    name: str,
    *,
    updated_at: str,
    created_at: str,
    content: str = "",
    category: str = "",
    tags: list[str] | None = None,
    source: str = "",
) -> LibraryItem:
    return LibraryItem(
        id=item_id,
        item_type=item_type,
        name=name,
        content=content,
        category=category,
        tags=tags or [],
        source=source,
        created_at=created_at,
        updated_at=updated_at,
    )


def test_query_items_matches_all_search_terms_across_fields():
    items = [
        make_item(
            "a",
            ItemType.PROMPT,
            "Alpha Signal",
            updated_at="2026-05-02T10:00:00+00:00",
            created_at="2026-05-01T10:00:00+00:00",
            category="Team",
            tags=["review"],
        ),
        make_item(
            "b",
            ItemType.SKILL,
            "Bravo Guide",
            updated_at="2026-05-03T10:00:00+00:00",
            created_at="2026-05-01T09:00:00+00:00",
            content="Alpha in the body",
            tags=["team"],
        ),
        make_item(
            "c",
            ItemType.PROMPT,
            "Charlie",
            updated_at="2026-05-04T10:00:00+00:00",
            created_at="2026-05-01T08:00:00+00:00",
            content="Nothing useful here",
            tags=["misc"],
        ),
    ]

    result = query_items(items, "alpha team", "ALLE", SORT_MODE_UPDATED_DESC)

    assert [item.id for item in result] == ["b", "a"]
    assert query_items(items, "alpha missing", "ALLE", SORT_MODE_UPDATED_DESC) == []


def test_query_items_sorts_by_selected_mode():
    items = [
        make_item(
            "a",
            ItemType.WORKFLOW,
            "Gamma",
            updated_at="2026-05-01T10:00:00+00:00",
            created_at="2026-05-01T09:00:00+00:00",
        ),
        make_item(
            "b",
            ItemType.PROMPT,
            "Alpha",
            updated_at="2026-05-03T10:00:00+00:00",
            created_at="2026-05-02T09:00:00+00:00",
        ),
        make_item(
            "c",
            ItemType.SKILL,
            "Beta",
            updated_at="2026-05-02T10:00:00+00:00",
            created_at="2026-05-02T08:00:00+00:00",
        ),
    ]

    assert [item.id for item in query_items(items, "", "ALLE", SORT_MODE_UPDATED_DESC)] == [
        "b",
        "c",
        "a",
    ]
    assert [item.id for item in query_items(items, "", "ALLE", SORT_MODE_NAME_ASC)] == [
        "b",
        "c",
        "a",
    ]
    assert [item.id for item in query_items(items, "", "ALLE", SORT_MODE_TYPE_NAME)] == [
        "b",
        "c",
        "a",
    ]


def test_coerce_sort_mode_falls_back_to_default():
    assert coerce_sort_mode("unknown") == DEFAULT_SORT_MODE
    assert coerce_sort_mode(None) == DEFAULT_SORT_MODE


def test_query_items_filter_all_works_in_english_and_german():
    items = [
        make_item(
            "a",
            ItemType.PROMPT,
            "Alpha",
            updated_at="2026-05-01T10:00:00+00:00",
            created_at="2026-05-01T10:00:00+00:00",
        ),
        make_item(
            "b",
            ItemType.SKILL,
            "Beta",
            updated_at="2026-05-02T10:00:00+00:00",
            created_at="2026-05-02T10:00:00+00:00",
        ),
    ]

    result_de = query_items(items, "", "ALLE", SORT_MODE_NAME_ASC)
    result_en = query_items(items, "", "ALL", SORT_MODE_NAME_ASC)
    result_any = query_items(items, "", "Anything", SORT_MODE_NAME_ASC)

    assert [i.id for i in result_de] == ["a", "b"]
    assert [i.id for i in result_en] == ["a", "b"]
    assert [i.id for i in result_any] == ["a", "b"]


def test_query_items_type_filter_selects_only_matching_type():
    items = [
        make_item(
            "a",
            ItemType.PROMPT,
            "Alpha",
            updated_at="2026-05-01T10:00:00+00:00",
            created_at="2026-05-01T10:00:00+00:00",
        ),
        make_item(
            "b",
            ItemType.SKILL,
            "Beta",
            updated_at="2026-05-02T10:00:00+00:00",
            created_at="2026-05-02T10:00:00+00:00",
        ),
        make_item(
            "c",
            ItemType.PROMPT,
            "Charlie",
            updated_at="2026-05-03T10:00:00+00:00",
            created_at="2026-05-03T10:00:00+00:00",
        ),
    ]

    result = query_items(items, "", "PROMPT", SORT_MODE_NAME_ASC)
    assert [i.id for i in result] == ["a", "c"]

    result = query_items(items, "", "SKILL", SORT_MODE_NAME_ASC)
    assert [i.id for i in result] == ["b"]
