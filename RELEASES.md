# PromptBoard — Releases

> Pro Version eine Zeile. Aktuelle Version oben.

## v1.0.0 — 2026-05-12

**Status:** released
**Plattform:** Windows x64
**Stores:** GitHub Release (geplant)

### Artefakte (`releases/v1.0.0/`)

| Datei | Inhalt |
|---|---|
| `PromptBoard-1.0.0-win64.exe` | Single-File Windows-Executable (PyInstaller, windowed, mit Icon) |
| `PromptBoard-1.0.0-source.zip` | Quellcode (`src/`) als Archiv |
| `CHANGELOG.txt` | Changelog dieser Version |
| `SHA256SUMS.txt` | SHA-256 Prüfsummen aller Artefakte |

### Highlights

- ExplorerPro-Adapter (bidirektional: Import + Rückexport, Round-Trip-Idempotenz)
- QTabWidget: getrennte Tabs "Bibliothek" und "Einstellungen"
- Theme-System (Light/Dark/System) mit Persistenz
- Rechtsklick-Kontextmenü auf der Eintragsliste
- Icon-Asset (`PromptBoard.ico`) in Fenster und Tray
- Logging nach `%LOCALAPPDATA%\PromptBoard\promptboard.log`
- Fehler-Dialoge statt nur Status-Label
- 29 pytest-Tests grün

### Bekannte Einschränkungen

- ExplorerPro-Adapter ignoriert `apps.json` (App-Entries ≠ PromptBoard-Typen).
- Materialisierungsbestätigung default deaktiviert (laut KONZEPT: Standard überschreibt ohne Rückfrage).
- Globale Hotkeys, Batch-Materialisierung und Vorlagen sind im Backlog (nicht v1.0).

### Cross-Refs

- Concept: [KONZEPT.md](./KONZEPT.md)
- Architecture: [ARCHITECTURE.md](./ARCHITECTURE.md)
- Decisions: [DECISIONS.md](./DECISIONS.md)
- Storage spec: see `src/storage.py` (atomic JSON writes)
- Build: `build.bat` + `pyinstaller.spec`
