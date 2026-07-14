from pathlib import Path

import pytest

from cli.mcp.adapters import get_mcp_adapter


def test_antigravity_adapter_lists_workspace_cli_ide_and_shared_paths(tmp_path):
    project = tmp_path / "proj"
    home = tmp_path / "home"
    adapter = get_mcp_adapter("antigravity")

    candidates = adapter.config_candidates(project, home)
    paths = [item.path for item in candidates]

    assert adapter.framework_root == ".maika"
    assert project / ".agents" / "mcp_config.json" in paths
    assert home / ".gemini" / "antigravity-cli" / "mcp_config.json" in paths
    assert home / ".gemini" / "antigravity" / "mcp_config.json" in paths
    assert home / ".gemini" / "config" / "mcp_config.json" in paths


def test_claude_adapter_lists_project_mcp_json_first(tmp_path):
    project = tmp_path / "proj"
    home = tmp_path / "home"
    adapter = get_mcp_adapter("claude-code")

    candidates = adapter.config_candidates(project, home)

    assert adapter.framework_root == ".maika"
    assert candidates[0].path == project / ".mcp.json"
    assert candidates[0].format == "json"


def test_codex_adapter_lists_project_config_toml_first(tmp_path):
    project = tmp_path / "proj"
    home = tmp_path / "home"
    adapter = get_mcp_adapter("codex")

    candidates = adapter.config_candidates(project, home)

    assert adapter.framework_root == ".maika"
    assert candidates[0].path == project / ".codex" / "config.toml"
    assert candidates[0].format == "toml"


def test_generic_adapter_has_no_native_candidates(tmp_path):
    adapter = get_mcp_adapter("generic")
    assert adapter.framework_root == ".maika"
    assert adapter.config_candidates(tmp_path / "proj", tmp_path / "home") == []


def test_unknown_adapter_fails_clearly():
    with pytest.raises(ValueError) as exc:
        get_mcp_adapter("unknown")

    assert "Unknown MCP platform adapter" in str(exc.value)
