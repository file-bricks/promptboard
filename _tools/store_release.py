from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Mapping

APP_NAME = "PromptBoard"
APP_VERSION = "1.1.1"
STORE_VERSION = "1.1.1.0"
APP_EXECUTABLE = f"{APP_NAME}-{APP_VERSION}-win64.exe"
STORE_CONFIG_NAME = "store_package.json"
LOCAL_STORE_CONFIG_NAME = "store_package.local.json"
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
        icon_source=str(base / "PromptBoard.png"),
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
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"[!] {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
