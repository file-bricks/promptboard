---
name: promptboard-state
type: state-snapshot
version: 1.1.1
updated: 2026-05-18
updated_by: Claude
current_phase: REL-PUB v1.1.1 stabilisiert, 6 Bugs gefixt (Dirty-Tracking, Dangling-Pointer, Filter, Delete-Datenverlust)
last_verified: 2026-05-18
description: |
  PromptBoard ist als öffentliches Desktop-Tool veröffentlicht. Die aktuelle
  Linie steht bei v1.1.1 inklusive Hotfix für den Import-Crash,
  vollständiger Release-Artefakte und lokalem REL-PUB-Lifecycle.
  Batch-Materialisierung, Typvorlagen und Inline-Variablen für Copy-Flows
  sind umgesetzt. 6 Bugs gefixt (Dirty-Tracking, Dangling-Pointer,
  EN-Filter, Delete-Datenverlust, Create-Datenverlust). 47/47 Tests grün.
  PyInstaller-Build + Release-Pipeline vorhanden.
---

# STATE.md - Aktueller Projekt-Stand

**Next review:** nach Auswahl des nächsten v1.2-Tickets oder nach dem
nächsten Runtime-Test.

## Current Phase

**v1.1.1 released auf file-bricks/promptboard.** v1.0.0, v1.1.0 und v1.1.1
sind als GitHub-Releases mit Asset-Upload live. Die SOFTWARE-Registry ist
synchronisiert und der lokale Projektordner trägt jetzt den Lifecycle
`REL-PUB_PromptBoard`.

## Focus gerade

Bugfix-Runde abgeschlossen (6 Bugs). Stabilisierungsphase mit v1.2-Foki
auf Batch-Materialisierung, Typvorlagen und Inline-Variablen für Copy-Flows.
Weitere Folge-Iterationen siehe TODO-Backlog.

## Letzte bedeutsame Aktion

2026-05-18:
- **6 Bugs gefixt** (systematisches Debugging mit /bugfix-protocol):
  1. EN-Filter kaputt: Hardcoded `"ALLE"` → `ItemType.choices()`-Check
  2. Dangling C++ Pointer: `reload_list()` im Save-Pfad → `_update_list_item_text()`
  3. Kein Dirty-Tracking: Jeder Item-Wechsel speicherte → `_dirty`-Flag eingeführt
  4. Falsche Re-Selektion nach Save: Nebeneffekt von Bug 2, durch gleichen Fix behoben
  5. Create-Datenverlust: `create_item()` sichert jetzt vorher ungespeicherte Edits
  6. Delete-Datenverlust: `clear_editor()` nur noch bei leerer Liste nach Delete
- **5 neue Regressionstests** hinzugefügt (47/47 grün)

2026-05-16:
- **Inline-Variablen für Copy-Flows** ergänzt: Platzhalter wie `{{name}}`
  werden bei Rohkopie und Markdown-Kopie ExplorerPro-kompatibel abgefragt,
  einmal ersetzt und bei Dialog-Abbruch ohne falsche Erfolgsmeldung verworfen.
- **Discoverability** erhöht: Editor-Placeholder weist jetzt auf `{{name}}`
  hin.
- **Teststand** auf 42/42 pytest-Tests angehoben.

2026-05-15:
- **Typvorlagen pro Eintragstyp** ergänzt: Neue Einträge orientieren sich
  jetzt am aktiven Typfilter oder Editor-Typ und starten mit passenden
  Namen und Inhaltsschablonen für Prompt, Skill, Workflow, Rolle und Agent.
- **Teststand** auf 38/38 pytest-Tests angehoben.

2026-05-14:
- **Batch-Materialisierung** ergänzt: Mehrfachauswahl im Board, Export von
  mehreren Einträgen per Button/Kontextmenü und Regressionstests für die
  Sammel-Materialisierung.
- **Teststand** auf 35/35 pytest-Tests angehoben.

2026-05-13:
- **Erweiterte Copy-Modi** ergänzt: `Kopieren` bleibt roh, zusätzlich gibt es
  Markdown-Kopie per Button-Menü und Kontextmenü. Dazu wurden zwei neue
  Regressionstests ergänzt.
