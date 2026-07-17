"""Antigravity Platform — Google Antigravity (Gemini-based agent)."""

from .base import BasePlatform


class AntigravityPlatform(BasePlatform):

    name = "antigravity"
    display_name = "Google Antigravity (Gemini)"
    config_entry_point = "AGENTS.md"
    native_skill_export = None
    worker_binary = "agy"
    worker_base_args = []

    tool_mapping = {
        # ── File Operations ──
        "read_file":         "view_file",
        "write_file":        "write_to_file",
        "edit_file":         "replace_file_content",
        "multi_edit_file":   "multi_replace_file_content",
        "search_text":       "grep_search",
        "list_directory":    "list_dir",
        "get_symbol":        "view_file",  # exact_source_inspection tool (current-source authority)

        # ── Terminal ──
        "run_command":       "run_command",
        "command_status":    "command_status",
        "send_input":        "send_command_input",

        # ── Domain / top-down (understand-anything MCP) ──
        "domain_overview":      "mcp_understand-anything_get_domain_overview",
        "domain_flow":          "mcp_understand-anything_get_domain_flow_detail",
        "domain_relationships": "mcp_understand-anything_get_relationships",

        # ── Serena MCP — semantic code reads/diagnostics ──
        "serena_symbols_overview":         "mcp_serena_get_symbols_overview",
        "serena_find_symbol":              "mcp_serena_find_symbol",
        "serena_find_references":          "mcp_serena_find_referencing_symbols",
        "serena_find_declaration":         "mcp_serena_find_declaration",
        "serena_find_implementations":     "mcp_serena_find_implementations",
        "serena_file_diagnostics":         "mcp_serena_get_diagnostics_for_file",
        "serena_symbol_diagnostics":       "mcp_serena_get_diagnostics_for_symbol",
        "serena_maintenance_restart_language_server": "mcp_serena_restart_language_server",

        # ── Document Search (Confluence) ──
        "search_docs":       "mcp_confluence-servicehub_confluence_search",
        "get_page":          "mcp_confluence-servicehub_confluence_get_page",
        "list_spaces":       "mcp_confluence-servicehub_confluence_list_spaces",
        "get_space_pages":   "mcp_confluence-servicehub_confluence_get_space_pages",

        # ── Database (db_access MCP — server-level reference) ──
        "db_list_databases": "mcp_db-access_list_databases",
        "db_list_tables":    "mcp_db-access_sql_list_tables",
        "db_get_columns":    "mcp_db-access_sql_get_columns",
        "db_get_constraints":"mcp_db-access_sql_get_constraints",
        "db_sql_read":       "mcp_db-access_sql_read",
        "db_mongo_read":     "mcp_db-access_mongo_read",
        "db_sql_write":      "mcp_db-access_sql_write",
        "db_mongo_write":    "mcp_db-access_mongo_write",
        "db_sql_execute_script": "mcp_db-access_sql_execute_script",

        # ── Web & Browser ──
        "search_web":        "search_web",
        "read_url":          "read_url_content",
        "browser_agent":     "browser_subagent",

        # ── Image ──
        "generate_image":    "generate_image",

        # ── Dynamic Memory (agent-memory MCP — tool-level; optional at runtime) ──
        "dynamic_memory_search":   "mcp_agent-memory_memory_smart_search",
        "dynamic_memory_recall":   "mcp_agent-memory_memory_recall",
        "dynamic_memory_sessions": "mcp_agent-memory_memory_sessions",
        "dynamic_memory_audit":    "mcp_agent-memory_memory_audit",
        "dynamic_memory_health":   "mcp_agent-memory_memory_diagnose",
        "dynamic_memory_save":     "mcp_agent-memory_memory_save",
        "dynamic_memory_forget":   "mcp_agent-memory_memory_governance_delete",
    }

    capabilities = {
        "subagent": True,
        "artifacts": True,
        "browser": True,
        "fresh_session": True,
        "task_dispatch": True,
        "review_dispatch": True,
        "model_selection": True,
        "write_gate_hook": True,
    }

    mcp_tool_prefix = "mcp_"

    notes = [
        "AGENTS.md is loaded via user_rules in Antigravity config",
        "Maika canonical runtime lives in .maika/",
        "MCP tools use prefix: mcp_<server>_<tool>",
        "Supports browser_subagent for visual tasks",
    ]
