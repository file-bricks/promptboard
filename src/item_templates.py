from __future__ import annotations

from dataclasses import dataclass

from i18n import DEFAULT_LANGUAGE, VALID_LANGUAGES, LanguageCode, get_language
from models import ItemType, normalize_name


@dataclass(frozen=True)
class ItemTemplate:
    name_base: str
    content: str
    source: str


_TEMPLATES: dict[ItemType, dict[LanguageCode, ItemTemplate]] = {
    ItemType.PROMPT: {
        "de": ItemTemplate(
            name_base="Neuer Prompt",
            content="Ziel:\nKontext:\nAufgabe:\nAusgabeformat:\nGrenzen:\n",
            source="lokal",
        ),
        "en": ItemTemplate(
            name_base="New Prompt",
            content="Goal:\nContext:\nTask:\nOutput format:\nConstraints:\n",
            source="local",
        ),
    },
    ItemType.SKILL: {
        "de": ItemTemplate(
            name_base="Neuer Skill",
            content="Zweck:\nAuslöser:\nEingaben:\nSchritte:\nErgebnis:\n",
            source="lokal",
        ),
        "en": ItemTemplate(
            name_base="New Skill",
            content="Purpose:\nTrigger:\nInputs:\nSteps:\nResult:\n",
            source="local",
        ),
    },
    ItemType.WORKFLOW: {
        "de": ItemTemplate(
            name_base="Neuer Workflow",
            content="Ziel:\nAuslöser:\nVoraussetzungen:\nSchritte:\nAbschluss:\n",
            source="lokal",
        ),
        "en": ItemTemplate(
            name_base="New Workflow",
            content="Goal:\nTrigger:\nPrerequisites:\nSteps:\nFinish:\n",
            source="local",
        ),
    },
    ItemType.ROLLE: {
        "de": ItemTemplate(
            name_base="Neue Rolle",
            content="Rolle:\nAufgabe:\nTon:\nWissen:\nGrenzen:\n",
            source="lokal",
        ),
        "en": ItemTemplate(
            name_base="New Role",
            content="Role:\nTask:\nTone:\nKnowledge:\nConstraints:\n",
            source="local",
        ),
    },
    ItemType.AGENT: {
        "de": ItemTemplate(
            name_base="Neuer Agent",
            content="Zweck:\nWerkzeuge:\nEingaben:\nAblauf:\nErgebnis:\n",
            source="lokal",
        ),
        "en": ItemTemplate(
            name_base="New Agent",
            content="Purpose:\nTools:\nInputs:\nFlow:\nResult:\n",
            source="local",
        ),
    },
}


def _resolve_language(language: str | None = None) -> LanguageCode:
    if language in VALID_LANGUAGES:
        return language
    current = get_language()
    if current in VALID_LANGUAGES:
        return current
    return DEFAULT_LANGUAGE


def get_item_template(item_type: ItemType, language: str | None = None) -> ItemTemplate:
    resolved_type = ItemType.from_value(item_type)
    resolved_language = _resolve_language(language)
    return _TEMPLATES[resolved_type][resolved_language]


def build_default_name(
    item_type: ItemType, sequence_number: int, language: str | None = None
) -> str:
    template = get_item_template(item_type, language=language)
    return normalize_name(f"{template.name_base} {sequence_number}")
