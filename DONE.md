# DONE.md - Erledigte Aufgaben

> Archiv für erledigte Aufgaben. Neue Einträge nach Möglichkeit aus TODO.md hierher verschieben, statt sie dort nur zu löschen.

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
