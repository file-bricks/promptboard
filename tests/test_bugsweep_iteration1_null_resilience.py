from __future__ import annotations

import json
from pathlib import Path

from models import parse_tags
from profiprompt_adapter import load_profiprompt_items
from explorerpro_adapter import load_explorerpro_items


class TestBugsweepIteration1NullResilience:
    def test_parse_tags_with_none_and_invalid_types(self) -> None:
        assert parse_tags(None) == []
        assert parse_tags(["tag1", None, "tag2"]) == ["tag1", "tag2"]
        assert parse_tags(123) == []
        assert parse_tags(True) == []

    def test_profiprompt_null_fields_resilience(self, tmp_path: Path) -> None:
        data_dir = tmp_path / "profiprompt"
        data_dir.mkdir()
        prompts_file = data_dir / "prompts.json"

        # JSON containing null values for tags, purpose, title, text, last_result, created_at, updated_at
        prompts_data = {
            "prompts": [
                {
                    "id": "p_null_1",
                    "title": None,
                    "purpose": None,
                    "tags": None,
                    "text": None,
                    "last_result": None,
                    "created_at": None,
                    "updated_at": None,
                    "versions": [
                        {
                            "version_number": 1,
                            "text": None,
                            "result": None,
                            "tags": None,
                            "created_at": None,
                            "updated_at": None,
                        }
                    ]
                }
            ]
        }
        prompts_file.write_text(json.dumps(prompts_data), encoding="utf-8")

        items = load_profiprompt_items(data_dir)
        assert len(items) == 1
        item = items[0]
        assert item.name == "IMPORTED PROMPT"
        assert item.tags == []
        assert "None" not in item.content
        assert item.source == "ProfiPrompt"

    def test_explorerpro_null_fields_resilience(self, tmp_path: Path) -> None:
        data_dir = tmp_path / "explorerpro"
        data_dir.mkdir()
        prompts_file = data_dir / "prompts.json"

        # JSON containing null values for title, content, category, tags, created, modified
        prompts_data = [
            {
                "id": "exp_null_1",
                "title": None,
                "content": None,
                "category": None,
                "tags": None,
                "created": None,
                "modified": None,
                "favorite": False,
            }
        ]
        prompts_file.write_text(json.dumps(prompts_data), encoding="utf-8")

        items = load_explorerpro_items(data_dir)
        assert len(items) == 1
        item = items[0]
        assert item.name == "IMPORTIERTER PROMPT"
        assert item.content == ""
        assert item.category == "ExplorerPro Import"
        assert item.tags == []
        assert "None" not in item.created_at
        assert item.source == "ExplorerPro"
