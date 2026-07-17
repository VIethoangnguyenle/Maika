"""Typed capability doctrine pins (harness plan §8/§9 + mutation test #1).

These tests are the CI half of the M2 mutation suite: moving CBM semantic
search (or the dependency aggregate) back to `required`, dropping the
structured-trace one_of group, or declaring a conditional capability without
triggers must fail here even if the generic contract validator still passes.
"""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
PROVIDERS_RULE = ROOT / ".maika/rules/jit/providers.md"

UA_STRUCTURED_TRACE = {"architecture_discovery", "domain_flow_trace", "call_chain_trace"}
MIGRATED = ("grounding-explorer", "reviewing-task", "reviewing-change", "database-explorer")


def _skill(name: str):
    text = (ROOT / f".maika/skills/{name}/SKILL.md").read_text(encoding="utf-8")
    _, frontmatter, body = text.split("---", 2)
    return yaml.safe_load(frontmatter), body


def _registry():
    return yaml.safe_load(
        (ROOT / ".maika/profiles/capability-registry.yaml").read_text(encoding="utf-8")
    )


def test_grounding_uses_one_of_structured_trace_and_conditional_cbm():
    frontmatter, body = _skill("grounding-explorer")
    caps = frontmatter["capabilities"]
    assert set(caps["one_of"]["structured_trace"]) == UA_STRUCTURED_TRACE
    assert {"exact_source_inspection", "historical_context_retrieval"} <= set(caps["required"])
    conditional = caps["conditional"]
    assert {"unresolved_anchor", "graph_gap", "ua_unavailable"} <= set(
        conditional["semantic_code_search"]["triggers"]
    )
    assert conditional["database_schema_inspection"]["triggers"] == ["persistence_change"]
    for field in (
        "graph_commit", "repository_head", "relevant_stale_files", "anchor_nodes",
        "traversals", "support_calls", "source_verifications",
    ):
        assert field in body


def test_cbm_capabilities_never_return_to_required():
    """Mutation #1 (plan §21): CBM semantic search moved back to required must fail CI."""
    for name in MIGRATED:
        frontmatter, _ = _skill(name)
        caps = frontmatter["capabilities"]
        pinned = set(caps.get("required") or [])
        for group in (caps.get("one_of") or {}).values():
            pinned |= set(group)
        assert "semantic_code_search" not in pinned, name
        assert "dependency_analysis" not in pinned, name


def test_reviewers_hold_only_neutral_required_capabilities():
    for name in ("reviewing-task", "reviewing-change"):
        frontmatter, body = _skill(name)
        caps = frontmatter["capabilities"]
        assert {"exact_source_inspection", "runtime_verification"} <= set(caps["required"])
        conditional = caps["conditional"]
        for capability in (
            "call_chain_trace", "impact_analysis", "semantic_code_search",
            "dependency_analysis", "historical_context_retrieval",
            "database_schema_inspection",
        ):
            assert conditional[capability]["triggers"], f"{name}: {capability}"
        assert "reason" in body.lower()


def test_database_explorer_conditional_consumer_mapping():
    frontmatter, _ = _skill("database-explorer")
    caps = frontmatter["capabilities"]
    assert "database_schema_inspection" in caps["required"]
    assert caps["conditional"]["semantic_code_search"]["triggers"] == [
        "database_code_consumer_gap"
    ]


def test_serena_capabilities_have_exact_mechanical_skill_consumers():
    grounding, _ = _skill("grounding-explorer")
    executing, _ = _skill("executing-task")
    reviewing_task, _ = _skill("reviewing-task")
    reviewing_change, _ = _skill("reviewing-change")

    assert grounding["capabilities"]["conditional"]["symbolic_code_navigation"][
        "triggers"
    ] == ["unresolved_anchor", "graph_gap", "relevant_graph_stale"]
    assert executing["capabilities"]["conditional"]["code_diagnostics"]["triggers"] == [
        "language_diagnostics_required"
    ]
    reviewer_routes = {
        "symbolic_code_navigation": {
            "triggers": [
                "hidden_consumer_risk",
                "reviewer_counter_evidence",
                "relevant_graph_stale",
            ]
        },
        "code_diagnostics": {"triggers": ["language_diagnostics_required"]},
    }
    for frontmatter in (reviewing_task, reviewing_change):
        conditional = frontmatter["capabilities"]["conditional"]
        for capability, route in reviewer_routes.items():
            assert conditional[capability] == route


def test_serena_skill_bodies_scope_lsp_evidence_and_require_current_source():
    for name in (
        "grounding-explorer", "executing-task", "reviewing-task", "reviewing-change"
    ):
        _, body = _skill(name)
        assert "scoped LSP evidence" in body, name
        assert "reflective/configured/event consumer" in body, name
        assert "current source" in body, name


def test_serena_maintenance_is_not_a_skill_evidence_capability():
    for name in (
        "grounding-explorer", "executing-task", "reviewing-task", "reviewing-change"
    ):
        frontmatter, body = _skill(name)
        caps = frontmatter["capabilities"]
        declared = set(caps.get("required") or [])
        declared.update((caps.get("conditional") or {}).keys())
        assert "operational_maintenance" not in declared, name
        assert "restart_language_server" in body, name
        assert "not evidence" in body, name


def test_ua_remains_trace_owner_in_provider_doctrine():
    text = PROVIDERS_RULE.read_text(encoding="utf-8")
    assert "UA-MCP" in text and "18 tools" in text
    assert "Serena không thay thế UA-MCP" in text
    assert "không bảo đảm hidden-consumer completeness" in text
    assert "get_node_source" in text and "một trong 18 tools" in text


def test_every_registry_trigger_has_a_consuming_skill():
    """R1: a trigger nobody consumes is dead vocabulary — remove it or wire it."""
    vocabulary = set(_registry().get("triggers") or {})
    assert vocabulary, "trigger vocabulary missing from capability registry"
    used: set[str] = set()
    for skill_md in (ROOT / ".maika/skills").glob("*/SKILL.md"):
        frontmatter, _ = _skill(skill_md.parent.name)
        conditional = (frontmatter.get("capabilities") or {}).get("conditional") or {}
        for spec in conditional.values():
            used.update((spec or {}).get("triggers") or [])
    assert used == vocabulary, (
        f"unconsumed triggers: {sorted(vocabulary - used)}; "
        f"undeclared triggers: {sorted(used - vocabulary)}"
    )


def test_writing_plan_keeps_compatibility_dependency_capability():
    frontmatter, _ = _skill("writing-plan")
    assert "dependency_analysis" in frontmatter["capabilities"]["required"]
