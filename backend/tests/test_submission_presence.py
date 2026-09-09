"""DEMO-03/DEMO-04/DEMO-05/D-07(c)(d): presence tests for submission
artifacts.

Machine-verifies that the repo-root LICENSE, repo-root README.md, and
docs/architecture.md + docs/demo-script.md all exist with the required
shape, so a later edit can't silently drop a submission artifact.

Repo-root resolution: this file lives at backend/tests/, so
Path(__file__).resolve().parents[2] climbs backend/tests/ -> backend/ ->
repo root — ONE MORE .parent than test_single_writer.py's repo_root
(which deliberately lands on backend/, not the true repo root, since that
test only scans backend/-relative directories).

Presence/substring checking only — no ast, no import-graph analysis (that
pattern is specific to test_single_writer.py's need to detect store
imports).
"""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]  # backend/tests -> backend -> repo root


def test_license_file_exists_at_repo_root():
    """DEMO-04/D-07(c): a repo-root LICENSE with valid OSI (MIT) text."""
    license_path = REPO_ROOT / "LICENSE"
    assert license_path.exists(), f"expected LICENSE at repo root: {license_path}"
    text = license_path.read_text()
    assert "MIT License" in text or "Permission is hereby granted" in text, (
        "LICENSE does not contain recognizable MIT license text"
    )


def test_readme_exists_with_required_sections():
    """DEMO-03/D-07(c): a repo-root README.md with Setup/Run/Test sections."""
    readme_path = REPO_ROOT / "README.md"
    assert readme_path.exists(), f"expected README.md at repo root: {readme_path}"
    text_lower = readme_path.read_text().lower()
    for heading in ("setup", "run", "test"):
        assert heading in text_lower, f"README.md is missing a '{heading}' section"


def test_architecture_doc_has_mermaid_block():
    """DEMO-05/D-07(d): docs/architecture.md exists with a mermaid fenced block."""
    arch_path = REPO_ROOT / "docs" / "architecture.md"
    assert arch_path.exists(), f"expected docs/architecture.md: {arch_path}"
    assert "```mermaid" in arch_path.read_text(), (
        "docs/architecture.md is missing a ```mermaid fenced block"
    )


def test_demo_script_doc_exists():
    """DEMO-05/D-07(d): docs/demo-script.md exists."""
    script_path = REPO_ROOT / "docs" / "demo-script.md"
    assert script_path.exists(), f"expected docs/demo-script.md: {script_path}"
