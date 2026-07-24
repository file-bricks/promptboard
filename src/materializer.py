from __future__ import annotations

from pathlib import Path
from typing import Iterable

from models import LibraryItem


def _origin_marker(item: LibraryItem) -> str:
    return (
        f'<!-- promptboard:item id="{item.id}" '
        f'type="{item.item_type.value}" '
        f'updated_at="{item.updated_at}" -->'
    )


def _build_metadata_lines(item: LibraryItem) -> list[str]:
    lines = [f"> Typ: {item.item_type.value}"]
    if item.category:
        lines.append(f"> Kategorie: {item.category}")
    if item.tags:
        lines.append(f"> Tags: {', '.join(item.tags)}")
    if item.source:
        lines.append(f"> Quelle: {item.source}")
    lines.append(f"> Stand: {item.updated_at}")
    if item.created_at and item.created_at != item.updated_at:
        lines.append(f"> Erstellt: {item.created_at}")
    return lines


def build_markdown(item: LibraryItem, *, content: str | None = None) -> str:
    rendered_content = (item.content if content is None else content).rstrip()
    lines = [
        _origin_marker(item),
        "",
        f"# {item.name}",
        "",
        *_build_metadata_lines(item),
        "",
        rendered_content or "_Kein Inhalt vorhanden._",
        "",
    ]
    return "\n".join(lines)


def _build_plaintext_metadata_lines(item: LibraryItem) -> list[str]:
    lines = [f"Typ: {item.item_type.value}"]
    if item.category:
        lines.append(f"Kategorie: {item.category}")
    if item.tags:
        lines.append(f"Tags: {', '.join(item.tags)}")
    if item.source:
        lines.append(f"Quelle: {item.source}")
    lines.append(f"Stand: {item.updated_at}")
    if item.created_at and item.created_at != item.updated_at:
        lines.append(f"Erstellt: {item.created_at}")
    return lines


def build_plaintext(item: LibraryItem, *, content: str | None = None) -> str:
    """Plain-text rendering of an entry (no Markdown syntax)."""
    rendered_content = (item.content if content is None else content).rstrip()
    lines = [
        item.name,
        "",
        *_build_plaintext_metadata_lines(item),
        "",
        rendered_content or "Kein Inhalt vorhanden.",
        "",
    ]
    return "\n".join(lines)


FORMAT_MARKDOWN = "markdown"
FORMAT_TXT = "txt"
_EXTENSIONS = {FORMAT_MARKDOWN: ".md", FORMAT_TXT: ".txt"}
_RENDERERS = {FORMAT_MARKDOWN: build_markdown, FORMAT_TXT: build_plaintext}


def materialize_extension(fmt: str = FORMAT_MARKDOWN) -> str:
    return _EXTENSIONS.get(fmt, _EXTENSIONS[FORMAT_MARKDOWN])


def render_item(item: LibraryItem, fmt: str = FORMAT_MARKDOWN) -> str:
    renderer = _RENDERERS.get(fmt, build_markdown)
    return renderer(item)


def materialize_item(
    item: LibraryItem,
    target_dir: Path,
    fmt: str = FORMAT_MARKDOWN,
) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"{item.filename_stem()}{materialize_extension(fmt)}"
    target_path.write_text(render_item(item, fmt), encoding="utf-8")
    return target_path


def materialize_items(
    items: Iterable[LibraryItem],
    target_dir: Path,
    fmt: str = FORMAT_MARKDOWN,
) -> list[Path]:
    """Materialize several items into the same target directory."""
    return [materialize_item(item, target_dir, fmt) for item in items]
