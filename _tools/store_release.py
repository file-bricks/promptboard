from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Mapping

APP_NAME = "PromptBoard"
APP_VERSION = "1.1.1"
STORE_VERSION = "1.1.1.0"
APP_EXECUTABLE = f"{APP_NAME}-{APP_VERSION}-win64.exe"
STORE_CONFIG_NAME = "store_package.json"
LOCAL_STORE_CONFIG_NAME = "store_package.local.json"
STORE_ICON_SOURCE_NAME = "PromptBoard.png"
STORE_CONFIG_DEFAULTS = {
    "app_name": APP_NAME,
    "publisher": "CN=YourPublisher",
    "publisher_display": "Lukas Geiger",
    "identity_name": "YourPublisher.PromptBoard",
    "version": STORE_VERSION,
    "description": "Lokales Tray-Tool für Prompts, Skills, Workflows, Rollen und Agenten.",
    "executable": APP_EXECUTABLE,
    "capabilities": "runFullTrust",
    "category": "Productivity",
    "age_rating": "3+",
    "privacy_url": "https://github.com/file-bricks/promptboard/blob/main/PRIVACY_POLICY.md",
    "support_url": "https://github.com/file-bricks/promptboard/issues",
}
PLACEHOLDER_VALUES = {
    "publisher": {"CN=YourPublisher", ""},
    "identity_name": {"YourPublisher.PromptBoard", ""},
}
TEST_STORE_OVERRIDES = {
    "publisher": "CN=PromptBoard Test",
    "identity_name": "PromptBoard.Test",
}
STORE_ENV_OVERRIDES = {
    "publisher": "PROMPTBOARD_STORE_PUBLISHER",
    "publisher_display": "PROMPTBOARD_STORE_PUBLISHER_DISPLAY",
    "identity_name": "PROMPTBOARD_STORE_IDENTITY_NAME",
}
STORE_ASSET_FILENAMES = {
    "icon_44x44.png": "Square44x44Logo.png",
    "icon_150x150.png": "Square150x150Logo.png",
    "icon_310x150.png": "Wide310x150Logo.png",
    "icon_310x310.png": "Square310x310Logo.png",
}
WACK_REPORT_DIRNAME = "test_reports"
WIDE_LOGO_SIZE = (310, 150)
WIDE_LOGO_PADDING = 8
WIDE_LOGO_FILENAME = "Wide310x150Logo.png"


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def software_root(root: Path | None = None) -> Path:
    base = root or project_root()
    return base.parent.parent


def store_tool_path(root: Path | None = None) -> Path:
    return software_root(root) / "_STORE" / "store_packager.py"


def build_store_config() -> dict[str, str]:
    return normalize_store_config(dict(STORE_CONFIG_DEFAULTS))


def store_config_path(root: Path | None = None) -> Path:
    base = root or project_root()
    return base / STORE_CONFIG_NAME


def local_store_config_path(root: Path | None = None) -> Path:
    base = root or project_root()
    return base / LOCAL_STORE_CONFIG_NAME


def store_icon_source_path(root: Path | None = None) -> Path:
    base = root or project_root()
    return base / STORE_ICON_SOURCE_NAME


def read_json_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Ungültige Store-Konfiguration in {path}: Objekt erwartet.")
    return {str(key): str(value) for key, value in data.items()}


def normalize_capabilities(value: str) -> str:
    capabilities = [cap.strip() for cap in value.split(",") if cap.strip()]
    if "runFullTrust" not in capabilities:
        capabilities.insert(0, "runFullTrust")
    return ",".join(dict.fromkeys(capabilities))


def normalize_store_config(config: Mapping[str, str]) -> dict[str, str]:
    normalized = {str(key): str(value) for key, value in config.items()}
    normalized["capabilities"] = normalize_capabilities(normalized.get("capabilities", ""))
    return normalized


def environment_store_overrides(environ: Mapping[str, str] | None = None) -> dict[str, str]:
    source = environ or os.environ
    overrides: dict[str, str] = {}
    for field, env_name in STORE_ENV_OVERRIDES.items():
        value = source.get(env_name, "").strip()
        if value:
            overrides[field] = value
    return overrides


