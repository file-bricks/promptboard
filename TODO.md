# TODO.md - Aktive Tasks

> Nur offene Aufgaben. Erledigtes nach [DONE.md](./DONE.md) archivieren.

## Active (Lifecycle-Übergang nach v1.0)

- [ ] Build-Artefakt `dist/PromptBoard-1.0.0-win64.exe` verifizieren (Doppelklick, Tray, beide Tabs).
- [ ] `releases/v1.0.0/` mit `.exe`, `source.zip`, `CHANGELOG.txt`, `SHA256SUMS.txt` befüllen.
- [ ] Ordner-Rename `DEV_PromptBoard/` → `RDY_PromptBoard/`.
- [ ] `git init` + initial commit (alle MVP-Dateien außer `.gitignore`-Patterns).
- [ ] GitHub-Repo `lukisch/promptboard` anlegen (oder `research-line/promptboard` — User-Entscheidung).
- [ ] `git remote add origin` + `git push -u origin main`.
- [ ] GitHub Release v1.0.0 mit Asset-Upload (`gh release create v1.0.0 releases/v1.0.0/*`).
- [ ] `C:\Users\User\OneDrive\.TOPICS\.SOFTWARE\releases.json` um PromptBoard-Eintrag erweitern.
- [ ] Lifecycle nach Push: `RDY_` → `REL-PUB_PromptBoard/`.
- [ ] STATUS_UEBERSICHT bzw. PROJECT_STATUS.md im SOFTWARE-Root aktualisieren (optional).

## Backlog (für v1.1+)

- [ ] Globale Hotkeys evaluieren (Tray-Show, Quick-Copy zuletzt benutzter Eintrag).
- [ ] Batch-Materialisierung (mehrere Einträge gleichzeitig).
- [ ] Vorlagen pro Eintragstyp.
- [ ] Prüfen, ob PromptBoard direkt einen kompatiblen Teil des ProfiPrompt-Speichers lesen/schreiben soll.
- [ ] ExplorerPro: AppEntries als optionaler PromptBoard-Typ?
- [ ] Windows-Store-Einreichung als MSIX (SOFTWARE/WINDOWS_STORE_PIPELINE.md).
- [ ] Erweiterte Copy-Modi (Markdown statt Plain Text, Roh-Inhalt vs. mit Metadaten).
- [ ] Inline-Variablen-Substitution `{{name}}` analog ExplorerPro.
