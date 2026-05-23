# TODO.md - Aktive Tasks

> Nur offene Aufgaben. Erledigtes nach [DONE.md](./DONE.md) archivieren.

## Active

- Keine offenen Aufgaben.

## Backlog (für v1.2+)

- [x] Globale Hotkeys umgesetzt (Tray-Show, Quick-Copy zuletzt benutzter Eintrag; Windows-native Registrierung, Fallback ohne Konflikt).
- [ ] Prüfen, ob PromptBoard direkt einen kompatiblen Teil des ProfiPrompt-Speichers lesen/schreiben soll.
- [ ] ExplorerPro: AppEntries als optionaler PromptBoard-Typ?
- [ ] Partner-Center-Publisher/Identity für den Store in `store_package.json` eintragen.
- [ ] MSIX + WACK-Lauf mit `build_store.bat` und `_STORE/msstore_build_msix.ps1` durchführen.

## Done

- [x] Windows-Store-Vorbereitung automatisiert: `store_package.json`,
  `STORE_LISTING.md`, `PRIVACY_POLICY.md`, `build_store.bat` und
  `_tools/store_release.py` angelegt; Store-Einreichung in konkrete Folgeaufgaben zerlegt.
- [x] Reproduzierbare Store-Screenshots erzeugt: `_tools/generate_store_screenshots.py`
  schreibt `tray.png`, `library.png`, `editor.png` und `settings.png` nach
  `README/screenshots/store/`; Smoke-Test `tests/test_store_screenshots.py` prüft die Ausgabe.
- [x] Inline-Variablen-Substitution `{{name}}` analog ExplorerPro umgesetzt:
  Rohkopie und Markdown-Kopie fragen Platzhalter beim Kopieren ab, ersetzen
  sie einmalig und brechen bei Dialog-Abbruch sauber ab.
- [x] Regressionstests für Inline-Variablen ergänzt; Teststand auf 42/42 pytest-Tests angehoben.
- [x] Vorlagen pro Eintragstyp umgesetzt: neue Einträge übernehmen jetzt je nach
  aktivem Typfilter oder Editor-Typ passende Namen und Inhaltsschablonen.
- [x] Regressionstests für Typvorlagen ergänzt; Teststand auf 38/38 pytest-Tests angehoben.
- [x] Nächsten v1.2-Schwerpunkt festgelegt und umgesetzt: Batch-Materialisierung als
  nächster Fokus gewählt und direkt implementiert.
- [x] Batch-Materialisierung umgesetzt: Mehrfachauswahl im Board, Materialisierung
  ausgewählter Einträge per Button und Kontextmenü.
- [x] Release-Artefakt `releases/v1.1.1/PromptBoard-1.1.1-win64.exe`
  manuell smoke-testen: isolierter Offscreen-Start, Log-Initialisierung und
  Laufzeitstabilität geprüft.
- [x] Erweiterte Copy-Modi umgesetzt: Markdown-Kopie per Button-Menü und Kontextmenü
- [x] `copy_item_markdown()` ergänzt und mit Regressionstests abgesichert
