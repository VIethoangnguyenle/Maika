from copy import deepcopy
from pathlib import Path

from cli.agent_content.provider_capabilities import (
    load_capability_registry, load_provider_capabilities, validate_provider_capabilities,
)

FRAMEWORK = Path(__file__).resolve().parents[2] / ".maika"


def _docs():
    return load_provider_capabilities(FRAMEWORK), load_capability_registry(FRAMEWORK)


def test_canonical_provider_mapping_is_valid():
    mapping, registry = _docs()
    assert validate_provider_capabilities(mapping, registry) == []


def test_ua_is_primary_for_structured_traces():
    mapping, _ = _docs()
    ua = mapping["providers"]["understand-anything-mcp"]["capabilities"]
    for capability in (
        "architecture_discovery", "domain_flow_trace", "call_chain_trace",
        "impact_analysis", "graph_path_trace", "inheritance_trace",
    ):
        assert ua[capability]["role"] == "primary"


def test_cbm_semantic_source_exact_and_compatibility_dependency():
    mapping, registry = _docs()
    providers = mapping["providers"]
    assert providers["codebase-memory-mcp"]["capabilities"]["semantic_code_search"]["role"] == "primary"
    exact = providers["current-source"]["capabilities"]["exact_source_inspection"]
    assert "exact_code_fact" in exact["authoritative_for"]
    assert registry["capabilities"]["dependency_analysis"]["compatibility_aggregate"] is True


def test_unknown_capability_and_ua_tool_fail():
    mapping, registry = _docs()
    mapping = deepcopy(mapping)
    ua = mapping["providers"]["understand-anything-mcp"]["capabilities"]
    ua["unknown_trace"] = {"role": "supporting"}
    ua["call_chain_trace"]["tools"].append("invented_tool")
    errors = validate_provider_capabilities(mapping, registry)
    assert any("unknown capability" in error for error in errors)
    assert any("invented_tool" in error for error in errors)


def test_concrete_cbm_tool_names_are_rejected_until_verified():
    mapping, registry = _docs()
    mapping = deepcopy(mapping)
    mapping["providers"]["codebase-memory-mcp"]["capabilities"]["semantic_code_search"]["tools"] = ["guess_search"]
    assert any("not verified" in error for error in validate_provider_capabilities(mapping, registry))
