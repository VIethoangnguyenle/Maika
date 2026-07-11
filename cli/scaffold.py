"""Shared, non-interactive scaffolding core for Maika.

Used by both `maika init` (writes directly to target) and `maika update`
(writes to a staging dir, then syncs). Contains no input() calls.
"""

import importlib.util
import json
import shutil
from pathlib import Path
from typing import List, Optional

import yaml

from cli import FRAMEWORK_VERSION, CANONICAL_FRAMEWORK_ROOT
from cli.renderer import render_string
from cli.renderer import _TEXT_EXTENSIONS as _RENDERED_SUFFIXES


# Maps plugin source prefixes to actual directories in the Maika repo.
SOURCE_MAP = {
    "rules/":               ".maika/rules/",
    "skills/":              ".maika/skills/",
    "workflows/":           ".maika/workflows/",
    "procedures/":          ".maika/procedures/",
    "profiles/":            ".maika/profiles/",
    "config/":              ".maika/config/",
    "tools/":               ".maika/tools/",
    "hooks/":               ".maika/hooks/",
    "knowledge-templates/": ".maika/knowledge/templates/",
    "knowledge-active/":    ".maika/knowledge/active/",
    "knowledge-long-term/": ".maika/knowledge/long-term/",
    "agent/":               ".maika/agent/",
    "runtime/":             ".maika/runtime/",
}

# File extensions eligible for single-file Jinja auto-render.
_RENDERABLE_SUFFIXES = {".md", ".yaml", ".yml", ".txt"}

MANAGED_BLOCK_BEGIN = "<!-- maika:begin -->"
MANAGED_BLOCK_END = "<!-- maika:end -->"

from cli.install.json_merge import merge_managed_json, remove_maika_json_entry


def merge_managed_markdown(existing: str, managed: str) -> str:
    """Insert or replace Maika's block without changing host-owned content."""
    begin_count = existing.count(MANAGED_BLOCK_BEGIN)
    end_count = existing.count(MANAGED_BLOCK_END)
    if begin_count != end_count or begin_count > 1:
        raise ValueError("malformed Maika managed block in host entrypoint")
    block = f"{MANAGED_BLOCK_BEGIN}\n{managed.rstrip()}\n{MANAGED_BLOCK_END}\n"
    if begin_count == 1:
        start = existing.index(MANAGED_BLOCK_BEGIN)
        end = existing.index(MANAGED_BLOCK_END, start) + len(MANAGED_BLOCK_END)
        suffix = existing[end:]
        if suffix.startswith("\n"):
            suffix = suffix[1:]
        return existing[:start] + block + suffix
    if not existing:
        return block
    separator = "\n" if existing.endswith("\n") else "\n\n"
    return existing + separator + block


def stage_managed_entrypoint(staging: Path, target: Path, entrypoint: str) -> None:
    """Merge a staged Maika entrypoint with an existing shared host file."""
    staged_path = staging / entrypoint
    if not staged_path.exists():
        return
    target_path = target / entrypoint
    existing = target_path.read_text(encoding="utf-8") if target_path.exists() else ""
    managed = staged_path.read_text(encoding="utf-8")
    staged_path.write_text(merge_managed_markdown(existing, managed), encoding="utf-8")


def strip_managed_markdown(existing: str) -> str:
    """Remove Maika's managed block, preserving host-owned content (inverse of
    merge_managed_markdown). No block present → returned unchanged."""
    if MANAGED_BLOCK_BEGIN not in existing:
        return existing
    start = existing.index(MANAGED_BLOCK_BEGIN)
    end = existing.index(MANAGED_BLOCK_END, start) + len(MANAGED_BLOCK_END)
    suffix = existing[end:]
    if suffix.startswith("\n"):
        suffix = suffix[1:]
    return existing[:start] + suffix


def stage_managed_json_configs(staging: Path, target: Path) -> None:
    """Structurally merge every staged host JSON config before target sync."""
    for relative in (".claude/settings.json", ".codex/hooks.json", ".agents/hooks.json"):
        staged_path = staging / relative
        target_path = target / relative
        if not staged_path.exists() or not target_path.exists():
            continue
        try:
            existing = json.loads(target_path.read_text(encoding="utf-8"))
            managed = json.loads(staged_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"cannot merge malformed host JSON config: {relative}") from exc
        merged = merge_managed_json(existing, managed)
        staged_path.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")


