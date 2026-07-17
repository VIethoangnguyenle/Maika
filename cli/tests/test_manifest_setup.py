from pathlib import Path
from cli.scaffold import load_manifest

MAIKA_ROOT = Path(__file__).resolve().parent.parent.parent


def _ua_setup():
    manifest = load_manifest(MAIKA_ROOT)
    return manifest["mcp_capabilities"]["understand-anything"]["setup"]


def test_setup_has_two_graph_artifacts():
    arts = _ua_setup()["graph_artifacts"]
    names = {a["name"] for a in arts}
    assert names == {"code", "domain"}
    for a in arts:
        assert a["path"].startswith(".understand-anything/")
        assert a["gen_cmd"].startswith("/understand")


def test_setup_engine_check_kinds_valid():
    checks = _ua_setup()["engine_check"]
    assert {"claude-code", "codex", "antigravity", "default"} <= set(checks)
    for spec in checks.values():
        assert spec["kind"] in ("path_exists", "file_contains")
        assert "{home}" in spec["path"]
    assert checks["claude-code"]["needle"] == "understand-anything@"


def test_setup_server_and_install_hint():
    setup = _ua_setup()
    assert setup["server"]["command"] == "uv"
    assert "{ua_mcp_dir}" in setup["server"]["args"]
    assert setup["server"]["env"]["PROJECT_ROOTS"] == "{project_root}"
    assert "claude-code" in setup["install_hint"]
    assert "default" in setup["install_hint"]


def test_socraticode_removed_from_manifest():
    manifest = load_manifest(MAIKA_ROOT)
    assert "socraticode" not in manifest["mcp_capabilities"]


def test_manifest_has_no_codebase_memory_capability():
    manifest = load_manifest(MAIKA_ROOT)
    assert "codebase-memory-mcp" not in manifest["mcp_capabilities"]


def test_serena_manifest_is_pinned_and_uses_maika_context():
    manifest = load_manifest(MAIKA_ROOT)
    cap = manifest["mcp_capabilities"]["serena"]
    assert cap["provides"] == "semantic_code_intelligence"
    assert cap["setup"]["version"] == "1.5.3"
    assert cap["setup"]["server"]["command"] == "serena"
    assert (
        "{project_root}/.maika/config/serena-context.yml"
        in cap["setup"]["server"]["args"]
    )
