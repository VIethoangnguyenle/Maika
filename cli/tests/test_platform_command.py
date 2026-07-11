"""Behavior tests for `maika platform` multi-host enable/disable/primary.

Core `.maika` renders once (at init); enabling another host installs only its
entrypoint + native config and never touches project knowledge.
"""

import hashlib
from pathlib import Path

from cli.commands.init import run_init
from cli.commands.platform import run_platform
from cli.config import project

REPO_ROOT = Path(__file__).resolve().parents[2]


def _init(target: Path, platform_key: str):
    run_init(target_dir=str(target), maika_root=str(REPO_ROOT),
             platform_key=platform_key, selected_mcps=[], language="python",
             assume_yes=True)


def _enable(target: Path, platform_key: str):
    run_platform(action="enable", target_dir=str(target), platform_key=platform_key,
                 maika_root=str(REPO_ROOT))


def _knowledge_hash(target: Path) -> dict:
    root = target / ".maika" / "knowledge"
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*")) if p.is_file()
    }


def test_init_writes_canonical_config(tmp_path):
    _init(tmp_path, "codex")
    cfg = project.load(tmp_path)
    assert cfg["platforms"]["enabled"] == ["codex"]
    assert cfg["platforms"]["primary"] == "codex"


def test_enable_second_host_installs_only_its_adapter(tmp_path):
    _init(tmp_path, "codex")
    _enable(tmp_path, "claude-code")

    assert (tmp_path / "AGENTS.md").exists()          # codex entrypoint
    assert (tmp_path / ".codex" / "hooks.json").exists()
    assert (tmp_path / "CLAUDE.md").exists()          # claude entrypoint
    assert (tmp_path / ".claude" / "settings.json").exists()
    assert set(project.load(tmp_path)["platforms"]["enabled"]) == {"codex", "claude-code"}


def test_enable_either_order_reaches_same_state(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    _init(a, "codex"); _enable(a, "claude-code")
    _init(b, "claude-code"); _enable(b, "codex")

    for target in (a, b):
        assert (target / "AGENTS.md").exists()
        assert (target / "CLAUDE.md").exists()
        assert (target / ".codex" / "hooks.json").exists()
        assert (target / ".claude" / "settings.json").exists()
        assert set(project.load(target)["platforms"]["enabled"]) == {"codex", "claude-code"}


def test_two_enables_are_idempotent(tmp_path):
    _init(tmp_path, "codex")
    _enable(tmp_path, "claude-code")
    _enable(tmp_path, "claude-code")
    body = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    assert body.count("<!-- maika:begin -->") == 1
    assert project.load(tmp_path)["platforms"]["enabled"] == ["codex", "claude-code"]


def test_primary_switch_preserves_knowledge(tmp_path):
    _init(tmp_path, "codex")
    _enable(tmp_path, "claude-code")
    before = _knowledge_hash(tmp_path)
    run_platform(action="primary", target_dir=str(tmp_path), platform_key="claude-code",
                 maika_root=str(REPO_ROOT))
    assert project.load(tmp_path)["platforms"]["primary"] == "claude-code"
    assert _knowledge_hash(tmp_path) == before


def test_disable_removes_only_that_adapter(tmp_path):
    _init(tmp_path, "codex")
    _enable(tmp_path, "claude-code")
    run_platform(action="disable", target_dir=str(tmp_path), platform_key="claude-code",
                 maika_root=str(REPO_ROOT))

    # claude adapter gone, codex + core intact
    assert "write_gate" not in (tmp_path / ".claude" / "settings.json").read_text(encoding="utf-8")
    assert (tmp_path / ".codex" / "hooks.json").exists()
    assert (tmp_path / ".maika" / "rules" / "RULES.md").exists()
    assert project.load(tmp_path)["platforms"]["enabled"] == ["codex"]


def test_disable_preserves_shared_entrypoint_block(tmp_path):
    _init(tmp_path, "codex")            # AGENTS.md
    _enable(tmp_path, "antigravity")    # also AGENTS.md + .agents/hooks.json
    run_platform(action="disable", target_dir=str(tmp_path), platform_key="antigravity",
                 maika_root=str(REPO_ROOT))

    # antigravity native config's maika entry gone...
    assert "write_gate" not in (tmp_path / ".agents" / "hooks.json").read_text(encoding="utf-8")
    # ...but AGENTS.md block stays (codex still needs it).
    assert "<!-- maika:begin -->" in (tmp_path / "AGENTS.md").read_text(encoding="utf-8")


def test_knowledge_hash_unchanged_through_all_ops(tmp_path):
    _init(tmp_path, "codex")
    before = _knowledge_hash(tmp_path)
    _enable(tmp_path, "claude-code")
    _enable(tmp_path, "antigravity")
    run_platform(action="primary", target_dir=str(tmp_path), platform_key="antigravity",
                 maika_root=str(REPO_ROOT))
    run_platform(action="disable", target_dir=str(tmp_path), platform_key="claude-code",
                 maika_root=str(REPO_ROOT))
    assert _knowledge_hash(tmp_path) == before
