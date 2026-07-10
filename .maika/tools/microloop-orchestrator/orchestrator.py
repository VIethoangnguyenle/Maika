"""Maika vNext task orchestrator.

The runtime contract is JSON-only: workspaces live under
`<framework-root>/changes/<change-id>` and tasks progress through generated
JSON queues, YAML results, and markdown reviews.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import shlex
import subprocess
from pathlib import Path

import yaml


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


def make_worker_runner(worker_command, timeout=900):
    """Adapt a worker command template into a prompt runner."""
    def runner(prompt):
        command = worker_command.replace("{prompt}", shlex.quote(prompt))
        try:
            proc = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return 124, f"worker timeout after {timeout}s"
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")

    return runner


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

    spec_parser = sub.add_parser("vnext-validate-spec")
    spec_parser.add_argument("--workspace", required=True)
    spec_parser.add_argument("--repo-root", required=True)

    run_parser = sub.add_parser("vnext-run")
    run_parser.add_argument("--workspace", required=True)
    run_parser.add_argument("--repo-root", required=True)

    status_parser = sub.add_parser("vnext-status")
    status_parser.add_argument("--workspace", required=True)
    status_parser.add_argument("--repo-root", required=True)


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
    if args.command not in {"vnext-init", "vnext-status"} and not _require_bootstrap(framework_path, gates, repo_root):
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
        runner = make_worker_runner(config.get("worker_command", "echo stub"))
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
        state = vs.load_state(ws)
        val = json.loads((ws / "generated" / "PLAN_VALIDATION.json").read_text(encoding="utf-8"))
        rev = (ws / "reviews" / "plan-review.md").read_text(encoding="utf-8") if (ws / "reviews" / "plan-review.md").exists() else ""
        if state["state"] == "PLAN_REVIEW":
            if val.get("verdict") == "APPROVED" and "VERDICT: APPROVED" in rev:
                vs.transition(ws, "EXECUTING")
            else:
                print("Refused: plan not approved")
                return 1
        elif state["state"] != "EXECUTING":
            print(f"Refused: wrong state {state['state']}")
            return 1
        runner = make_worker_runner(config.get("worker_command", "echo stub"))
        out = vd.run_queue(ws, args.repo_root, runner)
        if out["status"] == "done":
            vs.transition(ws, "FINAL_REVIEW")
        elif out["status"] == "stale_plan":
            vs.transition(ws, "BLOCKED", blocked={"reason": "stale_plan"})
        print(f"Run outcome: {out['status']}")
        return 0

    if args.command == "vnext-status":
        state = vs.load_state(ws)
        print(f"State: {state['state']}")
        queue = ws / "generated" / "TASK_QUEUE.json"
        if queue.exists():
            for task in json.loads(queue.read_text(encoding="utf-8")).get("tasks", []):
                print(f"- {task['id']}: {task['status']}")
        return 0

    print(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
