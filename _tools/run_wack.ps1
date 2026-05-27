param(
    [string]$MsixPath = "",
    [string]$ReportDir = ""
)

$projectRoot = Split-Path $PSScriptRoot -Parent
$softwareRoot = Split-Path (Split-Path $projectRoot -Parent) -Parent
$wackScript = Join-Path $softwareRoot "_STORE\msstore_wack.ps1"

if (!$MsixPath) {
    $MsixPath = Join-Path $projectRoot "releases\PromptBoard.msix"
}

if (!$ReportDir) {
    $ReportDir = Join-Path $projectRoot "releases\test_reports"
}

if (!(Test-Path $wackScript)) {
    Write-Host "FEHLER: Zentrales WACK-Skript nicht gefunden: $wackScript" -ForegroundColor Red
    exit 1
}

if (!(Test-Path $MsixPath)) {
    Write-Host "FEHLER: PromptBoard-MSIX nicht gefunden: $MsixPath" -ForegroundColor Red
    Write-Host "Tipp: zuerst `python _tools\store_release.py msix-preflight --exe ... --use-test-identity` oder den finalen Store-Build ausführen." -ForegroundColor Yellow
    exit 1
}

$argumentList = @(
    "-ExecutionPolicy Bypass",
    ('-File "{0}"' -f $wackScript),
    ('-MsixPath "{0}"' -f $MsixPath),
    ('-ReportDir "{0}"' -f $ReportDir)
) -join " "

Start-Process powershell -Verb RunAs -ArgumentList $argumentList | Out-Null

Write-Host "Erhöhter WACK-Lauf gestartet." -ForegroundColor Green
Write-Host "MSIX: $MsixPath"
Write-Host "Reports: $ReportDir"
Write-Host "Nach Abschluss: python _tools\store_release.py review-wack-report"
