"""maika init — Scaffold Maika framework into a target project."""

import shutil
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

from cli.assets import asset_root, load_asset_manifest
from cli.install.planner import build_plan
from cli.install.transaction import Transaction
from cli.mcp import ua_setup
from cli.platforms import PLATFORMS, get_platform
from cli.renderer import create_renderer
from cli.scaffold import (
    scaffold_plugins,
    scaffold_native_skill_exports,
    generate_resolved_config,
    generate_knowledge_index,
    verify_no_unresolved,
    stage_managed_entrypoint,
    stage_managed_json_configs,
)


def _ask_or_abort(question):
    """Run a questionary prompt and abort init cleanly on cancel.

    questionary swallows Ctrl-C internally and returns None; a closed / non-TTY
    stdin (e.g. CI running `maika init` without --yes) raises EOFError. Treat
    both as a clean cancel with a message instead of an uncaught traceback.
    """
    try:
        answer = question.ask()
    except EOFError:
        answer = None
    if answer is None:
        raise SystemExit("\n❌ Đã huỷ init.")
    return answer


def prompt_single_checkbox(
    message: str, choices: List[str], default: Optional[int] = 0
) -> str:
    """Interactive single-select prompt: arrow keys to move, Enter to pick."""
    # Lazy import so the module loads (and tests run) without questionary; only
    # the interactive `maika init` path needs it.
    import questionary

    return _ask_or_abort(
        questionary.select(
            message,
            choices=choices,
            default=choices[default] if default is not None else None,
        )
    )


def prompt_multi_checkbox(message: str, choices: List[dict]) -> List[str]:
    """Interactive multi-select prompt: Space to tick, Enter to confirm."""
    import questionary

    return _ask_or_abort(
        questionary.checkbox(
            message,
            choices=[
                questionary.Choice(title=choice["display"], value=choice["key"])
                for choice in choices
            ],
        )
    )


def parse_multi_values(values: Optional[List[str]]) -> List[str]:
    """Normalize repeated or comma-separated CLI option values."""
    if not values:
        return []
    parsed = []
    for value in values:
        for part in value.split(","):
            item = part.strip()
            if item:
                parsed.append(item)
    return parsed


def _validate_selected_mcps(selected_mcps: List[str], mcp_capabilities: dict) -> None:
    unknown = [mcp for mcp in selected_mcps if mcp not in mcp_capabilities]
    if unknown:
        raise ValueError(f"Unknown MCP server(s): {', '.join(unknown)}")


def _validate_language(language: str, languages: List[str]) -> None:
    if language not in languages:
        raise ValueError(
            f"Unknown language: {language}. Available: {', '.join(languages)}"
        )


def resolve_init_choices(
    manifest: dict,
    platform_key: Optional[str] = None,
    selected_mcps: Optional[List[str]] = None,
    language: Optional[str] = None,
    assume_yes: bool = False,
) -> Tuple[str, List[str], str]:
    """Resolve init choices from explicit options or interactive prompts."""
    mcp_capabilities = manifest.get("mcp_capabilities", {})
    languages = manifest.get("languages", ["java", "typescript", "python", "other"])
    explicit_selected_mcps = selected_mcps is not None
    selected_mcps = selected_mcps or []

    if assume_yes and (platform_key is None or language is None):
        raise ValueError("--yes requires --platform and --language")

    if platform_key is not None and platform_key not in PLATFORMS:
        raise ValueError(
            f"Unknown platform: {platform_key}. Available: {', '.join(PLATFORMS)}"
        )
    _validate_selected_mcps(selected_mcps, mcp_capabilities)
    if language is not None:
        _validate_language(language, languages)

    if platform_key is None:
        platform_keys = list(PLATFORMS.keys())
        platform_choices = [get_platform(k).display_name for k in platform_keys]
        chosen_display = prompt_single_checkbox(
            "Chọn agent platform:", platform_choices, default=None
        )
        platform_key = platform_keys[platform_choices.index(chosen_display)]
    print(f"\n  ✅ Platform: {get_platform(platform_key).display_name}")

    if not explicit_selected_mcps and not assume_yes:
        mcp_choices = [
            {"key": key, "display": value["display"]}
            for key, value in mcp_capabilities.items()
        ]
        selected_mcps = prompt_multi_checkbox("MCP servers có sẵn:", mcp_choices)
    print(f"  ✅ MCPs: {', '.join(selected_mcps) or 'none'}")

    if language is None:
        default_language = languages.index("other") if "other" in languages else None
        language = prompt_single_checkbox(
            "Ngôn ngữ chính của project:", languages, default=default_language
        )
    print(f"  ✅ Language: {language}")
    return platform_key, selected_mcps, language


