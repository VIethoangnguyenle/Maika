"""Codebase Memory adapter — conditional support-call records (plan §13).

CBM is conditional support (M2 skill contracts): every call must carry the
activating trigger and a reason, and is bound to the raw response by hash.
CBM tool names are deliberately unverified (no tested snapshot), so no tool
check happens here.
"""

from __future__ import annotations

from cli.mcp.integration.base import hash_payload

PROVIDER_ID = "codebase-memory-mcp"
CAPABILITY = "semantic_code_search"


def build_support_call(*, tool: str, trigger: str, reason: str, raw: bytes | str) -> dict:
    if not trigger or not str(reason or "").strip():
        raise ValueError("CBM support call requires trigger and reason (plan §8)")
    return {
        "provider_id": PROVIDER_ID,
        "capability": CAPABILITY,
        "tool": tool,
        "trigger": trigger,
        "reason": reason,
        "response_hash": hash_payload(raw),
    }
