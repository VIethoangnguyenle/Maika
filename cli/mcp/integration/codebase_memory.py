"""Codebase Memory adapter — verified tool surface and support-call records.

CBM is conditional support (M2 skill contracts): every call must carry the
activating trigger and a reason, and is bound to the raw response by hash.
``semantic_query`` is an input field on ``search_graph``; it is never a tool.
"""

from __future__ import annotations

import hashlib
import json

from cli.mcp.integration.base import hash_payload

PROVIDER_ID = "codebase-memory-mcp"
CAPABILITY = "semantic_code_search"
TOOLS = {
    "index_repository", "search_graph", "query_graph", "trace_path",
    "get_code_snippet", "get_graph_schema", "get_architecture", "search_code",
    "list_projects", "delete_project", "index_status", "detect_changes",
    "manage_adr", "ingest_traces",
}
REQUIRED_DISCOVERY_TOOLS = {
    "search_graph", "index_status", "list_projects", "query_graph", "trace_path",
}


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
    by_name = {
        str(item.get("name")): item for item in tools if isinstance(item, dict) and item.get("name")
    }
    missing = sorted(TOOLS - set(by_name))
    unexpected = sorted(set(by_name) - TOOLS)
    semantic = by_name.get("search_graph", {}).get("inputSchema", {})
    semantic_arg = (semantic.get("properties") or {}).get("semantic_query") or {}
    if semantic_arg.get("type") != "array":
        missing.append("search_graph.semantic_query[array]")
    if "semantic_query" in by_name:
        return {"status": "degraded", "reason": "semantic_query advertised as standalone tool"}
    observed_hash = tool_surface_hash(tools)
    hash_changed = bool(expected_tool_surface_hash and observed_hash != expected_tool_surface_hash)
    return {
        "status": "ready" if not missing and not unexpected and not hash_changed else "degraded",
        "missing": missing,
        "unexpected": unexpected,
        "tool_surface_hash": observed_hash,
        "prior_probe_valid": not hash_changed,
        "tools": sorted(by_name),
    }


def build_support_call(*, tool: str, trigger: str, reason: str, raw: bytes | str) -> dict:
    if not trigger or not str(reason or "").strip():
        raise ValueError("CBM support call requires trigger and reason (plan §8)")
    if tool not in TOOLS:
        raise ValueError(f"unknown Codebase Memory tool {tool!r}")
    return {
        "provider_id": PROVIDER_ID,
        "capability": CAPABILITY,
        "tool": tool,
        "trigger": trigger,
        "reason": reason,
        "response_hash": hash_payload(raw),
    }


def normalize_response(tool: str, raw: bytes | str) -> dict:
    """Normalize CBM output without claiming immutable snapshot isolation."""
    text = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        payload = {}
    observation = {
        "provider_id": PROVIDER_ID,
        "tool": tool,
        "response_hash": hash_payload(raw),
        "authority": "semantic_index_structure",
        "canonical": False,
        "status": "success",
        "provider_snapshot": {"index_generation": "unverified"},
    }
    if tool == "index_status":
        git = payload.get("git") if isinstance(payload.get("git"), dict) else {}
        snapshot = {
            "index_generation": "unverified",
            "head": git.get("head_sha") or payload.get("head") or "unverified",
            "working_tree_state": payload.get("working_tree_state") or "unverified",
            "nodes": payload.get("nodes", "unverified"),
            "edges": payload.get("edges", "unverified"),
            "index_timestamp": payload.get("index_timestamp") or "unverified",
        }
        observation.update(
            project=payload.get("project") or "unverified",
            source_revision=snapshot["head"],
            working_tree_state=snapshot["working_tree_state"],
            provider_snapshot=snapshot,
        )
    return observation
