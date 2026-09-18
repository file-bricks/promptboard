"""Contract and metadata regression test suite for PromptBoard (Pfad A fleet standards).

Ensures PEP 621 compliance, hardened CI workflows, multi-host .gitignore guardrails,
German statutory notice under § 521 BGB, security SLA commitments, and documentation parity.
"""
from __future__ import annotations

from pathlib import Path
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore

ROOT = Path(__file__).resolve().parent.parent


def test_pep621_metadata_and_urls():
    """Verify pyproject.toml PEP 621 compliance and canonical URL endpoints."""
    pyproject_file = ROOT / "pyproject.toml"
    assert pyproject_file.is_file(), "pyproject.toml must exist at repo root"

    data = tomllib.loads(pyproject_file.read_text(encoding="utf-8"))
    project = data.get("project", {})

    assert project.get("name") == "promptboard"
    assert project.get("license") == "MIT"
    assert project.get("license-files") == ["LICENSE", "THIRD_PARTY_LICENSES.txt"]
    assert project.get("requires-python") == ">=3.10"
    assert len(project.get("authors", [])) >= 1
    assert "keywords" in project and len(project["keywords"]) >= 5
    assert "classifiers" in project and len(project["classifiers"]) >= 5

    # Check dev dependencies
    dev_deps = project.get("optional-dependencies", {}).get("dev", [])
    assert any("pytest" in dep for dep in dev_deps)
    assert any("ruff" in dep for dep in dev_deps)

    # Check project URLs
    urls = project.get("urls", {})
    required_keys = [
        "Homepage",
        "Documentation",
        "Repository",
        "Issues",
        "Changelog",
        "Security",
        "Third-Party Licenses",
        "Parent Organization",
        "Umbrella Ecosystem",
        "Marketing Log",
        "LLM Ready",
    ]
    for key in required_keys:
        assert key in urls, f"Missing required project.urls entry: {key}"
        assert urls[key].startswith("https://github.com/"), f"URL for {key} must start with https://github.com/"

    # Check pytest configuration
    pytest_cfg = data.get("tool", {}).get("pytest", {}).get("ini_options", {})
    assert pytest_cfg.get("minversion") == "7.0"
    assert "tests" in pytest_cfg.get("testpaths", [])
    assert "norecursedirs" in pytest_cfg
    assert ".git" in pytest_cfg["norecursedirs"]


def test_ci_workflows_concurrency_and_timeouts():
    """Verify all GitHub Actions workflows enforce concurrency and timeouts."""
    workflows_dir = ROOT / ".github" / "workflows"
    assert workflows_dir.is_dir(), ".github/workflows must exist"

    tests_yml = workflows_dir / "tests.yml"
    assert tests_yml.is_file()
    tests_content = tests_yml.read_text(encoding="utf-8")
    assert "concurrency:" in tests_content
    assert "cancel-in-progress: true" in tests_content
    assert "timeout-minutes:" in tests_content
    assert "actions/checkout@v4" in tests_content
    assert "actions/setup-python@v5" in tests_content
    assert "ruff check" in tests_content

    stale_yml = workflows_dir / "stale.yml"
    assert stale_yml.is_file()
    stale_content = stale_yml.read_text(encoding="utf-8")
    assert "concurrency:" in stale_content
    assert "timeout-minutes:" in stale_content
    assert "actions/stale@v9" in stale_content
    assert "issues: write" in stale_content
    assert "pull-requests: write" in stale_content

    welcome_yml = workflows_dir / "welcome.yml"
    assert welcome_yml.is_file()
    welcome_content = welcome_yml.read_text(encoding="utf-8")
    assert "concurrency:" in welcome_content
    assert "timeout-minutes:" in welcome_content
    assert "actions/first-interaction@v3" in welcome_content
    assert "issues: write" in welcome_content
    assert "pull-requests: write" in welcome_content


