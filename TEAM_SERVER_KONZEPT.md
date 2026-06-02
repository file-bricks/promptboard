# TEAM_SERVER_KONZEPT - PromptBase Team Server

Stand: 2026-06-02

## Kurzentscheidung

Web/PWA und direkte Server-Synchronisierung sind für PromptBoard nicht als
kleiner Companion sinnvoll, können aber eine eigene Applinie rechtfertigen:
eine gemeinsame Promptbase für Teams.

Arbeitstitel: **PromptBase Team Server**

## Zweck

Teams sollen Prompts, Skills, Rollen, Workflows und Agenten-Bausteine gemeinsam
pflegen, versionieren, freigeben und über Browser/API nutzen können. Das ist ein
kollaborativer Server-Usecase, nicht der lokale Tray-Usecase von PromptBoard.

## Abgrenzung zu PromptBoard Desktop

| PromptBoard Desktop | PromptBase Team Server |
|---|---|
| Einzelnutzer | Teams und Arbeitsgruppen |
| Tray, Hotkeys, Clipboard | Browser/PWA, API, Rechte |
| lokale `library.json` | serverseitige Datenbank |
| offline-first | synchronisiert und kollaborativ |
| Markdown-Materialisierung | Versionierung, Review, Freigabe |
| Windows Store/GitHub | Self-hosting, Intranet oder Team-Cloud |

## Kernusecases

- Team teilt eine kuratierte Prompt-/Skill-Bibliothek
- Promptänderungen brauchen Review und Freigabe
- Rollen und Agentenbausteine sollen organisationsweit konsistent bleiben
- Browserzugriff ist wichtiger als Tray-Hotkeys
- Agenten oder Automationen greifen über API auf freigegebene Bausteine zu
- Desktop-Nutzer importieren/exportieren über `library.json`

## Erste Architekturidee

- Web/PWA-Frontend für Suche, Editieren, Review und Kopieren
- Server-API für Bibliothek, Auth, Rollen/Rechte und Versionen
- Datenbank statt lokaler Einzeldatei
- Import/Export-Brücke zu PromptBoard `library.json`
- optionaler Desktop-Client später nur als Sync-/Tray-Ergänzung, nicht als Kern

## Noch nicht entscheiden

- eigenes Repository oder Unterprojekt in PromptBoard
- Open Source, Open Core oder private Team-Version
- Self-hosting-only oder gehosteter Dienst
- Datenbank: SQLite für kleine Teams oder Postgres für Mehrnutzerbetrieb
- Auth: lokale Nutzer, OAuth/OIDC oder einfache Team-Tokens

## Nächster sinnvoller Schritt

Vor Implementierung erst ein kleines Produktkonzept erstellen:

- Nutzergruppen und Mindest-Usecases
- Datenmodell für Prompts, Rollen, Versionen und Freigaben
- Rechte- und Review-Modell
- Import/Export zu `library.json`
- Entscheidung: neues Projekt in `.SOFTWARE/LLM/` oder Subordner unter
  PromptBoard
