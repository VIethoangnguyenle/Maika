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
import subprocess
import sys
from pathlib import Path
from typing import Optional

from cli.config import project as project_cfg

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
        return cwd
    root = result.stdout.strip()
    return Path(root) if root else cwd


def _load_write_gate(path: Path):
    spec = importlib.util.spec_from_file_location("maika_target_write_gate", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_hook_write_gate(runtime: str, stdin_text: Optional[str] = None) -> int:
    """Delegate a PreToolUse event to the project's write-gate evaluator.

    Missing evaluator (not a Maika project, or a broken install) degrades to
    allow with a diagnostic — a hook that hard-blocks every write in a project
    without the gate installed would be worse than the status quo.
    """
    cwd = Path.cwd()
    root = _locate_project_root(cwd)
    core_root = project_cfg.load(root)["framework"]["core_root"]
    gate_path = root.joinpath(core_root, *_WRITE_GATE_REL)
    if not gate_path.is_file():
        print(
            "maika hook write-gate: no evaluator at "
            f"{core_root}/{'/'.join(_WRITE_GATE_REL)} — allowing "
            "(run `maika init` to install the write gate)",
            file=sys.stderr,
        )
        return 0
    module = _load_write_gate(gate_path)
    return module.main(
        argv=["--framework-root", core_root, "--runtime", runtime],
        stdin_text=stdin_text,
    )
