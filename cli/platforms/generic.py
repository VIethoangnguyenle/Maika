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
        "get_symbol":        "get_symbol",

        # ── Domain / top-down (understand-anything MCP) ──
        "domain_overview":      "get_domain_overview",
        "domain_flow":          "get_domain_flow_detail",
        "domain_relationships": "get_relationships",

        # ── Serena MCP — semantic code reads/diagnostics ──
        "serena_symbols_overview":         "get_symbols_overview",
        "serena_find_symbol":              "find_symbol",
        "serena_find_references":          "find_referencing_symbols",
        "serena_find_declaration":         "find_declaration",
        "serena_find_implementations":     "find_implementations",
        "serena_file_diagnostics":         "get_diagnostics_for_file",
        "serena_symbol_diagnostics":       "get_diagnostics_for_symbol",
        "serena_maintenance_restart_language_server": "restart_language_server",

        "search_docs":       "search_docs",
        "get_page":          "get_page",
        "list_spaces":       "list_spaces",
        "get_space_pages":   "get_space_pages",
        # ── Database (db_access MCP — server-level reference) ──
        "db_list_databases": "list_databases",
        "db_list_tables":    "sql_list_tables",
        "db_get_columns":    "sql_get_columns",
        "db_get_constraints":"sql_get_constraints",
        "db_sql_read":       "sql_read",
        "db_mongo_read":     "mongo_read",
        "db_sql_write":      "sql_write",
        "db_mongo_write":    "mongo_write",
        "db_sql_execute_script": "sql_execute_script",

        "search_web":        "search_web",
        "read_url":          "read_url",

        # ── Dynamic Memory (agent-memory MCP — tool-level; optional at runtime) ──
        "dynamic_memory_search":   "memory_smart_search",
        "dynamic_memory_recall":   "memory_recall",
        "dynamic_memory_sessions": "memory_sessions",
        "dynamic_memory_audit":    "memory_audit",
        "dynamic_memory_health":   "memory_diagnose",
        "dynamic_memory_save":     "memory_save",
        "dynamic_memory_forget":   "memory_governance_delete",
    }

    capabilities = {
        "subagent": False,
        "artifacts": False,
        "browser": False,
        "fresh_session": False,
        "task_dispatch": False,
        "review_dispatch": False,
        "model_selection": False,
        "write_gate_hook": False,
    }

    notes = [
        "Generic platform — tool names are abstract placeholders",
        "You will need to manually map tool names for your agent runtime",
        "Use this as a starting point for creating a custom platform adapter",
    ]
