"""Helpers for MCP capabilities that declare a `setup` block in the manifest.

Generic over the `setup` schema (no hard-coded server/path values) so any
capability can opt in; understand-anything is the first consumer.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Optional


def expand(template: str, *, home: Optional[Path] = None, platform: str = "",
           ua_mcp_dir: str = "", project_root: str = "", language: str = "") -> str:
    """Substitute the supported placeholders in a manifest template string."""
    home_value = home.as_posix() if home is not None else ""
    return (
        template
        .replace("{home}", home_value)
        .replace("{platform}", platform)
        .replace("{ua_mcp_dir}", ua_mcp_dir)
        .replace("{project_root}", project_root)
        .replace("{language}", language)
    )


def has_setup(capability: dict) -> bool:
    return isinstance(capability, dict) and isinstance(capability.get("setup"), dict)


def resolve_engine_check(setup: dict, platform: str, home: Path) -> bool:
    """True if the engine marker for `platform` (fallback 'default') is present."""
    checks = setup.get("engine_check", {})
    spec = checks.get(platform) or checks.get("default")
    if not spec:
        return False
    kind = spec.get("kind", "path_exists")
    if kind == "command_exists":
        return shutil.which(spec.get("command", "")) is not None
    if kind == "path_exists":
        path = Path(expand(spec["path"], home=home))
        return path.exists() or path.is_symlink()
    if kind == "file_contains":
        path = Path(expand(spec["path"], home=home))
        try:
            return spec.get("needle", "") in path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return False
    return False


def engine_status_line(setup: dict, platform: str, home: Path) -> str:
    if resolve_engine_check(setup, platform, home):
        return "engine: ✓ installed"
    hint = setup.get("install_hint", {})
    install = expand(hint.get(platform) or hint.get("default", ""), platform=platform)
    return f"engine: ✗ not installed — {install}"


def render_server_snippet(setup: dict, *, server_key: str, platform: str,
                          ua_mcp_dir: str, project_root: str) -> str:
    """Render one server recipe in the enabled host's native config format."""
    server = setup["server"]
    args = [expand(a, ua_mcp_dir=ua_mcp_dir, project_root=project_root) for a in server["args"]]
    env = {
        k: expand(v, ua_mcp_dir=ua_mcp_dir, project_root=project_root)
        for k, v in (server.get("env") or {}).items()
    }
    if platform == "codex":
        lines = [
            f"[mcp_servers.{server_key}]",
            f"command = {json.dumps(server['command'], ensure_ascii=False)}",
            f"args = {json.dumps(args, ensure_ascii=False)}",
        ]
        if env:
            lines.append(f"\n[mcp_servers.{server_key}.env]")
            lines.extend(
                f"{key} = {json.dumps(value, ensure_ascii=False)}"
                for key, value in env.items()
            )
        return "\n".join(lines)

    recipe = {"command": server["command"], "args": args}
    if env:
        recipe["env"] = env
    return json.dumps(
        {"mcpServers": {server_key: recipe}}, indent=2, ensure_ascii=False,
    )


def _platform_display_name(platform: str) -> str:
    return {
        "codex": "Codex",
        "claude-code": "Claude Code",
        "antigravity": "Antigravity",
        "generic": "Generic",
    }.get(platform, platform)


def _render_prepare_hint(template: str, *, project_root: str, language: str) -> str:
    command = template.split("  #", 1)[0]
    if language == "other":
        command = command.replace(" --language {language}", "")
    return expand(command, project_root=project_root, language=language)


def render_mcp_setup_section(setup: dict, *, server_key: str,
                             platform_keys: list[str], ua_mcp_dir: str,
                             project_root: str, language: str) -> str:
    """Render one provider section for every enabled project host."""
    install_lines = []
    hint = setup.get("install_hint", {})
    for platform in platform_keys:
        install = expand(
            hint.get(platform) or hint.get("default", ""), platform=platform,
        )
        install_lines.append(f"#### {_platform_display_name(platform)}\n{install}")

    artifacts = setup.get("graph_artifacts", [])
    if artifacts:
        prepare_title = "Generate graphs"
        prepare_body = "\n".join(
            f"Run: {artifact['gen_cmd']:<18} -> {artifact['path']} ({artifact['name']})"
            for artifact in artifacts
        )
    elif setup.get("prepare_hint"):
        prepare_title = "Prepare the project"
        prepare_body = _render_prepare_hint(
            setup["prepare_hint"], project_root=project_root, language=language,
        )
        prepare_body += (
            "\n\nNo separate index build is required; the language server "
            "initializes when the project is activated."
        )
    else:
        prepare_title = "Index the codebase"
        prepare_body = setup.get("index_hint", "")

    snippets = []
    for platform in platform_keys:
        snippet = render_server_snippet(
            setup, server_key=server_key, platform=platform,
            ua_mcp_dir=ua_mcp_dir, project_root=project_root,
        )
        fence = "toml" if platform == "codex" else "json"
        snippets.append(
            f"#### {_platform_display_name(platform)}\n```{fence}\n{snippet}\n```"
        )

    joined_installs = "\n\n".join(install_lines)
    joined_snippets = "\n\n".join(snippets)
    return (
        f"## Provider: {server_key}\n\n"
        f"### 1. Install engine (if missing)\n\n"
        f"{joined_installs}\n\n"
        f"### 2. {prepare_title}\n\n{prepare_body}\n\n"
        f"### 3. Wire MCP server\n\n{joined_snippets}\n\n"
        f"### 4. Verify\n\nmaika doctor mcp --target {project_root}"
    )


def render_mcp_setup_md(setup: dict, *, server_key: str, platform: str,
                        ua_mcp_dir: str, project_root: str) -> str:
    """Render the human-facing MCP_SETUP.md guide for one capability."""
    hint = setup.get("install_hint", {})
    install = expand(hint.get(platform) or hint.get("default", ""), platform=platform)
    artifacts = setup.get("graph_artifacts", [])
    if artifacts:
        step2 = "## 2. Generate graphs\n" + "\n".join(
            f"Run: {a['gen_cmd']:<18} -> {a['path']} ({a['name']})" for a in artifacts
        )
    else:
        step2 = "## 2. Index the codebase\n" + setup.get("index_hint", "")
    snippet = render_server_snippet(
        setup, server_key=server_key, platform=platform,
        ua_mcp_dir=ua_mcp_dir, project_root=project_root,
    )
    fence = "toml" if platform == "codex" else "json"
    return (
        f"# MCP Setup — {server_key}\n\n"
        f"## 1. Install engine (if missing)\n{install}\n\n"
        f"{step2}\n\n"
        f"## 3. Wire MCP server (paste into the {platform} MCP config)\n"
        f"```{fence}\n{snippet}\n```\n\n"
        f"## 4. Verify\nmaika doctor mcp --target {project_root}\n"
    )


def graph_status_lines(setup: dict, target: Path) -> list:
    """One report line per graph artifact: nodes/edges, missing, or unparseable."""
    lines = []
    for art in setup.get("graph_artifacts", []):
        path = target / art["path"]
        if not path.exists():
            lines.append(f"{art['name']}: ✗ run {art['gen_cmd']}")
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            nodes = len(data.get("nodes") or [])
            edges = len(data.get("edges") or [])
            lines.append(f"{art['name']}: nodes={nodes} edges={edges}")
        except (json.JSONDecodeError, OSError):
            lines.append(f"{art['name']}: present (unparseable)")
    return lines
