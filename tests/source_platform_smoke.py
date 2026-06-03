from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_ROOT))

from PySide6 import QtCore, QtWidgets

from i18n import set_language as set_global_language
from models import ItemType, LibraryItem
from promptboard import MainWindow, PromptBoardHotkeys, create_tray
from settings_manager import SettingsManager
from storage import Storage
from theme import apply_theme


class SmokeFailure(RuntimeError):
    pass


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeFailure(message)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="promptboard-platform-smoke-") as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        qsettings_root = tmpdir / "qsettings"
        data_dir = tmpdir / "library"
        export_dir = tmpdir / "Export Ärger"

        QtCore.QSettings.setDefaultFormat(QtCore.QSettings.IniFormat)
        QtCore.QSettings.setPath(
            QtCore.QSettings.IniFormat,
            QtCore.QSettings.UserScope,
            str(qsettings_root),
        )
        QtCore.QSettings.setPath(
            QtCore.QSettings.IniFormat,
            QtCore.QSettings.SystemScope,
            str(qsettings_root / "system"),
        )

        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        app.setApplicationName("PromptBoard")

        settings = SettingsManager()
        settings.qs.setValue("paths/data", str(data_dir))
        settings.set_materialize_path(export_dir)
        settings.set_language("de")
        settings.set_theme("system")
        settings.qs.sync()

        set_global_language(settings.get_language())
        apply_theme(app, settings.get_theme())

        storage = Storage(settings.get_data_path())
        storage.upsert_item(
            LibraryItem(
                id="smoke-äöü",
                item_type=ItemType.PROMPT,
                name="Ärztliche Übersicht",
                content="Überprüfung für Ölwechsel\nNächster Schritt: Rücksprache.",
                source="lokal",
                category="Prüfung",
                tags=["ärzte", "öko"],
            )
        )

        window = MainWindow(storage, settings)
        hotkeys = PromptBoardHotkeys(
            on_toggle_visibility=window.toggle_visibility_from_hotkey,
            on_quick_copy=window.quick_copy_last_used_item,
        )
        tray = None
        try:
            tray = create_tray(window)
            hotkeys.start(app)
            window.hotkeys = hotkeys
            window.show()
            app.processEvents()

            _assert(window.windowTitle() == "PromptBoard", "Fenstertitel weicht ab.")
            _assert(window.item_list.count() == 1, "Smoke-Bibliothek enthält nicht genau einen Eintrag.")

            window.item_list.setCurrentRow(0)
            app.processEvents()
            _assert(
                window.item_list.item(0).text() == "PROMPT | ÄRZTLICHE ÜBERSICHT",
                "Eintragsname wurde nicht wie erwartet geladen.",
            )
            editor_text = window.content_edit.toPlainText()
            _assert("Überprüfung" in editor_text and "Ölwechsel" in editor_text, "Editorinhalt enthält die erwarteten Umlaute nicht.")

            if sys.platform != "win32":
                _assert(not hotkeys.supported, "Hotkeys sollten auf Nicht-Windows-Plattformen deaktiviert sein.")
                _assert(not hotkeys.registered, "Nicht-Windows-Hotkeys dürfen nicht als registriert gelten.")

            if tray is None:
                _assert(
                    not QtWidgets.QSystemTrayIcon.isSystemTrayAvailable(),
                    "Tray-Fallback wurde ausgelöst, obwohl ein System-Tray gemeldet wird.",
                )
            else:
                _assert(tray.toolTip() == "PromptBoard", "Tray-Tooltip stimmt nicht.")

            window.materialize_current_item()
            app.processEvents()

            materialized = export_dir / "ÄRZTLICHE ÜBERSICHT.md"
            _assert(materialized.exists(), "Materialisierte Markdown-Datei fehlt.")
            markdown = materialized.read_text(encoding="utf-8")
            _assert("Überprüfung für Ölwechsel" in markdown, "Materialisierte Datei enthält den Editorinhalt nicht.")
            _assert("Prüfung" in markdown, "Materialisierte Datei enthält die Kategorie nicht.")
        finally:
            hotkeys.stop()
            if tray is not None:
                tray.hide()
            window.close()
            app.processEvents()

    print("source_platform_smoke: OK")


if __name__ == "__main__":
    main()
