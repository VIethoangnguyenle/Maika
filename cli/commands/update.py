"""maika update — re-render framework files, preserve user files.

Renders into a temp staging dir, verifies zero unresolved markers, then
syncs framework files over the target. Aborts without touching the target
if anything fails.
"""

import shutil
import tempfile
from pathlib import Path
from typing import Optional

from cli.platforms import PLATFORMS, get_platform
from cli.renderer import create_renderer
from cli.scaffold import (
    load_manifest,
    load_resolved_config,
    scaffold_plugins,
    scaffold_native_skill_exports,
    verify_no_unresolved,
    sync_tree,
    prune_orphans,
    generate_resolved_config,
    generate_knowledge_index,
)


def warn_legacy_maika(target: Path, platform) -> None:
    legacy = target / ".maika"
    if platform.framework_root != ".maika" and legacy.exists():
        print(f"  ⚠️  legacy .maika remains at {legacy}; not removed automatically.")


def run_update(target_dir: str, maika_root: Optional[str] = None, reconfigure: bool = False, hook_python: Optional[str] = None) -> None:
    """Re-render framework files into an existing Maika project."""
    target = Path(target_dir).resolve()
    maika = Path(maika_root).resolve() if maika_root else Path(__file__).resolve().parent.parent.parent

    resolved = load_resolved_config(target)
    if resolved is None:
        print(f"\n  ❌ No Maika installation found in {target}")
        print(f"     Run: maika init --target {target}")
        return

    manifest = load_manifest(maika)

    if reconfigure:
        from cli.commands.init import gather_choices
        print("\n  Maika update — reconfigure\n")
        platform_key, selected_mcps, language = gather_choices(manifest)
    else:
        platform_key = resolved.get("platform", "generic")
        selected_mcps = resolved.get("mcps", [])
        language = resolved.get("language", "other")

    platform = get_platform(platform_key)
    framework_root = resolved.get("framework_root", platform.framework_root)
    effective_hook_python = hook_python or resolved.get("hook_python")
    context = platform.build_render_context(selected_mcps, language, hook_python=effective_hook_python)
    jinja_env = create_renderer(str(maika))

    print(f"\n  Updating Maika ({platform.display_name})...\n")
    staging = Path(tempfile.mkdtemp(prefix="maika-update-"))
    try:
        scaffold_plugins(
            manifest.get("plugins", []), maika, staging, context, jinja_env,
            manifest.get("mcp_capabilities", {}), selected_mcps,
            only_framework=True,
        )
        scaffold_native_skill_exports(manifest.get("plugins", []), staging, platform)
        offenders = verify_no_unresolved(staging)
        if offenders:
            print("\n  ❌ Update aborted — unresolved template markers in:")
            for p in offenders:
                print(f"     • {p.relative_to(staging)}")
            print("  Target was NOT modified.")
            return
        count = sync_tree(staging, target)
        pruned = prune_orphans(staging, target, framework_root)
    finally:
        shutil.rmtree(staging, ignore_errors=True)

    if pruned:
        print(f"  🗑️  Pruned {len(pruned)} orphaned framework file(s):")
        for p in pruned:
            print(f"     • {p}")

    generate_knowledge_index(maika, target, framework_root)

    if reconfigure:
        generate_resolved_config(target, platform, selected_mcps, language, hook_python=effective_hook_python)
        from cli.commands.init import resolve_ua_mcp_dir, emit_mcp_setup_files
        ua_dir = resolve_ua_mcp_dir(selected_mcps, None, assume_yes=False)
        emit_mcp_setup_files(target, platform, platform_key, selected_mcps, manifest, ua_dir)
        # Remove stale entry-point files left by the previous platform.
        current_entry = platform.config_entry_point
        for key in PLATFORMS:
            other_entry = get_platform(key).config_entry_point
            if other_entry != current_entry:
                stale = target / other_entry
                if stale.exists():
                    stale.unlink()
                    print(f"  🗑️  Removed stale entry point: {other_entry}")
        for root in [".agents", ".claude", ".maika"]:
            root_path = target / root
            if root != platform.framework_root and root_path.exists():
                print(f"  ⚠️  stale framework root detected: {root_path}")
    else:
        framework_root = resolved.get("framework_root", framework_root)

    if not reconfigure and hook_python and hook_python != resolved.get("hook_python"):
        generate_resolved_config(target, platform, selected_mcps, language, hook_python=hook_python)

    warn_legacy_maika(target, platform)

    print(f"\n  ✅ Updated {count} framework files. User files preserved.\n")
