#!/usr/bin/env python3
"""Maika CLI — the working OS for AI coding agents.

Usage:
    maika init [--target DIR] [--source DIR]
    maika update [--target DIR] [--source DIR] [--reconfigure]
    maika status [--target DIR]
    maika task <action> [--target DIR] [--id ID]
    maika --version
    maika --help

Commands:
    init      Scaffold Maika framework into a target project
    update    Re-render framework files, preserving user-owned files
    status    Show current Maika configuration in a project
    task      Run public vNext task workflow commands
    bootstrap Produce provider-aware BOOTSTRAP_REPORT.yaml
"""

import argparse
import sys
import os


def _ensure_importable():
    """When run as `python cli/maika.py`, ensure repo root is on sys.path."""
    cli_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(cli_dir)
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)


def main():
    from cli import __version__

    parser = argparse.ArgumentParser(
        prog="maika",
        description="Maika — the working OS for AI coding agents (CLI)",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ─── init ───
    init_parser = subparsers.add_parser(
        "init",
        help="Scaffold Maika framework into a target project",
    )
    init_parser.add_argument(
        "--target",
        default=".",
        help="Target directory to scaffold into (default: current directory)",
    )
    init_parser.add_argument(
        "--source",
        default=None,
        help="Maika repo root (default: auto-detect from CLI location)",
    )
    init_parser.add_argument(
        "--platform",
        default=None,
        help="Agent platform key, e.g. antigravity, claude-code, codex, generic",
    )
    init_parser.add_argument(
        "--mcp",
        action="append",
        default=None,
        help="MCP server key. Repeat or pass comma-separated values.",
    )
    init_parser.add_argument(
        "--language",
        default=None,
        help="Primary project language from cli/plugin-manifest.yaml",
    )
    init_parser.add_argument(
        "--yes",
        action="store_true",
        help="Run non-interactively; requires --platform and --language",
    )
    init_parser.add_argument(
        "--ua-mcp-dir",
        default=None,
        help="Absolute path to the Understand-Anything-MCP clone (when understand-anything is selected)",
    )
    init_parser.add_argument(
        "--hook-python",
        default=None,
        help="Python invocation the write-gate hook uses on Windows (e.g. 'python' or 'py -3'). Default: python.",
    )

    # ─── status ───
    status_parser = subparsers.add_parser(
        "status",
        help="Show current Maika configuration in a project",
    )
    status_parser.add_argument(
        "--target",
        default=".",
        help="Project directory to check (default: current directory)",
    )

    bootstrap_parser = subparsers.add_parser(
        "bootstrap", help="Probe configured providers and create BOOTSTRAP_REPORT.yaml",
    )
    bootstrap_parser.add_argument("--target", default=".")

    skill_parser = subparsers.add_parser("skill", help="Promote or reject a reviewed skill candidate")
    skill_parser.add_argument("action", choices=["promote", "reject"])
    skill_parser.add_argument("--target", default=".")
    skill_parser.add_argument("--candidate", required=True)
    skill_parser.add_argument("--review", required=True)
    skill_parser.add_argument("--promotion")

    # ─── task ───
    task_parser = subparsers.add_parser(
        "task",
        help="Run public vNext task workflow commands",
    )
    task_parser.add_argument(
        "action",
        choices=[
            "start", "explore", "validate-reasoning", "reconcile", "brainstorm", "spec", "plan",
            "validate-plan", "apply", "review", "verify", "archive", "status",
            "resume", "cancel",
            "approve-command",
            "force-unlock",
        ],
    )
    task_parser.add_argument("--target", default=".")
    task_parser.add_argument("--id", dest="change_id", default=None)
    task_parser.add_argument("--class", dest="klass", default="small")
    task_parser.add_argument("--title", default=None)
    task_parser.add_argument("--command-id", default=None)

    # ─── update ───
    update_parser = subparsers.add_parser(
        "update",
        help="Re-render framework files in an existing Maika project",
    )
    update_parser.add_argument(
        "--target", default=".",
        help="Project directory to update (default: current directory)",
    )
    update_parser.add_argument(
        "--source", default=None,
        help="Maika repo root (default: auto-detect from CLI location)",
    )
    update_parser.add_argument(
        "--reconfigure", action="store_true",
        help="Re-prompt platform/MCP/language before re-rendering",
    )
    update_parser.add_argument(
        "--hook-python",
        default=None,
        help="Python invocation the write-gate hook uses on Windows (e.g. 'python' or 'py -3'). Default: python.",
    )

    # ─── platform ───
    platform_parser = subparsers.add_parser(
        "platform",
        help="Manage host adapters over one shared .maika core",
    )
    platform_parser.add_argument(
        "action", choices=["list", "enable", "disable", "primary"],
    )
    platform_parser.add_argument(
        "platform_key", nargs="?", default=None,
        help="Platform key (required for enable/disable/primary)",
    )
    platform_parser.add_argument("--target", default=".")
    platform_parser.add_argument("--source", default=None)

    # ─── dashboard ───
    dashboard_parser = subparsers.add_parser(
        "dashboard",
        help="Register projects and print Maika run progress (one-shot CLI)",
    )
    dashboard_parser.add_argument(
        "action",
        nargs="?",
        choices=["register", "unregister", "list", "serve", "sync-brain"],
        default=None,
        help="register/unregister/list/serve/sync-brain; omit to print a progress snapshot",
    )
    dashboard_parser.add_argument(
        "--target", default=".", help="Project directory (default: current directory)",
    )
    dashboard_parser.add_argument(
        "--path", default=None, help="Path for register/unregister (default: --target)",
    )
    dashboard_parser.add_argument(
        "--port", type=int, default=7077, help="Port for serve (default: 7077)",
    )
    dashboard_parser.add_argument(
        "--no-browser", action="store_true", help="Do not auto-open the browser on serve",
    )
    dashboard_parser.add_argument(
        "--brain-platform",
        choices=["antigravity"],
        default="antigravity",
        help="IDE brain source for dashboard sync-brain (default: antigravity)",
    )

    # ─── doctor ───
    doctor_parser = subparsers.add_parser(
        "doctor",
        help="Run Maika diagnostics",
    )
    doctor_subparsers = doctor_parser.add_subparsers(dest="doctor_command")
    mcp_parser = doctor_subparsers.add_parser(
        "mcp",
        help="Diagnose MCP config and runtime availability",
        description="Diagnose MCP config and runtime availability",
    )
    mcp_parser.add_argument("--target", default=".")
    mcp_parser.add_argument("--fix", action="store_true")
    mcp_parser.add_argument("--yes", action="store_true")
    setup_parser = doctor_subparsers.add_parser(
        "setup",
        help="Report whole-adapter installation health",
        description="Report whole-adapter installation health",
    )
    setup_parser.add_argument("--target", default=".")
    setup_parser.add_argument("--source", default=None)
    setup_parser.add_argument("--json", dest="as_json", action="store_true")

    # ─── hook ───
    hook_parser = subparsers.add_parser(
        "hook",
        help="Host-hook entrypoints (invoked by native PreToolUse hooks)",
    )
    hook_parser.add_argument("hook_action", choices=["write-gate"])
    hook_parser.add_argument(
        "--runtime", choices=["claude", "codex", "antigravity"], default="claude",
    )

    args = parser.parse_args()

    if args.command == "init":
        from cli.commands.init import parse_multi_values, run_init
        selected_mcps = (
            parse_multi_values(args.mcp) if args.mcp is not None else None
        )
        run_init(
            target_dir=args.target,
            maika_root=args.source,
            platform_key=args.platform,
            selected_mcps=selected_mcps,
            language=args.language,
            assume_yes=args.yes,
            ua_mcp_dir=args.ua_mcp_dir,
            hook_python=args.hook_python,
        )
    elif args.command == "update":
        from cli.commands.update import run_update
        run_update(target_dir=args.target, maika_root=args.source, reconfigure=args.reconfigure, hook_python=args.hook_python)
    elif args.command == "platform":
        from cli.commands.platform import run_platform
        sys.exit(run_platform(
            action=args.action, target_dir=args.target,
            platform_key=args.platform_key, maika_root=args.source,
        ))
    elif args.command == "status":
        from cli.commands.status import run_status
        run_status(target_dir=args.target)
    elif args.command == "bootstrap":
        from cli.commands.bootstrap import run_bootstrap
        sys.exit(run_bootstrap(args.target))
    elif args.command == "skill":
        from cli.commands.skill import run_skill
        sys.exit(run_skill(args.action, args.target, args.candidate, args.review, args.promotion))
    elif args.command == "task":
        from cli.commands.task import run_task
        rc = run_task(
            action=args.action,
            target_dir=args.target,
            change_id=args.change_id,
            klass=args.klass,
            title=args.title,
            command_id=args.command_id,
        )
        sys.exit(rc)
    elif args.command == "dashboard":
        from cli.commands.dashboard import run_dashboard
        run_dashboard(
            target=args.target,
            action=args.action,
            path=args.path,
            port=args.port,
            no_browser=args.no_browser,
            brain_platform=args.brain_platform,
        )
    elif args.command == "doctor" and args.doctor_command == "mcp":
        from cli.commands.doctor import run_doctor_mcp
        run_doctor_mcp(target_dir=args.target, fix=args.fix, assume_yes=args.yes)
    elif args.command == "doctor" and args.doctor_command == "setup":
        from cli.commands.doctor import run_doctor_setup
        sys.exit(run_doctor_setup(target_dir=args.target, as_json=args.as_json, maika_root=args.source))
    elif args.command == "hook" and args.hook_action == "write-gate":
        from cli.commands.hook import run_hook_write_gate
        sys.exit(run_hook_write_gate(runtime=args.runtime))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    _ensure_importable()
    main()
