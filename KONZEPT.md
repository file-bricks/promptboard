# KONZEPT.md - Produktidee und Weiterdenken

## Kurzidee

PromptBoard ist eine kleine Desktop-Anwendung im Systemtray für wiederverwendbare LLM-Bausteine. Das Tool soll eine lokale Bibliothek aus Prompts, Skills, Workflows, Rollen und Agenten verwalten, ohne die Komplexität eines vollwertigen Prompt-Managers mitzuschleppen.

## Problem

Viele Prompt- und Workflow-Bausteine liegen verstreut in Projekten, Archiven, Prompt-Managern oder Dokumentordnern. Für den Alltag fehlt oft ein kleines Werkzeug, das diese Bausteine schnell sichtbar und sofort nutzbar macht:

- ohne große Projektverwaltung
- ohne tiefe Board-Komplexität
- ohne fragile Automatisierung
- ohne Cloud-Zwang

## Zielgruppe

- Einzelanwender mit vielen LLM-Arbeitsbausteinen
- Entwickler und Wissensarbeiter mit wiederkehrenden Prompts
- Nutzer, die Skills, Rollen und Workflows schnell materialisieren oder kopieren wollen
- Nutzer bestehender Tools wie ProfiPrompt oder ExplorerPro, die eine leichtere Oberfläche brauchen

## Kernobjekte

PromptBoard verwaltet Einträge eines gemeinsamen Grundtyps mit folgenden Arten:

- `PROMPT`
- `SKILL`
- `WORKFLOW`
- `ROLLE`
- `AGENT`

Jeder Eintrag besitzt mindestens:

- Typ
- Name
- Inhalt
- Änderungsdatum
- optionale Kategorie
- optionale Tags
- optionale Herkunft

## Kernfunktionen

### 1. Tray-zentrierter Zugriff

- Anwendung läuft im Systemtray
- Board-Fenster öffnet sich schnell aus dem Tray
- Fokus auf einen schnellen Alltagszugriff statt schwerer Vollanwendung

### 2. Sortieren und Filtern

Einträge sollen mindestens sortierbar und filterbar sein nach:

- Art
- Name
- Änderungsdatum

Zusätzlich ist eine Filterung nach Kategorie sinnvoll.

### 3. Direktes Bearbeiten

- Einträge sind direkt editierbar
- Änderungen werden automatisch gespeichert
- Keine unnötigen Dialogketten im MVP

### 4. Copy-to-Clipboard

- Ein Klick kopiert den Eintrag in die Zwischenablage
- Später denkbar: unterschiedliche Copy-Modi
- Im MVP reicht zunächst der Volltext

### 5. Materialisierung als Markdown-Datei

Per Rechtsklick kann ein Eintrag als `.md`-Datei materialisiert werden:

- Standardziel: Desktop
- Zielpfad später in den Einstellungen änderbar
- bestehende Zieldateien werden standardmäßig überschrieben
- die Bestätigung ist im Standard unterdrückt
- der Dateiname basiert auf dem Namen in Großschreibung
- das Dokument bleibt inhaltszentriert: versteckter Herkunftsmarker, Titel, kompakter Metadatenkopf, dann der eigentliche Inhalt

### 6. Import / Austausch

Geplante Import- und Austauschpfade:

- Import aus einem bestehenden Prompt-Manager, zunächst nur der aktuellste Prompt
- Import aus `DATA/REL-PUB_ExplorerPro_SUITE`
- später auch Rückexport oder Austauschformat für ExplorerPro

## Kompatibilität zu ProfiPrompt

Bei einer kurzen technischen Prüfung zeigt sich: ProfiPrompt nutzt aktuell keine relationale Datenbank, sondern lokale JSON-Dateien wie `prompts.json` und `boards.json` plus `QSettings` für Pfade und Einstellungen.

Das ist für PromptBoard interessant, weil ein Teil dieser Struktur recycelt werden kann:

- Prompt-Metadaten
- Versionen
- Boards bzw. Sammlungen
- lokaler Speicherpfad

Sinnvoll erscheint daher kein völliger Neubau auf inkompatibler Datenbasis, sondern eine Teilkompatibilität:

- PromptBoard soll ProfiPrompt-Prompts lesen können
- ein reduzierter kompatibler Kern ist wünschenswert
- PromptBoard-spezifische Typen wie `SKILL`, `WORKFLOW`, `ROLLE` und `AGENT` brauchen wahrscheinlich eigene Erweiterungen

Damit bleibt Migration möglich, ohne dass PromptBoard die gesamte Logik von ProfiPrompt übernehmen muss.

## Produktabgrenzung

### Was PromptBoard bewusst nicht im MVP sein soll

- kein großer Prompt-Historien-Manager
- keine komplexe Multi-Board-Logik als Kern
- keine Cloud-Synchronisation
- keine LLM-API-Integration als Pflicht
- kein Daemon zur automatischen Session-Erzeugung
- kein Marktplatz, keine Freigabeplattform, kein Team-Backend

### Verhältnis zu verwandten Projekten

- **ProfiPrompt:** schwerer, historien- und boardorientierter Prompt-Manager
- **AutoPrompter:** stärker auf Prompt-Erzeugung und Automatisierung ausgerichtet, aber archiviert
- **PromptBoard:** schneller Alltagszugriff und Materialisierung im Vordergrund

## MVP-Vorschlag

### MVP 0.1

- Windows-First Desktop-App
- PySide6 mit `QSystemTrayIcon`
- lokale JSON-Speicherung
- direkter Editor
- Sortierung nach Typ, Name, Änderungsdatum
- Volltextsuche
- Copy-to-Clipboard
- Materialisierung als Markdown-Datei
- ein einfacher Importpfad

### MVP 0.2

- ExplorerPro-Import
- ExplorerPro-Rückexport
- Kategorien und bessere Filter
- konfigurierbarer Materialisierungspfad

### Später

- Hotkeys
- Mehrfachauswahl
- Batch-Materialisierung
- Validierung von Item-Namen
- Vorlagen für Eintragstypen

## UX-Richtung

PromptBoard sollte sich nicht wie ein schweres Admin-Tool anfühlen, sondern wie ein schnelles Arbeitsbrett:

- kleine Oberfläche
- flacher Klickpfad
- schnelle Sicht auf viele Einträge
- Bearbeiten ohne Modal-Overkill
- klare, funktionale Typkennzeichnung

## Technische Leitidee

Die App sollte lokal-first und robust sein:

- PySide6 statt PyQt
- möglichst wenige Laufzeitabhängigkeiten
- atomare Dateischreibvorgänge
- Adapter-Grenze zu ExplorerPro und anderen Tools
- kein harter Zwang zu SQLite im MVP

## Offene Produktfragen

- Reicht eine gemeinsame Eintragsliste oder braucht es mehrere Boards?
- Braucht die Materialisierung später zusätzlich einen zuschaltbaren erweiterten Metadatenmodus?
- Wie genau sieht der ExplorerPro-Austausch aus?
- Wie wird der „aktuellste Prompt“ aus ProfiPrompt oder einem Prompt-Manager bestimmt?
- Wird später ein globaler Hotkey nötig?

## Fazit

PromptBoard ist am stärksten, wenn es bewusst klein bleibt: ein lokales Tray-Werkzeug für schnelle Wiederverwendung und Materialisierung von LLM-Bausteinen. Der größte Produktwert liegt nicht in maximaler Funktionstiefe, sondern in Reibungsarmut.
