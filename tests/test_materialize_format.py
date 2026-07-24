"""Regression tests for U2: configurable materialize default (.md or .txt)."""
from __future__ import annotations

from materializer import (
    FORMAT_MARKDOWN,
    FORMAT_TXT,
    materialize_extension,
    materialize_item,
)
from models import ItemType, LibraryItem
from promptboard import MainWindow
from settings_manager import SettingsManager
from storage import Storage


def _item():
    return LibraryItem(
        id="x", item_type=ItemType.PROMPT, name="Mein Eintrag",
        content="Hallo Welt", category="Kat", tags=["a", "b"], source="lokal",
    )


def test_settings_format_default_and_round_trip(qapp, tmp_path):
    settings = SettingsManager()
    assert settings.get_materialize_format() == "markdown"
    settings.set_materialize_format("txt")
    assert SettingsManager().get_materialize_format() == "txt"


def test_settings_format_invalid_resets_to_markdown(qapp, tmp_path):
    settings = SettingsManager()
    settings.set_materialize_format("pdf")
    assert settings.get_materialize_format() == "markdown"


def test_materialize_extension():
    assert materialize_extension(FORMAT_MARKDOWN) == ".md"
    assert materialize_extension(FORMAT_TXT) == ".txt"
    assert materialize_extension("bogus") == ".md"


def test_materialize_item_txt_writes_plaintext(tmp_path):
    path = materialize_item(_item(), tmp_path, FORMAT_TXT)
    assert path.suffix == ".txt"
    text = path.read_text(encoding="utf-8")
    assert "MEIN EINTRAG" in text  # name is uppercased by normalize_name
    assert "Hallo Welt" in text
    assert not text.lstrip().startswith("#")  # no Markdown heading
    assert "<!-- promptboard" not in text  # no HTML origin marker
    assert "> Typ:" not in text  # no Markdown blockquote metadata


def test_materialize_item_markdown_is_default(tmp_path):
    path = materialize_item(_item(), tmp_path)
    assert path.suffix == ".md"
    text = path.read_text(encoding="utf-8")
    assert text.lstrip().startswith("<!-- promptboard")


def test_main_window_materializes_txt_when_configured(qapp, tmp_path):
    export_dir = tmp_path / "exports"
    settings = SettingsManager()
    settings.qs.setValue("paths/data", str(tmp_path / "library"))
    settings.set_materialize_path(export_dir)
    settings.set_materialize_format("txt")
    settings.qs.sync()
    storage = Storage(tmp_path / "library")
    storage.upsert_item(
        LibraryItem(id="m", item_type=ItemType.PROMPT, name="Export Ziel", content="Inhalt")
    )
    window = MainWindow(storage, settings)
    try:
        window.item_list.setCurrentRow(0)
        window.materialize_current_item()
        assert (export_dir / "EXPORT ZIEL.txt").exists()
        assert not (export_dir / "EXPORT ZIEL.md").exists()
    finally:
        window.close()
