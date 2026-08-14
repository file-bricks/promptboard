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
    assert instance.prepared_with["icon_source"].endswith("PromptBoard.png")
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


def test_refresh_store_icons_uses_promptboard_png_and_updates_store_assets(tmp_path):
    module = load_module()
    (tmp_path / "PromptBoard.png").write_bytes(b"png")
    generated: list[dict[str, Path]] = []

    class DummyPackager:
        def __init__(self, project_dir, app_name=None, config_file=None):
            self.project_dir = Path(project_dir)
            self.output_dir = self.project_dir / "store_package" / "PromptBoard"

        def set_output_dir(self, path):
            self.output_dir = Path(path)

        def generate_icons(self, icon_source=None, output_dir=None):
            icons_dir = Path(output_dir)
            icons_dir.mkdir(parents=True, exist_ok=True)
            generated.append(
                {
                    "icon_source": Path(icon_source),
                    "output_dir": icons_dir,
                }
            )
            for source_name in module.STORE_ASSET_FILENAMES:
                (icons_dir / source_name).write_bytes(source_name.encode("utf-8"))
            return True

    class DummyModule:
        StorePackager = DummyPackager

    original_loader = module.load_store_packager
    try:
        module.load_store_packager = lambda root=None: DummyModule
        assets_dir = module.refresh_store_icons(tmp_path)
    finally:
        module.load_store_packager = original_loader

    assert generated
    assert generated[0]["icon_source"] == tmp_path / "PromptBoard.png"
    assert generated[0]["output_dir"] == tmp_path / "store_package" / "PromptBoard" / "icons"
    for source_name, target_name in module.STORE_ASSET_FILENAMES.items():
        assert (assets_dir / target_name).read_bytes() == source_name.encode("utf-8")


def test_latest_wack_report_uses_newest_xml(tmp_path):
    import os
    import time
    module = load_module()
    report_dir = tmp_path / "reports"
    report_dir.mkdir()
    older = report_dir / "wack_20260527_100000.xml"
    newer = report_dir / "wack_20260527_101500.xml"
    older.write_text("<REPORT><OVERALL_RESULT>PASS</OVERALL_RESULT></REPORT>", encoding="utf-8")
    newer.write_text("<REPORT><OVERALL_RESULT>FAIL</OVERALL_RESULT></REPORT>", encoding="utf-8")
    t_now = time.time()
    os.utime(older, (t_now - 2, t_now - 2))
    os.utime(newer, (t_now, t_now))

    latest = module.latest_wack_report(report_dir=report_dir)

    assert latest == newer.resolve()


def test_summarize_wack_report_counts_failures_and_warnings(tmp_path):
    module = load_module()
    report = tmp_path / "wack_report.xml"
    report.write_text(
        """<REPORT>
  <OVERALL_RESULT>FAIL</OVERALL_RESULT>
  <REQUIREMENTS>
    <REQUIREMENT>
      <TITLE>Supported APIs</TITLE>
      <OVERALL_RESULT>PASS</OVERALL_RESULT>
    </REQUIREMENT>
    <REQUIREMENT>
      <TITLE>Package integrity</TITLE>
      <OVERALL_RESULT>FAIL</OVERALL_RESULT>
      <TEST>
        <RESULT>FAIL</RESULT>
        <DESCRIPTION>Manifest entry is invalid.</DESCRIPTION>
      </TEST>
    </REQUIREMENT>
    <REQUIREMENT>
      <TITLE>Installability</TITLE>
      <OVERALL_RESULT>WARNING</OVERALL_RESULT>
      <TEST>
        <RESULT>WARNING</RESULT>
        <DESCRIPTION>Test environment skipped a signing check.</DESCRIPTION>
      </TEST>
    </REQUIREMENT>
  </REQUIREMENTS>
</REPORT>
""",
        encoding="utf-8",
    )

    summary = module.summarize_wack_report(report)
    rendered = module.format_wack_summary(summary)

    assert summary["overall_result"] == "FAIL"
    assert summary["pass_count"] == 1
    assert summary["fail_count"] == 1
    assert summary["warning_count"] == 1
    assert "Package integrity" in rendered
    assert "Manifest entry is invalid." in rendered
    assert "Installability" in rendered
