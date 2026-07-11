"""maika task — public vNext task workflow commands."""

from __future__ import annotations

import json
import importlib.util
import getpass
import re
import shlex
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from cli.scaffold import load_resolved_config
from cli.provider_actions import build_learning_executors
from cli.runtime.policy import load_runtime_policy
from cli.knowledge_control import (
    apply_project_learning,
    validate_markdown_knowledge_trace,
    validate_skill_feedback,
)


COMMAND_MAP = {
    "explore": "vnext-dispatch-role",
    "reconcile": "vnext-dispatch-role",
    "brainstorm": "vnext-dispatch-role",
    "spec": "vnext-dispatch-role",
    "plan": "vnext-dispatch-role",
    "validate-reasoning": "vnext-validate-reasoning",
    "validate-spec": "vnext-validate-spec",
    "validate-plan": "vnext-compile",
    "review": "vnext-review-plan",
    "apply": "vnext-run",
    "resume": "vnext-resume",
}

# Authoring actions execute their routed skill in an isolated worker (PR 10);
# the role keys mirror config/workflow-router.yaml.
DISPATCH_ROLE_BY_ACTION = {
    "explore": "grounding",
    "reconcile": "reconciliation",
    "brainstorm": "brainstorming",
    "spec": "spec",
    "plan": "planning",
}


def action_requires_worker(action: str) -> bool:
    return action in {"review", "apply"} or action in DISPATCH_ROLE_BY_ACTION


def _framework_root(target: Path) -> str:
    resolved = load_resolved_config(target)
    return (resolved or {}).get("framework_root", ".maika")


def _workspace(target: Path, framework_root: str, change_id: str) -> Path:
    return target / framework_root / "changes" / change_id


def _archive_workspace(target: Path, framework_root: str, change_id: str) -> Path:
    return target / framework_root / "archive" / change_id


def _orchestrator(target: Path, framework_root: str) -> Path:
    return target / framework_root / "tools" / "microloop-orchestrator" / "orchestrator.py"


def _state_service(target: Path, framework_root: str):
    module_path = target / framework_root / "tools" / "microloop-orchestrator" / "vnext_state.py"
    if not module_path.exists():
        raise RuntimeError(f"canonical state service unavailable: {module_path}")
    spec = importlib.util.spec_from_file_location("maika_target_vnext_state", module_path)
    module = importlib.util.module_from_spec(spec)
    module_dir = str(module_path.parent)
    inserted = module_dir not in sys.path
    if inserted:
        sys.path.insert(0, module_dir)
    try:
        spec.loader.exec_module(module)
    finally:
        if inserted:
            sys.path.remove(module_dir)
    return module


def _runtime_hardening(target: Path, framework_root: str):
    module_path = target / framework_root / "tools" / "microloop-orchestrator" / "runtime_hardening.py"
    if not module_path.exists():
        raise RuntimeError(f"runtime command policy unavailable: {module_path}")
    spec = importlib.util.spec_from_file_location("maika_target_runtime_hardening", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _bootstrap_ready(target: Path, framework_root: str) -> tuple[bool, str]:
    from cli.commands.bootstrap import ACK_REL, ENV_REPORT_REL, verify_ack_freshness

    framework = target / framework_root
    report = framework / ENV_REPORT_REL
    if not report.exists():
        return False, f"missing {ENV_REPORT_REL} (run `maika bootstrap`)"
    candidates = [
        framework / "tools" / "gate-check" / "gates.py",
        Path(__file__).resolve().parents[2] / ".maika" / "tools" / "gate-check" / "gates.py",
    ]
    module_path = next((path for path in candidates if path.exists()), None)
    if module_path is None:
        return False, "bootstrap-complete validator unavailable"
    spec = importlib.util.spec_from_file_location("maika_bootstrap_gate", module_path)
    gates = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gates)
    result = gates.validate_bootstrap_complete(report.read_text(encoding="utf-8"))
    if not result.ok:
        return False, result.reason
    ack = framework / ACK_REL
    if not ack.exists():
        return False, f"missing {ACK_REL} (run `maika bootstrap --ack`)"
    ack_result = gates.validate_bootstrap_ack(ack.read_text(encoding="utf-8"))
    if not ack_result.ok:
        return False, ack_result.reason
    return verify_ack_freshness(framework)


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
    try:
        _state_service(target, framework_root).transition(ws, "CANCELLED")
    except (RuntimeError, ValueError) as exc:
        print(f"Refused: {exc}")
        return 1
    print(f"Cancelled {change_id}")
    return 0


