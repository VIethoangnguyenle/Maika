import json as _json
from pathlib import Path, PureWindowsPath
from cli.mcp import ua_setup


def test_expand_substitutes_all_placeholders():
    out = ua_setup.expand(
        "{home}/x {platform} {ua_mcp_dir} {project_root}",
        home=Path("/h"), platform="codex", ua_mcp_dir="/srv", project_root="/proj",
    )
    assert out == "/h/x codex /srv /proj"


def test_expand_normalizes_windows_home_to_forward_slashes():
    out = ua_setup.expand(
        "{home}/.agents",
        home=PureWindowsPath("C:/Users/maika"),
    )
    assert out == "C:/Users/maika/.agents"


def test_resolve_engine_check_path_exists(tmp_path):
    marker = tmp_path / ".agents" / "skills" / "understand"
    marker.parent.mkdir(parents=True)
    marker.write_text("x")
    setup = {"engine_check": {"codex": {"kind": "path_exists", "path": "{home}/.agents/skills/understand"}}}
    assert ua_setup.resolve_engine_check(setup, "codex", tmp_path) is True
    assert ua_setup.resolve_engine_check(setup, "codex", tmp_path / "empty") is False


def test_resolve_engine_check_file_contains(tmp_path):
    reg = tmp_path / ".claude" / "plugins" / "installed_plugins.json"
    reg.parent.mkdir(parents=True)
    reg.write_text('{"plugins": {"understand-anything@Egonex-AI": []}}')
    setup = {"engine_check": {"claude-code": {
        "kind": "file_contains", "path": "{home}/.claude/plugins/installed_plugins.json",
        "needle": "understand-anything@"}}}
    assert ua_setup.resolve_engine_check(setup, "claude-code", tmp_path) is True
    reg.write_text('{"plugins": {}}')
    assert ua_setup.resolve_engine_check(setup, "claude-code", tmp_path) is False


def test_resolve_engine_check_command_exists_uses_shutil_which(tmp_path, monkeypatch):
    setup = {
        "engine_check": {
            "default": {"kind": "command_exists", "command": "serena"},
        },
    }
    calls = []

    monkeypatch.setattr(
        "shutil.which", lambda command: calls.append(command) or "/usr/bin/serena"
    )
    assert ua_setup.resolve_engine_check(setup, "codex", tmp_path) is True
    assert calls == ["serena"]

    monkeypatch.setattr("shutil.which", lambda command: None)
    assert ua_setup.resolve_engine_check(setup, "codex", tmp_path) is False


def test_resolve_engine_check_falls_back_to_default(tmp_path):
    (tmp_path / ".understand-anything" / "repo").mkdir(parents=True)
    setup = {"engine_check": {"default": {"kind": "path_exists", "path": "{home}/.understand-anything/repo"}}}
    assert ua_setup.resolve_engine_check(setup, "unknown-platform", tmp_path) is True


def test_engine_status_line(tmp_path):
    setup = {
        "engine_check": {"default": {"kind": "path_exists", "path": "{home}/.understand-anything/repo"}},
        "install_hint": {"default": "curl ... bash -s {platform}"},
    }
    assert ua_setup.engine_status_line(setup, "codex", tmp_path).startswith("engine: ✗ not installed")
    assert "bash -s codex" in ua_setup.engine_status_line(setup, "codex", tmp_path)
    (tmp_path / ".understand-anything" / "repo").mkdir(parents=True)
    assert ua_setup.engine_status_line(setup, "codex", tmp_path) == "engine: ✓ installed"


def test_codex_server_snippet_is_toml_and_fills_placeholders():
    setup = {"server": {
        "command": "uv",
        "args": ["--directory", "{ua_mcp_dir}", "run", "server.py"],
        "env": {"PROJECT_ROOTS": "{project_root}"},
    }}
    text = ua_setup.render_server_snippet(
        setup, server_key="understand-anything",
        platform="codex", ua_mcp_dir="/srv/ua-mcp", project_root="/proj",
    )
    assert "[mcp_servers.understand-anything]" in text
    assert 'command = "uv"' in text
    assert 'args = ["--directory", "/srv/ua-mcp", "run", "server.py"]' in text
    assert '[mcp_servers.understand-anything.env]' in text
    assert 'PROJECT_ROOTS = "/proj"' in text


def test_json_hosts_receive_json_snippets_without_empty_env():
    setup = {"server": {
        "command": "serena",
        "args": ["start-mcp-server", "--project", "{project_root}"],
    }}
    for platform in ("claude-code", "antigravity"):
        text = ua_setup.render_server_snippet(
            setup, server_key="serena", platform=platform,
            ua_mcp_dir="", project_root="/proj",
        )
        server = _json.loads(text)["mcpServers"]["serena"]
        assert server["command"] == "serena"
        assert server["args"] == ["start-mcp-server", "--project", "/proj"]
        assert "env" not in server


def test_codex_server_snippet_omits_empty_env():
    text = ua_setup.render_server_snippet(
        {"server": {"command": "codebase-memory-mcp", "args": []}},
        server_key="codebase-memory-mcp", platform="codex",
        ua_mcp_dir="", project_root="/proj",
    )
    assert "[mcp_servers.codebase-memory-mcp]" in text
    assert "env" not in text


