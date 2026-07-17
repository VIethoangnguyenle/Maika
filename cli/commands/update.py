"""maika update — re-render framework files, preserve user files.

Renders into a temp staging dir, verifies zero unresolved markers, then
syncs framework files over the target. Aborts without touching the target
if anything fails.
"""

import shutil
import tempfile
from pathlib import Path
from typing import Optional

from cli.assets import asset_root, load_asset_manifest
from cli.install.planner import build_plan
from cli.install.transaction import Transaction
from cli.platforms import get_platform
from cli.renderer import create_renderer
from cli.scaffold import (
    load_resolved_config,
    scaffold_plugins,
    scaffold_native_skill_exports,
    verify_no_unresolved,
    generate_resolved_config,
    generate_knowledge_index,
    stage_managed_entrypoint,
    stage_managed_json_configs,
)


def _stage_index_inputs(target: Path, staging: Path, framework_root: str) -> None:
    """Copy the target's knowledge seeds into staging so the knowledge index can
    be regenerated and synced without re-writing the (user-owned) seeds
    themselves (the planner preserves existing project-owned files)."""
    src = target / framework_root / "knowledge" / "long-term"
    if not src.is_dir():
        return
    dst = staging / framework_root / "knowledge" / "long-term"
    dst.mkdir(parents=True, exist_ok=True)
    for name in ("author-dna.yaml", "conventions.yaml", "knowledge-snapshot.md"):
        seed = src / name
        if seed.exists():
            shutil.copy2(seed, dst / name)
    project_knowledge = src / "project-knowledge"
    if project_knowledge.is_dir():
        shutil.copytree(project_knowledge, dst / "project-knowledge", dirs_exist_ok=True)


def run_update(target_dir: str, maika_root: Optional[str] = None, reconfigure: bool = False):
    """Re-render framework files into an existing Maika project."""
    target = Path(target_dir).resolve()
    maika = asset_root(maika_root)

    resolved = load_resolved_config(target)
    if resolved is None:
        print(f"\n  ❌ No Maika installation found in {target}")
        print(f"     Run: maika init --target {target}")
        from cli.runtime.result import OperationResult
        return OperationResult("blocked", False, exit_code=2,
                               message="Maika installation not found")

    manifest = load_asset_manifest(maika)

    if reconfigure:
        from cli.commands.init import gather_choices
        print("\n  Maika update — reconfigure\n")
        platform_key, selected_mcps, language = gather_choices(manifest)
    else:
        platform_key = resolved.get("platform", "generic")
        selected_mcps = resolved.get("mcps", [])
        language = resolved.get("language", "other")

    platform = get_platform(platform_key)

    if not reconfigure:
        known_mcps = manifest.get("mcp_capabilities", {})
        unknown_mcps = [mcp for mcp in selected_mcps if mcp not in known_mcps]
        if unknown_mcps:
            selected_mcps = [mcp for mcp in selected_mcps if mcp in known_mcps]
            for name in unknown_mcps:
                print(f"  warning: unknown mcp selection dropped: {name}")
            generate_resolved_config(target, platform, selected_mcps, language)

    framework_root = resolved.get("framework_root", platform.framework_root)
    context = platform.build_render_context(selected_mcps, language)
    jinja_env = create_renderer(str(maika))

    print(f"\n  Updating Maika ({platform.display_name})...\n")
    staging = Path(tempfile.mkdtemp(prefix="maika-update-"))
    backups = Path(tempfile.mkdtemp(prefix="maika-backup-"))
    mcp_setup_written = None
    try:
        scaffold_plugins(
            manifest.get("plugins", []), maika, staging, context, jinja_env,
            manifest.get("mcp_capabilities", {}), selected_mcps,
            only_framework=True,
        )
        scaffold_native_skill_exports(manifest.get("plugins", []), staging, platform)
        from cli.commands.platform import _adapter_plugins
        from cli.config import project as project_cfg
        enabled = project_cfg.load(target)["platforms"]["enabled"] or [platform_key]
        adapter_platforms = []
        for enabled_platform in enabled:
            adapter = get_platform(enabled_platform)
            adapter_platforms.append(adapter)
            adapter_context = adapter.build_render_context(selected_mcps, language)
            plugins = _adapter_plugins(manifest, enabled_platform)
            scaffold_plugins(
                plugins, maika, staging, adapter_context, jinja_env,
                manifest.get("mcp_capabilities", {}), selected_mcps,
                verbose=False,
            )
            scaffold_native_skill_exports(plugins, staging, adapter, verbose=False)
        offenders = verify_no_unresolved(staging)
        if offenders:
            print("\n  ❌ Update aborted — unresolved template markers in:")
            for p in offenders:
                print(f"     • {p.relative_to(staging)}")
            print("  Target was NOT modified.")
            from cli.runtime.result import OperationResult
            return OperationResult("blocked", False, exit_code=1,
                                   message="unresolved template markers")
        # Build the complete desired tree in staging, then apply atomically.
        for entrypoint in sorted({adapter.config_entry_point for adapter in adapter_platforms}):
            stage_managed_entrypoint(staging, target, entrypoint)
        stage_managed_json_configs(staging, target)
        _stage_index_inputs(target, staging, framework_root)
        generate_knowledge_index(maika, staging, framework_root)
        from cli.runtime.platform_profile import stage_platform_runtime_profile
        for enabled_platform in enabled:
            # Merge framework-owned fields over the target's existing profile so a
            # re-render never resets detection/verification state (F3).
            stage_platform_runtime_profile(target, staging, enabled_platform)
        if reconfigure:
            generate_resolved_config(staging, platform, selected_mcps, language)
        if reconfigure:
            from cli.commands.init import resolve_ua_mcp_dir, emit_mcp_setup_files
            ua_dir = resolve_ua_mcp_dir(selected_mcps, None, assume_yes=False)
            mcp_setup_written = emit_mcp_setup_files(
                staging, enabled, selected_mcps, manifest, ua_dir, language,
                project_root=target,
            )
        plan = build_plan(staging, target, "update", framework_root)
        if mcp_setup_written is False and (target / ".maika/MCP_SETUP.md").is_file():
            plan["actions"].append({
                "kind": "delete_file",
                "path": ".maika/MCP_SETUP.md",
                "ownership": "framework",
            })
        if not plan["actions"]:
            from cli.runtime.result import OperationResult
            return OperationResult("no-op", False, message="already up to date")
        journal = Transaction(staging, target, backups).apply(plan)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
        shutil.rmtree(backups, ignore_errors=True)

    pruned = [a["path"] for a in plan["actions"] if a["kind"] == "delete_framework_file"]
    if pruned:
        print(f"  🗑️  Pruned {len(pruned)} orphaned framework file(s):")
        for p in pruned:
            print(f"     • {p}")

    count = sum(1 for a in plan["actions"] if a["kind"] != "delete_framework_file")
    print(f"\n  ✅ Updated {count} framework files. User files preserved.\n")
    from cli.runtime.result import OperationResult
    return OperationResult("committed", True,
                           transaction_id=journal.get("transaction_id"),
                           message="update committed")
