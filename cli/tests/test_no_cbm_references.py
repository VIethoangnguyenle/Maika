"""Locks the CBM removal: no live source may reference codebase-memory again.

Docs archives, the removal/uninstall documentation, and the doctor
contamination detector (which must name the marker to detect it) are the
only allowed mentions."""

import re
import subprocess
from pathlib import Path

ALLOWED_PREFIXES = (
    "docs/",
    "upgrade/",
    "README.md",
    "cli/mcp/doctor.py",
    "cli/tests/test_mcp_doctor.py",
    "cli/tests/test_no_cbm_references.py",
    # Negative-assertion / legacy-migration tests that need the literal string:
    "cli/tests/test_manifest_setup.py",
    "cli/tests/test_provider_capabilities.py",
    "cli/tests/test_update.py",
)
PATTERN = re.compile(r"codebase[-_]memory")


def test_no_codebase_memory_references():
    root = Path(__file__).resolve().parents[2]
    files = subprocess.run(
        ["git", "ls-files"], cwd=root, capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    offenders = []
    for rel in files:
        if rel.startswith(ALLOWED_PREFIXES):
            continue
        try:
            text = (root / rel).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if PATTERN.search(text):
            offenders.append(rel)
    assert not offenders, f"codebase-memory references remain: {offenders}"
