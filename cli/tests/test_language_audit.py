"""W7 language audit: Maika-owned runtime human-readable content must be Vietnamese.

Technical identifiers (capability IDs, artifact filenames, schema keys, CLI
commands, enums, MCP tool names) stay English by contract and are not prose, so
the check targets section headings and prose, not identifiers."""
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / ".maika" / "skills"
RULES = ROOT / ".maika" / "rules"
AUDIT = ROOT / "docs" / "refactor" / "maika-vnext" / "language-audit.yaml"

VALID_STATUS = {
    "pending", "translated", "kept_as_technical_identifier",
    "excluded_generated_vendor", "verified",
}

_VIET = re.compile(
    r"[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]",
    re.IGNORECASE,
)

# Old English skill/rule contract headings — presence signals a regression to English.
DISALLOWED_HEADINGS = [
    "## Purpose", "## Triggers", "## Inputs", "## Required outcomes",
    "## Evidence requirements", "## Process", "## Stop conditions",
    "## Output contract", "## Next handoff",
]


def _runtime_files():
    files = sorted(SKILLS.glob("*/SKILL.md"))
    files += [RULES / n for n in ("core/evidence.md", "jit/providers.md", "core/verification.md")]
    files += [ROOT / ".maika" / "workflows" / "task.md"]
    return [f for f in files if f.exists()]


def test_language_audit_schema():
    audit = yaml.safe_load(AUDIT.read_text(encoding="utf-8"))
    assert audit["version"] == 1
    entries = audit["entries"]
    assert entries, "language audit must list entries"
    for e in entries:
        for key in ("path", "category", "current_language", "action", "status", "reason"):
            assert e.get(key), f"audit entry missing {key}: {e}"
        assert e["status"] in VALID_STATUS, f"bad status: {e['status']}"


def test_verified_entries_are_vietnamese():
    audit = yaml.safe_load(AUDIT.read_text(encoding="utf-8"))
    for e in audit["entries"]:
        if e["status"] in {"verified", "translated"}:
            assert e["current_language"] == "vi", f"verified but not vi: {e['path']}"


def test_runtime_surface_is_localized():
    offenders = {}
    for f in _runtime_files():
        text = f.read_text(encoding="utf-8")
        problems = [h for h in DISALLOWED_HEADINGS if h in text]
        if not _VIET.search(text):
            problems.append("no Vietnamese prose found")
        if problems:
            offenders[str(f.relative_to(ROOT))] = problems
    assert not offenders, f"non-localized runtime files: {offenders}"
