#!/usr/bin/env python3
"""Preflight Windows Store readiness audit for PromptBoard.

Prüft alle Windows Store Release Readiness Artefakte auf Vollständigkeit,
Konsistenz und Richtlinienkonformität nach dem Tier-2 6-Sprachen-Standard (Policy P-006).
"""

from __future__ import annotations

import argparse
import json
import re
import struct
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

APP_NAME = "PromptBoard"
EXPECTED_CANONICAL_PUBLISHER = "CN=52596601-BAB4-4F3F-B182-E8F3F273B202"
EXPECTED_IDENTITY_NAME = "Geiger.PromptBoard"
EXPECTED_VERSION = "1.1.3.0"
EXPECTED_EXECUTABLE = "PromptBoard-1.1.3-win64.exe"
TIER2_LANGUAGES = ["de-DE", "en-US", "es-ES", "zh-CN", "ja-JP", "ru-RU"]
TIER2_LANGUAGE_CODES = ["de", "en", "es", "zh", "ja", "ru"]

REQUIRED_DOCUMENTS = [
    "pyinstaller.spec",
    "build.bat",
    "build_store.bat",
    "store_package.json",
    "STORE_LISTING.md",
    "PRIVACY_POLICY.md",
    "THIRD_PARTY_LICENSES.txt",
    "LICENSE",
    "releases/windowsstore/BUILD.md",
    "releases/windowsstore/WACK_PROTOCOL.md",
    "releases/windowsstore/store_settings.json",
    "releases/windowsstore/StoreLogo.png",
    "releases/windowsstore/store_listing_de.md",
    "releases/windowsstore/store_listing_en.md",
    "releases/windowsstore/store_listing_es.md",
    "releases/windowsstore/store_listing_zh.md",
    "releases/windowsstore/store_listing_ja.md",
    "releases/windowsstore/store_listing_ru.md",
]

REQUIRED_PACKAGE_ICONS = {
    "icon_44x44.png": (44, 44),
    "icon_50x50.png": (50, 50),
    "icon_150x150.png": (150, 150),
    "icon_310x150.png": (310, 150),
    "icon_310x310.png": (310, 310),
}

REQUIRED_STORE_ASSETS = {
    "Square44x44Logo.png": (44, 44),
    "StoreLogo.png": (50, 50),
    "Square150x150Logo.png": (150, 150),
    "Wide310x150Logo.png": (310, 150),
    "Square310x310Logo.png": (310, 310),
}

REQUIRED_STORE_SCREENSHOTS = [
    "tray.png",
    "library.png",
    "editor.png",
    "settings.png",
]

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


def _ensure_utf8_streams() -> None:
    """Sichert UTF-8-Konsolen-Encoding unter Windows für stdout und stderr."""
    for stream in (sys.stdout, sys.stderr):
        if stream and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError, AttributeError):
                pass


def _png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"{path.name} ist keine gültige PNG-Datei")
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def _check_keywords_and_descriptions(
    data: dict,
    source_label: str,
    findings: list[str],
) -> None:
    for code in TIER2_LANGUAGE_CODES:
        desc_k = f"description_{code}"
        desc_val = data.get(desc_k)
        if isinstance(desc_val, str) and desc_val.strip():
            if len(desc_val) > 100:
                findings.append(
                    f"{source_label} {desc_k} überschreitet 100 Zeichen ({len(desc_val)})"
                )
        else:
            findings.append(f"{source_label}: {desc_k} fehlt oder ist leer")

        kw_k = f"keywords_{code}"
        kws = data.get(kw_k)
        if isinstance(kws, list):
            if len(kws) != 7:
                findings.append(
                    f"{source_label} {kw_k} hat {len(kws)} Keywords (genau 7 erwartet)"
                )
            for kw in kws:
                kw_str = str(kw).strip()
                if not kw_str:
                    findings.append(f"{source_label} {kw_k} enthält ein leeres Keyword")
                elif len(kw_str) > 30:
                    findings.append(
                        f"{source_label} {kw_k} Keyword '{kw_str}' > 30 Zeichen"
                    )
                for tm in RESTRICTED_TRADEMARKS:
                    if re.search(rf"\b{re.escape(tm)}\b", kw_str.lower()):
                        findings.append(
                            f"{source_label} {kw_k} enthält geschützte Drittmarke '{tm}' in '{kw_str}'"
                        )
        else:
            findings.append(f"{source_label}: {kw_k} fehlt oder ist keine Liste")


