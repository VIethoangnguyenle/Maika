"""Tests for platform adapter definitions."""

import pytest

from cli.platforms import PLATFORMS, get_platform
from cli.platforms.base import (
    OPTIONAL_TOOL_KEYS,
    REQUIRED_TOOL_KEYS,
    BasePlatform,
    PlatformToolMappingError,
)
from cli.platforms.generic import GenericPlatform


SERENA_MAPPING = {
    "serena_symbols_overview": "get_symbols_overview",
    "serena_find_symbol": "find_symbol",
    "serena_find_references": "find_referencing_symbols",
    "serena_find_declaration": "find_declaration",
    "serena_find_implementations": "find_implementations",
    "serena_file_diagnostics": "get_diagnostics_for_file",
    "serena_symbol_diagnostics": "get_diagnostics_for_symbol",
    "serena_restart_language_server": "restart_language_server",
}

SERENA_EDITING_NAMES = {
    "create_text_file",
    "delete_lines",
    "insert_after_symbol",
    "insert_at_line",
    "insert_before_symbol",
    "rename_symbol",
    "replace_content",
    "replace_lines",
    "replace_symbol_body",
}


def test_platform_framework_roots():
    assert {get_platform(key).framework_root for key in PLATFORMS} == {".maika"}


def test_native_root_platforms_do_not_need_skill_mirror():
    assert get_platform("antigravity").native_skill_export is None
    assert get_platform("codex").native_skill_export is None
    assert get_platform("claude-code").native_skill_export is None


def test_render_context_includes_framework_root():
    ctx = get_platform("antigravity").build_render_context(["codebase-memory-mcp"], "python")
    assert ctx["platform"]["framework_root"] == ".maika"


def test_write_gate_hook_capability_matrix():
    assert get_platform("claude-code").capabilities["write_gate_hook"] is True
    assert get_platform("codex").capabilities["write_gate_hook"] is True
    assert get_platform("antigravity").capabilities["write_gate_hook"] is True
    assert get_platform("generic").capabilities["write_gate_hook"] is False


def test_dispatch_capability_matrix():
    for key in ("claude-code", "codex", "antigravity"):
        caps = get_platform(key).capabilities
        assert caps["fresh_session"] is True
        assert caps["task_dispatch"] is True
        assert caps["review_dispatch"] is True
    assert get_platform("generic").capabilities["task_dispatch"] is False
    assert get_platform("generic").capabilities["review_dispatch"] is False


def test_cursor_is_out_of_scope_for_platform_selection():
    assert "cursor" not in PLATFORMS


def test_generic_platform_defaults_to_maika_root():
    assert GenericPlatform().framework_root == ".maika"
    assert GenericPlatform().native_skill_export is None


def test_all_platforms_define_required_tool_keyset():
    for key, cls in PLATFORMS.items():
        platform = cls()
        missing = REQUIRED_TOOL_KEYS - set(platform.tool_mapping) - platform.unsupported_tools
        extra = set(platform.tool_mapping) - REQUIRED_TOOL_KEYS - OPTIONAL_TOOL_KEYS
        extra_unsupported = platform.unsupported_tools - REQUIRED_TOOL_KEYS
        assert missing == set(), f"{key} missing tool mappings: {sorted(missing)}"
        assert extra == set(), f"{key} declares unknown tool mappings: {sorted(extra)}"
        assert extra_unsupported == set(), (
            f"{key} declares unknown unsupported tools: {sorted(extra_unsupported)}"
        )


def test_serena_mapping_exists_on_all_supported_platforms():
    for key, cls in PLATFORMS.items():
        serena_keys = {
            operation for operation in cls().tool_mapping if operation.startswith("serena_")
        }
        assert serena_keys == set(SERENA_MAPPING), (
            f"{key} Serena mappings differ from the supported operation set"
        )


def test_serena_operations_are_optional_tool_keys():
    assert set(SERENA_MAPPING) <= OPTIONAL_TOOL_KEYS