def _with_workspace_lock(target: Path, framework_root: str, change_id: str, operation):
    policy = _runtime_hardening(target, framework_root)
    ws = _workspace(target, framework_root, change_id)
    lock = policy.WorkspaceLock(ws / "generated" / "WORKSPACE.lock", task_id=change_id)
    try:
        lock.acquire()
    except policy.WorkspaceBusy as exc:
        print(f"Refused: {exc}")
        return 1
    try:
        return operation()
    finally:
        archived_lock = _archive_workspace(target, framework_root, change_id) / "generated" / "WORKSPACE.lock"
        if not lock.path.exists() and archived_lock.exists():
            lock.path = archived_lock
        lock.release()


def _force_unlock(target: Path, framework_root: str, change_id: str) -> int:
    policy = _runtime_hardening(target, framework_root)
    path = _workspace(target, framework_root, change_id) / "generated" / "WORKSPACE.lock"
    if policy.WorkspaceLock.force_unlock(path, change_id):
        print(f"Force-unlocked {change_id}; audit record written")
        return 0
    print(f"No workspace lock exists for {change_id}")
    return 1


def _read_state(target: Path, framework_root: str, ws: Path) -> dict | None:
    state_path = ws / "STATE.yaml"
    if not state_path.exists():
        return None
    return _state_service(target, framework_root).load_state(ws)


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


def _run_declared_commands(target: Path, framework_root: str, declared: list,
                           workspace: Path | None = None) -> list[dict]:
    """Run real verification commands declared in verification/COMMANDS.yaml and
    record command, expected, observed output, exit code, timestamp, interpretation.
    A command passes only when it exits 0 AND (if declared) its expected substring
    is in the observed output — completion never rests on exit code alone."""
    records: list[dict] = []
    profiles_dir = target / framework_root / "profiles"
    config_path = profiles_dir / "execution-mode.local.yaml"
    if not config_path.exists():
        config_path = profiles_dir / "execution-mode.yaml"
    config = _load_yaml(config_path) if config_path.exists() else {}
    command_policy = load_runtime_policy(config).command_policy
    policy_module = _runtime_hardening(target, framework_root)
    registry = policy_module.load_verification_profiles(profiles_dir / "verification-profiles.yaml")
    for item in declared or []:
        command = None
        name = item.get("name") or item.get("profile") or "verification"
        expected = str(item.get("expected", ""))
        try:
            allowed_profiles = command_policy.get("allowed_profiles")
            if allowed_profiles is not None and item.get("profile") not in allowed_profiles:
                raise policy_module.CommandDenied(f"verification profile is disabled: {item.get('profile')}")
            command = policy_module.compile_verification_command(item, registry, target)
            command_id = str(item.get("id") or item.get("name") or item.get("profile"))
            approval_path = (
                workspace / "approvals" / f"{command_id}.yaml"
                if workspace and re.fullmatch(r"[A-Za-z0-9_.-]+", command_id) else None
            )
            human_confirmed = bool(
                approval_path and policy_module.trusted_approval_matches(
                    approval_path, workspace.name, command
                )
            )
            record = policy_module.execute_command(
                command, target,
                # Agent-authored `human_confirmed` is intentionally ignored.
                human_confirmed=human_confirmed,
                allowed_executables=command_policy.get("allowed_executables"),
                confirmation_executables=command_policy.get("requires_human_confirmation"),
                timeout=int(command_policy.get("timeout_seconds", 600)),
                output_cap=int(command_policy.get("output_cap_bytes", 2000)),
            )
            observed, exit_code = record["observed_output"].strip(), record["exit_code"]
        except Exception as exc:
            record = {"command": str(command or item), "category": item.get("category", "other"), "shell": False}
            observed, exit_code = f"command policy error: {exc}", 1
        ok = exit_code == 0 and (expected in observed if expected else True)
        records.append({
            "name": name,
            "command": record["command"],
            "category": record.get("category", item.get("category", "other")),
            "expected_output": expected,
            "observed_output": observed[-2000:],
            "exit_code": exit_code,
            "timestamp": _now(),
            "interpretation": "pass" if ok else "fail",
            "shell": False,
        })
    return records


