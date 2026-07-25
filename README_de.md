<img src="assets/banner.svg" width="100%" alt="PromptBoard">

<p>
  <b>🇩🇪 Deutsch</b> &nbsp;·&nbsp; <a href="./README.md">🇬🇧 English</a>
</p>

<p>
  <img src="https://img.shields.io/badge/license-MIT-green" alt="Lizenz: MIT">
  <img src="https://img.shields.io/badge/version-v1.1.1-blue" alt="Version v1.1.1">
  <img src="https://img.shields.io/badge/platform-Windows-0078D6?logo=windows&logoColor=white" alt="Plattform: Windows">
  <img src="https://img.shields.io/badge/built%20with-Python%20%26%20PySide6-3776AB?logo=python&logoColor=white" alt="Gebaut mit Python und PySide6">
  <img src="https://img.shields.io/badge/tests-116%2F116%20bestanden-success" alt="Tests: 116/116 bestanden">
</p>

# PromptBoard

**Deine lokale Prompt-Bibliothek — schnell, offline, tray-ready.**

> [!NOTE]
> **Abgrenzung:** `file-bricks/promptboard` ist eine native, lokale Windows-Desktop-Tray-Anwendung (Python & PySide6) zur offline Verwaltung von LLM-Prompts und lokalen Markdown-Materialisierungen. Es ist kein Cloud-Webdienst, keine SaaS-Plattform und keine Browser-Erweiterung.

[Features](#zielbild) &nbsp;·&nbsp; [Architektur](#architektur--datenfluss) &nbsp;·&nbsp; [Screenshots](#screenshots) &nbsp;·&nbsp; [Installation](#projekt-starten) &nbsp;·&nbsp; [Doku](#onboarding)

---

PromptBoard ist ein schnelles Desktop-Werkzeug und eine Windows-Tray-App für wiederverwendbare LLM-Bausteine: Prompts, Skills, Workflows, Rollen und Agenten. Im Unterschied zu umfangreicheren Prompt-Managern steht nicht Versionierung oder Board-Komplexität im Vordergrund, sondern schneller Zugriff: öffnen, filtern, kopieren, direkt editieren und bei Bedarf als `.md`-Datei materialisieren. Die Prompt-Bibliotheken bleiben offline, durchsuchbar und kopierbereit, ohne dass ein Cloud-Konto erforderlich ist.

## Status

**Phase:** öffentlich released (`v1.1.1`), Store- und Plattformhärtung im lokalen Entwicklungsstand aktiv<br/>
**Code:** PySide6-Desktop-App mit 116/116 pytest-Tests<br/>

**CI:** [PromptBoard tests](https://github.com/file-bricks/promptboard/actions/workflows/tests.yml) mit Windows-Pytest sowie macOS-/Linux-Source-Smoke  
**Repository:** [file-bricks/promptboard](https://github.com/file-bricks/promptboard)  
**Aktueller Ordnerstatus:** `LLM/REL-PUB_PromptBoard`  

## Architektur & Datenfluss

```mermaid
flowchart TD
    Tray["Windows System Tray"] --> UI["PySide6 UI-Fenster"]
    UI --> Store[("Lokaler JSON-Speicher<br/>~/.promptboard/library.json")]
    UI --> Exporter["Markdown-Materialisierer<br/>.md Exporter"]
    Exporter --> Desktop["Desktop / Arbeitsbereich"]
    UI --> Clipboard["Windows Zwischenablage"]
    UI <--> AdapterProfiPrompt["ProfiPrompt Adapter"]
    UI <--> AdapterExplorer["ExplorerPro Adapter"]
```

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
python -m pip install -e ".[dev]"
python src\promptboard.py
```

Unter Windows alternativ per Doppelklick auf `start.bat`.

## Lizenz

PromptBoard steht unter der [MIT](LICENSE)-Lizenz. Die Lizenzen der
Laufzeit-Abhängigkeiten sind in [THIRD_PARTY_LICENSES.txt](THIRD_PARTY_LICENSES.txt)
aufgeführt.
