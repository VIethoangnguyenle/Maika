"""maika doctor - diagnostics for Maika runtime dependencies."""

from pathlib import Path
from typing import Optional

from cli.mcp.doctor import apply_fix, build_doctor_status, write_report


def run_doctor_mcp(
    target_dir: str,
    fix: bool = False,
    assume_yes: bool = False,
    home: Optional[Path] = None,
) -> None:
    target = Path(target_dir).resolve()
    home_path = home or Path.home()
    maika_root = Path(__file__).resolve().parent.parent.parent
    try:
        status = build_doctor_status(target, home_path, maika_root=maika_root)
    except ValueError as exc:
        print(f"\n  {exc}")
        print("  Run `maika init` first, or point --target at an Maika project.")
        return
    report = write_report(target, status)
    print(f"\n  MCP doctor report: {report}")
    print(f"  native: {status.native_state} | bridge: {status.bridge_state}")
    if status.memory_daemon != "not-selected":
        print(f"  agent-memory daemon: {status.memory_daemon} ({status.memory_daemon_url})")
    if fix:
        fixed = apply_fix(target, home_path, assume_yes)
        if fixed is None:
            print("  no safe automatic fix available")
        else:
            print(f"  fixed config: {fixed}")
            status = build_doctor_status(target, home_path, maika_root=maika_root)
            report = write_report(target, status)
            print(f"  refreshed report: {report}")
