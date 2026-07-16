"""MCP doctor status and report generation."""

import json
import os
import shutil
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from cli.mcp.adapters import get_mcp_adapter
from cli.mcp.config import load_mcp_config, redact_mapping, selected_server_matches
from cli.mcp.integration import serena
from cli.mcp.runtime_probe import (
    probe_serena_version, probe_tool_call, probe_tools_list, sanitize_probe_error,
)
from cli.mcp import ua_setup
from cli.scaffold import load_resolved_config, load_manifest

AGENTMEMORY_DEFAULT_URL = "http://localhost:3111"
# Hint shown when the daemon is down. Doctor never starts the daemon itself
# (provider boundary): the end project owns the agentmemory lifecycle.
MEMORY_DAEMON_HINT = (
    "start: npm i -g @agentmemory/agentmemory && agentmemory "
    "(viewer :3113; deep check: agentmemory doctor)"
)


@dataclass(frozen=True)
class PlatformDoctorStatus:
    platform: str
    config_path: Path | None
    native_state: str
    matched: list[str]
    missing: list[str]
    bridge_state: str
    health_state: str
    redacted_servers: dict = field(default_factory=dict)
    setup_reports: dict = field(default_factory=dict)


@dataclass(frozen=True)
class DoctorStatus:
    platform: str
    framework_root: str
    selected_mcps: list[str]
    config_path: Path | None
    native_state: str
    matched: list[str]
    missing: list[str]
    bridge_state: str
    health_state: str
    recommendation: str
    redacted_servers: dict = field(default_factory=dict)
    setup_reports: dict = field(default_factory=dict)
    memory_daemon: str = "not-selected"   # not-selected | running | down
    memory_daemon_url: str = ""
    memory_governance: str = "not-selected"  # not-selected | controlled | degraded
    governance_warnings: list[str] = field(default_factory=list)
    platform_reports: dict[str, PlatformDoctorStatus] = field(default_factory=dict)


def _safe_probe_error(error: str) -> str:
    """Keep provider-controlled text and config secrets out of doctor reports."""
    return sanitize_probe_error(error)


def _serena_contract_line(snapshot: dict | None, error: str) -> str:
    if error:
        return f"contract: DEGRADED — {_safe_probe_error(error)}"
    result = serena.validate_tools_list(
        snapshot,
        expected_tool_surface_hash=serena.SERENA_READONLY_V1_TOOL_SURFACE_HASH,
    )
    if result["status"] == "ready":
        return f"contract: READY (8 Phase 1 tools; {result['tool_surface_hash']})"

    problems = []
    if result.get("forbidden"):
        problems.append(f"forbidden: {', '.join(result['forbidden'])}")
    if result.get("unexpected"):
        problems.append(f"unexpected: {', '.join(result['unexpected'])}")
    if result.get("missing"):
        problems.append(f"missing: {', '.join(result['missing'])}")
    if result.get("duplicates"):
        problems.append(f"duplicates: {', '.join(result['duplicates'])}")
    if result.get("prior_probe_valid") is False:
        problems.append("schema drift from pinned Serena 1.5.3 surface")
    if result.get("reason"):
        problems.append(result["reason"])
    return f"contract: DEGRADED — {'; '.join(problems) or 'invalid tools/list result'}"


def _serena_project_line(target: Path, server: dict) -> tuple[str, bool]:
    args = [str(item) for item in (server.get("args") or [])]
    try:
        configured_root = Path(args[args.index("--project") + 1]).resolve()
    except (ValueError, IndexError, OSError):
        return "project: DEGRADED — native server lacks an activated project", False
    if configured_root != target.resolve():
        return "project: DEGRADED — native server activates a different project", False
    path = target / ".serena" / "project.yml"
    try:
        config = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return "project: DEGRADED — .serena/project.yml missing or invalid", False
    raw = config.get("languages") or config.get("language") or []
    if isinstance(raw, str):
        languages = [raw]
    elif isinstance(raw, dict):
        languages = [str(item) for item in raw]
    elif isinstance(raw, list):
        languages = [str(item) for item in raw if str(item).strip()]
    else:
        languages = []
    if not languages:
        return "project: DEGRADED — no selected language backend", False
    return f"project: READY ({', '.join(languages)} backend)", True


def _tool_call_ready(result: dict | None, error: str) -> bool:
    if error or not isinstance(result, dict) or result.get("isError") is True:
        return False
    return bool(result.get("content") or result.get("structuredContent"))


