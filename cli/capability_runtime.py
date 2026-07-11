"""Maika vNext capability registry and health/freshness router."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

from cli.assets import asset_root


READY = "ready"
DEGRADED = "degraded"
UNSUPPORTED = "unsupported"


def _default_registry_path() -> Path:
    """Resolve the capability registry via the canonical asset root.

    Bundle-aware so it works from a wheel install (packaged assets) as well as
    a source checkout — not hard-coded relative to this file's location.
    """
    return asset_root() / ".maika" / "profiles" / "capability-registry.yaml"


def load_capability_registry(path: Path | None = None) -> dict[str, dict[str, Any]]:
    """Load canonical capability definitions keyed by capability id."""
    source = path or _default_registry_path()
    doc = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
    caps = doc.get("capabilities") or {}
    if not isinstance(caps, dict) or not caps:
        raise ValueError(f"capability registry has no capabilities: {source}")
    return deepcopy(caps)


CANONICAL_CAPABILITIES = load_capability_registry()


def capability_ids() -> set[str]:
    return set(CANONICAL_CAPABILITIES)


def _evidence_to_capability(registry=None) -> dict[str, list[str]]:
    """Inverse index: evidence_type -> capability_ids that prefer it."""
    registry = registry or CANONICAL_CAPABILITIES
    index: dict[str, list[str]] = {}
    for cap_id in sorted(registry):
        for etype in registry[cap_id].get("preferred_evidence") or []:
            index.setdefault(etype, []).append(cap_id)
    return index


def route_question(required_evidence_types, *, registry=None) -> dict:
    """Resolve which capabilities can supply a question's required evidence types.

    Pure lookup over the canonical registry's ``preferred_evidence`` (no I/O,
    no provider probing — that is ``route_capability``'s job). Returns the set
    of candidate capabilities, the per-evidence-type mapping, and any evidence
    type no capability serves (``uncovered`` — the retrieval plan cannot cover
    it and must degrade or block).
    """
    index = _evidence_to_capability(registry)
    by_evidence: dict[str, list[str]] = {}
    capabilities: list[str] = []
    uncovered: list[str] = []
    for etype in required_evidence_types or []:
        serving = index.get(etype, [])
        by_evidence[etype] = list(serving)
        if serving:
            for cap_id in serving:
                if cap_id not in capabilities:
                    capabilities.append(cap_id)
        else:
            uncovered.append(etype)
    return {
        "capabilities": capabilities,
        "by_evidence": by_evidence,
        "uncovered": uncovered,
    }


def route_capability(platform, capability_id: str, *, health=None, freshness=None) -> dict:
    """Route one capability for a platform.

    The W4 router is intentionally small: it checks static adapter support,
    optional health probes, and optional freshness probes. It does not perform
    cost, model, risk, or data-sensitivity routing.
    """
    registry = CANONICAL_CAPABILITIES
    if capability_id not in registry:
        raise ValueError(f"unknown capability: {capability_id}")
    spec = registry[capability_id]
    health = health or {}
    freshness = freshness or {}
    reasons = []
    tools = {}

    platform_capability = spec.get("platform_capability")
    if platform_capability and not platform.capabilities.get(platform_capability, False):
        return {
            "capability": capability_id,
            "platform": platform.name,
            "status": UNSUPPORTED,
            "reason": f"platform capability unsupported: {platform_capability}",
            "tools": {},
        }

    for tool_key in spec.get("tools") or []:
        try:
            tools[tool_key] = platform.get_tool(tool_key)
        except Exception as exc:
            return {
                "capability": capability_id,
                "platform": platform.name,
                "status": UNSUPPORTED,
                "reason": str(exc),
                "tools": tools,
            }

    for probe in spec.get("health") or []:
        if health.get(probe) is False:
            reasons.append(f"health check failed: {probe}")

    for probe in spec.get("freshness") or []:
        state = freshness.get(probe)
        if state in {"stale", "missing", "unknown"}:
            reasons.append(f"freshness check {probe}: {state}")

    status = DEGRADED if reasons else READY
    return {
        "capability": capability_id,
        "platform": platform.name,
        "status": status,
        "reason": "; ".join(reasons),
        "tools": tools,
    }


def build_capability_routes(platform, *, health=None, freshness=None) -> dict[str, dict]:
    """Route every canonical capability for one platform."""
    return {
        capability_id: route_capability(
            platform, capability_id, health=health, freshness=freshness,
        )
        for capability_id in sorted(CANONICAL_CAPABILITIES)
    }
