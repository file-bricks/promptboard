from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

# QT_SCALE_FACTOR MUSS vor QApplication-Erzeugung gesetzt werden (Qt6!)
os.environ.setdefault("QT_SCALE_FACTOR", "2")
# Offscreen-Fallback für CI / kopflosen Betrieb; wird ggf. durch vorhandenen
# Display überschrieben, wenn gesetzt – daher nur setdefault.
# Nicht erzwingen, damit echtes Rendering auf dem Desktop möglich bleibt.

from PySide6 import QtCore, QtGui, QtWidgets

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from models import ItemType, LibraryItem
from promptboard import MainWindow, create_tray
from settings_dialog import SettingsDialog
from settings_manager import SettingsManager
from storage import Storage
from theme import apply_theme


SCREENSHOT_NAMES = {
    "tray": "tray.png",
    "library": "library.png",
    "editor": "editor.png",
    "settings": "settings.png",
}

THEME = "dark"


def apply_screenshot_font(app: QtWidgets.QApplication) -> None:
    families = {family.casefold(): family for family in QtGui.QFontDatabase.families()}
    for preferred in ("Segoe UI", "Arial", "Noto Sans", "Liberation Sans", "Sans Serif"):
        family = families.get(preferred.casefold())
        if family:
            app.setFont(QtGui.QFont(family, 10))
            return


def configure_qsettings(base_dir: Path) -> None:
    settings_root = base_dir / "qsettings"
    QtCore.QSettings.setDefaultFormat(QtCore.QSettings.IniFormat)
    QtCore.QSettings.setPath(
        QtCore.QSettings.IniFormat,
        QtCore.QSettings.UserScope,
        str(settings_root),
    )
    QtCore.QSettings.setPath(
        QtCore.QSettings.IniFormat,
        QtCore.QSettings.SystemScope,
        str(settings_root),
    )


def build_demo_items() -> list[LibraryItem]:
    return [
        LibraryItem(
            id="store-prompt",
            item_type=ItemType.PROMPT,
            name="Projektstart Übersicht",
            category="Workflow",
            tags=["Start", "Checkliste", "Fokus"],
            source="lokal",
            content=(
                "Zweck:\n"
                "- Projektziel klären\n"
                "- Risiken benennen\n"
                "- nächste Schritte mit echtem Nutzen priorisieren\n\n"
                "Ausgabe:\n"
                "1. Kurzüberblick\n"
                "2. offene Fragen\n"
                "3. konkrete To-dos"
            ),
        ),
        LibraryItem(
            id="store-skill",
            item_type=ItemType.SKILL,
            name="Umlaut-Qualitätscheck",
            category="Qualität",
            tags=["Deutsch", "Umlaute"],
            source="lokal",
            content=(
                "Prüfe deutsche Endnutzertexte auf ä, ö, ü und ß.\n"
                "Korrigiere beschädigte Schreibweisen wie ae/oe/ue nur dann,\n"
                "wenn sie nicht absichtlich technisch motiviert sind."
            ),
        ),
        LibraryItem(
            id="store-agent",
            item_type=ItemType.AGENT,
            name="Release Coach",
            category="Release",
            tags=["Store", "Windows", "QA"],
            source="lokal",
            content=(
                "Zweck:\n"
                "- Release-Artefakte prüfen\n"
                "- Screenshots und Store-Texte abgleichen\n\n"
                "Werkzeuge:\n"
                "- pytest\n"
                "- PyInstaller\n"
                "- Windows Store Pipeline"
            ),
        ),
    ]


def _process_events(app: QtWidgets.QApplication) -> None:
    app.processEvents()
    QtCore.QTimer.singleShot(0, lambda: None)
    app.processEvents()