def _serena_smoke_line(server: dict, bridge_path: Path) -> str:
    arguments = {
        "relative_path": ".maika/tools/mcp-bridge/mcp_client.py",
        "depth": 0,
    }
    result, error = probe_tool_call(
        server, bridge_path, "get_symbols_overview", arguments,
    )
    if _tool_call_ready(result, error):
        return "symbol smoke: READY"
    probe_tool_call(server, bridge_path, "restart_language_server", {})
    result, error = probe_tool_call(
        server, bridge_path, "get_symbols_overview", arguments,
    )
    if _tool_call_ready(result, error):
        return "symbol smoke: READY (recovered after one language-server restart)"
    return "symbol smoke: DEGRADED — symbol backend unavailable after one recovery"


def _setup_reports(target: Path, home: Path, maika_root, platform: str,
                   selected: list, matched: list,
                   servers: dict | None = None) -> tuple[dict, bool]:
    if maika_root is None:
        return {}, False
    manifest = load_manifest(Path(maika_root))
    caps = manifest.get("mcp_capabilities", {})
    reports = {}
    probed = False
    servers = servers or {}
    for key in selected:
        capability = caps.get(key, {})
        if not ua_setup.has_setup(capability):
            continue
        setup = capability["setup"]
        engine_ready = ua_setup.resolve_engine_check(setup, platform, home)
        wired = "wired: ✓ configured" if key in matched else "wired: ✗ see MCP_SETUP.md"
        lines = (
            [ua_setup.engine_status_line(setup, platform, home)]
            + ua_setup.graph_status_lines(setup, target)
            + [wired]
        )
        if key == serena.PROVIDER_ID:
            if not engine_ready:
                lines.append("contract: DEGRADED — engine not installed")
            elif key not in matched:
                lines.append("contract: DEGRADED — native server not matched")
            else:
                server = servers[key]
                version, version_error = probe_serena_version(server)
                if version_error or version != "1.5.3":
                    lines.append("version: DEGRADED — expected Serena 1.5.3")
                else:
                    lines.append("version: READY (Serena 1.5.3)")
                    project_line, project_ready = _serena_project_line(target, server)
                    lines.append(project_line)
                    if project_ready:
                        probed = True
                        bridge_path = (
                            Path(maika_root) / ".maika" / "tools" / "mcp-bridge"
                            / "mcp_client.py"
                        )
                        try:
                            snapshot, error = probe_tools_list(server, bridge_path)
                        except Exception:
                            snapshot, error = None, "MCP runtime probe failed"
                        contract_line = _serena_contract_line(snapshot, error)
                        lines.append(contract_line)
                        if contract_line.startswith("contract: READY"):
                            try:
                                lines.append(_serena_smoke_line(server, bridge_path))
                            except Exception:
                                lines.append(
                                    "symbol smoke: DEGRADED — symbol backend unavailable"
                                )
        reports[key] = lines
    return reports, probed


def _probe_memory_daemon(url: str, timeout: float = 2.0) -> bool:
    """Any HTTP response (even 4xx/5xx) counts as alive — no dependency on a
    specific /health route. Connection refused, timeout, or a malformed URL
    counts as down."""
    try:
        urllib.request.urlopen(url, timeout=timeout)
        return True
    except urllib.error.HTTPError:
        return True
    except Exception:
        return False


def _memory_daemon_state(selected: list) -> tuple[str, str]:
    if "agent-memory" not in selected:
        return "not-selected", ""
    url = os.environ.get("AGENTMEMORY_URL") or AGENTMEMORY_DEFAULT_URL
    return ("running" if _probe_memory_daemon(url) else "down"), url


def _memory_governance_state(selected: list, home: Path) -> tuple[str, list[str]]:
    """Report user-global auto-capture; never mutate host-owned hook files."""
    if "agent-memory" not in selected:
        return "not-selected", []
    warnings = []
    for name in ("AGENTMEMORY_AUTO_CAPTURE", "AGENTMEMORY_INJECT_CONTEXT",
                 "AGENTMEMORY_STOP_SUMMARY"):
        if str(os.environ.get(name) or "").lower() in {"1", "true", "yes", "on"}:
            warnings.append(f"{name} enables host-level automatic memory behavior")
    candidates = (
        home / ".claude" / "settings.json",
        home / ".codex" / "settings.json",
        home / ".gemini" / "settings.json",
        home / ".config" / "agentmemory" / "config.json",
    )
    for path in candidates:
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8").lower()
        except OSError:
            continue
        if "agentmemory" in text and any(word in text for word in (
                "hook", "auto_capture", "inject", "stop_summary")):
            warnings.append(f"possible AgentMemory auto-capture hook in {path}")
    return ("degraded" if warnings else "controlled"), warnings


