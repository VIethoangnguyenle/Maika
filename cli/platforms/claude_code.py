"""Claude Code Platform — Anthropic Claude Code agent."""

from .base import BasePlatform


class ClaudeCodePlatform(BasePlatform):

    name = "claude-code"
    display_name = "Anthropic Claude Code"
    config_entry_point = "CLAUDE.md"
    native_skill_export = None
    worker_binary = "claude"
    worker_base_args = ["-p", "--prompt-file"]
    dangerous_permission_flag = "--dangerously-skip-permissions"

    tool_mapping = {
        # ── File Operations ──
        "read_file":         "Read",
        "write_file":        "Write",
        "edit_file":         "Edit",
        "multi_edit_file":   "MultiEdit",
        "search_text":       "Grep",
        "list_directory":    "LS",

        # ── Terminal ──
        "run_command":       "Bash",
        "command_status":    "Bash",
        "send_input":        "Bash",

        # ── Code Exploration (codebase-memory-mcp) ──
        "search_code":       "mcp__codebase-memory-mcp__search_code",
        "semantic_search":   "mcp__codebase-memory-mcp__search_graph",
        "index_code":        "mcp__codebase-memory-mcp__index_repository",
        "code_status":       "mcp__codebase-memory-mcp__index_status",
        "get_dependencies":  "mcp__codebase-memory-mcp__query_graph",
        "trace_flow":        "mcp__codebase-memory-mcp__trace_path",
        "find_blast_radius": "mcp__codebase-memory-mcp__detect_changes",
        "get_symbol":        "mcp__codebase-memory-mcp__get_code_snippet",
        "list_symbols":      "mcp__codebase-memory-mcp__search_graph",
        "graph_stats":       "mcp__codebase-memory-mcp__get_graph_schema",
        "graph_build":       "mcp__codebase-memory-mcp__index_repository",

        # ── Domain / top-down (understand-anything MCP) ──
        "domain_overview":      "mcp__understand-anything__get_domain_overview",
        "domain_flow":          "mcp__understand-anything__get_domain_flow_detail",
        "domain_relationships": "mcp__understand-anything__get_relationships",

        # ── Serena MCP — semantic code reads/diagnostics ──
        "serena_symbols_overview":         "mcp__serena__get_symbols_overview",
        "serena_find_symbol":              "mcp__serena__find_symbol",
        "serena_find_references":          "mcp__serena__find_referencing_symbols",
        "serena_find_declaration":         "mcp__serena__find_declaration",
        "serena_find_implementations":     "mcp__serena__find_implementations",
        "serena_file_diagnostics":         "mcp__serena__get_diagnostics_for_file",
        "serena_symbol_diagnostics":       "mcp__serena__get_diagnostics_for_symbol",
        "serena_restart_language_server":  "mcp__serena__restart_language_server",

        # ── Document Search (Confluence — if available) ──
        "search_docs":       "mcp__confluence__search",
        "get_page":          "mcp__confluence__get_page",
        "list_spaces":       "mcp__confluence__list_spaces",
        "get_space_pages":   "mcp__confluence__get_space_pages",

        # ── Database (db_access MCP — server-level reference) ──
        "db_list_databases": "mcp__db-access__list_databases",
        "db_list_tables":    "mcp__db-access__sql_list_tables",
        "db_get_columns":    "mcp__db-access__sql_get_columns",
        "db_get_constraints":"mcp__db-access__sql_get_constraints",
        "db_sql_read":       "mcp__db-access__sql_read",
        "db_mongo_read":     "mcp__db-access__mongo_read",
        "db_sql_write":      "mcp__db-access__sql_write",
        "db_mongo_write":    "mcp__db-access__mongo_write",
        "db_sql_execute_script": "mcp__db-access__sql_execute_script",

        # ── Web ──
        "search_web":        "WebSearch",
        "read_url":          "WebFetch",

        # ── Dynamic Memory (agent-memory MCP — tool-level; optional at runtime) ──
        "dynamic_memory_search":   "mcp__agent-memory__memory_smart_search",
        "dynamic_memory_recall":   "mcp__agent-memory__memory_recall",
        "dynamic_memory_sessions": "mcp__agent-memory__memory_sessions",
        "dynamic_memory_audit":    "mcp__agent-memory__memory_audit",
        "dynamic_memory_health":   "mcp__agent-memory__memory_diagnose",
        "dynamic_memory_save":     "mcp__agent-memory__memory_save",
        "dynamic_memory_forget":   "mcp__agent-memory__memory_governance_delete",
    }

    capabilities = {
        "subagent": True,       # Claude Code has Task tool
        "artifacts": False,     # No artifact system like Antigravity
        "browser": False,
        "fresh_session": True,
        "task_dispatch": True,
        "review_dispatch": True,
        "model_selection": True,
        "write_gate_hook": True,
    }

    mcp_tool_prefix = "mcp__"

    notes = [
        "CLAUDE.md is the config entry point",
        "Maika canonical runtime lives in .maika/",
        "MCP tools use double underscore prefix: mcp__<server>__<tool>",
        "Claude Code uses Task tool for subagent delegation",
    ]
