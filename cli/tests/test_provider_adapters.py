from __future__ import annotations

import json
from pathlib import Path

from cli.mcp.integration import agent_memory, codebase_memory, serena, understand_anything


FIXTURES = Path(__file__).parent / "fixtures" / "provider_contracts"


def _fixture(provider: str, name: str) -> dict:
    return json.loads((FIXTURES / provider / name).read_text(encoding="utf-8"))


def test_ua_nested_metadata_is_normalized_without_invention():
    raw = (FIXTURES / "understand-anything" / "graph-metadata-v1.json").read_bytes()
    observation = understand_anything.normalize_response("get_graph_metadata", raw)
    assert observation["authority"] == "structured_graph_trace"
    assert observation["provider_contract_version"] == 1
    assert observation["status"] == "success"
    assert observation["graph"] == {
        "project": "fixture-project",
        "graph_commit": "abc123",
        "repository_head": "def456",
        "freshness": "STALE",
        "health": "HEALTHY",
    }


def test_ua_missing_critical_provenance_degrades_and_emits_no_graph_claim():
    raw = (FIXTURES / "understand-anything" / "graph-metadata-missing-provenance.json").read_bytes()
    observation = understand_anything.normalize_response("get_graph_metadata", raw)
    assert observation["status"] == "degraded"
    assert "graph" not in observation
    assert "graph_commit" in observation["degradation_reasons"][0]


def test_cbm_runtime_tool_surface_uses_search_graph_semantic_argument():
    result = codebase_memory.validate_tools_list(
        _fixture("codebase-memory", "tools-list-current.json")
    )
    assert result["status"] == "ready"
    assert "search_graph" in result["tools"]
    assert "semantic_query" not in result["tools"]
    assert result["tool_surface_hash"].startswith("sha256:")


def test_cbm_tool_surface_change_invalidates_prior_capability_probe():
    fixture = _fixture("codebase-memory", "tools-list-current.json")
    baseline = codebase_memory.validate_tools_list(fixture)["tool_surface_hash"]
    changed = json.loads(json.dumps(fixture))
    changed["tools"][0]["description"] = "changed contract"
    result = codebase_memory.validate_tools_list(
        changed, expected_tool_surface_hash=baseline
    )
    assert result["status"] == "degraded"
    assert result["prior_probe_valid"] is False


def test_cbm_support_call_rejects_fake_semantic_query_tool():
    try:
        codebase_memory.build_support_call(
            tool="semantic_query", trigger="graph_gap", reason="test", raw=b"{}"
        )
    except ValueError as exc:
        assert "unknown Codebase Memory tool" in str(exc)
    else:
        raise AssertionError("semantic_query must not be treated as a tool")


def test_cbm_observation_is_semantic_index_not_structured_trace_authority():
    observation = codebase_memory.normalize_response("search_graph", b'{"hits": []}')
    assert observation["authority"] == "semantic_index_structure"


def test_agent_memory_local_fallback_never_satisfies_proxy_only_readiness():
    local = agent_memory.assess_readiness(
        _fixture("agent-memory", "tools-list-local-fallback.json")
    )
    proxy = agent_memory.assess_readiness(
        _fixture("agent-memory", "tools-list-proxy.json")
    )
    assert local["status"] == "degraded"
    assert "expected proxy mode" in local["degradation_reasons"][0]
    # Even proxy is degraded until the upstream server proves store/instance identity.
    assert proxy["status"] == "degraded"
    assert proxy["identity_status"] == "unverified"
    assert local["tool_surface_hash"] != proxy["tool_surface_hash"]


def test_agent_memory_recall_is_historical_candidate_not_authorization():
    observation = agent_memory.normalize_response(
        "memory_recall", json.dumps({"agentId": "worker-7", "results": []})
    )
    assert observation["authority"] == "historical_context"
    assert observation["classification"] == "candidate"
    assert observation["canonical"] is False
    assert observation["provider_snapshot"]["agent_id_authorizes"] is False


def test_serena_readonly_surface_is_exact_and_write_free():
    fixture = _fixture("serena", "tools-list-readonly-v1.json")
    result = serena.validate_tools_list(fixture)
    assert result["status"] == "ready"
    assert set(result["tools"]) == serena.SERENA_READ_TOOLS
    assert set(result["tools"]).isdisjoint(serena.SERENA_FORBIDDEN_TOOLS)


def test_serena_write_or_memory_tool_degrades_contract():
    fixture = _fixture("serena", "tools-list-readonly-v1.json")
    changed = json.loads(json.dumps(fixture))
    changed["tools"].append({"name": "rename_symbol", "inputSchema": {"type": "object"}})
    result = serena.validate_tools_list(changed)
    assert result["status"] == "degraded"
    assert result["forbidden"] == ["rename_symbol"]


def test_serena_observation_is_semantic_not_architecture_authority():
    result = serena.normalize_response("find_symbol", b'{"symbols": []}')
    assert result["authority"] == "semantic_symbol_resolution"
    assert result["canonical"] is False
