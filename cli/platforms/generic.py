"""Generic Platform — fallback with abstract tool names preserved."""

from .base import BasePlatform


class GenericPlatform(BasePlatform):
    """Generic platform that keeps abstract operation names.

    Use this when the target platform is unknown or when you want
    platform-agnostic output that can be manually adapted later.
    """

    name = "generic"
    display_name = "Generic (Platform-agnostic)"
    config_entry_point = "AGENTS.md"

    tool_mapping = {
        # All operations keep their abstract names.
        # The output files will contain the abstract operation names,
        # which the agent or user must resolve manually.
        "read_file":         "read_file",
        "write_file":        "write_file",
        "edit_file":         "edit_file",
        "multi_edit_file":   "multi_edit_file",
        "search_text":       "search_text",
        "list_directory":    "list_directory",
        "run_command":       "run_command",
        "command_status":    "command_status",
        "send_input":        "send_input",
        "search_code":       "search_code",
        "semantic_search":   "semantic_search",
        "index_code":        "index_code",
        "code_status":       "code_status",
        "get_dependencies":  "get_dependencies",
        "trace_flow":        "trace_flow",
        "find_blast_radius": "find_blast_radius",
        "get_symbol":        "get_symbol",
        "list_symbols":      "list_symbols",
        "graph_stats":       "graph_stats",
        "graph_build":       "graph_build",
        "search_docs":       "search_docs",
        "get_page":          "get_page",
        "list_spaces":       "list_spaces",
        "get_space_pages":   "get_space_pages",
        # ── Database (db_access MCP — server-level reference) ──
        "db_query":          "db-remote",

        "search_web":        "search_web",
        "read_url":          "read_url",

        # ── Dynamic Memory (agent-memory MCP — tool-level; optional at runtime) ──
        "dynamic_memory_search":   "memory_smart_search",
        "dynamic_memory_recall":   "memory_recall",
        "dynamic_memory_sessions": "memory_sessions",
        "dynamic_memory_audit":    "memory_audit",
        "dynamic_memory_health":   "memory_health",
        "dynamic_memory_save":     "memory_save",
        "dynamic_memory_forget":   "memory_governance_delete",
    }

    capabilities = {
        "subagent": False,
        "artifacts": False,
        "browser": False,
        "write_gate_hook": False,
    }

    notes = [
        "Generic platform — tool names are abstract placeholders",
        "You will need to manually map tool names for your agent runtime",
        "Use this as a starting point for creating a custom platform adapter",
    ]
