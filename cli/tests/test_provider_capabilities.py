from copy import deepcopy
from pathlib import Path

import yaml

from cli.agent_content.provider_capabilities import (
    load_capability_registry, load_provider_capabilities, validate_provider_capabilities,
    load_provider_registry, validate_canonical_provider_registry,
)
from cli.mcp.integration.serena import SERENA_READ_TOOLS

REPO = Path(__file__).resolve().parents[2]
FRAMEWORK = REPO / ".maika"


def _docs():
    return load_provider_capabilities(FRAMEWORK), load_capability_registry(FRAMEWORK)


def _identity_inputs():
    mapping, registry = _docs()
    manifest = yaml.safe_load(
        (REPO / "cli" / "plugin-manifest.yaml").read_text(encoding="utf-8")
    )
    workflows = yaml.safe_load(
        (FRAMEWORK / "config" / "external-workflows.yaml").read_text(encoding="utf-8")
    )
    manifest_ids = set((manifest.get("mcp_capabilities") or {}).keys())
    owners = {
        spec.get("owner")
        for spec in (workflows.get("workflows") or {}).values()
        if spec.get("owner")
    }
    return mapping, registry, manifest_ids, owners


def test_canonical_provider_mapping_is_valid():
    mapping, registry = _docs()
    assert validate_provider_capabilities(mapping, registry) == []


def test_ua_is_primary_for_structured_traces():
    mapping, _ = _docs()
    ua = mapping["providers"]["understand-anything"]["capabilities"]
    for capability in (
        "architecture_discovery", "domain_flow_trace", "call_chain_trace",
        "impact_analysis", "graph_path_trace", "inheritance_trace",
    ):
        assert ua[capability]["role"] == "primary"


def test_serena_is_primary_only_for_symbols_and_diagnostics():
    mapping, capabilities = _docs()
    providers = load_provider_registry(FRAMEWORK)
    serena = mapping["providers"]["serena"]["capabilities"]
    assert serena["symbolic_code_navigation"]["role"] == "primary"
    assert serena["code_diagnostics"]["role"] == "primary"
    assert serena["operational_maintenance"] == {
        "role": "primary",
        "tools": ["restart_language_server"],
    }
    assert serena["code_diagnostics"]["tools"] == [
        "get_diagnostics_for_file", "get_diagnostics_for_symbol",
    ]
    assert capabilities["capabilities"]["architecture_discovery"]["primary_provider"] == "understand-anything"
    assert capabilities["capabilities"]["call_chain_trace"]["primary_provider"] == "understand-anything"
    assert set(providers["providers"]["serena"]["tool_contract"]["tools"]) == SERENA_READ_TOOLS


def test_serena_contract_separates_read_only_discovery_and_maintenance_lanes():
    providers = load_provider_registry(FRAMEWORK)
    lanes = providers["providers"]["serena"]["tool_contract"]["lanes"]
    assert set(lanes) == {"discovery", "maintenance"}
    assert lanes["discovery"]["mutability"] == "read_only"
    assert "restart_language_server" not in lanes["discovery"]["tools"]
    assert lanes["maintenance"] == {
        "tools": ["restart_language_server"],
        "mutability": "operational",
        "evidence_eligible": False,
    }


def test_serena_registry_rejects_tool_or_lane_drift():
    _mapping, capabilities = _docs()
    providers = load_provider_registry(FRAMEWORK)

    wrong_tools = deepcopy(providers)
    wrong_tools["providers"]["serena"]["tool_contract"]["tools"].append("replace_symbol_body")
    assert any(
        "Serena tool snapshot" in error
        for error in validate_canonical_provider_registry(wrong_tools, capabilities)
    )

    extra_lane = deepcopy(providers)
    extra_lane["providers"]["serena"]["tool_contract"]["lanes"]["write"] = {
        "tools": ["replace_symbol_body"],
        "mutability": "write",
    }
    assert any(
        "exactly discovery and maintenance lanes" in error
        for error in validate_canonical_provider_registry(extra_lane, capabilities)
    )

    wrong_mutability = deepcopy(providers)
    wrong_mutability["providers"]["serena"]["tool_contract"]["lanes"]["discovery"][
        "mutability"
    ] = "write"
    assert any(
        "discovery lane must be read_only" in error
        for error in validate_canonical_provider_registry(wrong_mutability, capabilities)
    )

    mismatched_lane = deepcopy(providers)
    mismatched_lane["providers"]["serena"]["tool_contract"]["lanes"]["discovery"]["tools"].pop()
    assert any(
        "every Serena tool must belong to exactly one lane" in error
        for error in validate_canonical_provider_registry(mismatched_lane, capabilities)
    )


def test_serena_registry_rejects_duplicate_contract_and_lane_entries():
    _mapping, capabilities = _docs()
    providers = load_provider_registry(FRAMEWORK)

    duplicate_contract = deepcopy(providers)
    duplicate_contract["providers"]["serena"]["tool_contract"]["tools"].append(
        "find_symbol"
    )
    assert any(
        "duplicate Serena contract tools" in error
        for error in validate_canonical_provider_registry(duplicate_contract, capabilities)
    )

    duplicate_lane = deepcopy(providers)
    duplicate_lane["providers"]["serena"]["tool_contract"]["lanes"]["discovery"][
        "tools"
    ].append("find_symbol")
    assert any(
        "duplicate Serena lane tools" in error
        for error in validate_canonical_provider_registry(duplicate_lane, capabilities)
    )


def test_cbm_semantic_source_exact_and_compatibility_dependency():
    mapping, registry = _docs()
    providers = mapping["providers"]
    exact = providers["current-source"]["capabilities"]["exact_source_inspection"]
    assert "exact_code_fact" in exact["authoritative_for"]
    registry = load_capability_registry(FRAMEWORK)
    dependency = registry["capabilities"]["dependency_analysis"]
    assert dependency["primary_provider"] == "understand-anything"
    assert "codebase-memory-mcp" not in str(registry)


