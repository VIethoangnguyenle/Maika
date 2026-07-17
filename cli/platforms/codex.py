"""Codex Platform — OpenAI Codex CLI agent."""

from .base import BasePlatform


class CodexPlatform(BasePlatform):

    name = "codex"
    display_name = "OpenAI Codex CLI"
    config_entry_point = "AGENTS.md"
    native_skill_export = None
    worker_binary = "codex"
    worker_base_args = ["exec"]

    tool_mapping = {
        # Codex CLI does not publicly document its internal tool names the
        # way Claude Code/Antigravity do — keep abstract passthrough (same
        # approach as GenericPlatform) rather than inventing concrete names.
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
        "fresh_session": True,
        "task_dispatch": True,
        "review_dispatch": True,
        "model_selection": True,
        "write_gate_hook": True,
    }

    notes = [
        "AGENTS.md is the config entry point (developers.openai.com/codex/guides/agents-md)",
        "Maika canonical runtime lives in .maika/",
        "tool_mapping is abstract passthrough — Codex CLI's internal tool names are not "
        "publicly documented; map manually if your Maika skills need concrete tool calls",
        "Skills/workflows are shared from the .maika/ project core",
    ]