def load_store_config(
    root: Path | None = None,
    *,
    include_local_overrides: bool = True,
    environ: Mapping[str, str] | None = None,
) -> dict[str, str]:
    base = root or project_root()
    config = build_store_config()
    config.update(read_json_file(store_config_path(base)))
    if include_local_overrides:
        config.update(read_json_file(local_store_config_path(base)))
        config.update(environment_store_overrides(environ))
    return normalize_store_config(config)


def is_placeholder_value(field: str, value: str) -> bool:
    return value.strip() in PLACEHOLDER_VALUES.get(field, set())


def unresolved_store_fields(config: Mapping[str, str]) -> list[str]:
    unresolved = []
    for field in ("publisher", "identity_name"):
        value = str(config.get(field, ""))
        if is_placeholder_value(field, value):
            unresolved.append(field)
    return unresolved


def assert_store_ready(config: Mapping[str, str]) -> None:
    unresolved = unresolved_store_fields(config)
    if unresolved:
        raise ValueError(
            "Partner-Center-Werte fehlen noch: "
            f"{', '.join(unresolved)}. Trage sie in {STORE_CONFIG_NAME}, "
            f"{LOCAL_STORE_CONFIG_NAME} oder per Umgebungsvariablen ein "
            "(PROMPTBOARD_STORE_PUBLISHER, PROMPTBOARD_STORE_IDENTITY_NAME)."
        )


def build_store_listing(config: Mapping[str, str]) -> str:
    description_de = (
        "PromptBoard ist ein leichtgewichtiges, offline-first Desktop-Werkzeug für wiederverwendbare "
        "LLM-Bausteine. Die App verwaltet Prompts, Skills, Workflows, Rollen und "
        "Agenten lokal, bietet schnellen Tray-Zugriff, globale Hotkeys, DE/EN-Live-Wechsel "
        "und Markdown-Materialisierung ohne Cloud-Zwang."
    )
    description_en = (
        "PromptBoard is a lightweight, offline-first desktop utility for reusable LLM building blocks. "
        "It keeps prompts, skills, workflows, roles, and agents local, adds quick tray "
        "access, global hotkeys, live DE/EN switching, and Markdown materialization "
        "without mandatory cloud sync."
    )
    return (
        f"# Store Listing - {config['app_name']}\n\n"
        "Stand: 2026-05-24\n\n"
        "## Deutsch\n\n"
        f"**Name:** {config['app_name']}  \n"
        f"**Kurzbeschreibung:** {config['description']}  \n"
        f"**Kategorie:** {config['category']}  \n"
        f"**Altersfreigabe:** {config['age_rating']}\n\n"
        "### Beschreibung\n\n"
        f"{description_de}\n\n"
        "### Keywords\n\n"
        "Prompt, LLM, AI, Tray, Productivity, Markdown, Clipboard, Workflow, Skills, Agenten\n\n"
        "---\n\n"
        "## English\n\n"
        f"**Name:** {config['app_name']}  \n"
        f"**Short Description:** {config['description']}  \n"
        f"**Category:** {config['category']}  \n"
        f"**Age Rating:** {config['age_rating']}\n\n"
        "### Description\n\n"
        f"{description_en}\n\n"
        "### Keywords\n\n"
        "Prompt, LLM, AI, tray, productivity, Markdown, clipboard, workflow, skills, agents\n"
    )