def test_serena_native_names_are_platform_correct():
    platform_prefixes = {
        "claude-code": "mcp__serena__",
        "antigravity": "mcp_serena_",
        "codex": "",
        "generic": "",
    }
    for platform_key, prefix in platform_prefixes.items():
        mapping = get_platform(platform_key).tool_mapping
        for operation, native_name in SERENA_MAPPING.items():
            assert mapping[operation] == f"{prefix}{native_name}"


def test_serena_editing_tool_names_are_not_mapped():
    for key, cls in PLATFORMS.items():
        concrete_names = set(cls().tool_mapping.values())
        for editing_name in SERENA_EDITING_NAMES:
            assert not any(editing_name in concrete for concrete in concrete_names), (
                f"{key} unexpectedly maps Serena editing tool {editing_name}"
            )


def test_build_render_context_fails_on_missing_required_tool_mapping():
    class BrokenPlatform(BasePlatform):
        name = "broken"
        display_name = "Broken"
        config_entry_point = "AGENTS.md"
        tool_mapping = {"read_file": "Read"}

    with pytest.raises(PlatformToolMappingError) as exc:
        BrokenPlatform().build_render_context([], "python")

    message = str(exc.value)
    assert "broken" in message
    assert "missing required tool mappings" in message
    assert "write_file" in message


def test_build_render_context_allows_declared_optional_tool_mappings():
    class OptionalToolPlatform(BasePlatform):
        name = "optional-tools"
        display_name = "Optional Tools"
        config_entry_point = "AGENTS.md"
        tool_mapping = {
            **{key: key.upper() for key in REQUIRED_TOOL_KEYS},
            **{key: key.upper() for key in OPTIONAL_TOOL_KEYS},
        }

    context = OptionalToolPlatform().build_render_context([], "python")

    assert context["tools"]["browser_agent"] == "BROWSER_AGENT"
    assert context["tools"]["generate_image"] == "GENERATE_IMAGE"


def test_build_render_context_fails_on_unknown_extra_tool_mapping():
    class ExtraToolPlatform(BasePlatform):
        name = "extra-tools"
        display_name = "Extra Tools"
        config_entry_point = "AGENTS.md"
        tool_mapping = {
            **{key: key.upper() for key in REQUIRED_TOOL_KEYS},
            "surprise_tool": "SURPRISE_TOOL",
        }

    with pytest.raises(PlatformToolMappingError) as exc:
        ExtraToolPlatform().build_render_context([], "python")

    message = str(exc.value)
    assert "extra-tools" in message
    assert "unknown tool mappings" in message
    assert "surprise_tool" in message


def test_get_tool_fails_for_unknown_required_operation():
    platform = get_platform("generic")

    with pytest.raises(PlatformToolMappingError) as exc:
        platform.get_tool("not_a_real_tool")

    assert "not_a_real_tool" in str(exc.value)


def test_all_platforms_map_real_db_access_operations():
    for key, cls in PLATFORMS.items():
        for operation in (
            "db_list_databases", "db_list_tables", "db_get_columns", "db_get_constraints",
            "db_sql_read", "db_mongo_read", "db_sql_write", "db_mongo_write",
            "db_sql_execute_script",
        ):
            assert operation in cls().tool_mapping, f"{key} missing {operation} mapping"


def test_db_access_operations_resolve_in_render_context():
    ctx = get_platform("claude-code").build_render_context(["db-access"], "python")
    assert ctx["tools"]["db_list_tables"] == "mcp__db-access__sql_list_tables"
    assert ctx["tools"]["db_sql_write"] == "mcp__db-access__sql_write"


DYNAMIC_MEMORY_OPS = {
    "dynamic_memory_search",
    "dynamic_memory_recall",
    "dynamic_memory_sessions",
    "dynamic_memory_audit",
    "dynamic_memory_health",
    "dynamic_memory_save",
    "dynamic_memory_forget",
}


def test_all_platforms_map_dynamic_memory_ops():
    for key, cls in PLATFORMS.items():
        mapping = cls().tool_mapping
        for op in DYNAMIC_MEMORY_OPS:
            assert op in mapping, f"{key} missing {op} mapping"


def test_dynamic_memory_ops_are_required_keys():
    assert DYNAMIC_MEMORY_OPS <= REQUIRED_TOOL_KEYS


