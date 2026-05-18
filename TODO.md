# TODO.md - Aktive Tasks

> Nur offene Aufgaben. Erledigtes nach [DONE.md](./DONE.md) archivieren.

## Active

- Keine offenen Aufgaben.

## Backlog (für v1.2+)

- [ ] Globale Hotkeys evaluieren (Tray-Show, Quick-Copy zuletzt benutzter Eintrag).
- [ ] Prüfen, ob PromptBoard direkt einen kompatiblen Teil des ProfiPrompt-Speichers lesen/schreiben soll.
- [ ] ExplorerPro: AppEntries als optionaler PromptBoard-Typ?
- [ ] Windows-Store-Einreichung als MSIX (SOFTWARE/WINDOWS_STORE_PIPELINE.md).

## Done

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