def resolve_source_path(maika_root: Path, source: str) -> Path:
    """Resolve a plugin source path to its actual location in the Maika repo."""
    for prefix, actual_dir in SOURCE_MAP.items():
        if source.startswith(prefix) or source == prefix.rstrip("/"):
            return maika_root / source.replace(prefix, actual_dir, 1)
    return maika_root / source


def load_manifest(maika_root: Path) -> dict:
    """Load the plugin manifest YAML."""
    with open(maika_root / "cli" / "plugin-manifest.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def has_capability(selected_mcps: List[str], mcp_capabilities: dict, required: str) -> bool:
    """True if any selected MCP provides the required capability."""
    return any(
        mcp_capabilities.get(mcp, {}).get("provides") == required
        for mcp in selected_mcps
    )


def get_ownership(plugin: dict) -> str:
    """Return 'framework' (default) or 'user' for a plugin."""
    return plugin.get("ownership", "framework")


def resolved_config_candidates(target: Path) -> List[Path]:
    """Return supported resolved-config locations in preference order.

    Roots are derived from the platform registry, so a new platform with a
    new framework_root is covered automatically. The canonical root sorts
    first → the fallback in load_resolved_config is deterministic.
    """
    from cli.platforms import PLATFORMS, get_platform

    # Legacy roots remain readable during the compatibility window, but every
    # new write targets the canonical project core.
    roots = {get_platform(k).framework_root for k in PLATFORMS} | {".agents", ".claude"}
    ordered = [CANONICAL_FRAMEWORK_ROOT, *sorted(roots - {CANONICAL_FRAMEWORK_ROOT})]
    return [target / root / "resolved-config.yaml" for root in ordered]


def generate_resolved_config(
    target_dir: Path,
    platform,
    selected_mcps: List[str],
    language: str,
) -> None:
    """Write resolved-config.yaml under the platform's framework root."""
    config_path = target_dir / platform.framework_root / "resolved-config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    if config_path.is_dir():
        # Reject a directory at the canonical path deterministically: open() would
        # raise IsADirectoryError on POSIX but PermissionError on Windows.
        raise IsADirectoryError(f"resolved-config path is a directory: {config_path}")
    resolved = {
        "platform": platform.name,
        "framework_root": platform.framework_root,
        "mcps": selected_mcps,
        "language": language,
        "framework_version": FRAMEWORK_VERSION,
    }
    with open(config_path, "w", encoding="utf-8") as f:
        f.write("# Maika Resolved Configuration\n")
        f.write("# Generated by: maika init / maika update --reconfigure\n")
        f.write("# The adapter layer is pre-resolved — no runtime lookup needed.\n\n")
        yaml.dump(
            {"resolved": resolved},
            f, default_flow_style=False, allow_unicode=True,
        )
    _sweep_stale_configs(target_dir, keep=config_path)


def _sweep_stale_configs(target_dir: Path, keep: Path) -> None:
    """Remove Maika-generated resolved-config.yaml under candidate roots != keep.

    Enforces the single-config invariant after a write (e.g. clears the old
    config when a project switches platforms). Only deletes a file that parses
    as an Maika resolved config (has a ``resolved:`` mapping) — never an
    unrelated same-named file. Best-effort: missing/unreadable files are skipped.
    """
    for candidate in resolved_config_candidates(target_dir):
        if candidate == keep or not candidate.exists():
            continue
        if _read_resolved_config(candidate) is None:
            continue
        candidate.unlink()


def _read_resolved_config(config_path: Path) -> Optional[dict]:
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except (yaml.YAMLError, OSError):
        return None
    resolved = data.get("resolved") if isinstance(data, dict) else None
    if not isinstance(resolved, dict):
        return None
    return resolved


def load_resolved_config(target: Path) -> Optional[dict]:
    """Load resolved config from native or legacy roots."""
    from cli.platforms import get_platform

    valid = []
    for config_path in resolved_config_candidates(target):
        if not config_path.exists():
            continue
        resolved = _read_resolved_config(config_path)
        if resolved is None:
            continue
        platform_key = resolved.get("platform", "generic")
        try:
            expected_root = get_platform(platform_key).framework_root
        except ValueError:
            expected_root = CANONICAL_FRAMEWORK_ROOT
        resolved.setdefault("framework_root", expected_root)
        resolved["_config_path"] = str(config_path)
        valid.append(resolved)

    if not valid:
        return None

    for resolved in valid:
        path = Path(resolved["_config_path"])
        if path.parent.as_posix().endswith(resolved["framework_root"]):
            return resolved

    return valid[0]


def scaffold_plugin(
    plugin: dict, source_path: Path, target_path: Path, context: dict, jinja_env
) -> dict:
    """Copy or render a single plugin to target_path.

    Returns a stats dict: {"action": "dir"|"rendered"|"copied",
                           "count": int, "rendered": int}.
    Template errors propagate (never swallowed).
    """
    from cli.renderer import copy_and_render_directory

    if plugin.get("copy_dir"):
        count, rendered = copy_and_render_directory(
            jinja_env, source_path, target_path, context
        )
        return {"action": "dir", "count": count, "rendered": rendered}

    target_path.parent.mkdir(parents=True, exist_ok=True)

    if plugin.get("template") or source_path.suffix.lower() in _RENDERABLE_SUFFIXES:
        try:
            content = source_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = None
        if content is not None and ("{{ " in content or plugin.get("template")):
            output = render_string(jinja_env, content, context)
            target_path.write_text(output, encoding="utf-8")
            shutil.copystat(source_path, target_path)
            return {"action": "rendered", "count": 1, "rendered": 1}

    shutil.copy2(source_path, target_path)
    return {"action": "copied", "count": 1, "rendered": 0}


def scaffold_plugins(
    plugins: List[dict], maika_root: Path, write_root: Path, context: dict,
    jinja_env, mcp_capabilities: dict, selected_mcps: List[str],
    only_framework: bool = False, verbose: bool = True,
) -> dict:
    """Process all plugins into write_root.

    only_framework=True skips ownership=='user' plugins (used by update).
    Returns aggregate stats.
    """
    stats = {"rendered": 0, "copied": 0, "dirs": 0, "skipped": 0}
    for plugin in plugins:
        name = plugin["name"]
        requires = plugin.get("requires_capability")
        if requires and not has_capability(selected_mcps, mcp_capabilities, requires):
            if verbose:
                print(f"  ⏭️  {name:35s} (no {requires})")
            stats["skipped"] += 1
            continue
        platform_requires_name = plugin.get("requires_platform")
        platform_name = context.get("platform", {}).get("name")
        if platform_requires_name:
            allowed = (
                platform_requires_name
                if isinstance(platform_requires_name, list)
                else [platform_requires_name]
            )
            if platform_name not in allowed:
                if verbose:
                    print(
                        f"  ⏭️  {name:35s} "
                        f"(platform: {platform_name}, needs: {', '.join(allowed)})"
                    )
                stats["skipped"] += 1
                continue
        platform_requires = plugin.get("requires_platform_capability")
        if platform_requires and not context.get("capabilities", {}).get(platform_requires, False):
            if verbose:
                print(f"  ⏭️  {name:35s} (no platform capability: {platform_requires})")
            stats["skipped"] += 1
            continue
        if only_framework and get_ownership(plugin) == "user":
            if verbose:
                print(f"  🔒 {name:35s} (user-owned, preserved)")
            stats["skipped"] += 1
            continue

        source_path = resolve_source_path(maika_root, plugin["source"])
        output_rel = render_string(jinja_env, plugin["output"], context)
        target_path = write_root / output_rel
        if not source_path.exists():
            if verbose:
                print(f"  ⚠️  {name:35s} (source not found: {source_path})")
            stats["skipped"] += 1
            continue

        result = scaffold_plugin(plugin, source_path, target_path, context, jinja_env)
        if result["action"] == "dir":
            stats["dirs"] += 1
            stats["rendered"] += result["rendered"]
        elif result["action"] == "rendered":
            stats["rendered"] += 1
        else:
            stats["copied"] += 1
        if verbose:
            print(f"  ✅ {output_rel:35s}")
    return stats


def export_as_flat_command(skill_md_text: str) -> str:
    """Render a SKILL.md/workflow file as a frontmatter-free flat command.

    For platforms whose native command format forbids YAML frontmatter
    (e.g. Cursor's .cursor/commands/*.md). pre_conditions are re-rendered
    as a plain markdown checklist so the gates they encode (e.g.
    "ABORT - bootstrap hasn't run") aren't silently dropped.
    """
    _, frontmatter_text, body = skill_md_text.split("---", 2)
    meta = yaml.safe_load(frontmatter_text) or {}
    name = meta.get("name", "")
    description = (meta.get("description") or "").strip()

    header_lines = [f"# {name}", "", f"> {description}"]

    pre_conditions = meta.get("pre_conditions") or []
    if pre_conditions:
        header_lines.append("")
        header_lines.append("## Pre-conditions")
        for cond in pre_conditions:
            target = cond.get("file") or cond.get("input") or ""
            condition = cond.get("condition", "")
            on_fail = cond.get("on_fail", "")
            header_lines.append(f"- `{target}` {condition} -> if not met: {on_fail}")

    return "\n".join(header_lines) + "\n" + body.lstrip("\n")


def scaffold_native_skill_exports(
    plugins: List[dict], write_root: Path, platform, verbose: bool = True,
) -> dict:
    """Mirror skill/workflow plugins into the platform's native skill/command
    location (if it has one), in addition to their .maika/ output.

    Reads from write_root / plugin["output"] — already Jinja-rendered for
    this platform by scaffold_plugins() — rather than from the Maika repo
    source, so the native export always matches the rendered content
    exactly. No-op if platform.native_skill_export is None.
    """
    stats = {"exported": 0, "skipped": 0}
    export = platform.native_skill_export
    if export is None:
        return stats

    for plugin in plugins:
        if plugin.get("type") not in ("skill", "workflow"):
            continue

        output_path = write_root / plugin["output"]
        source_file = output_path / "SKILL.md" if plugin.get("copy_dir") else output_path
        if not source_file.exists():
            stats["skipped"] += 1
            continue

        text = source_file.read_text(encoding="utf-8")
        if not text.startswith("---"):
            if verbose:
                print(f"  ⏭️  native export skip: {plugin['name']} (no frontmatter)")
            stats["skipped"] += 1
            continue

        name = plugin["name"].removeprefix("workflow-")
        _, frontmatter_text, body = text.split("---", 2)
        meta = yaml.safe_load(frontmatter_text) or {}
        if "name" not in meta:
            meta = {"name": name, **meta}
            frontmatter_text = yaml.dump(meta, default_flow_style=False, allow_unicode=True)
            text = f"---\n{frontmatter_text}---{body}"

        content = export_as_flat_command(text) if export["strip_frontmatter"] else text

        if export["flatten"]:
            target = write_root / export["dir"] / f"{name}.md"
        else:
            target = write_root / export["dir"] / name / "SKILL.md"

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        stats["exported"] += 1
        if verbose:
            print(f"  ✅ native export: {target.relative_to(write_root)}")

    return stats


def verify_no_unresolved(root: Path) -> List[Path]:
    """Return text files under root that still contain an unresolved '{{ ' marker.

    Scans every extension the renderer actually renders (cli.renderer's
    _TEXT_EXTENSIONS), plus every known platform entry-point filename
    regardless of suffix — `.cursorrules` has an empty suffix and would
    otherwise escape the suffix-only filter, leaving the riskiest file
    (the one this scaffold renames dynamically) unchecked.
    """
    from cli.platforms import PLATFORMS, get_platform

    entry_points = {get_platform(k).config_entry_point for k in PLATFORMS}
    offenders = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in _RENDERED_SUFFIXES and path.name not in entry_points:
            continue
        try:
            if "{{ " in path.read_text(encoding="utf-8"):
                offenders.append(path)
        except UnicodeDecodeError:
            continue
    return offenders


def generate_knowledge_index(maika_root: Path, target: Path, framework_root: str) -> None:
    """Generate knowledge-index.yaml in the target project's long-term knowledge dir."""
    tool_path = maika_root / ".maika" / "tools" / "knowledge-index" / "generate_index.py"
    if not tool_path.exists():
        return
    long_term = target / framework_root / "knowledge" / "long-term"
    if not long_term.is_dir():
        return
    spec = importlib.util.spec_from_file_location("_ki_generate_index", tool_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    entries = mod.build_index(
        long_term / "author-dna.yaml",
        long_term / "conventions.yaml",
        snapshot_path=long_term / "knowledge-snapshot.md",
        project_path=long_term / "project-knowledge",
    )
    header = "# TỰ ĐỘNG TẠO BỞI generate_index.py — KHÔNG CHỈNH SỬA THỦ CÔNG\n"
    (long_term / "knowledge-index.yaml").write_text(
        header + yaml.safe_dump({"entries": entries}, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    print(f"  ✅ knowledge-index.yaml ({len(entries)} entries)")
