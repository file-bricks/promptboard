"""Guard the release license inventory against runtime dependency drift."""

import re
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def _requirement_names_from_text(text):
    names = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-r "):
            continue
        base = line.split(";", 1)[0].strip()
        names.append(re.split(r"[<>=!~\[]", base, 1)[0].strip())
    return names


def _runtime_requirement_names():
    names = set(
        _requirement_names_from_text(
            (ROOT / "requirements.txt").read_text(encoding="utf-8")
        )
    )
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    for requirement in pyproject["project"]["dependencies"]:
        names.update(_requirement_names_from_text(requirement))
    return sorted(names)


def test_third_party_license_inventory_covers_runtime_dependencies():
    inventory = (ROOT / "THIRD_PARTY_LICENSES.txt").read_text(encoding="utf-8")

    assert "Checked: 2026-07-02" in inventory
    assert "licensed under MIT according to `LICENSE`" in inventory
    assert "not a frozen transitive SBOM" in inventory

    for package in _runtime_requirement_names():
        assert f"| {package} " in inventory

    for package in ("PySide6_Addons", "PySide6_Essentials", "shiboken6"):
        assert f"| {package} " in inventory
