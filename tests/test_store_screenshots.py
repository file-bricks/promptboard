from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
TOOLS_DIR = PROJECT_ROOT / "_tools"
for entry in (str(SRC_DIR), str(TOOLS_DIR)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

from generate_store_screenshots import SCREENSHOT_NAMES, generate_store_screenshots


def test_generate_store_screenshots_writes_all_targets(tmp_path):
    targets = generate_store_screenshots(tmp_path)

    assert {target.name for target in targets} == set(SCREENSHOT_NAMES.values())
    for target in targets:
        assert target.exists()
        assert target.stat().st_size > 0
