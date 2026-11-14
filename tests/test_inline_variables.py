import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from inline_variables import extract_inline_variables, resolve_inline_variables


def test_extract_inline_variables_with_spaces_hyphens_dots():
    text = "Hallo {{ user-name }} aus {{city.name}}. Test {{ e-mail }} und {{user-name}}."
    vars_found = extract_inline_variables(text)
    assert vars_found == ["user-name", "city.name", "e-mail"]


def test_resolve_inline_variables_with_spaces_hyphens_dots():
    text = "Hallo {{ user-name }} aus {{city.name}}. Mail: {{ e-mail }}."
    values = {
        "user-name": "Ada Lovelace",
        "city.name": "London",
        "e-mail": "ada@example.org",
    }

    def provider(name: str):
        return values[name], True

    result = resolve_inline_variables(text, provider)
    assert result == "Hallo Ada Lovelace aus London. Mail: ada@example.org."


def test_resolve_inline_variables_single_pass_no_reentry():
    text = "Code: {{var1}} & {{var2}}"
    values = {
        "var1": "{{var2}}",
        "var2": "FINAL",
    }

    def provider(name: str):
        return values[name], True

    result = resolve_inline_variables(text, provider)
    assert result == "Code: {{var2}} & FINAL"