def test_semantic_search_is_required_key():
    from cli.platforms.base import REQUIRED_TOOL_KEYS
    assert "semantic_search" in REQUIRED_TOOL_KEYS


def test_codebase_memory_resolves_in_render_context_claude():
    ctx = get_platform("claude-code").build_render_context(["codebase-memory-mcp"], "python")
    t = ctx["tools"]
    assert t["search_code"] == "mcp__codebase-memory-mcp__search_code"
    assert t["semantic_search"] == "mcp__codebase-memory-mcp__search_graph"
    assert t["find_blast_radius"] == "mcp__codebase-memory-mcp__detect_changes"
    assert t["trace_flow"] == "mcp__codebase-memory-mcp__trace_path"
    assert t["get_symbol"] == "mcp__codebase-memory-mcp__get_code_snippet"
    assert t["graph_stats"] == "mcp__codebase-memory-mcp__get_graph_schema"


def test_codebase_memory_resolves_in_render_context_antigravity():
    ctx = get_platform("antigravity").build_render_context(["codebase-memory-mcp"], "python")
    t = ctx["tools"]
    assert t["search_code"] == "mcp_codebase-memory-mcp_search_code"
    assert t["semantic_search"] == "mcp_codebase-memory-mcp_search_graph"
    assert t["find_blast_radius"] == "mcp_codebase-memory-mcp_detect_changes"


def test_dynamic_memory_resolves_in_render_context_claude():
    ctx = get_platform("claude-code").build_render_context(["agent-memory"], "python")
    assert ctx["tools"]["dynamic_memory_save"] == "mcp__agent-memory__memory_save"
    assert ctx["tools"]["dynamic_memory_search"] == "mcp__agent-memory__memory_smart_search"
    assert ctx["tools"]["dynamic_memory_forget"] == "mcp__agent-memory__memory_governance_delete"
    # agentmemory exposes memory_diagnose (no memory_health) for infra health checks
    assert ctx["tools"]["dynamic_memory_health"] == "mcp__agent-memory__memory_diagnose"


def test_dynamic_memory_resolves_even_when_agent_memory_not_selected():
    # REQUIRED => the op is always in the `tools` namespace; runtime degrade
    # (R-Tool-6 / M7) handles the provider being absent, NOT template rendering.
    ctx = get_platform("generic").build_render_context([], "other")
    assert ctx["tools"]["dynamic_memory_save"] == "memory_save"


UA_DOMAIN_OPS = ("domain_overview", "domain_flow", "domain_relationships")


def test_ua_domain_ops_are_optional_keys():
    from cli.platforms.base import OPTIONAL_TOOL_KEYS
    for op in UA_DOMAIN_OPS:
        assert op in OPTIONAL_TOOL_KEYS, f"{op} must be an OPTIONAL tool key"


def test_every_platform_resolves_ua_domain_ops():
    for key, cls in PLATFORMS.items():
        platform = cls()
        for op in UA_DOMAIN_OPS:
            resolved = platform.get_tool(op)
            assert resolved, f"{key} did not resolve {op}"


def test_ua_domain_ops_use_understand_anything_server_where_prefixed():
    # claude-code uses mcp__<server>__<tool>; antigravity uses mcp_<server>_<tool>
    assert get_platform("claude-code").get_tool("domain_overview") == (
        "mcp__understand-anything__get_domain_overview"
    )
    assert get_platform("antigravity").get_tool("domain_flow") == (
        "mcp_understand-anything_get_domain_flow_detail"
    )
    # codex + generic use bare tool names
    assert get_platform("codex").get_tool("domain_relationships") == "get_relationships"
    assert get_platform("generic").get_tool("domain_overview") == "get_domain_overview"


def test_build_render_context_includes_is_windows_flag():
    import platform as _platform
    ctx = get_platform("claude-code").build_render_context([], "python")
    assert "is_windows" in ctx
    assert ctx["is_windows"] == (_platform.system() == "Windows")
    assert isinstance(ctx["is_windows"], bool)


def test_is_windows_flag_present_for_every_platform():
    from cli.platforms import PLATFORMS
    for key in PLATFORMS:
        ctx = get_platform(key).build_render_context([], "python")
        assert "is_windows" in ctx, f"{key} missing is_windows"
