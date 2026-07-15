"""Validate concrete provider mappings against canonical capability IDs."""

from __future__ import annotations

from pathlib import Path

import yaml

from cli.mcp.integration.serena import SERENA_READ_TOOLS

MAPPING_REL = "profiles/provider-capabilities.yaml"
REGISTRY_REL = "profiles/capability-registry.yaml"
PROVIDER_REGISTRY_REL = "config/provider-registry.yaml"
ROLES = {"primary", "supporting"}
UA_TOOLS = {
    "list_projects", "get_graph_stats", "get_graph_metadata", "get_tour", "query_nodes",
    "get_node_detail", "get_node_source", "get_relationships",
    "trace_call_chain", "get_layer_info", "find_entry_points", "find_impact",
    "find_path", "get_class_hierarchy", "search_by_file_path",
    "get_domain_overview", "get_domain_detail", "get_domain_flow_detail",
}
CBM_TOOLS = {
    "index_repository", "search_graph", "query_graph", "trace_path",
    "get_code_snippet", "get_graph_schema", "get_architecture", "search_code",
    "list_projects", "delete_project", "index_status", "detect_changes",
    "manage_adr", "ingest_traces",
}
AGENT_MEMORY_PROXY_TOOLS = {
    "memory_smart_search", "memory_recall", "memory_sessions", "memory_save",
    "memory_governance_delete",
}
SERENA_TOOLS = set(SERENA_READ_TOOLS)


def _load(path: Path, label: str) -> dict:
    if not path.exists():
        raise FileNotFoundError(str(path))
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValueError(f"{path}: {label} must be a mapping")
    return doc


def load_provider_capabilities(framework_dir: Path) -> dict:
    return _load(Path(framework_dir) / MAPPING_REL, "mapping")


def load_capability_registry(framework_dir: Path) -> dict:
    return _load(Path(framework_dir) / REGISTRY_REL, "registry")


def load_provider_registry(framework_dir: Path) -> dict:
    return _load(Path(framework_dir) / PROVIDER_REGISTRY_REL, "provider registry")


