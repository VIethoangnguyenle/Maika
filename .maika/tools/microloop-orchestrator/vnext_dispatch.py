# vnext_dispatch.py
"""Engine loop vNext: dispatch pending tasks to fresh workers."""
import json
import importlib.util
import hashlib
import os
import socket
import tempfile
from pathlib import Path
from datetime import datetime, timezone

import yaml

from adaptive_runtime import DEFAULT_TOKEN_BUDGET
from runtime_hardening import ReviewInvalid, parse_review


DISPATCH_KERNEL_ID = "KERNEL_ID: maika-knowledge-control-v1"
DISPATCH_TYPES = {
    "intent", "grounding", "reconciliation", "brainstorming", "spec", "planning",
    "plan_review", "implementation", "fix", "task_review", "final_review",
    "verification", "knowledge_curator", "skill_evolution_curator",
    "skill_evolution_implementer", "skill_evolution_reviewer",
}


def _dispatch_kernel():
    """Load the one canonical worker constitution; never duplicate prompt prose."""
    path = Path(__file__).resolve().parents[2] / "procedures" / "dispatch-kernel.md"
    text = path.read_text(encoding="utf-8")
    if DISPATCH_KERNEL_ID not in text:
        raise RuntimeError(f"invalid dispatch kernel: {path}")
    marker = "```text\n"
    start = text.find(marker)
    end = text.find("\n```", start + len(marker))
    if start < 0 or end < 0:
        raise RuntimeError(f"dispatch kernel has no canonical text block: {path}")
    return text[start + len(marker):end].strip()


