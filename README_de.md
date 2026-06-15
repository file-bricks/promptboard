<img src="assets/banner.svg" width="100%" alt="PromptBoard Banner">

🇩🇪 Deutsche Version | [🇬🇧 English Version](./README.md)

# PromptBoard

> Ein leichtgewichtiges Systemtray-Board für Prompts, Skills, Workflows, Rollen und Agenten.

PromptBoard ist als schnelles Desktop-Werkzeug für wiederverwendbare
LLM-Bausteine gedacht. Im Unterschied zu umfangreicheren Prompt-Managern steht
hier nicht Versionierung oder Board-Komplexität im Vordergrund, sondern
schneller Zugriff: öffnen, filtern, kopieren, direkt editieren und bei Bedarf
als `.md`-Datei materialisieren.

PromptBoard ist ein lokaler Prompt-Manager und eine Windows-Tray-App für wiederverwendbare
LLM-Prompts, Skills, Workflows, Rollen und Agenten. Die Prompt-Bibliotheken bleiben offline,
durchsuchbar und kopierbereit, ohne dass ein Cloud-Konto erforderlich ist.

## Status

**Phase:** öffentlich released (`v1.1.1`), Store- und Plattformhärtung im lokalen Entwicklungsstand aktiv  
**Code:** PySide6-Desktop-App mit 68/68 pytest-Tests  

**CI:** [PromptBoard tests](https://github.com/file-bricks/promptboard/actions/workflows/tests.yml) mit Windows-Pytest sowie macOS-/Linux-Source-Smoke  
**Repository:** [file-bricks/promptboard](https://github.com/file-bricks/promptboard)  
**Aktueller Ordnerstatus:** `LLM/REL-PUB_PromptBoard`  

## Screenshots

Die lokale README-Vorschau und die vier Store-Ansichten werden aus dem
aktuellen UI-Stand erzeugt.

![PromptBoard Hauptansicht](README/screenshots/main.png)

![PromptBoard Tray-Ansicht](README/screenshots/store/tray.png)
![PromptBoard Bibliothek](README/screenshots/store/library.png)
![PromptBoard Editor](README/screenshots/store/editor.png)
![PromptBoard Einstellungen](README/screenshots/store/settings.png)

Die Store-Bilder lassen sich reproduzierbar über
`_tools/generate_store_screenshots.py` neu erzeugen.

## Zielbild

PromptBoard ist ein kleines Tray-Tool zur lokalen Verwaltung von
Wissensbausteinen:

- Prompts
- Skills
- Workflows
- Rollen
- Agenten

Jeder Eintrag ist direkt editierbar, nach Typ und Name sortierbar und per
Klick in die Zwischenablage kopierbar. Per Rechtsklick kann ein Eintrag
zusätzlich als Markdown-Datei an einen konfigurierbaren Ort materialisiert
werden, standardmäßig auf den Desktop. Der Export bleibt inhaltszentriert:
H1, kompakter Metadatenkopf, dann der eigentliche Inhalt.

Globale Hotkeys blenden das Tray-Fenster ein oder aus und kopieren den
zuletzt benutzten Eintrag schnell in die Zwischenablage.

## Abgrenzung

- **Leichter als ProfiPrompt:** keine große Versionshistorie, kein schweres Board-System als Kern.
- **Robuster als AutoPrompter:** keine fragile Keyboard-/Daemon-Logik als Kern.
- **Lokaler als Cloud-Tools:** keine Pflicht zu Online-Sync oder externen APIs.

## Onboarding

| Für... | lies... |
|---|---|
| Erste Session | [START.md](./START.md) |
| Aktueller Stand | [STATE.md](./STATE.md) |
| Aktive Aufgaben | [TODO.md](./TODO.md) und [AUFGABEN.txt](./AUFGABEN.txt) |
| Produktbild | [KONZEPT.md](./KONZEPT.md) |
| Feature-Überblick | [Feature_Analyse_PromptBoard.md](./Feature_Analyse_PromptBoard.md) |
| Architektur | [ARCHITECTURE.md](./ARCHITECTURE.md) |
| Entscheidungen | [DECISIONS.md](./DECISIONS.md) |
| Begriffe | [GLOSSARY.md](./GLOSSARY.md) |
| Agentenregeln | [AGENTS.md](./AGENTS.md) und [CLAUDE.md](./CLAUDE.md) |

## Nächster sinnvoller Schritt

Der nächste sinnvolle Schritt ist jetzt der verbleibende Store-P1-Pfad:
reale Partner-Center-Werte eintragen und den erhöhten WACK-Lauf gegen
`releases/PromptBoard.msix` dokumentieren. Die macOS-/Linux-Source-Smokes sind
ab jetzt reproduzierbar im Projekt und in CI verankert.

## Projekt starten

```powershell
cd 'C:\Users\User\OneDrive\.TOPICS\.SOFTWARE\LLM\REL-PUB_PromptBoard'
python -m pip install -e ".[dev]"
python src\promptboard.py
```

Unter Windows alternativ per Doppelklick auf `start.bat`.
