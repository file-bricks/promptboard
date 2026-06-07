/// L10n-Tests: DE+EN Grundstrings, parametrisierte Methoden, Fallback.
library;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:promptboard/l10n/app_localizations.dart';

void main() {
  // ── DE: Grundstrings ─────────────────────────────────────────────────
  test('DE: Grundstrings', () {
    final l10n = AppLocalizations(const Locale('de'));
    expect(l10n.appTitle, 'PromptBoard Companion');
    expect(l10n.notLoaded, 'Noch nicht geladen');
    expect(l10n.sourceClipboard, 'Zwischenablage');
    expect(l10n.sourceManual, 'Manuelle Eingabe');
    expect(l10n.sourceDemo, 'Demo');
    expect(l10n.typeAll, 'ALLE');
    expect(l10n.cancel, 'Abbrechen');
    expect(l10n.loadLibrary, 'Bibliothek laden');
    expect(l10n.emptyTitle, 'Noch keine Bibliothek geladen');
    expect(l10n.noResults, 'Keine Einträge für diesen Filter gefunden.');
  });

  // ── EN: Basic strings ────────────────────────────────────────────────
  test('EN: Basic strings', () {
    final l10n = AppLocalizations(const Locale('en'));
    expect(l10n.appTitle, 'PromptBoard Companion');
    expect(l10n.notLoaded, 'Not loaded');
    expect(l10n.sourceClipboard, 'Clipboard');
    expect(l10n.sourceManual, 'Manual entry');
    expect(l10n.sourceDemo, 'Demo');
    expect(l10n.typeAll, 'ALL');
    expect(l10n.cancel, 'Cancel');
    expect(l10n.loadLibrary, 'Load library');
    expect(l10n.emptyTitle, 'No library loaded');
    expect(l10n.noResults, 'No entries found for this filter.');
  });

  // ── DE: Parametrisierte Methoden ─────────────────────────────────────
  test('DE: Parametrisierte Methoden', () {
    final l10n = AppLocalizations(const Locale('de'));
    expect(l10n.itemsLoaded(3, 'Demo'), '3 Einträge aus Demo geladen.');
    expect(l10n.itemsLoaded(1, 'Zwischenablage'),
        '1 Einträge aus Zwischenablage geladen.');
    expect(l10n.copiedToClipboard('Mein Prompt'),
        'Mein Prompt wurde in die Zwischenablage kopiert.');
    expect(l10n.tagsLabel('flutter, dart'), 'Tags: flutter, dart');
    expect(l10n.sourceLabel('Demo'), 'Quelle: Demo');
  });

  // ── EN: Parameterized methods ────────────────────────────────────────
  test('EN: Parameterized methods', () {
    final l10n = AppLocalizations(const Locale('en'));
    expect(l10n.itemsLoaded(3, 'Demo'), '3 entries from Demo loaded.');
    expect(l10n.copiedToClipboard('My Prompt'),
        'My Prompt was copied to clipboard.');
    expect(l10n.tagsLabel('flutter, dart'), 'Tags: flutter, dart');
    expect(l10n.sourceLabel('Demo'), 'Source: Demo');
  });

  // ── DE: Unnamed entry (Großschreibung per CLAUDE.md Hard Rule) ───────
  test('DE + EN: unnamedEntry großgeschrieben', () {
    expect(AppLocalizations(const Locale('de')).unnamedEntry,
        'UNBENANNTER EINTRAG');
    expect(AppLocalizations(const Locale('en')).unnamedEntry, 'UNNAMED ENTRY');
  });

  // ── Parse-Fehlertexte ────────────────────────────────────────────────
  test('DE: Parse-Fehlertexte', () {
    final l10n = AppLocalizations(const Locale('de'));
    expect(l10n.parseErrorInvalidRoot,
        'Ungültiges JSON: Wurzel muss Objekt oder Liste sein.');
    expect(l10n.parseErrorInvalidItems, contains('items'));
    expect(l10n.parseErrorInvalidEntry, contains('Eintrag'));
  });

  test('EN: Parse error messages', () {
    final l10n = AppLocalizations(const Locale('en'));
    expect(l10n.parseErrorInvalidRoot, contains('root'));
    expect(l10n.parseErrorInvalidItems, contains('items'));
    expect(l10n.parseErrorInvalidEntry, contains('object'));
  });

  // ── Fallback auf DE bei unbekannter Locale ───────────────────────────
  test('Fallback auf DE bei unbekannter Locale', () {
    final l10n = AppLocalizations(const Locale('fr'));
    expect(l10n.notLoaded, 'Noch nicht geladen');
    expect(l10n.typeAll, 'ALLE');
    expect(l10n.cancel, 'Abbrechen');
  });
}
