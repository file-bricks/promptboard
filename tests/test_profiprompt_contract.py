import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from profiprompt_adapter import (
    ADAPTER_NAME,
    IS_READ_ONLY,
    SUPPORTED_FILES,
    load_profiprompt_items,
    validate_profiprompt_contract,
)


def test_contract_metadata_constants():
    assert ADAPTER_NAME == "ProfiPrompt"
    assert IS_READ_ONLY is True
    assert "prompts.json" in SUPPORTED_FILES
    assert "boards.json" in SUPPORTED_FILES


def test_validate_profiprompt_contract_missing_directory(tmp_path):
    contract = validate_profiprompt_contract(tmp_path / "non_existent")
    assert contract["is_valid"] is False
    assert contract["prompts_exist"] is False
    assert contract["prompt_count"] == 0
    assert contract["is_read_only"] is True
    assert contract["write_back_supported"] is False


def test_validate_profiprompt_contract_valid_payload(tmp_path):
    prompts_file = tmp_path / "prompts.json"
    boards_file = tmp_path / "boards.json"

    prompts_payload = {
        "prompts": [
            {
                "id": "p1",
                "title": "System Prompt",
                "purpose": "Testing",
                "text": "Hello World",
            }
        ]
    }
    boards_payload = {
        "boards": [
            {
                "id": "b1",
                "title": "Main Board",
                "items": [{"prompt_id": "p1"}],
            }
        ]
    }

    prompts_file.write_text(json.dumps(prompts_payload), encoding="utf-8")
    boards_file.write_text(json.dumps(boards_payload), encoding="utf-8")

    contract = validate_profiprompt_contract(tmp_path)
    assert contract["is_valid"] is True
    assert contract["prompts_exist"] is True
    assert contract["boards_exist"] is True
    assert contract["prompt_count"] == 1
    assert contract["board_count"] == 1
    assert contract["adapter"] == "ProfiPrompt"
    assert contract["write_back_supported"] is False


def test_profiprompt_items_mapped_read_only(tmp_path):
    prompts_file = tmp_path / "prompts.json"
    prompts_payload = {
        "prompts": [
            {
                "id": "p_ro",
                "title": "Read Only Test",
                "purpose": "Verify mapping",
                "text": "Text content",
            }
        ]
    }
    prompts_file.write_text(json.dumps(prompts_payload), encoding="utf-8")

    items = load_profiprompt_items(tmp_path)
    assert len(items) == 1
    assert items[0].source == "ProfiPrompt"
    assert items[0].name == "READ ONLY TEST"
