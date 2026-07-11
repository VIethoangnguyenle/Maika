"""Maika vNext task orchestrator.

The runtime contract is JSON-only: workspaces live under
`<framework-root>/changes/<change-id>` and tasks progress through generated
JSON queues, YAML results, and markdown reviews.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import subprocess
from pathlib import Path

import yaml

import adaptive_runtime as ar
from runtime_hardening import WorkspaceBusy, WorkspaceLock


# Exit-code contract (plan §8.1). Shell automation reads these; blocked is
# never 0.
EXIT_OK = 0        # success / completed phase
EXIT_BLOCKED = 1   # runtime failure or generic blocked
EXIT_CONFIG = 2    # configuration or CLI usage error
EXIT_HUMAN = 3     # human input required
EXIT_BUDGET = 4    # budget exhausted
EXIT_STALE = 5     # stale artifact or contract


def _classify_block(reason: str | None) -> tuple[str, str, int]:
    """Map a blocked outcome's reason to (BLOCK_REASON, code, exit_code).

    BLOCK_REASON is one of vnext_state.BLOCK_REASONS (drives the state machine);
    code is a stable machine label; exit_code is the process exit code.
    """
    text = (reason or "").lower()
    if "budget" in text:
        return "capability", "budget_exhausted", EXIT_BUDGET
    if "stale" in text or "evidence_update_request" in text or "superseded" in text \
            or "stale_plan" in text:
        return "stale_plan", "stale_contract", EXIT_STALE
    if "human" in text or "approval" in text or "confirmation required" in text:
        return "user_input", "human_required", EXIT_HUMAN
    return "verification", "blocked", EXIT_BLOCKED


_RECOVERY_ACTIONS = {
    "budget_exhausted": ["raise worker budget in execution-mode config, or escalate the change class"],
    "stale_contract": ["re-run exploration/plan compile so evidence and hashes are refreshed"],
    "human_required": ["obtain the required trusted approval, then `task resume`"],
    "blocked": ["inspect the blocked task's result/review, fix the cause, then `task resume`"],
}


def _blocked_metadata(reason_text: str | None, resume_state: str) -> dict:
    block_reason, code, exit_code = _classify_block(reason_text)
    return {
        "reason": block_reason,
        "code": code,
        "resume_state": resume_state,
        "detail": reason_text,
        "recovery_actions": _RECOVERY_ACTIONS.get(code, _RECOVERY_ACTIONS["blocked"]),
    }, exit_code


def _execution_config_path(profiles_dir: Path) -> Path:
    local = profiles_dir / "execution-mode.local.yaml"
    if local.exists():
        return local
    return profiles_dir / "execution-mode.yaml"


def _load_gate_check():
    mod = Path(__file__).resolve().parents[1] / "gate-check" / "gates.py"
    spec = importlib.util.spec_from_file_location("gates", mod)
    gates = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gates)
    return gates


def _require_vnext(framework_path: Path) -> tuple[Path, dict] | tuple[None, None]:
    config_path = _execution_config_path(Path(framework_path) / "profiles")
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
    config = config or {}
    if config.get("workflow_engine") != "vnext":
        print("Refused: workflow_engine is not vnext")
        return None, None
    return config_path, config


def _require_bootstrap(framework_path: Path, gates, repo_root: Path) -> bool:
    report = Path(framework_path) / "knowledge" / "active" / "BOOTSTRAP_REPORT.yaml"
    if not report.exists():
        print("Refused: bootstrap-complete requires knowledge/active/BOOTSTRAP_REPORT.yaml")
        return False
    result = gates.validate_bootstrap_complete(report.read_text(encoding="utf-8"))
    if not result.ok:
        print(f"Refused: bootstrap-complete failed: {result.reason}")
        return False
    report_doc = yaml.safe_load(report.read_text(encoding="utf-8")) or {}
    recorded = report_doc.get("repository_commit")
    if recorded != "unavailable":
        probe = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_root,
                               capture_output=True, text=True, check=False)
        if probe.returncode != 0 or probe.stdout.strip() != recorded:
            print("Refused: bootstrap report repository_commit is stale")
            return False
    return True


def topo_sort(tasks):
    """Return tasks ordered so dependencies come first."""
    by_id = {task["id"]: task for task in tasks}
    for task in tasks:
        for dep_id in task.get("depends_on", []):
            if dep_id not in by_id:
                raise ValueError(f"task {task['id']} depends on non-existent task {dep_id}")
    indeg = {task["id"]: 0 for task in tasks}
    for task in tasks:
        for _ in task.get("depends_on", []):
            indeg[task["id"]] += 1
    ready = sorted([task_id for task_id, degree in indeg.items() if degree == 0])
    ordered = []
    while ready:
        task_id = ready.pop(0)
        ordered.append(by_id[task_id])
        for task in tasks:
            if task_id in task.get("depends_on", []):
                indeg[task["id"]] -= 1
                if indeg[task["id"]] == 0:
                    ready.append(task["id"])
        ready.sort()
    if len(ordered) != len(tasks):
        raise ValueError("dependency cycle detected in tasks")
    return ordered


WORKER_PLACEHOLDERS = ("{prompt}", "{prompt_file}", "{repo_root}", "{workspace}", "{task_id}")
_PLACEHOLDER_RE = re.compile(r"\{[a-zA-Z_][a-zA-Z0-9_]*\}")


def _validate_worker_tokens(tokens):
    """Reject any token containing a placeholder we do not understand."""
    allowed = set(WORKER_PLACEHOLDERS)
    for token in tokens:
        for found in _PLACEHOLDER_RE.findall(token):
            if found not in allowed:
                raise ValueError(f"unknown worker placeholder {found}; allowed: {sorted(allowed)}")


def make_worker_runner(worker, ws, repo_root, timeout=900):
    """Adapt a structured worker config into a prompt runner.

    ``worker`` is ``{"executable": str, "args": [str, ...]}``. Tokens may embed
    the placeholders in ``WORKER_PLACEHOLDERS``. The prompt is passed to the
    worker process directly through argv (``shell=False``) — never via a shell
    string — so it is not subject to shell quoting/expansion and is portable
    across POSIX and Windows. ``{prompt_file}`` writes the prompt to a temp file
    under ``<ws>/generated/prompts`` and substitutes its path.
    """
    executable = worker["executable"]
    arg_templates = list(worker.get("args") or [])
    _validate_worker_tokens([executable, *arg_templates])
    ws = Path(ws)
    repo_root = Path(repo_root)
    context = {
        "{repo_root}": str(repo_root),
        "{workspace}": str(ws),
        "{task_id}": ws.name,
    }
    needs_prompt_file = any("{prompt_file}" in tok for tok in [executable, *arg_templates])

    def _render(token, prompt_file_path):
        rendered = token
        for key, value in context.items():
            rendered = rendered.replace(key, value)
        if prompt_file_path is not None:
            rendered = rendered.replace("{prompt_file}", prompt_file_path)
        return rendered

    def runner(prompt):
        prompt_file = None
        if needs_prompt_file:
            prompts_dir = ws / "generated" / "prompts"
            prompts_dir.mkdir(parents=True, exist_ok=True)
            digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:12]
            prompt_file = prompts_dir / f"dispatch-{os.getpid()}-{digest}.txt"
            prompt_file.write_text(prompt, encoding="utf-8")
        prompt_file_path = str(prompt_file) if prompt_file is not None else None
        argv = []
        for token in [executable, *arg_templates]:
            if token == "{prompt}":
                argv.append(prompt)  # whole, unquoted argv element
            else:
                argv.append(_render(token, prompt_file_path))
        try:
            proc = subprocess.run(
                argv,
                shell=False,
                cwd=str(repo_root),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return 124, f"worker timeout after {timeout}s"
        finally:
            if prompt_file is not None:
                prompt_file.unlink(missing_ok=True)
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")

    return runner


def _worker_runner(config, ws, repo_root):
    worker = (config or {}).get("worker")
    if not isinstance(worker, dict) or not worker.get("executable") \
            or not isinstance(worker.get("args"), list):
        print("Refused: worker config (worker.executable + worker.args) is missing "
              "from profiles/execution-mode.local.yaml or execution-mode.yaml")
        return None
    timeout = int((config or {}).get("worker_timeout_seconds", 900))
    try:
        return make_worker_runner(worker, ws, repo_root, timeout=timeout)
    except ValueError as exc:
        print(f"Refused: invalid worker config: {exc}")
        return None


def _add_vnext_commands(sub):
    init_parser = sub.add_parser("vnext-init")
    init_parser.add_argument("--changes-root", required=True)
    init_parser.add_argument("--id", required=True)
    init_parser.add_argument("--class", dest="klass", required=True)
    init_parser.add_argument("--title", required=True)

    compile_parser = sub.add_parser("vnext-compile")
    compile_parser.add_argument("--workspace", required=True)
    compile_parser.add_argument("--repo-root", required=True)

    review_parser = sub.add_parser("vnext-review-plan")
    review_parser.add_argument("--workspace", required=True)
    review_parser.add_argument("--repo-root", required=True)

    reasoning_parser = sub.add_parser("vnext-validate-reasoning")
    reasoning_parser.add_argument("--workspace", required=True)
    reasoning_parser.add_argument("--repo-root", required=True)

    explore_parser = sub.add_parser("vnext-start-exploration")
    explore_parser.add_argument("--workspace", required=True)
    explore_parser.add_argument("--repo-root", required=True)

    transition_parser = sub.add_parser("vnext-transition")
    transition_parser.add_argument("--workspace", required=True)
    transition_parser.add_argument("--repo-root", required=True)
    transition_parser.add_argument("--expected", required=True)
    transition_parser.add_argument("--target", required=True)

    spec_parser = sub.add_parser("vnext-validate-spec")
    spec_parser.add_argument("--workspace", required=True)
    spec_parser.add_argument("--repo-root", required=True)

    run_parser = sub.add_parser("vnext-run")
    run_parser.add_argument("--workspace", required=True)
    run_parser.add_argument("--repo-root", required=True)

    status_parser = sub.add_parser("vnext-status")
    status_parser.add_argument("--workspace", required=True)
    status_parser.add_argument("--repo-root", required=True)

    resume_parser = sub.add_parser("vnext-resume")
    resume_parser.add_argument("--workspace", required=True)
    resume_parser.add_argument("--repo-root", required=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Maika vNext task orchestrator")
    sub = parser.add_subparsers(dest="command", required=True)
    _add_vnext_commands(sub)
    args = parser.parse_args(argv)

    repo_root = Path(getattr(args, "repo_root", "") or Path(args.changes_root).parents[1])
    framework_path = (
        Path(args.changes_root).parent
        if hasattr(args, "changes_root")
        else Path(args.workspace).parents[1]
    )
    config_path, config = _require_vnext(framework_path)
    if config_path is None:
        return 2

    import plan_compiler as pc
    import vnext_dispatch as vd
    import vnext_state as vs

    gates = _load_gate_check()
    if args.command not in {"vnext-init", "vnext-status", "vnext-resume"} and not _require_bootstrap(framework_path, gates, repo_root):
        return 1

    if args.command == "vnext-init":
        ws = vs.init_workspace(args.changes_root, args.id, args.klass, args.title)
        text = (ws / "CHANGE.yaml").read_text(encoding="utf-8")
        res = gates.validate_change_workspace(text)
        if not res.ok:
            print(f"Gate vnext-workspace failed: {res.reason}")
            return 1
        print(f"Workspace initialized at {ws}")
        return 0

    ws = Path(args.workspace)
    if args.command == "vnext-start-exploration":
        try:
            previous = vs.load_state(ws).get("state")
            state = vs.start_exploration(ws)
        except ValueError as exc:
            print(f"Refused: {exc}")
            return 1
        suffix = " (already started)" if previous == "EXPLORING" else ""
        print(f"Exploration state: {state['state']}{suffix}")
        return 0

    if args.command == "vnext-transition":
        state = vs.load_state(ws)
        if state.get("state") != args.expected:
            print(f"Refused: wrong state {state.get('state')} (expected {args.expected})")
            return 1
        try:
            vs.transition(ws, args.target)
        except ValueError as exc:
            print(f"Refused: {exc}")
            return 1
        print(f"{ws.name}: {args.expected} -> {args.target}")
        return 0

    if args.command == "vnext-compile":
        state = vs.load_state(ws)
        if state["state"] == "INTAKE":
            change = yaml.safe_load((ws / "CHANGE.yaml").read_text(encoding="utf-8")) or {}
            if change.get("class") not in {"trivial", "small"}:
                print("Refused: standard/architectural change requires reasoning/spec validation before planning")
                return 1
            vs.transition(ws, "PLANNING")
        elif state["state"] != "PLANNING":
            print(f"Refused: wrong state {state['state']}")
            return 1
        res = pc.compile_plan(ws, args.repo_root)
        if res.get("verdict") == "APPROVED":
            vs.transition(ws, "PLAN_REVIEW")
        print(f"Compile verdict: {res.get('verdict')}")
        return 0

    if args.command == "vnext-review-plan":
        state = vs.load_state(ws)
        if state["state"] != "PLAN_REVIEW":
            print(f"Refused: wrong state {state['state']}")
            return 1
        runner = _worker_runner(config, ws, args.repo_root)
        if runner is None:
            return 2
        verdict = vd.review_plan(ws, runner)
        print(f"Plan review verdict: {verdict}")
        return 0

    if args.command == "vnext-validate-reasoning":
        state = vs.load_state(ws)
        if state["state"] != "EXPLORING":
            print(f"Refused: wrong state {state['state']}")
            return 1
        gates = _load_gate_check()
        intent_res = gates.validate_intent(
            (ws / "INTENT.md").read_text(encoding="utf-8"),
            (ws / "CHANGE.yaml").read_text(encoding="utf-8"),
        )
        evidence_res = gates.validate_exploration_evidence(
            (ws / "exploration" / "GROUNDING.yaml").read_text(encoding="utf-8"),
            (ws / "exploration" / "EVIDENCE_MANIFEST.yaml").read_text(encoding="utf-8"),
            repo_root=args.repo_root,
        )
        registry_path = framework_path / "profiles" / "capability-registry.yaml"
        if not registry_path.exists():
            registry_path = Path(__file__).resolve().parents[2] / "profiles" / "capability-registry.yaml"
        registry = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
        capabilities = registry.get("capabilities") or {}
        coverable = {evidence for item in capabilities.values()
                     for evidence in (item.get("preferred_evidence") or [])}
        query_text = (ws / "exploration" / "QUERY_PLAN.yaml").read_text(encoding="utf-8")
        query_res = gates.validate_query_plan(
            query_text, valid_capabilities=set(capabilities), coverable_evidence=coverable
        )
        health_res = gates.validate_tool_health(
            (ws / "exploration" / "TOOL_HEALTH.yaml").read_text(encoding="utf-8")
        )
        conflict_res = gates.validate_conflicts(
            (ws / "exploration" / "CONFLICTS.yaml").read_text(encoding="utf-8")
        )
        coverage_res = gates.validate_coverage(
            (ws / "exploration" / "COVERAGE.yaml").read_text(encoding="utf-8")
        )
        change = yaml.safe_load((ws / "CHANGE.yaml").read_text(encoding="utf-8")) or {}
        memory_res = gates.Result(True)
        if change.get("class") in {"standard", "architectural"}:
            memory_path = ws / "exploration" / "MEMORY_RECALL.md"
            memory_res = gates.validate_memory_recall(
                memory_path.read_text(encoding="utf-8") if memory_path.exists() else ""
            )
        query_doc = yaml.safe_load(query_text) or {}
        needs_db = any(
            cap in {"database_schema_inspection", "database_dependency_analysis"}
            for q in query_doc.get("questions") or [] for cap in q.get("required_capabilities") or []
        )
        database_res = gates.Result(True)
        if needs_db:
            database_path = ws / "exploration" / "DATABASE_CONTEXT.yaml"
            database_res = gates.validate_database_context(
                database_path.read_text(encoding="utf-8") if database_path.exists() else ""
            )
        checks = [
            ("intent", intent_res), ("exploration-evidence", evidence_res),
            ("query-plan", query_res), ("tool-health", health_res),
            ("conflicts", conflict_res), ("coverage", coverage_res),
            ("memory-recall", memory_res), ("database-context", database_res),
        ]
        ok = all(result.ok for _, result in checks)
        (ws / "generated" / "EXPLORATION_VALIDATION.json").write_text(json.dumps({
            "verdict": "APPROVED" if ok else "REVISE",
            "checks": [{"id": name, "ok": result.ok, "reason": result.reason}
                       for name, result in checks],
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        if not ok:
            print("Reasoning validation verdict: REVISE")
            return 1
        vs.transition(ws, "RECONCILING")
        print("Reasoning validation verdict: APPROVED")
        return 0

    if args.command == "vnext-validate-spec":
        state = vs.load_state(ws)
        if state["state"] != "SPEC_REVIEW":
            print(f"Refused: wrong state {state['state']}")
            return 1
        gates = _load_gate_check()
        change = yaml.safe_load((ws / "CHANGE.yaml").read_text(encoding="utf-8")) or {}
        spec_res = gates.validate_vnext_spec(
            (ws / "SPEC.md").read_text(encoding="utf-8"),
            change_class=change.get("class", "standard"),
        )
        (ws / "generated" / "SPEC_VALIDATION.json").write_text(json.dumps({
            "verdict": "APPROVED" if spec_res.ok else "REVISE",
            "checks": [{"id": "spec", "ok": spec_res.ok, "reason": spec_res.reason}],
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        if not spec_res.ok:
            print("Spec validation verdict: REVISE")
            return 1
        vs.transition(ws, "PLANNING")
        print("Spec validation verdict: APPROVED")
        return 0

    if args.command == "vnext-run":
        lock = WorkspaceLock(ws / "generated" / "WORKSPACE.lock", task_id=ws.name)
        try:
            lock.acquire()
        except WorkspaceBusy as exc:
            print(f"Refused: {exc}")
            return 1
        try:
            state = vs.load_state(ws)
            change = yaml.safe_load((ws / "CHANGE.yaml").read_text(encoding="utf-8")) or {}
            if change.get("class") in {"trivial", "small"}:
                if state.get("state") != "INTAKE":
                    print(f"Refused: lightweight apply requires INTAKE (found {state.get('state')})")
                    return 1
                runner = _worker_runner(config, ws, args.repo_root)
                if runner is None:
                    return 2
                outcome = ar.execute_lightweight(ws, runner)
                metrics = outcome.get("runtime_metrics")
                if metrics:
                    vs.record_runtime_metrics(ws, metrics)
                if outcome["status"] == "escalate":
                    target = outcome.get("target_class", "standard")
                    vs.escalate_to_full(ws, target, outcome.get("triggers") or [])
                    print(f"Run outcome: escalated to {target}")
                    return 1
                if outcome["status"] != "done":
                    blocked_doc, exit_code = _blocked_metadata(outcome.get("reason"), resume_state="INTAKE")
                    vs.transition(ws, "BLOCKED", blocked=blocked_doc)
                    print(f"Run outcome: blocked ({blocked_doc['code']}): {outcome.get('reason')}")
                    return exit_code
                vs.transition(ws, "EXECUTING")
                vs.transition(ws, "VERIFYING")
                print("Run outcome: ready_for_verification")
                return EXIT_OK
            val = json.loads((ws / "generated" / "PLAN_VALIDATION.json").read_text(encoding="utf-8"))
            rev = (ws / "reviews" / "plan-review.md").read_text(encoding="utf-8") if (ws / "reviews" / "plan-review.md").exists() else ""
            if state["state"] == "PLAN_REVIEW":
                if val.get("verdict") == "APPROVED" and vd._verdict(ws, rev, "plan") == "APPROVED":
                    vs.transition(ws, "EXECUTING")
                else:
                    print("Refused: plan not approved")
                    return 1
            elif state["state"] != "EXECUTING":
                print(f"Refused: wrong state {state['state']}")
                return 1
            runner = _worker_runner(config, ws, args.repo_root)
            if runner is None:
                return 2
            out = vd.run_queue(ws, args.repo_root, runner)
            if out["status"] == "done":
                vs.transition(ws, "FINAL_REVIEW")
                print("Run outcome: done")
                return EXIT_OK
            blocked_doc, exit_code = _blocked_metadata(out.get("reason"), resume_state="EXECUTING")
            vs.transition(ws, "BLOCKED", blocked=blocked_doc)
            print(f"Run outcome: blocked ({blocked_doc['code']}): {out.get('reason')}")
            return exit_code
        finally:
            lock.release()

    if args.command == "vnext-status":
        state = vs.load_state(ws)
        print(f"State: {state['state']}")
        if state.get("state") == "BLOCKED":
            blocked = state.get("blocked") or {}
            print(f"Blocked: code={blocked.get('code')} reason={blocked.get('reason')} "
                  f"resume_state={blocked.get('resume_state')}")
            for action in blocked.get("recovery_actions") or []:
                print(f"  - {action}")
        queue = ws / "generated" / "TASK_QUEUE.json"
        if queue.exists():
            for task in json.loads(queue.read_text(encoding="utf-8")).get("tasks", []):
                print(f"- {task['id']}: {task['status']}")
        return EXIT_OK

    if args.command == "vnext-resume":
        state = vs.load_state(ws)
        if state.get("state") != "BLOCKED":
            print(f"Refused: resume requires BLOCKED (found {state.get('state')})")
            return EXIT_CONFIG
        blocked = state.get("blocked") or {}
        resume_state = blocked.get("resume_state")
        if not resume_state:
            print("Refused: BLOCKED state has no resume_state")
            return EXIT_CONFIG
        # Return the workspace to its resume_state. This does NOT bypass any gate:
        # the caller must re-run the phase, which re-checks the original blocker.
        vs.transition(ws, resume_state)
        print(f"Resumed to {resume_state}; re-run the phase (gates re-check the blocker: "
              f"{blocked.get('code')}).")
        return EXIT_OK

    print(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
