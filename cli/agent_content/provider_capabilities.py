"""Validate concrete provider mappings against canonical capability IDs."""

from __future__ import annotations

from pathlib import Path

import yaml

MAPPING_REL = "profiles/provider-capabilities.yaml"
REGISTRY_REL = "profiles/capability-registry.yaml"
ROLES = {"primary", "supporting"}
UA_TOOLS = {
    "list_projects", "get_graph_stats", "get_graph_metadata", "get_tour", "query_nodes",
    "get_node_detail", "get_node_source", "get_relationships",
    "trace_call_chain", "get_layer_info", "find_entry_points", "find_impact",
    "find_path", "get_class_hierarchy", "search_by_file_path",
    "get_domain_overview", "get_domain_detail", "get_domain_flow_detail",
}


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
            elif provider == "codebase-memory-mcp" and tools:
                errors.append(f"{prefix}: concrete CBM tool names are not verified")
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
