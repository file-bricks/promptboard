@echo off
setlocal
cd /d "%~dp0"

set EXE_PATH=dist\PromptBoard-1.1.1-win64.exe
if not exist "%EXE_PATH%" set EXE_PATH=releases\v1.1.1\PromptBoard-1.1.1-win64.exe

python --version >nul 2>&1
if errorlevel 1 (
    echo [FEHLER] Python nicht gefunden.
    exit /b 1
)

if not exist "%EXE_PATH%" (
    echo [FEHLER] Keine PromptBoard-EXE gefunden.
    echo Erwartet: dist\PromptBoard-1.1.1-win64.exe oder releases\v1.1.1\PromptBoard-1.1.1-win64.exe
    exit /b 1
)

echo.
echo === PromptBoard Windows-Store Vorbereitung ===
python _tools\store_release.py write-root-files
if errorlevel 1 exit /b 1

python _tools\store_release.py check
if errorlevel 1 (
    echo.
    echo [FEHLER] Partner-Center-Werte fehlen noch.
    echo Trage `publisher` und `identity_name` in `store_package.json` ein
    echo oder lege lokal `store_package.local.json` bzw. die Umgebungsvariablen
    echo `PROMPTBOARD_STORE_PUBLISHER` und `PROMPTBOARD_STORE_IDENTITY_NAME` an.
    exit /b 1
)

python _tools\store_release.py prepare --exe "%EXE_PATH%"
if errorlevel 1 exit /b 1

echo.
echo === Pretest ===
powershell -ExecutionPolicy Bypass -File "..\..\_STORE\msstore_pretest.ps1" -ExePath "%CD%\%EXE_PATH%" -ProjectRoot "%CD%"
if errorlevel 1 exit /b 1

echo.
echo Vorbereitung abgeschlossen.
echo Nächste Schritte:
echo 1. Falls noch nicht geschehen: Partner-Center-Werte lokal oder tracked pflegen
echo 2. Screenshots ergänzen
echo 3. Lokaler MSIX-Preflight ohne dauerhaftes Überschreiben:
echo    python _tools\store_release.py msix-preflight --exe "%EXE_PATH%" --use-test-identity
echo 4. Finalen Store-Build mit echten Werten prüfen
echo 5. Erhöhten WACK-Lauf über den Projekt-Wrapper starten:
echo    powershell -ExecutionPolicy Bypass -File "_tools\run_wack.ps1"
echo 6. Danach den neuesten XML-Report kompakt prüfen:
echo    python _tools\store_release.py review-wack-report
echo.
endlocal
