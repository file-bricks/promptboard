import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from materializer import build_markdown, materialize_item, materialize_items
from models import (
    ItemType,
    LibraryItem,
    gen_id,
    item_to_dict,
    normalize_name,
    parse_tags,
)
from profiprompt_adapter import load_latest_profiprompt_item, load_profiprompt_items
from storage import Storage


def test_storage_crud(tmp_path):
    store = Storage(tmp_path)
    item = LibraryItem(
        id=gen_id(),
        item_type=ItemType.PROMPT,
        name="TEST ITEM",
        content="Hallo",
        source="test",
    )
    store.upsert_item(item)
    loaded = store.load_items()
    assert len(loaded) == 1
    assert loaded[0].name == "TEST ITEM"

    item.content = "Geändert"
    store.upsert_item(item)
    loaded = store.load_items()
    assert loaded[0].content == "Geändert"

    store.delete_item(item.id)
    assert store.load_items() == []


def test_profiprompt_latest_import(tmp_path):
    prompts = {
        "prompts": [
            {
                "id": "one",
                "title": "Pruefen",
                "purpose": "Zweck eins",
                "text": "Text alt",
                "created_at": "2026-05-01T00:00:00+00:00",
                "updated_at": "2026-05-03T00:00:00+00:00",
                "tags": ["a"],
                "versions": [
                    {
                        "id": "one-v1",
                        "prompt_id": "one",
                        "version_number": 1,
                        "title": "Pruefen",
                        "text": "Text alt",
                        "result": "Ergebnis alt",
                        "tags": ["beta"],
                        "created_at": "2026-05-01T00:00:00+00:00",
                        "updated_at": "2026-05-01T00:00:00+00:00",
                    },
                    {
                        "id": "one-v2",
                        "prompt_id": "one",
                        "version_number": 2,
                        "title": "Pruefen",
                        "text": "Text neu",
                        "result": "Ergebnis neu",
                        "tags": ["gamma"],
                        "created_at": "2026-05-02T00:00:00+00:00",
                        "updated_at": "2026-05-03T00:00:00+00:00",
                    },
                ],
            },
            {
                "id": "two",
                "title": "Einfach",
                "purpose": "",
                "text": "Nur Text",
                "created_at": "2026-05-01T00:00:00+00:00",
                "updated_at": "2026-05-02T00:00:00+00:00",
                "tags": ["solo"],
            },
        ]
    }
    boards = {
        "boards": [
            {
                "id": "board-1",
                "title": "Arbeitsboard",
                "description": "Wichtige Prompts",
                "items": [
                    {
                        "id": "board-item-1",
                        "board_id": "board-1",
                        "prompt_id": "one",
                        "version_id": "one-v2",
                    }
                ],
            }
        ]
    }
    (tmp_path / "prompts.json").write_text(json.dumps(prompts), encoding="utf-8")
    (tmp_path / "boards.json").write_text(json.dumps(boards), encoding="utf-8")

    items = load_profiprompt_items(tmp_path)
    assert len(items) == 2

    item = load_latest_profiprompt_item(tmp_path)
    assert item is not None
    assert item.id == "profiprompt:prompt:one"
    assert item.name == "PRUEFEN"
    assert "Zweck eins" in item.content
    assert "Text neu" in item.content
    assert "Ergebnis neu" in item.content
    assert "## Boards" in item.content
    assert "Arbeitsboard" in item.content
    assert "## Version" in item.content
    assert "v2" in item.content
    assert item.category == "Arbeitsboard"
    assert item.tags == ["a", "gamma", "board:Arbeitsboard"]


def test_normalize_name():
    assert normalize_name("  Hallo   Welt  ") == "HALLO WELT"


def test_item_model_normalizes_type_tags_and_filename():
    item = LibraryItem(
        id="item-1",
        item_type="role",
        name="  Mein / Prompt:  ",
        content="Inhalt",
        tags=["alpha", " beta ", "ALPHA", "", "gamma"],
        source="  lokal  ",
    )

    assert item.item_type is ItemType.ROLLE
    assert item.name == "MEIN / PROMPT:"
    assert item.tags == ["alpha", "beta", "gamma"]
    assert item.source == "lokal"
    assert item.filename_stem() == "MEIN _ PROMPT_"

    payload = item_to_dict(item)
    assert payload["item_type"] == "ROLLE"
    assert payload["tags"] == ["alpha", "beta", "gamma"]


def test_parse_tags_accepts_strings_and_lists():
    assert parse_tags("a, b, a, c") == ["a", "b", "c"]
    assert parse_tags(["x", " x ", "y"]) == ["x", "y"]


def test_markdown_materialization_is_content_first():
    item = LibraryItem(
        id="item-2",
        item_type=ItemType.SKILL,
        name="Skill",
        content="### Schritt 1",
        source="lokal",
        category="Abläufe",
        tags=["eins", "zwei"],
        created_at="2026-05-01T10:00:00+00:00",
        updated_at="2026-05-02T11:00:00+00:00",
    )

    markdown = build_markdown(item)
    assert markdown.startswith(
        '<!-- promptboard:item id="item-2" type="SKILL" updated_at="2026-05-02T11:00:00+00:00" -->'
    )
    assert "\n# SKILL\n" in markdown
    assert "> Typ: SKILL" in markdown
    assert "> Kategorie: Abläufe" in markdown
    assert "> Tags: eins, zwei" in markdown
    assert "> Quelle: lokal" in markdown
    assert "> Stand: 2026-05-02T11:00:00+00:00" in markdown
    assert "> Erstellt: 2026-05-01T10:00:00+00:00" in markdown
    assert "## Metadaten" not in markdown
    assert "## Inhalt" not in markdown
    assert markdown.rstrip().endswith("### Schritt 1")


def test_materialize_item_writes_content_first_markdown(tmp_path):
    item = LibraryItem(
        id="item-3",
        item_type=ItemType.PROMPT,
        name="Mein Prompt",
        content="",
        source="lokal",
        updated_at="2026-05-10T10:00:00+00:00",
    )

    target = materialize_item(item, tmp_path)

    assert target == tmp_path / "MEIN PROMPT.md"
    markdown = target.read_text(encoding="utf-8")
    assert "> Typ: PROMPT" in markdown
    assert "> Quelle: lokal" in markdown
    assert "> Stand: 2026-05-10T10:00:00+00:00" in markdown
    assert "> Kategorie:" not in markdown
    assert "> Tags:" not in markdown
    assert "_Kein Inhalt vorhanden._" in markdown


def test_materialize_items_writes_multiple_markdowns(tmp_path):
    items = [
        LibraryItem(
            id="item-4",
            item_type=ItemType.PROMPT,
            name="Erster Eintrag",
            content="Alpha",
        ),
        LibraryItem(
            id="item-5",
            item_type=ItemType.SKILL,
            name="Zweiter Eintrag",
            content="Beta",
        ),
    ]

    targets = materialize_items(items, tmp_path)

    assert targets == [tmp_path / "ERSTER EINTRAG.md", tmp_path / "ZWEITER EINTRAG.md"]
    assert targets[0].read_text(encoding="utf-8").endswith("Alpha\n")
    assert targets[1].read_text(encoding="utf-8").endswith("Beta\n")
