# PromptBoard Flutter Companion - Porting Status

## Status 2026-06-02: gestrichen

Die Android-/iOS-Linie wird nicht weitergeführt. Der vorhandene Flutter-MVP war
ein brauchbarer read-only Prototyp für `library.json`, bildet aber keinen
ausreichend starken eigenständigen Endnutzer-Usecase.

## Begründung

- Mobile Nutzung wäre nur ein kleiner Ausschnitt der Desktop-App.
- Der Kernnutzen von PromptBoard liegt in Tray, Hotkeys, Clipboard,
  Dateisystem-Workflows und Markdown-Materialisierung.
- Für Teams ist Web/PWA mit Server-Synchronisierung interessanter, aber das ist
  eine eigene Applinie, kein Mobile-Companion.

## Umgang mit dem Ordner

`flutter_port/` bleibt vorerst als technischer Prototyp und historische Notiz im
Repo. Keine neuen Android-/iOS-Aufgaben aus diesem Ordner ableiten. Später kann
der Ordner entfernt oder in ein Archiv verschoben werden.
