"""AgentMemory proxy-only readiness and tool-surface policy."""

from __future__ import annotations

import hashlib
import json

from cli.mcp.integration.base import hash_payload


PROVIDER_ID = "agent-memory"
REQUIRED_TOOLS = {"memory_smart_search", "memory_recall", "memory_sessions"}
PROXY_TOOLS = REQUIRED_TOOLS | {"memory_save", "memory_governance_delete"}


def _surface_hash(names: set[str]) -> str:
    raw = json.dumps(sorted(names), separators=(",", ":"))
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def assess_readiness(snapshot: dict, *, expected_mode: str = "proxy",
                     expected_tool_surface_hash: str = "") -> dict:
    tools = snapshot.get("tools") if isinstance(snapshot, dict) else None
    names = {
        str(item.get("name")) if isinstance(item, dict) else str(item)
        for item in (tools or [])
        if (isinstance(item, str) and item) or (isinstance(item, dict) and item.get("name"))
    }
    reasons = []
    if snapshot.get("mode") != expected_mode:
        reasons.append(f"expected {expected_mode} mode, got {snapshot.get('mode') or 'unknown'}")
    missing = sorted(PROXY_TOOLS - names)
    if missing:
        reasons.append(f"missing required tools: {missing}")
    unexpected = sorted(names - PROXY_TOOLS)
    if snapshot.get("mode") == expected_mode and unexpected:
        reasons.append(f"unreviewed proxy tools: {unexpected}")
    if not snapshot.get("runtime_version"):
        reasons.append("runtime version unavailable")
    identity = snapshot.get("store_id") or snapshot.get("server_instance_id")
    identity_status = "verified" if identity else "unverified"
    if identity_status == "unverified":
        reasons.append("server/store identity unverified")
    observed_hash = _surface_hash(names)
    hash_changed = bool(expected_tool_surface_hash and observed_hash != expected_tool_surface_hash)
    if hash_changed:
        reasons.append("tool surface changed since the prior capability probe")
    return {
        "status": "ready" if not reasons else "degraded",
        "mode": snapshot.get("mode") or "unknown",
        "resolved_url": snapshot.get("resolved_url") or "",
        "runtime_version": snapshot.get("runtime_version") or "",
        "identity_status": identity_status,
        "tool_surface_hash": observed_hash,
        "prior_probe_valid": not hash_changed,
        "missing": missing,
        "unexpected": unexpected,
        "degradation_reasons": reasons,
    }


def normalize_response(tool: str, raw: bytes | str) -> dict:
    """Treat recalled memory as historical candidate evidence, never authority."""
    text = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        payload = {}
    runtime_version = payload.get("runtime_version") or "unverified"
    identity = payload.get("store_id") or payload.get("server_instance_id")
    reasons = [] if identity else ["server/store identity unverified"]
    return {
        "provider_id": PROVIDER_ID,
        "tool": tool,
        "response_hash": hash_payload(raw),
        "provider_runtime_version": runtime_version,
        "project": payload.get("project") or "unverified",
        "source_revision": "unverified",
        "working_tree_state": "unverified",
        "provider_snapshot": {
            "identity": identity or "unverified",
            "agent_id": payload.get("agentId") or payload.get("agent_id") or "unverified",
            "agent_id_authorizes": False,
        },
        "authority": "historical_context",
        "classification": "candidate",
        "canonical": False,
        "status": "degraded" if reasons else "success",
        "degradation_reasons": reasons,
    }
