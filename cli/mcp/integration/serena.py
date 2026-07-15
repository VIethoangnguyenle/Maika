"""Serena adapter for Maika's pinned Phase 1 read-only semantic surface."""
from __future__ import annotations

import hashlib
import json

from cli.mcp.integration.base import hash_payload

PROVIDER_ID = "serena"
SERENA_READ_TOOLS = frozenset({
    "get_symbols_overview", "find_symbol", "find_referencing_symbols",
    "find_implementations", "find_declaration", "get_diagnostics_for_file",
    "get_diagnostics_for_symbol", "restart_language_server",
})
SERENA_FORBIDDEN_TOOLS = frozenset({
    "replace_symbol_body", "insert_after_symbol", "insert_before_symbol",
    "rename_symbol", "safe_delete_symbol", "create_text_file", "replace_content",
    "delete_lines", "replace_lines", "insert_at_line", "read_file", "list_dir",
    "find_file", "search_for_pattern", "execute_shell_command", "write_memory",
    "read_memory", "list_memories", "delete_memory", "rename_memory", "edit_memory",
    "activate_project", "remove_project", "onboarding", "initial_instructions",
    "open_dashboard", "serena_info",
})


def tool_surface_hash(tools: list[dict] | list[str]) -> str:
    normalized = sorted(
        [item if isinstance(item, dict) else {"name": str(item)} for item in tools],
        key=lambda item: str(item.get("name") or ""),
    )
    payload = json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_tools_list(snapshot: dict, *, expected_tool_surface_hash: str = "") -> dict:
    tools = snapshot.get("tools") if isinstance(snapshot, dict) else None
    if not isinstance(tools, list):
        return {"status": "degraded", "reason": "tools/list missing tools array"}
    names = {str(item.get("name")) for item in tools if isinstance(item, dict) and item.get("name")}
    missing = sorted(SERENA_READ_TOOLS - names)
    unexpected = sorted(names - SERENA_READ_TOOLS)
    forbidden = sorted(names & SERENA_FORBIDDEN_TOOLS)
    observed_hash = tool_surface_hash(tools)
    hash_changed = bool(expected_tool_surface_hash and observed_hash != expected_tool_surface_hash)
    ready = not missing and not unexpected and not forbidden and not hash_changed
    return {
        "status": "ready" if ready else "degraded",
        "missing": missing, "unexpected": unexpected, "forbidden": forbidden,
        "tool_surface_hash": observed_hash, "prior_probe_valid": not hash_changed,
        "tools": sorted(names),
    }


def normalize_response(tool: str, raw: bytes | str) -> dict:
    if tool not in SERENA_READ_TOOLS:
        raise ValueError(f"unknown Serena Phase 1 tool {tool!r}")
    return {
        "provider_id": PROVIDER_ID,
        "tool": tool,
        "response_hash": hash_payload(raw),
        "authority": "semantic_symbol_resolution",
        "canonical": False,
        "status": "success",
        "provider_snapshot": {"version": "1.5.3", "language_backend": "unverified"},
    }
