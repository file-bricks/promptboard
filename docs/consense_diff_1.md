# Consense-Diff 1 — PromptBoard Readback 2026-08-12

## Nutzer- und Steuerdokumente

- README.md und README_de.md tragen denselben Readback: 116/116 Pytest,
  Source-Smoke/Compile-Smoke, veröffentlichte v1.1.1 und offenes Store-P1.
- STATE.md und CHANGELOG.md führen den Readback chronologisch und lassen alte,
  datierte Teststände unverändert erkennbar.
- RELEASES.md beschreibt jetzt die tatsächliche Archivgrenze und genau eine
  kanonische SHA256SUMS.txt.
- STORE_LISTING.md und PRIVACY_POLICY.md nennen den lokalen Vorbereitungsstatus,
  nicht eine fingierte Store-Einreichung.
- llms.txt ist auf 2026-08-12 datiert und nennt dieselben Kommandos/Grenzen.

## Artefakte und Lizenzen

- `scripts/certify_release.py` erzeugt ein deterministisches Archiv aus
  getrackten Dateien. Runtime-Daten, Caches, Store-Staging, frühere Releases
  und die historische `flutter_port/`-Linie gelangen nicht hinein.
- `releases/v1.1.1/` enthält lokal EXE, Source-ZIP, CHANGELOG.txt und
  SHA256SUMS.txt; jede Prüfsumme wurde gegen die Datei zurückgelesen.
- Der MSIX-Preflight stoppte reproduzierbar mit `makeappx.exe nicht gefunden`.
  Deshalb bleibt die MSIX-/WACK-Zeile offen.
- THIRD_PARTY_LICENSES.txt ist im Source-Archiv enthalten und verknüpft die
  vier tatsächlich geladenen Qt-for-Python-Runtime-Wheels mit ihren Lizenzdaten.

## Offen für den nächsten Lauf

1. OneDrive-Steuerdateien nach Freigabe des Locks live gegen diesen Readback
   prüfen und erst danach gezielt synchronisieren.
2. Die Entscheidung zur Paketmetadaten-Version `1.1.3` gegenüber der
   veröffentlichten `v1.1.1` durch den Projektverantwortlichen treffen.
3. Windows SDK (`makeappx.exe`), echte Partner-Center-Werte und erhöhter WACK-
   Readback bereitstellen; anschließend `verify --require-msix` wiederholen.