def _save_widget(widget: QtWidgets.QWidget, target: Path) -> None:
    widget.show()
    widget.raise_()
    widget.activateWindow()
    _process_events(QtWidgets.QApplication.instance())
    pixmap = widget.grab()
    if pixmap.isNull():
        raise RuntimeError(f"Screenshot für {target.name} konnte nicht erzeugt werden")
    # Pixel-Dimensionen ausgeben – beweist, ob 2x-DPI griff
    print(f"  {target.name}: {pixmap.width()}×{pixmap.height()} px (physikalisch)")
    target.parent.mkdir(parents=True, exist_ok=True)
    if not pixmap.save(str(target)):
        raise RuntimeError(f"Screenshot {target} konnte nicht gespeichert werden")


def _render_tray_menu(tray: QtWidgets.QSystemTrayIcon, target: Path) -> None:
    menu = tray.contextMenu()
    if menu is None:
        raise RuntimeError("Tray-Menü fehlt")
    menu.ensurePolished()
    menu.adjustSize()
    _save_widget(menu, target)
    menu.hide()


def _build_tray_preview_menu(window: MainWindow) -> QtWidgets.QMenu:
    menu = QtWidgets.QMenu()
    menu.addAction(tr("tray.open"), window.showNormal)
    menu.addAction(tr("tray.hide"), window.hide)
    menu.addSeparator()
    app = QtWidgets.QApplication.instance()
    if app is not None:
        menu.addAction(tr("tray.quit"), app.quit)
    return menu


def _render_tray_preview(
    window: MainWindow,
    tray: QtWidgets.QSystemTrayIcon | None,
    target: Path,
) -> None:
    if tray is not None:
        _render_tray_menu(tray, target)
        return
    menu = _build_tray_preview_menu(window)
    menu.ensurePolished()
    menu.adjustSize()
    _save_widget(menu, target)
    menu.hide()


def _build_settings_dialog(window: MainWindow) -> SettingsDialog:
    dialog = SettingsDialog(
        window.settings,
        parent=window,
        on_import_profiprompt=lambda: None,
        on_import_explorerpro=lambda: None,
        on_export_explorerpro=lambda: None,
    )
    dialog.theme_combo.setCurrentIndex(
        max(dialog.theme_combo.findData(THEME), 0)
    )
    dialog.language_combo.setCurrentIndex(
        max(dialog.language_combo.findData("de"), 0)
    )
    return dialog


