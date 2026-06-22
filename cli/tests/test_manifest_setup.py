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


def _cbm_setup():
    manifest = load_manifest(MAIKA_ROOT)
    return manifest["mcp_capabilities"]["codebase-memory-mcp"]["setup"]


def test_socraticode_removed_from_manifest():
    manifest = load_manifest(MAIKA_ROOT)
    assert "socraticode" not in manifest["mcp_capabilities"]


def test_cbm_capability_present():
    manifest = load_manifest(MAIKA_ROOT)
    cap = manifest["mcp_capabilities"]["codebase-memory-mcp"]
    assert cap["provides"] == "code_exploration"


def test_cbm_setup_server_is_uvx_no_clone_dir():
    setup = _cbm_setup()
    assert setup["server"]["command"] == "uvx"
    assert setup["server"]["args"] == ["codebase-memory-mcp"]
    assert "{ua_mcp_dir}" not in str(setup["server"])


def test_cbm_setup_has_no_graph_artifacts_but_has_index_hint():
    setup = _cbm_setup()
    assert "graph_artifacts" not in setup
    assert setup["index_hint"]


def test_cbm_setup_engine_check_and_install_hint():
    setup = _cbm_setup()
    assert setup["engine_check"]["default"]["kind"] == "path_exists"
    assert "{home}" in setup["engine_check"]["default"]["path"]
    assert "default" in setup["install_hint"]
