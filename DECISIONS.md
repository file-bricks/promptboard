# DECISIONS.md - Architektur- und Produktentscheidungen

> Chronologisch, neueste oben. Entscheidungen nicht löschen, sondern durch neue Einträge ersetzen oder revidieren.

---

## 2026-05-10: Markdown-Materialisierung bleibt content-first und trägt nur leichte Metadaten

### Kontext

Die offene Frage war, wie materialisierte `.md`-Dateien aussehen sollen, ohne den eigentlichen Inhalt unter einer Exporthülle zu verstecken.

### Entscheidung

PromptBoard materialisiert standardmäßig ein kurzes Dokument mit:

- verstecktem Herkunftsmarker als HTML-Kommentar
- H1 mit dem Eintragsnamen
- kompaktem sichtbaren Metadatenkopf als Blockquote
- direktem Dokumentkörper ohne zusätzliche `## Inhalt`-Hülle

### Begründung

- Der Export bleibt leichtgewichtig und lesbar.
- Der eigentliche Inhalt steht im Vordergrund und lässt sich direkt weiterverwenden.
- Wichtige Kontextinfos wie Typ, Kategorie, Tags und Zeitstempel gehen nicht verloren.
- Ein versteckter Marker erleichtert spätere Adapter- oder Roundtrip-Pfade.

---

## 2026-05-10: PromptBoard wird als DEV-Projekt im LLM-Bereich geführt

### Kontext

Der Projektordner lag zunächst ohne Lifecycle-Präfix als reine Ideenablage vor.

### Entscheidung

Das Projekt wird unter `LLM/DEV_PromptBoard` geführt und als aktives Entwicklungs- bzw. Konzeptprojekt registriert.

### Begründung

- Die Idee ist relevant und soll aktiv weiterentwickelt werden.
- Ein `DEV`-Präfix macht Status und Einordnung sofort sichtbar.
- Die zentrale Registry bleibt konsistent mit der `.SOFTWARE`-Konvention.

---

## 2026-05-10: PromptBoard wird bewusst als leichtgewichtiges Tray-Tool positioniert

### Kontext

Verwandte Projekte wie ProfiPrompt und AutoPrompter decken bereits schwerere bzw. anders gelagerte Nutzungsmuster ab.

### Entscheidung

PromptBoard fokussiert auf schnellen lokalen Zugriff, Direktbearbeitung, Clipboard und Materialisierung. Große Historien-, Board- oder Automationslogik gehört nicht in den ersten Kern.

### Begründung

- Der Produktwert liegt in Reibungsarmut.
- Eine klare Abgrenzung verhindert Funktionswucher.
- Das Projekt füllt eine echte Lücke zwischen “zu groß” und “zu fragil”.

---

## 2026-05-10: Windows-First und PySide6 für den MVP

### Kontext

Die Idee ist stark desktop- und traybezogen. Das globale Software-Regelwerk bevorzugt zudem PySide6 für neue GUI-Projekte.

### Entscheidung

Der erste MVP wird als Windows-First-Desktop-App mit PySide6 gedacht.

### Begründung

- Systemtray und Desktop-Materialisierung passen direkt zu diesem Zielbild.
- PySide6 ist die bevorzugte GUI-Wahl im Software-Portfolio.
- Ein klarer erster Zielpfad ist besser als vorschnelles Multi-Plattform-Design.

---

## 2026-05-10: Lokale JSON-Speicherung vor Datenbank

### Kontext

Das Projekt startet mit einer kleinen lokalen Bibliothek und noch überschaubarem Datenmodell.

### Entscheidung

Für den MVP wird JSON als primäre Speicherung bevorzugt. Markdown-Dateien sind zunächst Export-/Materialisierungsausgabe, nicht die primäre Datenquelle.

### Begründung

- schneller prototypisierbar
- leicht verständlich
- ausreichend für den frühen Projektstand

---

## 2026-05-10: ProfiPrompt-Kompatibilität soll über einen teilrecycelten JSON-Kern geprüft werden

### Kontext

Nach Sichtung von `REL_ProfiPrompt` zeigt sich: Die dortige Speicherung läuft über `prompts.json`, `boards.json` und `QSettings`, nicht über SQLite.

### Entscheidung

PromptBoard soll prüfen, ob ein Teil dieses Speichermodells direkt recycelt oder kompatibel gespiegelt werden kann, vor allem für Prompt- und Board-nahe Daten.

### Begründung

- Kompatibilität und Migration werden leichter.
- Bereits vorhandene Modelle für Prompt, Version, Board und BoardItem können als Referenz dienen.
- PromptBoard kann trotzdem leicht bleiben, wenn nur ein sinnvoller Teil übernommen wird.

### Grenzen

- PromptBoard übernimmt nicht automatisch die gesamte ProfiPrompt-Komplexität.
- Typen wie `SKILL`, `WORKFLOW`, `ROLLE` und `AGENT` brauchen wahrscheinlich eine Erweiterung über das bestehende ProfiPrompt-Schema hinaus.

### Folge-Aktionen

- [x] Konzept und Onboarding-Dokumente erstellen.
- [ ] Ein konkretes JSON-Schema entwerfen.
- [x] Materialisierungsformat für `.md` spezifizieren.
- [x] Mapping von ProfiPrompt-JSON zu PromptBoard-Library entwerfen und umsetzen.

---

## 2026-05-10: Der erste MVP speichert in `library.json` und importiert ProfiPrompt zunächst read-only

### Kontext

Für einen schnellen ersten Prototypen war wichtig, PromptBoard direkt lauffähig zu machen, ohne die komplette ProfiPrompt-Struktur sofort mitzuschreiben oder mitzupflegen.

### Entscheidung

Der MVP speichert lokal in einer eigenen `library.json`. ProfiPrompt wird zunächst read-only angebunden, konkret über einen Import des zuletzt aktualisierten Prompts aus `prompts.json`.

### Begründung

- Der Prototyp bleibt klein und stabil.
- Kompatibilität wird bereits praktisch getestet.
- Ein späteres engeres Mapping bleibt offen, ohne den ersten MVP zu blockieren.

---

## 2026-05-10: Systemtray, Copy und Materialisierung sind echte MVP-Funktionen

### Kontext

PromptBoard sollte nicht als bloße Speicherdemo enden, sondern die Kernidee eines schnellen Alltagswerkzeugs direkt zeigen.

### Entscheidung

Der erste Prototyp enthält bereits Systemtray, Editor, automatische Speicherung, Copy-to-Clipboard und Markdown-Materialisierung.

### Begründung

- Diese Funktionen bilden den eigentlichen Produktkern ab.
- So lässt sich der Nutzwert früh real testen.
- Architektur und UX-Fragen werden schneller sichtbar als in einer reinen Datenschema-Phase.
