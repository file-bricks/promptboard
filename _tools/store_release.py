from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any

APP_NAME = "PromptBoard"
APP_VERSION = "1.1.1"
STORE_VERSION = "1.1.1.0"
APP_EXECUTABLE = f"{APP_NAME}-{APP_VERSION}-win64.exe"


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def software_root(root: Path | None = None) -> Path:
    base = root or project_root()
    return base.parent.parent


def store_tool_path(root: Path | None = None) -> Path:
    return software_root(root) / "_STORE" / "store_packager.py"


def build_store_config() -> dict[str, str]:
    return {
        "app_name": APP_NAME,
        "publisher": "CN=YourPublisher",
        "publisher_display": "Lukas Geiger",
        "identity_name": "YourPublisher.PromptBoard",
        "version": STORE_VERSION,
        "description": "Lokales Tray-Tool für Prompts, Skills, Workflows, Rollen und Agenten.",
        "executable": APP_EXECUTABLE,
        "capabilities": "",
        "category": "Productivity",
        "age_rating": "3+",
        "privacy_url": "https://github.com/file-bricks/promptboard/blob/master/PRIVACY_POLICY.md",
        "support_url": "https://github.com/file-bricks/promptboard/issues",
    }


def build_store_listing(config: dict[str, str]) -> str:
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
        f"# Store Listing — {config['app_name']}\n\n"
        "Stand: 2026-05-20\n\n"
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
    config = build_store_config()
    config_path = base / "store_package.json"
    config_path.write_text(
        json.dumps(config, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    listing_path = base / "STORE_LISTING.md"
    listing_path.write_text(build_store_listing(config), encoding="utf-8")
    return config_path, listing_path


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
    executable = resolve_executable(base, explicit=explicit_exe)
    module = load_store_packager(base)
    packager = module.StorePackager(str(base), app_name=APP_NAME, config_file=str(config_path))
    packager.config.update(build_store_config())
    packager.save_config(str(config_path))
    packager.prepare_package(
        icon_source=str(base / "PromptBoard.png"),
        exe_path=str(executable),
    )
    return Path(packager.output_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description="PromptBoard Windows-Store Vorbereitung")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("write-root-files", help="store_package.json und STORE_LISTING.md schreiben")

    prepare_parser = subparsers.add_parser("prepare", help="Store-Paket-Staging erzeugen")
    prepare_parser.add_argument("--exe", help="Pfad zur PromptBoard-EXE")

    args = parser.parse_args()

    if args.command == "write-root-files":
        config_path, listing_path = write_root_files()
        print(f"[+] Geschrieben: {config_path}")
        print(f"[+] Geschrieben: {listing_path}")
        return

    if args.command == "prepare":
        output_dir = prepare_store_package(explicit_exe=args.exe)
        print(f"[+] Store-Staging vorbereitet: {output_dir}")
        return


if __name__ == "__main__":
    main()
