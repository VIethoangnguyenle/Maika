"""vNext W4 capability runtime and adapter contract tests."""

import re
from pathlib import Path

import pytest

from cli.capability_runtime import (
    CANONICAL_CAPABILITIES,
    DEGRADED,
    READY,
    UNSUPPORTED,
    build_capability_routes,
    capability_ids,
    route_capability,
)
from cli.platforms import PLATFORMS, get_platform


ROOT = Path(__file__).resolve().parents[2]


def _profile_ids():
    text = (ROOT / ".maika" / "profiles" / "capabilities.md").read_text(encoding="utf-8")
    return set(re.findall(r"`([a-z_]+)`", text))


def _skill_ids():
    ids = set()
    for path in (ROOT / ".maika" / "skills").glob("*/SKILL.md"):
        text = path.read_text(encoding="utf-8")
        for block in re.findall(r"Capability IDs:\s*(.+?)(?:\n\n|$)", text, re.DOTALL):
            ids.update(re.findall(r"`([a-z_]+)`", block))
    return ids


def test_registry_covers_profile_and_skill_capability_ids():
    assert _profile_ids() <= capability_ids()
    assert _skill_ids() <= capability_ids()


def test_render_context_exposes_registry_and_routes():
    ctx = get_platform("claude-code").build_render_context(["codebase-memory-mcp"], "python")

    assert ctx["capability_registry"] == CANONICAL_CAPABILITIES
    assert set(ctx["capability_routes"]) == capability_ids()
    assert ctx["capability_routes"]["task_dispatch"]["status"] == READY


def test_every_platform_has_route_for_every_capability():
    for key in PLATFORMS:
        routes = build_capability_routes(get_platform(key))
        assert set(routes) == capability_ids(), key
        for route in routes.values():
            assert route["status"] in {READY, DEGRADED, UNSUPPORTED}
            assert route["platform"] == key


def test_code_capabilities_degrade_when_index_stale():
    route = route_capability(
        get_platform("claude-code"),
        "exact_source_inspection",
        freshness={"code_index": "stale"},
    )

    assert route["status"] == DEGRADED
    assert "code_index" in route["reason"]


def test_business_knowledge_degrades_when_memory_health_fails():
    route = route_capability(
        get_platform("antigravity"),
        "business_knowledge_retrieval",
        health={"dynamic_memory": False},
    )

    assert route["status"] == DEGRADED
    assert "dynamic_memory" in route["reason"]


def test_generic_dispatch_capabilities_are_explicitly_unsupported():
    route = route_capability(get_platform("generic"), "task_dispatch")

    assert route["status"] == UNSUPPORTED
    assert "task_dispatch" in route["reason"]


def test_unknown_capability_fails_clearly():
    with pytest.raises(ValueError) as exc:
        route_capability(get_platform("claude-code"), "telepathy")

    assert "unknown capability" in str(exc.value)
