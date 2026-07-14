import json
from pathlib import Path

import yaml

from cli.commands.doctor import run_doctor_mcp
from cli.commands.init import run_init
from cli.mcp.doctor import build_doctor_status, render_report

MAIKA_ROOT = Path(__file__).resolve().parent.parent.parent


def write_resolved(target, platform="antigravity", mcps=None):
    root = ".agents" if platform in ("antigravity", "codex") else ".claude"
    path = target / root / "resolved-config.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(
        yaml.dump({"resolved": {
            "platform": platform,
            "framework_root": root,
            "mcps": mcps or ["codebase-memory-mcp"],
            "language": "python",
        }}),
        encoding="utf-8",
    )
    return path


def test_doctor_writes_report_for_missing_native_config(tmp_path):
    target = tmp_path / "proj"
    home = tmp_path / "home"
    write_resolved(target)

    run_doctor_mcp(str(target), fix=False, assume_yes=False, home=home)

    report = target / ".maika" / "knowledge" / "active" / "mcp-doctor-report.md"
    text = report.read_text(encoding="utf-8")
    assert "Platform: antigravity" in text
    assert "codebase-memory-mcp" in text
    assert "native: unavailable" in text
    assert "bridge: not-probed" in text


def test_doctor_matches_selected_server_in_existing_config(tmp_path):
    target = tmp_path / "proj"
    home = tmp_path / "home"
    write_resolved(target, mcps=["codebase-memory-mcp", "db-access"])
    cfg = target / ".agents" / "mcp_config.json"
    cfg.write_text(json.dumps({"mcpServers": {"codebase-memory-mcp": {"command": "npx"}}}), encoding="utf-8")

    run_doctor_mcp(str(target), fix=False, assume_yes=False, home=home)

    text = (target / ".maika" / "knowledge" / "active" / "mcp-doctor-report.md").read_text(encoding="utf-8")
    assert "matched: codebase-memory-mcp" in text
    assert "missing: db-access" in text
    assert "native: partial" in text
    assert "bridge: not-probed" in text


def test_build_doctor_status_marks_partial_native_state_for_partial_match(tmp_path):
    target = tmp_path / "proj"
    home = tmp_path / "home"
    write_resolved(target, mcps=["codebase-memory-mcp", "db-access"])
    cfg = target / ".agents" / "mcp_config.json"
    cfg.write_text(json.dumps({"mcpServers": {"codebase-memory-mcp": {"command": "npx"}}}), encoding="utf-8")

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
    write_resolved(target, mcps=["codebase-memory-mcp"])
    cfg = target / ".agents" / "mcp_config.json"
    cfg.write_text(
        json.dumps({"mcpServers": {"codebase-memory-mcp": {"command": "npx", "env": {"TOKEN": "supersecret"}}}}),
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
    write_resolved(target, platform="antigravity", mcps=["codebase-memory-mcp"])
    source = home / ".gemini" / "antigravity" / "mcp_config.json"
    source.parent.mkdir(parents=True)
    source.write_text(json.dumps({"mcpServers": {"codebase-memory-mcp": {"command": "npx"}}}), encoding="utf-8")

    run_doctor_mcp(str(target), fix=True, assume_yes=True, home=home)

    dest = home / ".gemini" / "antigravity-cli" / "mcp_config.json"
    assert dest.exists()
    assert json.loads(dest.read_text(encoding="utf-8"))["mcpServers"]["codebase-memory-mcp"]["command"] == "npx"


def test_doctor_fix_cleanly_replaces_existing_destination_without_backup(tmp_path):
    target = tmp_path / "proj"
    home = tmp_path / "home"
    write_resolved(target, platform="antigravity", mcps=["codebase-memory-mcp"])
    source = home / ".gemini" / "antigravity" / "mcp_config.json"
    source.parent.mkdir(parents=True)
    source.write_text(json.dumps({"mcpServers": {"codebase-memory-mcp": {"command": "npx"}}}), encoding="utf-8")
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
    write_resolved(target)  # mcps mặc định: codebase-memory-mcp

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
