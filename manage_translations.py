"""
manage_translations.py - Multi-Language Translation Manager & CI Gate
======================================================================
Unterstuetzt 6 Sprachen (Policy P-006 Tier-2): de, en, es, zh, ja, ru.

Verwendung:
    python manage_translations.py [--check] [--stats] [--scan] [--dir PROJEKTVERZEICHNIS]
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import stat
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
TRANSLATION_FILE = "locales/translations.json"
SUPPORTED_LANGUAGES = ("de", "en", "es", "zh", "ja", "ru")

STRING_PATTERNS = [
    re.compile(r'text\s*=\s*"([^"\n]+)"'),
    re.compile(r'setText\s*\(\s*["\']([^"\'\n]+)["\']\s*\)'),
    re.compile(r'setWindowTitle\s*\(\s*["\']([^"\'\n]+)["\']\s*\)'),
    re.compile(r'QLabel\s*\(\s*["\']([^"\'\n]+)["\']\s*\)'),
    re.compile(r'QPushButton\s*\(\s*["\']([^"\'\n]+)["\']\s*\)'),
    re.compile(r'addAction\s*\([^,\n]*["\']([^"\'\n]+)["\']\s*\)'),
    re.compile(r'setToolTip\s*\(\s*["\']([^"\'\n]+)["\']\s*\)'),
    re.compile(r'setPlaceholderText\s*\(\s*["\']([^"\'\n]+)["\']\s*\)'),
]

GERMAN_HINTS = [
    "datei", "filter", "fehler", "laden", "speichern",
    "ansicht", "optionen", "zurueck", "anzeigen", "export",
    "import", "einstellungen", "abbrechen", "hilfe", "bearbeiten",
    "oeffnen", "schliessen", "start", "aktualisieren",
]


def _ensure_utf8_streams() -> None:
    """Sichert UTF-8-Konsolen-Encoding unter Windows für stdout und stderr."""
    for stream in (sys.stdout, sys.stderr):
        if stream and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError, AttributeError):
                pass


def is_german(text: str) -> bool:
    if any(ch in text for ch in "\u00e4\u00f6\u00fc\u00c4\u00d6\u00dc\u00df"):
        return True
    text_lower = text.lower()
    return any(w in text_lower for w in GERMAN_HINTS)


def find_german_strings(source_dir: str | None = None) -> set[str]:
    if not source_dir:
        source_dir = str(APP_DIR)
    german_strings: set[str] = set()
    skip_dirs = {
        "build",
        "dist",
        "venv",
        ".venv",
        "__pycache__",
        "releases",
        "scratch",
        "tests",
        "scripts",
        "_tools",
        "flutter_port",
        ".git",
        ".pytest_cache",
        ".ruff_cache",
    }
    skip_files = {
        "manage_translations.py",
        "translator.py",
        "source_platform_smoke.py",
    }

    for root, dirs, files in os.walk(source_dir):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for file in files:
            if file.endswith(".py") and not file.startswith("test_") and file not in skip_files:
                path = os.path.join(root, file)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                except Exception:
                    continue
                for pattern in STRING_PATTERNS:
                    for match in pattern.findall(content):
                        if match and is_german(match):
                            german_strings.add(match.strip())
    return german_strings


def _atomic_write_json(file_path: str | Path, data: dict) -> None:
    """Schreibt JSON atomar über eine temporäre Datei im selben Verzeichnis."""
    target = Path(file_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp_path = target.with_name(f"{target.name}.tmp.{os.getpid()}")
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        if target.exists():
            try:
                os.chmod(target, stat.S_IWRITE | stat.S_IREAD)
            except (OSError, PermissionError):
                pass
        os.replace(temp_path, target)
    except Exception:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass
        raise


def _load_translations_dict(source_dir: str | Path) -> tuple[dict | None, str | None]:
    trans_file = Path(source_dir) / TRANSLATION_FILE
    if not trans_file.exists():
        return None, f"Übersetzungsdatei {trans_file} existiert nicht!"
    try:
        with open(trans_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        return None, f"Fehler beim Parsen von {trans_file}: {exc}"
    if not isinstance(data, dict):
        return None, f"Ungültiges Format in {trans_file}: JSON-Objekt erwartet."
    return data, None


def _load_i18n_keys(source_dir: str | Path) -> set[str] | None:
    """Lädt optional die kanonischen Schlüssel aus src/i18n.py, falls vorhanden."""
    i18n_file = Path(source_dir) / "src" / "i18n.py"
    if not i18n_file.is_file():
        return None
    spec = importlib.util.spec_from_file_location("promptboard_i18n_check", i18n_file)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    raw = getattr(module, "_TRANSLATIONS", None)
    if isinstance(raw, dict):
        return set(raw.keys())
    return None


def compute_translation_stats(translations: dict) -> tuple[int, dict[str, list[str]]]:
    entries = {k: v for k, v in translations.items() if not k.startswith("_")}
    total_keys = len(entries)
    missing_by_lang: dict[str, list[str]] = {lang: [] for lang in SUPPORTED_LANGUAGES}

    for key, val in entries.items():
        if not isinstance(val, dict):
            for lang in SUPPORTED_LANGUAGES:
                missing_by_lang[lang].append(key)
            continue
        for lang in SUPPORTED_LANGUAGES:
            target_val = val.get(lang)
            if not isinstance(target_val, str) or not target_val.strip():
                missing_by_lang[lang].append(key)

    return total_keys, missing_by_lang


def print_stats(source_dir: str | None = None) -> int:
    """Gibt eine formatierte Statistik-Tabelle mit Abdeckungsgrad je Sprache aus."""
    _ensure_utf8_streams()
    if not source_dir:
        source_dir = str(APP_DIR)
    translations, err = _load_translations_dict(source_dir)
    if err or translations is None:
        print(f"[FAIL] {err}")
        return 1

    total_keys, missing_by_lang = compute_translation_stats(translations)
    print(f"PromptBoard Übersetzungsstatistik ({total_keys} Schlüssel)")
    print("-" * 52)
    print(f"{'Sprache':<10} | {'Übersetzt':>10} | {'Fehlend':>8} | {'Abdeckung':>10}")
    print("-" * 52)
    for lang in SUPPORTED_LANGUAGES:
        missing_count = len(missing_by_lang[lang])
        translated_count = total_keys - missing_count
        pct = (translated_count / total_keys * 100.0) if total_keys > 0 else 0.0
        print(f"{lang:<10} | {translated_count:>10} | {missing_count:>8} | {pct:>9.1f}%")
    print("-" * 52)
    return 0


def check_translations(source_dir: str | None = None) -> int:
    """CI-Gate: Prüft 100% Sprachabdeckung aller 6 Zielsprachen und i18n-Parität."""
    _ensure_utf8_streams()
    if not source_dir:
        source_dir = str(APP_DIR)
    translations, err = _load_translations_dict(source_dir)
    if err or translations is None:
        print(f"[FAIL] {err}")
        return 1

    total_keys, missing_by_lang = compute_translation_stats(translations)
    if total_keys == 0:
        print(f"[FAIL] Keine Übersetzungsschlüssel in {Path(source_dir) / TRANSLATION_FILE} gefunden!")
        return 1

    has_error = False
    for lang, missing in missing_by_lang.items():
        if missing:
            has_error = True
            print(f"[!] {len(missing)}/{total_keys} fehlende Übersetzungen für Sprache '{lang}':")
            for k in missing[:5]:
                print(f"    - {k}")
            if len(missing) > 5:
                print(f"    ... und {len(missing) - 5} weitere")

    i18n_keys = _load_i18n_keys(source_dir)
    if i18n_keys is not None:
        json_keys = {k for k in translations if not k.startswith("_")}
        missing_from_json = sorted(i18n_keys - json_keys)
        if missing_from_json:
            has_error = True
            print(
                f"[!] {len(missing_from_json)} Schlüssel aus src/i18n.py fehlen in locales/translations.json:"
            )
            for k in missing_from_json[:5]:
                print(f"    - {k}")
            if len(missing_from_json) > 5:
                print(f"    ... und {len(missing_from_json) - 5} weitere")

    if has_error:
        print("\n[FAIL] Übersetzungsprüfung fehlgeschlagen. Nicht alle Schlüssel vollständig übersetzt.")
        return 1

    print(
        f"[OK] 100% Übersetzungsparität: Alle {total_keys} Schlüssel in allen 6 Sprachen vorhanden "
        f"({', '.join(SUPPORTED_LANGUAGES)})."
    )
    return 0


def manage_translations(source_dir: str | None = None) -> None:
    _ensure_utf8_streams()
    if not source_dir:
        source_dir = str(APP_DIR)
    trans_file = os.path.join(source_dir, TRANSLATION_FILE)

    if os.path.exists(trans_file):
        try:
            with open(trans_file, "r", encoding="utf-8") as f:
                translations = json.load(f)
        except (json.JSONDecodeError, OSError):
            translations = {}
    else:
        translations = {}

    found = find_german_strings(source_dir)

    added: list[str] = []
    upgraded: list[str] = []
    for s in sorted(found):
        if s not in translations:
            entry = {"de": s}
            for lang in SUPPORTED_LANGUAGES:
                if lang != "de":
                    entry[lang] = ""
            translations[s] = entry
            added.append(s)
        else:
            for lang in SUPPORTED_LANGUAGES:
                if lang not in translations[s]:
                    translations[s][lang] = ""
                    if s not in upgraded:
                        upgraded.append(s)

    _atomic_write_json(trans_file, translations)

    if added:
        print(f"[+] {len(added)} neue Einträge hinzugefügt:")
        for s in added[:20]:
            print(f"    - {s}")
        if len(added) > 20:
            print(f"    ... und {len(added) - 20} weitere")
    else:
        print("[i] Keine neuen deutschen Strings gefunden.")

    if upgraded:
        print(f"[+] {len(upgraded)} bestehende Einträge um neue Sprach-Slots erweitert")

    for lang in SUPPORTED_LANGUAGES:
        if lang == "de":
            continue
        missing = [
            k
            for k, v in translations.items()
            if not k.startswith("_") and isinstance(v, dict) and not v.get(lang)
        ]
        if missing:
            print(f"[!] {lang}: {len(missing)} fehlende Übersetzungen")

    total_keys = len([k for k in translations if not k.startswith("_")])
    print(f"\n[i] Gesamt: {total_keys} Schlüssel in {trans_file}")
    print(f"[i] Sprachen: {', '.join(SUPPORTED_LANGUAGES)}")


def main(argv: list[str] | None = None) -> int:
    _ensure_utf8_streams()
    parser = argparse.ArgumentParser(
        description="PromptBoard Translation Manager & CI Gate (Tier-2 6 Sprachen)"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="CI-Gate: Validiert 100%% Sprachabdeckung aller 6 Zielsprachen (Exit 0/1)",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Gibt eine formatierte Statistik-Tabelle mit Abdeckungsgrad je Sprache aus",
    )
    parser.add_argument(
        "--scan",
        action="store_true",
        help="Scannt .py-Quelltexte nach deutschen Strings und aktualisiert translations.json atomar",
    )
    parser.add_argument(
        "--dir",
        default=str(APP_DIR),
        help="Wurzelverzeichnis des Projekts (Default: Skriptverzeichnis)",
    )
    args = parser.parse_args(argv)

    if args.check:
        rc = check_translations(args.dir)
        if args.stats:
            print_stats(args.dir)
        return rc
    if args.stats:
        return print_stats(args.dir)
    # --scan oder Standardverhalten ohne Flag
    manage_translations(args.dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
