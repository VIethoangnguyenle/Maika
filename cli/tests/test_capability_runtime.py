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
    route_question,
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
    ctx = get_platform("claude-code").build_render_context(["understand-anything"], "python")

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


# ── W1: knowledge-native capability additions ──────────────────────────────

def test_knowledge_native_capabilities_registered():
    """W1 adds historical + database capabilities to the canonical registry."""
    required = {
        "historical_context_retrieval",
        "database_schema_inspection",
        "database_dependency_analysis",
    }
    assert required <= capability_ids()


def test_historical_context_degrades_when_memory_health_fails():
    route = route_capability(
        get_platform("claude-code"),
        "historical_context_retrieval",
        health={"dynamic_memory": False},
    )

    assert route["status"] == DEGRADED
    assert "dynamic_memory" in route["reason"]


def test_historical_context_ready_when_memory_healthy():
    route = route_capability(
        get_platform("claude-code"),
        "historical_context_retrieval",
        health={"dynamic_memory": True},
    )

    assert route["status"] == READY


@pytest.mark.parametrize(
    "capability",
    ["database_schema_inspection", "database_dependency_analysis"],
)
def test_database_capabilities_degrade_when_db_health_fails(capability):
    route = route_capability(
        get_platform("claude-code"),
        capability,
        health={"database": False},
    )

    assert route["status"] == DEGRADED
    assert "database" in route["reason"]


# ── W2a: route_question — evidence-type -> capability resolution ─────────────

def test_route_question_resolves_capabilities_from_evidence_types():
    plan = route_question(["architecture_node", "dependency_path", "file_symbol"])
    assert "architecture_discovery" in plan["capabilities"]
    assert "dependency_analysis" in plan["capabilities"]
    assert "exact_source_inspection" in plan["capabilities"]
    assert plan["uncovered"] == []


def test_route_question_maps_history_and_database_evidence():
    plan = route_question(["incident_reference", "database_object", "database_dependency"])
    assert "historical_context_retrieval" in plan["capabilities"]
    assert "database_schema_inspection" in plan["capabilities"]
    assert "database_dependency_analysis" in plan["capabilities"]


def test_route_question_flags_uncovered_evidence_type():
    plan = route_question(["telepathic_signal"])
    assert plan["capabilities"] == []
    assert "telepathic_signal" in plan["uncovered"]


def test_route_question_by_evidence_lists_serving_capabilities():
    # domain_flow is served by both architecture_discovery and business_knowledge_retrieval
    plan = route_question(["domain_flow"])
    assert set(plan["by_evidence"]["domain_flow"]) >= {
        "architecture_discovery",
        "business_knowledge_retrieval",
    }
