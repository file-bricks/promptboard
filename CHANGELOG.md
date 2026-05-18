# Changelog

Alle nennenswerten Änderungen an PromptBoard werden hier dokumentiert.

## [Unreleased] - 2026-05-16

### Hinzugefügt

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

- Neue Tests für Inline-Variablen in Rohkopie, Markdown-Kopie und
  Abbruch-Statusmeldungen.
- 42/42 pytest-Tests grün.
- Neue Tests für Typvorlagen und deren Integration in `create_item()`.
- 38/38 pytest-Tests grün.

## [1.1.1] - 2026-05-12 — Hotfix

### Behoben

- **Absturz nach ProfiPrompt-/ExplorerPro-Import**: Signal-Rekursion in `reload_list()`. Beim `item_list.clear()` wurde `currentItemChanged` ausgelöst, das den noch nicht aktualisierten `current_item_id` zurück in `save_current_item()` schickte, was erneut `reload_list()` aufrief — bei einer leeren oder gerade geleerten Library führte das zu Stack-Recursion und Abbruch ohne Stacktrace im Log.

### Verändert

- `reload_list()` schützt das Rebuild der Liste mit `blockSignals(True/False)`.
- Neuer `Storage.upsert_many()` — eine `load_items()` + eine `save_items()` für beliebige Batch-Größe (statt O(n²) Reads + Writes pro Import-Item).
- `import_profiprompt_library` und `import_explorerpro_library` rufen `save_current_item()` vor dem Import, nutzen `upsert_many`, setzen `current_item_id = None` vor dem `reload_list()` und selektieren das gewünschte Item per Helper `_select_item_by_id()` danach.

### Tests

- Neuer Regression-Test `test_import_profiprompt_does_not_recurse_or_crash` baut ein echtes `MainWindow` + `Storage` + `QSettings`, importiert drei ProfiPrompt-Einträge und prüft `reload_list`-Aufrufzähler < 10 sowie korrekten finalen Selektionsstand.
- 30 / 30 pytest-Tests grün.

## [1.1.0] - 2026-05-12

### Hinzugefügt

- **Einstellungen als Menü-Dialog** statt eigener Tab (`menu Einstellungen → Einstellungen…`). Hauptfenster zeigt nur noch die Bibliothek; Konfiguration läuft über einen modalen `SettingsDialog`.
- **Drittes Theme „Vibrant“** mit violett-orangenen Akzentfarben, zusätzlich zu Light/Dark/System.
- **Internationalisierung (DE/EN)**: neuer `i18n`-Layer (`src/i18n.py`) mit `tr()`-Helper; alle UI-Strings (Menü, Buttons, Labels, Statusmeldungen, Dialoge) sprachfähig. Sprache wählbar in den Einstellungen und persistent gespeichert. Standard: Deutsch.
- Live-Sprachwechsel: das Hauptfenster relabelt sich beim Wechsel der Sprache, ohne Neustart.
- `SettingsManager` erweitert um `language` (de/en) und Theme-Choice `vibrant`.

### Verändert

- Hauptfenster (`promptboard.py`) refactored: `QTabWidget` entfernt, Settings-Tab in `SettingsDialog` extrahiert (`src/settings_dialog.py`). Menübar bekommt zwei Menüs: „Datei“ und „Einstellungen“.
- Repository-Transfer von `lukisch/promptboard` zu `file-bricks/promptboard` (neben ProfiPrompt).

### Tests

- 29/29 weiterhin grün nach Refactor.

## [1.0.0] - 2026-05-12

### Hinzugefügt

- **ExplorerPro-Adapter (bidirektional)**: Import aus `~/.explorerpro/prompts.json` und Rückexport mit Round-Trip-Idempotenz (stabile IDs `explorerpro:prompt:*`); ExplorerPro-Einträge, die nicht aus PromptBoard kommen, bleiben beim Export erhalten.
- **QTabWidget-Layout**: Tab "Bibliothek" und Tab "Einstellungen" für klarere Trennung von Inhalt und Konfiguration.
- **Theme-System** (`theme.py`): Light/Dark/System-Modus via QPalette-Override, persistent gespeichert.
- **Rechtsklick-Kontextmenü** auf der Eintragsliste: Kopieren, Materialisieren, Löschen direkt zugänglich (laut ursprünglicher Idee).
- **Icon-Asset gewired**: `PromptBoard.ico` ist Fenster- und Tray-Icon (Fallback `PromptBoard.png` und Qt-Standard-Icon).
- **Logging** (`logging_setup.py`): Rotating-File-Handler nach `%LOCALAPPDATA%\PromptBoard\promptboard.log`, 1 MB, 3 Backups.
- **Fehler-Dialoge**: Storage-, Import-, Export- und Materialisierungs-Fehler werden über `QMessageBox.warning` mit Pfad/Detail angezeigt; Fehler werden geloggt.
- **Optional bestätigungsdialog** vor Materialisierung mit existierender Zieldatei (Schalter in Settings, Default: aus).
- **PyInstaller-Build**: `pyinstaller.spec` + `build.bat` erzeugen `PromptBoard-1.0.0-win64.exe` (single-file, windowed) in `releases/v1.0.0/` inkl. Source-Zip, CHANGELOG, SHA256SUMS.
- **Dev-Dependencies** als `requirements-dev.txt` (`pytest`, `pyinstaller`).
- **MIT-Lizenz**.

### Verändert

- `atomic_write_json` als modul-level Helper aus `storage.py` extrahiert; sowohl Storage als auch ExplorerPro-Adapter nutzen denselben atomaren Write-Pfad.
- `SettingsManager` um Keys `imports/explorerpro_data`, `view/theme`, `materialize/confirm_overwrite` erweitert.
- `start.bat` unverändert lauffähig; zusätzlich `build.bat` für Release-Build.

### Tests

- 29 pytest-Tests grün (8 neue ExplorerPro-Adapter, 4 neue Theme, 5 neue Settings, plus bestehende Storage/Materializer/Profiprompt/Query/Promptboard-Tests).

## [0.1.0-seed] - 2026-05-10

### Hinzugefügt

- Ursprüngliche Idee in `IDEE.txt`.
- Erster lauffähiger PySide6-Prototyp unter `src/` mit Tray, lokalem `library.json`-Storage (atomares Schreiben), Editor, Copy-to-Clipboard, content-first Markdown-Materialisierung, ProfiPrompt-Latest-Import.
- ProfiPrompt-Schema-Mapping mit Board-Zuordnungen und stabilen Import-IDs `profiprompt:prompt:*`.
- Sortier-/Filter-Logik mit auswählbarem Modus und Mehrwortsuche.
- Löschvorgang mit Bestätigungsdialog.
- Onboarding-Dokumente: AGENTS, CLAUDE, ARCHITECTURE, DECISIONS, KONZEPT, GLOSSARY, Feature-Analyse, START/STATE/TODO/AUFGABEN/DONE.
- `requirements.txt`, `start.bat`, erste Tests.
