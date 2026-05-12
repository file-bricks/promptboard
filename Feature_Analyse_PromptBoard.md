# Feature-Analyse: PromptBoard

## Kurzbeschreibung

PromptBoard ist ein geplantes leichtgewichtiges Systemtray-Tool zur lokalen Verwaltung und schnellen Wiederverwendung von Prompts, Skills, Workflows, Rollen und Agenten.

---

## Highlights

| Feature | Beschreibung |
|---|---|
| **Tray-Zugriff** | Das Tool lebt im Systemtray und ist mit wenig Reibung erreichbar. |
| **Schnelles Kopieren** | Einträge können mit einem Klick in die Zwischenablage kopiert werden. |
| **Materialisierung** | Einträge lassen sich als `.md`-Datei an einen Zielpfad exportieren. |
| **Direktbearbeitung** | Inhalte sollen ohne schwere Dialogkaskaden editierbar sein. |
| **Leichtgewichtiges Modell** | Fokus auf schnellen Zugriff statt auf große Historien- oder Board-Komplexität. |
| **ExplorerPro-Brücke** | Späterer Import und Austausch mit ExplorerPro ist vorgesehen. |

---

## Bewertung der Ausbaustufe

### Aktueller Stand: **Konzept / Prototype-Vorphase (15%)**

| Kategorie | Bewertung (1-5) | Details |
|---|:---:|---|
| **Funktionsumfang** | 2 | Kernidee ist klar, MVP-Schnitt noch nicht final. |
| **UI/UX** | 2 | Tray-orientierte UX ist greifbar, aber noch nicht konkret skizziert. |
| **Stabilität** | 1 | Noch kein Code vorhanden. |
| **Dokumentation** | 3 | Idee und Onboarding vorhanden, Spezifikation wird aufgebaut. |
| **Integration** | 2 | ExplorerPro- und Prompt-Manager-Import sind als Richtung definiert, aber noch unscharf. |

---

## Empfohlene Erweiterungen

### Priorität: Hoch

1. MVP-Schnitt definieren: Was ist Version 0.1 und was nicht?
2. Datenmodell für Eintragstypen festlegen.
3. Materialisierungsverhalten präzise spezifizieren.
4. Importpfad für einen ersten Fremd-Adapter konkret definieren.

### Priorität: Mittel

1. UI-Skizze für Tray, Liste, Editor und Vorschau erstellen.
2. Speicherformat festlegen: JSON only oder JSON plus Markdown-Spiegel.
3. Such-, Filter- und Sortierlogik spezifizieren.

### Priorität: Niedrig

1. Globale Hotkeys prüfen.
2. Mehrfachauswahl und Batch-Materialisierung erwägen.
3. Tags und Vorlagen erst nach stabilem MVP ausbauen.

---

## Technische Details

Framework: empfohlen PySide6  
Dateigröße: kein Quellcode vorhanden  
Hauptdatei: keine  
Primärdokument: [KONZEPT.md](./KONZEPT.md)

---

## Code-Qualitätsprüfung

Noch nicht anwendbar, weil kein Code vorliegt. Für den ersten Prototypen sollten direkt geprüft werden:

- UTF-8-Encoding
- Tray-Verhalten auf Windows
- atomare Speicherung
- überschreibende Materialisierung
- Adapter-Grenzen zu ExplorerPro / Fremdformaten

---

*Analyse erstellt: 2026-05-10*