def gather_choices(manifest: dict) -> Tuple[str, List[str], str]:
    """Interactively gather (platform_key, selected_mcps, language)."""
    return resolve_init_choices(manifest)


UA_MCP_KEY = "understand-anything"
UA_MCP_PLACEHOLDER = "<PATH_TO_Understand-Anything-MCP>"


def resolve_ua_mcp_dir(selected_mcps, ua_mcp_dir, assume_yes: bool) -> str:
    """Resolve the Understand-Anything-MCP clone dir: flag > prompt > placeholder.
    Returns '' when UA is not selected."""
    if UA_MCP_KEY not in selected_mcps:
        return ""
    if ua_mcp_dir:
        return ua_mcp_dir
    if assume_yes:
        return UA_MCP_PLACEHOLDER
    raw = input(
        "\nĐường dẫn tuyệt đối tới clone Understand-Anything-MCP "
        "(Enter để chèn placeholder): "
    ).strip()
    return raw or UA_MCP_PLACEHOLDER


def emit_mcp_setup_files(target, platform, platform_key, selected_mcps, manifest, ua_dir) -> bool:
    """Write <framework_root>/MCP_SETUP.md for selected MCPs that declare a `setup`
    block; remove a stale file when none apply. Returns True if a file was written.
    Shared by init and update --reconfigure."""
    mcp_caps = manifest.get("mcp_capabilities", {})
    setup_path = target / platform.framework_root / "MCP_SETUP.md"
    setup_path.parent.mkdir(parents=True, exist_ok=True)
    wrote = False
    for mcp_key in selected_mcps:
        capability = mcp_caps.get(mcp_key, {})
        if not ua_setup.has_setup(capability):
            continue
        dir_value = ua_dir if mcp_key == UA_MCP_KEY else UA_MCP_PLACEHOLDER
        setup_md = ua_setup.render_mcp_setup_md(
            capability["setup"], server_key=mcp_key, platform=platform_key,
            ua_mcp_dir=dir_value, project_root=str(target),
        )
        setup_path.write_text(setup_md, encoding="utf-8")
        wrote = True
    if not wrote and setup_path.exists():
        setup_path.unlink()
    return wrote