def _extract_listing_sections(content: str) -> dict[str, str]:
    headers = [
        ("de", "## Deutsch"),
        ("en", "## English"),
        ("es", "## Español"),
        ("zh", "## 简体中文"),
        ("ja", "## 日本語"),
        ("ru", "## Русский"),
    ]
    positions: list[tuple[int, str]] = []
    for code, header in headers:
        idx = content.find(header)
        if idx != -1:
            positions.append((idx, code))
    positions.sort()

    sections: dict[str, str] = {}
    for pos_i, (start_idx, code) in enumerate(positions):
        end_idx = positions[pos_i + 1][0] if pos_i + 1 < len(positions) else len(content)
        sections[code] = content[start_idx:end_idx]
    return sections


def run_store_readiness_check(
    project_root: Path | None = None,
    *,
    require_executable: bool = False,
) -> list[str]:
    if project_root is None:
        project_root = Path(__file__).resolve().parents[1]

    findings: list[str] = []

    # 1. Document Existence Check
    for doc in REQUIRED_DOCUMENTS:
        if not (project_root / doc).exists():
            findings.append(f"Fehlendes Store-Pflichtdokument: {doc}")

    # 2. store_package.json Validation
    package_json_path = project_root / "store_package.json"
    package_data: dict = {}
    if package_json_path.exists():
        try:
            package_data = json.loads(package_json_path.read_text(encoding="utf-8"))
            if package_data.get("app_name") != APP_NAME:
                findings.append(
                    f"Ungültiger app_name in store_package.json: {package_data.get('app_name')}"
                )
            if package_data.get("identity_name") != EXPECTED_IDENTITY_NAME:
                findings.append(
                    f"Ungültiger identity_name in store_package.json: {package_data.get('identity_name')}"
                )
            if package_data.get("publisher") != EXPECTED_CANONICAL_PUBLISHER:
                findings.append(
                    f"Publisher stimmt nicht mit kanonischem CN überein: {package_data.get('publisher')}"
                )
            if package_data.get("version") != EXPECTED_VERSION:
                findings.append(
                    f"Version in store_package.json != {EXPECTED_VERSION}: {package_data.get('version')}"
                )
            if package_data.get("executable") != EXPECTED_EXECUTABLE:
                findings.append(
                    f"Executable in store_package.json != {EXPECTED_EXECUTABLE}: {package_data.get('executable')}"
                )
            base_desc = str(package_data.get("description", ""))
            if not base_desc.strip() or len(base_desc) > 100:
                findings.append(
                    f"store_package.json description ungültig oder > 100 Zeichen ({len(base_desc)})"
                )
            if "runFullTrust" not in str(package_data.get("capabilities", "")):
                findings.append("Fehlende Berechtigung runFullTrust in store_package.json")
            for url_field in ("privacy_url", "support_url"):
                url_val = str(package_data.get(url_field, ""))
                if not url_val.startswith("https://"):
                    findings.append(f"store_package.json {url_field} muss HTTPS verwenden: {url_val}")

            languages = package_data.get("languages", [])
            if not isinstance(languages, list) or any(lang not in languages for lang in TIER2_LANGUAGES):
                findings.append(
                    f"store_package.json: Tier-2 Zielsprachen unvollständig ({TIER2_LANGUAGES})"
                )

            _check_keywords_and_descriptions(package_data, "store_package.json", findings)
        except Exception as exc:
            findings.append(f"store_package.json Parsefehler: {exc}")

    # 3. Executable Validation (if required)
    if require_executable:
        exe_name = package_data.get("executable", EXPECTED_EXECUTABLE)
        candidates = [
            project_root / "dist" / exe_name,
            project_root / "releases" / "v1.1.3" / exe_name,
        ]
        if not any(c.exists() for c in candidates):
            findings.append(f"Store-Executable nicht gefunden ({exe_name} in dist/ oder releases/v1.1.3/)")

    # 4. STORE_LISTING.md Validation (Tier-2 6 Sprachen & Policy 10.1.3)
    listing_path = project_root / "STORE_LISTING.md"
    if listing_path.exists():
        content = listing_path.read_text(encoding="utf-8")
        sections = _extract_listing_sections(content)
        expected_headers = {
            "de": "## Deutsch",
            "en": "## English",
            "es": "## Español",
            "zh": "## 简体中文",
            "ja": "## 日本語",
            "ru": "## Русский",
        }
        for code, header in expected_headers.items():
            if code not in sections:
                findings.append(f"STORE_LISTING.md: Abschnitt '{header}' fehlt")
                continue
            sec = sections[code]
            short_match = re.search(
                r"\*\*(?:Kurzbeschreibung|Short Description|Descripción corta|简短描述|短い説明|Краткое описание):\*\*\s*(.+)",
                sec,
            )
            if not short_match:
                findings.append(f"STORE_LISTING.md ({header}): Kurzbeschreibung fehlt")
            else:
                short_text = short_match.group(1).strip()
                if len(short_text) > 100:
                    findings.append(
                        f"STORE_LISTING.md ({header}): Kurzbeschreibung > 100 Zeichen ({len(short_text)})"
                    )
                if code == "en" and "Lokales Tray-Tool" in short_text:
                    findings.append(
                        "STORE_LISTING.md (English): Short Description enthält noch deutschen Text"
                    )

            kw_match = re.search(
                r"###\s*(?:Keywords|Palabras clave|关键词|キーワード|Ключевые слова)\s*\n+([^\n#]+)",
                sec,
            )
            if not kw_match:
                findings.append(f"STORE_LISTING.md ({header}): Keywords-Zeile fehlt")
            else:
                kws = [k.strip() for k in kw_match.group(1).split(",") if k.strip()]
                if not (1 <= len(kws) <= 7):
                    findings.append(
                        f"STORE_LISTING.md ({header}): {len(kws)} Keywords (1..7 erlaubt)"
                    )
                for kw in kws:
                    if len(kw) > 30:
                        findings.append(
                            f"STORE_LISTING.md ({header}): Keyword '{kw}' > 30 Zeichen"
                        )
                    for tm in RESTRICTED_TRADEMARKS:
                        if re.search(rf"\b{re.escape(tm)}\b", kw.lower()):
                            findings.append(
                                f"STORE_LISTING.md ({header}): geschützte Drittmarke '{tm}' in '{kw}'"
                            )

    # 5. Store Assets & Package Icons Validation
    assets_dir = project_root / "store_assets"
    if not assets_dir.exists():
        findings.append(f"store_assets Verzeichnis fehlt: {assets_dir}")
    else:
        for asset_name, req_size in REQUIRED_STORE_ASSETS.items():
            asset_file = assets_dir / asset_name
            if not asset_file.exists():
                findings.append(f"Pflicht-Asset fehlt in store_assets: {asset_name}")
            else:
                try:
                    w, h = _png_size(asset_file)
                    if (w, h) != req_size:
                        findings.append(
                            f"Falsche Bildgröße für store_assets/{asset_name}: ({w}, {h}) != {req_size}"
                        )
                except Exception as exc:
                    findings.append(f"Ungültiges PNG store_assets/{asset_name}: {exc}")

    pkg_icons_dir = project_root / "store_package" / APP_NAME / "icons"
    if not pkg_icons_dir.exists():
        findings.append(f"Icons-Verzeichnis fehlt: {pkg_icons_dir}")
    else:
        for icon_name, req_size in REQUIRED_PACKAGE_ICONS.items():
            icon_file = pkg_icons_dir / icon_name
            if not icon_file.exists():
                findings.append(f"Store-Icon fehlt in store_package: {icon_name}")
            else:
                try:
                    w, h = _png_size(icon_file)
                    if (w, h) != req_size:
                        findings.append(
                            f"Falsche Bildgröße für {icon_name}: ({w}, {h}) != {req_size}"
                        )
                except Exception as exc:
                    findings.append(f"Ungültiges PNG {icon_name}: {exc}")

    # 6. Screenshots Validation
    shots_dir = project_root / "README" / "screenshots" / "store"
    if not shots_dir.exists():
        findings.append(f"Store-Screenshots-Verzeichnis fehlt: {shots_dir}")
    else:
        for shot_name in REQUIRED_STORE_SCREENSHOTS:
            shot_file = shots_dir / shot_name
            if not shot_file.exists():
                findings.append(f"Store-Screenshot fehlt: README/screenshots/store/{shot_name}")
            else:
                try:
                    _png_size(shot_file)
                except Exception as exc:
                    findings.append(f"Ungültiges Screenshot-PNG {shot_name}: {exc}")

    # 7. AppxManifest.xml Validation
    manifest_path = project_root / "store_package" / APP_NAME / "AppxManifest.xml"
    if not manifest_path.exists():
        findings.append(f"AppxManifest.xml fehlt: {manifest_path}")
    else:
        try:
            tree = ET.parse(manifest_path)
            root = tree.getroot()
            ns = {
                "m": "http://schemas.microsoft.com/appx/manifest/foundation/windows10",
                "uap": "http://schemas.microsoft.com/appx/manifest/uap/windows10",
                "rescap": "http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities",
            }
            identity = root.find("m:Identity", ns)
            if identity is None:
                findings.append("AppxManifest.xml: <Identity> fehlt")
            else:
                if identity.attrib.get("Name") != EXPECTED_IDENTITY_NAME:
                    findings.append(
                        f"AppxManifest.xml Identity Name != {EXPECTED_IDENTITY_NAME}: {identity.attrib.get('Name')}"
                    )
                if identity.attrib.get("Publisher") != EXPECTED_CANONICAL_PUBLISHER:
                    findings.append(
                        f"AppxManifest.xml Identity Publisher != {EXPECTED_CANONICAL_PUBLISHER}: {identity.attrib.get('Publisher')}"
                    )
                if identity.attrib.get("Version") != EXPECTED_VERSION:
                    findings.append(
                        f"AppxManifest.xml Identity Version != {EXPECTED_VERSION}: {identity.attrib.get('Version')}"
                    )

            has_run_full_trust = any(
                cap.attrib.get("Name") == "runFullTrust"
                for cap in root.findall(".//rescap:Capability", ns) + root.findall(".//m:Capability", ns)
            )
            if not has_run_full_trust:
                findings.append("AppxManifest.xml: Capability runFullTrust fehlt")

            app_node = root.find(".//m:Application", ns)
            if app_node is None or app_node.attrib.get("Executable") != EXPECTED_EXECUTABLE:
                findings.append(
                    f"AppxManifest.xml: Application Executable != {EXPECTED_EXECUTABLE}"
                )

            manifest_langs = {
                r.attrib.get("Language", "").strip().lower()
                for r in root.findall(".//m:Resource", ns)
            }
            for req_lang in TIER2_LANGUAGES:
                if req_lang.lower() not in manifest_langs:
                    findings.append(f"AppxManifest.xml: Resource Language '{req_lang}' fehlt")
        except Exception as exc:
            findings.append(f"AppxManifest.xml Parsefehler: {exc}")

    # 8. Release Staging Consistency (releases/windowsstore/)
    staging_dir = project_root / "releases" / "windowsstore"
    if staging_dir.exists():
        staging_logo = staging_dir / "StoreLogo.png"
        if staging_logo.exists():
            try:
                w, h = _png_size(staging_logo)
                if (w, h) != (50, 50):
                    findings.append(
                        f"releases/windowsstore/StoreLogo.png hat Größe ({w}, {h}) != (50, 50)"
                    )
            except Exception as exc:
                findings.append(f"releases/windowsstore/StoreLogo.png Lesefehler: {exc}")

        settings_file = staging_dir / "store_settings.json"
        if settings_file.exists():
            try:
                s_data = json.loads(settings_file.read_text(encoding="utf-8"))
                if s_data.get("publisher") != EXPECTED_CANONICAL_PUBLISHER:
                    findings.append(
                        f"releases/windowsstore/store_settings.json publisher mismatch: {s_data.get('publisher')}"
                    )
                if s_data.get("identity_name") != EXPECTED_IDENTITY_NAME:
                    findings.append(
                        f"releases/windowsstore/store_settings.json identity mismatch: {s_data.get('identity_name')}"
                    )
                if s_data.get("version") != EXPECTED_VERSION:
                    findings.append(
                        f"releases/windowsstore/store_settings.json version mismatch: {s_data.get('version')}"
                    )
                s_langs = s_data.get("languages", [])
                for req_lang in TIER2_LANGUAGES:
                    if req_lang not in s_langs:
                        findings.append(f"store_settings.json: Sprache {req_lang} fehlt")
                _check_keywords_and_descriptions(
                    s_data, "releases/windowsstore/store_settings.json", findings
                )
            except Exception as exc:
                findings.append(f"store_settings.json Parsefehler: {exc}")

        for code in TIER2_LANGUAGE_CODES:
            lf = staging_dir / f"store_listing_{code}.md"
            if lf.exists():
                lf_text = lf.read_text(encoding="utf-8")
                if len(lf_text.strip()) < 50:
                    findings.append(f"releases/windowsstore/{lf.name} zu kurz (< 50 Zeichen)")
                if "Keywords:" not in lf_text or "Short Description:" not in lf_text:
                    findings.append(
                        f"releases/windowsstore/{lf.name} fehlt 'Short Description:' oder 'Keywords:'"
                    )

    return findings


def main(argv: list[str] | None = None) -> int:
    _ensure_utf8_streams()
    parser = argparse.ArgumentParser(description="PromptBoard Preflight Store Readiness Audit")
    parser.add_argument(
        "--require-exe",
        action="store_true",
        help="Prüft zwingend das Vorhandensein des kompilierten Executables",
    )
    args = parser.parse_args(argv)

    findings = run_store_readiness_check(require_executable=args.require_exe)
    if findings:
        print(f"[FEHLER] Preflight-Store-Audit fehlgeschlagen ({len(findings)} Findings):")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("[OK] Preflight-Store-Audit erfolgreich: Alle Kriterien erfüllt (0 Findings)!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
