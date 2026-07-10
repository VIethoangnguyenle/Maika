"""maika task — public vNext task workflow commands."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from cli.scaffold import generate_knowledge_index, load_resolved_config


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


def _archive_workspace(target: Path, framework_root: str, change_id: str) -> Path:
    return target / framework_root / "archive" / change_id


def _orchestrator(target: Path, framework_root: str) -> Path:
    return target / framework_root / "tools" / "microloop-orchestrator" / "orchestrator.py"


def _maika_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


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


def _read_state(ws: Path) -> dict | None:
    state_path = ws / "STATE.yaml"
    if not state_path.exists():
        return None
    return _load_yaml(state_path)


def _write_state(ws: Path, state: dict, new_state: str) -> None:
    state.update(state=new_state, updated_at=_now(), blocked=None)
    _write_yaml(ws / "STATE.yaml", state)


def _command_record(name: str, expected: str, observed: str, exit_code: int = 0) -> dict:
    return {
        "name": name,
        "command": f"internal:{name}",
        "expected_output": expected,
        "observed_output": observed,
        "exit_code": exit_code,
        "timestamp": _now(),
        "interpretation": "pass" if exit_code == 0 else "fail",
    }


def _run_declared_commands(target: Path, declared: list) -> list[dict]:
    """Run real verification commands declared in verification/COMMANDS.yaml and
    record command, expected, observed output, exit code, timestamp, interpretation.
    A command passes only when it exits 0 AND (if declared) its expected substring
    is in the observed output — completion never rests on exit code alone."""
    records: list[dict] = []
    for item in declared or []:
        command = item.get("command")
        if not command:
            continue
        name = item.get("name") or command
        expected = str(item.get("expected", ""))
        try:
            proc = subprocess.run(command, cwd=str(target), shell=True,
                                  capture_output=True, text=True, timeout=600)
            observed = ((proc.stdout or "") + (proc.stderr or "")).strip()
            exit_code = proc.returncode
        except subprocess.SubprocessError as exc:
            observed, exit_code = f"command error: {exc}", 1
        ok = exit_code == 0 and (expected in observed if expected else True)
        records.append({
            "name": name,
            "command": command,
            "expected_output": expected,
            "observed_output": observed[-2000:],
            "exit_code": exit_code,
            "timestamp": _now(),
            "interpretation": "pass" if ok else "fail",
        })
    return records


def _apply_knowledge_lifecycle(ws: Path) -> dict:
    """Turn reviews/KNOWLEDGE_IMPACT.yaml into recorded lifecycle actions:
    promote candidates, supersede/invalidate stale entries, save episodic memory,
    request graph refresh. Actions are recorded in the archive manifest so the
    curator's promote/supersede/save/refresh is auditable."""
    ki_path = ws / "reviews" / "KNOWLEDGE_IMPACT.yaml"
    ki = _load_yaml(ki_path) if ki_path.exists() else {}
    return {
        "promoted": ki.get("new_candidates") or [],
        "superseded": ki.get("superseded_decisions") or [],
        "stale_invalidated": ki.get("stale_entries") or [],
        "memory_saved": ki.get("memory_updates") or [],
        "graph_refresh_requested": bool(ki.get("graph_refresh_required")),
    }


_DEAD_REFERENCE_PATTERNS = (
    "-".join(("idea", "to", "task")),
    "-".join(("index", "source")),
    "-".join(("convention", "scan")),
    "-".join(("approve", "conventions")),
    "-".join(("dna", "scan")),
    "-".join(("approve", "dna")),
    "".join(("Open", "Spec")),
    "".join(("open", "spec")),
)


def _scan_workspace_refs(ws: Path) -> list[str]:
    hits: list[str] = []
    for path in sorted(p for p in ws.rglob("*") if p.is_file()):
        if path.parts[-2:] == ("verification", "COMMANDS.yaml"):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in _DEAD_REFERENCE_PATTERNS:
            if pattern in text:
                hits.append(f"{path.relative_to(ws)}:{pattern}")
    return hits


def _task_artifacts_ok(ws: Path, queue_doc: dict) -> tuple[bool, str]:
    tasks = queue_doc.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        return False, "task queue has no tasks"
    for task in tasks:
        task_id = task.get("id")
        if task.get("status") != "done":
            return False, f"{task_id}: status is not done"
        result_path = ws / (task.get("result_path") or f"results/{task_id}.yaml")
        review_path = ws / (task.get("review_path") or f"reviews/{task_id}.md")
        if not result_path.exists():
            return False, f"{task_id}: missing result {result_path.relative_to(ws)}"
        if not review_path.exists():
            return False, f"{task_id}: missing review {review_path.relative_to(ws)}"
        if "VERDICT: APPROVED" not in review_path.read_text(encoding="utf-8"):
            return False, f"{task_id}: review is not approved"
    return True, f"{len(tasks)} task(s) done and reviewed"


