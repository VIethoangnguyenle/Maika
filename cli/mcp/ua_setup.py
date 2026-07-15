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
           ua_mcp_dir: str = "", project_root: str = "") -> str:
    """Substitute the four supported placeholders in a manifest template string."""
    home_value = home.as_posix() if home is not None else ""
    return (
        template
        .replace("{home}", home_value)
        .replace("{platform}", platform)
        .replace("{ua_mcp_dir}", ua_mcp_dir)
        .replace("{project_root}", project_root)
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


def render_server_snippet(setup: dict, *, server_key: str, ua_mcp_dir: str,
                          project_root: str) -> dict:
    """Build the mcpServers dict for the capability's `server` recipe."""
    server = setup["server"]
    args = [expand(a, ua_mcp_dir=ua_mcp_dir, project_root=project_root) for a in server["args"]]
    env = {
        k: expand(v, ua_mcp_dir=ua_mcp_dir, project_root=project_root)
        for k, v in (server.get("env") or {}).items()
    }
    return {"mcpServers": {server_key: {"command": server["command"], "args": args, "env": env}}}


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
        setup, server_key=server_key, ua_mcp_dir=ua_mcp_dir, project_root=project_root,
    )
    body = json.dumps(snippet, indent=2, ensure_ascii=False)
    return (
        f"# MCP Setup — {server_key}\n\n"
        f"## 1. Install engine (if missing)\n{install}\n\n"
        f"{step2}\n\n"
        f"## 3. Wire MCP server (paste into the {platform} MCP config)\n"
        f"```json\n{body}\n```\n\n"
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
