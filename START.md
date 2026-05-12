---
name: promptboard-start
type: session-bootstrap
version: 0.1.0
updated: 2026-05-10
last_verified: 2026-05-10
description: |
  Bootstrap-Sequenz für neue Arbeitssessions im PromptBoard-Projekt.
---

# START.md - Session-Bootstrap für PromptBoard

> Zu Beginn jeder neuen Session in diesem Projekt lesen.

## Bootstrap-Sequenz

1. [CLAUDE.md](./CLAUDE.md) lesen, falls sie nicht automatisch geladen wurde.
2. Prüfen, ob `TEST.txt` oder `TESTS.txt` existiert. Falls ja: keine Dateien ändern, bis der Test-Lock aufgehoben ist.
3. Falls Git später initialisiert wurde: `git status` prüfen.
4. [STATE.md](./STATE.md) lesen.
5. [TODO.md](./TODO.md) und [AUFGABEN.txt](./AUFGABEN.txt) lesen.
6. [KONZEPT.md](./KONZEPT.md) lesen, wenn Produktumfang oder Abgrenzung unklar sind.
7. Bei Architekturfragen [ARCHITECTURE.md](./ARCHITECTURE.md) und [DECISIONS.md](./DECISIONS.md) prüfen.

## Quick Commands

```powershell
# Projektdateien anzeigen
Get-ChildItem -Force 'C:\Users\User\OneDrive\.TOPICS\.SOFTWARE\LLM\DEV_PromptBoard'

# Aktive Aufgaben lesen
Get-Content -LiteralPath 'C:\Users\User\OneDrive\.TOPICS\.SOFTWARE\LLM\DEV_PromptBoard\TODO.md'
Get-Content -LiteralPath 'C:\Users\User\OneDrive\.TOPICS\.SOFTWARE\LLM\DEV_PromptBoard\AUFGABEN.txt'
```

## Session-Ende

1. [STATE.md](./STATE.md) aktualisieren: Was wurde getan, was ist als Nächstes dran, welche Blocker gibt es?
2. [TODO.md](./TODO.md) aktualisieren.
3. Bei bedeutsamen Produkt- oder Architekturentscheidungen [DECISIONS.md](./DECISIONS.md) ergänzen.
4. Bei strukturrelevanten Änderungen [CHANGELOG.md](./CHANGELOG.md) pflegen.
