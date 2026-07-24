# Changelog

Alle nennenswerten Änderungen an PromptBoard werden hier dokumentiert.

## [Unreleased] - 2026-07-22

### Dokumentation & Marketing

- **Sichtbarkeit & Discoverability**: `llms.txt` Last-checked Datum auf `2026-07-22` aktualisiert und RAG/LLM-Suchphrasen erweitert.
- **README & Badges**: Test-Badge und Status-Text in `README.md` & `README_de.md` auf 85/85 bestandene Pytest-Tests synchronisiert.
- **Architektur-Visualisierung**: Mermaid-Diagramm für System-Tray-, JSON-Store- und Markdown-Materialisierungsfluss in `README.md` und `README_de.md` ergänzt.
- **Disambiguation**: Abgrenzung gegenüber webbasierten/SaaS PromptBoard-Tools zur Vermeidung von Such- und Agenten-Kollisionen geschärft.

## [Unreleased] - 2026-06-28

### Sicherheit

- Die optionale Dev-Testabhängigkeit `pytest` ist auf `>=9.0.3` angehoben,
  weil OSV für die bisher erlaubte 8.x-Untergrenze `GHSA-6w46-j5rx-g56g`
  meldet und `9.0.3` im Zielcheck keine Treffer hat.

### Dokumentation

- `THIRD_PARTY_LICENSES.txt` für die direkten Python-Runtime-Abhängigkeiten und
  das transitive Qt-for-Python-Wheel-Set ergänzt (plus Regressionstest
  `tests/test_third_party_licenses.py`, der das Inventar gegen Dependency-Drift
  absichert).

### Fehlerbehebungen

- **BUGSWEEP-41 – ExplorerPro-Export: Silent Data Loss bei ID-losen Einträgen**
  (`src/explorerpro_adapter.py`, Rebuild-Schleife).
  Mehrere ExplorerPro-`prompts.json`-Einträge ohne `id`-Feld wurden ab dem
  zweiten Eintrag still verworfen: `seen_existing.add("")` beim ersten Eintrag
  ließ alle weiteren durch den `continue`-Zweig fallen.
  Fix: ID-lose Einträge werden jetzt separat behandelt — direkt in `output`
  geschrieben ohne Deduplizierungscheck, da ohne ID keine Zuordnung möglich ist.
  Bestehende Einträge *mit* ID werden weiterhin wie bisher dedupliziert.

### Tests

- Neuer Regressionstest `test_export_preserves_all_idless_existing_entries`
  in `tests/test_explorerpro_adapter.py` (BUGSWEEP-41): 3 ID-lose Einträge
  exportieren → alle 3 müssen erhalten bleiben.
- `python -m pytest -q` läuft lokal mit 85/85 Tests grün.

## [Unreleased] - 2026-06-19

### Dokumentation & Interop

- `EXPORTFORMAT.md` nennt jetzt den tatsächlichen Desktop-Standardpfad
  `~/.promptboard/library.json`; `%APPDATA%/PromptBoard/library.json` ist nur
  noch als Legacy-Fallback für lesende Integrationen dokumentiert.
- Die BACH-Interop-Hinweise nennen die Suchreihenfolge:
  `BACH_PROMPTBOARD_LIBRARY`, Desktop-Standardpfad, dann AppData-Fallback.

### Tests

- Neuer Settings-Test fixiert den Default von `SettingsManager.get_data_path()`
  auf `~/.promptboard` und prüft, dass der Ordner angelegt wird.
- `python -m pytest -q` läuft lokal mit 78/78 Tests grün.

## [Unreleased] - 2026-06-17

### Verändert

- Store-/MSIX-Logos lassen sich jetzt reproduzierbar mit
  `python _tools/store_release.py refresh-icons` aus dem kanonischen
  Skateboard-Icon `PromptBoard.png` regenerieren.
- Die versionierten `store_assets/`-Logos wurden aus `PromptBoard.png`
  aktualisiert, damit Store-Kacheln nicht mehr das alte Dokument-Icon zeigen.
- `PromptBoard-1.1.1-win64.exe` wurde mit dem aktualisierten Icon neu gebaut
  und unter `dist/` sowie `releases/v1.1.1/` abgelegt.

### Tests

- Neuer Regressionstest stellt sicher, dass der Store-Icon-Refresh
  `PromptBoard.png` als Quelle nutzt und alle erwarteten Store-Asset-Dateien
  neu schreibt.
- `python -m pytest -q` läuft lokal mit 77/77 Tests grün; der neue EXE-Build
  bestand einen kurzen Offscreen-Startsmoke.

## [Unreleased] - 2026-06-12

### Dokumentation & Hygiene

