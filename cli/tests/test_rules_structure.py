"""Rules core/JIT split — structure + always-on budget (PR 13, plan §15)."""

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RULES = REPO / ".maika" / "rules"

CORE = ("flow.md", "evidence.md", "write-boundary.md", "verification.md")
JIT = ("providers.md", "knowledge-lifecycle.md", "skill-evolution.md", "teaching-moment.md")


def test_rules_tree_is_core_plus_jit_only():
    top = sorted(p.name for p in RULES.iterdir())
    assert top == ["RULES.md", "core", "jit"]
    assert sorted(p.name for p in (RULES / "core").glob("*.md")) == sorted(CORE)
    assert sorted(p.name for p in (RULES / "jit").glob("*.md")) == sorted(JIT)


def test_core_always_on_budget_under_250_lines():
    total = sum(
        len((RULES / "core" / name).read_text(encoding="utf-8").splitlines())
        for name in CORE
    )
    assert total < 250, f"core rules must stay under 250 lines (found {total})"


def test_manifest_declares_jit_load_matrix():
    manifest = (RULES / "RULES.md").read_text(encoding="utf-8")
    assert "JIT — load theo điều kiện" in manifest
    for name in JIT:
        assert f"rules/jit/{name}" in manifest, name
    for name in CORE:
        assert f"rules/core/{name}" in manifest, name


def test_no_stale_flat_rule_references():
    """Old flat rule filenames must be gone from agent-facing content."""
    stale = ("rules-flow.md", "rules-tool.md", "rules-exec.md", "rules-knowledge.md",
             "rules-skill-evolution.md", "rules-guard.md")
    scan_dirs = ("rules", "procedures", "workflows", "skills", "agent", "config")
    offenders = []
    for rel in scan_dirs:
        root = REPO / ".maika" / rel
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.suffix not in (".md", ".yaml"):
                continue
            text = path.read_text(encoding="utf-8")
            for token in stale:
                if token in text:
                    offenders.append(f"{path}:{token}")
    assert offenders == [], offenders