_VERIFICATION_POLICY = {
    "trivial": {"minimum": 0, "categories": set()},
    "small": {"minimum": 1, "categories": set()},
    "standard": {"minimum": 1, "categories": {"test_or_build"}},
    "architectural": {"minimum": 2, "categories": {"build", "test"}},
}


def _verification_policy_result(klass: str, records: list[dict]) -> tuple[bool, str]:
    policy = _VERIFICATION_POLICY.get(klass, _VERIFICATION_POLICY["standard"])
    real = [record for record in records if not str(record.get("command", "")).startswith("internal:")]
    passed = [record for record in real if record.get("interpretation") == "pass"]
    categories = {str(record.get("category", "other")) for record in passed}
    required = policy["categories"]
    if "test_or_build" in required and not categories.intersection({"test", "build"}):
        return False, f"{klass} requires categories: test or build; observed {', '.join(sorted(categories)) or 'none'}"
    missing = (required - {"test_or_build"}) - categories
    if missing:
        return False, f"{klass} requires categories: {', '.join(sorted(required))}; missing {', '.join(sorted(missing))}"
    if len(passed) < policy["minimum"]:
        return False, f"{klass} requires at least {policy['minimum']} real verification command(s); observed {len(passed)}"
    return True, f"{len(passed)} real command(s) satisfy {klass} policy"


def _apply_knowledge_lifecycle(target: Path, framework_root: str, ws: Path) -> dict:
    """Execute verified learning actions; provider absence becomes explicit outbox."""
    memory_saver, graph_refresher = build_learning_executors(target, framework_root)
    return apply_project_learning(
        target, framework_root, ws,
        memory_saver=memory_saver, graph_refresher=graph_refresher,
    )


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


