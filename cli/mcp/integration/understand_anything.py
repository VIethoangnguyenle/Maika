"""Understand-Anything adapter — normalize black-box responses (plan §13, E6).

UA tools return human text except ``get_graph_metadata`` (structured JSON
snapshot). Normalization is defensive: known metadata keys are lifted when
present; text responses are wrapped with a truncation heuristic. The adapter
never re-interprets trace content — that stays worker-authored and is bound
to these records by response hash.
"""

from __future__ import annotations

import json
import re

from cli.mcp.integration.base import hash_payload

PROVIDER_ID = "understand-anything"
METADATA_TOOL = "get_graph_metadata"

# Prose truncation markers observed in UA text output (defensive heuristic;
# UA is a black box, so absence of a marker is not proof of completeness).
_TRUNCATION = re.compile(r"\btruncated\b|\.\.\.\s*\(\d+\s+more\b", re.IGNORECASE)

_GRAPH_KEYS = ("project", "graph_commit", "repository_head", "freshness", "health")


def _decode(raw: bytes | str) -> str:
    return raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw


def normalize_response(tool: str, raw: bytes | str) -> dict:
    """Return a provider observation entry; metadata responses also carry a
    ``graph`` block lifted from the structured snapshot."""
    text = _decode(raw)
    observation = {
        "provider_id": PROVIDER_ID,
        "tool": tool,
        "response_hash": hash_payload(raw),
        "truncated": bool(_TRUNCATION.search(text)),
    }
    if tool == METADATA_TOOL:
        try:
            snapshot = json.loads(text)
        except json.JSONDecodeError:
            snapshot = None
        if isinstance(snapshot, dict):
            graph = {key: snapshot.get(key) for key in _GRAPH_KEYS if snapshot.get(key) is not None}
            if graph:
                observation["graph"] = graph
    return observation
