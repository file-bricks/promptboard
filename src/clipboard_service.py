from __future__ import annotations

from collections.abc import Callable

from PySide6 import QtWidgets

from i18n import tr
from inline_variables import resolve_inline_variables
from materializer import build_markdown
from models import LibraryItem


class ClipboardService:
    def __init__(
        self,
        app: QtWidgets.QApplication,
        prompt_for_variable: Callable[[str], tuple[str, bool]] | None = None,
    ):
        self.app = app
        self.prompt_for_variable = prompt_for_variable or self._prompt_for_variable

    def _copy_text(self, text: str) -> None:
        clipboard = self.app.clipboard()
        clipboard.setText(text)

    def _prompt_for_variable(self, name: str) -> tuple[str, bool]:
        parent = self.app.activeWindow() if self.app is not None else None
        return QtWidgets.QInputDialog.getText(
            parent,
            tr("dialog.inline_variable.title", name=name),
            tr("dialog.inline_variable.body", name=name),
        )

    def _resolve_content(self, item: LibraryItem) -> str | None:
        return resolve_inline_variables(item.content, self.prompt_for_variable)

    def copy_item(self, item: LibraryItem) -> bool:
        resolved_content = self._resolve_content(item)
        if resolved_content is None:
            return False
        self._copy_text(resolved_content)
        return True

    def copy_item_markdown(self, item: LibraryItem) -> bool:
        resolved_content = self._resolve_content(item)
        if resolved_content is None:
            return False
        self._copy_text(build_markdown(item, content=resolved_content))
        return True
