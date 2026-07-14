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

SUPPORTED_CONTRACT_VERSIONS = {1}


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
        "authority": "domain_semantics",
        "canonical": False,
    }
    if tool == METADATA_TOOL:
        try:
            snapshot = json.loads(text)
        except json.JSONDecodeError:
            snapshot = None
        if isinstance(snapshot, dict):
            version = snapshot.get("contract_version", 1)
            observation["provider_contract_version"] = version
            observation["provider_runtime_version"] = (
                snapshot.get("runtime_version") or "unverified"
            )
            if version not in SUPPORTED_CONTRACT_VERSIONS:
                observation["status"] = "degraded"
                observation["degradation_reasons"] = [
                    f"unsupported metadata contract version {version!r}"
                ]
                return observation
            graph_data = snapshot.get("graph") if isinstance(snapshot.get("graph"), dict) else {}
            repository = (snapshot.get("repository")
                          if isinstance(snapshot.get("repository"), dict) else {})
            freshness_data = (snapshot.get("freshness")
                              if isinstance(snapshot.get("freshness"), dict) else {})
            health_data = (snapshot.get("health")
                           if isinstance(snapshot.get("health"), dict) else {})
            # Top-level aliases are accepted only for the legacy Maika fixture
            # window.  The canonical producer response is nested.
            graph = {
                "project": snapshot.get("project"),
                "graph_commit": graph_data.get("graph_commit") or snapshot.get("graph_commit"),
                "repository_head": repository.get("head") or snapshot.get("repository_head"),
                "freshness": freshness_data.get("status") or snapshot.get("freshness"),
                "health": health_data.get("status") or snapshot.get("health"),
            }
            missing = [key for key, value in graph.items() if value in {None, ""}]
            if missing:
                observation["status"] = "degraded"
                observation["degradation_reasons"] = [
                    "metadata missing critical provenance: " + ", ".join(missing)
                ]
            else:
                observation["status"] = "success"
                observation["graph"] = graph
        else:
            observation["status"] = "degraded"
            observation["degradation_reasons"] = ["metadata response is not valid JSON object"]
    return observation
