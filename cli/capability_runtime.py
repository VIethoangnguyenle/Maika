"""Maika vNext capability registry and health/freshness router."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / ".maika" / "profiles" / "capability-registry.yaml"
READY = "ready"
DEGRADED = "degraded"
UNSUPPORTED = "unsupported"


def load_capability_registry(path: Path | None = None) -> dict[str, dict[str, Any]]:
    """Load canonical capability definitions keyed by capability id."""
    source = path or REGISTRY_PATH
    doc = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
    caps = doc.get("capabilities") or {}
    if not isinstance(caps, dict) or not caps:
        raise ValueError(f"capability registry has no capabilities: {source}")
    return deepcopy(caps)


CANONICAL_CAPABILITIES = load_capability_registry()


def capability_ids() -> set[str]:
    return set(CANONICAL_CAPABILITIES)


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
