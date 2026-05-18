# Beitragsrichtlinie / Contributing Guide

## Deutsch

Vielen Dank für Ihr Interesse, zu diesem Projekt beizutragen.

### Wie Sie beitragen können

1. **Bug melden:** Erstellen Sie ein Issue mit dem Label `bug`
2. **Feature vorschlagen:** Erstellen Sie ein Issue mit dem Label `enhancement`
3. **Code beitragen:** Erstellen Sie einen Pull Request

### Pull Requests

1. Forken Sie das Repository
2. Erstellen Sie einen Feature-Branch: `git checkout -b feature/mein-feature`
3. Committen Sie Ihre Änderungen: `git commit -m "Beschreibung der Änderung"`
4. Pushen Sie den Branch: `git push origin feature/mein-feature`
5. Erstellen Sie einen Pull Request

### Projekt-Setup

```powershell
pip install -r requirements.txt
python -m pytest -q
python src\promptboard.py
```

Für Windows-Releases nutzt das Projekt zusätzlich `build.bat`.

### Code-Richtlinien

- Python: PEP 8 Stil
- Encoding: UTF-8 für alle Dateien
- Sprache: Code und Kommentare auf Deutsch oder Englisch
- Keine hardcoded Pfade oder API-Keys
- Leichtgewichtig bleiben: keine unnötige Cloud-, Daemon- oder Heavy-Workflow-Logik in den Kern ziehen

### Lizenz- und Rechtehinweise

Falls dieses Projekt ein CLA, DCO oder eine andere Beitragsvereinbarung nutzt,
ist dies im Repository gesondert dokumentiert. Ohne ausdrückliche Zusatzregel
gelten Pull Requests unter der Lizenz des Projekts.

---

## English

Thank you for your interest in contributing to this project.

### How to Contribute

1. **Report bugs:** Create an issue with the `bug` label
2. **Suggest features:** Create an issue with the `enhancement` label
3. **Contribute code:** Create a Pull Request

### Pull Requests

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -m "Description of change"`
4. Push the branch: `git push origin feature/my-feature`
5. Create a Pull Request

### Project Setup

```powershell
pip install -r requirements.txt
python -m pytest -q
python src\promptboard.py
```

Use `build.bat` for local Windows release builds.

### Code Guidelines

- Python: PEP 8 style
- Encoding: UTF-8 for all files
- Language: Code and comments in German or English
- No hardcoded paths or API keys
- Keep the core lightweight; avoid unnecessary cloud, daemon, or heavy workflow logic

### Licensing and Contribution Terms

If this project uses a CLA, DCO, or any other contribution agreement, it
should be documented separately in the repository. Unless stated otherwise,
pull requests are understood to be submitted under the project's license.
