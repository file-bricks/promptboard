"""Hermetische Vertragstests für Store-Materialien, Tier-2-Lokalisierung und Doku-Parität."""

from __future__ import annotations

import importlib.util
import json
import re
import struct
import xml.etree.ElementTree as ET
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TIER2_LANGUAGES = ["de-DE", "en-US", "es-ES", "zh-CN", "ja-JP", "ru-RU"]
TIER2_CODES = ["de", "en", "es", "zh", "ja", "ru"]
RESTRICTED_TRADEMARKS = [
    "windows",
    "microsoft",
    "office",
    "word",
    "apple",
    "ios",
    "android",
    "google",
    "adobe",
    "outlook",
    "gmail",
    "amazon",
    "netflix",
    "spotify",
]


def _load_readiness_module():
    path = PROJECT_ROOT / "scripts" / "check_store_readiness.py"
    spec = importlib.util.spec_from_file_location("check_store_readiness", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", f"{path.name} ist keine gültige PNG-Datei"
    return struct.unpack(">II", data[16:24])


def test_store_package_json_harmonized_tier2():
    data = json.loads((PROJECT_ROOT / "store_package.json").read_text(encoding="utf-8"))

    assert data["app_name"] == "PromptBoard"
    assert data["publisher"] == "CN=52596601-BAB4-4F3F-B182-E8F3F273B202"
    assert data["identity_name"] == "Geiger.PromptBoard"
    assert data["version"] == "1.1.3.0"
    assert data["executable"] == "PromptBoard-1.1.3-win64.exe"
    assert data["capabilities"] == "runFullTrust"
    assert data["languages"] == TIER2_LANGUAGES

    for code in TIER2_CODES:
        desc = data[f"description_{code}"]
        assert isinstance(desc, str) and desc.strip()
        assert len(desc) <= 100, f"description_{code} > 100 Zeichen ({len(desc)})"

        kws = data[f"keywords_{code}"]
        assert len(kws) == 7, f"keywords_{code} muss genau 7 Keywords enthalten"
        for kw in kws:
            assert len(kw) <= 30, f"Keyword '{kw}' überschreitet 30 Zeichen"
            for tm in RESTRICTED_TRADEMARKS:
                assert not re.search(rf"\b{re.escape(tm)}\b", kw.lower()), (
                    f"Verbotene Marke '{tm}' in Keyword '{kw}'"
                )


def test_appx_manifest_xml_and_six_resources():
    manifest = PROJECT_ROOT / "store_package" / "PromptBoard" / "AppxManifest.xml"
    assert manifest.is_file(), "AppxManifest.xml fehlt"

    root = ET.parse(manifest).getroot()
    ns = {
        "m": "http://schemas.microsoft.com/appx/manifest/foundation/windows10",
        "rescap": "http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities",
    }

    identity = root.find("m:Identity", ns)
    assert identity is not None
    assert identity.attrib.get("Name") == "Geiger.PromptBoard"
    assert identity.attrib.get("Publisher") == "CN=52596601-BAB4-4F3F-B182-E8F3F273B202"
    assert identity.attrib.get("Version") == "1.1.3.0"

    app_node = root.find(".//m:Application", ns)
    assert app_node is not None
    assert app_node.attrib.get("Executable") == "PromptBoard-1.1.3-win64.exe"

    caps = [c.attrib.get("Name") for c in root.findall(".//rescap:Capability", ns)]
    assert "runFullTrust" in caps

    manifest_langs = {
        r.attrib.get("Language", "").strip().lower()
        for r in root.findall(".//m:Resource", ns)
    }
    for lang in TIER2_LANGUAGES:
        assert lang.lower() in manifest_langs, f"Manifest-Sprache {lang} fehlt"


def test_store_listing_has_six_languages_and_policy_10_1_3_compliance():
    text = (PROJECT_ROOT / "STORE_LISTING.md").read_text(encoding="utf-8")

    for header in ["## Deutsch", "## English", "## Español", "## 简体中文", "## 日本語", "## Русский"]:
        assert header in text, f"Abschnitt '{header}' fehlt in STORE_LISTING.md"

    en_short = re.search(r"## English[\s\S]*?\*\*Short Description:\*\*\s*(.+)", text)
    assert en_short is not None
    en_short_val = en_short.group(1).strip()
    assert "Lokales Tray-Tool" not in en_short_val
    assert len(en_short_val) <= 100

    for umlaut in ("ä", "ö", "ü", "ß"):
        assert umlaut in text, f"Echter deutscher Umlaut '{umlaut}' fehlt in STORE_LISTING.md"


def test_windows_store_staging_directory_complete():
    staging = PROJECT_ROOT / "releases" / "windowsstore"
    assert staging.is_dir()

    for required in ("BUILD.md", "WACK_PROTOCOL.md", "store_settings.json", "StoreLogo.png"):
        assert (staging / required).is_file(), f"Staging-Datei fehlt: {required}"

    assert _png_size(staging / "StoreLogo.png") == (50, 50)

    settings = json.loads((staging / "store_settings.json").read_text(encoding="utf-8"))
    pkg = json.loads((PROJECT_ROOT / "store_package.json").read_text(encoding="utf-8"))
    assert settings["publisher"] == pkg["publisher"]
    assert settings["identity_name"] == pkg["identity_name"]
    assert settings["version"] == pkg["version"]
    assert settings["languages"] == pkg["languages"]

    for code in TIER2_CODES:
        listing_file = staging / f"store_listing_{code}.md"
        assert listing_file.is_file(), f"Staging-Listing fehlt: {listing_file.name}"
        content = listing_file.read_text(encoding="utf-8")
        assert "Short Description:" in content
        assert "Keywords:" in content
        assert len(content.strip()) >= 100


def test_store_assets_and_screenshots_present():
    assets = PROJECT_ROOT / "store_assets"
    expected_sizes = {
        "Square44x44Logo.png": (44, 44),
        "StoreLogo.png": (50, 50),
        "Square150x150Logo.png": (150, 150),
        "Wide310x150Logo.png": (310, 150),
        "Square310x310Logo.png": (310, 310),
    }
    for filename, size in expected_sizes.items():
        assert _png_size(assets / filename) == size

    shots_dir = PROJECT_ROOT / "README" / "screenshots" / "store"
    for shot in ("tray.png", "library.png", "editor.png", "settings.png"):
        assert (shots_dir / shot).is_file()


def test_readme_reciprocal_six_language_headers_and_llms_parity():
    readme_files = [
        "README.md",
        "README_de.md",
        "README_es.md",
        "README_zh.md",
        "README_ja.md",
        "README_ru.md",
    ]
    labels = ["Deutsch", "English", "Español", "简体中文", "日本語", "Русский"]
    for name in readme_files:
        path = PROJECT_ROOT / name
        assert path.is_file(), f"{name} fehlt"
        head = "\n".join(path.read_text(encoding="utf-8").splitlines()[:10])
        for label in labels:
            assert label in head, f"Sprachlink '{label}' fehlt in Kopfzeile von {name}"

    llms_text = (PROJECT_ROOT / "llms.txt").read_text(encoding="utf-8")
    llm_text = (PROJECT_ROOT / "llm.txt").read_text(encoding="utf-8")
    assert llms_text == llm_text, "llms.txt und llm.txt müssen synchron sein"
    for marker in ("de", "en", "es", "zh", "ja", "ru"):
        assert marker in llms_text


def test_check_store_readiness_script_passes_cleanly():
    module = _load_readiness_module()
    findings = module.run_store_readiness_check(PROJECT_ROOT, require_executable=False)
    assert findings == [], f"Store-Readiness-Findings unerwartet: {findings}"
