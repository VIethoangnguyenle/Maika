"""Runtime MCP surface probe backed by Maika's existing controlled bridge."""
from __future__ import annotations

import importlib.util
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


def probe_tools_list(server: dict, bridge_path: Path) -> tuple[dict | None, str]:
    """Initialize the matched server and return its real ``tools/list`` result."""
    spec = importlib.util.spec_from_file_location("maika_mcp_runtime_probe", bridge_path)
    if spec is None or spec.loader is None:
        return None, "MCP bridge could not be loaded"
    try:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception:
        return None, "MCP bridge could not be loaded"

    try:
        if "command" in server:
            response, error = module.call_stdio(server, "tools-list", None, {})
        else:
            response, error = module.call_http(server, "tools-list", None, {})
    except FileNotFoundError:
        return None, "MCP server launch failed"
    except Exception:
        return None, "MCP runtime probe failed"
    if error:
        return None, sanitize_probe_error(error)
    return ((response or {}).get("result") or None), ""
