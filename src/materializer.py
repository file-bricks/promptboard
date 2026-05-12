from __future__ import annotations

from pathlib import Path

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


def build_markdown(item: LibraryItem) -> str:
    content = item.content.rstrip()
    lines = [
        _origin_marker(item),
        "",
        f"# {item.name}",
        "",
        *_build_metadata_lines(item),
        "",
        content or "_Kein Inhalt vorhanden._",
        "",
    ]
    return "\n".join(lines)


def materialize_item(
    item: LibraryItem,
    target_dir: Path,
) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"{item.filename_stem()}.md"
    target_path.write_text(build_markdown(item), encoding="utf-8")
    return target_path
