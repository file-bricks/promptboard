# -*- coding: utf-8 -*-
"""Regressionstests — PromptBoard Desktop-Bugsweep 2026-06-22 (Bugsweep-Loop-Lauf 38).

models/settings_manager-Helper sind ohne QApplication testbar -> echte Tests. Rest statisch
(red-on-revert via PB_SRC -> PRE-Backup/src).

  BUG-38 models.item_from_dict (HOCH): null-Feldwerte / fehlende id -> robust (kein Crash der GESAMTEN
        Bibliothek beim Laden); or-Defaults + gen_id-Fallback.
  BUG-38 hotkeys.nativeEventFilter: callback() in try/except (keine App-Termination durch Hotkey-Fehler).
  BUG-38 settings_manager._ensure_dir: OSError beim mkdir -> Fallback-Pfad statt Start-Crash.
"""
import os
import sys
from pathlib import Path

import pytest

_SRCDIR = os.path.join(os.path.dirname(__file__), "..", "src")
sys.path.insert(0, _SRCDIR)

_SRC = Path(os.environ.get("PB_SRC", Path(__file__).resolve().parents[1] / "src"))


def read(rel):
    return (_SRC / rel).read_text(encoding="utf-8")


# --- echte Tests ---
def test_bug38_item_from_dict_null_fields_no_crash():
    from models import item_from_dict, LibraryItem
    # null-Feldwerte (korrupte/handeditierte library.json) -> vor Fix AttributeError/TypeError
    item = item_from_dict({"id": "x1", "name": None, "category": None, "tags": None, "source": None})
    assert isinstance(item, LibraryItem)
    assert item.category == ""
    assert list(item.tags) == []


def test_bug38_item_from_dict_missing_id_gets_generated():
    from models import item_from_dict
    # fehlende id -> vor Fix KeyError -> load_items reisst gesamte Bibliothek mit
    item = item_from_dict({"name": "Test"})
    assert item.id  # nicht-leere generierte ID


def test_bug38_ensure_dir_falls_back_on_oserror(tmp_path):
    from settings_manager import _ensure_dir
    # Pfad UNTER einer Datei -> mkdir wirft NotADirectoryError/OSError -> Fallback
    afile = tmp_path / "afile"
    afile.write_text("x", encoding="utf-8")
    fallback = tmp_path / "fallback"
    result = _ensure_dir(afile / "sub", fallback)
    assert result == fallback
    assert fallback.exists()


# --- statische Assertions (red-on-revert via PB_SRC -> PRE) ---
def test_bug38_static_models_or_defaults():
    src = read("models.py")
    assert 'id=data.get("id") or gen_id()' in src, "BUG-38 id-Fallback fehlt"
    assert 'tags=data.get("tags") or []' in src, "BUG-38 tags or-Default fehlt"
    assert 'name=data.get("name") or ""' in src, "BUG-38 name or-Default fehlt"


def test_bug38_static_hotkeys_callback_guard():
    src = read("hotkeys.py")
    assert "Hotkey-Callback fehlgeschlagen" in src, "BUG-38 nativeEventFilter try/except fehlt"


def test_bug38_static_settings_ensure_dir():
    src = read("settings_manager.py")
    assert "def _ensure_dir(path: Path, fallback: Path)" in src, "BUG-38 _ensure_dir fehlt"
    assert "except OSError as exc:" in src, "BUG-38 mkdir OSError-Guard fehlt"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
