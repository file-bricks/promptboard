"""Vertragstests für manage_translations.py und translator.py (Tier-2 6-Sprachen-Gate)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import manage_translations as mt  # noqa: E402
from translator import TranslationSystem  # noqa: E402


def test_project_translations_check_and_stats_pass():
    assert mt.check_translations(str(PROJECT_ROOT)) == 0
    assert mt.main(["--check", "--stats", "--dir", str(PROJECT_ROOT)]) == 0


def test_translations_json_matches_i18n_keys():
    sys.path.insert(0, str(PROJECT_ROOT / "src"))
    from i18n import _TRANSLATIONS, VALID_LANGUAGES

    data = json.loads((PROJECT_ROOT / "locales" / "translations.json").read_text(encoding="utf-8"))
    json_keys = {k for k in data if not k.startswith("_")}
    assert json_keys == set(_TRANSLATIONS.keys())
    assert len(json_keys) == 158
    for key in json_keys:
        for lang in VALID_LANGUAGES:
            assert data[key].get(lang), f"Leerer Wert für {key}[{lang}]"


def test_check_gate_fails_on_missing_file_or_incomplete_language(tmp_path):
    assert mt.main(["--check", "--dir", str(tmp_path)]) == 1

    locales_dir = tmp_path / "locales"
    locales_dir.mkdir(parents=True)
    bad_json = locales_dir / "translations.json"
    bad_json.write_text("{broken json", encoding="utf-8")
    assert mt.main(["--check", "--dir", str(tmp_path)]) == 1

    incomplete = {
        "hello": {
            "de": "Hallo",
            "en": "Hello",
            "es": "Hola",
            "zh": "",
            "ja": "こんにちは",
            "ru": "Привет",
        }
    }
    bad_json.write_text(json.dumps(incomplete, ensure_ascii=False), encoding="utf-8")
    assert mt.main(["--check", "--dir", str(tmp_path)]) == 1

    incomplete["hello"]["zh"] = "你好"
    bad_json.write_text(json.dumps(incomplete, ensure_ascii=False), encoding="utf-8")
    assert mt.main(["--check", "--dir", str(tmp_path)]) == 0


def test_scan_and_atomic_write_leave_no_temp_files(tmp_path):
    src = tmp_path / "sample.py"
    src.write_text('button.setText("Datei öffnen")\n', encoding="utf-8")

    rc = mt.main(["--scan", "--dir", str(tmp_path)])
    assert rc == 0

    trans_file = tmp_path / "locales" / "translations.json"
    assert trans_file.is_file()
    data = json.loads(trans_file.read_text(encoding="utf-8"))
    assert "Datei öffnen" in data
    assert data["Datei öffnen"]["de"] == "Datei öffnen"
    leftovers = list((tmp_path / "locales").glob("*.tmp.*"))
    assert leftovers == []


def test_translator_system_atomic_save_and_umlaut_detection(tmp_path):
    ts = TranslationSystem("ja", app_dir=tmp_path)
    ts.add_translation("save_btn", de="Speichern", en="Save", ja="保存")
    assert ts.t("save_btn") == "保存"

    ts.set_language("fr")  # unbekannt -> unverändert
    assert ts.get_language() == "ja"

    ts.set_language("ru")
    assert ts.t("save_btn") == "Save"  # Fallback-Kette en -> de -> Key

    assert ts._is_german("Einstellungen öffnen") is True
    assert ts.t("Einstellungen öffnen") == "Einstellungen öffnen"
    assert "Einstellungen öffnen" in ts.translations
    assert list((tmp_path / "locales").glob("*.tmp.*")) == []
