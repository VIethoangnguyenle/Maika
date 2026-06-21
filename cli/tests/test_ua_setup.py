from pathlib import Path
from cli.mcp import ua_setup


def test_expand_substitutes_all_placeholders():
    out = ua_setup.expand(
        "{home}/x {platform} {ua_mcp_dir} {project_root}",
        home=Path("/h"), platform="codex", ua_mcp_dir="/srv", project_root="/proj",
    )
    assert out == "/h/x codex /srv /proj"


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
