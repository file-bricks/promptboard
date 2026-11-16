"""Tab-Reihenfolge des Einstellungsdialogs folgt dem Layout, schreibgeschützte Pfadfelder eingeschlossen.

Screenreader lesen den Pfad nur, wenn das Feld in der Tab-Kette steht. Ein OneDrive-only-Entwurf vom
2026-07-26 hätte die Felder ans Ende hinter „Schließen“ geschoben (2026-11-14 geprüft, nicht übernommen)."""
from __future__ import annotations

from settings_dialog import SettingsDialog
from settings_manager import SettingsManager


def test_settings_dialog_tab_order_follows_the_layout_including_path_fields(qapp, tmp_path):
    settings = SettingsManager()
    settings.qs.setValue("paths/data", str(tmp_path / "library"))
    dialog = SettingsDialog(settings)
    try:
        expected = [
            dialog.materialize_path_edit,
            dialog.change_materialize_button,
            dialog.profiprompt_path_edit,
            dialog.change_profiprompt_button,
            dialog.explorerpro_path_edit,
            dialog.change_explorerpro_button,
            dialog.profiprompt_enabled_check,
            dialog.explorerpro_enabled_check,
            dialog.import_profiprompt_button,
            dialog.import_explorerpro_button,
            dialog.export_explorerpro_button,
            dialog.theme_combo,
            dialog.language_combo,
            dialog.materialize_format_combo,
            dialog.confirm_overwrite_check,
            dialog.close_button,
        ]
        widget = expected[0]
        for nxt in expected[1:]:
            widget = widget.nextInFocusChain()
            while not widget.focusPolicy() or widget.focusProxy() is not None:
                widget = widget.nextInFocusChain()
            assert widget is nxt, (widget.objectName() or type(widget).__name__, nxt.objectName())
    finally:
        dialog.close()