def _platform_status(target: Path, home: Path, maika_root, platform: str,
                     selected: list[str]) -> PlatformDoctorStatus:
    adapter = get_mcp_adapter(platform)
    best_config = None
    for candidate in adapter.config_candidates(target, home):
        config = load_mcp_config(candidate)
        if config.valid:
            best_config = config
            break

    if best_config is None:
        setup_reports, _ = _setup_reports(
            target, home, maika_root, platform, selected, [], {},
        )
        return PlatformDoctorStatus(
            platform=platform,
            config_path=None,
            native_state="unavailable",
            matched=[],
            missing=selected,
            bridge_state="not-probed",
            health_state="degraded",
            setup_reports=setup_reports,
        )

    matched, missing = selected_server_matches(best_config, selected)
    if matched and not missing:
        native_state = "configured"
    elif matched:
        native_state = "partial"
    else:
        native_state = "unavailable"

    setup_reports, probed = _setup_reports(
        target, home, maika_root, platform, selected, matched, best_config.servers,
    )
    bridge_state = "probed" if probed else "not-probed"
    redacted_servers = {name: redact_mapping(best_config.servers[name]) for name in matched}
    serena_lines = setup_reports.get(serena.PROVIDER_ID) or []
    serena_ready = (
        serena.PROVIDER_ID not in selected
        or (
            any(line.startswith("version: READY") for line in serena_lines)
            and any(line.startswith("project: READY") for line in serena_lines)
            and any(line.startswith("contract: READY") for line in serena_lines)
            and any(line.startswith("symbol smoke: READY") for line in serena_lines)
        )
    )
    return PlatformDoctorStatus(
        platform=platform,
        config_path=best_config.path,
        native_state=native_state,
        matched=matched,
        missing=missing,
        bridge_state=bridge_state,
        health_state="ready" if native_state == "configured" and serena_ready else "degraded",
        redacted_servers=redacted_servers,
        setup_reports=setup_reports,
    )


def build_doctor_status(target: Path, home: Path, maika_root=None) -> DoctorStatus:
    resolved = load_resolved_config(target)
    if resolved is None:
        raise ValueError(f"No Maika resolved-config.yaml found under {target}")
    selected = list(resolved.get("mcps") or [])
    from cli.config import project as project_config
    canonical = project_config.load(target)
    enabled = list((canonical.get("platforms") or {}).get("enabled") or [])
    if not enabled:
        enabled = [resolved.get("platform", "generic")]
    primary = (canonical.get("platforms") or {}).get("primary")
    if primary not in enabled:
        primary = resolved.get("platform") if resolved.get("platform") in enabled else enabled[0]
    platform_reports = {
        key: _platform_status(target, home, maika_root, key, selected)
        for key in enabled
    }
    primary_report = platform_reports[primary]
    states = [report.native_state for report in platform_reports.values()]
    if states and all(state == "configured" for state in states):
        native_state = "configured"
    elif states and all(state == "unavailable" for state in states):
        native_state = "unavailable"
    else:
        native_state = "partial"
    matched = [
        provider for provider in selected
        if all(provider in report.matched for report in platform_reports.values())
    ]
    missing = [provider for provider in selected if provider not in matched]
    bridge_states = [report.bridge_state for report in platform_reports.values()]
    if bridge_states and all(state == "probed" for state in bridge_states):
        bridge_state = "probed"
    elif any(state == "probed" for state in bridge_states):
        bridge_state = "partial"
    else:
        bridge_state = "not-probed"
    health_state = (
        "ready" if all(report.health_state == "ready" for report in platform_reports.values())
        else "degraded"
    )
    memory_daemon, memory_daemon_url = _memory_daemon_state(selected)
    memory_governance, governance_warnings = _memory_governance_state(selected, home)
    return DoctorStatus(
        platform=primary,
        framework_root=get_mcp_adapter(primary).framework_root,
        selected_mcps=selected,
        config_path=primary_report.config_path,
        native_state=native_state,
        matched=matched,
        missing=missing,
        bridge_state=bridge_state,
        health_state=health_state,
        recommendation="run native MCP in every enabled IDE/CLI and inspect tool availability",
        redacted_servers=primary_report.redacted_servers,
        setup_reports=primary_report.setup_reports,
        memory_daemon=memory_daemon,
        memory_daemon_url=memory_daemon_url,
        memory_governance=memory_governance,
        governance_warnings=governance_warnings,
        platform_reports=platform_reports,
    )


