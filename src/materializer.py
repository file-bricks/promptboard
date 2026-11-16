from __future__ import annotations

from pathlib import Path
from typing import Iterable

from models import LibraryItem
from storage import atomic_write_text


def _escape_marker_attr(value: object) -> str:
    raw = "" if value is None else str(value)
    cleaned = raw.replace("\r", " ").replace("\n", " ")
    cleaned = (
        cleaned.replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "&#45;&#45;")
    return cleaned


def _origin_marker(item: LibraryItem) -> str:
    return (
        f'<!-- promptboard:item id="{_escape_marker_attr(item.id)}" '
        f'type="{_escape_marker_attr(item.item_type.value)}" '
        f'updated_at="{_escape_marker_attr(item.updated_at)}" -->'
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


def resolve_batch_targets(
    items: Iterable[LibraryItem],
    target_dir: Path,
    fmt: str = FORMAT_MARKDOWN,
) -> list[tuple[LibraryItem, Path]]:
    """Resolve target file paths for a batch, disambiguating intra-batch stem collisions."""
    target_dir = Path(target_dir)
    ext = materialize_extension(fmt)
    used_keys: set[str] = set()
    resolved: list[tuple[LibraryItem, Path]] = []

    for item in items:
        stem = item.filename_stem()
        candidate_name = f"{stem}{ext}"
        if candidate_name.casefold() in used_keys:
            idx = 2
            while True:
                suffix = f" ({idx})"
                max_base = max(1, 120 - len(suffix))
                trimmed_stem = stem[:max_base].rstrip(". ") or stem[:max_base]
                candidate_name = f"{trimmed_stem}{suffix}{ext}"
                if candidate_name.casefold() not in used_keys:
                    break
                idx += 1
        used_keys.add(candidate_name.casefold())
        resolved.append((item, target_dir / candidate_name))

    return resolved


def materialize_item(
    item: LibraryItem,
    target_dir: Path,
    fmt: str = FORMAT_MARKDOWN,
) -> Path:
    target_dir = Path(target_dir)
    target_path = target_dir / f"{item.filename_stem()}{materialize_extension(fmt)}"
    atomic_write_text(target_path, render_item(item, fmt), encoding="utf-8")
    return target_path


def materialize_items(
    items: Iterable[LibraryItem],
    target_dir: Path,
    fmt: str = FORMAT_MARKDOWN,
) -> list[Path]:
    """Materialize several items into the same target directory without intra-batch clobbering."""
    pairs = resolve_batch_targets(items, target_dir, fmt)
    written: list[Path] = []
    for item, target_path in pairs:
        atomic_write_text(target_path, render_item(item, fmt), encoding="utf-8")
        written.append(target_path)
    return written
