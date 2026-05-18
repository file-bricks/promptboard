import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from clipboard_service import ClipboardService
from models import ItemType, LibraryItem


class _FakeClipboard:
    def __init__(self) -> None:
        self.text = ""

    def setText(self, text: str) -> None:  # noqa: N802 - Qt-style API
        self.text = text


class _FakeApp:
    def __init__(self) -> None:
        self._clipboard = _FakeClipboard()

    def clipboard(self) -> _FakeClipboard:
        return self._clipboard


def test_copy_item_copies_plain_content():
    app = _FakeApp()
    service = ClipboardService(app)
    item = LibraryItem(
        id="item-plain",
        item_type=ItemType.PROMPT,
        name="Plain",
        content="Nur Inhalt",
    )

    assert service.copy_item(item) is True

    assert app.clipboard().text == "Nur Inhalt"


def test_copy_item_replaces_inline_variables_before_copy():
    app = _FakeApp()
    asked: list[str] = []

    def prompt_for_variable(name: str) -> tuple[str, bool]:
        asked.append(name)
        values = {
            "name": "Ada",
            "city": "Bernau",
        }
        return values[name], True

    service = ClipboardService(app, prompt_for_variable=prompt_for_variable)
    item = LibraryItem(
        id="item-inline",
        item_type=ItemType.PROMPT,
        name="Inline",
        content="Hallo {{name}} aus {{city}}. {{name}} testet PromptBoard.",
    )

    assert service.copy_item(item) is True

    assert asked == ["name", "city"]
    assert app.clipboard().text == "Hallo Ada aus Bernau. Ada testet PromptBoard."


def test_copy_item_returns_false_when_inline_variable_prompt_is_cancelled():
    app = _FakeApp()

    service = ClipboardService(
        app,
        prompt_for_variable=lambda _name: ("", False),
    )
    item = LibraryItem(
        id="item-cancelled",
        item_type=ItemType.PROMPT,
        name="Abbruch",
        content="Hallo {{name}}",
    )

    assert service.copy_item(item) is False
    assert app.clipboard().text == ""


def test_copy_item_markdown_copies_rendered_markdown():
    app = _FakeApp()
    service = ClipboardService(
        app,
        prompt_for_variable=lambda name: ({"step": "Setup"}[name], True),
    )
    item = LibraryItem(
        id="item-markdown",
        item_type=ItemType.SKILL,
        name="Markdown",
        content="### {{step}}",
        category="Abläufe",
        tags=["eins", "zwei"],
        source="lokal",
    )

    assert service.copy_item_markdown(item) is True

    clipboard_text = app.clipboard().text
    assert clipboard_text.startswith(
        '<!-- promptboard:item id="item-markdown" type="SKILL"'
    )
    assert "> Typ: SKILL" in clipboard_text
    assert "> Kategorie: Abläufe" in clipboard_text
    assert "### Setup" in clipboard_text
    assert "{{step}}" not in clipboard_text