def validate_canonical_provider_registry(doc: dict, capabilities: dict) -> list[str]:
    errors: list[str] = []
    providers = doc.get("providers")
    if doc.get("version") != 1 or not isinstance(providers, dict) or not providers:
        return ["provider registry requires version 1 and a non-empty providers map"]
    known_caps = set(capabilities.get("capabilities") or {})
    authority = doc.get("authority") or {}
    expected_authority = {
        "exact_current_source": {"authoritative": "current-source"},
        "structured_graph_trace": {
            "preferred": "understand-anything",
            "conflict_action": "verify_current_source",
        },
        "semantic_index_structure": {
            "preferred": "codebase-memory-mcp",
            "conflict_action": "verify_current_source",
        },
        "semantic_symbol_resolution": {
            "preferred": "serena",
            "conflict_action": "verify_current_source",
        },
        "historical_context": {"conflict_action": "treat_as_candidate"},
        "canonical_project_knowledge": {
            "authoritative": "maika-knowledge-kernel"
        },
    }
    for lane, expected_fields in expected_authority.items():
        for key, expected in expected_fields.items():
            if (authority.get(lane) or {}).get(key) != expected:
                errors.append(f"authority.{lane}.{key} must be {expected}")
    for provider_id, spec in providers.items():
        prefix = f"providers.{provider_id}"
        if not spec.get("display_name") or not spec.get("kind"):
            errors.append(f"{prefix}: display_name and kind are required")
        if not spec.get("synthetic"):
            if spec.get("configured_externally"):
                if spec.get("client_config_key") != provider_id:
                    errors.append(f"{prefix}: client_config_key must equal provider ID")
            elif spec.get("setup_ref") != provider_id:
                errors.append(f"{prefix}: setup_ref must equal canonical provider ID")
        contract = spec.get("contract") or {}
        if contract and contract.get("id") != provider_id:
            errors.append(f"{prefix}: contract ID must equal canonical provider ID")
        for role in ("primary", "supporting"):
            for capability in (spec.get("capabilities") or {}).get(role) or []:
                if capability not in known_caps:
                    errors.append(f"{prefix}: unknown capability {capability}")
        if provider_id == "understand-anything":
            tools = set((spec.get("tool_contract") or {}).get("tools") or [])
            if tools != UA_TOOLS:
                errors.append(
                    f"{prefix}: tool contract differs from tested UA tool snapshot"
                )
        if provider_id == "db-access":
            tool_contract = spec.get("tool_contract") or {}
            tools = set(tool_contract.get("tools") or [])
            lanes = tool_contract.get("lanes") or {}
            if not tools or not isinstance(lanes, dict):
                errors.append(f"{prefix}: tool contract and lanes are required")
                continue
            for lane, lane_spec in lanes.items():
                unknown = set((lane_spec or {}).get("tools") or []) - tools
                if unknown:
                    errors.append(f"{prefix}.tool_contract.lanes.{lane}: unknown tools {sorted(unknown)!r}")
            exploration = set((lanes.get("exploration") or {}).get("tools") or [])
            privileged = {
                "sql_write", "mongo_write", "sql_execute_script",
            }
            leaked = exploration & privileged
            if leaked:
                errors.append(f"{prefix}: exploration lane exposes privileged tools {sorted(leaked)!r}")
            for lane in ("explicit_write", "explicit_script"):
                lane_spec = lanes.get(lane) or {}
                if lane_spec.get("activation") != "explicit_user_request":
                    errors.append(f"{prefix}.tool_contract.lanes.{lane}: explicit user activation required")
                if lane_spec.get("provider_confirmation_required") is not True:
                    errors.append(f"{prefix}.tool_contract.lanes.{lane}: provider confirmation required")
        if provider_id == "codebase-memory-mcp":
            tool_contract = spec.get("tool_contract") or {}
            tools = set(tool_contract.get("tools") or [])
            if tools != CBM_TOOLS:
                errors.append(f"{prefix}: tool contract differs from tested CBM tool snapshot")
            lanes = tool_contract.get("lanes") or {}
            lane_tools = {
                tool for lane in lanes.values() for tool in ((lane or {}).get("tools") or [])
            }
            if lane_tools != tools:
                errors.append(f"{prefix}: every CBM tool must belong to exactly one declared lane")
            semantic = (tool_contract.get("capabilities") or {}).get("semantic_code_search") or {}
            if semantic != {"tool": "search_graph", "argument": "semantic_query", "argument_type": "array"}:
                errors.append(f"{prefix}: semantic search must use search_graph.semantic_query[array]")
        if provider_id == "serena":
            tool_contract = spec.get("tool_contract") or {}
            tools = set(tool_contract.get("tools") or [])
            if tools != SERENA_TOOLS:
                errors.append(f"{prefix}: tool contract differs from tested Serena tool snapshot")
            lanes = tool_contract.get("lanes") or {}
            if set(lanes) != {"discovery"}:
                errors.append(f"{prefix}: tool contract must have exactly one discovery lane")
            discovery = lanes.get("discovery") or {}
            if discovery.get("mutability") != "read_only":
                errors.append(f"{prefix}: discovery lane must be read_only")
            if set(discovery.get("tools") or []) != tools:
                errors.append(f"{prefix}: discovery lane tools must equal contract tools")
        if provider_id == "agent-memory":
            if spec.get("integration_mode") != "mcp_proxy_only":
                errors.append(f"{prefix}: integration_mode must be mcp_proxy_only")
            if spec.get("fallback_policy") != "reject_store_change":
                errors.append(f"{prefix}: fallback must reject store changes")
            hooks = spec.get("hooks") or {}
            if hooks.get("auto_capture") is not False or hooks.get("session_injection") is not False:
                errors.append(f"{prefix}: auto capture and session injection must be disabled")
            tools = set((spec.get("tool_contract") or {}).get("tools") or [])
            if tools != AGENT_MEMORY_PROXY_TOOLS:
                errors.append(f"{prefix}: tool contract differs from tested proxy tool snapshot")
            if spec.get("agent_id_semantics") != "retrieval_filter_only":
                errors.append(f"{prefix}: agentId is a retrieval filter, not authorization")
            forbidden = set(spec.get("not_authoritative_for") or [])
            if not {"exact_current_code", "canonical_project_knowledge"} <= forbidden:
                errors.append(f"{prefix}: memory must not be current-code or canonical authority")
    return errors


