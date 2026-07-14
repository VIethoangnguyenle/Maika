"""maika status — Show current Maika configuration in a project.

Reads resolved-config.yaml and reports the current platform, MCPs,
language, and installed skills/workflows.
"""

import json
from pathlib import Path

from cli import CANONICAL_FRAMEWORK_ROOT
from cli.platforms import get_platform
from cli.scaffold import load_resolved_config


def _snapshot(target: Path) -> dict:
    """Machine-readable lifecycle snapshot (consumed by `maika status --json`)."""
    resolved = load_resolved_config(target) or {}
    platform = resolved.get("platform", "generic")
    try:
        framework_root = resolved.get("framework_root") or get_platform(platform).framework_root
    except ValueError:
        framework_root = resolved.get("framework_root", CANONICAL_FRAMEWORK_ROOT)
    root = target / framework_root
    skills = sorted(d.name for d in (root / "skills").iterdir() if d.is_dir()) \
        if (root / "skills").is_dir() else []
    workflows = sorted(f.stem for f in (root / "workflows").iterdir()
                       if f.is_file() and f.suffix == ".md") if (root / "workflows").is_dir() else []
    from cli.config import project as project_cfg
    cfg = project_cfg.load(target)
    runtime_platform = None
    runtime_source = None
    try:
        from cli.runtime.session import resolve_active_platform
        runtime_platform, runtime_source = resolve_active_platform(target)
    except ValueError:
        pass
    platform_health = {}
    for key in cfg["platforms"]["enabled"]:
        try:
            from cli.platforms.probe import probe_platform
            probe = probe_platform(key, target, verify=False)
            platform_health[key] = {
                "support_tier": probe.support_tier,
                "binary_found": probe.binary.found,
                "hook_state": probe.verification["hook"],
            }
        except ValueError as exc:
            platform_health[key] = {"support_tier": 0, "error": str(exc)}
    return {
        "project": str(target),
        "installed": (target / framework_root).is_dir() and bool(resolved),
        "framework_version": resolved.get("framework_version", "unknown"),
        "platform": platform,
        "mcps": resolved.get("mcps", []),
        "language": resolved.get("language", "unknown"),
        "framework_root": framework_root,
        "skills": skills,
        "workflows": workflows,
        "enabled_platforms": cfg["platforms"]["enabled"],
        "primary": cfg["platforms"]["primary"],
        "runtime_platform": runtime_platform,
        "runtime_source": runtime_source,
        "platform_health": platform_health,
    }


def run_status(target_dir: str, as_json: bool = False) -> None:
    """Show Maika status for a target project."""
    target = Path(target_dir).resolve()

    if as_json:
        print(json.dumps(_snapshot(target), ensure_ascii=False, indent=2))
        return

    # ─── Check for Maika installation ───
    # Resolve the entry-point file from the recorded platform; fall back to
    # AGENTS.md for legacy installs predating resolved-config.yaml.
    resolved = load_resolved_config(target)
    if resolved is not None:
        try:
            entry = get_platform(resolved.get("platform", "generic")).config_entry_point
        except ValueError:
            entry = "AGENTS.md"
    else:
        entry = "AGENTS.md"

    if not (target / entry).exists():
        print(f"\n  ❌ No Maika installation found in {target}")
        print(f"     Run: maika init --target {target}")
        return

    print()
    print(f"  📁 Project: {target}")
    print()

    # ─── Resolved config ───
    resolved = load_resolved_config(target)
    if resolved is not None:
        platform = resolved.get("platform", "unknown")
        mcps = resolved.get("mcps", [])
        language = resolved.get("language", "unknown")
        version = resolved.get("framework_version", "unknown")
        framework_root = resolved.get("framework_root", get_platform(platform).framework_root)

        print(f"  🔧 Framework: Maika v{version}")
        print(f"  🔌 Platform:  {platform}")
        print(f"  📦 MCPs:      {', '.join(mcps) if mcps else 'none'}")
        print(f"  💬 Language:  {language}")
        print(f"  🧭 Root:      {framework_root}")
    else:
        print(f"  ⚠️  No resolved-config.yaml — may be a legacy installation")
        print(f"     Run: maika init --target {target}")
        framework_root = CANONICAL_FRAMEWORK_ROOT

    root = target / framework_root

    # ─── Skills ───
    skills_dir = root / "skills"
    if skills_dir.is_dir():
        skills = sorted([d.name for d in skills_dir.iterdir() if d.is_dir()])
        print(f"\n  🧠 Skills ({len(skills)}):")
        for s in skills:
            print(f"     • {s}")

    # ─── Workflows ───
    workflows_dir = root / "workflows"
    if workflows_dir.is_dir():
        wfs = sorted([f.stem for f in workflows_dir.iterdir() if f.is_file() and f.suffix == ".md"])
        print(f"\n  📋 Workflows ({len(wfs)}):")
        for w in wfs:
            print(f"     • /{w}")

    # ─── Knowledge layer ───
    kl_active = root / "knowledge" / "active"
    kl_archive = root / "knowledge" / "archive"

    if kl_active.is_dir():
        req = kl_active / "REQUIREMENT.md"
        has_req = req.exists() and req.stat().st_size > 200  # More than just template
        print(f"\n  📋 Active context: {'has content' if has_req else 'empty'}")

    if kl_archive.is_dir():
        tickets = [d.name for d in kl_archive.iterdir() if d.is_dir()]
        print(f"  📦 Archive: {len(tickets)} tickets")

    # ─── Author DNA ───
    dna = root / "knowledge" / "long-term" / "author-dna.yaml"
    dna_draft = root / "knowledge" / "long-term" / "author-dna.draft.yaml"
    if dna.exists():
        print(f"  🧬 Author DNA: approved")
    elif dna_draft.exists():
        print(f"  🧬 Author DNA: draft (not yet approved)")
    else:
        print(f"  🧬 Author DNA: not configured")

    lifecycle = _snapshot(target)
    if lifecycle["enabled_platforms"]:
        print("\n  🖥️  Host runtimes:")
        for key, health in lifecycle["platform_health"].items():
            marker = " (current)" if key == lifecycle["runtime_platform"] else ""
            print(f"     • {key}: Tier {health.get('support_tier', 0)}, "
                  f"hook={health.get('hook_state', 'unknown')}{marker}")

    print()
