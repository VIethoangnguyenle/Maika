import json

from cli.mcp.adapters import McpConfigCandidate
from cli.mcp import config as mcp_config
from cli.mcp.config import load_mcp_config, redact_mapping, selected_server_matches, server_names


def test_load_json_mcp_servers(tmp_path):
    path = tmp_path / "mcp_config.json"
    path.write_text(
        json.dumps({"mcpServers": {"codebase-memory-mcp": {"command": "npx", "args": ["x"]}}}),
        encoding="utf-8",
    )
    config = load_mcp_config(McpConfigCandidate(path, "workspace", "json"))

    assert config.exists is True
    assert config.valid is True
    assert server_names(config) == ["codebase-memory-mcp"]


def test_load_codex_toml_mcp_servers(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(
        '[mcp_servers.codebase-memory-mcp]\ncommand = "npx"\nargs = ["codebase-memory-mcp"]\n',
        encoding="utf-8",
    )
    config = load_mcp_config(McpConfigCandidate(path, "workspace", "toml"))

    assert config.valid is True
    assert server_names(config) == ["codebase-memory-mcp"]


def test_load_codex_toml_mcp_servers_without_tomllib(tmp_path, monkeypatch):
    monkeypatch.setattr(mcp_config, "tomllib", None)
    path = tmp_path / "config.toml"
    path.write_text(
        '[mcp_servers.codebase-memory-mcp]\ncommand = "npx"\nargs = ["codebase-memory-mcp"]\n',
        encoding="utf-8",
    )
    config = load_mcp_config(McpConfigCandidate(path, "workspace", "toml"))

    assert config.valid is True
    assert server_names(config) == ["codebase-memory-mcp"]


def test_missing_and_empty_configs_are_not_valid(tmp_path):
    missing = load_mcp_config(McpConfigCandidate(tmp_path / "missing.json", "x", "json"))
    assert missing.exists is False
    assert missing.valid is False

    empty_path = tmp_path / "empty.json"
    empty_path.write_text("", encoding="utf-8")
    empty = load_mcp_config(McpConfigCandidate(empty_path, "x", "json"))
    assert empty.exists is True
    assert empty.valid is False
    assert "empty" in empty.error


def test_selected_server_matches_returns_present_and_missing(tmp_path):
    path = tmp_path / "mcp_config.json"
    path.write_text(json.dumps({"mcpServers": {"db-access": {}, "agent-memory": {}}}), encoding="utf-8")
    config = load_mcp_config(McpConfigCandidate(path, "workspace", "json"))

    present, missing = selected_server_matches(config, ["db-access", "codebase-memory-mcp"])

    assert present == ["db-access"]
    assert missing == ["codebase-memory-mcp"]


def test_redact_mapping_hides_secrets_recursively():
    value = {
        "headers": {"Authorization": "Bearer abc", "X-Plain": "ok"},
        "env": {"TOKEN": "secret", "NORMAL": "value"},
        "nested": [{"api_key": "123"}],
    }

    redacted = redact_mapping(value)

    assert redacted["headers"]["Authorization"] == "<redacted>"
    assert redacted["headers"]["X-Plain"] == "ok"
    assert redacted["env"]["TOKEN"] == "<redacted>"
    assert redacted["env"]["NORMAL"] == "<redacted>"
    assert redacted["nested"][0]["api_key"] == "<redacted>"
