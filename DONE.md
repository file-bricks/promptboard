# DONE.md - Erledigte Aufgaben

> Archiv für erledigte Aufgaben. Neue Einträge nach Möglichkeit aus TODO.md hierher verschieben, statt sie dort nur zu löschen.

## v1.2-Start (2026-05-13)

- Inline-Variablen `{{name}}` analog ExplorerPro umgesetzt: Rohkopie und
  Markdown-Kopie fragen Platzhalter beim Kopieren interaktiv ab, ersetzen sie
  einmalig und brechen bei Abbruch ohne falsche Erfolgsmeldung sauber ab.
- Regressionstests für Inline-Variablen und Abbruch-Status ergänzt; Teststand
  auf 42/42 pytest-Tests erhöht.
- Vorlagen pro Eintragstyp umgesetzt: neue Einträge übernehmen jetzt je nach
  aktivem Typfilter oder Editor-Typ passende Namen und Inhaltsvorlagen.
- Regressionstests für Typvorlagen ergänzt; Teststand auf 38/38 pytest-Tests erhöht.
- Nächsten v1.2-Schwerpunkt festgelegt und direkt umgesetzt: Batch-Materialisierung
  als erster Fokus gewählt.
- Batch-Materialisierung umgesetzt: Mehrfachauswahl im Board, Materialisierung
  ausgewählter Einträge per Button und Kontextmenü.
- Release-Artefakt `releases/v1.1.1/PromptBoard-1.1.1-win64.exe` in einer
  isolierten Offscreen-Session gestartet; Startup-Log und Theme-Initialisierung
  bestätigt.
- Erweiterte Copy-Modi ergänzt: Rohinhalt bleibt der Standard, Markdown-Kopie
  ist jetzt über Button-Menü und Kontextmenü verfügbar.
- `copy_item_markdown()` ergänzt und mit zwei Regressionstests abgesichert.
- Teststand auf 33/33 pytest-Tests angehoben.

## Lifecycle-Sync + v1.1.1-Stand (2026-05-12)

- Lokaler Projektordner auf `REL-PUB_PromptBoard` umgestellt.
- Projektstatus, Aufgabenlisten und Release-Dokumente auf den echten Stand `v1.1.1` synchronisiert.
- Root-Dokumente (`releases.json`, `PROJECT_STATUS.md`) auf REL-PUB umgestellt.
- GitHub-Releases `v1.0.0`, `v1.1.0` und `v1.1.1` bestätigt.
- 30/30 pytest-Tests erneut verifiziert.

## v1.1-Sprint (2026-05-12)

- **Settings als Menü-Dialog** statt eigener Tab (`menu Einstellungen → Einstellungen…`); `src/settings_dialog.py` neu.
- **3. Theme „Vibrant"** mit violett-orangenen Akzentfarben.
- **i18n DE/EN** mit `src/i18n.py` und `tr()`-Helper; Live-Sprachwechsel; alle UI-Strings übersetzt.
- `SettingsManager` um `language` und Theme-Choice `vibrant` erweitert.
- Repo von `lukisch/promptboard` zu `file-bricks/promptboard` transferiert (neben ProfiPrompt).
- v1.1.0 PyInstaller-Build + GitHub Release mit Asset-Upload.
- 29/29 pytest-Tests grün nach Refactor.

## v1.0-Sprint (2026-05-12)

- **ExplorerPro-Adapter (bidirektional)** — `src/explorerpro_adapter.py` mit Import + Export, stabilen IDs `explorerpro:prompt:*`, Round-Trip-Idempotenz, Schutz von Fremd-Einträgen beim Export.
- **QTabWidget mit Tabs Bibliothek + Einstellungen** — `src/promptboard.py` umstrukturiert.
- **Theme-System** — `src/theme.py` mit Light/Dark/System-Modi via QPalette-Override.
- **Rechtsklick-Kontextmenü** auf der Eintragsliste (Kopieren, Materialisieren, Löschen).
- **Icon-Asset gewired** — `PromptBoard.ico` in Fenster + Tray + EXE-Icon.
- **Logging** — `src/logging_setup.py` mit RotatingFileHandler nach `%LOCALAPPDATA%\PromptBoard\promptboard.log`.
- **Fehler-Dialoge** — Storage/Import/Export/Materialisierung mit `QMessageBox.warning` + Logging.
- **Konflikt-Dialog bei Materialisierung** (optional, Schalter in Settings).
- **PyInstaller-Spec + build.bat** — `pyinstaller.spec`, `build.bat`, `requirements-dev.txt`.
- **MIT-Lizenz** als `LICENSE`.
- **RELEASES.md** angelegt für v1.0.0.
- **CHANGELOG.md v1.0.0-Block** mit detailliertem Stand.
- **Tests: 29/29 grün** — 8 neue ExplorerPro-Adapter-Tests, 4 neue Theme-Tests, 5 neue Settings-Tests.
- **SettingsManager erweitert** — Keys `imports/explorerpro_data`, `view/theme`, `materialize/confirm_overwrite`.
- **storage.atomic_write_json** als modul-level Helper extrahiert (von ExplorerPro-Adapter wiederverwendet).

## Erledigt (vorher)

- 2026-05-12 — Sortier- und Filterlogik präzisiert (auswählbare Sortierung, Mehrwortsuche, Helper-Modul und Tests).
- 2026-05-12 — Löschvorgang mit Bestätigungsdialog und Abbruchstatus abgesichert.
- 2026-05-10 — Eintrags- und Typmodell robuster gemacht (Enum-Koerzierung, Tag-Normalisierung, sichere Markdown-Dateinamen).
- 2026-05-10 — Projekt als `DEV_PromptBoard` klassifiziert.
- 2026-05-10 — Onboarding-Dokumentation und Produktspezifikation angelegt.
- 2026-05-10 — Erster PySide6-MVP mit Tray, JSON-Speicherung, Editor, Copy und Materialisierung umgesetzt.
- 2026-05-10 — ProfiPrompt-Latest-Import aus `prompts.json` implementiert.
- 2026-05-10 — ProfiPrompt-Schema auf PromptBoard gemappt (alle Prompts importiert, Board-Zuordnungen als Metadaten, stabile Import-IDs).
- 2026-05-10 — Markdown-Materialisierungsformat als content-first Export mit leichtem Metadatenkopf und Herkunftsmarker festgelegt.
- 2026-05-10 — Tests und GUI-Smoketest erfolgreich ausgeführt.
