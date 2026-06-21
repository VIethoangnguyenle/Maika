"""Helpers for MCP capabilities that declare a `setup` block in the manifest.

Generic over the `setup` schema (no hard-coded server/path values) so any
capability can opt in; understand-anything is the first consumer.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional


def expand(template: str, *, home: Optional[Path] = None, platform: str = "",
           ua_mcp_dir: str = "", project_root: str = "") -> str:
    """Substitute the four supported placeholders in a manifest template string."""
    return (
        template
        .replace("{home}", str(home) if home is not None else "")
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
    path = Path(expand(spec["path"], home=home))
    kind = spec.get("kind", "path_exists")
    if kind == "path_exists":
        return path.exists() or path.is_symlink()
    if kind == "file_contains":
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
