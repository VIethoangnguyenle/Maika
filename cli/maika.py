#!/usr/bin/env python3
"""Maika CLI — the working OS for AI coding agents.

Usage:
    maika init [--target DIR] [--source DIR]
    maika update [--target DIR] [--source DIR] [--reconfigure]
    maika status [--target DIR]
    maika --version
    maika --help

Commands:
    init      Scaffold Maika framework into a target project
    update    Re-render framework files, preserving user-owned files
    status    Show current Maika configuration in a project
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
    elif args.command == "status":
        from cli.commands.status import run_status
        run_status(target_dir=args.target)
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
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    _ensure_importable()
    main()
