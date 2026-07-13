"""Typed capability doctrine pins (harness plan §8/§9 + mutation test #1).

These tests are the CI half of the M2 mutation suite: moving CBM semantic
search (or the dependency aggregate) back to `required`, dropping the
structured-trace one_of group, or declaring a conditional capability without
triggers must fail here even if the generic contract validator still passes.
"""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]

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