def run_init(
    target_dir: str,
    maika_root: Optional[str] = None,
    platform_key: Optional[str] = None,
    selected_mcps: Optional[List[str]] = None,
    language: Optional[str] = None,
    assume_yes: bool = False,
    ua_mcp_dir: Optional[str] = None,
    migration_files: Optional[dict[str, Path]] = None,
    verify_platform: bool = False,
) -> None:
    """Main init command — scaffold Maika into a target project."""
    target = Path(target_dir).resolve()
    maika = asset_root(maika_root)

    print(f"\n  Maika Framework v3.0 — init")
    print(f"  Target: {target}\n  Source: {maika}")

    manifest = load_asset_manifest(maika)
    platform_key, selected_mcps, language = resolve_init_choices(
        manifest,
        platform_key=platform_key,
        selected_mcps=selected_mcps,
        language=language,
        assume_yes=assume_yes,
    )
    ua_dir = resolve_ua_mcp_dir(selected_mcps, ua_mcp_dir, assume_yes)
    platform = get_platform(platform_key)

    print(f"\n{'─' * 50}")
    print(f"  Platform:  {platform.display_name}")
    print(f"  MCPs:      {', '.join(selected_mcps) or 'none'}")
    print(f"  Language:  {language}")
    print(f"  Target:    {target}\n{'─' * 50}")
    if not assume_yes and input("\nTiến hành scaffold? [Y/n]: ").strip().lower() == "n":
        print("\n❌ Đã huỷ.")
        return

    context = platform.build_render_context(selected_mcps, language)
    jinja_env = create_renderer(str(maika))
    print("\nScaffolding Maika framework...\n")

    framework_root = platform.framework_root
    staging = Path(tempfile.mkdtemp(prefix="maika-init-"))
    backups = Path(tempfile.mkdtemp(prefix="maika-backup-"))
    try:
        stats = scaffold_plugins(
            manifest.get("plugins", []), maika, staging, context, jinja_env,
            manifest.get("mcp_capabilities", {}), selected_mcps,
        )
        scaffold_native_skill_exports(manifest.get("plugins", []), staging, platform)
        offenders = verify_no_unresolved(staging)
        if offenders:
            print("\n  ❌ Init aborted — unresolved template markers in:")
            for p in offenders:
                print(f"     • {p.relative_to(staging)}")
            print("  Target was NOT modified.")
            return
        # Build the complete desired tree in staging, then apply atomically.
        stage_managed_entrypoint(staging, target, platform.config_entry_point)
        stage_managed_json_configs(staging, target)
        generate_knowledge_index(maika, staging, framework_root)
        generate_resolved_config(staging, platform, selected_mcps, language)
        from cli.runtime.platform_profile import write_platform_runtime_profile
        write_platform_runtime_profile(staging, platform_key)
        for logical, source in (migration_files or {}).items():
            destination = staging / ".maika" / logical
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        emit_mcp_setup_files(staging, platform, platform_key, selected_mcps, manifest, ua_dir)
        # Canonical metadata is part of the same transaction as core/adapter
        # files; no post-commit writes may leave a partial installation.
        from cli.config import platforms as platforms_cfg
        from cli.config import project as project_cfg
        project_config = project_cfg.enable(project_cfg.load(target), platform_key)
        project_cfg.save(staging, project_config)
        platforms_cfg.write_platforms_config(staging, project_config["platforms"]["enabled"])
        platforms_cfg.record_install(staging, platform_key, platforms_cfg.adapter_files(platform_key))
        # Detection (and, with --verify-platform, the hook/worker smoke) runs
        # after the project config is staged so the hook command can resolve the
        # project. Persists real binary detection so a fresh install reports its
        # true tier instead of advertising a worker the orchestrator refuses (F2).
        from cli.platforms.probe import probe_and_persist
        probe_and_persist(staging, platform_key, verify=verify_platform)
        plan = build_plan(staging, target, "init", framework_root)
        Transaction(staging, target, backups).apply(plan)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
        shutil.rmtree(backups, ignore_errors=True)

    total = stats["rendered"] + stats["copied"] + stats["dirs"]
    print(f"\n{'═' * 50}")
    print(f"  Done! Maika scaffolded for {platform.display_name}")
    print(f"  {total} plugins installed, {stats['skipped']} skipped")
    print(f"{'═' * 50}")
    if platform.worker_binary and not verify_platform:
        print("\n  ⚠  Worker not verified yet — run before dispatching tasks:")
        print(f"       maika platform verify {platform_key}")
    print("\n  Next steps:")
    print(f"  1. Customize {platform.framework_root}/knowledge/long-term/persona.yaml")
    print("  2. Start your first task: maika task start --id <id> --title '<title>'")
    print("  3. Continue with: maika task status --id <id>\n")
    if selected_mcps:
        print(f"  4. Run MCP diagnostics: maika doctor mcp --target {target}\n")
    if UA_MCP_KEY in selected_mcps:
        print(f"  5. Wire Understand-Anything: see {platform.framework_root}/MCP_SETUP.md\n")