def validate_provider_capabilities(mapping: dict, registry: dict) -> list[str]:
    errors: list[str] = []
    if not isinstance(mapping.get("version"), int):
        errors.append("version: required integer field")
    providers = mapping.get("providers")
    capabilities = registry.get("capabilities") or {}
    if not isinstance(providers, dict) or not providers:
        return errors + ["providers: required non-empty mapping"]
    primary_seen: dict[str, str] = {}
    for provider, provider_spec in providers.items():
        mapped = (provider_spec or {}).get("capabilities")
        if not isinstance(mapped, dict) or not mapped:
            errors.append(f"providers.{provider}: capabilities must be non-empty")
            continue
        probe = (provider_spec or {}).get("freshness_probe") or {}
        if provider == "understand-anything" and probe.get("tool") not in UA_TOOLS:
            errors.append("understand-anything: unknown freshness probe")
        for capability, spec in mapped.items():
            prefix = f"providers.{provider}.capabilities.{capability}"
            if capability not in capabilities:
                errors.append(f"{prefix}: unknown capability")
                continue
            role = (spec or {}).get("role")
            if role not in ROLES:
                errors.append(f"{prefix}: unknown role {role!r}")
            if role == "primary":
                if capability in primary_seen:
                    errors.append(f"{prefix}: duplicate primary provider {primary_seen[capability]}")
                primary_seen[capability] = provider
            tools = (spec or {}).get("tools") or []
            if provider == "understand-anything":
                unknown = set(tools) - UA_TOOLS
                if unknown:
                    errors.append(f"{prefix}: unknown UA-MCP tools {sorted(unknown)!r}")
            elif provider == "codebase-memory-mcp":
                unknown = set(tools) - CBM_TOOLS
                if unknown:
                    errors.append(f"{prefix}: unknown CBM tools {sorted(unknown)!r}")
                if capability == "semantic_code_search" and tools != ["search_graph"]:
                    errors.append(f"{prefix}: semantic search must route through search_graph")
            elif provider == "serena":
                unknown = set(tools) - SERENA_TOOLS
                if unknown:
                    errors.append(f"{prefix}: unknown Serena tools {sorted(unknown)!r}")
            declared_primary = capabilities[capability].get("primary_provider")
            if role == "primary" and declared_primary != provider:
                errors.append(
                    f"{prefix}: registry primary is {declared_primary!r}, not {provider!r}"
                )
    for capability, spec in capabilities.items():
        declared = spec.get("primary_provider")
        if declared and primary_seen.get(capability) != declared:
            errors.append(f"capabilities.{capability}: primary provider mapping missing")
    exact = ((providers.get("current-source") or {}).get("capabilities") or {}).get(
        "exact_source_inspection", {}
    )
    if "exact_code_fact" not in (exact.get("authoritative_for") or []):
        errors.append("current-source must be authoritative for exact_code_fact")
    return errors


SYNTHETIC_PROVIDERS = {"current-source"}


def validate_provider_identity(
    mapping: dict,
    registry: dict,
    manifest_ids: set[str],
    workflow_owners: set[str],
) -> list[str]:
    """Cross-surface identity check: every provider ID used in the profiles must be
    a plugin-manifest mcp_capabilities key (or the synthetic current-source), and
    every external-workflow owner must be a known provider ID."""
    errors: list[str] = []
    used: set[str] = set((mapping.get("providers") or {}).keys())
    for capability, spec in (registry.get("capabilities") or {}).items():
        primary = (spec or {}).get("primary_provider")
        if primary:
            used.add(primary)
        for supporting in (spec or {}).get("supporting_providers") or []:
            used.add(supporting)
    known = manifest_ids | SYNTHETIC_PROVIDERS
    for provider in sorted(used - known):
        errors.append(
            f"provider ID {provider!r} not in plugin-manifest mcp_capabilities "
            f"(known: {sorted(known)!r})"
        )
    for owner in sorted(workflow_owners - used - known):
        errors.append(f"workflow owner {owner!r} is not a known provider ID")
    return errors
