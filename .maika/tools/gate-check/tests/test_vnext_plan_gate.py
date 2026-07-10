# .maika/tools/gate-check/tests/test_vnext_plan_gate.py
import importlib.util
import subprocess
from pathlib import Path

_G = Path(__file__).resolve().parents[1] / "gates.py"
spec = importlib.util.spec_from_file_location("gates", _G)
gates = importlib.util.module_from_spec(spec); spec.loader.exec_module(gates)

_PP = Path(__file__).resolve().parents[2] / "microloop-orchestrator" / "plan_parser.py"
spec2 = importlib.util.spec_from_file_location("plan_parser", _PP)
pp = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(pp)

PLAN_TPL = """---
change_id: demo
plan_version: 1
knowledge_trace:
  id: DEC-PLAN-001
  statement: Decompose the verified change.
  type: task_decomposition
  knowledge_questions: ["What tasks are required?"]
  evidence_ids: [CODE-001]
  authority: current source
  conflicts: []
  assumptions: []
  confidence: high
  freshness: fresh
  verdict: accepted
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
    (tmp_path / "src").mkdir(); (tmp_path / "tests").mkdir()
    (tmp_path / "src" / "a.py").write_text("A = 1\n")
    (tmp_path / "tests" / "test_a.py").write_text("def test_a():\n    assert True\n")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-qm", "base"], cwd=tmp_path, check=True)
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=tmp_path,
                         capture_output=True, text=True).stdout.strip()
    return PLAN_TPL.replace("BASESHA", sha), sha


def _check(tmp_path, text, spec_sha256="SPECSHA"):
    return gates.validate_vnext_plan(
        text, plan_doc=pp.parse_plan(text), repo_root=str(tmp_path),
        spec_sha256=spec_sha256)


def test_plan_ok_passes(tmp_path):
    text, _ = _mk(tmp_path)
    res = _check(tmp_path, text)
    assert res.ok, res.reason


def test_unresolvable_base_commit_fails(tmp_path):
    text, sha = _mk(tmp_path)
    res = _check(tmp_path, text.replace(sha, "deadbeef" * 5))
    assert not res.ok and "base_commit" in res.reason


def test_spec_hash_mismatch_fails(tmp_path):
    text, _ = _mk(tmp_path)
    res = _check(tmp_path, text, spec_sha256="khac_sha")
    assert not res.ok and "spec_hash" in res.reason


def test_missing_verification_fails(tmp_path):
    text, _ = _mk(tmp_path)
    res = _check(tmp_path, text.replace('    expected: "1 passed"\n', ""))
    assert not res.ok and "verification" in res.reason


def test_todo_marker_fails(tmp_path):
    text, _ = _mk(tmp_path)
    res = _check(tmp_path, text.replace("Thân task 1.", "Thân task 1. TODO: fix"))
    assert not res.ok and "placeholder" in res.reason


def test_cyclic_deps_fails(tmp_path):
    text, _ = _mk(tmp_path)
    res = _check(tmp_path, text.replace("depends_on: []", "depends_on: [TASK-002]"))
    assert not res.ok and "cycle" in res.reason


def test_modify_file_missing_fails(tmp_path):
    text, _ = _mk(tmp_path)
    res = _check(tmp_path, text.replace("modify: [src/a.py]", "modify: [src/missing.py]"))
    assert not res.ok and "missing" in res.reason


def test_delete_file_missing_fails(tmp_path):
    text, _ = _mk(tmp_path)
    text = text.replace("modify: [src/a.py]", "delete: [src/missing.py]")
    res = _check(tmp_path, text)
    assert not res.ok and "files.delete missing" in res.reason


def test_symbol_not_found_fails(tmp_path):
    text, _ = _mk(tmp_path)
    res = _check(tmp_path, text.replace("src/a.py: [A]", "src/a.py: [KhongTonTai]"))
    assert not res.ok and "symbol" in res.reason


def test_change_workspace_gate():
    ok = "change_id: demo\nclass: small\ntitle: t\ncreated_at: 2026-07-10\n"
    assert gates.validate_change_workspace(ok).ok
    assert not gates.validate_change_workspace(ok.replace("small", "gigantic")).ok
    assert not gates.validate_change_workspace("change_id: demo\n").ok
