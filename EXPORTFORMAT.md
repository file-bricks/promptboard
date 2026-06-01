# EXPORTFORMAT - PromptBoard `library.json`

Stand: 2026-06-02

## Zweck

`library.json` ist das lokale Bibliotheksformat von PromptBoard und zugleich das
dateibasierte Austauschformat für den Android-/iOS-Companion. Es transportiert
Prompts, Skills, Workflows, Rollen und Agenten ohne Cloud-Zwang.

## Datei

Standardpfad in der Desktop-App:

```text
%APPDATA%/PromptBoard/library.json
```

Der Companion soll diese Datei über Dateiauswahl, Share-Intent, Zwischenablage
oder manuelle JSON-Eingabe lesen können. Schreibzugriff vom Companion zurück in
die Desktop-Bibliothek ist vorerst kein Ziel.

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

## Datenschutzgrenze

Das Format enthält bewusst nur Bibliothekseinträge. Es soll keine Logs, lokalen
Fensterzustände, Store-Metadaten, Hotkey-Konfigurationen, absoluten
Materialisierungspfade oder Systeminformationen exportieren.