def _task_artifacts_ok(ws: Path, queue_doc: dict, review_policy) -> tuple[bool, str]:
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
        try:
            review_policy.parse_review(
                review_path.read_text(encoding="utf-8"), "task",
                queue_doc.get("base_commit"), "sha256:" + queue_doc.get("plan_sha256", ""),
            )
        except review_policy.ReviewInvalid as exc:
            return False, f"{task_id}: invalid structured review: {exc}"
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
    evidence_ids = [record["name"] for record in commands]
    lines.extend([
        "",
        "## Knowledge Trace",
        "```yaml",
        "decision:",
        f"  id: DEC-VERIFY-{change_id}",
        f"  statement: Verification result is {verdict}.",
        "  type: verification_claim",
        "  knowledge_questions:",
        "    - Do fresh commands and reviews prove the completion claim?",
        "  evidence_ids:",
        *[f"    - {item}" for item in evidence_ids],
        "  authority: live runtime/test evidence",
        "  conflicts: []",
        "  assumptions: []",
        "  confidence: high",
        "  freshness: verified",
        "  verdict: verified",
        "```",
    ])
    (verification / "VERIFICATION_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _verify_lightweight(target: Path, framework_root: str, ws: Path, change: dict) -> int:
    task = _load_yaml(ws / "TASK.yaml")
    declared = (task.get("verification") or {}).get("commands") or []
    commands = _run_declared_commands(target, framework_root, declared, ws) if declared else []
    if any(record["interpretation"] == "fail" for record in commands):
        _write_verification(ws, change["change_id"], commands, "FAILED_VERIFICATION", declared)
        print("Refused: a lightweight verification command failed")
        return 1
    if change["class"] == "trivial" and not commands:
        scoped = [path for values in ((task.get("scope") or {}).get("files") or {}).values()
                  for path in (values or [])]
        doc_suffixes = {".md", ".rst", ".txt", ".adoc"}
        non_documentation = [path for path in scoped if Path(path).suffix.lower() not in doc_suffixes]
        if non_documentation:
            reason = "trivial may omit real commands only for documentation-only scope"
            commands.append(_command_record("real-verification-policy", reason,
                                            ", ".join(non_documentation), 1))
            _write_verification(ws, change["change_id"], commands, "FAILED_VERIFICATION", declared)
            print(f"Refused: {reason}")
            return 1
    policy_ok, reason = _verification_policy_result(change["class"], commands)
    commands.append(_command_record(
        "real-verification-policy", "change-class verification policy satisfied",
        reason, 0 if policy_ok else 1,
    ))
    if not policy_ok:
        _write_verification(ws, change["change_id"], commands, "FAILED_VERIFICATION", declared)
        print(f"Refused: real verification policy failed: {reason}")
        return 1
    _write_verification(ws, change["change_id"], commands, "VERIFIED", declared)
    service = _state_service(target, framework_root)
    state = service.load_state(ws)
    metrics = dict(state.get("runtime_metrics") or {})
    metrics["real_verification_commands"] = len([
        record for record in commands if not record["command"].startswith("internal:")
        and record["interpretation"] == "pass"
    ])
    metrics["tool_calls"] = int(metrics.get("tool_calls") or 0) + metrics["real_verification_commands"]
    service.record_runtime_metrics(ws, metrics)
    service.transition(ws, "COMPLETED")
    print(f"Verified {change['change_id']}")
    return 0


def _verify(target: Path, framework_root: str, change_id: str) -> int:
    ws = _workspace(target, framework_root, change_id)
    state = _read_state(target, framework_root, ws)
    if state is None:
        print(f"No such vNext task workspace: {change_id}")
        return 1
    if state.get("state") not in {"FINAL_REVIEW", "VERIFYING"}:
        print(f"Refused: verification requires FINAL_REVIEW or VERIFYING (found {state.get('state')})")
        return 1

    change = _load_yaml(ws / "CHANGE.yaml")
    if change.get("class") in {"trivial", "small"}:
        if state.get("state") != "VERIFYING":
            print(f"Refused: lightweight verification requires VERIFYING (found {state.get('state')})")
            return 1
        return _verify_lightweight(target, framework_root, ws, change)

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
    review_policy = _runtime_hardening(target, framework_root)
    queue_path = ws / "generated" / "TASK_QUEUE.json"
    queue_doc = json.loads(queue_path.read_text(encoding="utf-8")) if queue_path.exists() else {}
    try:
        final_verdict = review_policy.parse_review(
            final_text, "final", queue_doc.get("base_commit"),
            "sha256:" + queue_doc.get("plan_sha256", ""),
        ).get("verdict")
    except review_policy.ReviewInvalid:
        final_verdict = None
    if final_verdict != "APPROVED":
        commands.append(_command_record("final-review-approved", "VERDICT: APPROVED", "final review not approved", 1))
        _write_verification(ws, change_id, commands, "FAILED_VERIFICATION")
        print("Refused: final review is not approved")
        return 1
    commands.append(_command_record("final-review-approved", "VERDICT: APPROVED", "approved"))

    if not queue_path.exists():
        commands.append(_command_record("task-results-reviewed", "queue exists", "missing task queue", 1))
        _write_verification(ws, change_id, commands, "FAILED_VERIFICATION")
        print("Refused: task queue is missing")
        return 1
    ok, detail = _task_artifacts_ok(ws, queue_doc, review_policy)
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
        declared_records = _run_declared_commands(target, framework_root, declared, ws)
        commands.extend(declared_records)
        if any(record["interpretation"] == "fail" for record in declared_records):
            _write_verification(ws, change_id, commands, "FAILED_VERIFICATION", declared)
            print("Refused: a declared verification command failed")
            return 1

    policy_ok, policy_reason = _verification_policy_result(change.get("class", "standard"), commands)
    commands.append(_command_record(
        "real-verification-policy", "change-class verification policy satisfied",
        policy_reason, 0 if policy_ok else 1,
    ))
    if not policy_ok:
        _write_verification(ws, change_id, commands, "FAILED_VERIFICATION", declared)
        print(f"Refused: real verification policy failed: {policy_reason}")
        return 1

    skill_feedback = ws / "reviews" / "SKILL_FEEDBACK.yaml"
    if skill_feedback.exists():
        feedback = _load_yaml(skill_feedback)
        feedback["change_id"] = change_id
        feedback["verified"] = True
    else:
        feedback = {"version": 1, "change_id": change_id, "verified": True, "observations": []}
    _write_yaml(skill_feedback, feedback)
    feedback_gate = validate_skill_feedback(skill_feedback.read_text(encoding="utf-8"))
    commands.append(_command_record(
        "skill-feedback", "valid verified SKILL_FEEDBACK.yaml",
        "valid" if feedback_gate.ok else feedback_gate.reason,
        0 if feedback_gate.ok else 1,
    ))
    if not feedback_gate.ok:
        _write_verification(ws, change_id, commands, "FAILED_VERIFICATION", declared)
        print("Refused: SKILL_FEEDBACK.yaml failed skill-feedback gate")
        return 1

    _write_verification(ws, change_id, commands, "VERIFIED", declared)
    metrics = dict(queue_doc.get("runtime_metrics") or {})
    metrics["real_verification_commands"] = len([
        record for record in commands if not record["command"].startswith("internal:")
        and record["interpretation"] == "pass"
    ])
    metrics["tool_calls"] = int(metrics.get("tool_calls") or 0) + metrics["real_verification_commands"]
    _state_service(target, framework_root).record_runtime_metrics(ws, metrics)
    _state_service(target, framework_root).transition(ws, "COMPLETED")
    print(f"Verified {change_id}")
    return 0


def _archive(target: Path, framework_root: str, change_id: str) -> int:
    ws = _workspace(target, framework_root, change_id)
    state = _read_state(target, framework_root, ws)
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

    feedback_path = ws / "reviews" / "SKILL_FEEDBACK.yaml"
    if not feedback_path.exists():
        print("Refused: archive requires reviews/SKILL_FEEDBACK.yaml")
        return 1
    feedback_gate = validate_skill_feedback(feedback_path.read_text(encoding="utf-8"))
    if not feedback_gate.ok:
        print(f"Refused: SKILL_FEEDBACK.yaml failed skill-feedback gate: {feedback_gate.reason}")
        return 1

    dest = _archive_workspace(target, framework_root, change_id)
    if dest.exists():
        print(f"Refused: archive destination already exists: {dest}")
        return 1

    long_term = target / framework_root / "knowledge" / "long-term"
    long_term.mkdir(parents=True, exist_ok=True)
    try:
        lifecycle = _apply_knowledge_lifecycle(target, framework_root, ws)
    except ValueError as exc:
        print(f"Refused: knowledge lifecycle failed: {exc}")
        return 1
    _write_yaml(ws / "ARCHIVE_MANIFEST.yaml", {
        "change_id": change_id,
        "archived_at": _now(),
        "source_state": "COMPLETED",
        "verification_report": "verification/VERIFICATION_REPORT.md",
        "knowledge_index": "knowledge/long-term/knowledge-index.yaml",
        "knowledge_index_sha256": lifecycle["knowledge_index_sha256"],
        "knowledge_lifecycle": lifecycle,
    })
    _state_service(target, framework_root).transition(ws, "ARCHIVED")
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
    service = _state_service(target, framework_root)
    state = service.load_state(ws)
    if state.get("state") != expected:
        print(f"Refused: wrong state {state.get('state')} (expected {expected})")
        return 1
    if expected == "RECONCILING":
        reconciliation = ws / "RECONCILIATION.md"
        trace = validate_markdown_knowledge_trace(
            reconciliation.read_text(encoding="utf-8") if reconciliation.exists() else ""
        )
        if not trace.ok:
            print(f"Refused: reconciliation Knowledge Trace failed: {trace.reason}")
            return 1
    try:
        service.transition(ws, new_state)
    except ValueError as exc:
        print(f"Refused: {exc}")
        return 1
    print(f"{change_id}: {expected} -> {new_state}")
    return 0


def _approve_command(target: Path, framework_root: str, change_id: str, command_id: str) -> int:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", command_id or ""):
        print("Refused: command id must contain only letters, digits, dot, dash or underscore")
        return 2
    ws = _workspace(target, framework_root, change_id)
    task_path = ws / "TASK.yaml"
    commands_path = ws / "verification" / "COMMANDS.yaml"
    if commands_path.exists():
        declared = _load_yaml(commands_path).get("declared") or []
    elif task_path.exists():
        declared = (_load_yaml(task_path).get("verification") or {}).get("commands") or []
    else:
        declared = []
    proposal = next((item for item in declared if str(item.get("id") or item.get("name") or item.get("profile")) == command_id), None)
    if proposal is None:
        print(f"Refused: unknown verification command id {command_id}")
        return 2
    policy = _runtime_hardening(target, framework_root)
    registry = policy.load_verification_profiles(target / framework_root / "profiles" / "verification-profiles.yaml")
    try:
        command = policy.compile_verification_command(proposal, registry, target)
    except policy.CommandDenied as exc:
        print(f"Refused: {exc}")
        return 2
    approval = {
        "version": 1, "approval_id": f"APPROVAL-{change_id}-{command_id}",
        "change_id": change_id, "command_id": command_id,
        "command_hash": policy.verification_command_hash(command),
        "approved_by": getpass.getuser(), "approved_at": _now(), "source": "cli-user-action",
    }
    path = ws / "approvals" / f"{command_id}.yaml"
    _write_yaml(path, approval)
    print(f"Approved verification command {command_id}")
    return 0


def _route_dry_run(target: Path, framework_root: str, change_id: str, action_arg: str) -> int:
    from cli.agent_content.router import load_router, resolve_route

    ws = _workspace(target, framework_root, change_id)
    if not (ws / "STATE.yaml").exists():
        print(f"No such vNext task workspace: {change_id}")
        return 2
    change = _load_yaml(ws / "CHANGE.yaml")
    state = _load_yaml(ws / "STATE.yaml")
    klass = change.get("effective_class") or change.get("class") or "small"
    try:
        router = load_router(target / framework_root)
        route = resolve_route(router, action_arg, klass, state.get("state"))
    except FileNotFoundError as exc:
        print(f"Refused: no workflow router at {exc}")
        return 2
    except KeyError:
        print(f"Refused: unknown routed action {action_arg}")
        return 2
    payload = {"change_id": change_id, "selected_skill": route.pop("skill"), **route}
    print(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), end="")
    return 0


