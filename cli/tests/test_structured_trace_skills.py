from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def _skill(name: str):
    text = (ROOT / f".maika/skills/{name}/SKILL.md").read_text(encoding="utf-8")
    _, frontmatter, body = text.split("---", 2)
    return yaml.safe_load(frontmatter), body


def test_grounding_requires_precise_trace_capabilities_and_evidence_shape():
    frontmatter, body = _skill("grounding-explorer")
    required = set(frontmatter["capabilities"]["required"])
    assert {"domain_flow_trace", "call_chain_trace", "impact_analysis", "semantic_code_search"} <= required
    for field in (
        "graph_commit", "repository_head", "relevant_stale_files", "anchor_nodes",
        "traversals", "support_calls", "source_verifications",
    ):
        assert field in body


def test_reviewers_retrace_and_use_semantic_counter_evidence_conditionally():
    for name in ("reviewing-task", "reviewing-change"):
        frontmatter, body = _skill(name)
        required = set(frontmatter["capabilities"]["required"])
        assert {"call_chain_trace", "impact_analysis", "semantic_code_search"} <= required
        assert "current source" in body.lower()
        assert "reason" in body.lower()


def test_writing_plan_keeps_compatibility_dependency_capability():
    frontmatter, _ = _skill("writing-plan")
    assert "dependency_analysis" in frontmatter["capabilities"]["required"]
