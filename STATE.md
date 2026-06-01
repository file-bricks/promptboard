---
name: promptboard-state
type: state-snapshot
version: 1.1.1
updated: 2026-06-02
updated_by: GPT
current_phase: REL-PUB v1.1.1 stabilisiert; Portierungsplan usecase-basiert geprüft
last_verified: 2026-06-02
description: |
  PromptBoard ist als öffentliches Desktop-Tool veröffentlicht. Die aktuelle
  Linie steht bei v1.1.1 inklusive Hotfix für den Import-Crash,
  vollständiger Release-Artefakte und lokalem REL-PUB-Lifecycle.
  Batch-Materialisierung, Typvorlagen, Inline-Variablen, globale Hotkeys sowie
  der Store-Workflow stehen; dazu kommt ein erster read-only Flutter-Companion
  für Android und iOS. Der Portierungsplan wurde am 2026-06-02 auf Features,
  Usecases und getrennte Usecase-Settings zurückgeführt.
---

# STATE.md - Aktueller Projekt-Stand

**Next review:** nach dem ersten Android-/iOS-Smoke mit echter `library.json`
oder nach dem ersten erhöhten WACK-Lauf über `_tools\run_wack.ps1`.

## Current Phase

**v1.1.1 released auf file-bricks/promptboard.** Die GitHub-Releases
`v1.0.0`, `v1.1.0` und `v1.1.1` sind live. Der lokale Projektordner trägt den
Lifecycle `REL-PUB_PromptBoard`.

## Focus gerade

Die Bugfix-Runde ist abgeschlossen. Der aktuelle Fokus liegt auf zwei klar
getrennten Plattformpfaden: der Windows-Store-Vorbereitung und einem ersten
Flutter-Mobile-Companion für Android/iOS. Metadaten, Privacy-Text,
Build-Wrapper, reproduzierbare Screenshots, lokaler MSIX-Preflight und jetzt
auch ein projektlokaler WACK-Start-/Review-Flow sind da; im Mobile-Strang gibt
es nun einen read-only Viewer für `library.json` per Demo, Zwischenablage oder
manueller JSON-Eingabe. Offen bleiben Partner-Center-Werte, der erhöhte echte
WACK-Lauf, macOS-/Linux-Source-Smokes und ein echter Datei-/Share-Import im
Flutter-Companion.

## Letzte bedeutsame Aktion

2026-06-02:
- **Portierungsplan geprüft und geschärft**: `PORTIERUNGSPLAN.md` leitet die
  Plattformentscheidung jetzt aus Features, Usecases und getrennten
  Usecase-Settings ab.
- **Austauschformat dokumentiert**: `EXPORTFORMAT.md` beschreibt `library.json`
  als lokales, dateibasiertes Format für den read-only Companion.
- **Mobile-Grenze festgelegt**: Android/iOS bleiben Companion für Lesen, Suchen
  und Kopieren. Schreibsync und direkte Server-Synchronisierung sind Nicht-Ziele
  ohne belegten Live-Mehrgerätebedarf.

2026-05-27:
- **Flutter-Mobile-Companion als MVP umgesetzt**: Das vorhandene
  `flutter_port/`-Scaffold zeigt PromptBoard-`library.json` jetzt read-only
  mobil an.
- **Drei Ladepfade im Mobile-UI**: Demo-Daten, Import aus der Zwischenablage
  und manuelle JSON-Eingabe direkt im Bottom Sheet.
- **Mobile-Nutzung fokussiert**: Suche, Typfilter, Detailansicht und
  Copy-Button decken den ersten Android-/iOS-Unterwegs-Usecase ab, ohne den
  Desktop-Storage zu beschreiben.
- **Flutter-Smoke-Test ergänzt**: Widget-Test prüft Demo-Import und mobile
  Suchfilterung.
- **WACK-Wrapper projektspezifisch angebunden**: `_tools/run_wack.ps1`
  startet den zentralen `_STORE/msstore_wack.ps1` mit festen PromptBoard-
  Pfaden erhöht, statt dass der Lauf jedes Mal händisch zusammengesetzt
  werden muss.
- **XML-Review im Store-Helper**: `_tools/store_release.py review-wack-report`
  findet den neuesten Report unter `releases/test_reports/` oder lädt einen
  expliziten XML-Pfad und fasst PASS/FAIL/WARNING kompakt zusammen.
- **Build-Hinweise nachgezogen**: `build_store.bat`, `AUFGABEN.txt` und
  `TODO.md` nennen jetzt den reproduzierbaren WACK-Start und die
  Report-Prüfung.
- **Teststand** für den Store-Helper erneut erweitert.

2026-05-24:
- **Store-Workflow gehärtet**: `_tools/store_release.py` überschreibt
  Partner-Center-Werte nicht mehr mit Platzhaltern.
- **Lokale Store-Overrides ergänzt**: `store_package.local.json` oder
  `PROMPTBOARD_STORE_*` können Publisher/Identity lokal liefern, ohne den
  getrackten Standardworkflow zu verbiegen.
