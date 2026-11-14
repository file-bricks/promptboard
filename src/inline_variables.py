from __future__ import annotations

import re
from collections.abc import Callable

INLINE_VARIABLE_PATTERN = re.compile(r"\{\{\s*([\w.\-]+)\s*\}\}")

VariableValueProvider = Callable[[str], tuple[str, bool]]


def extract_inline_variables(text: str) -> list[str]:
    seen: set[str] = set()
    variables: list[str] = []
    for match in INLINE_VARIABLE_PATTERN.finditer(text):
        name = match.group(1).strip()
        if name and name not in seen:
            seen.add(name)
            variables.append(name)
    return variables


def resolve_inline_variables(
    text: str,
    value_provider: VariableValueProvider,
) -> str | None:
    variables = extract_inline_variables(text)
    if not variables:
        return text

    values: dict[str, str] = {}
    for name in variables:
        value, accepted = value_provider(name)
        if not accepted:
            return None
        values[name] = value

    def _replace(match: re.Match[str]) -> str:
        name = match.group(1).strip()
        return values.get(name, match.group(0))

    return INLINE_VARIABLE_PATTERN.sub(_replace, text)

