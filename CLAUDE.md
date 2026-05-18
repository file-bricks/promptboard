---
name: promptboard
type: project-docs
profile: FULL
version: 1.1.1
created: 2026-05-10
updated: 2026-05-12
last_verified: 2026-05-12
author: Lukas Geiger
anthropic_compatible: true
description: |
  Projektanweisungen für AI-Coding-Agenten im PromptBoard-Projekt.
  AGENTS.md verweist für Codex und andere Agenten auf diese Datei.
---

# CLAUDE.md - Instructions für AI Coding Agents

> Für LLM-Agenten. Diese Datei ist die projektlokale Single Source of Truth. Vor jeder Arbeit in PromptBoard zusätzlich [START.md](./START.md) und [STATE.md](./STATE.md) lesen.

## Projekt

**PromptBoard** ist ein leichtgewichtiges Systemtray-Tool zur lokalen Verwaltung und Wiederverwendung von Prompts, Skills, Workflows, Rollen und Agenten.

**Pfad:** `C:\Users\User\OneDrive\.TOPICS\.SOFTWARE\LLM\REL-PUB_PromptBoard`  
**Repository:** [file-bricks/promptboard](https://github.com/file-bricks/promptboard)  
**Phase:** öffentlich released, Stabilisierung / v1.2-Backlog  
**Empfohlener Stack:** PySide6, lokale JSON-Speicherung, Markdown-Materialisierung

## Rolle & Stil

Arbeite als Produkt- und Architekturpartner mit Fokus auf:

- Leichtgewichtigkeit statt Feature-Überfrachtung
- robuste lokale Speicherung
- klare Adapter-Grenzen zu Fremdtools
- schnellen Alltagsnutzen

Kommunikation:

- Sprache: Deutsch; Code-Identifier bleiben englisch
- Endnutzertexte nutzen echte Umlaute: ä, ö, ü, Ä, Ö, Ü, ß
- bei Architekturunsicherheit lieber klein anfangen statt vorschnell aufblasen

## Hard Rules

- Keine unnötige Schwergewichtigkeit aus ProfiPrompt oder anderen größeren Tools übernehmen.
- Keine Cloud- oder API-Pflicht in den MVP mischen.
- Keine Keyboard-Automation oder Daemon-Logik als Kern des MVP.
- Bei Materialisierung bleibt das Standardverhalten überschreibend und bestätigt standardmäßig nicht.
- Namen materialisierter Einträge werden als Großschreibung behandelt.
- ExplorerPro- oder Prompt-Manager-Importe als Adapter bauen, nicht als harte Kernabhängigkeit.

## Einstieg

```powershell
# Projektstatus ansehen
Get-ChildItem -Force 'C:\Users\User\OneDrive\.TOPICS\.SOFTWARE\LLM\REL-PUB_PromptBoard'

# Kernidee lesen
Get-Content -LiteralPath 'C:\Users\User\OneDrive\.TOPICS\.SOFTWARE\LLM\REL-PUB_PromptBoard\IDEE.txt'
Get-Content -LiteralPath 'C:\Users\User\OneDrive\.TOPICS\.SOFTWARE\LLM\REL-PUB_PromptBoard\KONZEPT.md'

# App starten / Tests / Build
python src\promptboard.py
python -m pytest -q
build.bat
```

Release-Linie und GitHub-Repo sind aktiv. Historische Konzeptaussagen in den
Dokumenten bleiben als Verlauf stehen; für den Ist-Stand immer zuerst
`STATE.md`, `TODO.md` und `AUFGABEN.txt` lesen.

## Wichtige Dateien

| Datei | Zweck |
|---|---|
| [IDEE.txt](./IDEE.txt) | Ursprüngliche Rohidee |
| [KONZEPT.md](./KONZEPT.md) | Weitergedachte Produktspezifikation |
| [README.md](./README.md) | Projektüberblick |
| [START.md](./START.md) | Session-Bootstrap |
| [STATE.md](./STATE.md) | Aktueller Arbeitsstand |
| [TODO.md](./TODO.md) | Aktive Aufgaben |
| [AUFGABEN.txt](./AUFGABEN.txt) | Kompakte Aufgabenliste nach Software-Pipeline-Konvention |
| [Feature_Analyse_PromptBoard.md](./Feature_Analyse_PromptBoard.md) | Erste Feature-Analyse |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Konzeptionelle Architektur |
| [DECISIONS.md](./DECISIONS.md) | Architektur- und Produktentscheidungen |
| [WORKFLOWS.md](./WORKFLOWS.md) | Wiederkehrende Abläufe |
| [TOOLS.md](./TOOLS.md) | Projektnahe Hilfswerkzeuge |

## Domain-Kontext

PromptBoard liegt in derselben Themenfamilie wie Prompt- und Wissenswerkzeuge, soll aber bewusst leichter bleiben. Es adressiert den Bedarf nach schnellem Zugriff auf wiederverwendbare Textbausteine, nicht nach einem großen Prompt-Archiv mit komplexer Historie.

Zentrale Domänenbausteine:

- Einträge verschiedener Typen
- lokale Bibliothek
- Tray-Zugriff
- Zwischenablage
- Materialisierung nach Markdown
- Fremdformate über Adapter

## Projekt-Struktur

```text
REL-PUB_PromptBoard/
├── IDEE.txt
├── KONZEPT.md
├── README.md
├── START.md
├── STATE.md
├── TODO.md
├── AUFGABEN.txt
├── Feature_Analyse_PromptBoard.md
├── ARCHITECTURE.md
├── DECISIONS.md
├── GLOSSARY.md
├── WORKFLOWS.md
├── PATTERNS.md
├── TOOLS.md
├── DONE.md
├── CHANGELOG.md
├── .gitignore
├── workflows/
├── _tools/
└── .github/
```
