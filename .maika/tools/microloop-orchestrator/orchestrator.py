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
import signal
import subprocess
import sys
from pathlib import Path

import yaml

import adaptive_runtime as ar
import loop_engineer as le
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


def _observe_friction(ws: Path, observation: dict) -> None:
    """Best-effort Loop Engineer hook (W6). Advisory only — a loop-machinery
    error must never block the safety-critical BLOCKED transition."""
    try:
        le.observe(ws, ws.name, observation)
    except Exception:
        pass


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


def _run_reasoning_validation(ws: Path, framework_path: Path, repo_root, gates):
    """Gate the exploration package; write EXPLORATION_VALIDATION.json.

    Returns (ok, reason). Shared by vnext-validate-reasoning and the grounding
    authoring dispatch — one validation path (R5).
    """
    ws = Path(ws)
    intent_res = gates.validate_intent(
        (ws / "INTENT.md").read_text(encoding="utf-8"),
        (ws / "CHANGE.yaml").read_text(encoding="utf-8"),
    )
    evidence_res = gates.validate_exploration_evidence(
        (ws / "exploration" / "GROUNDING.yaml").read_text(encoding="utf-8"),
        (ws / "exploration" / "EVIDENCE_MANIFEST.yaml").read_text(encoding="utf-8"),
        repo_root=repo_root,
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
    # M6 persistence routing: the recorded risk signal is the primary basis
    # (errata E5 — one classification surface); worker-authored query-plan DB
    # capabilities can only ADD the requirement, never remove it (B4).
    intent_text = (ws / "INTENT.md").read_text(encoding="utf-8") \
        if (ws / "INTENT.md").exists() else ""
    persistence = ar.derive_persistence_signal(
        intent_text, query_doc, (change.get("risk_signals") or {})
    )
    needs_db = (change.get("risk_signals") or {}).get("persistence") is True \
        or persistence["persistence"]
    registry_file = framework_path / "config" / "provider-registry.yaml"
    if not registry_file.exists():
        registry_file = (
            Path(__file__).resolve().parents[2] / "config" / "provider-registry.yaml"
        )
    provider_registry = (
        yaml.safe_load(registry_file.read_text(encoding="utf-8")) or {}
        if registry_file.exists() else {}
    )
    invocations_path = ws / "exploration" / "PROVIDER_INVOCATIONS.jsonl"
    invocations_text = (invocations_path.read_text(encoding="utf-8")
                        if invocations_path.exists() else "")
    database_request_res = gates.Result(True)
    database_res = gates.Result(True)
    if needs_db:
        request_path = ws / "exploration" / "DATABASE_REQUEST.yaml"
        request_text = (request_path.read_text(encoding="utf-8")
                        if request_path.exists() else "")
        database_request_res = gates.validate_database_request(request_text)
        database_path = ws / "exploration" / "DATABASE_CONTEXT.yaml"
        database_res = gates.validate_database_context(
            database_path.read_text(encoding="utf-8") if database_path.exists() else "",
            provider_registry=provider_registry,
            request_text=request_text,
            invocations_text=invocations_text,
        )
    provider_res = gates.Result(True)
    if invocations_path.exists():
        provider_res = gates.validate_provider_invocations(
            invocations_path.read_text(encoding="utf-8"),
            provider_registry=provider_registry,
        )
    # M5 router flip: trace request/evidence are mandatory for exploration —
    # explore only runs for standard/architectural changes (workflow-router).
    trace_request_path = ws / "exploration" / "TRACE_REQUEST.yaml"
    trace_evidence_path = ws / "exploration" / "TRACE_EVIDENCE.yaml"
    if not trace_request_path.exists():
        trace_request_res = gates.Result(
            False, "exploration/TRACE_REQUEST.yaml missing — run "
                   "vnext-compile-trace-request after QUERY_PLAN")
        trace_evidence_res = gates.Result(
            False, "exploration/TRACE_EVIDENCE.yaml cannot be validated without "
                   "TRACE_REQUEST.yaml")
    else:
        trace_request_res = gates.validate_trace_request(
            trace_request_path.read_text(encoding="utf-8"),
            valid_capabilities=set(capabilities),
            trigger_vocabulary=set(registry.get("triggers") or {}),
        )
        trace_evidence_res = gates.validate_trace_evidence(
            trace_evidence_path.read_text(encoding="utf-8")
            if trace_evidence_path.exists() else "",
            request_text=trace_request_path.read_text(encoding="utf-8"),
            invocations_text=(invocations_path.read_text(encoding="utf-8")
                              if invocations_path.exists() else ""),
            repo_root=repo_root,
        )
    checks = [
        ("intent", intent_res), ("exploration-evidence", evidence_res),
        ("query-plan", query_res), ("tool-health", health_res),
        ("conflicts", conflict_res), ("coverage", coverage_res),
        ("memory-recall", memory_res), ("database-request", database_request_res),
        ("database-context", database_res),
        ("provider-invocations", provider_res),
        ("trace-request", trace_request_res), ("trace-evidence", trace_evidence_res),
    ]
    ok = all(result.ok for _, result in checks)
    (ws / "generated" / "EXPLORATION_VALIDATION.json").write_text(json.dumps({
        "verdict": "APPROVED" if ok else "REVISE",
        "checks": [{"id": name, "ok": result.ok, "reason": result.reason}
                   for name, result in checks],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    failed = "; ".join(f"{name}: {result.reason}" for name, result in checks if not result.ok)
    return ok, failed


def _require_bootstrap(framework_path: Path, gates, repo_root: Path) -> bool:
    report = Path(framework_path) / "runtime" / "BOOTSTRAP_ENV_REPORT.yaml"
    if not report.exists():
        print("Refused: bootstrap-complete requires runtime/BOOTSTRAP_ENV_REPORT.yaml")
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


def make_worker_runner(worker, ws, repo_root, timeout=900):
    """Compatibility adapter around the canonical resolver/argv builder.

    The prompt is always materialized to a file and passed as one argv element.
    This function owns process lifecycle only; it does not own worker policy.
    """
    from cli.runtime.worker_resolver import (
        FRESH_PROCESS, WorkerProfile, build_worker_argv, validate_worker_profile,
    )
    args = tuple(
        token.replace("{prompt}", "{prompt_file}")
        for token in (worker.get("args") or [])
    )
    profile = validate_worker_profile(WorkerProfile(
        platform=worker.get("platform", "generic"),
        strategy=FRESH_PROCESS,
        executable=worker.get("executable"),
        args=args,
        timeout_seconds=timeout,
        dangerous_permissions=bool(worker.get("dangerous_permissions", False)),
        reason=worker.get("reason", "trusted orchestrator override"),
    ))
    ws = Path(ws)
    repo_root = Path(repo_root)

    def runner(prompt):
        prompts_dir = ws / "generated" / "prompts"
        prompts_dir.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:12]
        prompt_file = prompts_dir / f"dispatch-{os.getpid()}-{digest}.txt"
        prompt_file.write_text(prompt, encoding="utf-8")
        argv = build_worker_argv(profile, str(prompt_file), context={
            "repo_root": str(repo_root), "workspace": str(ws), "task_id": ws.name,
        })
        try:
            try:
                proc = subprocess.Popen(
                    argv, shell=False, cwd=str(repo_root), stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, text=True,
                    start_new_session=(os.name != "nt"),
                    creationflags=(subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0),
                )
            except OSError as exc:
                return 127, f"worker process error: {exc}"
            try:
                output, _ = proc.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                if os.name == "nt":  # pragma: no cover - Windows CI
                    proc.kill()
                else:
                    os.killpg(proc.pid, signal.SIGKILL)
                proc.communicate()
                return 124, f"worker timeout after {timeout}s"
        finally:
            prompt_file.unlink(missing_ok=True)
        return proc.returncode, output or ""

    return runner


def _worker_runner(config, ws, repo_root, platform_key=None, *, allow_primary_fallback=False):
    from cli.config import project as project_cfg
    from cli.runtime.worker_resolver import (
        FRESH_PROCESS, WorkerResolutionError, resolve_worker_profile,
    )

    config = config or {}
    worker = config.get("worker")
    primary = platform_key
    if primary is None and allow_primary_fallback:
        primary = project_cfg.load(Path(repo_root))["platforms"]["primary"]
    if primary is None and allow_primary_fallback and isinstance(worker, dict):
        primary = worker.get("platform", "generic")
    if primary is None:
        print("Refused: missing active or primary platform; pass an explicit platform")
        return None
    timeout = ar.load_runtime_policy(config).worker_timeout_seconds
    override = None
    if isinstance(worker, dict) and worker.get("executable"):
        override = {
            "platform": primary,
            "strategy": FRESH_PROCESS,
            "executable": worker["executable"],
            "args": [token.replace("{prompt}", "{prompt_file}")
                     for token in (worker.get("args") or [])],
            "timeout_seconds": timeout,
            "dangerous_permissions": False,
            "reason": "trusted execution-mode.local compatibility override",
        }
    try:
        profile = resolve_worker_profile(Path(repo_root), primary, override)
        if profile.strategy != FRESH_PROCESS:
            print(f"Refused: no verified worker for {primary} "
                  f"({profile.strategy}: {profile.reason})")
            print(f"  Remediation: run `maika platform verify {primary}` "
                  "to detect the CLI and run the worker smoke test.")
            return None
        return make_worker_runner({
            "platform": profile.platform,
            "executable": profile.executable,
            "args": list(profile.args),
            "dangerous_permissions": profile.dangerous_permissions,
            "reason": profile.reason,
        }, ws, repo_root, timeout=profile.timeout_seconds)
    except WorkerResolutionError as exc:
        print(f"Refused: invalid worker profile: {exc}")
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
    review_parser.add_argument("--platform")

    reasoning_parser = sub.add_parser("vnext-validate-reasoning")
    reasoning_parser.add_argument("--workspace", required=True)
    reasoning_parser.add_argument("--repo-root", required=True)

    explore_parser = sub.add_parser("vnext-start-exploration")
    explore_parser.add_argument("--workspace", required=True)
    explore_parser.add_argument("--repo-root", required=True)

    trace_request_parser = sub.add_parser("vnext-compile-trace-request")
    trace_request_parser.add_argument("--workspace", required=True)
    trace_request_parser.add_argument("--repo-root", required=True)

    transition_parser = sub.add_parser("vnext-transition")
    transition_parser.add_argument("--workspace", required=True)
    transition_parser.add_argument("--repo-root", required=True)
    transition_parser.add_argument("--expected", required=True)
    transition_parser.add_argument("--target", required=True)

    spec_parser = sub.add_parser("vnext-validate-spec")
    spec_parser.add_argument("--workspace", required=True)
    spec_parser.add_argument("--repo-root", required=True)

    dispatch_role_parser = sub.add_parser("vnext-dispatch-role")
    dispatch_role_parser.add_argument("--workspace", required=True)
    dispatch_role_parser.add_argument("--repo-root", required=True)
    dispatch_role_parser.add_argument("--platform")
    dispatch_role_parser.add_argument(
        "--role", required=True,
        choices=["grounding", "database", "reconciliation", "brainstorming",
                 "spec", "planning"],
    )

    run_parser = sub.add_parser("vnext-run")
    run_parser.add_argument("--workspace", required=True)
    run_parser.add_argument("--repo-root", required=True)
    run_parser.add_argument("--platform")

    status_parser = sub.add_parser("vnext-status")
    status_parser.add_argument("--workspace", required=True)
    status_parser.add_argument("--repo-root", required=True)

    resume_parser = sub.add_parser("vnext-resume")
    resume_parser.add_argument("--workspace", required=True)
    resume_parser.add_argument("--repo-root", required=True)

    fulfill_parser = sub.add_parser("vnext-fulfill-workflow")
    fulfill_parser.add_argument("--workspace", required=True)
    fulfill_parser.add_argument("--repo-root", required=True)


def _main_unlocked(argv=None):
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

    if args.command == "vnext-compile-trace-request":
        state = vs.load_state(ws)
        if state.get("state") != "EXPLORING":
            print(f"Refused: wrong state {state.get('state')} (expected EXPLORING)")
            return 1
        if not (ws / "exploration" / "QUERY_PLAN.yaml").exists():
            print("Refused: exploration/QUERY_PLAN.yaml required before trace request")
            return 1
        import trace_compiler as tc
        path = tc.write_trace_request(ws, framework_path)
        registry_path = framework_path / "profiles" / "capability-registry.yaml"
        if not registry_path.exists():
            registry_path = (Path(__file__).resolve().parents[2]
                             / "profiles" / "capability-registry.yaml")
        registry_doc = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
        res = gates.validate_trace_request(
            path.read_text(encoding="utf-8"),
            valid_capabilities=set(registry_doc.get("capabilities") or {}),
            trigger_vocabulary=set(registry_doc.get("triggers") or {}),
        )
        if not res.ok:
            print(f"Gate trace-request failed: {res.reason}")
            return 1
        print(f"Trace request compiled at {path}")
        # M6: derive + persist the umbrella persistence signal (errata E5 —
        # one classification surface) and compile the DATABASE_REQUEST
        # skeleton so the database-explorer route is mechanical (B4).
        change_path = ws / "CHANGE.yaml"
        change = yaml.safe_load(change_path.read_text(encoding="utf-8")) or {}
        intent_text = (ws / "INTENT.md").read_text(encoding="utf-8") \
            if (ws / "INTENT.md").exists() else ""
        query_doc = yaml.safe_load(
            (ws / "exploration" / "QUERY_PLAN.yaml").read_text(encoding="utf-8")
        ) or {}
        persistence = ar.derive_persistence_signal(
            intent_text, query_doc, change.get("risk_signals") or {}
        )
        signals = dict(change.get("risk_signals") or {})
        signals["persistence"] = persistence["persistence"]
        if persistence["basis"]:
            signals["persistence_basis"] = persistence["basis"]
        change["risk_signals"] = signals
        change_path.write_text(
            yaml.safe_dump(change, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        if persistence["persistence"]:
            request_path = tc.write_database_request(ws)
            print(f"Persistence detected ({', '.join(persistence['basis'])}) — "
                  f"database-explorer required; request skeleton at {request_path}")
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
        runner = _worker_runner(config, ws, args.repo_root, args.platform)
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
        ok, _reason = _run_reasoning_validation(ws, framework_path, args.repo_root, gates)
        if not ok:
            print("Reasoning validation verdict: REVISE")
            return 1
        vs.transition(ws, "RECONCILING")
        print("Reasoning validation verdict: APPROVED")
        return 0

    if args.command == "vnext-dispatch-role":
        role = args.role
        runner = _worker_runner(config, ws, args.repo_root, args.platform)
        if runner is None:
            return 2
        gates = _load_gate_check()
        vd_mod = vd

        def _trace_ok(path):
            block = vd_mod.markdown_trace_block(path.read_text(encoding="utf-8"))
            if block is None:
                return gates.Result(False, f"{path.name} missing Knowledge Trace YAML")
            return gates.validate_knowledge_trace(block)

        if role == "grounding":
            def validator(ws_path):
                # Worker chạy trong EXPLORING; validation + transition dùng chung
                # đường vnext-validate-reasoning.
                return _run_reasoning_validation(Path(ws_path), framework_path,
                                                 args.repo_root, gates)
        elif role == "database":
            def validator(ws_path):
                ws_path = Path(ws_path)
                request_path = ws_path / "exploration" / "DATABASE_REQUEST.yaml"
                request_text = (request_path.read_text(encoding="utf-8")
                                if request_path.exists() else "")
                request = gates.validate_database_request(request_text)
                if not request.ok:
                    return False, f"database-request: {request.reason}"
                registry_file = framework_path / "config" / "provider-registry.yaml"
                if not registry_file.exists():
                    registry_file = (Path(__file__).resolve().parents[2]
                                     / "config" / "provider-registry.yaml")
                invocations_file = ws_path / "exploration" / "PROVIDER_INVOCATIONS.jsonl"
                context = gates.validate_database_context(
                    (ws_path / "exploration" / "DATABASE_CONTEXT.yaml")
                    .read_text(encoding="utf-8"),
                    provider_registry=(
                        yaml.safe_load(registry_file.read_text(encoding="utf-8")) or {}
                        if registry_file.exists() else {}),
                    request_text=request_text,
                    invocations_text=(invocations_file.read_text(encoding="utf-8")
                                      if invocations_file.exists() else ""),
                )
                return context.ok, context.reason
        elif role == "reconciliation":
            def validator(ws_path):
                ws_path = Path(ws_path)
                conflict = gates.validate_conflicts(
                    (ws_path / "exploration" / "CONFLICTS.yaml").read_text(encoding="utf-8"))
                if not conflict.ok:
                    return False, f"conflicts: {conflict.reason}"
                trace = _trace_ok(ws_path / "RECONCILIATION.md")
                return trace.ok, trace.reason
        elif role == "brainstorming":
            def validator(ws_path):
                trace = _trace_ok(Path(ws_path) / "RECONCILIATION.md")
                return trace.ok, trace.reason
        elif role == "spec":
            def validator(ws_path):
                ws_path = Path(ws_path)
                change = yaml.safe_load((ws_path / "CHANGE.yaml").read_text(encoding="utf-8")) or {}
                res = gates.validate_vnext_spec(
                    (ws_path / "SPEC.md").read_text(encoding="utf-8"),
                    change_class=change.get("class", "standard"),
                )
                return res.ok, res.reason
        elif role == "planning":
            def validator(ws_path):
                ok = vd_mod.run_planning_dispatch(Path(ws_path), args.repo_root)
                return ok, "" if ok else "vnext-plan gate failed (see CONTEXT_REQUEST.yaml)"
        else:
            print(f"Refused: unknown dispatch role {role}")
            return 2
        result = vd.run_authoring_dispatch(ws, role, runner, vs, validator)
        if not result.get("ok"):
            reason = result.get("reason")
            if reason in {"EXTERNAL_WORKFLOW_REQUEST", "DB_REPROBE_REQUEST"}:
                code = ("external_workflow" if reason == "EXTERNAL_WORKFLOW_REQUEST"
                        else "db_reprobe")
                blocked = vd.block_on_refresh_request(
                    ws, role, result.get("request") or {}, vs, code
                )
                print(f"Blocked ({code}): {blocked['remediation']}")
                print(f"After fulfillment, resume with: {blocked['resume_action']}")
                return EXIT_HUMAN
            print(f"Refused: {role} dispatch failed: {reason}")
            return 1
        print(f"{role} dispatch complete: state={result.get('state')}")
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
        runtime_policy = ar.RuntimePolicy.from_config(config)
        lock = WorkspaceLock(ws / "generated" / "WORKSPACE.lock", task_id=ws.name)
        try:
            lock.acquire()
        except WorkspaceBusy as exc:
            print(f"Refused: {exc}")
            return 1
        try:
            state = vs.load_state(ws)
            change = yaml.safe_load((ws / "CHANGE.yaml").read_text(encoding="utf-8")) or {}
            if change.get("class") in {"trivial", "small"} and (ws / "TASK.yaml").exists():
                task = yaml.safe_load((ws / "TASK.yaml").read_text(encoding="utf-8")) or {}
                try:
                    signals = ar.derive_risk_signals(
                        task, Path(args.repo_root), rules=(config or {}).get("risk_rules")
                    )
                except ValueError as exc:
                    blocked_doc, exit_code = _blocked_metadata(str(exc), resume_state="INTAKE")
                    vs.transition(ws, "BLOCKED", blocked=blocked_doc)
                    print(f"Run outcome: blocked ({blocked_doc['code']}): {exc}")
                    return exit_code
                requested = change.get("requested_class") or change.get("class")
                classified = ar.classify_risk(signals, current_class=requested)
                target = classified["classification"]["proposed_class"]
                evidence = classified["classification"].get("evidence") or []
                if target in {"standard", "architectural"}:
                    vs.escalate_to_full(ws, target, evidence)
                    print(f"Run outcome: escalated to {target}")
                    return EXIT_BLOCKED
                change = vs.record_effective_class(ws, target, signals, evidence)
                task["class"] = target
                task["risk_signals"] = signals
                task["classification"] = classified["classification"]
                vs._dump_yaml(task, ws / "TASK.yaml")
                if target == "small" and not (ws / "EVIDENCE.yaml").exists():
                    vs._dump_yaml({
                        "version": 1, "change_id": change.get("change_id"), "items": [],
                        "evidence_metrics": {"retrieved": 0, "reused": 0, "revalidated": 0, "newly_created": 0},
                    }, ws / "EVIDENCE.yaml")
                    vs._dump_yaml({"version": 1, "change_id": change.get("change_id"), "status": "pending",
                                   "changes": []}, ws / "RESULT.yaml")
            if change.get("class") in {"trivial", "small"}:
                if state.get("state") != "INTAKE":
                    print(f"Refused: lightweight apply requires INTAKE (found {state.get('state')})")
                    return 1
                runner = _worker_runner(config, ws, args.repo_root, args.platform)
                if runner is None:
                    return 2
                try:
                    contract = ar.build_lightweight_execution_contract(
                        ws, Path(args.repo_root), task, state, ar.RuntimeOwner(
                            lease_seconds=runtime_policy.worker_timeout_seconds + 60
                        ),
                    )
                except (OSError, RuntimeError, ValueError) as exc:
                    blocked_doc, exit_code = _blocked_metadata(str(exc), resume_state="INTAKE")
                    vs.transition(ws, "BLOCKED", blocked=blocked_doc)
                    print(f"Run outcome: blocked ({blocked_doc['code']}): {exc}")
                    return exit_code
                # The write gate only accepts the contract while canonical state
                # is EXECUTING, so dispatch can never occur from INTAKE.
                vs.transition(ws, "EXECUTING")
                outcome = ar.execute_lightweight(ws, runner, policy=runtime_policy)
                metrics = outcome.get("runtime_metrics")
                if metrics:
                    vs.record_runtime_metrics(ws, metrics)
                if outcome["status"] == "escalate":
                    target = outcome.get("target_class", "standard")
                    ar.invalidate_lightweight_execution_contract(ws, "escalated")
                    blocked_doc, exit_code = _blocked_metadata(
                        f"runtime risk requires escalation to {target}", resume_state="INTAKE"
                    )
                    vs.transition(ws, "BLOCKED", blocked=blocked_doc)
                    print(f"Run outcome: blocked pending escalation to {target}")
                    return exit_code
                if outcome["status"] != "done":
                    ar.invalidate_lightweight_execution_contract(ws, "blocked")
                    blocked_doc, exit_code = _blocked_metadata(outcome.get("reason"), resume_state="INTAKE")
                    vs.transition(ws, "BLOCKED", blocked=blocked_doc)
                    print(f"Run outcome: blocked ({blocked_doc['code']}): {outcome.get('reason')}")
                    return exit_code
                observed = ar.inspect_lightweight_changes(Path(args.repo_root), contract)
                if observed["outside_scope"]:
                    reason = "actual worktree changes outside lightweight scope: " + ", ".join(observed["outside_scope"])
                    ar.invalidate_lightweight_execution_contract(ws, "invalid")
                    _observe_friction(ws, {"trigger": "scope_escape",
                                           "outside_scope": observed["outside_scope"],
                                           "evidence_refs": observed["outside_scope"]})
                    blocked_doc, exit_code = _blocked_metadata(reason, resume_state="INTAKE")
                    vs.transition(ws, "BLOCKED", blocked=blocked_doc)
                    print(f"Run outcome: blocked ({blocked_doc['code']}): {reason}")
                    return exit_code
                ar.invalidate_lightweight_execution_contract(ws, "completed")
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
            runner = _worker_runner(config, ws, args.repo_root, args.platform)
            if runner is None:
                return 2
            out = vd.run_queue(ws, args.repo_root, runner,
                               max_retries=runtime_policy.max_retries,
                               runtime_policy=runtime_policy)
            if out["status"] == "done":
                vs.transition(ws, "FINAL_REVIEW")
                print("Run outcome: done")
                return EXIT_OK
            reason = out.get("reason")
            if reason and "retry budget" in reason.lower():
                _observe_friction(ws, {"trigger": "repeated_failure", "retries_exhausted": True,
                                       "evidence_refs": [reason]})
            blocked_doc, exit_code = _blocked_metadata(reason, resume_state="EXECUTING")
            vs.transition(ws, "BLOCKED", blocked=blocked_doc)
            print(f"Run outcome: blocked ({blocked_doc['code']}): {reason}")
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

    if args.command == "vnext-fulfill-workflow":
        ok, detail = vd.fulfill_blocked_request(ws, vs)
        if not ok:
            print(f"Refused: {detail}")
            return EXIT_BLOCKED
        resolution = detail["resolution"]
        print(f"Refresh fulfilled with new evidence {resolution['evidence_hash']}; "
              f"result at {detail['result_file']}")
        print(f"Resumed; redispatch the original role: {detail['resume_action']}")
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


def main(argv=None):
    raw = list(argv) if argv is not None else sys.argv[1:]
    command = raw[0] if raw else ""
    lifecycle_mutations = {
        "vnext-start-exploration", "vnext-transition", "vnext-compile",
        "vnext-review-plan", "vnext-validate-reasoning", "vnext-validate-spec",
        "vnext-dispatch-role", "vnext-resume", "vnext-fulfill-workflow",
        "vnext-compile-trace-request",
    }
    if command not in lifecycle_mutations:
        return _main_unlocked(raw)
    try:
        ws = Path(raw[raw.index("--workspace") + 1])
    except (ValueError, IndexError):
        return _main_unlocked(raw)
    lock = WorkspaceLock(ws / "generated" / "WORKSPACE.lock", task_id=ws.name)
    try:
        lock.acquire()
    except WorkspaceBusy as exc:
        print(f"Refused: {exc}")
        return EXIT_BLOCKED
    try:
        return _main_unlocked(raw)
    finally:
        lock.release()


if __name__ == "__main__":
    raise SystemExit(main())
