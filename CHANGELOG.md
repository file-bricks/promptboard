# Changelog

Alle nennenswerten Änderungen an PromptBoard werden hier dokumentiert.

## [Unreleased] - 2026-05-22

### Hinzugefügt

- **Store-Screenshot-Generator**: `_tools/generate_store_screenshots.py`
  erzeugt reproduzierbar Bilder für Tray, Bibliothek, Editor und
  Einstellungen unter `README/screenshots/store/`.
- **Store-Screenshot-Assets**: `tray.png`, `library.png`, `editor.png` und
  `settings.png` liegen jetzt versioniert im Projekt.

### Behoben

- Batch-Materialisierung speichert offene Edits jetzt vor dem Export, damit
  ausgewählte Einträge nicht mit veralteten Inhalten exportiert werden.
- Der Hotkey-Startpfad verträgt wiederholte Aufrufe ohne Absturz.

### Tests

- Neuer Smoke-Test für die Screenshot-Erzeugung
  (`tests/test_store_screenshots.py`).
- 56/56 pytest-Tests grün.

## [Unreleased] - 2026-05-20

### Hinzugefügt

- **Windows-Store-Vorbereitung**: `store_package.json`,
  `STORE_LISTING.md`, `PRIVACY_POLICY.md`, `build_store.bat` und
  `_tools/store_release.py` legen eine reproduzierbare MSIX-Vorbereitung auf
  Basis der zentralen `_STORE`-Pipeline an.
- **Globale Hotkeys**: Windows-native Registrierung für Tray-Fenster
  ein-/ausblenden und Schnellkopie des zuletzt benutzten Eintrags.
- **Inline-Variablen-Substitution für Copy-Flows**: Platzhalter wie
  `{{name}}` werden bei Rohkopie und Markdown-Kopie ExplorerPro-kompatibel
  abgefragt, mehrfach vorkommende Variablen nur einmal erfasst und dann in
  allen Vorkommen ersetzt.
- Hinweis im Editor-Placeholder, dass `{{name}}` beim Kopieren interaktiv
  abgefragt wird.
- **Typvorlagen für neue Einträge**: Neue Einträge übernehmen jetzt je nach
  aktivem Typfilter oder aktuell gewähltem Editor-Typ passende Startnamen und
  Inhaltsschablonen für `PROMPT`, `SKILL`, `WORKFLOW`, `ROLLE` und `AGENT`.

### Verändert

- `ClipboardService` meldet Abbrüche der Variablenabfrage jetzt explizit an
  die UI zurück, damit keine falschen Erfolgsmeldungen entstehen.

### Tests

- Neue Tests für Store-Metadaten, Listing-Text und Root-Dateien des
  Windows-Store-Helfers.
- 54/54 pytest-Tests grün.
- Neue Tests für Persistenz des zuletzt benutzten Eintrags und
  Hotkey-Dispatch.
- 51/51 pytest-Tests grün.
- Neue Tests für Inline-Variablen in Rohkopie, Markdown-Kopie und
  Abbruch-Statusmeldungen.
- 42/42 pytest-Tests grün.
- Neue Tests für Typvorlagen und deren Integration in `create_item()`.
- 38/38 pytest-Tests grün.

## [1.1.1] - 2026-05-12 — Hotfix

### Behoben

- **Absturz nach ProfiPrompt-/ExplorerPro-Import**: Signal-Rekursion in
  `reload_list()` führte beim Leeren und Neuaufbau der Liste zu Stack-Recursion
  und Abbruch ohne Stacktrace im Log.

### Verändert

- `reload_list()` schützt das Rebuild der Liste mit `blockSignals(True/False)`.
- Neuer `Storage.upsert_many()` für effiziente Batch-Importe.
- `import_profiprompt_library` und `import_explorerpro_library` sichern
  vorherige Edits, nutzen `upsert_many` und selektieren das Zielobjekt erst
  nach dem Rebuild.

### Tests

- Neuer Regression-Test gegen Import-Rekursion.
- 30/30 pytest-Tests grün.

## [1.1.0] - 2026-05-12

### Hinzugefügt

- **Einstellungen als Menü-Dialog** statt eigener Tab.
- **Drittes Theme „Vibrant“** zusätzlich zu Light/Dark/System.
- **Internationalisierung (DE/EN)** mit Live-Wechsel und persistenten Settings.
- `SettingsManager` erweitert um `language` und Theme-Choice `vibrant`.

### Verändert

- Hauptfenster refactored: `QTabWidget` entfernt, `SettingsDialog` extrahiert.
- Repository-Transfer von `lukisch/promptboard` zu `file-bricks/promptboard`.

### Tests

- 29/29 pytest-Tests grün.

## [1.0.0] - 2026-05-12

### Hinzugefügt

- **ExplorerPro-Adapter (bidirektional)** mit stabilen IDs und Round-Trip.
- **QTabWidget-Layout** für Bibliothek und Einstellungen.
- **Theme-System** (`theme.py`) mit persistentem Modus.
- **Kontextmenü** auf der Eintragsliste.
- **Icon-Asset gewired**: `PromptBoard.ico` als Fenster-, Tray- und EXE-Icon.
- **Logging** nach `%LOCALAPPDATA%\\PromptBoard\\promptboard.log`.
- **Fehler-Dialoge** für Storage-, Import-, Export- und Materialisierungsfehler.
- **Optionaler Überschreibdialog** vor Materialisierung.
- **PyInstaller-Build** via `pyinstaller.spec` und `build.bat`.
- **Dev-Dependencies** in `requirements-dev.txt`.
- **MIT-Lizenz**.

### Verändert

- `atomic_write_json` als gemeinsamer Helper extrahiert.
- `SettingsManager` um ExplorerPro-/Theme-/Materialize-Settings erweitert.

### Tests

- 29 pytest-Tests grün.

## [0.1.0-seed] - 2026-05-10

### Hinzugefügt

- Ursprüngliche Idee in `IDEE.txt`.
- Erster lauffähiger PySide6-MVP unter `src/` mit Tray, lokalem
  JSON-Storage, Editor, Copy-to-Clipboard, Markdown-Materialisierung und
  ProfiPrompt-Latest-Import.
- ProfiPrompt-Schema-Mapping mit stabilen Import-IDs.
- Sortier-/Filter-Logik mit auswählbarem Modus und Mehrwortsuche.
- Löschvorgang mit Bestätigungsdialog.
- Onboarding-Dokumente, `requirements.txt`, `start.bat` und erste Tests.
