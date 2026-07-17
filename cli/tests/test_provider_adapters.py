from __future__ import annotations

import json
from pathlib import Path

from cli.mcp.integration import agent_memory, serena, understand_anything


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


def test_serena_duplicate_tool_degrades_contract_even_when_names_match():
    fixture = _fixture("serena", "tools-list-readonly-v1.json")
    changed = json.loads(json.dumps(fixture))
    changed["tools"].append(changed["tools"][0])

    result = serena.validate_tools_list(changed)

    assert result["status"] == "degraded"
    assert result["duplicates"] == [changed["tools"][0]["name"]]


def test_serena_observation_is_semantic_not_architecture_authority():
    result = serena.normalize_response("find_symbol", b'{"symbols": []}')
    assert result["authority"] == "semantic_symbol_resolution"
    assert result["canonical"] is False


def test_serena_restart_observation_is_maintenance_not_semantic_evidence():
    result = serena.normalize_response("restart_language_server", b'{"ok": true}')

    assert result["authority"] == "operational_maintenance"
    assert result["evidence_eligible"] is False