def write_root_files(root: Path | None = None) -> tuple[Path, Path]:
    base = root or project_root()
    config = load_store_config(base, include_local_overrides=False)
    config_path = store_config_path(base)
    config_path.write_text(
        json.dumps(config, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    listing_path = base / "STORE_LISTING.md"
    listing_path.write_text(build_store_listing(config), encoding="utf-8")
    return config_path, listing_path


def ensure_store_assets(root: Path | None = None, *, icons_dir: Path | None = None) -> Path:
    base = root or project_root()
    source_dir = icons_dir or (base / "store_package" / APP_NAME / "icons")
    if not source_dir.exists():
        raise FileNotFoundError(f"Store-Icons nicht gefunden: {source_dir}")

    assets_dir = base / "store_assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    for source_name, target_name in STORE_ASSET_FILENAMES.items():
        source_path = source_dir / source_name
        if not source_path.exists():
            raise FileNotFoundError(f"Store-Icon fehlt: {source_path}")
        shutil.copy2(source_path, assets_dir / target_name)

    return assets_dir


def refresh_store_icons(root: Path | None = None) -> Path:
    """Regenerate Store/MSIX logos from the canonical PromptBoard app icon."""
    base = root or project_root()
    source = store_icon_source_path(base)
    if not source.exists():
        raise FileNotFoundError(f"Store-Icon-Quelle nicht gefunden: {source}")

    module = load_store_packager(base)
    packager = module.StorePackager(str(base), app_name=APP_NAME, config_file=str(store_config_path(base)))
    if hasattr(packager, "set_output_dir"):
        packager.set_output_dir(base / "store_package" / APP_NAME)
    icons_dir = base / "store_package" / APP_NAME / "icons"
    result = packager.generate_icons(str(source), output_dir=icons_dir)
    if result is False:
        raise RuntimeError(f"Store-Icon-Generierung fehlgeschlagen: {source}")
    assets_dir = ensure_store_assets(base, icons_dir=icons_dir)
    # U7: the generic packager stretches the square motif onto the 310x150 wide
    # tile. Rebuild it proportionally — best effort, so a missing PIL or an
    # unreadable source never breaks the icon refresh.
    try:
        regenerate_wide_logo(base)
    except Exception as exc:  # noqa: BLE001
        print(f"[!] Wide-Logo-Proportionsfix uebersprungen: {exc}")
    return assets_dir


def regenerate_wide_logo(
    root: Path | None = None,
    *,
    source: Path | None = None,
    target: Path | None = None,
) -> Path:
    """Rebuild the wide store logo, fitting the motif proportionally (U7).

    The generic store packager scales the square app icon to 310x150, which
    stretches the skateboard horizontally. Instead, contain-fit the motif
    (preserving aspect ratio), centered on a transparent 310x150 canvas.
    """
    from PIL import Image  # dev-only dependency, imported lazily

    base = root or project_root()
    src = Path(source) if source else store_icon_source_path(base)
    dst = Path(target) if target else (base / "store_assets" / WIDE_LOGO_FILENAME)
    if not src.exists():
        raise FileNotFoundError(f"Icon-Quelle nicht gefunden: {src}")

    motif = Image.open(src).convert("RGBA")
    # Trim fully transparent margins so padding is applied to the actual motif.
    bbox = motif.getbbox()
    if bbox:
        motif = motif.crop(bbox)

    canvas_w, canvas_h = WIDE_LOGO_SIZE
    max_w = canvas_w - 2 * WIDE_LOGO_PADDING
    max_h = canvas_h - 2 * WIDE_LOGO_PADDING
    scale = min(max_w / motif.width, max_h / motif.height)
    new_w = max(1, round(motif.width * scale))
    new_h = max(1, round(motif.height * scale))
    resized = motif.resize((new_w, new_h), Image.LANCZOS)

    canvas = Image.new("RGBA", WIDE_LOGO_SIZE, (0, 0, 0, 0))
    offset = ((canvas_w - new_w) // 2, (canvas_h - new_h) // 2)
    canvas.paste(resized, offset, resized)

    dst.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(dst, format="PNG")
    return dst


def resolve_executable(root: Path | None = None, explicit: str | None = None) -> Path:
    base = root or project_root()
    candidates = []
    if explicit:
        candidates.append(Path(explicit))
    candidates.extend(
        [
            base / "dist" / APP_EXECUTABLE,
            base / "releases" / f"v{APP_VERSION}" / APP_EXECUTABLE,
        ]
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    raise FileNotFoundError(
        f"Keine PromptBoard-EXE gefunden. Erwartet z. B. {APP_EXECUTABLE} in dist/ oder releases/v{APP_VERSION}/."
    )


def resolve_msix(root: Path | None = None, explicit: str | None = None) -> Path:
    base = root or project_root()
    candidates = []
    if explicit:
        candidates.append(Path(explicit))
    candidates.append(base / "releases" / f"{APP_NAME}.msix")
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    raise FileNotFoundError(
        f"Keine PromptBoard-MSIX gefunden. Erwartet z. B. {APP_NAME}.msix in releases/."
    )


def default_wack_report_dir(root: Path | None = None) -> Path:
    base = root or project_root()
    return base / "releases" / WACK_REPORT_DIRNAME


def latest_wack_report(root: Path | None = None, *, report_dir: Path | None = None) -> Path:
    target_dir = report_dir or default_wack_report_dir(root)
    if not target_dir.exists():
        raise FileNotFoundError(f"WACK-Report-Verzeichnis nicht gefunden: {target_dir}")

    candidates = sorted(
        target_dir.glob("wack_*.xml"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError(f"Keine WACK-XML-Reports gefunden in: {target_dir}")
    return candidates[0].resolve()


def summarize_wack_report(report_path: str | Path) -> dict[str, Any]:
    resolved = Path(report_path).resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"WACK-Report nicht gefunden: {resolved}")

    root = ET.fromstring(resolved.read_text(encoding="utf-8"))
    requirements = []
    pass_count = 0
    fail_count = 0
    warning_count = 0

    for requirement in root.findall("./REQUIREMENTS/REQUIREMENT"):
        title = (requirement.findtext("TITLE") or "").strip() or "Unbenannter Test"
        result = (requirement.findtext("OVERALL_RESULT") or "UNKNOWN").strip() or "UNKNOWN"
        details = []
        for test in requirement.findall("TEST"):
            test_result = (test.findtext("RESULT") or "").strip()
            description = (test.findtext("DESCRIPTION") or "").strip()
            if test_result in {"FAIL", "WARNING"} and description:
                details.append(description)

        requirements.append(
            {
                "title": title,
                "result": result,
                "details": details,
            }
        )

        if result == "PASS":
            pass_count += 1
        elif result == "FAIL":
            fail_count += 1
        elif result == "WARNING":
            warning_count += 1

    return {
        "report_path": resolved,
        "overall_result": (root.findtext("OVERALL_RESULT") or "UNKNOWN").strip() or "UNKNOWN",
        "pass_count": pass_count,
        "fail_count": fail_count,
        "warning_count": warning_count,
        "requirements": requirements,
    }


def format_wack_summary(summary: Mapping[str, Any]) -> str:
    lines = [
        f"Report: {summary['report_path']}",
        f"Gesamtergebnis: {summary['overall_result']}",
        f"PASS {summary['pass_count']} | FAIL {summary['fail_count']} | WARNING {summary['warning_count']}",
    ]

    for requirement in summary["requirements"]:
        if requirement["result"] == "PASS":
            continue
        lines.append(f"- {requirement['result']}: {requirement['title']}")
        for detail in requirement["details"]:
            lines.append(f"  -> {detail}")

    return "\n".join(lines)


def load_store_packager(root: Path | None = None) -> Any:
    tool_path = store_tool_path(root)
    spec = importlib.util.spec_from_file_location("store_packager", tool_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"StorePackager konnte nicht geladen werden: {tool_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prepare_store_package(root: Path | None = None, explicit_exe: str | None = None) -> Path:
    base = root or project_root()
    config_path, _listing_path = write_root_files(base)
    effective_config = load_store_config(base)
    assert_store_ready(effective_config)
    executable = resolve_executable(base, explicit=explicit_exe)
    module = load_store_packager(base)
    packager = module.StorePackager(str(base), app_name=APP_NAME, config_file=str(config_path))
    packager.config.update(effective_config)
    packager.prepare_package(
        icon_source=str(store_icon_source_path(base)),
        exe_path=str(executable),
    )
    ensure_store_assets(base, icons_dir=packager.output_dir / "icons")
    return Path(packager.output_dir)


def with_test_overrides_if_needed(
    config: Mapping[str, str],
    *,
    allow_test_identity: bool = False,
) -> dict[str, str]:
    effective = dict(config)
    if allow_test_identity:
        for field, value in TEST_STORE_OVERRIDES.items():
            if field in unresolved_store_fields(effective):
                effective[field] = value
    return normalize_store_config(effective)


def build_msix_preflight(
    root: Path | None = None,
    *,
    explicit_exe: str | None = None,
    allow_test_identity: bool = False,
) -> Path:
    base = root or project_root()
    effective_config = with_test_overrides_if_needed(
        load_store_config(base),
        allow_test_identity=allow_test_identity,
    )
    assert_store_ready(effective_config)

    config_path = store_config_path(base)
    original_config_text = config_path.read_text(encoding="utf-8") if config_path.exists() else None
    try:
        config_path.write_text(
            json.dumps(effective_config, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        prepare_store_package(base, explicit_exe=explicit_exe)
        executable = resolve_executable(base, explicit=explicit_exe)
        command = [
            "powershell",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(software_root(base) / "_STORE" / "msstore_build_msix.ps1"),
            "-ProjectRoot",
            str(base),
            "-ExePath",
            str(executable),
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(
                "MSIX-Build fehlgeschlagen:\n"
                f"{result.stdout}{result.stderr}"
            )
        return base / "releases" / f"{APP_NAME}.msix"
    finally:
        if original_config_text is None:
            config_path.unlink(missing_ok=True)
        else:
            config_path.write_text(original_config_text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="PromptBoard Windows-Store Vorbereitung")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("write-root-files", help="store_package.json und STORE_LISTING.md schreiben")
    subparsers.add_parser("check", help="Store-Konfiguration auf echte Partner-Center-Werte prüfen")
    subparsers.add_parser(
        "refresh-icons",
        help="Store-/MSIX-Logos aus PromptBoard.png neu erzeugen",
    )
    subparsers.add_parser(
        "refresh-wide-logo",
        help="Nur Wide310x150Logo.png proportionsgetreu aus PromptBoard.png neu erzeugen",
    )

    prepare_parser = subparsers.add_parser("prepare", help="Store-Paket-Staging erzeugen")
    prepare_parser.add_argument("--exe", help="Pfad zur PromptBoard-EXE")

    msix_parser = subparsers.add_parser(
        "msix-preflight",
        help="Store-Staging plus generischen MSIX-Build mit effektiver Konfiguration ausführen",
    )
    msix_parser.add_argument("--exe", help="Pfad zur PromptBoard-EXE")
    msix_parser.add_argument(
        "--use-test-identity",
        action="store_true",
        help="Für lokalen Preflight gültige Testwerte nutzen, falls noch keine echten Partner-Center-Werte gesetzt sind.",
    )

    report_parser = subparsers.add_parser(
        "review-wack-report",
        help="Neueste oder explizite WACK-XML laden und kompakt auswerten",
    )
    report_parser.add_argument("--report", help="Pfad zu einem konkreten WACK-XML-Report")
    report_parser.add_argument(
        "--report-dir",
        help=f"Report-Verzeichnis (Default: releases\\{WACK_REPORT_DIRNAME})",
    )

    args = parser.parse_args()

    try:
        if args.command == "write-root-files":
            config_path, listing_path = write_root_files()
            print(f"[+] Geschrieben: {config_path}")
            print(f"[+] Geschrieben: {listing_path}")
            return

        if args.command == "check":
            config = load_store_config()
            assert_store_ready(config)
            print("[+] Store-Konfiguration ist für den echten Partner-Center-Lauf bereit.")
            return

        if args.command == "refresh-icons":
            assets_dir = refresh_store_icons()
            print(f"[+] Store-Icons aktualisiert: {assets_dir}")
            return

        if args.command == "refresh-wide-logo":
            path = regenerate_wide_logo()
            print(f"[+] Wide-Logo proportionsgetreu neu erzeugt: {path}")
            return

        if args.command == "prepare":
            output_dir = prepare_store_package(explicit_exe=args.exe)
            print(f"[+] Store-Staging vorbereitet: {output_dir}")
            return
        if args.command == "msix-preflight":
            output_path = build_msix_preflight(
                explicit_exe=args.exe,
                allow_test_identity=args.use_test_identity,
            )
            print(f"[+] MSIX-Preflight erstellt: {output_path}")
            return
        if args.command == "review-wack-report":
            report_dir = Path(args.report_dir).resolve() if args.report_dir else None
            report_path = Path(args.report).resolve() if args.report else latest_wack_report(report_dir=report_dir)
            summary = summarize_wack_report(report_path)
            print(format_wack_summary(summary))
            return
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"[!] {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