def test_gitignore_multihost_and_cloud_sync_hardening():
    """Verify .gitignore contains patterns protecting against multi-host conflict files and locks."""
    gitignore_file = ROOT / ".gitignore"
    assert gitignore_file.is_file()
    content = gitignore_file.read_text(encoding="utf-8")

    # Multi-host sync conflict copies
    assert "*conflicted copy*" in content
    assert "*-ASUS-GEI*" in content
    assert "*-WORKSTATION-LG*" in content
    assert "*-Mac Studio*" in content

    # Systemwide locks
    assert "LOCK" in content
    assert "LOCK.*" in content
    assert "LOCK.permissions.json" in content

    # Tool caches & SQLite WAL
    assert "uv.lock" in content
    assert ".ruff_cache/" in content
    assert "*.db-wal" in content


def test_security_policy_sla_and_version_support():
    """Verify SECURITY.md declares version support table, 48h SLA, and architectural invariants."""
    sec_file = ROOT / "SECURITY.md"
    assert sec_file.is_file()
    content = sec_file.read_text(encoding="utf-8")

    assert "## Supported Versions" in content
    assert "1.1.x" in content
    assert "48 Stunden" in content or "48 hours" in content
    assert "[INV-SLA-10]" in content
    assert "[INV-LOCAL-01]" in content
    assert "[INV-PERM-02]" in content
    assert "[INV-MEM-06]" in content
    assert "[INV-RULE-07]" in content


def test_third_party_licenses_audit_and_invariants():
    """Verify THIRD_PARTY_LICENSES.txt contains re-audit readback and invariants."""
    tpl_file = ROOT / "THIRD_PARTY_LICENSES.txt"
    assert tpl_file.is_file()
    content = tpl_file.read_text(encoding="utf-8")

    assert "Checked: 2026-07-02" in content
    assert "Turnus-Audit & Invarianten" in content
    assert "2026-09-18" in content
    assert "[INV-LOCAL-01]" in content
    assert "[INV-PERM-02]" in content
    assert "[INV-MEM-06]" in content
    assert "[INV-RULE-07]" in content
    assert "[INV-SLA-10]" in content
    assert "PySide6" in content
    assert "LGPL" in content


def test_german_readme_statutory_notice_and_umlauts():
    """Verify README_de.md includes statutory notice (§ 521 BGB) and has no UTF-8 mojibake."""
    readme_de = ROOT / "README_de.md"
    assert readme_de.is_file()
    raw = readme_de.read_bytes()

    # Verify no UTF-8 decoding issues
    text = raw.decode("utf-8")
    assert "\ufffd" not in text, "README_de.md contains Unicode replacement character"

    # Verify no typical Mojibake patterns
    mojibake_patterns = ["Ã¤", "Ã¶", "Ã¼", "ÃŸ", "Ã„", "Ã–", "Ãœ"]
    for pattern in mojibake_patterns:
        assert pattern not in text, f"README_de.md contains mojibake sequence: {pattern}"

    # Statutory notice
    assert "§ 521 BGB" in text
    assert "Gefälligkeitsrecht" in text
    assert "vorsatz" in text.lower()
    assert "grobe fahrlässigkeit" in text.lower()


def test_documentation_and_marketing_log_parity():
    """Verify README.md, llms.txt, and MARKETING-LOG.txt are synchronized."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "2026-09-18" in readme
    assert "Architecture & Data Flow" in readme
    assert "Disambiguation:" in readme

    llms = (ROOT / "llms.txt").read_text(encoding="utf-8")
    assert "Last-checked: 2026-09-18" in llms
    assert "Release boundary (readback 2026-09-18):" in llms

    mktg = (ROOT / "MARKETING-LOG.txt").read_text(encoding="utf-8")
    assert "Date: 2026-09-18" in mktg
    assert "Pfad A Hygiene" in mktg

    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "[Unreleased] - 2026-09-18" in changelog
