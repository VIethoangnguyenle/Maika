# tests/test_vnext_dispatch.py
import json
import subprocess
from pathlib import Path

import vnext_dispatch as vd
import vnext_state as vs
import plan_compiler as pc

def _setup(tmp_path):
    ws = vs.init_workspace(tmp_path / "changes", "demo", "small", "t")
    (ws / "SPEC.md").write_text("# spec\n", encoding="utf-8")
    (tmp_path / "src").mkdir(exist_ok=True); (tmp_path / "tests").mkdir(exist_ok=True)
    (tmp_path / "src" / "a.py").write_text("A = 1\n")
    (tmp_path / "tests" / "test_a.py").write_text("def test_a():\n    assert True\n")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-qm", "base"], cwd=tmp_path, check=True)
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=tmp_path,
                         capture_output=True, text=True).stdout.strip()
    import hashlib
    plan_text = f"""---
change_id: demo
plan_version: 1
base_commit: {sha}
spec_hash: sha256:{hashlib.sha256((ws / "SPEC.md").read_bytes()).hexdigest()}
evidence_hash: sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
---

# Plan

### TASK-001: Tạo module A

```yaml
task:
  id: TASK-001
  implementation_mode: exact
  depends_on: []
  files:
    create: [src/b.py]
  verification:
    command: pytest tests/test_a.py -q
    expected: "1 passed"
```

Thân task 1.
"""
    (ws / "IMPLEMENTATION_PLAN.md").write_text(plan_text, encoding="utf-8")
    pc.compile_plan(ws, repo_root=tmp_path)
    return ws, tmp_path


def test_dispatch_happy_path(tmp_path):
    ws, root = _setup(tmp_path)
    
    def dummy_worker(tid, brief_path, result_path):
        import yaml
        res = {
            "task_id": tid,
            "status": "success",
            "files": {"create": ["src/b.py"]},
            "verification": {"passed": True, "output": "ok"}
        }
        Path(result_path).write_text(yaml.safe_dump(res, sort_keys=False), encoding="utf-8")
        return True

    vd.run_dispatch(ws, repo_root=root, worker_fn=dummy_worker)
    
    q = json.loads((ws / "generated" / "TASK_QUEUE.json").read_text(encoding="utf-8"))
    assert q["tasks"][0]["status"] == "success"


def test_dispatch_stops_on_brief_integrity_fail(tmp_path):
    ws, root = _setup(tmp_path)
    (ws / "briefs" / "TASK-001.md").write_text("Sửa đổi lén", encoding="utf-8")
    
    called = []
    def dummy_worker(tid, brief_path, result_path):
        called.append(tid)
        return True

    res = vd.run_dispatch(ws, repo_root=root, worker_fn=dummy_worker)
    assert res == False
    assert not called
    q = json.loads((ws / "generated" / "TASK_QUEUE.json").read_text(encoding="utf-8"))
    assert q["tasks"][0]["status"] == "failed"


def test_dispatch_stops_on_worker_fail(tmp_path):
    ws, root = _setup(tmp_path)
    
    def dummy_worker(tid, brief_path, result_path):
        import yaml
        res = {
            "task_id": tid,
            "status": "failure",
            "files": {},
            "verification": {"passed": False, "output": "error"}
        }
        Path(result_path).write_text(yaml.safe_dump(res, sort_keys=False), encoding="utf-8")
        return False

    res = vd.run_dispatch(ws, repo_root=root, worker_fn=dummy_worker)
    assert res == False
    q = json.loads((ws / "generated" / "TASK_QUEUE.json").read_text(encoding="utf-8"))
    assert q["tasks"][0]["status"] == "failed"


def test_planning_dispatch_fail(tmp_path):
    ws, root = _setup(tmp_path)
    import yaml
    p = ws / "IMPLEMENTATION_PLAN.md"
    p.write_text(p.read_text().replace("expected:", "TODO_expected:"), encoding="utf-8")
    res = vd.run_planning_dispatch(ws, repo_root=root)
    assert res == False
    req = yaml.safe_load((ws / "CONTEXT_REQUEST.yaml").read_text(encoding="utf-8"))
    assert req["request_type"] == "context"
    assert "expected required" in req["missing"][0]
