"""Execute learning capabilities through configured MCP adapters when available."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from cli.mcp.doctor import build_doctor_status
from cli.platforms import get_platform
from cli.platforms.base import PlatformToolMappingError


def _load_bridge(target: Path, framework_root: str):
    path = target / framework_root / "tools" / "mcp-bridge" / "mcp_client.py"
    spec = importlib.util.spec_from_file_location("maika_learning_bridge", path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def _call(bridge, config: dict, operation: str, tool_name=None, arguments=None):
    arguments = arguments or {}
    if config.get("command"):
        return bridge.call_stdio(config, operation, tool_name, arguments)
    return bridge.call_http(config, operation, tool_name, arguments)


def _tools(response: dict | None) -> list[dict]:
    if not response:
        return []
    result = response.get("result") or {}
    inner = result.get("result") if isinstance(result.get("result"), dict) else result
    return inner.get("tools") or []


def _resolve_tool(tools: list[dict], concrete_mapping: str) -> str | None:
    names = [item.get("name") for item in tools if item.get("name")]
    return next((name for name in names if name == concrete_mapping or concrete_mapping.endswith(name)), None)


def build_learning_executors(target: Path, framework_root: str):
    """Return real MCP-backed save/refresh callables, or None for safe degradation."""
    target = Path(target)
    status = build_doctor_status(target, Path.home(), maika_root=Path(__file__).resolve().parents[1])
    if not status.config_path:
        return None, None
    bridge = _load_bridge(target, framework_root)
    platform = get_platform(status.platform)

    def executor(server_id: str, abstract_tool: str, arguments: dict):
        config = bridge.load_config(status.config_path, server_id)
        if not config:
            return {"ok": False, "verified": False, "status": "provider-not-configured"}
        listed, error = _call(bridge, config, "tools-list")
        if error:
            return {"ok": False, "verified": False, "status": "tools-list-failed", "error": error}
        try:
            concrete_mapping = platform.get_tool(abstract_tool)
        except PlatformToolMappingError:
            return {"ok": False, "verified": False, "status": "capability-tool-not-found"}
        tool_name = _resolve_tool(_tools(listed), concrete_mapping)
        if not tool_name:
            return {"ok": False, "verified": False, "status": "capability-tool-not-found"}
        result, error = _call(bridge, config, "tools-call", tool_name, arguments)
        return {"ok": not bool(error), "verified": not bool(error),
                "status": "executed" if not error else "execution-failed",
                "provider_id": server_id, "tool": tool_name,
                "result": result if not error else None, "error": error}

    memory_saver = None
    if "agent-memory" in status.selected_mcps and status.memory_daemon == "running":
        memory_saver = lambda item: executor(
            "agent-memory", "dynamic_memory_save",
            {"content": item.get("lesson") or item.get("statement"), "metadata": item},
        )
    graph_servers = [item for item in status.selected_mcps
                     if item == "understand-anything"]
    graph_refresher = None
    if graph_servers:
        def graph_refresher(request):
            # UA graphs are produced by the external Understand-Anything
            # producer; there is no MCP re-index tool to invoke.
            return {"verified": False, "status": "refresh-external",
                    "detail": "understand-anything graphs are re-indexed by the "
                              "external UA producer; re-run it and re-probe freshness"}
    return memory_saver, graph_refresher
