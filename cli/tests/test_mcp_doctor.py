import json
from pathlib import Path

import pytest
import yaml

from cli.commands.doctor import run_doctor_mcp
from cli.commands.init import run_init
from cli.mcp.doctor import _smoke_source, build_doctor_status, render_report
from cli.mcp.integration import serena

MAIKA_ROOT = Path(__file__).resolve().parent.parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "provider_contracts"


def write_resolved(target, platform="antigravity", mcps=None, language="python"):
    root = ".agents" if platform in ("antigravity", "codex") else ".claude"
    path = target / root / "resolved-config.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.dump({"resolved": {
            "platform": platform,
            "framework_root": root,
            "mcps": mcps or ["db-access"],
            "language": language,
        }}),
        encoding="utf-8",
    )
    return path


def _init_serena(tmp_path):
    target = tmp_path / "proj"
    home = tmp_path / "home"
    home.mkdir()
    write_resolved(target, platform="antigravity", mcps=["serena"])
    config = target / ".agents" / "mcp_config.json"
    config.write_text(
        json.dumps({"mcpServers": {"serena": {
            "command": "serena",
            "args": ["start-mcp-server", "--project", str(target)],
        }}}),
        encoding="utf-8",
    )
    project = target / ".serena" / "project.yml"
    project.parent.mkdir()
    project.write_text(
        "project_name: doctor-fixture\nlanguages:\n  - python\n",
        encoding="utf-8",
    )
    source = target / "src" / "app.py"
    source.parent.mkdir()
    source.write_text("def doctor_fixture():\n    return True\n", encoding="utf-8")
    return target, home


def _stub_serena_version(monkeypatch, version="1.5.3"):
    monkeypatch.setattr(
        "cli.mcp.doctor.probe_serena_version", lambda server: (version, "")
    )


def _stub_serena_smoke(monkeypatch):
    monkeypatch.setattr(
        "cli.mcp.doctor.probe_serena_symbol_smoke",
        lambda server, bridge_path, relative_path: ("ready", ""),
        raising=False,
    )


def test_doctor_marks_serena_ready_from_real_tools_list(tmp_path, monkeypatch):
    target, home = _init_serena(tmp_path)
    fixture = json.loads(
        (FIXTURES / "serena" / "tools-list-readonly-v1.json").read_text()
    )
    monkeypatch.setattr("cli.mcp.ua_setup.shutil.which", lambda command: "/bin/serena")
    _stub_serena_version(monkeypatch)
    _stub_serena_smoke(monkeypatch)
    monkeypatch.setattr(
        "cli.mcp.doctor.probe_tools_list", lambda server, bridge_path: (fixture, "")
    )

    status = build_doctor_status(target, home, maika_root=MAIKA_ROOT)

    assert "version: READY (Serena 1.5.3)" in status.setup_reports["serena"]
    assert (
        "project: READY (python backend; smoke file: src/app.py)"
        in status.setup_reports["serena"]
    )
    assert any(
        line == f"contract: READY (8 Phase 1 tools; {serena.SERENA_READONLY_V1_TOOL_SURFACE_HASH})"
        for line in status.setup_reports["serena"]
    )
    assert "symbol smoke: READY" in status.setup_reports["serena"]
    assert status.bridge_state == "probed"


def test_doctor_degrades_serena_when_write_tool_is_exposed(tmp_path, monkeypatch):
    target, home = _init_serena(tmp_path)
    snapshot = {"tools": [{"name": "rename_symbol", "inputSchema": {"type": "object"}}]}
    monkeypatch.setattr("cli.mcp.ua_setup.shutil.which", lambda command: "/bin/serena")
    _stub_serena_version(monkeypatch)
    monkeypatch.setattr(
        "cli.mcp.doctor.probe_tools_list", lambda server, bridge_path: (snapshot, "")
    )

    status = build_doctor_status(target, home, maika_root=MAIKA_ROOT)

    assert any(
        "DEGRADED" in line and "rename_symbol" in line
        for line in status.setup_reports["serena"]
    )


