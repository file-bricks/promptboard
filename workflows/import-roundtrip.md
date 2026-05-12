# Import-Roundtrip-Workflow

## Zweck

Geplant wird ein sauberer Austausch mit ExplorerPro und ein begrenzter Import aus einem Fremdmanager, ohne dass PromptBoard davon strukturell abhängig wird.

## Schritte

1. Quellformat benennen.
2. Entscheiden, welche Felder wirklich übernommen werden.
3. Konfliktfälle definieren: gleicher Name, anderer Typ, fehlendes Datum, leere Inhalte.
4. Festlegen, was im MVP nur Import und was später auch Export ist.
5. Das Mapping in [ARCHITECTURE.md](../ARCHITECTURE.md) und [TODO.md](../TODO.md) nachziehen.

## Prüffragen

- Ist der Adapter austauschbar?
- Bleibt PromptBoard auch ohne Fremdtool vollständig nutzbar?
- Wird keine große Sync-Engine aus Versehen in den MVP gezogen?
