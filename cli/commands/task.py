"""maika task — public vNext task workflow commands."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from cli.scaffold import load_resolved_config


COMMAND_MAP = {
    "explore": "vnext-validate-reasoning",
    "spec": "vnext-validate-spec",
    "plan": "vnext-compile",
    "validate-plan": "vnext-compile",
    "review": "vnext-review-plan",
    "apply": "vnext-run",
    "resume": "vnext-status",
}


def _framework_root(target: Path) -> str:
    resolved = load_resolved_config(target)
    return (resolved or {}).get("framework_root", ".maika")


def _workspace(target: Path, framework_root: str, change_id: str) -> Path:
    return target / framework_root / "changes" / change_id


def _orchestrator(target: Path, framework_root: str) -> Path:
    return target / framework_root / "tools" / "microloop-orchestrator" / "orchestrator.py"


def _run(cmd: list[str], cwd: Path) -> int:
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, end="", file=sys.stderr)
    return proc.returncode


def _print_status(target: Path, framework_root: str, change_id: str | None = None) -> int:
    changes = target / framework_root / "changes"
    if change_id:
        workspaces = [_workspace(target, framework_root, change_id)]
    else:
        workspaces = sorted(p for p in changes.glob("*") if (p / "STATE.yaml").exists())
    if not workspaces:
        print("No vNext task workspaces found.")
        return 0
    for ws in workspaces:
        state = yaml.safe_load((ws / "STATE.yaml").read_text(encoding="utf-8")) or {}
        change = yaml.safe_load((ws / "CHANGE.yaml").read_text(encoding="utf-8")) or {}
        print(f"{change.get('change_id', ws.name)}: {state.get('state')} — {change.get('title', '')}")
        queue = ws / "generated" / "TASK_QUEUE.json"
        if queue.exists():
            doc = json.loads(queue.read_text(encoding="utf-8"))
            for task in doc.get("tasks", []):
                print(f"  - {task.get('id')}: {task.get('status')}")
    return 0


def _cancel(target: Path, framework_root: str, change_id: str) -> int:
    ws = _workspace(target, framework_root, change_id)
    state_path = ws / "STATE.yaml"
    if not state_path.exists():
        print(f"No such vNext task workspace: {change_id}")
        return 1
    state = yaml.safe_load(state_path.read_text(encoding="utf-8")) or {}
    state.update(state="CANCELLED", updated_at=datetime.now(timezone.utc).isoformat())
    state_path.write_text(yaml.safe_dump(state, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(f"Cancelled {change_id}")
    return 0


def _transition(
    target: Path, framework_root: str, change_id: str, expected: str, new_state: str
) -> int:
    ws = _workspace(target, framework_root, change_id)
    state_path = ws / "STATE.yaml"
    if not state_path.exists():
        print(f"No such vNext task workspace: {change_id}")
        return 1
    state = yaml.safe_load(state_path.read_text(encoding="utf-8")) or {}
    if state.get("state") != expected:
        print(f"Refused: wrong state {state.get('state')} (expected {expected})")
        return 1
    state.update(state=new_state, updated_at=datetime.now(timezone.utc).isoformat(), blocked=None)
    state_path.write_text(yaml.safe_dump(state, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(f"{change_id}: {expected} -> {new_state}")
    return 0


def run_task(
    action: str,
    target_dir: str = ".",
    change_id: str | None = None,
    klass: str = "small",
    title: str | None = None,
) -> int:
    target = Path(target_dir).resolve()
    framework_root = _framework_root(target)
    orchestrator = _orchestrator(target, framework_root)
    if action == "status":
        return _print_status(target, framework_root, change_id)
    if action == "cancel":
        if not change_id:
            print("task cancel requires --id")
            return 2
        return _cancel(target, framework_root, change_id)
    if action == "reconcile":
        if not change_id:
            print("task reconcile requires --id")
            return 2
        return _transition(target, framework_root, change_id, "RECONCILING", "BRAINSTORMING")
    if action == "brainstorm":
        if not change_id:
            print("task brainstorm requires --id")
            return 2
        return _transition(target, framework_root, change_id, "BRAINSTORMING", "SPEC_REVIEW")
    if action in {"verify", "archive"}:
        print(f"task {action} is reserved for the W6 verification/archive cutover.")
        return 2
    if not orchestrator.exists():
        print(f"Missing vNext orchestrator: {orchestrator}")
        print("Run `maika update` to refresh the target scaffold.")
        return 2
    if action == "start":
        if not change_id or not title:
            print("task start requires --id and --title")
            return 2
        changes_root = target / framework_root / "changes"
        changes_root.mkdir(parents=True, exist_ok=True)
        return _run([
            sys.executable, str(orchestrator),
            "vnext-init",
            "--changes-root", str(changes_root),
            "--id", change_id,
            "--class", klass,
            "--title", title,
        ], target)
    if action not in COMMAND_MAP:
        print(f"Unknown task action: {action}")
        return 2
    if not change_id:
        print(f"task {action} requires --id")
        return 2
    ws = _workspace(target, framework_root, change_id)
    return _run([
        sys.executable, str(orchestrator),
        COMMAND_MAP[action],
        "--workspace", str(ws),
        "--repo-root", str(target),
    ], target)
