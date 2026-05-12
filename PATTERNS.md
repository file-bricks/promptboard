# PATTERNS.md - Produkt- und Implementierungsmuster

## Do

- Halte das Kernmodell klein und generisch.
- Trenne Kernlogik von Import-/Export-Adaptern.
- Schreibe lokale Daten atomar.
- Behandle Materialisierung als klaren Service mit eindeutigen Regeln.
- Bevorzuge direkte, schnelle Bearbeitung statt tiefer Dialogketten.

## Don't

- Nicht sofort Versionierung, Teamsync und Cloud als Grundannahme einbauen.
- Keine ExplorerPro-Logik in den Kern mischen.
- Keine Keyboard-Automation oder Makrologik in den MVP ziehen.
- Nicht verschiedene Persistenzmodelle gleichzeitig einführen.

## Beispiel: Sinnvolles Eintragsmodell

```json
{
  "id": "item-001",
  "type": "PROMPT",
  "name": "REVIEW CHECKLIST",
  "content": "Prüfe den Code auf Risiken, Regressionen und fehlende Tests.",
  "category": "Code Review",
  "tags": ["review", "quality"],
  "updated_at": "2026-05-10T06:00:00"
}
```

## Beispiel: Saubere Modulgrenze

- `storage/` kennt das JSON-Format
- `materialization/` kennt Markdown-Ausgabe
- `adapters/explorerpro/` kennt ExplorerPro
- `ui/` kennt Fenster und Tray

So bleibt späterer Umbau möglich, ohne alles gleichzeitig anfassen zu müssen.
