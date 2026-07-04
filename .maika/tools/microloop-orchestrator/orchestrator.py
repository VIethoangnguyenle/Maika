"""Micro-loop orchestrator: topo-sort, slice assembly, loop protocol.

All functions are pure logic. run_loop() takes dispatch_fn and gate_fn via
dependency injection so the whole protocol is unit-testable with stubs —
no Java, no real subagent.
"""
import importlib.util
import argparse
import json
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import yaml


VALID_RUNTIME_STATUS = {"pending", "in_progress", "done", "blocked", "stale"}


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _microloop_dir(active_dir):
    path = Path(active_dir) / "microloop"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _queue_path(active_dir):
    return _microloop_dir(active_dir) / "TASK_QUEUE.md"


def _activity_log_path(active_dir):
    return _microloop_dir(active_dir) / "ACTIVITY_LOG.jsonl"


def _parent_brain_path(active_dir):
    return Path(active_dir) / "PARENT_BRAIN.md"


def _load_gate_check():
    mod = Path(__file__).resolve().parents[1] / "gate-check" / "gates.py"
    spec = importlib.util.spec_from_file_location("gates", mod)
    gates = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gates)
    return gates


def _project_rel(framework_root, *parts):
    return str(Path(framework_root, "knowledge", "active", *parts))


def append_activity_event(active_dir, event, **fields):
    """Append one dashboard activity event to microloop/ACTIVITY_LOG.jsonl."""
    record = {"ts": fields.pop("ts", _now_iso()), "event": event}
    record.update({k: v for k, v in fields.items() if v is not None})
    path = _activity_log_path(active_dir)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return record


def record_parent_event(active_dir, event, phase=None, summary=None, **fields):
    """Append a parent-agent lifecycle event for dashboard timelines."""
    return append_activity_event(
        active_dir,
        event,
        actor="parent",
        phase=phase,
        summary=summary,
        **fields,
    )


def write_parent_brain(active_dir, body, source="ide-brain-mirror", append=False, **fields):
    """Write a dashboard-visible mirror of the parent IDE brain/conversation."""
    path = _parent_brain_path(active_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    updated_at = _now_iso()
    body = str(body).rstrip()
    if append and path.exists():
        current = path.read_text(encoding="utf-8").rstrip()
        content = f"{current}\n\n{body}\n" if current else f"{body}\n"
    else:
        content = (
            "# PARENT_BRAIN\n\n"
            f"source: {source}\n"
            f"updated_at: {updated_at}\n\n"
            f"{body}\n"
        )
    path.write_text(content, encoding="utf-8")
    summary = fields.pop("summary", None) or _first_nonempty_line(body) or "Parent brain updated."
    record_parent_event(
        active_dir,
        "parent_brain_updated",
        summary=summary,
        source=source,
        path=str(path),
        **fields,
    )
    return path


def _first_nonempty_line(text):
    for line in str(text).splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:160]
    return None


def initialize_runtime_queue(active_dir, ticket_id, spec_path, tasks,
                             execution_mode="subagent", *, framework_root):
    """Create dashboard-visible TASK_QUEUE.md before dispatching subagents."""
    normalized = []
    for task in topo_sort(tasks):
        task_id = task["id"]
        normalized.append({
            "id": task_id,
            "desc": task.get("desc", task_id),
            "depends_on": task.get("depends_on", []),
            "status": task.get("status", "pending"),
            "retries": task.get("retries", 0),
            "handoff_path": task.get(
                "handoff_path",
                _project_rel(framework_root, f"TASK_HANDOFF.{task_id}.md"),
            ),
            "result_path": task.get(
                "result_path",
                _project_rel(framework_root, "microloop", f"TASK_RESULT.{task_id}.md"),
            ),
        })
    queue = {
        "ticket_id": ticket_id,
        "spec_path": spec_path,
        "execution_mode": execution_mode,
        "tasks": normalized,
    }
    path = _queue_path(active_dir)
    path.write_text(yaml.safe_dump(queue, sort_keys=False, allow_unicode=True), encoding="utf-8")
    append_activity_event(
        active_dir,
        "task_queue_created",
        actor="parent",
        ticket_id=ticket_id,
        tasks_total=len(normalized),
    )
    return queue