- `llms.txt` auf Standard-Format gebracht: `## Last-checked` an Zeile 1, `## Audience`- und `## Search Phrases`-Block ergänzt; Verweise auf gitignorierte Dateien entfernt.
- `README.md`: Internen OneDrive-Pfad (`Current Folder Status`) entfernt; `cd`-Zeile mit lokalem Pfad aus dem Quickstart entfernt; Onboarding-Tabelle bereinigt (Links auf gitignorierte Dateien entfernt).
- `.gitignore`: Pattern `*_BUGSWEEP_*.py` ergänzt.

## [Unreleased] - 2026-06-10

### Dokumentation & Hygiene

- `README.md` auf Englisch umstrukturiert (English-first) und Übersetzung nach `README_de.md` verschoben.
- `llms.txt` im Root-Verzeichnis hinzugefügt, um Entdeckung und Indexierung durch KI-Crawler zu verbessern.

## [Unreleased] - 2026-06-04

### Hinzugefügt

- Neuer reproduzierbarer Desktop-Source-Smoke `tests/source_platform_smoke.py`
  für den plattformübergreifenden Startpfad mit echtem Umlaut-Content,
  Materialisierung und Hotkey-/Tray-Grundverhalten.
- GitHub-Actions-Job `platform-smoke` für `ubuntu-latest` und `macos-latest`
  ergänzt.

### Verändert

- `create_tray()` fällt ohne verfügbares System-Tray jetzt sauber auf `None`
  zurück, statt Headless- oder Nicht-Windows-Umgebungen unnötig hart zu
  behandeln.
- `_tools/generate_store_screenshots.py` rendert das Tray-Bild bei fehlendem
  System-Tray jetzt über ein äquivalentes Vorschau-Menü und bleibt dadurch
  auch im Offscreen-Testpfad reproduzierbar.

### Tests

- Neuer Regressionstest für den Tray-Fallback in `tests/test_promptboard.py`.
- Lokaler Teststand auf 67/67 pytest-Tests erhöht.
- `python tests/source_platform_smoke.py` lokal grün.

## [Unreleased] - 2026-06-03

### Hinzugefügt

- `pyproject.toml` mit Projektmetadaten, Dev-Extras, pytest-Konfiguration und
  `promptboard`-Console-Script ergänzt.
- GitHub-Actions-Workflow `PromptBoard tests` für Windows und Python 3.11/3.12
  ergänzt.

## [Unreleased] - 2026-05-24

### Behoben

- **Copy-Flow nutzt wieder den sichtbaren Editorzustand**: Listenaktionen wie
  Doppelklick-Schnellkopie holen bei noch ausstehendem Autosave jetzt erst den
  aktuellen Editorinhalt in den Storage, statt veralteten Bibliotheksstand in
  die Zwischenablage zu legen.

### Verändert

- **Windows-Store-Workflow gehärtet**: `_tools/store_release.py` erhält
  bestehende Partner-Center-Werte in `store_package.json`, statt sie beim
  nächsten Vorbereitungslauf wieder durch Platzhalter zu ersetzen.
- **Lokale Store-Overrides**: `store_package.local.json` sowie
  `PROMPTBOARD_STORE_PUBLISHER`, `PROMPTBOARD_STORE_PUBLISHER_DISPLAY` und
  `PROMPTBOARD_STORE_IDENTITY_NAME` können reale Partner-Center-Werte lokal
  einspeisen.
- **Früher Store-Readiness-Check**: `build_store.bat` prüft vor dem Staging,
  ob `publisher` und `identity_name` echte Werte haben.
- **FullTrust-MSIX korrekt vorbereitet**: `store_package.json` setzt für den
  Desktop-Store-Lauf jetzt standardmäßig `runFullTrust`.
- **Store-Assets synchronisiert**: `_tools/store_release.py` spiegelt die
  generierten Icons zusätzlich nach `store_assets/`, damit der generische
  `_STORE/msstore_build_msix.ps1`-Builder ohne manuelle Zusatzschritte läuft.
- **Lokaler MSIX-Preflight**: neuer Befehl
  `python _tools/store_release.py msix-preflight --exe ... --use-test-identity`
  materialisiert effektive Store-Werte nur temporär, erzeugt
  `releases/PromptBoard.msix` und stellt die getrackte Konfiguration danach
  wieder her.

### Tests

- Neue Tests für Konfig-Merging, Platzhalter-Erkennung und Store-Staging mit
  echten effektiven Werten im Helper `tests/test_store_release.py`.
- Neuer lokaler MSIX-Preflight erfolgreich; direkter WACK-Aufruf ist nur noch
  durch fehlende Erhöhung/UAC blockiert.

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