- **Früher Readiness-Check**: `build_store.bat` prüft jetzt vor dem Staging,
  ob `publisher` und `identity_name` echte Werte haben.
- **MSIX-Preflight ergänzt**: `store_package.json` setzt für die Desktop-App
  jetzt `runFullTrust`, `_tools/store_release.py` synchronisiert
  `store_assets/` und kann via `msix-preflight` den generischen
  `_STORE`-MSIX-Build mit temporären effektiven Werten anstoßen, ohne die
  getrackten Platzhalter dauerhaft zu überschreiben.
- **Lokaler MSIX-Build verifiziert**: `releases/PromptBoard.msix` wurde
  erfolgreich erzeugt; der direkte WACK-Lauf scheitert nur noch an fehlender
  Erhöhung/UAC.
- **Teststand** für den Store-Helper erweitert.

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
- [x] Flutter-Companion als read-only Android/iOS-MVP aus dem Scaffold bauen.
- [x] Portierungsplan usecase-basiert prüfen und aktualisieren.
- [ ] Partner-Center-Werte eintragen und WACK-Report prüfen.
- [ ] macOS-/Linux-Source-Smokes dokumentieren.
- [ ] Flutter-Companion um Dateiimport oder Share-Intent für `library.json`
      erweitern.

## Aktuelle Blocker

- Keine technischen Code-Blocker.
- Für den finalen Store-Lauf fehlen weiter die finalen Partner-Center-Werte
  (`publisher`, `identity_name`); sie blockieren echte Einreichungen jetzt
  aber sauber und früh.
- Der WACK-Lauf benötigt weiter erhöhte Rechte; `_tools\run_wack.ps1`
  standardisiert jetzt nur den Aufruf, ersetzt aber nicht die nötige UAC-
  Bestätigung und keinen echten Admin-Durchlauf.
- Der Mobile-Companion lädt `library.json` noch nicht direkt als Datei oder
  Share-Intent; aktuell laufen Demo, Zwischenablage und manuelle JSON-Eingabe.

## Notizen für nächste Session

- ExplorerPro-Adapter überspringt `apps.json` bewusst.
- Materialisierungsbestätigung bleibt standardmäßig `False`.
- Materialisierte Dateien behalten Platzhalter unverändert; nur Copy-Flows
  lösen `{{name}}` interaktiv auf.
- Theme-Wechsel läuft zur Laufzeit ohne Neustart.
- Logdatei: `%LOCALAPPDATA%\PromptBoard\promptboard.log`.
- `build_store.bat` nutzt die zentrale `_STORE`-Pipeline und erwartet eine
  vorhandene EXE in `dist/` oder `releases/v1.1.1/`.
- `store_package.json` darf Platzhalter behalten; lokale echte Werte können
  über `store_package.local.json` oder `PROMPTBOARD_STORE_*` kommen.
- `python _tools\store_release.py msix-preflight --exe dist\PromptBoard-1.1.1-win64.exe --use-test-identity`
  baut einen lokalen MSIX-Preflight und stellt danach die getrackte
  `store_package.json` wieder her.
- `powershell -ExecutionPolicy Bypass -File "_tools\run_wack.ps1"` startet
  den zentralen WACK-Runner mit PromptBoard-Pfaden erhöht.
- `python _tools\store_release.py review-wack-report` liest den neuesten
  XML-Report unter `releases\test_reports\` und fasst nur die relevanten
  FAIL-/WARNING-Blöcke zusammen.
- `store_assets/` wird aus dem App-Icon abgeleitet und liefert dem generischen
  `_STORE`-MSIX-Builder die erwarteten Logos.
- Store-Screenshots liegen unter `README/screenshots/store/` und können per
  `_tools/generate_store_screenshots.py` neu erzeugt werden.
- `flutter_port/` ist ein read-only Mobile-Viewer für `library.json`; nächster
  realistischer Schritt ist Datei- oder Share-Import statt reinem Paste-Flow.
- `EXPORTFORMAT.md` dokumentiert die Companion-Grenze: keine Logs, keine
  lokalen Pfade, keine Hotkey-/Store-Konfigurationen und kein Schreibsync.

## Kurz-Historie

- 2026-05-10 — Projekt klassifiziert, Onboarding-Struktur angelegt, erster MVP.
- 2026-05-12 — v1.0/v1.1/v1.1.1-Release-Linie, ExplorerPro-Adapter, Theme,
  Settings-Dialog, Logging und Import-Hotfix fertiggestellt.
- 2026-05-14 bis 2026-05-16 — Batch-Materialisierung, Typvorlagen und
  Inline-Variablen umgesetzt.
- 2026-05-18 — Bugfix-Runde + globale Hotkeys.
- 2026-05-20 — Store-Metadaten, Listing, Privacy-Text und Build-Wrapper ergänzt.
- 2026-05-22 — Reproduzierbare Store-Screenshots und Screenshot-Smoke-Test ergänzt.
- 2026-05-27 — Flutter-Companion-MVP für Android/iOS mit JSON-Import,
  Suche, Typfilter und Detailansicht umgesetzt.
