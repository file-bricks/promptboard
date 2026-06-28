# EXPORTFORMAT - PromptBoard `library.json`

Stand: 2026-06-19

## Zweck

`library.json` ist das lokale Bibliotheksformat von PromptBoard und das
dateibasierte Austauschformat für Backups, Tool-Importe und eine mögliche
spätere Team-Server-Linie. Es transportiert Prompts, Skills, Workflows, Rollen
und Agenten ohne Cloud-Zwang.

## Datei

Standardpfad in der Desktop-App:

```text
~/.promptboard/library.json
```

Die Desktop-App legt diesen Ordner über `SettingsManager.get_data_path()` an
und speichert die Bibliothek darin als `library.json`. Ältere Integrationen
können noch `%APPDATA%/PromptBoard/library.json` verwenden; dieser Pfad gilt
nur noch als Legacy-Fallback für lesende Adapter. BACH liest zuerst eine
explizite `BACH_PROMPTBOARD_LIBRARY`, dann den Desktop-Standardpfad und danach
den AppData-Fallback.

Das Format ist eine Datei-Brücke, kein Live-Sync-Protokoll. Eine mögliche
Web-/Server-Linie darf `library.json` importieren oder exportieren, sollte aber
für Team-Rechte, Versionen, Freigaben und Synchronisierung ein eigenes
serverseitiges Datenmodell nutzen.

## Struktur

```json
{
  "items": [
    {
      "id": "b8d2c0e1f2a34b5c9d0e112233445566",
      "item_type": "PROMPT",
      "name": "KURZER REVIEW-PROMPT",
      "content": "Prüfe den folgenden Text auf Klarheit...",
      "category": "Review",
      "tags": ["Review", "Deutsch"],
      "source": "PromptBoard",
      "created_at": "2026-06-02T08:00:00+00:00",
      "updated_at": "2026-06-02T08:10:00+00:00"
    }
  ]
}
```

## Felder

| Feld | Typ | Pflicht | Bedeutung |
|---|---|---:|---|
| `items` | Array | ja | Liste der Bibliothekseinträge |
| `id` | String | ja | stabile Eintrags-ID |
| `item_type` | String | ja | `PROMPT`, `SKILL`, `WORKFLOW`, `ROLLE` oder `AGENT` |
| `name` | String | ja | Anzeigename; Desktop normalisiert auf Großschreibung |
| `content` | String | ja | eigentlicher Bausteintext |
| `category` | String | nein | freie Kategorie |
| `tags` | Array[String] | nein | freie Schlagworte |
| `source` | String | nein | Herkunft, z. B. `PromptBoard`, `ProfiPrompt`, `ExplorerPro` |
| `created_at` | ISO-8601 String | nein | Erstellzeitpunkt |
| `updated_at` | ISO-8601 String | nein | letzter Änderungszeitpunkt |

## Kompatibilitätsregeln

- Unbekannte `item_type`-Werte werden in der Desktop-App defensiv als `PROMPT`
  behandelt.
- Fehlende optionale Felder werden mit leeren Werten oder aktuellem Zeitstempel
  ergänzt.
- Die Datei wird UTF-8 ohne BOM geschrieben.
- Inhalte bleiben unverändert; Inline-Variablen wie `{{name}}` werden erst im
  Copy-Flow aufgelöst.
- Der Companion darf für read-only Anzeige unbekannte Felder ignorieren.

## Server-/Team-Grenze

`library.json` kann eine Team-Promptbase initial befüllen oder einzelne
Bibliotheken aus ihr exportieren. Es soll aber keine direkte Mehrnutzer-
Synchronisierung abbilden. Für kollaborative Nutzung braucht eine separate
Server-Linie zusätzliche Objekte wie Nutzer, Rollen, Rechte, Versionen,
Review-Status und Änderungsverlauf.

## Datenschutzgrenze

Das Format enthält bewusst nur Bibliothekseinträge. Es soll keine Logs, lokalen
Fensterzustände, Store-Metadaten, Hotkey-Konfigurationen, absoluten
Materialisierungspfade oder Systeminformationen exportieren.