def load_runtime_queue(active_dir):
    path = _queue_path(active_dir)
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def save_runtime_queue(active_dir, queue):
    path = _queue_path(active_dir)
    path.write_text(yaml.safe_dump(queue, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return queue


def write_task_handoff(active_dir, task_id, prompt, label=None):
    """Write TASK_HANDOFF.<task_id>.md and emit subagent_spawned."""
    result = _load_gate_check().validate_implementation_context(prompt)
    if not result.ok:
        raise ValueError(f"invalid implementation context for TASK_HANDOFF.{task_id}: {result.reason}")
    path = Path(active_dir) / f"TASK_HANDOFF.{task_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(prompt, encoding="utf-8")
    append_activity_event(
        active_dir,
        "subagent_spawned",
        actor="subagent",
        task_id=task_id,
        label=label,
        path=str(path),
    )
    return path


def update_task_status(active_dir, task_id, status, event=None):
    """Update one task status in TASK_QUEUE.md and append a lifecycle event."""
    if status not in VALID_RUNTIME_STATUS:
        raise ValueError(f"bad runtime task status: {status}")
    queue = load_runtime_queue(active_dir)
    tasks = queue.get("tasks", [])
    task = next((t for t in tasks if t.get("id") == task_id), None)
    if task is None:
        raise ValueError(f"task {task_id} not in queue")
    task["status"] = status
    task["updated_at"] = _now_iso()
    if status == "in_progress" and not task.get("started_at"):
        task["started_at"] = task["updated_at"]
    if status in {"done", "blocked"}:
        task["finished_at"] = task["updated_at"]
    save_runtime_queue(active_dir, queue)
    append_activity_event(
        active_dir,
        event or f"task_{status}",
        actor="subagent",
        ticket_id=queue.get("ticket_id"),
        task_id=task_id,
        status=status,
    )
    return queue


def write_task_result(active_dir, task_id, body, status="done"):
    """Write TASK_RESULT.<task_id>.md, update queue status, and emit result events."""
    path = _microloop_dir(active_dir) / f"TASK_RESULT.{task_id}.md"
    path.write_text(body, encoding="utf-8")
    append_activity_event(
        active_dir,
        "result_written",
        actor="subagent",
        task_id=task_id,
        path=str(path),
    )
    update_task_status(
        active_dir,
        task_id,
        status,
        event="subagent_done" if status == "done" else "subagent_blocked",
    )
    return path


def topo_sort(tasks):
    """Kahn's algorithm. Returns tasks ordered so deps come first. Raises on cycle."""
    by_id = {t["id"]: t for t in tasks}
    for t in tasks:
        for dep_id in t.get("depends_on", []):
            if dep_id not in by_id:
                raise ValueError(f"task {t['id']} depends on non-existent task {dep_id}")
    indeg = {t["id"]: 0 for t in tasks}
    for t in tasks:
        for _ in t.get("depends_on", []):
            indeg[t["id"]] += 1
    ready = sorted([tid for tid, d in indeg.items() if d == 0])
    ordered = []
    while ready:
        tid = ready.pop(0)
        ordered.append(by_id[tid])
        for t in tasks:
            if tid in t.get("depends_on", []):
                indeg[t["id"]] -= 1
                if indeg[t["id"]] == 0:
                    ready.append(t["id"])
        ready.sort()
    if len(ordered) != len(tasks):
        raise ValueError("dependency cycle detected in tasks")
    return ordered


def slice_dna(dna, principle_ids):
    """Extract only requested principle entries + always-global thresholds (anti-bloat)."""
    wanted = set(principle_ids)
    return {
        "complexity_thresholds": dna.get("complexity_thresholds", {}),
        "hard_principles": [p for p in dna.get("hard_principles", []) if p["id"] in wanted],
        "style_preferences": [p for p in dna.get("style_preferences", []) if p["id"] in wanted],
    }


def build_handoff(task, dna, spec_slice, snapshot_slice, written_files, boundary, feedback=None):
    """Assemble TASK_HANDOFF dict (spec §5.2). dna_slice is anti-bloat (only task principles)."""
    return {
        "task": {"id": task["id"], "desc": task["desc"]},
        "dna_slice": slice_dna(dna, task.get("principle_ids", [])),
        "spec_slice": spec_slice,
        "snapshot_slice": snapshot_slice,
        "written_files": written_files,
        "boundary": boundary,
        "feedback": feedback,
    }


def next_task(queue):
    """Resume in_progress first; else first pending whose deps are all done."""
    tasks = queue["tasks"]
    done = {t["id"] for t in tasks if t["status"] == "done"}
    for t in tasks:
        if t["status"] == "in_progress":
            return t
    for t in tasks:
        if t["status"] == "pending" and all(d in done for d in t.get("depends_on", [])):
            return t
    return None


def apply_result(queue, task_id, gate_result, max_retries=2):
    """Mutate queue per gate outcome. PASS->done; FAIL->retry; FAIL over budget->blocked.

    gate_result: str ('PASS'/'FAIL') for backward compat, or dict
    {'status': 'PASS'|'FAIL', 'violations': [...]} from enriched gate (SP1c).
    Stores gate_history per-attempt for outcome loop."""
    t = next((t for t in queue["tasks"] if t["id"] == task_id), None)
    if t is None:
        raise ValueError(f"task {task_id} not in queue")

    # Backward-compatible: accept string or dict
    if isinstance(gate_result, str):
        gate_status = gate_result
        violations = []
    else:
        gate_status = gate_result["status"]
        violations = gate_result.get("violations", [])

    # Record gate history per-attempt (SP1c outcome loop)
    t.setdefault("gate_history", []).append({
        "attempt": t.get("retries", 0),
        "status": gate_status,
        "violations": violations,
    })

    if gate_status == "PASS":
        t["status"] = "done"
        return queue
    # FAIL
    if t["retries"] >= max_retries:
        t["status"] = "blocked"
    else:
        t["retries"] += 1
        t["status"] = "in_progress"
    return queue


def make_gate_fn(runner, parse_fn=None):
    """Adapt a (changed_files)->(exit_code, output) runner into enriched gate_fn.

    Returns dict {'status': 'PASS'|'FAIL', 'violations': [...]}.
    parse_fn: optional (raw_output) -> list[{rule, file, line, message}].
    If None, violations is always []. Injected so backend-specific parsing
    (Checkstyle, ESLint, Ruff) is decoupled from the protocol."""
    def gate_fn(changed_files):
        exit_code, output = runner(changed_files)
        status = "PASS" if exit_code == 0 else "FAIL"
        violations = parse_fn(output) if parse_fn else []
        return {"status": status, "violations": violations}
    return gate_fn


def make_worker_runner(worker_command, timeout=900):
    """Tạo runner spawn MỘT worker CLI dùng-một-lần (fresh-session tier).

    worker_command: template có placeholder {prompt} (vd 'agy -p {prompt}');
    prompt được shell-quote trước khi thay. Trả về (exit_code, output).
    Timeout → exit_code 124 (convention của timeout(1))."""
    def runner(prompt):
        command = worker_command.replace("{prompt}", shlex.quote(prompt))
        try:
            proc = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return 124, f"worker timeout sau {timeout}s"
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")

    return runner


def dispatch_worker(prompt, runner, *, retries=2, active_dir=None, task_id=None):
    """Chạy một worker context mới cho prompt; retry khi fail; log activity event.

    runner: (prompt) -> (exit_code, output) — inject được (make_worker_runner cho
    subprocess thật, stub cho unit test; cùng pattern với make_gate_fn).
    Khi truyền active_dir: tự emit subagent_started (mỗi attempt) và subagent_blocked
    (fail cuối). KHÔNG emit subagent_done — write_task_result của worker đã emit,
    tránh double-emission."""
    attempt = 0
    while True:
        if active_dir is not None:
            append_activity_event(
                active_dir, "subagent_started",
                actor="subagent", task_id=task_id, attempt=attempt,
            )
        exit_code, output = runner(prompt)
        if exit_code == 0:
            return {"status": "done", "attempts": attempt + 1, "output": output}
        attempt += 1
        if attempt > retries:
            if active_dir is not None:
                append_activity_event(
                    active_dir, "subagent_blocked",
                    actor="subagent", task_id=task_id, reason=str(output)[:500],
                )
            return {"status": "blocked", "attempts": attempt, "output": output}


def run_loop(queue, dispatch_fn, gate_fn, max_retries=2):
    """Drive the micro-loop. dispatch_fn(task)->changed_files;
    gate_fn(changed_files)->dict{'status','violations'} or str 'PASS'|'FAIL'.

    Pure protocol: no knowledge of tiers or the real gate — both injected. This is
    what makes the loop platform-agnostic and unit-testable (portability gate).
    gate_history is accumulated in each task for SP1c outcome loop.
    """
    while True:
        t = next_task(queue)
        if t is None:
            return queue
        t["status"] = "in_progress"  # resumable marker before dispatch
        changed_files = dispatch_fn(t)
        gate_result = gate_fn(changed_files)
        apply_result(queue, t["id"], gate_result, max_retries=max_retries)
        if t["status"] == "blocked":
            return queue


def topo_sort_nodes(nodes):
    """Topo-sort Contract DAG nodes by depends_on, preserving deterministic id order."""
    by_id = {node["id"]: node for node in nodes}
    for node in nodes:
        for dep_id in node.get("depends_on", []):
            if dep_id not in by_id:
                raise ValueError(f"node {node['id']} depends on non-existent node {dep_id}")
    indeg = {node["id"]: len(node.get("depends_on", [])) for node in nodes}
    ready = sorted([node_id for node_id, degree in indeg.items() if degree == 0])
    ordered = []
    while ready:
        node_id = ready.pop(0)
        ordered.append(by_id[node_id])
        for node in nodes:
            if node_id in node.get("depends_on", []):
                indeg[node["id"]] -= 1
                if indeg[node["id"]] == 0:
                    ready.append(node["id"])
        ready.sort()
    if len(ordered) != len(nodes):
        raise ValueError("dependency cycle detected in contract dag")
    return ordered


def find_write_conflicts(nodes):
    """Return paths written by more than one node: {path: [node_id, ...]}."""
    writers = {}
    for node in nodes:
        for path in node.get("writes", []):
            writers.setdefault(path, []).append(node["id"])
    return {path: ids for path, ids in writers.items() if len(ids) > 1}


def plan_parallel_batches(nodes):
    """Plan deterministic batches where no nodes in the same batch write the same file.

    Dependencies pointing outside the provided node set are treated as already
    satisfied: the Implementation Lane only receives nodes whose dependencies are
    already done, and those done nodes are not part of the batch-candidate set.
    """
    ids = {node["id"] for node in nodes}
    by_id = {node["id"]: node for node in nodes}
    scoped = [dict(node, depends_on=[dep for dep in node.get("depends_on", []) if dep in ids])
              for node in nodes]
    pending = [by_id[node["id"]] for node in topo_sort_nodes(scoped)]
    batches = []
    while pending:
        batch = []
        used_writes = set()
        remaining = []
        for node in pending:
            writes = set(node.get("writes", []))
            if used_writes.isdisjoint(writes):
                batch.append(node)
                used_writes.update(writes)
            else:
                remaining.append(node)
        batches.append(batch)
        pending = remaining
    return batches


def invalidate_contract_dependents(dag, contract_node_id, new_version):
    """Mark downstream nodes stale when their contract_ref version is older than new_version."""
    for node in dag.get("nodes", []):
        ref = node.get("contract_ref")
        if ref and ref.get("node_id") == contract_node_id and ref.get("version") != new_version:
            node["status"] = "stale"
    return dag


def check_knowledge_gate(knowledge_pack, complexity="standard", user_override=False):
    """Return PASS/BLOCK for Phase 3 knowledge readiness."""
    issues = []
    graph_status = knowledge_pack.get("ua_kg", {}).get("graph_status")
    if complexity == "complex" and graph_status != "available":
        issues.append("KG graph unavailable for complex task")
    database = knowledge_pack.get("database", {})
    if database.get("required") and not database.get("evidence"):
        issues.append("DB evidence missing for data-touching task")
    if issues and not user_override:
        return {"status": "BLOCK", "issues": issues}
    if issues:
        return {"status": "WARN", "issues": issues}
    return {"status": "PASS", "issues": []}


def build_contract_handoff(task, knowledge_pack, spec_slice, snapshot_slice, contract_snapshot,
                           written_files, boundary, feedback=None):
    """Build role-aware TASK_HANDOFF content for Hybrid Contract DAG nodes."""
    return {
        "task": {"id": task["id"], "desc": task["desc"]},
        "dna_slice": knowledge_pack.get("dna", {}),
        "convention_slice": knowledge_pack.get("conventions", {}),
        "spec_slice": spec_slice,
        "snapshot_slice": snapshot_slice,
        "contract_snapshot": contract_snapshot,
        "written_files": written_files,
        "boundary": boundary,
        "feedback": feedback,
    }


def load_execution_config(active_dir):
    """Đọc profiles/execution-mode.yaml (bản ĐÃ render) của scaffold chứa active_dir.

    active_dir = <framework_root>/knowledge/active → config ở <framework_root>/profiles/.
    Trả None nếu file không tồn tại (precondition sẽ báo)."""
    path = Path(active_dir).resolve().parents[1] / "profiles" / "execution-mode.yaml"
    if not path.exists():
        return None
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def check_apply_preconditions(active_dir, config):
    """Preconditions cơ học của driver (thay rule text — spec §4.2).

    Trả list lý do từ chối (rỗng = chạy được); mỗi lý do một dòng chỉ thẳng cách sửa."""
    reasons = []
    active = Path(active_dir)
    if config is None:
        reasons.append(
            "Thiếu profiles/execution-mode.yaml — chạy `maika update` để render lại scaffold."
        )
        return reasons
    if config.get("execution_mode") != "fresh-session":
        reasons.append(
            f"Driver chỉ hỗ trợ execution_mode fresh-session (hiện tại: "
            f"{config.get('execution_mode')!r}) — tier subagent/inline-reload do parent "
            "agent vận hành theo workflows/task.md."
        )
    if not str(config.get("worker_command") or "").strip():
        reasons.append(
            "worker_command rỗng trong execution-mode.yaml — khai báo lệnh worker cho platform này."
        )
    if not (active / "KNOWLEDGE_CHECKPOINT.md").exists():
        reasons.append("Thiếu KNOWLEDGE_CHECKPOINT.md — hoàn thành Pha 1/2 trước khi apply.")
    if not _queue_path(active).exists():
        reasons.append(
            "Thiếu microloop/TASK_QUEUE.md — parent phải chạy initialize_runtime_queue trước."
        )
        return reasons
    tasks = (load_runtime_queue(active).get("tasks") or [])
    if not tasks:
        reasons.append("TASK_QUEUE.md không có task nào.")
        return reasons
    project_root = active.resolve().parents[2]
    for t in tasks:
        if t.get("status") == "done":
            continue
        handoff = t.get("handoff_path")
        if not handoff or not (project_root / handoff).exists():
            reasons.append(
                f"Node {t.get('id')}: thiếu TASK_HANDOFF ({handoff}) — parent phải ghi handoff trước."
            )
    return reasons


def apply_command(active_dir, runner=None, config=None):
    """Driver Pha 3 (fresh-session): vòng lặp node chạy bằng code — LLM chỉ còn trong worker.

    Disk (TASK_QUEUE.md) là source of truth mỗi vòng: crash-safe, resume tự nhiên
    (next_task resume-first, skip node done). runner inject được cho test; mặc định
    make_worker_runner từ execution-mode.yaml. Gate v1: worker exit 0 + TASK_RESULT
    tồn tại (executor procedure tự chạy gate dự án; write-gate vẫn chặn cơ học trong
    worker process). Trả dict {"status","done","task_id","reason"}."""
    active = Path(active_dir)
    if config is None:
        config = load_execution_config(active)
    reasons = check_apply_preconditions(active, config)
    if reasons:
        return {"status": "refused", "done": 0, "task_id": None,
                "reason": "\n".join(reasons)}
    from tiers import get_dispatch  # lazy: giữ loop protocol không biết tier (docstring module)
    dispatch = get_dispatch("fresh-session")
    if runner is None:
        runner = make_worker_runner(
            config["worker_command"], config.get("worker_timeout_seconds", 900)
        )
    max_retries = config.get("max_retries", 2)
    project_root = active.resolve().parents[2]
    done_count = 0
    while True:
        queue = load_runtime_queue(active)
        task = next_task(queue)
        if task is None:
            blocked = [t["id"] for t in queue["tasks"] if t["status"] == "blocked"]
            if blocked:
                return {"status": "blocked", "done": done_count, "task_id": blocked[0],
                        "reason": "node blocked từ lần chạy trước — sửa nguyên nhân rồi đặt lại pending"}
            return {"status": "done", "done": done_count, "task_id": None, "reason": None}
        task_id = task["id"]
        if task["status"] != "in_progress":
            update_task_status(active, task_id, "in_progress")
        prompt = dispatch(task["handoff_path"], task["result_path"])
        outcome = dispatch_worker(
            prompt, runner, retries=max_retries, active_dir=active, task_id=task_id,
        )
        if outcome["status"] == "done" and not (project_root / task["result_path"]).exists():
            outcome = {"status": "blocked", "attempts": outcome["attempts"],
                       "output": f"worker exit 0 nhưng thiếu {task['result_path']}"}
        current = next(
            t for t in load_runtime_queue(active)["tasks"] if t["id"] == task_id
        )
        if outcome["status"] == "done":
            if current["status"] != "done":  # worker dùng write_task_result thì đã done + emit
                update_task_status(active, task_id, "done", event="subagent_done")
            done_count += 1
        else:
            if current["status"] != "blocked":
                update_task_status(active, task_id, "blocked")
            return {"status": "blocked", "done": done_count, "task_id": task_id,
                    "reason": str(outcome["output"])[:500]}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Micro-loop orchestrator CLI (Pha 3 driver)")
    sub = parser.add_subparsers(dest="command", required=True)
    apply_parser = sub.add_parser("apply", help="Chạy vòng lặp node Pha 3 (fresh-session)")
    apply_parser.add_argument(
        "--active-dir", required=True,
        help="Đường dẫn knowledge/active của scaffold (chạy từ project root)",
    )
    args = parser.parse_args(argv)
    summary = apply_command(args.active_dir)
    if summary["status"] == "refused":
        print(f"[DRIVER] Từ chối chạy:\n{summary['reason']}")
        return 2
    if summary["status"] == "blocked":
        print(
            f"[DRIVER] BLOCKED tại node {summary['task_id']} "
            f"(đã xong {summary['done']} node): {summary['reason']}"
        )
        print(
            "[DRIVER] Sửa nguyên nhân (handoff/feedback), đặt node về pending, "
            "chạy lại lệnh này — driver tự resume."
        )
        return 3
    print(
        f"[DRIVER] Hoàn thành {summary['done']} node. "
        "Parent tiếp tục §3 bước 6 (post_apply_verify)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
