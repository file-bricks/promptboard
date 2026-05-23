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
echo 3. ..\..\_STORE\msstore_build_msix.ps1 mit dem Projekt ausführen
echo 4. WACK und manuellen Store-Testlauf durchführen
echo.
endlocal
