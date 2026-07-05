"""MCP doctor status and report generation."""

import json
import os
import shutil
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from cli.mcp.adapters import get_mcp_adapter
from cli.mcp.config import load_mcp_config, redact_mapping, selected_server_matches
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
class DoctorStatus:
    platform: str
    framework_root: str
    selected_mcps: list[str]
    config_path: Path | None
    native_state: str
    matched: list[str]
    missing: list[str]
    bridge_state: str
    recommendation: str
    redacted_servers: dict = field(default_factory=dict)
    setup_reports: dict = field(default_factory=dict)
    memory_daemon: str = "not-selected"   # not-selected | running | down
    memory_daemon_url: str = ""


def _setup_reports(target: Path, home: Path, maika_root, platform: str,
                   selected: list, matched: list) -> dict:
    if maika_root is None:
        return {}
    manifest = load_manifest(Path(maika_root))
    caps = manifest.get("mcp_capabilities", {})
    reports = {}
    for key in selected:
        capability = caps.get(key, {})
        if not ua_setup.has_setup(capability):
            continue
        setup = capability["setup"]
        wired = "wired: ✓ configured" if key in matched else "wired: ✗ see MCP_SETUP.md"
        reports[key] = (
            [ua_setup.engine_status_line(setup, platform, home)]
            + ua_setup.graph_status_lines(setup, target)
            + [wired]
        )
    return reports


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


def build_doctor_status(target: Path, home: Path, maika_root=None) -> DoctorStatus:
    resolved = load_resolved_config(target)
    if resolved is None:
        raise ValueError(f"No Maika resolved-config.yaml found under {target}")
    platform = resolved.get("platform", "generic")
    framework_root = resolved.get("framework_root", get_mcp_adapter(platform).framework_root)
    selected = list(resolved.get("mcps") or [])
    adapter = get_mcp_adapter(platform)

    memory_daemon, memory_daemon_url = _memory_daemon_state(selected)

    best_config = None
    for candidate in adapter.config_candidates(target, home):
        config = load_mcp_config(candidate)
        if config.valid:
            best_config = config
            break

    if best_config is None:
        return DoctorStatus(
            platform=platform,
            framework_root=framework_root,
            selected_mcps=selected,
            config_path=None,
            native_state="unavailable",
            matched=[],
            missing=selected,
            bridge_state="not-probed",
            recommendation="create or link a valid MCP config with maika doctor mcp --fix",
            setup_reports=_setup_reports(target, home, maika_root, platform, selected, []),
            memory_daemon=memory_daemon,
            memory_daemon_url=memory_daemon_url,
        )

    matched, missing = selected_server_matches(best_config, selected)
    if matched and not missing:
        native_state = "configured"
    elif matched:
        native_state = "partial"
    else:
        native_state = "unavailable"

    bridge_state = "not-probed"
    redacted_servers = {name: redact_mapping(best_config.servers[name]) for name in matched}
    return DoctorStatus(
        platform=platform,
        framework_root=framework_root,
        selected_mcps=selected,
        config_path=best_config.path,
        native_state=native_state,
        matched=matched,
        missing=missing,
        bridge_state=bridge_state,
        recommendation="run native MCP in the IDE/CLI and inspect tool availability",
        redacted_servers=redacted_servers,
        setup_reports=_setup_reports(target, home, maika_root, platform, selected, matched),
        memory_daemon=memory_daemon,
        memory_daemon_url=memory_daemon_url,
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
        f"- matched: {matched}\n"
        f"- missing: {missing}\n"
        + _render_memory_daemon(status)
        + f"- Recommendation: {status.recommendation}\n"
        + _render_setup_reports(status.setup_reports)
        + _render_matched_config(status.redacted_servers)
    )


def _render_memory_daemon(status: DoctorStatus) -> str:
    if status.memory_daemon == "not-selected":
        return ""
    if status.memory_daemon == "running":
        return f"- agent-memory daemon: RUNNING ({status.memory_daemon_url})\n"
    return f"- agent-memory daemon: DOWN ({status.memory_daemon_url}) — {MEMORY_DAEMON_HINT}\n"


def _render_setup_reports(setup_reports: dict) -> str:
    if not setup_reports:
        return ""
    out = ["\n## Setup verification\n"]
    for key, lines in setup_reports.items():
        out.append(f"\n### {key}\n")
        out.extend(f"- {line}\n" for line in lines)
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
    if destination.exists() and destination.read_text(encoding="utf-8").strip():
        backup = destination.with_name(destination.name + ".bak")
        shutil.copy2(destination, backup)
    shutil.copy2(source, destination)
    return destination
