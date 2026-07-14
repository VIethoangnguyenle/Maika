"""Platform-specific MCP config discovery for Maika doctor."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class McpConfigCandidate:
    path: Path
    scope: str
    format: str


@dataclass(frozen=True)
class McpPlatformAdapter:
    platform: str
    framework_root: str
    candidates: tuple[tuple[str, str, str], ...]

    def config_candidates(self, project_root: Path, home: Path) -> list[McpConfigCandidate]:
        values: list[McpConfigCandidate] = []
        for scope, raw_path, fmt in self.candidates:
            if raw_path.startswith("~/"):
                path = home / raw_path.removeprefix("~/")
            else:
                path = project_root / raw_path
            values.append(McpConfigCandidate(path=path, scope=scope, format=fmt))
        return values


_ADAPTERS = {
    "antigravity": McpPlatformAdapter(
        platform="antigravity",
        framework_root=".maika",
        candidates=(
            ("workspace", ".agents/mcp_config.json", "json"),
            ("cli", "~/.gemini/antigravity-cli/mcp_config.json", "json"),
            ("ide", "~/.gemini/antigravity/mcp_config.json", "json"),
            ("shared", "~/.gemini/config/mcp_config.json", "json"),
        ),
    ),
    "claude-code": McpPlatformAdapter(
        platform="claude-code",
        framework_root=".maika",
        candidates=(
            ("workspace", ".mcp.json", "json"),
            ("user", "~/.claude/mcp_config.json", "json"),
        ),
    ),
    "codex": McpPlatformAdapter(
        platform="codex",
        framework_root=".maika",
        candidates=(
            ("workspace", ".codex/config.toml", "toml"),
            ("user", "~/.codex/config.toml", "toml"),
        ),
    ),
    "generic": McpPlatformAdapter(
        platform="generic",
        framework_root=".maika",
        candidates=(),
    ),
}


def get_mcp_adapter(platform: str) -> McpPlatformAdapter:
    try:
        return _ADAPTERS[platform]
    except KeyError as exc:
        raise ValueError(f"Unknown MCP platform adapter: {platform}") from exc
