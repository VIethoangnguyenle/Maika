"""Base platform definition — abstract interface for all agent platforms."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Set
import platform as _platform

from cli import FRAMEWORK_VERSION
from cli.capability_runtime import build_capability_routes, load_capability_registry


REQUIRED_TOOL_KEYS = frozenset({
    "read_file",
    "write_file",
    "edit_file",
    "multi_edit_file",
    "search_text",
    "list_directory",
    "run_command",
    "command_status",
    "send_input",
    "search_code",
    "semantic_search",
    "index_code",
    "code_status",
    "get_dependencies",
    "trace_flow",
    "find_blast_radius",
    "get_symbol",
    "list_symbols",
    "graph_stats",
    "graph_build",
    "search_docs",
    "get_page",
    "list_spaces",
    "get_space_pages",
    "db_query",
    "search_web",
    "read_url",
    # ── Dynamic (episodic/advisory) memory — provider-mapped, runtime-optional ──
    "dynamic_memory_search",
    "dynamic_memory_recall",
    "dynamic_memory_sessions",
    "dynamic_memory_audit",
    "dynamic_memory_health",
    "dynamic_memory_save",
    "dynamic_memory_forget",
})

OPTIONAL_TOOL_KEYS = frozenset({
    "browser_agent",
    "generate_image",
    # ── Understand-Anything MCP — domain/top-down (runtime-optional) ──
    "domain_overview",
    "domain_flow",
    "domain_relationships",
})


class PlatformToolMappingError(ValueError):
    """Raised when a platform adapter cannot resolve required Maika tool keys."""


class BasePlatform(ABC):
    """Each platform provides tool mapping + config format + capabilities.

    A platform represents a specific AI agent runtime environment
    (Antigravity, Claude Code, Cursor, etc.) and defines how
    abstract Maika operations map to concrete tool calls.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Platform identifier (e.g., 'antigravity', 'claude-code')."""

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name (e.g., 'Google Antigravity')."""

    @property
    @abstractmethod
    def config_entry_point(self) -> str:
        """File the platform reads as system prompt / agent config.

        Antigravity: AGENTS.md (loaded via user_rules)
        Claude Code: CLAUDE.md
        Cursor: .cursorrules
        """

    @property
    @abstractmethod
    def tool_mapping(self) -> Dict[str, str]:
        """Map abstract operation → concrete tool name.

        Keys are abstract operations used in Jinja2 templates.
        Values are the exact tool names for this platform.
        """

    @property
    def capabilities(self) -> Dict[str, bool]:
        """Platform-specific capabilities."""
        return {
            "subagent": False,
            "artifacts": False,
            "browser": False,
            "fresh_session": False,
            "task_dispatch": False,
            "review_dispatch": False,
            "model_selection": False,
            "write_gate_hook": False,
        }

    @property
    def mcp_tool_prefix(self) -> str:
        """How this platform prefixes MCP tool names.

        Antigravity: 'mcp_<server>_<tool>'
        Claude Code: 'mcp__<server>__<tool>'
        """
        return ""

    @property
    def native_skill_export(self) -> Optional[dict]:
        """Where (if anywhere) this platform natively auto-discovers skills.

        None = no native discovery; skills/workflows are reachable only via
        bootstrap.md's manual PHASE 1 self-registration (works on every
        platform, including this one).

        dir: root directory; the skill/workflow name is appended automatically.
        strip_frontmatter: True means export as a flat <name>.md with YAML
          frontmatter removed — pre_conditions (if any) are re-rendered into
          the body as a checklist instead of being silently dropped (see
          export_as_flat_command in cli/scaffold.py).
        flatten: True means output is <dir>/<name>.md (no subfolder); False
          means <dir>/<name>/SKILL.md.
        """
        return None

    @property
    def framework_root(self) -> str:
        """Canonical Maika runtime root inside a target project.

        This is where rules, skills, workflows, procedures, tools, profiles,
        knowledge, and resolved-config.yaml are scaffolded for the platform.
        """
        return ".maika"

    @property
    def notes(self) -> List[str]:
        """Platform-specific notes shown during init."""
        return []

    @property
    def unsupported_tools(self) -> Set[str]:
        """Required abstract operations intentionally unsupported by this platform."""
        return set()

    def get_tool(self, abstract_name: str) -> str:
        """Resolve abstract operation to concrete tool name."""
        if abstract_name in self.tool_mapping:
            return self.tool_mapping[abstract_name]
        raise PlatformToolMappingError(
            f"{self.name} has no mapping for abstract tool operation: {abstract_name}"
        )

    def validate_tool_mapping(self) -> None:
        """Fail early when a platform adapter drifts from Maika's tool contract."""
        tool_keys = set(self.tool_mapping)
        allowed_keys = REQUIRED_TOOL_KEYS | OPTIONAL_TOOL_KEYS
        missing = REQUIRED_TOOL_KEYS - tool_keys - self.unsupported_tools
        extra = tool_keys - allowed_keys
        extra_unsupported = self.unsupported_tools - REQUIRED_TOOL_KEYS
        if missing:
            raise PlatformToolMappingError(
                f"{self.name} missing required tool mappings: {', '.join(sorted(missing))}"
            )
        if extra:
            raise PlatformToolMappingError(
                f"{self.name} declares unknown tool mappings: {', '.join(sorted(extra))}"
            )
        if extra_unsupported:
            raise PlatformToolMappingError(
                f"{self.name} declares unknown unsupported tools: "
                f"{', '.join(sorted(extra_unsupported))}"
            )

    def build_render_context(self, mcps: List[str], language: str, hook_python: Optional[str] = None) -> dict:
        """Build the full Jinja2 render context for this platform."""
        self.validate_tool_mapping()
        return {
            "platform": {
                "name": self.name,
                "display_name": self.display_name,
                "config_entry_point": self.config_entry_point,
                "framework_root": self.framework_root,
            },
            "tools": self.tool_mapping,
            "capabilities": self.capabilities,
            "capability_registry": load_capability_registry(),
            "capability_routes": build_capability_routes(self),
            "mcps": mcps,
            "language": language,
            "framework_version": FRAMEWORK_VERSION,
            "is_windows": _platform.system() == "Windows",
            "hook_python": hook_python or "python",
        }
