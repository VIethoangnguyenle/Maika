# vnext_dispatch.py
"""Engine loop vNext: dispatch pending tasks to worker."""
import json
import importlib.util
from pathlib import Path


def _load(name, rel):
    mod_path = Path(__file__).resolve().parent / rel if "/" not in rel else \
        Path(__file__).resolve().parents[1] / rel
    spec = importlib.util.spec_from_file_location(name, mod_path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _update_status(q_path, tid, status):
    doc = json.loads(q_path.read_text(encoding="utf-8"))
    for t in doc["tasks"]:
        if t["id"] == tid:
            t["status"] = status
    q_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    return doc


def run_dispatch(ws, repo_root, worker_fn=None):
    ws = Path(ws)
    q_path = ws / "generated" / "TASK_QUEUE.json"
    doc = json.loads(q_path.read_text(encoding="utf-8"))
    gates = _load("gates", "gate-check/gates.py")
    
    for t in doc["tasks"]:
        if t["status"] != "pending":
            continue
            
        tid = t["id"]
        brief_path = ws / t["brief_path"]
        result_path = ws / t["result_path"]
        
        # 1. Gate: brief-integrity
        text = brief_path.read_text(encoding="utf-8")
        res = gates.validate_brief_integrity(text, queue_doc=doc)
        if not res.ok:
            _update_status(q_path, tid, "failed")
            return False
            
        # 2. Worker
        _update_status(q_path, tid, "running")
        if worker_fn:
            ok = worker_fn(tid, str(brief_path), str(result_path))
        else:
            # dummy implementation if no mock provided
            ok = False
            
        if not ok:
            _update_status(q_path, tid, "failed")
            return False
            
        # 3. Gate: result-contract
        if not result_path.exists():
            _update_status(q_path, tid, "failed")
            return False
        result_text = result_path.read_text(encoding="utf-8")
        current_doc = json.loads(q_path.read_text(encoding="utf-8"))
        res = gates.validate_result_contract(result_text, queue_doc=current_doc, task_id=tid)
        if not res.ok:
            _update_status(q_path, tid, "failed")
            return False
            
        doc = _update_status(q_path, tid, "success")
        
    return True


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
