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
    """Entrypoint (kernel render) + this platform's native hook plugin only."""
    plugins = []
    for plugin in manifest.get("plugins", []):
        if plugin.get("type") == "kernel-entrypoint":
            plugins.append(plugin)
        elif plugin.get("requires_platform") == platform_key:
            plugins.append(plugin)
    return plugins


def _stage_metadata(staging: Path, target: Path, cfg: dict, platform_key: str,
                    *, remove: bool = False) -> None:
    """Stage the complete config/manifest mutation for the adapter transaction."""
    for name in ("install-manifest.yaml",):
        source = target / ".maika/config" / name
        dest = staging / ".maika/config" / name
        if source.is_file():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dest)
    project.save(staging, cfg)
    platforms_cfg.write_platforms_config(staging, cfg["platforms"]["enabled"])
    if remove:
        platforms_cfg.remove_install(staging, platform_key)
    else:
        platforms_cfg.record_install(staging, platform_key, platforms_cfg.adapter_files(platform_key))


def install_adapter(target: Path, platform_key: str, maika_root: Optional[str] = None,
                    project_config: Optional[dict] = None) -> None:
    """Render + transactionally apply one platform's adapter (entrypoint + native
    hook config). The `.maika` core is not re-rendered."""
    maika = asset_root(maika_root)
    manifest = load_asset_manifest(maika)
    platform = get_platform(platform_key)
    resolved = load_resolved_config(target) or {}
    context = platform.build_render_context(
        resolved.get("mcps", []), resolved.get("language", "other"),
    )
    jinja_env = create_renderer(str(maika))

    staging = Path(tempfile.mkdtemp(prefix="maika-adapter-"))
    backups = Path(tempfile.mkdtemp(prefix="maika-backup-"))
    mcp_setup_written = None
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
        from cli.runtime.platform_profile import stage_platform_runtime_profile
        # Merge over any existing target profile so re-enable preserves
        # fingerprint-consistent runtime-observed facts before the probe refreshes
        # detection (F3).
        stage_platform_runtime_profile(target, staging, platform_key)
        from cli.platforms.probe import probe_and_persist
        probe_and_persist(staging, platform_key, verify=False)
        if project_config is not None:
            from cli.commands.init import (
                emit_mcp_setup_files,
                existing_ua_mcp_dir,
            )
            mcp_setup_written = emit_mcp_setup_files(
                staging,
                project_config["platforms"]["enabled"],
                resolved.get("mcps", []),
                manifest,
                existing_ua_mcp_dir(target),
                resolved.get("language", "other"),
                project_root=target,
            )
            _stage_metadata(staging, target, project_config, platform_key)
        plan = build_plan(staging, target, "init", platform.framework_root)
        if mcp_setup_written is False and (target / ".maika/MCP_SETUP.md").is_file():
            plan["actions"].append({
                "kind": "delete_file",
                "path": ".maika/MCP_SETUP.md",
                "ownership": "framework",
            })
        Transaction(staging, target, backups).apply(plan)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
        shutil.rmtree(backups, ignore_errors=True)


def remove_adapter(target: Path, platform_key: str, remaining: List[str], cfg: dict) -> None:
    """Remove one adapter and metadata in a single transaction."""
    descriptor = platforms_cfg.adapter_descriptor(platform_key)
    staging = Path(tempfile.mkdtemp(prefix="maika-disable-"))
    backups = Path(tempfile.mkdtemp(prefix="maika-backup-"))
    extra = []
    try:
        entrypoint = descriptor["entrypoint"]
        shared = any(platforms_cfg.adapter_descriptor(other)["entrypoint"] == entrypoint
                     for other in remaining)
        ep_path = target / entrypoint
        if ep_path.is_file() and not shared:
            stripped = strip_managed_markdown(ep_path.read_text(encoding="utf-8"))
            if stripped.strip():
                staged = staging / entrypoint
                staged.parent.mkdir(parents=True, exist_ok=True)
                staged.write_text(stripped, encoding="utf-8")
                extra.append({"kind": "replace", "path": entrypoint, "ownership": "shared-host"})
            else:
                extra.append({"kind": "delete_file", "path": entrypoint, "ownership": "shared-host"})
        hook_config = descriptor["hook_config"]
        hc_path = target / hook_config if hook_config else None
        if hc_path and hc_path.is_file():
            cleaned = remove_maika_json_entry(json.loads(hc_path.read_text(encoding="utf-8")))
            staged = staging / hook_config
            staged.parent.mkdir(parents=True, exist_ok=True)
            staged.write_text(json.dumps(cleaned, indent=2) + "\n", encoding="utf-8")
            extra.append({"kind": "replace", "path": hook_config, "ownership": "shared-host"})
        _stage_metadata(staging, target, cfg, platform_key, remove=True)
        plan = build_plan(staging, target, "platform-disable", ".maika")
        # Host replacements are full desired documents, not merge inputs.
        host_paths = {action["path"] for action in extra}
        plan["actions"] = [a for a in plan["actions"] if a["path"] not in host_paths]
        plan["actions"].extend(extra)
        profile = f".maika/runtime/platforms/{platform_key}.yaml"
        if (target / profile).exists():
            plan["actions"].append({"kind": "delete_file", "path": profile,
                                    "ownership": "framework"})
        Transaction(staging, target, backups).apply(plan)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
        shutil.rmtree(backups, ignore_errors=True)


def set_primary_transaction(target: Path, cfg: dict) -> None:
    staging = Path(tempfile.mkdtemp(prefix="maika-primary-"))
    backups = Path(tempfile.mkdtemp(prefix="maika-backup-"))
    try:
        project.save(staging, cfg)
        plan = build_plan(staging, target, "platform-primary", ".maika")
        Transaction(staging, target, backups).apply(plan)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
        shutil.rmtree(backups, ignore_errors=True)


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

    if action in {"enable", "disable", "primary"} \
            and not (target / ".maika/config/project.yaml").is_file():
        print("  ❌ Canonical .maika core is missing; run `maika init` before managing adapters")
        return 1

    if action in {"verify", "status"}:
        from cli.platforms.probe import probe_and_persist, probe_platform
        try:
            result = (probe_and_persist(target, platform_key, verify=True)
                      if action == "verify" else probe_platform(platform_key, target, verify=False))
        except (OSError, ValueError) as exc:
            print(f"  ❌ {platform_key}: {exc}")
            return 1
        print(f"  {platform_key}: tier {result.support_tier}; "
              f"binary={'detected' if result.binary.found else 'missing'}; "
              f"worker={result.verification['worker']}")
        return 0 if action == "status" or result.support_tier >= 2 else 1

    cfg = project.load(target)

    if action == "enable":
        cfg = project.enable(cfg, platform_key)
        install_adapter(target, platform_key, maika_root, project_config=cfg)
        print(f"  ✅ Enabled {platform_key} (primary: {cfg['platforms']['primary']})")
    elif action == "disable":
        remaining = [p for p in cfg["platforms"]["enabled"] if p != platform_key]
        cfg = project.disable(cfg, platform_key)
        remove_adapter(target, platform_key, remaining, cfg)
        print(f"  ✅ Disabled {platform_key}")
    elif action == "primary":
        cfg = project.set_primary(cfg, platform_key)
        set_primary_transaction(target, cfg)
        print(f"  ✅ Primary set to {platform_key}")
    else:
        print(f"  ❌ Unknown action: {action}")
        return 1
    return 0
