# PromptBoard

> Ein leichtgewichtiges Systemtray-Board für Prompts, Skills, Workflows, Rollen und Agenten.

PromptBoard ist als schnelles Desktop-Werkzeug für wiederverwendbare LLM-Bausteine gedacht. Im Unterschied zu umfangreicheren Prompt-Managern steht hier nicht Versionierung oder Board-Komplexität im Vordergrund, sondern schneller Zugriff: öffnen, filtern, kopieren, direkt editieren und bei Bedarf als `.md`-Datei materialisieren.

## Status

**Phase:** erster lauffähiger Prototyp  
**Code:** PySide6-MVP vorhanden  
**Repository:** noch nicht initialisiert  
**Aktueller Ordnerstatus:** `LLM/DEV_PromptBoard`

## Zielbild

PromptBoard soll ein kleines Tray-Tool werden, das lokal gespeicherte Wissensbausteine verwaltet:

- Prompts
- Skills
- Workflows
- Rollen
- Agenten

Jeder Eintrag soll direkt editierbar, nach Typ und Name sortierbar und per Klick in die Zwischenablage kopierbar sein. Per Rechtsklick kann ein Eintrag zusätzlich als Markdown-Datei an einen konfigurierbaren Ort materialisiert werden, standardmäßig auf den Desktop. Der Export bleibt inhaltszentriert: H1, kompakter Metadatenkopf, dann der eigentliche Inhalt.

## Abgrenzung

- **Leichter als ProfiPrompt:** keine große Versionshistorie, kein schweres Board-System als Kern.
- **Robuster als AutoPrompter:** keine fragile Keyboard-/Daemon-Logik als MVP.
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

Der nächste sinnvolle Schritt ist der ExplorerPro-Adapter und die weitere UX-Politur, damit aus dem MVP ein stabiler Arbeitsprototyp wird.

## Prototyp starten

```powershell
cd 'C:\Users\User\OneDrive\.TOPICS\.SOFTWARE\LLM\DEV_PromptBoard'
python -m pip install -r requirements.txt
python src\promptboard.py
```

Unter Windows alternativ per Doppelklick auf `start.bat`.