def test_unknown_capability_and_ua_tool_fail():
    mapping, registry = _docs()
    mapping = deepcopy(mapping)
    ua = mapping["providers"]["understand-anything"]["capabilities"]
    ua["unknown_trace"] = {"role": "supporting"}
    ua["call_chain_trace"]["tools"].append("invented_tool")
    errors = validate_provider_capabilities(mapping, registry)
    assert any("unknown capability" in error for error in errors)
    assert any("invented_tool" in error for error in errors)


def test_identity_flags_provider_missing_from_manifest():
    from cli.agent_content.provider_capabilities import validate_provider_identity
    mapping = {"providers": {"understand-anything-mcp": {"capabilities": {}}}}
    registry = {"capabilities": {}}
    errors = validate_provider_identity(
        mapping, registry, manifest_ids={"understand-anything"}, workflow_owners=set()
    )
    assert any("understand-anything-mcp" in e for e in errors)


def test_identity_flags_unknown_workflow_owner():
    from cli.agent_content.provider_capabilities import validate_provider_identity
    mapping = {"providers": {"understand-anything": {"capabilities": {}}}}
    registry = {"capabilities": {}}
    errors = validate_provider_identity(
        mapping, registry,
        manifest_ids={"understand-anything"},
        workflow_owners={"understand-anything-mcp"},
    )
    assert any("workflow owner" in e for e in errors)


def test_identity_accepts_synthetic_current_source():
    from cli.agent_content.provider_capabilities import validate_provider_identity
    mapping = {"providers": {"current-source": {"capabilities": {}}}}
    registry = {"capabilities": {"x": {"primary_provider": "current-source"}}}
    errors = validate_provider_identity(
        mapping, registry, manifest_ids=set(), workflow_owners=set()
    )
    assert errors == []


def test_repo_provider_ids_converge_across_surfaces():
    from cli.agent_content.provider_capabilities import validate_provider_identity
    mapping, registry, manifest_ids, owners = _identity_inputs()
    assert validate_provider_identity(mapping, registry, manifest_ids, owners) == []


def test_canonical_provider_registry_is_valid_and_owns_db_access():
    _mapping, capabilities = _docs()
    providers = load_provider_registry(FRAMEWORK)
    assert validate_canonical_provider_registry(providers, capabilities) == []
    db = providers["providers"]["db-access"]
    assert db["configured_externally"] is True
    assert db["client_config_key"] == "db-access"
    assert "runtime" not in db
    assert db["tool_contract"]["lanes"]["explicit_write"]["activation"] == "explicit_user_request"
    assert db["tool_contract"]["lanes"]["explicit_write"]["provider_confirmation_required"] is True


def test_ua_registry_uses_observed_tool_snapshot_without_provider_rewrite():
    _mapping, capabilities = _docs()
    providers = load_provider_registry(FRAMEWORK)
    ua = providers["providers"]["understand-anything"]
    assert "contract" not in ua
    assert "get_graph_metadata" in ua["tool_contract"]["tools"]
    assert validate_canonical_provider_registry(providers, capabilities) == []


def test_db_exploration_lane_rejects_write_tool_leak():
    _mapping, capabilities = _docs()
    providers = deepcopy(load_provider_registry(FRAMEWORK))
    providers["providers"]["db-access"]["tool_contract"]["lanes"]["exploration"]["tools"].append(
        "sql_write"
    )
    errors = validate_canonical_provider_registry(providers, capabilities)
    assert any("exploration lane exposes privileged tools" in error for error in errors)


def test_db_write_lane_requires_explicit_user_request_and_provider_confirmation():
    _mapping, capabilities = _docs()
    providers = deepcopy(load_provider_registry(FRAMEWORK))
    lane = providers["providers"]["db-access"]["tool_contract"]["lanes"]["explicit_write"]
    lane["activation"] = "automatic"
    lane["provider_confirmation_required"] = False
    errors = validate_canonical_provider_registry(providers, capabilities)
    assert any("explicit user activation required" in error for error in errors)
    assert any("provider confirmation required" in error for error in errors)


def test_cbm_and_agent_memory_registry_contracts_are_enforced():
    _mapping, capabilities = _docs()
    providers = load_provider_registry(FRAMEWORK)
    assert validate_canonical_provider_registry(providers, capabilities) == []
    memory = providers["providers"]["agent-memory"]
    assert memory["integration_mode"] == "mcp_proxy_only"
    assert memory["hooks"]["auto_capture"] is False


def test_authority_policy_keeps_ua_primary_for_structured_graph_trace():
    _mapping, capabilities = _docs()
    providers = load_provider_registry(FRAMEWORK)
    authority = providers["authority"]
    assert authority["structured_graph_trace"]["preferred"] == "understand-anything"

    changed = deepcopy(providers)
    changed["authority"]["structured_graph_trace"]["preferred"] = "serena"
    errors = validate_canonical_provider_registry(changed, capabilities)
    assert any("structured_graph_trace.preferred" in error for error in errors)


def test_registry_rejects_codebase_memory_provider():
    doc = deepcopy(load_provider_registry(FRAMEWORK))
    doc["providers"]["codebase-memory-mcp"] = {
        "display_name": "Codebase Memory MCP", "kind": "semantic_code_index",
        "setup_ref": "codebase-memory-mcp",
        "capabilities": {"primary": ["semantic_code_search"]},
    }
    registry = load_capability_registry(FRAMEWORK)
    errors = validate_canonical_provider_registry(doc, registry)
    assert any("unknown capability" in error for error in errors)
