@echo off
REM Build script for PromptBoard v1.0.0
REM ===================================
REM Builds a single-file Windows executable via PyInstaller,
REM copies artefacts into releases\v1.0.0\, generates SHA256SUMS.txt.

setlocal enabledelayedexpansion
cd /d "%~dp0"

set VERSION=1.1.0
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
echo --- Stage release artefacts ---
copy /Y "dist\PromptBoard-1.1.0-win64.exe" "%RELEASE_DIR%\" >nul

echo --- Source archive ---
python -c "import shutil; shutil.make_archive(r'%RELEASE_DIR%\PromptBoard-1.1.0-source', 'zip', '.', 'src')"

echo --- CHANGELOG ---
copy /Y "CHANGELOG.md" "%RELEASE_DIR%\CHANGELOG.txt" >nul

echo --- SHA256SUMS ---
pushd "%RELEASE_DIR%"
if exist SHA256SUMS.txt del SHA256SUMS.txt
for %%F in (*.exe *.zip) do (
    for /f "delims=" %%H in ('certutil -hashfile "%%F" SHA256 ^| findstr /R "^[0-9a-f][0-9a-f]"') do (
        echo %%H  %%F>> SHA256SUMS.txt
    )
)
popd

echo.
echo === BUILD ERFOLGREICH ===
echo Release-Artefakte in %RELEASE_DIR%\
dir "%RELEASE_DIR%"
echo.
endlocal
