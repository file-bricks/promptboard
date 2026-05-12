@echo off
cd /d "%~dp0"
python --version >nul 2>&1
if errorlevel 1 (
    echo [FEHLER] Python nicht gefunden!
    pause
    exit /b 1
)
set PYTHONIOENCODING=utf-8
echo Starte PromptBoard...
python src\promptboard.py
if errorlevel 1 pause
