"""maika hook — the stable host-hook entrypoint.

Host PreToolUse hooks invoke `maika hook write-gate --runtime <runtime>` (one
OS-agnostic command) instead of a hard-coded `python .../write_gate.py` line.
This wrapper locates the project root, reads the canonical config for the core
root, then delegates to the project's own write-gate evaluator. It never
duplicates write-gate policy — the target's `write_gate.main` still finds the
root from cwd, reads stdin, and emits the runtime-specific decision.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

_WRITE_GATE_REL = ("hooks", "write-gate", "write_gate.py")


def _locate_project_root(cwd: Path) -> Path:
    """Git top-level from cwd, falling back to cwd (mirrors write_gate's own
    root resolution so both agree on the same project)."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(cwd), capture_output=True, text=True, check=True,
        )
    except (FileNotFoundError, OSError, subprocess.CalledProcessError):
        root = None
    else:
        root = result.stdout.strip()
        if root and (Path(root) / ".maika/config/project.yaml").is_file():
            return Path(root)
    for candidate in (cwd, *cwd.parents):
        if (candidate / ".maika/config/project.yaml").is_file():
            return candidate
    return Path(root) if root else cwd


def _load_write_gate(path: Path):
    spec = importlib.util.spec_from_file_location("maika_target_write_gate", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_hook_write_gate(runtime: str, platform: Optional[str] = None,
                        stdin_text: Optional[str] = None) -> int:
    """Delegate a PreToolUse event to the project's write-gate evaluator.

    Missing evaluator (not a Maika project, or a broken install) degrades to
    allow with a diagnostic — a hook that hard-blocks every write in a project
    without the gate installed would be worse than the status quo.
    """
    cwd = Path.cwd()
    root = _locate_project_root(cwd)
    config_path = root / ".maika/config/project.yaml"
    if not config_path.is_file():
        print("maika hook write-gate: not a Maika project — allowing", file=sys.stderr)
        return 0
    try:
        import yaml
        raw_config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        if not isinstance(raw_config, dict) or not isinstance(raw_config.get("framework"), dict):
            raise ValueError("project config must contain framework mapping")
        core_root = raw_config["framework"].get("core_root")
        if core_root != ".maika":
            raise ValueError("canonical framework.core_root must be .maika")
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"maika hook write-gate: malformed Maika config ({exc}); run `maika repair --all-safe`",
              file=sys.stderr)
        return 2
    platform = platform or {"claude": "claude-code", "codex": "codex",
                            "antigravity": "antigravity"}.get(runtime)
    if platform:
        from cli.runtime.platform_profile import PlatformProfileError, load_platform_runtime_profile
        from cli.runtime.session import SessionError, record_session
        try:
            profile = load_platform_runtime_profile(root, platform)
            if not profile.adapter.enabled:
                raise SessionError(f"platform {platform} runtime profile is disabled")
            # A capability-verification smoke exercises the full pipeline but must
            # not record a runtime session: session records describe real host
            # activity, not a probe. (This is intentional, not an F8 workaround —
            # the per-session registry means it would no longer conflict, but a
            # verify still should not pollute the session registry.)
            if not os.environ.get("MAIKA_HOOK_SMOKE"):
                session_id = (os.environ.get("MAIKA_SESSION_ID")
                              or f"{runtime}-{os.getppid()}-{os.getpid()}")
                record_session(root, platform, source="native-hook",
                               session_id=session_id)
        except (SessionError, PlatformProfileError) as exc:
            print(f"maika hook write-gate: {exc}", file=sys.stderr)
            return 2
    gate_path = root.joinpath(core_root, *_WRITE_GATE_REL)
    if not gate_path.is_file():
        print(
            "maika hook write-gate: canonical project evaluator missing at "
            f"{core_root}/{'/'.join(_WRITE_GATE_REL)} — denying "
            "(run `maika repair --all-safe`)",
            file=sys.stderr,
        )
        return 2
    module = _load_write_gate(gate_path)
    return module.main(
        argv=["--framework-root", core_root, "--runtime", runtime],
        stdin_text=stdin_text,
    )
