---
name: promptboard-state
type: state-snapshot
version: 1.1.1
updated: 2026-05-22
updated_by: GPT
current_phase: REL-PUB v1.1.1 stabilisiert; Windows-Store-Vorbereitung für v1.2 mit reproduzierbaren Screenshots erweitert
last_verified: 2026-05-22
description: |
  PromptBoard ist als öffentliches Desktop-Tool veröffentlicht. Die aktuelle
  Linie steht bei v1.1.1 inklusive Hotfix für den Import-Crash,
  vollständiger Release-Artefakte und lokalem REL-PUB-Lifecycle.
  Batch-Materialisierung, Typvorlagen, Inline-Variablen, globale Hotkeys und
  jetzt auch reproduzierbare Store-Screenshots sind umgesetzt.
  56/56 Tests grün. PyInstaller-Build + Release-Pipeline vorhanden.
---

# STATE.md - Aktueller Projekt-Stand

**Next review:** nach dem ersten echten MSIX-/WACK-Lauf oder nach Eintrag der
finalen Partner-Center-Werte.

## Current Phase

**v1.1.1 released auf file-bricks/promptboard.** Die GitHub-Releases
`v1.0.0`, `v1.1.0` und `v1.1.1` sind live. Der lokale Projektordner trägt den
Lifecycle `REL-PUB_PromptBoard`.

## Focus gerade

Die Bugfix-Runde ist abgeschlossen. Der aktuelle Fokus liegt auf der
Windows-Store-Vorbereitung: Metadaten, Privacy-Text, Build-Wrapper und
reproduzierbare Screenshots sind da; offen bleiben Partner-Center-Werte sowie
der echte MSIX-/WACK-Lauf.

## Letzte bedeutsame Aktion

2026-05-22:
- **Bugfix-Runde ergänzt**: Batch-Materialisierung speichert offene Edits jetzt
  vor dem Export und globale Hotkeys können gefahrlos zweimal gestartet werden.
- **Teststand** auf 56/56 pytest-Tests erhöht.
- **Store-Screenshots automatisiert**: `_tools/generate_store_screenshots.py`
  erzeugt reproduzierbar `tray.png`, `library.png`, `editor.png` und
  `settings.png` unter `README/screenshots/store/`.
- **Screenshot-Smoke-Test** ergänzt: `tests/test_store_screenshots.py`
  verifiziert, dass alle vier PNGs geschrieben werden.

2026-05-20:
- **Windows-Store-Vorbereitung konkretisiert**: `store_package.json`,
  `STORE_LISTING.md`, `PRIVACY_POLICY.md`, `build_store.bat` und
  `_tools/store_release.py` angelegt.
- **Store-Workflow an die zentrale `_STORE`-Pipeline angebunden**.
- **3 neue Tests** für Store-Metadaten/Helferskript ergänzt; Teststand auf
  54/54 pytest-Tests erhöht.

2026-05-18:
- **6 Bugs gefixt**: EN-Filter, Dangling-Pointer in `reload_list()`,
  Dirty-Tracking, Re-Selektion nach Save sowie Datenverlust bei Create/Delete.
- **Globale Hotkeys umgesetzt** für Tray-Toggle und Quick-Copy.
- Teststand auf 51/51 pytest-Tests erhöht.

2026-05-16 bis 2026-05-14:
- **Inline-Variablen**, **Typvorlagen** und **Batch-Materialisierung**
  umgesetzt und jeweils per Regressionstests abgesichert.

## Next

- [x] Release-Artefakt `releases/v1.1.1/PromptBoard-1.1.1-win64.exe`
      manuell smoke-testen.
- [x] Nächsten v1.2-Schwerpunkt festlegen und starten.
- [x] Inline-Variablen `{{name}}` im Copy-Flow umsetzen.
- [x] Windows-Store-Einreichung als MSIX technisch prüfen.
- [x] Store-Screenshots für Tray, Bibliothek, Editor und Einstellungen erzeugen.

## Aktuelle Blocker

- Keine technischen Code-Blocker.
- Für den echten MSIX-Build fehlen noch die finalen Partner-Center-Werte
  (`publisher`, `identity_name`).

## Notizen für nächste Session

- ExplorerPro-Adapter überspringt `apps.json` bewusst.
- Materialisierungsbestätigung bleibt standardmäßig `False`.
- Materialisierte Dateien behalten Platzhalter unverändert; nur Copy-Flows
  lösen `{{name}}` interaktiv auf.
- Theme-Wechsel läuft zur Laufzeit ohne Neustart.
- Logdatei: `%LOCALAPPDATA%\PromptBoard\promptboard.log`.
- `build_store.bat` nutzt die zentrale `_STORE`-Pipeline und erwartet eine
  vorhandene EXE in `dist/` oder `releases/v1.1.1/`.
- `store_package.json` enthält bewusst Platzhalter für Publisher/Identity.
- Store-Screenshots liegen unter `README/screenshots/store/` und können per
  `_tools/generate_store_screenshots.py` neu erzeugt werden.

## Kurz-Historie

- 2026-05-10 — Projekt klassifiziert, Onboarding-Struktur angelegt, erster MVP.
- 2026-05-12 — v1.0/v1.1/v1.1.1-Release-Linie, ExplorerPro-Adapter, Theme,
  Settings-Dialog, Logging und Import-Hotfix fertiggestellt.
- 2026-05-14 bis 2026-05-16 — Batch-Materialisierung, Typvorlagen und
  Inline-Variablen umgesetzt.
- 2026-05-18 — Bugfix-Runde + globale Hotkeys.
- 2026-05-20 — Store-Metadaten, Listing, Privacy-Text und Build-Wrapper ergänzt.
- 2026-05-22 — Reproduzierbare Store-Screenshots und Screenshot-Smoke-Test ergänzt.
