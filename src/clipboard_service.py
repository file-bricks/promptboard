from __future__ import annotations

from PySide6 import QtGui

from models import LibraryItem


class ClipboardService:
    def __init__(self, app):
        self.app = app

    def copy_item(self, item: LibraryItem) -> None:
        clipboard = self.app.clipboard()
        clipboard.setText(item.content)
