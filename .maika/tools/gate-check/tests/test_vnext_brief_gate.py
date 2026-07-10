# .maika/tools/gate-check/tests/test_vnext_brief_gate.py
import importlib.util
import json
import subprocess
from pathlib import Path

_G = Path(__file__).resolve().parents[1] / "gates.py"
spec = importlib.util.spec_from_file_location("gates", _G)
gates = importlib.util.module_from_spec(spec); spec.loader.exec_module(gates)

_PC = Path(__file__).resolve().parents[2] / "microloop-orchestrator" / "plan_compiler.py"
spec_pc = importlib.util.spec_from_file_location("plan_compiler", _PC)
pc = importlib.util.module_from_spec(spec_pc); spec_pc.loader.exec_module(pc)

_VS = Path(__file__).resolve().parents[2] / "microloop-orchestrator" / "vnext_state.py"
spec_vs = importlib.util.spec_from_file_location("vnext_state", _VS)
vs = importlib.util.module_from_spec(spec_vs); spec_vs.loader.exec_module(vs)

PLAN_TPL = """---
change_id: demo
plan_version: 1
base_commit: BASESHA
spec_hash: sha256:SPECSHA
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
    test: [tests/test_a.py]
  verification:
    command: pytest tests/test_a.py -q
    expected: "1 passed"
```

Thân task 1.
"""

def _mk(tmp_path):
    (tmp_path / "src").mkdir(exist_ok=True); (tmp_path / "tests").mkdir(exist_ok=True)
    (tmp_path / "src" / "a.py").write_text("A = 1\n")
    (tmp_path / "tests" / "test_a.py").write_text("def test_a():\n    assert True\n")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-qm", "base"], cwd=tmp_path, check=True)
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=tmp_path,
                         capture_output=True, text=True).stdout.strip()
    return PLAN_TPL.replace("BASESHA", sha), sha

def _setup(tmp_path):
    import hashlib
    ws = vs.init_workspace(tmp_path / "changes", "demo", "small", "t")
    (ws / "SPEC.md").write_text("# spec\n", encoding="utf-8")
    plan_text, _ = _mk(tmp_path)
    evidence_sha = hashlib.sha256(
        (ws / "exploration" / "EVIDENCE_MANIFEST.yaml").read_bytes()
    ).hexdigest()
    plan_text = plan_text.replace(
        "SPECSHA", hashlib.sha256((ws / "SPEC.md").read_bytes()).hexdigest())
    plan_text = plan_text.replace(
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        evidence_sha,
    )
    (ws / "IMPLEMENTATION_PLAN.md").write_text(plan_text, encoding="utf-8")
    pc.compile_plan(ws, repo_root=tmp_path)
    return ws, tmp_path


def test_brief_integrity_passes(tmp_path):
    ws, _ = _setup(tmp_path)
    text = (ws / "briefs" / "TASK-001.md").read_text(encoding="utf-8")
    queue_doc = json.loads((ws / "generated" / "TASK_QUEUE.json").read_text(encoding="utf-8"))
    res = gates.validate_brief_integrity(text, queue_doc=queue_doc)
    assert res.ok


def test_brief_hash_mismatch_fails(tmp_path):
    ws, _ = _setup(tmp_path)
    text = (ws / "briefs" / "TASK-001.md").read_text(encoding="utf-8")
    text = text.replace("Thân task 1.", "Thân task 1. sửa đổi")
    queue_doc = json.loads((ws / "generated" / "TASK_QUEUE.json").read_text(encoding="utf-8"))
    res = gates.validate_brief_integrity(text, queue_doc=queue_doc)
    assert not res.ok and "mismatch" in res.reason


def test_task_id_missing_fails(tmp_path):
    ws, _ = _setup(tmp_path)
    text = (ws / "briefs" / "TASK-001.md").read_text(encoding="utf-8")
    text = text.replace("task_id: TASK-001", "task_id: TASK-002")
    queue_doc = json.loads((ws / "generated" / "TASK_QUEUE.json").read_text(encoding="utf-8"))
    res = gates.validate_brief_integrity(text, queue_doc=queue_doc)
    assert not res.ok and "not in queue" in res.reason


def test_stale_plan_fails(tmp_path):
    ws, _ = _setup(tmp_path)
    text = (ws / "briefs" / "TASK-001.md").read_text(encoding="utf-8")
    queue_doc = json.loads((ws / "generated" / "TASK_QUEUE.json").read_text(encoding="utf-8"))
    queue_doc["plan_sha256"] = "x"
    res = gates.validate_brief_integrity(text, queue_doc=queue_doc)
    assert not res.ok and "stale plan" in res.reason
