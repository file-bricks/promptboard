from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


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
    assert config["capabilities"] == "runFullTrust"
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
    assert "Store Listing - PromptBoard" in listing
    assert "Altersfreigabe" in listing


def test_write_root_files_preserves_existing_partner_center_values(tmp_path):
    module = load_module()
    config_path = tmp_path / "store_package.json"
    config_path.write_text(
        json.dumps(
            {
                "publisher": "CN=Real Publisher",
                "identity_name": "RealPublisher.PromptBoard",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    module.write_root_files(tmp_path)

    config = json.loads(config_path.read_text(encoding="utf-8"))
    assert config["publisher"] == "CN=Real Publisher"
    assert config["identity_name"] == "RealPublisher.PromptBoard"


def test_load_store_config_merges_local_and_environment_overrides(tmp_path):
    module = load_module()
    (tmp_path / "store_package.json").write_text(
        json.dumps({"publisher": "CN=Tracked Publisher"}, ensure_ascii=False),
        encoding="utf-8",
    )
    (tmp_path / "store_package.local.json").write_text(
        json.dumps({"identity_name": "LocalPublisher.PromptBoard"}, ensure_ascii=False),
        encoding="utf-8",
    )

    config = module.load_store_config(
        tmp_path,
        environ={
            "PROMPTBOARD_STORE_PUBLISHER_DISPLAY": "PromptBoard Labs",
        },
    )

    assert config["publisher"] == "CN=Tracked Publisher"
    assert config["identity_name"] == "LocalPublisher.PromptBoard"
    assert config["publisher_display"] == "PromptBoard Labs"
    assert config["capabilities"] == "runFullTrust"


def test_load_store_config_adds_run_full_trust_to_existing_capabilities(tmp_path):
    module = load_module()
    (tmp_path / "store_package.json").write_text(
        json.dumps({"capabilities": "internetClient"}, ensure_ascii=False),
        encoding="utf-8",
    )

    config = module.load_store_config(tmp_path, include_local_overrides=False)

    assert config["capabilities"] == "runFullTrust,internetClient"


def test_assert_store_ready_rejects_placeholders():
    module = load_module()

    with pytest.raises(ValueError) as excinfo:
        module.assert_store_ready(module.build_store_config())

    message = str(excinfo.value)
    assert "publisher" in message
    assert "identity_name" in message


def test_prepare_store_package_uses_effective_store_values(tmp_path):
    module = load_module()
    (tmp_path / "store_package.json").write_text(
        json.dumps(
            {
                "publisher": "CN=Tracked Publisher",
                "identity_name": "TrackedPublisher.PromptBoard",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    exe_path = tmp_path / "PromptBoard-1.1.1-win64.exe"
    exe_path.write_bytes(b"stub")
    icon_path = tmp_path / "PromptBoard.png"
    icon_path.write_bytes(b"png")

    class DummyPackager:
        last_instance = None

        def __init__(self, project_dir, app_name=None, config_file=None):
            self.project_dir = Path(project_dir)
            self.config = {}
            self.output_dir = self.project_dir / "store_package" / "PromptBoard"
            self.prepared_with = None
            DummyPackager.last_instance = self

        def prepare_package(self, icon_source=None, exe_path=None):
            self.prepared_with = {
                "icon_source": icon_source,
                "exe_path": exe_path,
            }
            self.output_dir.mkdir(parents=True, exist_ok=True)
            icons_dir = self.output_dir / "icons"
            icons_dir.mkdir(parents=True, exist_ok=True)
            for source_name in module.STORE_ASSET_FILENAMES:
                (icons_dir / source_name).write_bytes(b"png")
            return str(self.output_dir)

    class DummyModule:
        StorePackager = DummyPackager

    original_loader = module.load_store_packager
    try:
        module.load_store_packager = lambda root=None: DummyModule
        output_dir = module.prepare_store_package(tmp_path, explicit_exe=str(exe_path))
    finally:
        module.load_store_packager = original_loader

    instance = DummyPackager.last_instance
    assert instance is not None
    assert output_dir == instance.output_dir
    assert instance.config["publisher"] == "CN=Tracked Publisher"
    assert instance.config["identity_name"] == "TrackedPublisher.PromptBoard"
    assert instance.prepared_with["exe_path"] == str(exe_path.resolve())


def test_ensure_store_assets_copies_expected_logo_names(tmp_path):
    module = load_module()
    icons_dir = tmp_path / "icons"
    icons_dir.mkdir()
    for source_name in module.STORE_ASSET_FILENAMES:
        (icons_dir / source_name).write_bytes(b"png")

    assets_dir = module.ensure_store_assets(tmp_path, icons_dir=icons_dir)

    for target_name in module.STORE_ASSET_FILENAMES.values():
        assert (assets_dir / target_name).exists()
