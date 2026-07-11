"""Structural golden snapshots for platform scaffold output."""

from pathlib import Path

import pytest

from cli.commands.init import run_init


PLATFORM_OPTIONS = {
    "antigravity": {
        "mcps": ["codebase-memory-mcp", "confluence", "db-remote"],
        "language": "python",
    },
    "codex": {
        "mcps": ["codebase-memory-mcp", "confluence", "db-remote"],
        "language": "python",
    },
    "claude-code": {
        "mcps": ["codebase-memory-mcp", "confluence", "db-remote"],
        "language": "python",
    },
    "generic": {
        "mcps": [],
        "language": "other",
    },
}


def _snapshot_tree(root: Path) -> str:
    entries = []
    for path in sorted(root.rglob("*"), key=lambda p: p.relative_to(root).parts):
        rel = path.relative_to(root).as_posix()
        if "__pycache__" in rel:
            continue
        suffix = "/" if path.is_dir() else ""
        entries.append(f"{rel}{suffix}")
    return "\n".join(entries) + "\n"


def test_snapshot_tree_sort_is_case_sensitive_and_posix(tmp_path):
    root = tmp_path / "proj"
    (root / ".agents" / "knowledge" / "templates").mkdir(parents=True)
    (root / ".agents" / "hooks").mkdir()
    (root / ".agents" / "MCP_SETUP.md").write_text("", encoding="utf-8")
    (root / ".agents" / "hooks.json").write_text("", encoding="utf-8")
    (root / ".agents" / "knowledge" / "templates" / "AGENT.tpl.md").write_text("", encoding="utf-8")
    (root / ".agents" / "knowledge" / "templates" / "feature.tpl.md").write_text("", encoding="utf-8")

    lines = _snapshot_tree(root).splitlines()

    assert lines.index(".agents/MCP_SETUP.md") < lines.index(".agents/knowledge/")
    assert lines.index(".agents/hooks/") < lines.index(".agents/hooks.json")
    assert lines.index(".agents/knowledge/templates/AGENT.tpl.md") < lines.index(
        ".agents/knowledge/templates/feature.tpl.md"
    )


@pytest.mark.parametrize("platform_key", sorted(PLATFORM_OPTIONS))
def test_platform_scaffold_tree_matches_snapshot(tmp_path, maika_root, platform_key):
    target = tmp_path / "proj"
    options = PLATFORM_OPTIONS[platform_key]

    run_init(
        target_dir=str(target),
        maika_root=str(maika_root),
        platform_key=platform_key,
        selected_mcps=options["mcps"],
        language=options["language"],
        assume_yes=True,
    )

    actual = _snapshot_tree(target)
    snapshot_path = Path(__file__).resolve().parent / "snapshots" / f"{platform_key}.txt"
    expected = snapshot_path.read_text(encoding="utf-8") if snapshot_path.exists() else ""
    import os
    if os.environ.get("UPDATE_SNAPSHOTS") == "1":
        snapshot_path.write_text(actual, encoding="utf-8")
        expected = actual
    assert actual == expected
    if platform_key in {"antigravity", "codex"}:
        assert "AGENTS.md" in actual
        assert ".maika/resolved-config.yaml" in actual
    elif platform_key == "claude-code":
        assert "CLAUDE.md" in actual
        assert ".maika/resolved-config.yaml" in actual
    elif platform_key == "generic":
        assert "AGENTS.md" in actual
        assert ".maika/resolved-config.yaml" in actual
        assert ".agents/resolved-config.yaml" not in actual
        assert ".claude/resolved-config.yaml" not in actual
