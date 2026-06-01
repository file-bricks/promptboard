# PromptBoard Flutter Companion

Read-only Android/iOS-Companion für `PromptBoard`. Der Mobile-Strang lädt die
Desktop-Datei `library.json` ohne Cloud-Zwang und zeigt Einträge für schnelle
Unterwegs-Sicht, Suche und Kopierpfade mobil an.

## Aktueller Umfang

- Demo-Daten für schnelle UI-Smokes
- Import aus der Zwischenablage
- Manuelle JSON-Eingabe für `library.json`
- Suche über Name, Inhalt, Tags und Quelle
- Filter nach Eintragstyp
- Detailansicht mit Copy-Button

## Start

```powershell
cd 'C:\Users\User\OneDrive\.TOPICS\.SOFTWARE\LLM\REL-PUB_PromptBoard\flutter_port'
flutter pub get
flutter run
```

## Tests

```powershell
flutter test
```

## Nächste sinnvolle Schritte

- Echten Dateiupload oder Share-Intent für `library.json` ergänzen
- Lokalen Offline-Cache für die zuletzt geladene Bibliothek ergänzen
- Android- und iOS-Smoke mit realer Desktop-Exportdatei dokumentieren

## Grenze

Der Companion bleibt read-only. Er soll `library.json` dateibasiert übernehmen,
aber keine Einträge zurück in die Desktop-Bibliothek schreiben und keine direkte
Server-Synchronisierung einführen.