def render_report(status: DoctorStatus) -> str:
    config_path = status.config_path.as_posix() if status.config_path else "none"
    matched = ", ".join(status.matched) if status.matched else "none"
    missing = ", ".join(status.missing) if status.missing else "none"
    selected = ", ".join(status.selected_mcps) if status.selected_mcps else "none"
    return (
        "# MCP Doctor Report\n\n"
        f"- Platform: {status.platform}\n"
        f"- Framework root: {status.framework_root}\n"
        f"- Selected MCPs: {selected}\n"
        f"- Config path: {config_path}\n"
        f"- native: {status.native_state}\n"
        f"- bridge: {status.bridge_state}\n"
        f"- health: {status.health_state}\n"
        f"- matched: {matched}\n"
        f"- missing: {missing}\n"
        + _render_memory_daemon(status)
        + _render_governance(status)
        + f"- Recommendation: {status.recommendation}\n"
        + (_render_setup_reports(status.setup_reports)
           if len(status.platform_reports) <= 1 else _render_platform_reports(status))
        + (_render_matched_config(status.redacted_servers)
           if len(status.platform_reports) <= 1 else "")
    )


def _render_memory_daemon(status: DoctorStatus) -> str:
    if status.memory_daemon == "not-selected":
        return ""
    if status.memory_daemon == "running":
        return f"- agent-memory daemon: RUNNING ({status.memory_daemon_url})\n"
    return f"- agent-memory daemon: DOWN ({status.memory_daemon_url}) — {MEMORY_DAEMON_HINT}\n"


def _render_governance(status: DoctorStatus) -> str:
    if status.memory_governance == "not-selected":
        return ""
    out = [f"- agent-memory governance: {status.memory_governance.upper()}\n"]
    out.extend(f"  - WARNING: {warning}\n" for warning in status.governance_warnings)
    return "".join(out)


def _render_setup_reports(setup_reports: dict) -> str:
    if not setup_reports:
        return ""
    out = ["\n## Setup verification\n"]
    for key, lines in setup_reports.items():
        out.append(f"\n### {key}\n")
        out.extend(f"- {line}\n" for line in lines)
    return "".join(out)


def _render_platform_reports(status: DoctorStatus) -> str:
    out = ["\n## Platform health\n"]
    for key, report in status.platform_reports.items():
        out.extend([
            f"\n### Platform: {get_mcp_adapter(key).platform.replace('-', ' ').title()}\n",
            f"- Config path: {report.config_path.as_posix() if report.config_path else 'none'}\n",
            f"- native: {report.native_state}\n",
            f"- bridge: {report.bridge_state}\n",
            f"- health: {report.health_state}\n",
            f"- matched: {', '.join(report.matched) if report.matched else 'none'}\n",
            f"- missing: {', '.join(report.missing) if report.missing else 'none'}\n",
        ])
        for provider, lines in report.setup_reports.items():
            out.append(f"\n#### {provider}\n")
            out.extend(f"- {line}\n" for line in lines)
        if report.redacted_servers:
            body = json.dumps(
                report.redacted_servers, indent=2, ensure_ascii=False, sort_keys=True,
            )
            out.append(
                "\n#### Matched server config (redacted)\n\n"
                f"```json\n{body}\n```\n"
            )
    return "".join(out)


def _render_matched_config(redacted_servers: dict) -> str:
    if not redacted_servers:
        return ""
    body = json.dumps(redacted_servers, indent=2, ensure_ascii=False, sort_keys=True)
    return f"\n## Matched server config (redacted)\n\n```json\n{body}\n```\n"


def write_report(target: Path, status: DoctorStatus) -> Path:
    report = target / status.framework_root / "knowledge" / "active" / "mcp-doctor-report.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(render_report(status), encoding="utf-8")
    return report


def apply_fix(target: Path, home: Path, assume_yes: bool) -> Path | None:
    resolved = load_resolved_config(target)
    if resolved is None:
        raise ValueError(f"No Maika resolved-config.yaml found under {target}")
    platform = resolved.get("platform", "generic")
    if platform != "antigravity":
        return None
    adapter = get_mcp_adapter(platform)
    candidates = adapter.config_candidates(target, home)
    destination = next(item.path for item in candidates if item.scope == "cli")
    source = None
    for candidate in candidates:
        if candidate.scope == "cli":
            continue
        config = load_mcp_config(candidate)
        if config.valid:
            source = config.path
            break
    if source is None:
        return None
    if not assume_yes:
        answer = input(f"Copy {source} to {destination}? [y/N]: ").strip().lower()
        if answer != "y":
            return None
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return destination
