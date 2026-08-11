@echo off
REM Build script for PromptBoard v1.1.1
REM ===================================
REM Builds a single-file Windows executable via PyInstaller,
REM stages the complete release set and verifies SHA256SUMS.txt.

setlocal enabledelayedexpansion
cd /d "%~dp0"

set VERSION=1.1.1
set RELEASE_DIR=releases\v%VERSION%

echo.
echo === PromptBoard Build v%VERSION% ===
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [FEHLER] Python nicht gefunden!
    pause
    exit /b 1
)

REM Ensure PyInstaller is available
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo [INFO] PyInstaller fehlt, installiere requirements-dev.txt...
    python -m pip install -r requirements-dev.txt
    if errorlevel 1 (
        echo [FEHLER] PyInstaller-Installation fehlgeschlagen.
        pause
        exit /b 1
    )
)

echo.
echo --- Clean build/dist ---
if exist build rmdir /S /Q build
if exist dist rmdir /S /Q dist
if not exist "%RELEASE_DIR%" mkdir "%RELEASE_DIR%"

echo.
echo --- PyInstaller ---
python -m PyInstaller pyinstaller.spec --noconfirm
if errorlevel 1 (
    echo [FEHLER] Build fehlgeschlagen.
    pause
    exit /b 1
)

echo.
echo --- Stage and certify release artefacts ---
python scripts\certify_release.py stage --exe "dist\PromptBoard-1.1.1-win64.exe"
if errorlevel 1 (
    echo [FEHLER] Release-Staging fehlgeschlagen.
    exit /b 1
)
python scripts\certify_release.py verify --require-msix
if errorlevel 1 (
    echo [FEHLER] Vollstaendige Zertifizierung fehlgeschlagen; MSIX/WACK-Gate bleibt offen.
    exit /b 1
)

echo.
echo === BUILD ERFOLGREICH ===
echo Release-Artefakte in %RELEASE_DIR%\
dir "%RELEASE_DIR%"
echo.
endlocal
