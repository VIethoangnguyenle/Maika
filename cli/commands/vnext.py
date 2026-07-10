import sys
from pathlib import Path
import importlib.util

def _load(name, abs_path):
    spec = importlib.util.spec_from_file_location(name, abs_path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

def _get_root(maika_root):
    return Path(maika_root).resolve() if maika_root else Path(__file__).resolve().parents[2]

def run_compile(workspace, maika_root=None):
    root = _get_root(maika_root)
    pc = _load("plan_compiler", root / ".maika" / "tools" / "microloop-orchestrator" / "plan_compiler.py")
    res = pc.compile_plan(workspace, repo_root=root)
    if res.get("verdict") == "REVISE":
        print(f"FAIL: {res.get('reason')}", file=sys.stderr)
        sys.exit(1)
    print("PASS: Plan compiled")

def run_dispatch(workspace, maika_root=None):
    root = _get_root(maika_root)
    vd = _load("vnext_dispatch", root / ".maika" / "tools" / "microloop-orchestrator" / "vnext_dispatch.py")
    if not vd.run_planning_dispatch(workspace, repo_root=root):
        print("FAIL: Planning dispatch failed (see CONTEXT_REQUEST.yaml)", file=sys.stderr)
        sys.exit(1)
    print("PASS: Planning dispatch OK")

def run_e2e(workspace, maika_root=None):
    root = _get_root(maika_root)
    vd = _load("vnext_dispatch", root / ".maika" / "tools" / "microloop-orchestrator" / "vnext_dispatch.py")
    if not vd.run_planning_dispatch(workspace, repo_root=root):
        print("FAIL: e2e blocked at planning", file=sys.stderr)
        sys.exit(1)
    if not vd.run_dispatch(workspace, repo_root=root):
        print("FAIL: e2e blocked at execution", file=sys.stderr)
        sys.exit(1)
    print("PASS: e2e ok")
