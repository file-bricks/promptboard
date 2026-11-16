# PromptBoard — Windows Store Build-Anleitung

## Voraussetzungen

1. Python 3.10+ mit PySide6 (`pip install -e ".[dev]"`)
2. PyInstaller für den Desktop-Build (`build.bat`)
3. Windows 10/11 SDK mit `makeappx.exe`, `signtool.exe` und `appcert.exe` (WACK)
4. Kanonische Partner-Center-Identität `Geiger.PromptBoard` (`CN=52596601-BAB4-4F3F-B182-E8F3F273B202`, Version `1.1.3.0`)

## Build-Schritte

1. PyInstaller Build ausführen:
   ```cmd
   build.bat
   ```
   Erzeugt `dist\PromptBoard-1.1.3-win64.exe`.

2. Store-Paket vorbereiten und MSIX-Preflight prüfen:
   ```powershell
   python _tools\store_release.py prepare
   python _tools\store_release.py msix-preflight
   ```

3. WACK-Zertifizierungstest (mit Administratorrechten) ausführen:
   ```powershell
   powershell -ExecutionPolicy Bypass -File "_tools\run_wack.ps1"
   python _tools\store_release.py review-wack-report
   ```

4. Preflight-Store-Audit und Übersetzungs-Gate verifizieren:
   ```powershell
   python -X utf8 scripts\check_store_readiness.py
   python -X utf8 manage_translations.py --check
   ```
