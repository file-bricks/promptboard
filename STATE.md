---
name: promptboard-state
type: state-snapshot
version: 1.0.0
updated: 2026-05-12
updated_by: Claude/Code
current_phase: v1.0 fertig
last_verified: 2026-05-12
description: |
  PromptBoard v1.0 ist fertig: alle MVP-Features (Tray, Editor, Copy,
  Materialisierung, ProfiPrompt-Import) plus ExplorerPro-Adapter
  (bidirektional), Theme-System, Settings-Tab, Logging, Fehler-Dialoge.
  29/29 Tests grün. PyInstaller-Build + Release-Pipeline vorhanden.
---

# STATE.md - Aktueller Projekt-Stand

**Next review:** nach Lifecycle-Rename + GitHub-Push.

## Current Phase

**v1.0 fertig (Code + Tests + Build-Pipeline).** Verbleibend für Lifecycle-Wechsel von DEV zu RDY/REL-PUB: Ordner-Rename, GitHub-Repo-Init + Push, `releases.json`-Eintrag im SOFTWARE-Root, GitHub-Release v1.0.0 mit Asset-Upload.

## Focus gerade

Lifecycle-Übergang: Build-Verify → Ordner-Rename `DEV_PromptBoard/` → `RDY_PromptBoard/` → `git init` + initial commit → `gh repo create` + push → GitHub Release → SOFTWARE-Registry-Sync.

## Letzte bedeutsame Aktion

v1.0-Sprint 2026-05-12:
- **ExplorerPro-Adapter** (`src/explorerpro_adapter.py`) bidirektional mit Round-Trip-Idempotenz und stabilen IDs.
- **QTabWidget-Layout** mit Tabs "Bibliothek" und "Einstellungen".
- **Theme-System** (`src/theme.py`, `system/light/dark`).
- **Rechtsklick-Kontextmenü** auf der Eintragsliste.
- **Icon-Asset** (`PromptBoard.ico`) wired (Fenster + Tray).
- **Logging** mit Rotating-File-Handler in `%LOCALAPPDATA%\PromptBoard\`.
- **Fehler-Dialoge** für Storage/Import/Export/Materialisierung.
- **PyInstaller-Spec** + `build.bat` + `requirements-dev.txt` + `LICENSE` (MIT) + `RELEASES.md`.
- **29 pytest-Tests grün** (8 neue ExplorerPro, 4 neue Theme, 5 neue Settings).

## Next

- [ ] Build-Artefakt `dist/PromptBoard-1.0.0-win64.exe` verifizieren und in `releases/v1.0.0/` ablegen.
- [ ] Ordner-Rename `DEV_PromptBoard/` → `RDY_PromptBoard/` (Lifecycle-Wechsel laut SOFTWARE/NAMING-SYSTEM.md).
- [ ] `git init` + initial commit + remote (lukisch/promptboard) + push.
- [ ] GitHub Release v1.0.0 mit Asset-Upload (`.exe`, source-zip, SHA256SUMS, CHANGELOG).
- [ ] `C:\Users\User\OneDrive\.TOPICS\.SOFTWARE\releases.json` ergänzen.
- [ ] Lifecycle nach Push: `RDY_` → `REL-PUB_`.

## Aktuelle Blocker

- Keine technischen Blocker; nur Verifikations- + Veröffentlichungs-Schritte.

## Notizen für nächste Session

- ExplorerPro-Adapter überspringt `apps.json` bewusst (kein Mapping auf PromptBoard-Typen).
- Materialisierungsbestätigung default `False` (laut KONZEPT überschreibend, Standard).
- Theme-Wechsel zur Laufzeit ohne Neustart (Palette-Override über `Fusion`-Style).
- Logfile-Pfad: `%LOCALAPPDATA%\PromptBoard\promptboard.log`.
- Backlog für v1.1+: Globale Hotkeys, Batch-Materialisierung, Vorlagen pro Typ, ggf. ProfiPrompt-Live-Storage-Adapter.

## Historie

- 2026-05-10 — Projekt klassifiziert, Konzept weitergedacht, Onboarding-Struktur.
- 2026-05-10 — Erster lauffähiger PySide6-Prototyp mit Tests und GUI-Smoketest.
- 2026-05-10 — Eintrags- und Typmodell robuster gemacht.
- 2026-05-10 — Markdown-Materialisierungsformat als content-first Export.
- 2026-05-10 — ProfiPrompt-Schema gemappt, stabile Import-IDs.
- 2026-05-12 — Sortier/Filter-Logik präzisiert.
- 2026-05-12 — Löschvorgang mit Bestätigungsdialog.
- **2026-05-12 — v1.0 Sprint: ExplorerPro-Adapter (bidirektional), Theme-System, Settings-Tab, Logging, Fehler-Dialoge, PyInstaller-Build, LICENSE, RELEASES.md, CHANGELOG v1.0.0, 29/29 Tests grün.**