def _full_setup():
    return {
        "graph_artifacts": [
            {"name": "code", "path": ".understand-anything/knowledge-graph.json", "gen_cmd": "/understand"},
            {"name": "domain", "path": ".understand-anything/domain-graph.json", "gen_cmd": "/understand-domain"},
        ],
        "install_hint": {
            "claude-code": "/plugin install understand-anything",
            "default": "curl ... bash -s {platform}",
        },
        "server": {
            "command": "uv",
            "args": ["--directory", "{ua_mcp_dir}", "run", "server.py"],
            "env": {"PROJECT_ROOTS": "{project_root}"},
        },
    }


def _serena_setup():
    return {
        "install_hint": {"default": "uv tool install serena-agent"},
        "prepare_hint": (
            "serena project create {project_root} --language {language}  "
            "# omit --language for Maika language 'other'"
        ),
        "server": {
            "command": "serena",
            "args": ["start-mcp-server", "--project", "{project_root}"],
        },
    }


def test_render_mcp_setup_section_includes_every_enabled_host():
    text = ua_setup.render_mcp_setup_section(
        _serena_setup(), server_key="serena",
        platform_keys=["codex", "claude-code", "antigravity"],
        ua_mcp_dir="", project_root="/proj", language="python",
    )
    assert text.startswith("## Provider: serena")
    assert "serena project create /proj --language python" in text
    assert "No separate index build is required" in text
    assert "#### Codex" in text and "```toml" in text
    assert "#### Claude Code" in text and "#### Antigravity" in text
    assert text.count("```json") == 2


def test_render_mcp_setup_section_lets_serena_infer_other_language():
    text = ua_setup.render_mcp_setup_section(
        _serena_setup(), server_key="serena", platform_keys=["codex"],
        ua_mcp_dir="", project_root="/proj", language="other",
    )
    assert "serena project create /proj\n" in text
    assert "--language other" not in text


def test_render_mcp_setup_md_codex():
    md = ua_setup.render_mcp_setup_md(
        _full_setup(), server_key="understand-anything", platform="codex",
        ua_mcp_dir="/srv/ua-mcp", project_root="/proj",
    )
    assert "bash -s codex" in md
    assert "/understand" in md and "/understand-domain" in md
    assert 'PROJECT_ROOTS = "/proj"' in md
    assert "/srv/ua-mcp" in md


def test_render_mcp_setup_md_claude_uses_platform_hint():
    md = ua_setup.render_mcp_setup_md(
        _full_setup(), server_key="understand-anything", platform="claude-code",
        ua_mcp_dir="<PATH_TO_Understand-Anything-MCP>", project_root="/proj",
    )
    assert "/plugin install understand-anything" in md
    assert "<PATH_TO_Understand-Anything-MCP>" in md


def test_graph_status_lines(tmp_path):
    setup = {"graph_artifacts": [
        {"name": "code", "path": ".understand-anything/knowledge-graph.json", "gen_cmd": "/understand"},
        {"name": "domain", "path": ".understand-anything/domain-graph.json", "gen_cmd": "/understand-domain"},
    ]}
    ua = tmp_path / ".understand-anything"
    ua.mkdir()
    (ua / "knowledge-graph.json").write_text(_json.dumps({"nodes": [1, 2, 3], "edges": [1, 2]}))
    lines = ua_setup.graph_status_lines(setup, tmp_path)
    assert lines[0] == "code: nodes=3 edges=2"
    assert lines[1] == "domain: ✗ run /understand-domain"


def test_graph_status_lines_unparseable(tmp_path):
    setup = {"graph_artifacts": [
        {"name": "code", "path": ".understand-anything/knowledge-graph.json", "gen_cmd": "/understand"},
    ]}
    ua = tmp_path / ".understand-anything"
    ua.mkdir()
    (ua / "knowledge-graph.json").write_text("{not json")
    assert ua_setup.graph_status_lines(setup, tmp_path) == ["code: present (unparseable)"]


def test_render_mcp_setup_md_index_step_when_no_graph_artifacts():
    setup = {
        "install_hint": {"default": "install uv"},
        "index_hint": "Ask the agent: 'Index this project'.",
        "server": {"command": "uvx", "args": ["codebase-memory-mcp"]},
    }
    md = ua_setup.render_mcp_setup_md(
        setup, server_key="codebase-memory-mcp", platform="claude-code",
        ua_mcp_dir="", project_root="/proj",
    )
    assert "## 2. Index the codebase" in md
    assert "Ask the agent: 'Index this project'." in md
    assert "Generate graphs" not in md


def test_render_mcp_setup_md_keeps_generate_graphs_when_artifacts_present():
    setup = {
        "install_hint": {"default": "install"},
        "graph_artifacts": [{"name": "code", "path": ".x/g.json", "gen_cmd": "/understand"}],
        "server": {"command": "uv", "args": ["run", "server.py"]},
    }
    md = ua_setup.render_mcp_setup_md(
        setup, server_key="understand-anything", platform="claude-code",
        ua_mcp_dir="/srv", project_root="/proj",
    )
    assert "## 2. Generate graphs" in md
    assert "Index the codebase" not in md
