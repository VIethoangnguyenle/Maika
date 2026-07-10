# vnext_dispatch.py
"""Engine loop vNext: dispatch pending tasks to fresh workers."""
import json
import importlib.util
from pathlib import Path


DISPATCH_TYPES = {"planning", "implementation", "fix", "task_review", "final_review"}


def _load(name, rel):
    mod_path = Path(__file__).resolve().parent / rel if "/" not in rel else \
        Path(__file__).resolve().parents[1] / rel
    spec = importlib.util.spec_from_file_location(name, mod_path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _read_queue(ws):
    return json.loads((Path(ws) / "generated" / "TASK_QUEUE.json").read_text(encoding="utf-8"))


def _write_queue(ws, doc):
    q_path = Path(ws) / "generated" / "TASK_QUEUE.json"
    q_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    return doc


def _update_task(ws, tid, **fields):
    doc = _read_queue(ws)
    for task in doc["tasks"]:
        if task["id"] == tid:
            task.update(fields)
            return _write_queue(ws, doc)
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


def _verdict(text):
    for line in text.splitlines():
        if line.startswith("VERDICT:"):
            return line.split(":", 1)[1].strip()
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
    lines = [
        f"DISPATCH_TYPE: {klass}",
        f"ROLE: {klass}",
        f"TASK_ID: {task_id}",
        f"ARTIFACT_FILE: {ws / brief_rel}",
        f"BRIEF_FILE: {ws / brief_rel}",
        f"OUTPUT_FILE: {ws / result_rel}",
        f"ALLOWED_SCOPE: {allowed}",
        f"DEPENDENCY_OUTPUTS: {dependencies}",
        "",
        "Read exactly the artifact path above and write exactly the output file.",
        "Do not rely on parent-session history. Do not write outside allowed scope.",
    ]
    if extra:
        lines.extend(["", str(extra)])
    return "\n".join(lines) + "\n"

def review_plan(ws, runner, output_path=None):
    ws = Path(ws)
    prompt = build_prompt("planning", ws, "IMPLEMENTATION_PLAN.md", "reviews/plan-review.md")
    (ws / "reviews").mkdir(exist_ok=True)
    out = output_path or (ws / "reviews" / "plan-review.md")
    if out.exists():
        out.unlink()
    
    exit_code, output = runner(prompt)
    if not out.exists():
        out.write_text(f"VERDICT: FINDINGS\nWorker exit {exit_code}: {output}", encoding="utf-8")
        
    text = out.read_text(encoding="utf-8")
    if text.startswith("VERDICT: APPROVED"):
        return "APPROVED"
    return "FINDINGS"


def _dispatch_to_runner(ws, dispatch_type, task, artifact_rel, output_rel, runner,
                        *, attempt=0, extra=None):
    prompt = build_prompt(dispatch_type, ws, artifact_rel, output_rel, extra=extra, task=task)
    _append_dispatch_log(ws, {
        "dispatch_type": dispatch_type,
        "task_id": task.get("id") if task else None,
        "artifact_path": artifact_rel,
        "output_path": output_rel,
        "attempt": attempt,
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
        return gates.validate_capsule_integrity(
            cap_file.read_text(encoding="utf-8"),
            queue_doc=queue_doc,
            task_id=task["id"],
            evidence_manifest_text=ev.read_text(encoding="utf-8") if ev.exists() else None,
        )
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
        _update_task(ws, task_id, status="in_progress", attempts=attempt)
        exit_code, output = _dispatch_to_runner(
            ws, dispatch_type, current, current["brief_path"], current["result_path"],
            runner, attempt=attempt,
        )
        if exit_code != 0:
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
    verdict = _verdict(review_path.read_text(encoding="utf-8"))
    if verdict == "APPROVED":
        _update_task(ws, task_id, status="done", review_path=review_rel)
        return {"status": "approved"}
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
    task = {"id": "FINAL_REVIEW", "files": {}, "depends_on": []}
    exit_code, output = _dispatch_to_runner(
        ws, "final_review", task, "generated/TASK_QUEUE.json", review_rel, runner,
    )
    if exit_code != 0:
        return {"status": "blocked", "reason": f"final_review exit {exit_code}: {output}"}
    if not review_path.exists():
        return {"status": "blocked", "reason": f"final_review exit 0 but did not write {review_rel}"}
    queue_doc = _read_queue(ws)
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


def run_queue(ws, repo_root, runner, max_retries=2):
    ws = Path(ws)
    gates = _load("gates", "gate-check/gates.py")

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
