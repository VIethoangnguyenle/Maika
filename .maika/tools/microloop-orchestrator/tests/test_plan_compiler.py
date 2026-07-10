# tests/test_plan_compiler.py
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import plan_compiler as pc
import vnext_state as vs

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

### TASK-002: Dùng A

```yaml
task:
  id: TASK-002
  implementation_mode: guided
  depends_on: [TASK-001]
  files:
    modify: [src/a.py]
    test: [tests/test_a.py]
  symbols:
    src/a.py: [A]
  verification:
    command: pytest tests/ -q
    expected: "2 passed"
```

Thân task 2.
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
    return ws, tmp_path


def test_compile_writes_queue_and_briefs(tmp_path):
    ws, root = _setup(tmp_path)
    out = pc.compile_plan(ws, repo_root=root)
    q = json.loads((ws / "generated" / "TASK_QUEUE.json").read_text())
    assert [t["id"] for t in q["tasks"]] == ["TASK-001", "TASK-002"]
    assert all(t["status"] == "pending" for t in q["tasks"])
    brief = (ws / "briefs" / "TASK-001.md").read_text()
    head, _, body = brief.partition("\n---\n")
    assert hashlib.sha256(body.encode()).hexdigest() == q["tasks"][0]["brief_hash"]
    assert "Thân task 1." in body                 # verbatim


def test_compile_deterministic(tmp_path):
    ws, root = _setup(tmp_path)
    pc.compile_plan(ws, repo_root=root)
    q1 = (ws / "generated" / "TASK_QUEUE.json").read_bytes()
    pc.compile_plan(ws, repo_root=root)
    assert (ws / "generated" / "TASK_QUEUE.json").read_bytes() == q1


def test_compile_refuses_invalid_plan(tmp_path):
    ws, root = _setup(tmp_path)
    p = ws / "IMPLEMENTATION_PLAN.md"
    p.write_text(p.read_text().replace("expected:", "TODO_expected:"), encoding="utf-8")
    out = pc.compile_plan(ws, repo_root=root)
    assert out["verdict"] != "APPROVED"
    assert not (ws / "generated" / "TASK_QUEUE.json").exists()
    v = json.loads((ws / "generated" / "PLAN_VALIDATION.json").read_text())
    assert v["verdict"] == "REVISE"


def test_plan_edit_invalidates_hash(tmp_path):
    ws, root = _setup(tmp_path)
    m1 = pc.compile_plan(ws, repo_root=root)["plan_sha256"]
    p = ws / "IMPLEMENTATION_PLAN.md"
    p.write_text(p.read_text() + "\n<!-- edit -->\n", encoding="utf-8")
    m2 = pc.compile_plan(ws, repo_root=root)["plan_sha256"]
    assert m1 != m2


# ── W4: task knowledge capsule ──────────────────────────────────────────────

def test_compile_writes_knowledge_capsule(tmp_path):
    import hashlib as _h
    import yaml as _yaml
    ws, root = _setup(tmp_path)
    pc.compile_plan(ws, repo_root=root)
    q = json.loads((ws / "generated" / "TASK_QUEUE.json").read_text())
    cap_path = ws / "briefs" / "TASK-001.knowledge.yaml"
    assert cap_path.exists()
    cap = _yaml.safe_load(cap_path.read_text())
    assert cap["task_id"] == "TASK-001"
    assert set(cap["knowledge_slice"]) >= {
        "author_dna", "conventions", "code_evidence", "business_rules",
        "historical_context", "database_evidence",
    }
    assert "forbidden_patterns" in cap and "assumptions" in cap
    # capsule hash recorded in queue matches the file
    assert _h.sha256(cap_path.read_text(encoding="utf-8").encode("utf-8")).hexdigest() == q["tasks"][0]["capsule_hash"]
    assert q["tasks"][0]["capsule_path"] == "briefs/TASK-001.knowledge.yaml"


def test_capsule_freshness_matches_evidence(tmp_path):
    import hashlib as _h
    import yaml as _yaml
    ws, root = _setup(tmp_path)
    pc.compile_plan(ws, repo_root=root)
    cap = _yaml.safe_load((ws / "briefs" / "TASK-001.knowledge.yaml").read_text())
    ev_sha = _h.sha256((ws / "exploration" / "EVIDENCE_MANIFEST.yaml").read_bytes()).hexdigest()
    assert cap["freshness"]["evidence_manifest_hash"] == "sha256:" + ev_sha
    assert cap["freshness"]["repository_commit"]


def test_capsule_carries_declared_slice(tmp_path):
    import yaml as _yaml
    ws, root = _setup(tmp_path)
    # inject a knowledge block into TASK-001's header
    p = ws / "IMPLEMENTATION_PLAN.md"
    p.write_text(
        p.read_text().replace(
            "  implementation_mode: exact\n",
            "  implementation_mode: exact\n"
            "  knowledge:\n    code_evidence: [CODE-001]\n    conventions: [CONV-1]\n"
            "  forbidden_patterns: [duplicate validation]\n",
            1,
        ),
        encoding="utf-8",
    )
    pc.compile_plan(ws, repo_root=root)
    cap = _yaml.safe_load((ws / "briefs" / "TASK-001.knowledge.yaml").read_text())
    assert cap["knowledge_slice"]["code_evidence"] == ["CODE-001"]
    assert cap["knowledge_slice"]["conventions"] == ["CONV-1"]
    assert cap["forbidden_patterns"] == ["duplicate validation"]