def generate_store_screenshots(output_dir: Path) -> list[Path]:
    """Erzeugt die vier Store-Screenshots (tray, library, editor, settings)."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="promptboard-store-shots-") as temp_dir:
        temp_root = Path(temp_dir)
        configure_qsettings(temp_root)

        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        app.setApplicationName("PromptBoard Screenshot Generator")
        apply_screenshot_font(app)
        apply_theme(app, THEME)

        settings = SettingsManager()
        data_dir = temp_root / "data"
        materialize_dir = temp_root / "exports"
        profiprompt_dir = temp_root / "profiprompt"
        explorerpro_dir = temp_root / "explorerpro"
        settings.qs.setValue("paths/data", str(data_dir))
        settings.qs.setValue("paths/materialize", str(materialize_dir))
        settings.qs.setValue("imports/profiprompt_data", str(profiprompt_dir))
        settings.qs.setValue("imports/explorerpro_data", str(explorerpro_dir))
        settings.qs.setValue("view/language", "de")
        settings.qs.setValue("view/theme", THEME)
        settings.qs.sync()

        storage = Storage(data_dir)
        storage.upsert_many(build_demo_items())

        window = MainWindow(storage, settings)
        window.resize(1480, 920)
        tray = create_tray(window)

        targets = [
            output_dir / SCREENSHOT_NAMES["tray"],
            output_dir / SCREENSHOT_NAMES["library"],
            output_dir / SCREENSHOT_NAMES["editor"],
            output_dir / SCREENSHOT_NAMES["settings"],
        ]

        try:
            _render_tray_preview(window, tray, targets[0])

            # library.png: Liste + Detail beide befüllt (store-skill ausgewählt)
            window.type_filter.setCurrentText(tr("filter.all"))
            window.search_edit.setText("")
            window.reload_list()
            window._select_item_by_id("store-skill")
            window.status_label.setText("Bibliothek mit lokalen Prompt-Bausteinen")
            _save_widget(window, targets[1])

            # editor.png: anderer Eintrag als main.png (store-agent)
            window._select_item_by_id("store-agent")
            window.status_label.setText("Editor mit ausgewähltem Agenten-Eintrag")
            _save_widget(window, targets[2])

            dialog = _build_settings_dialog(window)
            _save_widget(dialog, targets[3])
            dialog.close()
        finally:
            if tray is not None:
                tray.hide()
                tray.deleteLater()
            window.close()
            _process_events(app)

    return targets


def generate_main_screenshot(main_path: Path) -> Path:
    """Erzeugt das Hero-Bild README/screenshots/main.png im dark-Theme.

    Zeigt das Haupt-Fenster mit dem inhaltlich reichsten Eintrag (store-prompt)
    ausgewählt – bewusst ein anderes Element als editor.png (store-agent).
    """
    main_path = Path(main_path)
    main_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="promptboard-main-shot-") as temp_dir:
        temp_root = Path(temp_dir)
        configure_qsettings(temp_root)

        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        app.setApplicationName("PromptBoard Screenshot Generator")
        apply_screenshot_font(app)
        apply_theme(app, THEME)

        settings = SettingsManager()
        data_dir = temp_root / "data"
        materialize_dir = temp_root / "exports"
        profiprompt_dir = temp_root / "profiprompt"
        explorerpro_dir = temp_root / "explorerpro"
        settings.qs.setValue("paths/data", str(data_dir))
        settings.qs.setValue("paths/materialize", str(materialize_dir))
        settings.qs.setValue("imports/profiprompt_data", str(profiprompt_dir))
        settings.qs.setValue("imports/explorerpro_data", str(explorerpro_dir))
        settings.qs.setValue("view/language", "de")
        settings.qs.setValue("view/theme", THEME)
        settings.qs.sync()

        storage = Storage(data_dir)
        storage.upsert_many(build_demo_items())

        window = MainWindow(storage, settings)
        window.resize(1480, 920)
        tray = create_tray(window)

        try:
            window.type_filter.setCurrentText(tr("filter.all"))
            window.search_edit.setText("")
            window.reload_list()
            # Hero-Eintrag: store-prompt (inhaltreich, klar strukturiert)
            window._select_item_by_id("store-prompt")
            window.status_label.setText("PromptBoard – lokale Prompt-Bausteine verwalten")
            _save_widget(window, main_path)
        finally:
            if tray is not None:
                tray.hide()
                tray.deleteLater()
            window.close()
            _process_events(app)

    return main_path


def tr(key: str) -> str:
    from i18n import set_language, tr as translate

    set_language("de")
    return translate(key)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Erzeugt reproduzierbare Store-Screenshots für PromptBoard."
    )
    parser.add_argument(
        "--output",
        default=str(PROJECT_ROOT / "README" / "screenshots" / "store"),
        help="Zielordner für tray.png, library.png, editor.png und settings.png",
    )
    parser.add_argument(
        "--main",
        default=str(PROJECT_ROOT / "README" / "screenshots" / "main.png"),
        help="Pfad für das Hero-Bild main.png",
    )
    parser.add_argument(
        "--no-main",
        action="store_true",
        help="main.png NICHT erzeugen (nur Store-Screenshots)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    print("=== Store-Screenshots ===")
    targets = generate_store_screenshots(Path(args.output))
    for target in targets:
        size = target.stat().st_size if target.exists() else 0
        print(f"  → {target}  ({size // 1024} KB)")

    if not args.no_main:
        print("=== Hero-Bild (main.png) ===")
        main_path = generate_main_screenshot(Path(args.main))
        size = main_path.stat().st_size if main_path.exists() else 0
        print(f"  → {main_path}  ({size // 1024} KB)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
