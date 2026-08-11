# CON1 Anforderungsanalyse — PromptBoard 1136/1137

Stand: 2026-08-12
Scope: ein Selector-Bündel (`TW-PROMPTBOARD-05`, `TW-PROMPTBOARD-06`)

## Auftrag und Nachweisgrenze

Die Nutzer- und Steuerdokumente sollen denselben verifizierten Readback tragen:
Version/Release `v1.1.1`, aktueller Python-Teststand, Plattformgrenzen und
Store-P1-Status. Die Release-Artefakte sollen als ein nachvollziehbares Set aus
EXE, Source-Archiv, Changelog und SHA-256-Inventar vorliegen; die Runtime-
Lizenzdatei muss im Source-Archiv enthalten sein.

Der Plan-D-Klon
`C:\_Local_DEV\repos\REL-PUB_PromptBoard-tasksolver-1136-1137` ist die einzige
Schreibfläche dieses Readbacks. Die OneDrive-Quelle
`C:\Users\lukas\OneDrive\.TOPICS\.SOFTWARE\DATA\REL-PUB_PromptBoard` war beim
Start cloud-locked und fremd-dirty; `AUFGABEN.txt`/`TODO.md` dort wurden daher
nicht überschrieben oder als erledigt markiert.

## Akzeptanzmatrix

| Requirement | Nachweis | Status |
|---|---|---|
| 1136: Teststand, Version, Release und Plattformgrenzen | README/README_de, STATE, CHANGELOG, RELEASES, STORE_LISTING, PRIVACY_POLICY, `llms.txt` | Teilweise erfüllt; Paketmetadaten `1.1.3` und OneDrive-Steuerdateien bleiben offen |
| 1137: EXE, Source-ZIP, Changelog und SHA-256 | `scripts/certify_release.py`, `releases/v1.1.1/`, Readback | Erfüllt für drei lokale Artefakte |
| 1137: MSIX als Release-Set | `store_release.py msix-preflight --use-test-identity` | Offen: `makeappx.exe` fehlt |
| 1137: Runtime-Lizenzinventur | `THIRD_PARTY_LICENSES.txt`, 6.11.1-Runtime-Readback, Archivprüfung | Erfüllt für den dokumentierten Runtime-Scope; kein eingefrorenes SBOM |

## Reproduzierbare Kommandos

```powershell
python -X utf8 -m pytest -q
python -X utf8 tests/source_platform_smoke.py
python -X utf8 -m compileall -q src _tools tests
python -X utf8 scripts\certify_release.py stage --exe dist\PromptBoard-1.1.1-win64.exe
python -X utf8 scripts\certify_release.py verify
python -X utf8 scripts\certify_release.py verify --require-msix  # erwartetes offenes Gate
```

## Entscheidungen

- Historische Testzahlen bleiben datiert; nur der aktuelle Readback wird als
  116/116 behauptet.
- `pyproject.toml` wird nicht auf eine ältere Version zurückgesetzt. Die
  veröffentlichte Artefaktlinie und die unveröffentlichten Paketmetadaten werden
  stattdessen getrennt benannt.
- Fehlende Windows-SDK-Tools, Partner-Center-Zugang oder WACK-Ergebnisse werden
  nicht durch Text oder Test-Identitäten als Store-Abnahme ausgegeben.