def _write_verification(ws: Path, change_id: str, commands: list[dict], verdict: str,
                        declared: list | None = None) -> None:
    verification = ws / "verification"
    verification.mkdir(exist_ok=True)
    payload: dict = {"commands": commands}
    if declared:
        payload["declared"] = declared
    _write_yaml(verification / "COMMANDS.yaml", payload)
    lines = [
        f"# Verification Report: {change_id}",
        "",
        f"VERDICT: {verdict}",
        f"checked_at: {_now()}",
        "",
        "## Evidence",
    ]
    for record in commands:
        lines.extend([
            f"- {record['name']}: {record['interpretation']}",
            f"  observed: {record['observed_output']}",
        ])
    (verification / "VERIFICATION_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _verify(target: Path, framework_root: str, change_id: str) -> int:
    ws = _workspace(target, framework_root, change_id)
    state = _read_state(ws)
    if state is None:
        print(f"No such vNext task workspace: {change_id}")
        return 1
    if state.get("state") not in {"FINAL_REVIEW", "VERIFYING"}:
        print(f"Refused: verification requires FINAL_REVIEW or VERIFYING (found {state.get('state')})")
        return 1

    commands: list[dict] = []
    commands_path = ws / "verification" / "COMMANDS.yaml"
    declared = (_load_yaml(commands_path).get("declared") if commands_path.exists() else None) or []
    final_review = ws / "reviews" / "FINAL_REVIEW.md"
    if not final_review.exists():
        commands.append(_command_record("final-review-approved", "VERDICT: APPROVED", "missing final review", 1))
        _write_verification(ws, change_id, commands, "FAILED_VERIFICATION")
        print("Refused: final review is missing")
        return 1
    final_text = final_review.read_text(encoding="utf-8")
    if "VERDICT: APPROVED" not in final_text:
        commands.append(_command_record("final-review-approved", "VERDICT: APPROVED", "final review not approved", 1))
        _write_verification(ws, change_id, commands, "FAILED_VERIFICATION")
        print("Refused: final review is not approved")
        return 1
    commands.append(_command_record("final-review-approved", "VERDICT: APPROVED", "approved"))

    queue_path = ws / "generated" / "TASK_QUEUE.json"
    if not queue_path.exists():
        commands.append(_command_record("task-results-reviewed", "queue exists", "missing task queue", 1))
        _write_verification(ws, change_id, commands, "FAILED_VERIFICATION")
        print("Refused: task queue is missing")
        return 1
    queue_doc = json.loads(queue_path.read_text(encoding="utf-8"))
    ok, detail = _task_artifacts_ok(ws, queue_doc)
    commands.append(_command_record("task-results-reviewed", "all tasks done with approved reviews", detail, 0 if ok else 1))
    if not ok:
        _write_verification(ws, change_id, commands, "FAILED_VERIFICATION")
        print(f"Refused: {detail}")
        return 1

    dead_refs = _scan_workspace_refs(ws)
    commands.append(_command_record(
        "dead-reference-scan",
        "no obsolete vNext references in task workspace",
        "no hits" if not dead_refs else "; ".join(dead_refs),
        0 if not dead_refs else 1,
    ))
    if dead_refs:
        _write_verification(ws, change_id, commands, "FAILED_VERIFICATION", declared)
        print("Refused: obsolete references found in task workspace")
        return 1

    # Run real declared verification commands (build/test/lint/...) fresh.
    if declared:
        declared_records = _run_declared_commands(target, declared)
        commands.extend(declared_records)
        if any(record["interpretation"] == "fail" for record in declared_records):
            _write_verification(ws, change_id, commands, "FAILED_VERIFICATION", declared)
            print("Refused: a declared verification command failed")
            return 1

    _write_verification(ws, change_id, commands, "VERIFIED", declared)
    _write_state(ws, state, "COMPLETED")
    print(f"Verified {change_id}")
    return 0


def _archive(target: Path, framework_root: str, change_id: str) -> int:
    ws = _workspace(target, framework_root, change_id)
    state = _read_state(ws)
    if state is None:
        print(f"No such vNext task workspace: {change_id}")
        return 1
    if state.get("state") != "COMPLETED":
        print(f"Refused: archive requires COMPLETED (found {state.get('state')})")
        return 1
    verification_report = ws / "verification" / "VERIFICATION_REPORT.md"
    if not verification_report.exists() or "VERDICT: VERIFIED" not in verification_report.read_text(encoding="utf-8"):
        print("Refused: archive requires verified verification/VERIFICATION_REPORT.md")
        return 1

    ki_path = ws / "reviews" / "KNOWLEDGE_IMPACT.yaml"
    if not ki_path.exists():
        print("Refused: archive requires reviews/KNOWLEDGE_IMPACT.yaml (final knowledge impact)")
        return 1
    ki = _load_yaml(ki_path)
    missing_lanes = [k for k in ("stale_entries", "superseded_decisions", "new_candidates",
                                 "graph_refresh_required", "memory_updates") if k not in ki]
    if missing_lanes:
        print(f"Refused: KNOWLEDGE_IMPACT.yaml missing lanes: {', '.join(missing_lanes)}")
        return 1

    dest = _archive_workspace(target, framework_root, change_id)
    if dest.exists():
        print(f"Refused: archive destination already exists: {dest}")
        return 1

    long_term = target / framework_root / "knowledge" / "long-term"
    long_term.mkdir(parents=True, exist_ok=True)
    generate_knowledge_index(_maika_root(), target, framework_root)
    lifecycle = _apply_knowledge_lifecycle(ws)
    _write_yaml(ws / "ARCHIVE_MANIFEST.yaml", {
        "change_id": change_id,
        "archived_at": _now(),
        "source_state": "COMPLETED",
        "verification_report": "verification/VERIFICATION_REPORT.md",
        "knowledge_index": "knowledge/long-term/knowledge-index.yaml",
        "knowledge_lifecycle": lifecycle,
    })
    _write_state(ws, state, "ARCHIVED")
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(ws), str(dest))
    print(f"Archived {change_id} -> {dest}")
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
    if action == "verify":
        if not change_id:
            print("task verify requires --id")
            return 2
        return _verify(target, framework_root, change_id)
    if action == "archive":
        if not change_id:
            print("task archive requires --id")
            return 2
        return _archive(target, framework_root, change_id)
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