- **Teststand** auf 33/33 pytest-Tests angehoben.
- **Release-Artefakt v1.1.1** im isolierten Smoke-Test gestartet; Log bestätigt
  `PromptBoard startet` und Theme-Initialisierung.

2026-05-12:
- **v1.1.1-Hotfix** behebt den Import-Crash nach ProfiPrompt-/ExplorerPro-
  Import über eine abgesicherte `reload_list()`-Sequenz und `Storage.upsert_many()`.
- **GitHub-Release-Linie** mit v1.0.0, v1.1.0 und v1.1.1 ist live.
- **Lokaler Lifecycle-Sync** abgeschlossen: Ordner-Rename auf
  `REL-PUB_PromptBoard`, Projektstatus und Root-Registry aktualisiert.
- **30 pytest-Tests grün**.

## Next

- [x] Release-Artefakt `releases/v1.1.1/PromptBoard-1.1.1-win64.exe`
      manuell unter Windows smoke-testen (Doppelklick, Tray, DE/EN,
      Import, Materialisierung) -- erledigt 2026-05-13 (isolierter Starttest
      mit bestätigtem Startup-Log).
- [x] Nächsten v1.2-Schwerpunkt festlegen und als konkrete Umsetzung starten
      -- erledigt 2026-05-14 (Batch-Materialisierung).
- [x] Inline-Variablen `{{name}}` analog ExplorerPro im Copy-Flow umsetzen
      -- erledigt 2026-05-16 (Rohkopie und Markdown-Kopie fragen Variablen
      jetzt beim Kopieren ab).

## Aktuelle Blocker

- Keine technischen Blocker. Offene Punkte sind nur die Priorisierung der
  nächsten v1.2-Schritte.

## Notizen für nächste Session

- ExplorerPro-Adapter überspringt `apps.json` bewusst (kein Mapping auf PromptBoard-Typen).
- Materialisierungsbestätigung default `False` (laut KONZEPT überschreibend, Standard).
- Materialisierte Dateien behalten Platzhalter unverändert; nur Copy-Flows
  lösen `{{name}}` interaktiv auf.
- Theme-Wechsel zur Laufzeit ohne Neustart (Palette-Override über `Fusion`-Style).
- Logfile-Pfad: `%LOCALAPPDATA%\PromptBoard\promptboard.log`.
- Backlog für v1.2+: Globale Hotkeys, Windows-Store, ggf.
  ProfiPrompt-Live-Storage-Adapter.

## Historie

- 2026-05-10 — Projekt klassifiziert, Konzept weitergedacht, Onboarding-Struktur.
- 2026-05-10 — Erster lauffähiger PySide6-Prototyp mit Tests und GUI-Smoketest.
- 2026-05-10 — Eintrags- und Typmodell robuster gemacht.
- 2026-05-10 — Markdown-Materialisierungsformat als content-first Export.
- 2026-05-10 — ProfiPrompt-Schema gemappt, stabile Import-IDs.
- 2026-05-12 — Sortier/Filter-Logik präzisiert.
- 2026-05-12 — Löschvorgang mit Bestätigungsdialog.
- 2026-05-15 — Typvorlagen für neue Einträge ergänzt; aktive Typauswahl für
  neue Elemente genutzt; Teststand auf 38/38 erhöht.
- 2026-05-16 — Inline-Variablen für Rohkopie und Markdown-Kopie ergänzt;
  Dialog-Abbruch zeigt jetzt korrekte Statusmeldungen; Teststand auf 42/42 erhöht.
- 2026-05-18 — 6 Bugs gefixt: Dirty-Tracking, Dangling-Pointer, EN-Filter,
  Delete/Create-Datenverlust. 5 neue Regressionstests. Teststand auf 47/47 erhöht.
- **2026-05-12 — v1.0 Sprint: ExplorerPro-Adapter (bidirektional), Theme-System, Settings-Tab, Logging, Fehler-Dialoge, PyInstaller-Build, LICENSE, RELEASES.md, CHANGELOG v1.0.0, 29/29 Tests grün.**
- **2026-05-12 — v1.1.1 Hotfix + Lifecycle-Sync: Import-Crash behoben, 30/30 Tests grün, GitHub-Releases v1.0.0/v1.1.0/v1.1.1 live, lokaler Ordner auf `REL-PUB_PromptBoard` umgestellt.**
