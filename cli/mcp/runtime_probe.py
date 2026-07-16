"""Runtime MCP surface probe backed by Maika's existing controlled bridge."""
from __future__ import annotations

import importlib.util
import re
import subprocess
from pathlib import Path


def sanitize_probe_error(error: str) -> str:
    """Collapse provider-controlled errors to secret-safe diagnostic categories."""
    normalized = str(error or "").lower()
    if "initialize" in normalized:
        suffix = " (timed out)" if "timed out" in normalized else ""
        return f"MCP initialize failed{suffix}"
    if "tools/list" in normalized:
        suffix = " (timed out)" if "timed out" in normalized else ""
        return f"MCP tools/list failed{suffix}"
    if "bridge" in normalized and "load" in normalized:
        return "MCP bridge could not be loaded"
    if "launch" in normalized:
        return "MCP server launch failed"
    return "MCP runtime probe failed"


def _load_bridge(bridge_path: Path):
    spec = importlib.util.spec_from_file_location("maika_mcp_runtime_probe", bridge_path)
    if spec is None or spec.loader is None:
        return None, "MCP bridge could not be loaded"
    try:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception:
        return None, "MCP bridge could not be loaded"
    return module, ""


def _call(server: dict, bridge_path: Path, operation: str,
          tool_name: str | None = None, arguments: dict | None = None):
    module, error = _load_bridge(bridge_path)
    if error:
        return None, error

    try:
        if "command" in server:
            response, error = module.call_stdio(
                server, operation, tool_name, arguments or {},
            )
        else:
            response, error = module.call_http(
                server, operation, tool_name, arguments or {},
            )
    except FileNotFoundError:
        return None, "MCP server launch failed"
    except Exception:
        return None, "MCP runtime probe failed"
    if error:
        return None, sanitize_probe_error(error)
    return ((response or {}).get("result") or None), ""


def probe_tools_list(server: dict, bridge_path: Path) -> tuple[dict | None, str]:
    """Initialize the matched server and return its real ``tools/list`` result."""
    return _call(server, bridge_path, "tools-list")


def probe_tool_call(server: dict, bridge_path: Path, tool_name: str,
                    arguments: dict) -> tuple[dict | None, str]:
    """Run one bounded read/maintenance call through the controlled bridge."""
    return _call(server, bridge_path, "tools-call", tool_name, arguments)


def probe_serena_version(server: dict) -> tuple[str, str]:
    """Read the configured Serena executable's version without exposing output."""
    command = str(server.get("command") or "serena")
    try:
        result = subprocess.run(
            [command, "--version"], capture_output=True, text=True,
            check=False, timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "", "Serena version probe failed"
    match = re.search(r"(?<!\d)(\d+\.\d+\.\d+)(?!\d)", result.stdout + result.stderr)
    if result.returncode != 0 or match is None:
        return "", "Serena version probe failed"
    return match.group(1), ""
