# Sicherheitsrichtlinie / Security Policy

## Supported Versions / Unterstützte Versionen

| Version | Supported / Unterstützt | Status |
|---|---|---|
| `1.1.x` | :white_check_mark: Yes / Ja | Aktive Wartungs- und Sicherheitslinie / Current release line |
| `1.0.x` | :x: No / Nein | Veraltet; bitte aktualisieren / Superseded; please upgrade |

## Response Commitment & SLA / Reaktionszeit & SLA

- **Initial Acknowledgment / Erstantwort**: Innerhalb von **48 Stunden** (`[INV-SLA-10]`).
- **Triage & Reproduction**: Innerhalb von 5 Werktagen.
- **Remediation & Patch**: Kritische Sicherheitsprobleme werden priorisiert und im Rahmen eines koordinierten Patches bereitgestellt.

## Security Architecture & Invariants / Sicherheitsarchitektur

PromptBoard folgt strikten lokalen Sicherheits- und Isolationsgrenzen:
- **`[INV-LOCAL-01]` Zero Egress**: 100 % lokaler Offline-Betrieb. Keine Cloud-Sockets, keine Telemetrie, kein Tracking und keine unautorisierten Netzwerkverbindungen.
- **`[INV-PERM-02]` Unprivilegierte Ausführung (`RunAsInvoker`)**: Die Anwendung läuft vollständig unter Standard-Nutzerrechten. Es sind weder Administrator- noch Kernel-Rechte erforderlich.
- **`[INV-MEM-06]` Sicherer Speicher- und Zwischenablagezugriff**: Zwischenablagedaten verbleiben volatil im Speicher und werden niemals unverschlüsselt persistent abgelegt.
- **`[INV-RULE-07]` Mutex-basierte Einzelinstanz (`SingleInstance`)**: Verhindert parallele Instanzkonflikte und Schreibkollisionen auf die lokale JSON-Bibliothek.

---

## Deutsch

### Sicherheitslücken melden

Wenn Sie eine Sicherheitslücke finden, melden Sie diese bitte verantwortungsvoll:

1. **Kein öffentliches Issue eröffnen**
2. **GitHub Private Vulnerability Reporting verwenden**
3. Beschreibung, Reproduktionsschritte und potenzielle Auswirkungen angeben

### So melden Sie ein Problem

1. Öffnen Sie im Repository: `Security` → `Advisories` → `New`
2. Tragen Sie Titel, Beschreibung, Schweregrad und betroffene Versionen ein
3. Reichen Sie die Meldung privat ein

Falls Private Vulnerability Reporting im Repository noch nicht aktiviert ist,
kontaktieren Sie die Maintainer direkt über GitHub oder via `security@file-bricks.org` bzw. `security@open-bricks.org` und veröffentlichen Sie
keine Details in einem öffentlichen Issue.

### Geltungsbereich

- Lokale JSON-Speicherung und Dateischreibvorgänge (`~/.promptboard/library.json`)
- Markdown-Materialisierung und Exportpfade
- Import-/Export-Adapter für Fremdformate und Zwischenablage-Flows

---

## English

### Reporting a Vulnerability

If you find a security vulnerability, please report it responsibly:

1. **Do not open a public issue**
2. **Use GitHub Private Vulnerability Reporting**
3. Include a description, reproduction steps, and potential impact

### How to Report

1. Open: `Security` → `Advisories` → `New`
2. Fill in the title, description, severity, and affected versions
3. Submit the report privately

If private vulnerability reporting is not enabled yet, contact the maintainers
through GitHub or via `security@file-bricks.org` / `security@open-bricks.org` and do not publish details in a public issue.

### Scope

- Local JSON storage and file writes (`~/.promptboard/library.json`)
- Markdown materialization and export paths
- Import/export adapters and clipboard-related flows