def run_task(
    action: str,
    target_dir: str = ".",
    change_id: str | None = None,
    klass: str = "small",
    title: str | None = None,
    command_id: str | None = None,
    platform_key: str | None = None,
    action_arg: str | None = None,
) -> int:
    target = Path(target_dir).resolve()
    framework_root = _framework_root(target)
    orchestrator = _orchestrator(target, framework_root)
    if action == "status":
        return _print_status(target, framework_root, change_id)
    if action == "route":
        if not change_id or not action_arg:
            print("task route requires --id and --action")
            return 2
        return _route_dry_run(target, framework_root, change_id, action_arg)
    if action == "cancel":
        if not change_id:
            print("task cancel requires --id")
            return 2
        return _with_workspace_lock(
            target, framework_root, change_id,
            lambda: _cancel(target, framework_root, change_id),
        )
    if action == "approve-command":
        if not change_id or not command_id:
            print("task approve-command requires --id and --command-id")
            return 2
        return _with_workspace_lock(
            target, framework_root, change_id,
            lambda: _approve_command(target, framework_root, change_id, command_id),
        )
    if action == "force-unlock":
        if not change_id:
            print("task force-unlock requires --id")
            return 2
        return _force_unlock(target, framework_root, change_id)
    if action != "start":
        ready, reason = _bootstrap_ready(target, framework_root)
        if not ready:
            print(f"Refused: bootstrap-complete failed: {reason}")
            return 1
    if action == "verify":
        if not change_id:
            print("task verify requires --id")
            return 2
        return _with_workspace_lock(
            target, framework_root, change_id,
            lambda: _verify(target, framework_root, change_id),
        )
    if action == "archive":
        if not change_id:
            print("task archive requires --id")
            return 2
        return _with_workspace_lock(
            target, framework_root, change_id,
            lambda: _archive(target, framework_root, change_id),
        )
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
    command = [
        sys.executable, str(orchestrator),
        COMMAND_MAP[action],
        "--workspace", str(ws),
        "--repo-root", str(target),
    ]
    if action in DISPATCH_ROLE_BY_ACTION:
        command.extend(["--role", DISPATCH_ROLE_BY_ACTION[action]])
    if action_requires_worker(action):
        try:
            from cli.runtime.session import SessionError, resolve_active_platform
            active_platform, _source = resolve_active_platform(
                target, explicit_platform=platform_key,
            )
        except SessionError as exc:
            print(f"Refused: {exc}")
            return 2
        command.extend(["--platform", active_platform])
    return _run(command, target)