def _load(name, rel):
    mod_path = Path(__file__).resolve().parent / rel if "/" not in rel else \
        Path(__file__).resolve().parents[1] / rel
    spec = importlib.util.spec_from_file_location(name, mod_path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _read_queue(ws):
    return json.loads((Path(ws) / "generated" / "TASK_QUEUE.json").read_text(encoding="utf-8"))


def _write_queue(ws, doc, expected_generation=None):
    q_path = Path(ws) / "generated" / "TASK_QUEUE.json"
    current_generation = 0
    if q_path.exists():
        current_generation = int(json.loads(q_path.read_text(encoding="utf-8")).get("generation") or 0)
    if expected_generation is not None and current_generation != int(expected_generation):
        raise ValueError(f"queue generation mismatch: expected {expected_generation}, found {current_generation}")
    doc["schema_version"] = int(doc.get("schema_version") or 1)
    doc["generation"] = current_generation + 1
    doc.setdefault("version", 1)
    payload = json.dumps(doc, ensure_ascii=False, indent=2)
    fd, temp_name = tempfile.mkstemp(prefix=".TASK_QUEUE.", dir=q_path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, q_path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise
    return doc


def _update_task(ws, tid, **fields):
    doc = _read_queue(ws)
    generation = int(doc.get("generation") or 0)
    for task in doc["tasks"]:
        if task["id"] == tid:
            if fields.get("status") == "in_progress":
                fields.setdefault("lease", {
                    "version": 1, "pid": os.getpid(), "host": socket.gethostname(),
                    "started_at": datetime.now(timezone.utc).isoformat(),
                })
            elif fields.get("status") in {"done", "blocked", "changes_required"}:
                fields.setdefault("lease", None)
            task.update(fields)
            return _write_queue(ws, doc, expected_generation=generation)
    raise ValueError(f"task {tid} not in queue")


def _task_by_id(doc, tid):
    return next((t for t in doc.get("tasks", []) if t.get("id") == tid), None)


def _next_pending_task(doc):
    done = {t["id"] for t in doc.get("tasks", []) if t.get("status") == "done"}
    for task in doc.get("tasks", []):
        if task.get("status") in {"pending", "changes_required", "in_progress", "reviewing"}:
            if all(dep in done for dep in task.get("depends_on", []) or []):
                return task
    return None


def _append_dispatch_log(ws, record):
    path = Path(ws) / "generated" / "DISPATCH_LOG.jsonl"
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def _verdict(ws, text, review_type):
    queue = _read_queue(ws)
    try:
        return parse_review(
            text, review_type, queue.get("base_commit"),
            "sha256:" + queue.get("plan_sha256", ""),
        )["verdict"]
    except ReviewInvalid:
        return None


def run_planning_dispatch(ws, repo_root):
    ws = Path(ws)
    pc = _load("plan_compiler", "plan_compiler.py")
    res = pc.compile_plan(ws, repo_root)
    if res.get("verdict") == "REVISE":
        import yaml
        req = {
            "request_type": "context",
            "missing": [f"Plan validation failed: {res.get('reason')}"],
            "blocked_reason": "vnext-plan gate failed"
        }
        (ws / "CONTEXT_REQUEST.yaml").write_text(
            yaml.safe_dump(req, sort_keys=False, allow_unicode=True),
            encoding="utf-8"
        )
        return False
    return True

def build_prompt(klass, ws, brief_rel, result_rel, extra=None, task=None):
    if klass not in DISPATCH_TYPES:
        raise ValueError(f"unknown dispatch type: {klass}")
    ws = Path(ws)
    task = task or {}
    task_id = task.get("id", "stub")
    allowed = json.dumps(task.get("files") or {}, ensure_ascii=False, sort_keys=True)
    dependencies = json.dumps(task.get("depends_on") or [], ensure_ascii=False)
    capsule = task.get("capsule_path") or "none"
    context_package = task.get("context_package_path") or "none"
    prior_review = task.get("review_path") or "none"
    lines = [
        f"DISPATCH_TYPE: {klass}",
        f"ROLE: {klass}",
        f"TASK_ID: {task_id}",
        f"ARTIFACT_FILE: {ws / brief_rel}",
        f"BRIEF_FILE: {ws / brief_rel}",
        f"OUTPUT_FILE: {ws / result_rel}",
        f"ALLOWED_SCOPE: {allowed}",
        f"DEPENDENCY_OUTPUTS: {dependencies}",
        f"KNOWLEDGE_CAPSULE: {ws / capsule if capsule != 'none' else capsule}",
        f"CONTEXT_PACKAGE: {ws / context_package if context_package != 'none' else context_package}",
        f"PRIOR_REVIEW: {ws / prior_review if prior_review != 'none' else prior_review}",
        DISPATCH_KERNEL_ID,
        "",
        _dispatch_kernel(),
        "",
        "Read exactly the assigned artifacts above and write exactly the output file.",
        "For implementation/review, read KNOWLEDGE_CAPSULE and record consumed IDs.",
        "Do not write outside ALLOWED_SCOPE.",
    ]
    if extra:
        lines.extend(["", str(extra)])
    return "\n".join(lines) + "\n"

def review_plan(ws, runner, output_path=None):
    ws = Path(ws)
    prompt = build_prompt("plan_review", ws, "IMPLEMENTATION_PLAN.md", "reviews/plan-review.md")
    (ws / "reviews").mkdir(exist_ok=True)
    out = output_path or (ws / "reviews" / "plan-review.md")
    if out.exists():
        out.unlink()
    
    exit_code, output = runner(prompt)
    if not out.exists():
        out.write_text(f"VERDICT: FINDINGS\nWorker exit {exit_code}: {output}", encoding="utf-8")
        
    text = out.read_text(encoding="utf-8")
    gates = _load("gates_plan_review", "gate-check/gates.py")
    queue = _read_queue(ws)
    evidence_ids = {item for task in queue.get("tasks") or [] for item in task.get("evidence_ids") or []}
    review = gates.validate_plan_review(
        text, valid_evidence_ids=evidence_ids, repo_root=queue.get("repo_root")
    )
    if review.ok and _verdict(ws, text, "plan") == "APPROVED":
        return "APPROVED"
    return "FINDINGS"


def _dispatch_to_runner(ws, dispatch_type, task, artifact_rel, output_rel, runner,
                        *, attempt=0, extra=None):
    queue = _read_queue(ws)
    metrics = queue.setdefault("runtime_metrics", {})
    task_class = queue.get("task_class", "standard")
    limits = (queue.get("runtime_limits") or {}).get(task_class) or DEFAULT_TOKEN_BUDGET[task_class]
    maximum = int(limits["max_worker_calls"])
    prompt = build_prompt(dispatch_type, ws, artifact_rel, output_rel, extra=extra, task=task)
    context_bytes = len(prompt.encode("utf-8"))
    for rel in {artifact_rel, task.get("capsule_path"), task.get("context_package_path"), task.get("review_path")}:
        path = Path(ws) / rel if rel else None
        if path and path.is_file():
            context_bytes += path.stat().st_size
    estimated_tokens = (context_bytes + 3) // 4
    metrics.update({
        "prompt_bytes": len(prompt.encode("utf-8")),
        "context_bytes": context_bytes,
        "estimated_tokens": int(metrics.get("estimated_tokens") or 0) + estimated_tokens,
        "estimation_method": "chars_div_4",
        "total_tokens": metrics.get("total_tokens", "unavailable"),
    })
    if estimated_tokens > int(limits["max_context_tokens"]):
        _write_queue(ws, queue, expected_generation=int(queue.get("generation") or 0))
        return 76, (f"{task_class} context budget exceeded "
                    f"({estimated_tokens}/{limits['max_context_tokens']} estimated tokens)")
    if int(metrics.get("worker_calls") or 0) >= maximum:
        return 75, f"{task_class} worker-call budget exhausted; escalate or block"
    metrics["worker_calls"] = int(metrics.get("worker_calls") or 0) + 1
    if metrics["worker_calls"] == maximum:
        metrics["budget_warning"] = f"worker-call budget reached ({maximum}/{maximum})"
    if dispatch_type == "fix":
        metrics["retry_count"] = int(metrics.get("retry_count") or 0) + 1
    _write_queue(ws, queue, expected_generation=int(queue.get("generation") or 0))
    _append_dispatch_log(ws, {
        "dispatch_type": dispatch_type,
        "task_id": task.get("id") if task else None,
        "artifact_path": artifact_rel,
        "output_path": output_rel,
        "attempt": attempt,
        "kernel_id": DISPATCH_KERNEL_ID.split(": ", 1)[1],
        "capsule_path": task.get("capsule_path") if task else None,
    })
    return runner(prompt)


def _validate_brief(ws, gates, task, queue_doc):
    brief_path = Path(ws) / task["brief_path"]
    if not brief_path.exists():
        return gates.Result(False, f"missing brief: {task['brief_path']}")
    brief = gates.validate_brief_integrity(
        brief_path.read_text(encoding="utf-8"),
        queue_doc=queue_doc,
    )
    if not brief.ok:
        return brief
    # W4: Task Knowledge Capsule must be immutable + fresh before dispatch.
    capsule_path = task.get("capsule_path")
    if capsule_path:
        cap_file = Path(ws) / capsule_path
        if not cap_file.exists():
            return gates.Result(False, f"missing capsule: {capsule_path}")
        ev = Path(ws) / "exploration" / "EVIDENCE_MANIFEST.yaml"
        capsule_result = gates.validate_capsule_integrity(
            cap_file.read_text(encoding="utf-8"),
            queue_doc=queue_doc,
            task_id=task["id"],
            evidence_manifest_text=ev.read_text(encoding="utf-8") if ev.exists() else None,
        )
        if not capsule_result.ok:
            return capsule_result
        context_rel = task.get("context_package_path")
        if not context_rel:
            return gates.Result(False, "missing context_package_path")
        context_file = Path(ws) / context_rel
        if not context_file.exists():
            return gates.Result(False, f"missing context package: {context_rel}")
        import hashlib
        observed = hashlib.sha256(context_file.read_text(encoding="utf-8").encode("utf-8")).hexdigest()
        if observed != task.get("context_package_hash"):
            return gates.Result(False, "context package hash mismatch")
        return gates.validate_context_package(context_file.read_text(encoding="utf-8"))
    return brief


def _run_implementation_or_fix(ws, gates, task, runner, max_retries, dispatch_type,
                               starting_attempt=0):
    task_id = task["id"]
    result_path = Path(ws) / task["result_path"]
    last_reason = None
    for attempt in range(starting_attempt, max_retries + 1):
        queue_doc = _read_queue(ws)
        current = _task_by_id(queue_doc, task_id)
        brief = _validate_brief(ws, gates, current, queue_doc)
        if not brief.ok:
            _update_task(ws, task_id, status="blocked", blocked_reason=brief.reason)
            return {"status": "blocked", "reason": brief.reason, "attempt": attempt}

        if result_path.exists():
            result_path.unlink()
        update_path = result_path.with_name(f"{task_id}.EVIDENCE_UPDATE_REQUEST.yaml")
        if update_path.exists():
            update_path.unlink()
        _update_task(ws, task_id, status="in_progress", attempts=attempt)
        exit_code, output = _dispatch_to_runner(
            ws, dispatch_type, current, current["brief_path"], current["result_path"],
            runner, attempt=attempt,
        )
        if update_path.exists():
            request = gates.validate_evidence_update_request(update_path.read_text(encoding="utf-8"))
            if request.ok:
                _update_task(ws, task_id, status="blocked", blocked_reason="EVIDENCE_UPDATE_REQUEST",
                             evidence_update_request=str(update_path.relative_to(ws)))
                return {"status": "blocked", "reason": "EVIDENCE_UPDATE_REQUEST", "attempt": attempt}
            last_reason = request.reason
        elif exit_code != 0:
            last_reason = f"{dispatch_type} exit {exit_code}: {output}"
        elif not result_path.exists():
            last_reason = f"{dispatch_type} exit 0 but did not write {current['result_path']}"
        else:
            queue_doc = _read_queue(ws)
            result = gates.validate_result_contract(
                result_path.read_text(encoding="utf-8"),
                queue_doc=queue_doc,
                task_id=task_id,
            )
            if result.ok:
                _update_task(ws, task_id, status="reviewing", result_path=current["result_path"])
                return {"status": "ready_for_review", "attempt": attempt}
            last_reason = result.reason
        if attempt >= max_retries:
            break

    _update_task(ws, task_id, status="blocked", blocked_reason=last_reason)
    return {"status": "blocked", "reason": last_reason, "attempt": max_retries}


def _run_task_review(ws, gates, task, runner, attempt):
    task_id = task["id"]
    review_rel = f"reviews/{task_id}.md"
    review_path = Path(ws) / review_rel
    if review_path.exists():
        review_path.unlink()
    exit_code, output = _dispatch_to_runner(
        ws, "task_review", task, task["result_path"], review_rel, runner, attempt=attempt,
    )
    if exit_code != 0:
        reason = f"task_review exit {exit_code}: {output}"
        _update_task(ws, task_id, status="blocked", blocked_reason=reason)
        return {"status": "blocked", "reason": reason}
    if not review_path.exists():
        reason = f"task_review exit 0 but did not write {review_rel}"
        _update_task(ws, task_id, status="blocked", blocked_reason=reason)
        return {"status": "blocked", "reason": reason}
    queue_doc = _read_queue(ws)
    review = gates.validate_task_review(
        review_path.read_text(encoding="utf-8"),
        queue_doc=queue_doc,
        task_id=task_id,
    )
    if not review.ok:
        _update_task(ws, task_id, status="blocked", blocked_reason=review.reason)
        return {"status": "blocked", "reason": review.reason}
    verdict = _verdict(ws, review_path.read_text(encoding="utf-8"), "task")
    if verdict == "APPROVED":
        _update_task(ws, task_id, status="done", review_path=review_rel)
        return {"status": "approved"}
    if verdict != "CHANGES_REQUESTED":
        reason = "task review is malformed or has unsupported verdict"
        _update_task(ws, task_id, status="blocked", blocked_reason=reason)
        return {"status": "blocked", "reason": reason}
    _update_task(ws, task_id, status="changes_required", review_path=review_rel)
    return {"status": "changes_required"}


def _run_one_task(ws, gates, task, runner, max_retries):
    dispatch_type = "fix" if task.get("status") == "changes_required" else "implementation"
    attempt = int(task.get("attempts") or 0)
    while attempt <= max_retries:
        if task.get("status") != "reviewing":
            impl = _run_implementation_or_fix(
                ws, gates, task, runner, max_retries, dispatch_type, starting_attempt=attempt,
            )
            if impl["status"] == "blocked":
                return {"status": "blocked", "task_id": task["id"], "reason": impl["reason"]}
            attempt = impl["attempt"]
        current = _task_by_id(_read_queue(ws), task["id"])
        review = _run_task_review(ws, gates, current, runner, attempt)
        if review["status"] == "approved":
            return {"status": "done", "task_id": task["id"]}
        if review["status"] == "blocked":
            return {"status": "blocked", "task_id": task["id"], "reason": review["reason"]}
        attempt += 1
        if attempt > max_retries:
            reason = "task review requested changes after retry budget"
            _update_task(ws, task["id"], status="blocked", blocked_reason=reason)
            return {"status": "blocked", "task_id": task["id"], "reason": reason}
        task = _task_by_id(_read_queue(ws), task["id"])
        dispatch_type = "fix"
    reason = "retry budget exhausted"
    _update_task(ws, task["id"], status="blocked", blocked_reason=reason)
    return {"status": "blocked", "task_id": task["id"], "reason": reason}


def _run_final_review(ws, gates, runner):
    review_rel = "reviews/FINAL_REVIEW.md"
    review_path = Path(ws) / review_rel
    if review_path.exists():
        review_path.unlink()
    queue_doc = _read_queue(ws)
    loaded = ["generated/TASK_QUEUE.json"]
    knowledge_slice, source_anchors = [], []
    for queued in queue_doc.get("tasks") or []:
        loaded.extend([queued.get("brief_path"), queued.get("capsule_path"),
                       queued.get("result_path"), queued.get("review_path")])
        capsule_path = Path(ws) / queued["capsule_path"]
        capsule = yaml.safe_load(capsule_path.read_text(encoding="utf-8")) or {}
        knowledge_slice.extend(capsule.get("project_knowledge") or [])
        source_anchors.extend((capsule.get("knowledge_slice") or {}).get("code_evidence") or [])
    package = {
        "version": 1, "role": "reviewer", "change_id": queue_doc.get("change_id"),
        "state": "FINAL_REVIEW", "loaded_artifacts": [item for item in loaded if item],
        "knowledge_slice": knowledge_slice, "memory_slice": [],
        "source_anchors": source_anchors, "database_slice": [],
        "missing_context": [], "degradation": [], "confidence": "high",
        "freshness": {"repository_commit": (yaml.safe_load(
            (Path(ws) / "briefs" / f"{queue_doc['tasks'][0]['id']}.knowledge.yaml")
            .read_text(encoding="utf-8")) or {}).get("freshness", {}).get("repository_commit"),
                      "generated_at": datetime.fromtimestamp(
                          (Path(ws) / "generated" / "TASK_QUEUE.json").stat().st_mtime,
                          timezone.utc,
                      ).isoformat()},
    }
    context_rel = "generated/CONTEXT_PACKAGE.final-review.yaml"
    context_path = Path(ws) / context_rel
    context_text = yaml.safe_dump(package, sort_keys=False, allow_unicode=True)
    context_path.write_text(context_text, encoding="utf-8")
    context_gate = gates.validate_context_package(context_text)
    if not context_gate.ok:
        return {"status": "blocked", "reason": context_gate.reason}
    task = {
        "id": "FINAL_REVIEW", "files": {}, "depends_on": [],
        "context_package_path": context_rel,
        "context_package_hash": hashlib.sha256(context_text.encode("utf-8")).hexdigest(),
    }
    exit_code, output = _dispatch_to_runner(
        ws, "final_review", task, "generated/TASK_QUEUE.json", review_rel, runner,
    )
    if exit_code != 0:
        return {"status": "blocked", "reason": f"final_review exit {exit_code}: {output}"}
    if not review_path.exists():
        return {"status": "blocked", "reason": f"final_review exit 0 but did not write {review_rel}"}
    if _verdict(ws, review_path.read_text(encoding="utf-8"), "final") != "APPROVED":
        return {"status": "blocked", "reason": "final review is malformed or not approved"}
    final = gates.validate_final_review(
        review_path.read_text(encoding="utf-8"),
        queue_doc=queue_doc,
    )
    if not final.ok:
        return {"status": "blocked", "reason": final.reason}
    # W5: the final review must report whole-change knowledge impact.
    ki_path = Path(ws) / "reviews" / "KNOWLEDGE_IMPACT.yaml"
    if not ki_path.exists():
        return {"status": "blocked", "reason": "final review missing reviews/KNOWLEDGE_IMPACT.yaml"}
    ki = gates.validate_knowledge_impact(ki_path.read_text(encoding="utf-8"))
    if not ki.ok:
        return {"status": "blocked", "reason": ki.reason}
    return {"status": "done"}


def run_queue(ws, repo_root, runner, max_retries=2, runtime_policy=None):
    ws = Path(ws)
    gates = _load("gates", "gate-check/gates.py")
    if runtime_policy is not None:
        queue = _read_queue(ws)
        queue["runtime_limits"] = runtime_policy.token_budget
        _write_queue(ws, queue, expected_generation=int(queue.get("generation") or 0))

    while True:
        doc = _read_queue(ws)
        blocked = next((t for t in doc.get("tasks", []) if t.get("status") == "blocked"), None)
        if blocked:
            return {
                "status": "blocked",
                "task_id": blocked.get("id"),
                "reason": blocked.get("blocked_reason") or "task blocked",
            }
        task = _next_pending_task(doc)
        if task is None:
            if all(t.get("status") == "done" for t in doc.get("tasks", [])):
                final = _run_final_review(ws, gates, runner)
                return final
            return {"status": "blocked", "reason": "no runnable task"}
        out = _run_one_task(ws, gates, task, runner, max_retries)
        if out["status"] == "blocked":
            return out
