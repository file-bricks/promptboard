"""Minimaler i18n-Layer für PromptBoard.

Deutsch ist Standardsprache. Englisch via ``tr(key, 'en')`` oder via
globalen Switch ``set_language('en')``. Keine externen Dependencies.

Verwendung:
    from i18n import tr, set_language
    set_language("de")
    label.setText(tr("menu.file"))
"""
from __future__ import annotations

import logging
from typing import Literal

logger = logging.getLogger(__name__)

LanguageCode = Literal["de", "en"]
VALID_LANGUAGES: tuple[LanguageCode, ...] = ("de", "en")
DEFAULT_LANGUAGE: LanguageCode = "de"

_TRANSLATIONS: dict[str, dict[LanguageCode, str]] = {
    # ----- Menüs ---------------------------------------------------------
    "menu.file": {"de": "Datei", "en": "File"},
    "menu.settings": {"de": "Einstellungen", "en": "Settings"},
    "menu.file.new": {"de": "Neuer Eintrag", "en": "New entry"},
    "menu.file.import_profiprompt": {
        "de": "Aus ProfiPrompt importieren",
        "en": "Import from ProfiPrompt",
    },
    "menu.file.import_explorerpro": {
        "de": "Aus ExplorerPro importieren",
        "en": "Import from ExplorerPro",
    },
    "menu.file.export_explorerpro": {
        "de": "Nach ExplorerPro exportieren",
        "en": "Export to ExplorerPro",
    },
    "menu.file.quit": {"de": "Beenden", "en": "Quit"},
    "menu.settings.open": {"de": "Einstellungen…", "en": "Preferences…"},

    # ----- Toolbar / Buttons --------------------------------------------
    "btn.new": {"de": "Neu", "en": "New"},
    "btn.delete": {"de": "Löschen", "en": "Delete"},
    "btn.copy": {"de": "Kopieren", "en": "Copy"},
    "btn.copy_markdown": {"de": "Als Markdown kopieren", "en": "Copy as Markdown"},
    "btn.materialize": {"de": "Materialisieren", "en": "Materialize"},
    "btn.materialize_current": {
        "de": "Aktuellen Eintrag materialisieren",
        "en": "Materialize current entry",
    },
    "btn.materialize_selected": {
        "de": "Ausgewählte Einträge materialisieren",
        "en": "Materialize selected entries",
    },
    "btn.change": {"de": "Ändern…", "en": "Change…"},
    "btn.ok": {"de": "OK", "en": "OK"},
    "btn.cancel": {"de": "Abbrechen", "en": "Cancel"},

    # ----- Filter / Liste ------------------------------------------------
    "filter.all": {"de": "ALLE", "en": "ALL"},
    "filter.search_placeholder": {
        "de": "Suche nach Name, Inhalt oder Kategorie…",
        "en": "Search by name, content, or category…",
    },
    "filter.type_name": {"de": "Typfilter", "en": "Type filter"},
    "filter.type_description": {
        "de": "Bibliothek nach Eintragstyp filtern",
        "en": "Filter the library by entry type",
    },
    "filter.sort_name": {"de": "Sortierung", "en": "Sort order"},
    "filter.sort_description": {
        "de": "Sortierung der Bibliothek ändern",
        "en": "Change the library sort order",
    },
    "filter.search_name": {"de": "Bibliothek durchsuchen", "en": "Search library"},
    "filter.search_description": {
        "de": "Bibliothek nach Name, Inhalt oder Kategorie durchsuchen",
        "en": "Search the library by name, content, or category",
    },

    # ----- Form-Labels ---------------------------------------------------
    "form.type": {"de": "Typ", "en": "Type"},
    "form.name": {"de": "Name", "en": "Name"},
    "form.category": {"de": "Kategorie", "en": "Category"},
    "form.tags": {"de": "Tags", "en": "Tags"},
    "form.source": {"de": "Quelle", "en": "Source"},
    "form.source_placeholder": {
        "de": "z. B. lokal, ProfiPrompt, ExplorerPro",
        "en": "e.g. local, ProfiPrompt, ExplorerPro",
    },
    "form.content_placeholder": {
        "de": "Inhalt des Eintrags… Platzhalter wie {{name}} werden beim Kopieren abgefragt.",
        "en": "Entry content… Placeholders like {{name}} are prompted when copying.",
    },

    # ----- Settings-Dialog ----------------------------------------------
    "settings.title": {"de": "PromptBoard – Einstellungen", "en": "PromptBoard — Settings"},
    "settings.group.paths": {"de": "Pfade", "en": "Paths"},
    "settings.path.materialize": {"de": "Materialisierung", "en": "Materialization"},
    "settings.path.profiprompt": {"de": "ProfiPrompt-Ordner", "en": "ProfiPrompt folder"},
    "settings.path.explorerpro": {"de": "ExplorerPro-Ordner", "en": "ExplorerPro folder"},
    "settings.group.io": {"de": "Import / Export", "en": "Import / Export"},
    "settings.io.import_profiprompt": {
        "de": "Aus ProfiPrompt importieren",
        "en": "Import from ProfiPrompt",
    },
    "settings.io.import_explorerpro": {
        "de": "Aus ExplorerPro importieren",
        "en": "Import from ExplorerPro",
    },
    "settings.io.export_explorerpro": {
        "de": "Nach ExplorerPro exportieren",
        "en": "Export to ExplorerPro",
    },
    "settings.group.view": {"de": "Ansicht", "en": "Appearance"},
    "settings.view.theme": {"de": "Farbschema", "en": "Color theme"},
    "settings.view.language": {"de": "Sprache", "en": "Language"},
    "settings.view.confirm_overwrite": {
        "de": "Vor Überschreiben beim Materialisieren nachfragen",
        "en": "Confirm before overwriting on materialize",
    },
    "settings.group.info": {"de": "Info", "en": "Info"},
    "settings.info.data_dir": {"de": "Datenordner", "en": "Data folder"},
    "settings.info.log_file": {"de": "Logdatei", "en": "Log file"},

    # ----- Theme-Namen ---------------------------------------------------
    "theme.system": {"de": "System", "en": "System"},
    "theme.light": {"de": "Hell", "en": "Light"},
    "theme.dark": {"de": "Dunkel", "en": "Dark"},
    "theme.vibrant": {"de": "Vibrant (bunt)", "en": "Vibrant"},

    # ----- Sprach-Namen --------------------------------------------------
    "lang.de": {"de": "Deutsch", "en": "German"},
    "lang.en": {"de": "Englisch", "en": "English"},

    # ----- Statusmeldungen ----------------------------------------------
    "status.ready": {"de": "Bereit", "en": "Ready"},
    "status.editing": {"de": "Bearbeite: {name}", "en": "Editing: {name}"},
    "status.autosaved": {
        "de": "Automatisch gespeichert: {name}",
        "en": "Auto-saved: {name}",
    },
    "status.created": {"de": "Neuer Eintrag erstellt", "en": "New entry created"},
    "status.copied": {
        "de": "In Zwischenablage kopiert: {name}",
        "en": "Copied to clipboard: {name}",
    },
    "status.copied_markdown": {
        "de": "Als Markdown kopiert: {name}",
        "en": "Copied as Markdown: {name}",
    },
    "status.copy_cancelled": {
        "de": "Kopieren abgebrochen",
        "en": "Copy cancelled",
    },
    "status.copy_markdown_cancelled": {
        "de": "Markdown-Kopie abgebrochen",
        "en": "Markdown copy cancelled",
    },
    "status.materialized": {"de": "Materialisiert: {target}", "en": "Materialized: {target}"},
    "status.materialized_batch": {
        "de": "{count} Einträge materialisiert: {target}",
        "en": "Materialized {count} entries: {target}",
    },
    "status.materialize_cancelled": {
        "de": "Materialisierung abgebrochen",
        "en": "Materialization cancelled",
    },
    "status.delete_cancelled": {
        "de": "Löschen abgebrochen: {name}",
        "en": "Delete cancelled: {name}",
    },
    "status.deleted": {"de": "Gelöscht: {name}", "en": "Deleted: {name}"},
    "status.minimized_to_tray": {
        "de": "Fenster in den Systemtray minimiert",
        "en": "Window minimized to system tray",
    },
    "status.theme_updated": {
        "de": "Farbschema aktualisiert: {mode}",
        "en": "Theme updated: {mode}",
    },
    "status.language_updated": {
        "de": "Sprache geändert: {lang}",
        "en": "Language changed: {lang}",
    },
    "status.materialize_path_set": {
        "de": "Neuer Materialisierungspfad: {path}",
        "en": "New materialize path: {path}",
    },
    "status.hotkeys_enabled": {
        "de": "Globale Hotkeys aktiv: {show} / {copy}",
        "en": "Global hotkeys active: {show} / {copy}",
    },
    "status.hotkeys_unavailable": {
        "de": "Globale Hotkeys nicht verfügbar; Systemtray bleibt aktiv",
        "en": "Global hotkeys unavailable; system tray remains active",
    },
    "status.hotkeys_toggle_shown": {
        "de": "Fenster über Hotkey eingeblendet",
        "en": "Window shown via hotkey",
    },
    "status.hotkeys_toggle_hidden": {
        "de": "Fenster über Hotkey ausgeblendet",
        "en": "Window hidden via hotkey",
    },
    "status.hotkeys_no_recent_item": {
        "de": "Kein zuletzt benutzter Eintrag für die Schnellkopie gefunden",
        "en": "No recently used entry found for quick copy",
    },
    "status.hotkeys_quick_copy": {
        "de": "Schnellkopie per Hotkey: {name}",
        "en": "Quick copy via hotkey: {name}",
    },
    "status.profiprompt_path_set": {
        "de": "Neuer ProfiPrompt-Pfad: {path}",
        "en": "New ProfiPrompt path: {path}",
    },
    "status.explorerpro_path_set": {
        "de": "Neuer ExplorerPro-Pfad: {path}",
        "en": "New ExplorerPro path: {path}",
    },
    "status.imported_profiprompt": {
        "de": "Importiert aus ProfiPrompt: {count} Einträge",
        "en": "Imported from ProfiPrompt: {count} entries",
    },
    "status.imported_explorerpro": {
        "de": "Importiert aus ExplorerPro: {count} Einträge",
        "en": "Imported from ExplorerPro: {count} entries",
    },
    "status.exported_explorerpro": {
        "de": "Nach ExplorerPro exportiert: {count} Einträge",
        "en": "Exported to ExplorerPro: {count} entries",
    },

    # ----- Dialoge / Fehler ---------------------------------------------
    "dialog.delete.title": {"de": "Eintrag löschen", "en": "Delete entry"},
    "dialog.delete.body": {
        "de": "Möchtest du den Eintrag '{name}' wirklich löschen?",
        "en": "Really delete entry '{name}'?",
    },
    "dialog.overwrite.title": {"de": "Datei überschreiben?", "en": "Overwrite file?"},
    "dialog.overwrite.body": {
        "de": "'{name}' existiert bereits. Überschreiben?",
        "en": "'{name}' already exists. Overwrite?",
    },
    "dialog.inline_variable.title": {
        "de": "Variable: {name}",
        "en": "Variable: {name}",
    },
    "dialog.inline_variable.body": {
        "de": "Wert für '{name}' eingeben:",
        "en": "Enter value for '{name}':",
    },
    "dialog.import_failed.title": {"de": "Import fehlgeschlagen", "en": "Import failed"},
    "dialog.import_failed.profiprompt": {
        "de": "Kein ProfiPrompt-`prompts.json` mit mindestens einem Prompt gefunden.",
        "en": "No ProfiPrompt `prompts.json` with at least one prompt found.",
    },
    "dialog.import_failed.explorerpro": {
        "de": "Kein ExplorerPro-`prompts.json` mit mindestens einem Prompt gefunden.",
        "en": "No ExplorerPro `prompts.json` with at least one prompt found.",
    },
    "dialog.export_empty.title": {"de": "Export", "en": "Export"},
    "dialog.export_empty.body": {
        "de": "Es gibt keine PROMPT-Einträge zum Export nach ExplorerPro.",
        "en": "No PROMPT entries available to export to ExplorerPro.",
    },
    "dialog.choose_materialize_path": {
        "de": "Materialisierungspfad wählen",
        "en": "Choose materialize folder",
    },
    "dialog.choose_profiprompt_path": {
        "de": "ProfiPrompt-Datenordner wählen",
        "en": "Choose ProfiPrompt data folder",
    },
    "dialog.choose_explorerpro_path": {
        "de": "ExplorerPro-Datenordner wählen",
        "en": "Choose ExplorerPro data folder",
    },
    "error.library_load": {
        "de": "Bibliothek konnte nicht geladen werden",
        "en": "Library could not be loaded",
    },
    "error.save_failed": {"de": "Speichern fehlgeschlagen", "en": "Save failed"},
    "error.create_failed": {
        "de": "Eintrag konnte nicht angelegt werden",
        "en": "Entry could not be created",
    },
    "error.delete_failed": {"de": "Löschen fehlgeschlagen", "en": "Delete failed"},
    "error.materialize_failed": {
        "de": "Materialisierung fehlgeschlagen",
        "en": "Materialization failed",
    },
    "error.profiprompt_failed": {
        "de": "ProfiPrompt-Import fehlgeschlagen",
        "en": "ProfiPrompt import failed",
    },
    "error.explorerpro_import_failed": {
        "de": "ExplorerPro-Import fehlgeschlagen",
        "en": "ExplorerPro import failed",
    },
    "error.explorerpro_export_failed": {
        "de": "ExplorerPro-Export fehlgeschlagen",
        "en": "ExplorerPro export failed",
    },

    # ----- Tray ----------------------------------------------------------
    "tray.open": {"de": "Öffnen", "en": "Open"},
    "tray.hide": {"de": "Verstecken", "en": "Hide"},
    "tray.quit": {"de": "Beenden", "en": "Quit"},
}

_current_language: LanguageCode = DEFAULT_LANGUAGE


def set_language(code: str) -> None:
    """Globaler Sprach-Switch."""
    global _current_language
    if code not in VALID_LANGUAGES:
        logger.warning("Ungültiger Sprach-Code '%s', verwende Default '%s'.", code, DEFAULT_LANGUAGE)
        _current_language = DEFAULT_LANGUAGE
        return
    _current_language = code  # type: ignore[assignment]


def get_language() -> LanguageCode:
    return _current_language


def tr(key: str, lang: str | None = None, **kwargs) -> str:
    """Translate a key. Falls back to DEFAULT_LANGUAGE or the key itself.

    ``**kwargs`` are forwarded to ``str.format`` for placeholders.
    """
    code: LanguageCode = (lang if lang in VALID_LANGUAGES else _current_language)  # type: ignore[assignment]
    entry = _TRANSLATIONS.get(key)
    if entry is None:
        return key
    text = entry.get(code) or entry.get(DEFAULT_LANGUAGE) or key
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text
    return text
