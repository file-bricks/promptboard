"""Exportiert alle Keys aus src/i18n.py nach locales/translations.json.

Einmaliges Hilfsskript zum Aufbau der translations.json.
Bestehende DE+EN-Werte werden uebernommen, fehlende Sprachen als leere Strings.
"""
import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / "src"))

from i18n import _TRANSLATIONS, VALID_LANGUAGES  # noqa: E402

output = {
    "_meta": {
        "description": "PromptBoard translation file - Premium 6-language tier",
        "format": "key -> {de, en, es, zh, ja, ru}",
        "languages": list(VALID_LANGUAGES),
        "source": "Generated from src/i18n.py _TRANSLATIONS dict",
        "instructions": "Fill empty strings for es, zh, ja, ru. Do NOT modify de or en values.",
    }
}

for key, translations in _TRANSLATIONS.items():
    entry = {}
    for lang in VALID_LANGUAGES:
        entry[lang] = translations.get(lang, "")
    output[key] = entry

out_path = PROJECT / "locales" / "translations.json"
out_path.parent.mkdir(parents=True, exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

langs = ", ".join(VALID_LANGUAGES)
print("Geschrieben: %d Keys -> %s" % (len(_TRANSLATIONS), out_path))
print("Sprachen: %s" % langs)

for lang in VALID_LANGUAGES:
    if lang in ("de", "en"):
        continue
    empty = sum(1 for v in _TRANSLATIONS.values() if not v.get(lang))
    print("  %s: %d leere Platzhalter (zu uebersetzen)" % (lang, empty))
