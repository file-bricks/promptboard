import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from explorerpro_adapter import (
    ID_PREFIX,
    PROMPTS_FILENAME,
    export_to_explorerpro,
    load_explorerpro_items,
)
from models import ItemType, LibraryItem, gen_id


def _write_prompts(data_dir, prompts):
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / PROMPTS_FILENAME).write_text(
        json.dumps(prompts, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def test_load_empty_when_file_missing(tmp_path):
    items = load_explorerpro_items(tmp_path)
    assert items == []


def test_load_ignores_non_dict_entries(tmp_path):
    _write_prompts(
        tmp_path,
        [
            {
                "id": "prompt_1",
                "title": "Test",
                "content": "Hallo",
                "category": "Code",
                "tags": ["a", "b"],
                "created": "2026-05-01T10:00:00",
                "modified": "2026-05-02T11:00:00",
                "favorite": True,
                "use_count": 5,
            },
            "not-a-dict",
            42,
        ],
    )
    items = load_explorerpro_items(tmp_path)
    assert len(items) == 1
    item = items[0]
    assert item.id.startswith(ID_PREFIX)
    assert item.item_type == ItemType.PROMPT
    assert item.name == "TEST"
    assert item.content == "Hallo"
    assert item.category == "Code"
    assert "a" in item.tags and "b" in item.tags
    assert "favorite" in item.tags  # mapped from favorite=True
    assert item.source == "ExplorerPro"
    assert item.created_at == "2026-05-01T10:00:00"
    assert item.updated_at == "2026-05-02T11:00:00"


def test_load_handles_corrupt_json_gracefully(tmp_path):
    (tmp_path / PROMPTS_FILENAME).write_text("{ broken", encoding="utf-8")
    assert load_explorerpro_items(tmp_path) == []


def test_load_handles_object_root_gracefully(tmp_path):
    _write_prompts.__wrapped__ if False else None
    # ExplorerPro uses an array root; an object root should be ignored.
    (tmp_path / PROMPTS_FILENAME).write_text(
        json.dumps({"prompts": []}, ensure_ascii=False),
        encoding="utf-8",
    )
    assert load_explorerpro_items(tmp_path) == []


def test_export_creates_file_with_new_entries(tmp_path):
    item = LibraryItem(
        id=gen_id(),
        item_type=ItemType.PROMPT,
        name="NEUER PROMPT",
        content="Inhalt",
        category="Code",
        tags=["x"],
        source="local",
    )
    count = export_to_explorerpro([item], tmp_path)
    assert count == 1
    payload = json.loads((tmp_path / PROMPTS_FILENAME).read_text(encoding="utf-8"))
    assert isinstance(payload, list)
    assert len(payload) == 1
    assert payload[0]["title"] == "NEUER PROMPT"
    assert payload[0]["content"] == "Inhalt"
    assert payload[0]["category"] == "Code"
    assert "x" in payload[0]["tags"]
    assert payload[0]["favorite"] is False
    assert payload[0]["use_count"] == 0


def test_export_skips_non_prompt_items(tmp_path):
    skill = LibraryItem(
        id=gen_id(),
        item_type=ItemType.SKILL,
        name="SKILL ITEM",
        content="Skill",
        source="local",
    )
    count = export_to_explorerpro([skill], tmp_path)
    assert count == 0
    assert not (tmp_path / PROMPTS_FILENAME).exists() or json.loads(
        (tmp_path / PROMPTS_FILENAME).read_text(encoding="utf-8")
    ) == []


def test_roundtrip_preserves_original_id_and_unrelated_fields(tmp_path):
    _write_prompts(
        tmp_path,
        [
            {
                "id": "prompt_original",
                "title": "Alt",
                "content": "Alter Inhalt",
                "category": "Code",
                "tags": ["a"],
                "created": "2026-05-01T10:00:00",
                "modified": "2026-05-02T11:00:00",
                "favorite": True,
                "use_count": 7,
            }
        ],
    )
    items = load_explorerpro_items(tmp_path)
    assert len(items) == 1
    item = items[0]
    item.content = "Geänderter Inhalt"

    count = export_to_explorerpro([item], tmp_path)
    assert count == 1
    payload = json.loads((tmp_path / PROMPTS_FILENAME).read_text(encoding="utf-8"))
    assert len(payload) == 1
    entry = payload[0]
    assert entry["id"] == "prompt_original"
    assert entry["content"] == "Geänderter Inhalt"
    assert entry["favorite"] is True  # preserved
    assert entry["use_count"] == 7    # preserved
    assert entry["created"] == "2026-05-01T10:00:00"  # preserved


def test_export_preserves_unrelated_entries(tmp_path):
    _write_prompts(
        tmp_path,
        [
            {
                "id": "prompt_keep",
                "title": "Bleibt",
                "content": "Nicht angefasst",
                "category": "Other",
                "tags": [],
                "created": "2026-01-01T00:00:00",
                "modified": "2026-01-01T00:00:00",
                "favorite": False,
                "use_count": 0,
            }
        ],
    )
    new_item = LibraryItem(
        id=gen_id(),
        item_type=ItemType.PROMPT,
        name="NEU",
        content="Neuer Inhalt",
        source="local",
    )
    count = export_to_explorerpro([new_item], tmp_path)
    assert count == 1
    payload = json.loads((tmp_path / PROMPTS_FILENAME).read_text(encoding="utf-8"))
    titles = [entry["title"] for entry in payload]
    assert "Bleibt" in titles
    assert "NEU" in titles
