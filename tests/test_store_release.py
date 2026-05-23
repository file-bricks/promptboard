from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def load_module():
    module_path = Path(__file__).resolve().parents[1] / "_tools" / "store_release.py"
    spec = importlib.util.spec_from_file_location("store_release", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_store_config_has_store_defaults():
    module = load_module()

    config = module.build_store_config()

    assert config["app_name"] == "PromptBoard"
    assert config["version"] == "1.1.1.0"
    assert config["executable"] == "PromptBoard-1.1.1-win64.exe"
    assert config["capabilities"] == ""
    assert config["privacy_url"].endswith("/PRIVACY_POLICY.md")


def test_build_store_listing_mentions_local_offline_use():
    module = load_module()

    listing = module.build_store_listing(module.build_store_config())

    assert "lokal" in listing
    assert "offline" in listing.lower()
    assert "global hotkeys" in listing.lower()
    assert "PromptBoard" in listing


def test_write_root_files_creates_json_and_markdown(tmp_path):
    module = load_module()

    config_path, listing_path = module.write_root_files(tmp_path)

    config = json.loads(config_path.read_text(encoding="utf-8"))
    listing = listing_path.read_text(encoding="utf-8")

    assert config["support_url"].endswith("/issues")
    assert "Store Listing — PromptBoard" in listing
    assert "Altersfreigabe" in listing