def test_doctor_degrades_serena_when_pinned_tool_schema_drifts(tmp_path, monkeypatch):
    target, home = _init_serena(tmp_path)
    snapshot = json.loads(
        (FIXTURES / "serena" / "tools-list-readonly-v1.json").read_text()
    )
    snapshot["tools"][0]["description"] = "changed runtime schema"
    monkeypatch.setattr("cli.mcp.ua_setup.shutil.which", lambda command: "/bin/serena")
    _stub_serena_version(monkeypatch)
    monkeypatch.setattr(
        "cli.mcp.doctor.probe_tools_list", lambda server, bridge_path: (snapshot, "")
    )

    status = build_doctor_status(target, home, maika_root=MAIKA_ROOT)

    assert any(
        "DEGRADED" in line and "schema drift" in line
        for line in status.setup_reports["serena"]
    )


def test_doctor_degrades_failed_serena_handshake_without_exposing_secrets(
    tmp_path, monkeypatch
):
    target, home = _init_serena(tmp_path)
    config = target / ".agents" / "mcp_config.json"
    config.write_text(
        json.dumps({
            "mcpServers": {
                    "serena": {
                        "command": "serena",
                        "args": ["start-mcp-server", "--project", str(target)],
                        "env": {"SERENA_TOKEN": "runtime-secret"},
                    "headers": {"X-Custom": "header-runtime-secret"},
                }
            }
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr("cli.mcp.ua_setup.shutil.which", lambda command: "/bin/serena")
    _stub_serena_version(monkeypatch)
    monkeypatch.setattr(
        "cli.mcp.doctor.probe_tools_list",
        lambda server, bridge_path: (None, "initialize failed: runtime-secret"),
    )

    status = build_doctor_status(target, home, maika_root=MAIKA_ROOT)
    report = render_report(status)

    assert "contract: DEGRADED" in report
    assert "initialize failed" in report
    assert "runtime-secret" not in report
    assert "header-runtime-secret" not in report
    assert '"X-Custom": "<redacted>"' in report
    assert "contract: READY" not in report


def test_run_doctor_uses_packaged_asset_root_for_serena_bridge(tmp_path, monkeypatch):
    target, home = _init_serena(tmp_path)
    packaged_root = tmp_path / "site-packages" / "cli" / "_assets"
    packaged_manifest = packaged_root / "cli" / "plugin-manifest.yaml"
    packaged_manifest.parent.mkdir(parents=True)
    packaged_manifest.write_text(
        (MAIKA_ROOT / "cli" / "plugin-manifest.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    expected_bridge = (
        packaged_root / ".maika" / "tools" / "mcp-bridge" / "mcp_client.py"
    )
    fixture = json.loads(
        (FIXTURES / "serena" / "tools-list-readonly-v1.json").read_text()
    )
    calls = []
    monkeypatch.setattr("cli.mcp.ua_setup.shutil.which", lambda command: "/bin/serena")
    _stub_serena_version(monkeypatch)
    _stub_serena_smoke(monkeypatch)
    monkeypatch.setattr("cli.commands.doctor.asset_root", lambda: packaged_root)
    monkeypatch.setattr(
        "cli.mcp.doctor.probe_tools_list",
        lambda server, bridge_path: (calls.append(bridge_path) or fixture, ""),
    )

    run_doctor_mcp(str(target), fix=False, assume_yes=False, home=home)

    assert calls == [expected_bridge]


def test_doctor_degrades_wrong_serena_version_before_runtime_probe(tmp_path, monkeypatch):
    target, home = _init_serena(tmp_path)
    calls = []
    monkeypatch.setattr("cli.mcp.ua_setup.shutil.which", lambda command: "/bin/serena")
    _stub_serena_version(monkeypatch, "1.5.2")
    monkeypatch.setattr(
        "cli.mcp.doctor.probe_tools_list",
        lambda server, bridge_path: calls.append((server, bridge_path)),
    )

    status = build_doctor_status(target, home, maika_root=MAIKA_ROOT)

    assert calls == []
    assert "version: DEGRADED — expected Serena 1.5.3" in status.setup_reports["serena"]
    assert not any("contract: READY" in line for line in status.setup_reports["serena"])


def test_doctor_degrades_missing_or_unusable_serena_project_backend(tmp_path, monkeypatch):
    target, home = _init_serena(tmp_path)
    (target / ".serena" / "project.yml").write_text(
        "project_name: doctor-fixture\nlanguages: []\n", encoding="utf-8"
    )
    calls = []
    monkeypatch.setattr("cli.mcp.ua_setup.shutil.which", lambda command: "/bin/serena")
    _stub_serena_version(monkeypatch)
    monkeypatch.setattr(
        "cli.mcp.doctor.probe_tools_list",
        lambda server, bridge_path: calls.append((server, bridge_path)),
    )

    status = build_doctor_status(target, home, maika_root=MAIKA_ROOT)

    assert calls == []
    assert "project: DEGRADED — no selected language backend" in status.setup_reports["serena"]


@pytest.mark.parametrize(
    ("language", "backend", "relative_path", "body"),
    [
        ("python", "python", "src/main.py", "def main():\n    return 0\n"),
        ("typescript", "typescript", "src/main.ts", "export const main = () => 0;\n"),
        ("java", "java", "src/Main.java", "class Main {}\n"),
        ("go", "go", "cmd/main.go", "package main\nfunc main() {}\n"),
        ("csharp", "csharp", "src/Main.cs", "class Main {}\n"),
        ("javascript", "javascript", "web/main.js", "export const main = () => 0;\n"),
        ("other", "javascript", "web/inferred.js", "export const inferred = true;\n"),
    ],
)
def test_doctor_smokes_deterministic_source_for_selected_language_backend(
    tmp_path, monkeypatch, language, backend, relative_path, body
):
    target, home = _init_serena(tmp_path)
    write_resolved(
        target, platform="antigravity", mcps=["serena"], language=language,
    )
    for source in (target / "src").glob("*"):
        source.unlink()
    selected_source = target / relative_path
    selected_source.parent.mkdir(parents=True, exist_ok=True)
    selected_source.write_text(body, encoding="utf-8")
    (target / ".serena" / "project.yml").write_text(
        f"project_name: doctor-fixture\nlanguages:\n  - {backend}\n",
        encoding="utf-8",
    )
    fixture = json.loads(
        (FIXTURES / "serena" / "tools-list-readonly-v1.json").read_text()
    )
    calls = []
    monkeypatch.setattr("cli.mcp.ua_setup.shutil.which", lambda command: "/bin/serena")
    _stub_serena_version(monkeypatch)
    monkeypatch.setattr(
        "cli.mcp.doctor.probe_tools_list", lambda server, bridge_path: (fixture, "")
    )
    monkeypatch.setattr(
        "cli.mcp.doctor.probe_serena_symbol_smoke",
        lambda server, bridge_path, path: (calls.append(path) or "ready", ""),
        raising=False,
    )

    status = build_doctor_status(target, home, maika_root=MAIKA_ROOT)

    assert calls == [relative_path]
    assert f"project: READY ({backend} backend; smoke file: {relative_path})" in status.setup_reports["serena"]
    assert "symbol smoke: READY" in status.setup_reports["serena"]


def test_smoke_source_prunes_excluded_trees_before_inspecting_files(
    tmp_path, monkeypatch
):
    target = tmp_path / "proj"
    source = target / "src" / "app.py"
    source.parent.mkdir(parents=True)
    source.write_text("def app():\n    return True\n", encoding="utf-8")
    excluded = target / "node_modules" / "package" / "ignored.py"
    excluded.parent.mkdir(parents=True)
    excluded.write_text("raise RuntimeError('must not be scanned')\n", encoding="utf-8")
    git_cache = target / ".git" / "cache" / "ignored.py"
    git_cache.parent.mkdir(parents=True)
    git_cache.write_text("raise RuntimeError('must not be scanned')\n", encoding="utf-8")
    real_is_file = Path.is_file

    def guarded_is_file(path):
        relative_parts = path.relative_to(target).parts
        if "node_modules" in relative_parts or ".git" in relative_parts:
            raise AssertionError(f"excluded tree inspected: {path}")
        return real_is_file(path)

    monkeypatch.setattr(Path, "is_file", guarded_is_file)

    assert _smoke_source(target, "python") == "src/app.py"


def test_doctor_degrades_selected_language_backend_mismatch_without_smoke(
    tmp_path, monkeypatch
):
    target, home = _init_serena(tmp_path)
    write_resolved(
        target, platform="antigravity", mcps=["serena"], language="typescript",
    )
    (target / "src" / "app.ts").write_text("export const app = true;\n", encoding="utf-8")
    calls = []
    monkeypatch.setattr("cli.mcp.ua_setup.shutil.which", lambda command: "/bin/serena")
    _stub_serena_version(monkeypatch)
    monkeypatch.setattr(
        "cli.mcp.doctor.probe_tools_list",
        lambda server, bridge_path: calls.append("tools-list"),
    )
    monkeypatch.setattr(
        "cli.mcp.doctor.probe_serena_symbol_smoke",
        lambda server, bridge_path, path: calls.append(path),
        raising=False,
    )

    status = build_doctor_status(target, home, maika_root=MAIKA_ROOT)

    assert calls == []
    assert (
        "project: DEGRADED — Maika language typescript is not enabled by Serena backends: python"
        in status.setup_reports["serena"]
    )


def test_doctor_degrades_when_selected_backend_has_no_smokeable_project_file(
    tmp_path, monkeypatch
):
    target, home = _init_serena(tmp_path)
    write_resolved(target, platform="antigravity", mcps=["serena"], language="java")
    (target / ".serena" / "project.yml").write_text(
        "project_name: doctor-fixture\nlanguages:\n  - java\n", encoding="utf-8"
    )
    calls = []
    monkeypatch.setattr("cli.mcp.ua_setup.shutil.which", lambda command: "/bin/serena")
    _stub_serena_version(monkeypatch)
    monkeypatch.setattr(
        "cli.mcp.doctor.probe_tools_list",
        lambda server, bridge_path: calls.append("tools-list"),
    )

    status = build_doctor_status(target, home, maika_root=MAIKA_ROOT)

    assert calls == []
    assert (
        "project: DEGRADED — no deterministic java source file available for symbol smoke"
        in status.setup_reports["serena"]
    )


def test_doctor_restarts_language_server_once_and_recovers_symbol_smoke(
    tmp_path, monkeypatch
):
    target, home = _init_serena(tmp_path)
    fixture = json.loads(
        (FIXTURES / "serena" / "tools-list-readonly-v1.json").read_text()
    )
    calls = []
    monkeypatch.setattr("cli.mcp.ua_setup.shutil.which", lambda command: "/bin/serena")
    _stub_serena_version(monkeypatch)
    monkeypatch.setattr(
        "cli.mcp.doctor.probe_tools_list", lambda server, bridge_path: (fixture, "")
    )

    monkeypatch.setattr(
        "cli.mcp.doctor.probe_serena_symbol_smoke",
        lambda server, bridge_path, relative_path: (
            calls.append(relative_path) or "recovered", ""
        ),
        raising=False,
    )

    status = build_doctor_status(target, home, maika_root=MAIKA_ROOT)
    report = render_report(status)

    assert calls == ["src/app.py"]
    assert "symbol smoke: READY (recovered after one language-server restart)" in report
    assert "backend-secret" not in report


def test_doctor_degrades_after_one_failed_smoke_recovery_without_raw_output(
    tmp_path, monkeypatch
):
    target, home = _init_serena(tmp_path)
    fixture = json.loads(
        (FIXTURES / "serena" / "tools-list-readonly-v1.json").read_text()
    )
    calls = []
    monkeypatch.setattr("cli.mcp.ua_setup.shutil.which", lambda command: "/bin/serena")
    _stub_serena_version(monkeypatch)
    monkeypatch.setattr(
        "cli.mcp.doctor.probe_tools_list", lambda server, bridge_path: (fixture, "")
    )

    monkeypatch.setattr(
        "cli.mcp.doctor.probe_serena_symbol_smoke",
        lambda server, bridge_path, relative_path: (
            calls.append(relative_path) or "degraded",
            "MCP runtime probe failed",
        ),
        raising=False,
    )

    report = render_report(build_doctor_status(target, home, maika_root=MAIKA_ROOT))

    assert calls == ["src/app.py"]
    assert "symbol smoke: DEGRADED — symbol backend unavailable after one recovery" in report
    assert "super-secret-provider-output" not in report
    assert "contract: READY" in report


def test_doctor_does_not_probe_serena_until_engine_check_passes(tmp_path, monkeypatch):
    target, home = _init_serena(tmp_path)
    calls = []
    monkeypatch.setattr("cli.mcp.ua_setup.shutil.which", lambda command: None)
    monkeypatch.setattr(
        "cli.mcp.doctor.probe_tools_list",
        lambda server, bridge_path: calls.append((server, bridge_path)),
    )

    status = build_doctor_status(target, home, maika_root=MAIKA_ROOT)

    assert calls == []
    assert "contract: DEGRADED — engine not installed" in status.setup_reports["serena"]
    assert status.bridge_state == "not-probed"


def test_doctor_inspects_every_enabled_platform_and_aggregates_conservatively(
    tmp_path, monkeypatch
):
    target, home = _init_serena(tmp_path)
    (target / ".maika" / "config").mkdir(parents=True)
    (target / ".maika" / "config" / "project.yaml").write_text(
        "version: 1\nframework:\n  core_root: .maika\nplatforms:\n"
        "  enabled: [antigravity, claude-code]\n  primary: antigravity\n",
        encoding="utf-8",
    )
    (target / ".mcp.json").write_text(
        json.dumps({"mcpServers": {"other": {"command": "other"}}}),
        encoding="utf-8",
    )
    fixture = json.loads(
        (FIXTURES / "serena" / "tools-list-readonly-v1.json").read_text()
    )
    monkeypatch.setattr("cli.mcp.ua_setup.shutil.which", lambda command: "/bin/serena")
    _stub_serena_version(monkeypatch)
    _stub_serena_smoke(monkeypatch)
    monkeypatch.setattr(
        "cli.mcp.doctor.probe_tools_list", lambda server, bridge_path: (fixture, "")
    )

    status = build_doctor_status(target, home, maika_root=MAIKA_ROOT)
    report = render_report(status)

    assert set(status.platform_reports) == {"antigravity", "claude-code"}
    assert status.platform_reports["antigravity"].native_state == "configured"
    assert status.platform_reports["claude-code"].native_state == "unavailable"
    assert status.native_state == "partial"
    assert status.health_state == "degraded"
    assert status.matched == []
    assert status.missing == ["serena"]
    assert "## Platform health" in report
    assert "### Platform: Antigravity" in report
    assert "### Platform: Claude Code" in report
    assert "native: unavailable" in report


def test_doctor_writes_report_for_missing_native_config(tmp_path):
    target = tmp_path / "proj"
    home = tmp_path / "home"
    write_resolved(target)

    run_doctor_mcp(str(target), fix=False, assume_yes=False, home=home)

    report = target / ".maika" / "knowledge" / "active" / "mcp-doctor-report.md"
    text = report.read_text(encoding="utf-8")
    assert "Platform: antigravity" in text
    assert "db-access" in text
    assert "native: unavailable" in text
    assert "bridge: not-probed" in text


def test_doctor_matches_selected_server_in_existing_config(tmp_path):
    target = tmp_path / "proj"
    home = tmp_path / "home"
    write_resolved(target, mcps=["confluence", "db-access"])
    cfg = target / ".agents" / "mcp_config.json"
    cfg.write_text(json.dumps({"mcpServers": {"db-access": {"command": "npx"}}}), encoding="utf-8")

    run_doctor_mcp(str(target), fix=False, assume_yes=False, home=home)

    text = (target / ".maika" / "knowledge" / "active" / "mcp-doctor-report.md").read_text(encoding="utf-8")
    assert "matched: db-access" in text
    assert "missing: confluence" in text
    assert "native: partial" in text
    assert "bridge: not-probed" in text


def test_build_doctor_status_marks_partial_native_state_for_partial_match(tmp_path):
    target = tmp_path / "proj"
    home = tmp_path / "home"
    write_resolved(target, mcps=["confluence", "db-access"])
    cfg = target / ".agents" / "mcp_config.json"
    cfg.write_text(json.dumps({"mcpServers": {"db-access": {"command": "npx"}}}), encoding="utf-8")

    status = build_doctor_status(target, home)

    assert status.native_state == "partial"
    assert status.bridge_state == "not-probed"


def test_build_doctor_status_marks_missing_config_as_unavailable_and_not_probed(tmp_path):
    target = tmp_path / "proj"
    home = tmp_path / "home"
    write_resolved(target)

    status = build_doctor_status(target, home)

    assert status.native_state == "unavailable"
    assert status.bridge_state == "not-probed"


def test_doctor_report_redacts_secrets_in_matched_server_config(tmp_path):
    target = tmp_path / "proj"
    home = tmp_path / "home"
    write_resolved(target, mcps=["db-access"])
    cfg = target / ".agents" / "mcp_config.json"
    cfg.write_text(
        json.dumps({"mcpServers": {"db-access": {"command": "npx", "env": {"TOKEN": "supersecret"}}}}),
        encoding="utf-8",
    )

    run_doctor_mcp(str(target), fix=False, assume_yes=False, home=home)

    text = (target / ".maika" / "knowledge" / "active" / "mcp-doctor-report.md").read_text(encoding="utf-8")
    assert "npx" in text            # non-secret detail is shown
    assert "<redacted>" in text     # env value is redacted
    assert "supersecret" not in text


def test_doctor_reports_friendly_error_when_not_maika_project(tmp_path, capsys):
    target = tmp_path / "not-maika"
    target.mkdir()

    run_doctor_mcp(str(target), fix=False, assume_yes=False, home=tmp_path / "home")

    out = capsys.readouterr().out
    assert "resolved-config" in out


def test_doctor_fix_copies_known_good_antigravity_ide_config(tmp_path):
    target = tmp_path / "proj"
    home = tmp_path / "home"
    write_resolved(target, platform="antigravity", mcps=["db-access"])
    source = home / ".gemini" / "antigravity" / "mcp_config.json"
    source.parent.mkdir(parents=True)
    source.write_text(json.dumps({"mcpServers": {"db-access": {"command": "npx"}}}), encoding="utf-8")

    run_doctor_mcp(str(target), fix=True, assume_yes=True, home=home)

    dest = home / ".gemini" / "antigravity-cli" / "mcp_config.json"
    assert dest.exists()
    assert json.loads(dest.read_text(encoding="utf-8"))["mcpServers"]["db-access"]["command"] == "npx"


def test_doctor_fix_cleanly_replaces_existing_destination_without_backup(tmp_path):
    target = tmp_path / "proj"
    home = tmp_path / "home"
    write_resolved(target, platform="antigravity", mcps=["db-access"])
    source = home / ".gemini" / "antigravity" / "mcp_config.json"
    source.parent.mkdir(parents=True)
    source.write_text(json.dumps({"mcpServers": {"db-access": {"command": "npx"}}}), encoding="utf-8")
    dest = home / ".gemini" / "antigravity-cli" / "mcp_config.json"
    dest.parent.mkdir(parents=True)
    dest.write_text(json.dumps({"mcpServers": {"old": {"command": "old"}}}), encoding="utf-8")

    run_doctor_mcp(str(target), fix=True, assume_yes=True, home=home)

    assert not (dest.parent / ("mcp_config.json." + "bak")).exists()
    assert "old" not in dest.read_text(encoding="utf-8")


def _init_ua(tmp_path, home):
    run_init(
        target_dir=str(tmp_path), maika_root=str(MAIKA_ROOT),
        platform_key="codex", selected_mcps=["understand-anything"],
        language="python", assume_yes=True, ua_mcp_dir="/srv/ua-mcp",
    )


def test_doctor_reports_engine_and_graphs(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    _init_ua(tmp_path, home)
    (home / ".agents" / "skills").mkdir(parents=True)
    (home / ".agents" / "skills" / "understand").write_text("x")
    ua = tmp_path / ".understand-anything"
    ua.mkdir()
    (ua / "knowledge-graph.json").write_text(json.dumps({"nodes": [1, 2], "edges": [1]}))

    status = build_doctor_status(tmp_path, home, maika_root=MAIKA_ROOT)
    report = render_report(status)
    assert "engine: ✓ installed" in report
    assert "code: nodes=2 edges=1" in report
    assert "domain: ✗ run /understand-domain" in report


def test_doctor_reports_missing_serena_command_without_crashing(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    write_resolved(tmp_path, platform="codex", mcps=["serena"])
    monkeypatch.setattr("shutil.which", lambda command: None)

    status = build_doctor_status(tmp_path, home, maika_root=MAIKA_ROOT)

    assert status.setup_reports["serena"][0].startswith("engine: ✗ not installed")


def test_doctor_regression_no_ua(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    run_init(
        target_dir=str(tmp_path), maika_root=str(MAIKA_ROOT),
        platform_key="codex", selected_mcps=[], language="python", assume_yes=True,
    )
    status = build_doctor_status(tmp_path, home, maika_root=MAIKA_ROOT)
    assert status.setup_reports == {}


def test_probe_memory_daemon_connection_refused_is_down():
    from cli.mcp.doctor import _probe_memory_daemon
    # port 1: không có gì lắng nghe -> connection refused -> DOWN
    assert _probe_memory_daemon("http://127.0.0.1:1", timeout=0.3) is False


def test_probe_memory_daemon_any_http_response_is_up():
    import http.server
    import threading
    from cli.mcp.doctor import _probe_memory_daemon

    # BaseHTTPRequestHandler tra loi 501 cho moi request — van tinh la ALIVE
    # (khong phu thuoc endpoint /health cu the cua upstream)
    server = http.server.HTTPServer(("127.0.0.1", 0), http.server.BaseHTTPRequestHandler)
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        assert _probe_memory_daemon(f"http://127.0.0.1:{port}", timeout=2.0) is True
    finally:
        server.server_close()


def test_doctor_reports_memory_daemon_down_with_start_hint(tmp_path, monkeypatch):
    target = tmp_path / "proj"
    home = tmp_path / "home"
    write_resolved(target, mcps=["agent-memory"])
    monkeypatch.delenv("AGENTMEMORY_URL", raising=False)
    monkeypatch.setattr("cli.mcp.doctor._probe_memory_daemon", lambda url, timeout=2.0: False)

    run_doctor_mcp(str(target), fix=False, assume_yes=False, home=home)

    text = (target / ".maika" / "knowledge" / "active" / "mcp-doctor-report.md").read_text(encoding="utf-8")
    assert "agent-memory daemon: DOWN (http://localhost:3111)" in text
    assert "npm i -g @agentmemory/agentmemory" in text
    assert "agentmemory doctor" in text


def test_doctor_reports_memory_daemon_running(tmp_path, monkeypatch):
    target = tmp_path / "proj"
    home = tmp_path / "home"
    write_resolved(target, mcps=["agent-memory"])
    monkeypatch.delenv("AGENTMEMORY_URL", raising=False)
    monkeypatch.setattr("cli.mcp.doctor._probe_memory_daemon", lambda url, timeout=2.0: True)

    run_doctor_mcp(str(target), fix=False, assume_yes=False, home=home)

    text = (target / ".maika" / "knowledge" / "active" / "mcp-doctor-report.md").read_text(encoding="utf-8")
    assert "agent-memory daemon: RUNNING (http://localhost:3111)" in text


def test_doctor_memory_daemon_respects_agentmemory_url_env(tmp_path, monkeypatch):
    target = tmp_path / "proj"
    home = tmp_path / "home"
    write_resolved(target, mcps=["agent-memory"])
    monkeypatch.setenv("AGENTMEMORY_URL", "http://127.0.0.1:4222")
    monkeypatch.setattr("cli.mcp.doctor._probe_memory_daemon", lambda url, timeout=2.0: True)

    run_doctor_mcp(str(target), fix=False, assume_yes=False, home=home)

    text = (target / ".maika" / "knowledge" / "active" / "mcp-doctor-report.md").read_text(encoding="utf-8")
    assert "agent-memory daemon: RUNNING (http://127.0.0.1:4222)" in text


def test_doctor_omits_memory_daemon_line_when_not_selected(tmp_path):
    target = tmp_path / "proj"
    home = tmp_path / "home"
    write_resolved(target)  # mcps mặc định: db-access

    run_doctor_mcp(str(target), fix=False, assume_yes=False, home=home)

    text = (target / ".maika" / "knowledge" / "active" / "mcp-doctor-report.md").read_text(encoding="utf-8")
    assert "agent-memory daemon" not in text


def test_doctor_warns_without_mutating_user_global_agentmemory_hooks(tmp_path, monkeypatch):
    target = tmp_path / "proj"
    home = tmp_path / "home"
    write_resolved(target, mcps=["agent-memory"])
    settings = home / ".claude" / "settings.json"
    settings.parent.mkdir(parents=True)
    original = '{"hooks":{"Stop":[{"command":"agentmemory stop_summary"}]}}'
    settings.write_text(original, encoding="utf-8")
    monkeypatch.setattr("cli.mcp.doctor._probe_memory_daemon", lambda url, timeout=2.0: True)

    status = build_doctor_status(target, home)
    report = render_report(status)

    assert status.memory_governance == "degraded"
    assert "WARNING" in report and "auto-capture hook" in report
    assert settings.read_text(encoding="utf-8") == original


def test_doctor_flags_cbm_contamination(tmp_path):
    target = tmp_path / "proj"
    home = tmp_path / "home"
    write_resolved(target, mcps=["db-access"])
    hooks = home / ".claude" / "hooks"
    hooks.mkdir(parents=True)
    (hooks / "cbm-gate.sh").write_text(
        "# Installed by codebase-memory-mcp\n", encoding="utf-8")
    status = build_doctor_status(target, home)
    assert status.cbm_contamination == "contaminated"
    assert status.health_state == "degraded"
    text = render_report(status)
    assert "cbm contamination: CONTAMINATED" in text
    assert "codebase-memory-mcp uninstall" in text


def test_doctor_flags_cbm_in_global_settings(tmp_path):
    target = tmp_path / "proj"
    home = tmp_path / "home"
    write_resolved(target, mcps=["db-access"])
    settings = home / ".claude" / "settings.json"
    settings.parent.mkdir(parents=True)
    settings.write_text(json.dumps({"hooks": {"PreToolUse": [
        {"matcher": "Grep|Glob",
         "hooks": [{"command": "codebase-memory-mcp hook run"}]}]}}),
        encoding="utf-8")
    status = build_doctor_status(target, home)
    assert status.cbm_contamination == "contaminated"
    assert any("settings.json" in item for item in status.contamination_findings)


def test_doctor_flags_cbm_in_project_config(tmp_path):
    target = tmp_path / "proj"
    home = tmp_path / "home"
    write_resolved(target, mcps=["db-access"])
    mcp_json = target / ".mcp.json"
    mcp_json.write_text(json.dumps(
        {"mcpServers": {"codebase-memory-mcp": {"command": "codebase-memory-mcp"}}}),
        encoding="utf-8")
    status = build_doctor_status(target, home)
    assert status.cbm_contamination == "contaminated"


def test_doctor_contamination_clean(tmp_path):
    target = tmp_path / "proj"
    home = tmp_path / "home"
    write_resolved(target, mcps=["db-access"])
    status = build_doctor_status(target, home)
    assert status.cbm_contamination == "clean"
    assert status.contamination_findings == []
    assert "cbm contamination: CLEAN" in render_report(status)


def test_doctor_contamination_never_mutates(tmp_path):
    target = tmp_path / "proj"
    home = tmp_path / "home"
    write_resolved(target, mcps=["db-access"])
    hook = home / ".claude" / "hooks" / "cbm-gate.sh"
    hook.parent.mkdir(parents=True)
    payload = "# Installed by codebase-memory-mcp\n"
    hook.write_text(payload, encoding="utf-8")
    build_doctor_status(target, home)
    assert hook.read_text(encoding="utf-8") == payload
