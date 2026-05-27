# PromptBoard Flutter Companion - Porting Status

## Stand 2026-05-27

Die vorhandene Android-/iOS-Linie war bislang nur ein leeres Flutter-Scaffold.
Jetzt existiert ein erster nutzbarer Mobile-MVP:

- read-only Viewer für PromptBoard-`library.json`
- Laden per Demo, Zwischenablage oder manueller JSON-Eingabe
- mobile Suche und Typfilter
- Detailansicht mit Copy-Flow

## Bewusste Grenzen des aktuellen Schritts

- kein Schreibzugriff zurück in die Desktop-Bibliothek
- noch kein echter Datei-Picker oder Share-Intent
- noch kein lokaler Persistenz-Cache

## Nächste Aufgaben

- reale `library.json` über Datei oder Share-Intent importieren
- Android- und iOS-Smoke mit echter Exportdatei dokumentieren
- später optional Offline-Cache für zuletzt geladene Bibliothek ergänzen
