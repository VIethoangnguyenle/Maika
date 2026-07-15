"""Behavior tests for `maika platform` multi-host enable/disable/primary.

Core `.maika` renders once (at init); enabling another host installs only its
entrypoint + native config and never touches project knowledge.
"""

import hashlib
from pathlib import Path

import pytest

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


def _tree_hash(target: Path) -> dict:
    return {
        p.relative_to(target).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(target.rglob("*")) if p.is_file()
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
    assert "write-gate" not in (tmp_path / ".claude" / "settings.json").read_text(encoding="utf-8")
    assert (tmp_path / ".codex" / "hooks.json").exists()
    assert (tmp_path / ".maika" / "rules" / "RULES.md").exists()
    assert project.load(tmp_path)["platforms"]["enabled"] == ["codex"]


def test_disable_preserves_shared_entrypoint_block(tmp_path):
    _init(tmp_path, "codex")            # AGENTS.md
    _enable(tmp_path, "antigravity")    # also AGENTS.md + .agents/hooks.json
    run_platform(action="disable", target_dir=str(tmp_path), platform_key="antigravity",
                 maika_root=str(REPO_ROOT))

    # antigravity native config's maika entry gone...
    assert "write-gate" not in (tmp_path / ".agents" / "hooks.json").read_text(encoding="utf-8")
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


def test_enable_rolls_back_adapter_and_metadata_together(tmp_path, monkeypatch):
    _init(tmp_path, "codex")
    before = _tree_hash(tmp_path)
    from cli.install.transaction import Transaction
    real = Transaction._execute

    def fail_at_metadata(self, action):
        if action["path"] == ".maika/config/project.yaml":
            raise RuntimeError("injected metadata failure")
        return real(self, action)

    monkeypatch.setattr(Transaction, "_execute", fail_at_metadata)
    with pytest.raises(RuntimeError, match="metadata failure"):
        _enable(tmp_path, "claude-code")
    assert _tree_hash(tmp_path) == before
    assert not (tmp_path / "CLAUDE.md").exists()


def test_enable_refreshes_aggregate_mcp_setup_for_all_hosts(tmp_path):
    selected = ["understand-anything", "codebase-memory-mcp", "serena"]
    run_init(
        target_dir=str(tmp_path), maika_root=str(REPO_ROOT),
        platform_key="codex", selected_mcps=selected, language="python",
        assume_yes=True, ua_mcp_dir="/srv/ua-mcp",
    )

    _enable(tmp_path, "claude-code")

    text = (tmp_path / ".maika" / "MCP_SETUP.md").read_text(encoding="utf-8")
    for provider in selected:
        assert text.count(f"## Provider: {provider}") == 1
    assert "/srv/ua-mcp" in text
    assert "#### Codex" in text
    assert "#### Claude Code" in text
    assert "[mcp_servers.serena]" in text
    assert '"mcpServers": {' in text


def test_enable_rolls_back_when_setup_refresh_fails(tmp_path, monkeypatch):
    run_init(
        target_dir=str(tmp_path), maika_root=str(REPO_ROOT),
        platform_key="codex", selected_mcps=["serena"], language="python",
        assume_yes=True,
    )
    before = _tree_hash(tmp_path)
    from cli.install.transaction import Transaction
    real = Transaction._execute

    def fail_at_setup(self, action):
        if action["path"] == ".maika/MCP_SETUP.md":
            raise RuntimeError("injected setup refresh failure")
        return real(self, action)

    monkeypatch.setattr(Transaction, "_execute", fail_at_setup)
    with pytest.raises(RuntimeError, match="setup refresh failure"):
        _enable(tmp_path, "claude-code")
    assert _tree_hash(tmp_path) == before
    assert not (tmp_path / "CLAUDE.md").exists()
