from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from item_templates import build_default_name, get_item_template
from models import ItemType


def test_item_templates_support_english_role_defaults():
    template = get_item_template(ItemType.ROLLE, language="en")

    assert build_default_name(ItemType.ROLLE, 3, language="en") == "NEW ROLE 3"
    assert template.source == "local"
    assert template.content.startswith("Role:")
    assert "Tone:" in template.content
