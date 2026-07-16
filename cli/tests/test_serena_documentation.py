"""Documentation contracts for the pinned Serena Phase 1 integration."""

import json
from pathlib import Path
import re
import tomllib

from cli.agent_content.provider_capabilities import UA_TOOLS
from cli.mcp.integration.serena import SERENA_READ_TOOLS


ROOT = Path(__file__).resolve().parents[2]
GUIDE = ROOT / "docs" / "providers" / "serena.md"


def _guide_text() -> str:
    return GUIDE.read_text(encoding="utf-8")


def test_serena_guide_covers_provider_authority_and_phase_boundary():
    text = _guide_text()
    for term in (
        "UA-MCP",
        "18 tools",
        "Serena",
        "CBM",
        "AgentMemory",
        "current source",
        "current tests",
        "hidden consumers",
    ):
        assert term in text
    for tool in sorted(UA_TOOLS | SERENA_READ_TOOLS):
        assert f"`{tool}`" in text
    assert "Phase 2" in text and "not enabled" in text
    assert "all three hosts" in text
    assert "pathless symbol writes" in text
    assert "bypass characterization" in text


def test_serena_guide_covers_install_and_all_language_project_commands():
    text = _guide_text()
    for term in (
        "serena-agent==1.5.3",
        ">=3.11,<3.15",
        "uv tool install --python 3.13 'serena-agent==1.5.3'",
        ".maika/config/serena-context.yml",
        ".serena/project.yml",
    ):
        assert term in text
    for language in ("java", "typescript", "python", "go", "csharp"):
        assert (
            f"serena project create /absolute/project/path --language {language}"
            in text
        )
    assert "serena project create /absolute/project/path" in text
    assert "--language other" not in text


def test_serena_guide_covers_exact_workspace_configs_and_verification():
    text = _guide_text()
    for term in (
        "Codex",
        "Claude Code",
        "Antigravity",
        ".codex/config.toml",
        ".mcp.json",
        ".agents/mcp_config.json",
        "[mcp_servers.serena]",
        '"mcpServers"',
        'command = "serena"',
        '"command": "serena"',
        '"start-mcp-server"',
        '"--project"',
        '"--context"',
        '"no-memories"',
        '"--enable-web-dashboard"',
        "serena tools list --all --quiet",
        "maika doctor mcp --target /absolute/project/path",
        "contract: READY (8 read-only tools)",
        "find_symbol",
        "find_referencing_symbols",
        "get_diagnostics_for_file",
    ):
        assert term in text


def test_serena_workspace_snippets_parse_and_use_the_fixed_renderer_arguments():
    text = _guide_text()
    codex_block = re.search(
        r"### Codex.*?```toml\n(.*?)\n```", text, flags=re.DOTALL
    )
    assert codex_block is not None
    codex_server = tomllib.loads(codex_block.group(1))["mcp_servers"]["serena"]

    json_blocks = re.findall(
        r"### (?:Claude Code|Antigravity).*?```json\n(.*?)\n```",
        text,
        flags=re.DOTALL,
    )
    assert len(json_blocks) == 2
    servers = [codex_server]
    servers.extend(json.loads(block)["mcpServers"]["serena"] for block in json_blocks)

    expected_args = [
        "start-mcp-server",
        "--project",
        "/absolute/project/path",
        "--context",
        "/absolute/project/path/.maika/config/serena-context.yml",
        "--mode",
        "no-memories",
        "--enable-web-dashboard",
        "false",
        "--open-web-dashboard",
        "false",
    ]
    for server in servers:
        assert server == {"command": "serena", "args": expected_args}


def test_serena_guide_covers_operations_security_and_lifecycle():
    text = _guide_text()
    for term in (
        "binary missing",
        "project config missing",
        "language server unavailable",
        "empty symbols",
        "stale LSP",
        "unexpected/write tools",
        "Windows path quoting",
        "logs without secrets",
        "tools-list-readonly-v1.json",
        "tools-list-readonly-v1.provenance.yaml",
        "SERENA_READONLY_V1_TOOL_SURFACE_HASH",
        "test_provider_contract_fixtures.py",
        "test_platforms.py",
        "test_mcp_doctor.py",
        "uv tool uninstall serena-agent",
        "preserve `.serena`",
        "delete `.serena`",
        "does not automatically mutate native workspace or global MCP configs",
    ):
        assert term in text


def test_readme_has_concise_supported_host_matrix_and_guide_link():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "docs/providers/serena.md" in text
    assert "Codex | Claude Code | Antigravity" in text
    assert "read-only symbols/references/diagnostics" in text
    assert "Phase 1" in text
