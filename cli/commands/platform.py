"""maika platform — manage host adapters over one shared `.maika` core.

    maika platform list
    maika platform enable <platform>
    maika platform disable <platform>
    maika platform primary <platform>

Enabling a host installs only its entrypoint + native hook config; the `.maika`
core (and all project knowledge) is rendered once at init and never touched here.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import List, Optional

from cli.assets import asset_root, load_asset_manifest
from cli.config import platforms as platforms_cfg
from cli.config import project
from cli.install.planner import build_plan
from cli.install.transaction import Transaction
from cli.platforms import PLATFORMS, get_platform
from cli.renderer import create_renderer
from cli.scaffold import (
    load_resolved_config,
    remove_maika_json_entry,
    scaffold_native_skill_exports,
    scaffold_plugins,
    stage_managed_entrypoint,
    stage_managed_json_configs,
    strip_managed_markdown,
    verify_no_unresolved,
)


def _adapter_plugins(manifest: dict, platform_key: str) -> List[dict]:
    """Entrypoint (meta-prompt) + this platform's native hook plugin only."""
    plugins = []
    for plugin in manifest.get("plugins", []):
        if plugin.get("type") == "meta-prompt":
            plugins.append(plugin)
        elif plugin.get("requires_platform") == platform_key:
            plugins.append(plugin)
    return plugins


def install_adapter(target: Path, platform_key: str, maika_root: Optional[str] = None) -> None:
    """Render + transactionally apply one platform's adapter (entrypoint + native
    hook config). The `.maika` core is not re-rendered."""
    maika = asset_root(maika_root)
    manifest = load_asset_manifest(maika)
    platform = get_platform(platform_key)
    resolved = load_resolved_config(target) or {}
    context = platform.build_render_context(
        resolved.get("mcps", []),
        resolved.get("language", "other"),
        hook_python=resolved.get("hook_python"),
    )
    jinja_env = create_renderer(str(maika))

    staging = Path(tempfile.mkdtemp(prefix="maika-adapter-"))
    backups = Path(tempfile.mkdtemp(prefix="maika-backup-"))
    try:
        plugins = _adapter_plugins(manifest, platform_key)
        scaffold_plugins(
            plugins, maika, staging, context, jinja_env,
            manifest.get("mcp_capabilities", {}), resolved.get("mcps", []),
            verbose=False,
        )
        scaffold_native_skill_exports(plugins, staging, platform, verbose=False)
        offenders = verify_no_unresolved(staging)
        if offenders:
            raise ValueError(f"unresolved template markers in adapter for {platform_key}")
        stage_managed_entrypoint(staging, target, platform.config_entry_point)
        stage_managed_json_configs(staging, target)
        plan = build_plan(staging, target, "init", platform.framework_root)
        Transaction(staging, target, backups).apply(plan)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
        shutil.rmtree(backups, ignore_errors=True)


def _remove_adapter(target: Path, platform_key: str, remaining: List[str]) -> None:
    """Strip only Maika-managed adapter entries; keep host-owned content and any
    entrypoint still shared by a remaining enabled platform."""
    descriptor = platforms_cfg.adapter_descriptor(platform_key)
    entrypoint = descriptor["entrypoint"]
    hook_config = descriptor["hook_config"]

    shared = any(
        platforms_cfg.adapter_descriptor(other)["entrypoint"] == entrypoint
        for other in remaining
    )
    if not shared:
        ep_path = target / entrypoint
        if ep_path.exists():
            stripped = strip_managed_markdown(ep_path.read_text(encoding="utf-8"))
            if stripped.strip() == "":
                ep_path.unlink()
            else:
                ep_path.write_text(stripped, encoding="utf-8")

    if hook_config:
        hc_path = target / hook_config
        if hc_path.exists():
            cleaned = remove_maika_json_entry(json.loads(hc_path.read_text(encoding="utf-8")))
            hc_path.write_text(json.dumps(cleaned, indent=2) + "\n", encoding="utf-8")


def _print_list(target: Path) -> None:
    cfg = project.load(target)
    enabled = cfg["platforms"]["enabled"]
    primary = cfg["platforms"]["primary"]
    print("\n  Maika platforms")
    for key in sorted(PLATFORMS):
        marks = []
        if key in enabled:
            marks.append("enabled")
        if key == primary:
            marks.append("primary")
        suffix = f"  [{', '.join(marks)}]" if marks else ""
        print(f"    • {key}{suffix}")
    print()


def run_platform(action: str, target_dir: str, platform_key: Optional[str] = None,
                 maika_root: Optional[str] = None) -> int:
    target = Path(target_dir).resolve()

    if action == "list":
        _print_list(target)
        return 0

    if platform_key is None:
        print(f"  ❌ 'maika platform {action}' requires a platform")
        return 1
    if platform_key not in PLATFORMS:
        print(f"  ❌ Unknown platform: {platform_key}. Available: {', '.join(sorted(PLATFORMS))}")
        return 1

    cfg = project.load(target)

    if action == "enable":
        install_adapter(target, platform_key, maika_root)
        cfg = project.enable(cfg, platform_key)
        project.save(target, cfg)
        platforms_cfg.write_platforms_config(target, cfg["platforms"]["enabled"])
        platforms_cfg.record_install(target, platform_key, platforms_cfg.adapter_files(platform_key))
        print(f"  ✅ Enabled {platform_key} (primary: {cfg['platforms']['primary']})")
    elif action == "disable":
        remaining = [p for p in cfg["platforms"]["enabled"] if p != platform_key]
        _remove_adapter(target, platform_key, remaining)
        cfg = project.disable(cfg, platform_key)
        project.save(target, cfg)
        platforms_cfg.write_platforms_config(target, cfg["platforms"]["enabled"])
        platforms_cfg.remove_install(target, platform_key)
        print(f"  ✅ Disabled {platform_key}")
    elif action == "primary":
        cfg = project.set_primary(cfg, platform_key)
        project.save(target, cfg)
        print(f"  ✅ Primary set to {platform_key}")
    else:
        print(f"  ❌ Unknown action: {action}")
        return 1
    return 0
