from __future__ import annotations

import re
from collections.abc import Callable

INLINE_VARIABLE_PATTERN = re.compile(r"\{\{(\w+)\}\}")

VariableValueProvider = Callable[[str], tuple[str, bool]]


def extract_inline_variables(text: str) -> list[str]:
    seen: set[str] = set()
    variables: list[str] = []
    for name in INLINE_VARIABLE_PATTERN.findall(text):
        if name in seen:
            continue
        seen.add(name)
        variables.append(name)
    return variables


def resolve_inline_variables(
    text: str,
    value_provider: VariableValueProvider,
) -> str | None:
    resolved = text
    for name in extract_inline_variables(text):
        value, accepted = value_provider(name)
        if not accepted:
            return None
        resolved = resolved.replace(f"{{{{{name}}}}}", value)
    return resolved
