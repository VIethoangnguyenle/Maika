"""Antigravity Platform — Google Antigravity (Gemini-based agent)."""

from .base import BasePlatform


class AntigravityPlatform(BasePlatform):

    name = "antigravity"
    display_name = "Google Antigravity (Gemini)"
    config_entry_point = "AGENTS.md"
    framework_root = ".agents"
    native_skill_export = None

    tool_mapping = {
        # ── File Operations ──
        "read_file":         "view_file",
        "write_file":        "write_to_file",
        "edit_file":         "replace_file_content",
        "multi_edit_file":   "multi_replace_file_content",
        "search_text":       "grep_search",
        "list_directory":    "list_dir",

        # ── Terminal ──
        "run_command":       "run_command",
        "command_status":    "command_status",
        "send_input":        "send_command_input",

        # ── Code Exploration (codebase-memory-mcp) ──
        "search_code":       "mcp_codebase-memory-mcp_search_code",
        "semantic_search":   "mcp_codebase-memory-mcp_semantic_query",
        "index_code":        "mcp_codebase-memory-mcp_index_repository",
        "code_status":       "mcp_codebase-memory-mcp_index_status",
        "get_dependencies":  "mcp_codebase-memory-mcp_query_graph",
        "trace_flow":        "mcp_codebase-memory-mcp_trace_path",
        "find_blast_radius": "mcp_codebase-memory-mcp_detect_changes",
        "get_symbol":        "mcp_codebase-memory-mcp_get_code_snippet",
        "list_symbols":      "mcp_codebase-memory-mcp_search_graph",
        "graph_stats":       "mcp_codebase-memory-mcp_get_graph_schema",
        "graph_build":       "mcp_codebase-memory-mcp_index_repository",

        # ── Domain / top-down (understand-anything MCP) ──
        "domain_overview":      "mcp_understand-anything_get_domain_overview",
        "domain_flow":          "mcp_understand-anything_get_domain_flow_detail",
        "domain_relationships": "mcp_understand-anything_get_relationships",

        # ── Document Search (Confluence) ──
        "search_docs":       "mcp_confluence-servicehub_confluence_search",
        "get_page":          "mcp_confluence-servicehub_confluence_get_page",
        "list_spaces":       "mcp_confluence-servicehub_confluence_list_spaces",
        "get_space_pages":   "mcp_confluence-servicehub_confluence_get_space_pages",

        # ── Database (db_access MCP — server-level reference) ──
        "db_query":          "db-remote",

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
        "Maika runtime scaffolds into .agents/",
        "MCP tools use prefix: mcp_<server>_<tool>",
        "Supports browser_subagent for visual tasks",
    ]
