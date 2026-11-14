# PromptBoard — WACK-Protokoll (Windows App Certification Kit)

## Ziel

Nach dem lokalen MSIX-Build (`PromptBoard-1.1.3-win64.exe` / `releases\PromptBoard.msix`) dokumentiert dieses Protokoll den reproduzierbaren WACK-Lauf für die Store-Einreichung (`Geiger.PromptBoard`).

## Vorbereiteter Befehl (Elevated PowerShell)

```powershell
powershell -ExecutionPolicy Bypass -File "_tools\run_wack.ps1"
python _tools\store_release.py review-wack-report
```

Alternativ direkt über `appcert.exe`:

```powershell
$projectRoot = "C:\_Local_DEV\repos\PromptBoard"
$reportDir = Join-Path $projectRoot "releases\test_reports"
New-Item -ItemType Directory -Force -Path $reportDir | Out-Null
& appcert.exe test -appxpackagepath "$projectRoot\releases\PromptBoard.msix" -reportoutputpath "$reportDir\wack_report.xml"
```

## Prüfkriterien

- **Crashes and hangs:** App startet ohne unbehandelte Ausnahmen und beendet sich sauber
- **App manifest compliance:** Deklaration von `runFullTrust`, `TargetDeviceFamily` und 6 Tier-2-Sprachressourcen (`de-de`, `en-us`, `es-es`, `zh-cn`, `ja-jp`, `ru-ru`)
- **Package compliance:** Gültige XML-Struktur (`AppxManifest.xml`) und Tile-Assets (`44x44`, `50x50`, `150x150`, `310x150`, `310x310`)
- **Zero-Egress & Privacy:** Reine Offline-Nutzung, lokale Speicherung unter `~/.promptboard/library.json` sowie benutzerbezogene QSettings
