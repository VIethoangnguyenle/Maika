# tests/test_vnext_dispatch.py
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import vnext_dispatch as vd
import vnext_state as vs
import plan_compiler as pc

REVIEW_TRACE = """
## Knowledge Trace
```yaml
decision:
  id: DEC-REVIEW-001
  statement: Approve verified task behavior.
  type: verification_claim
  knowledge_questions: ["Does current source satisfy the task?"]
  evidence_ids: [CODE-001]
  authority: current source
  conflicts: []
  assumptions: []
  confidence: high
  freshness: verified
  verdict: approved
```
"""


def _review(ws, review_type, verdict="APPROVED", body="", task_id=None):
    queue = json.loads((ws / "generated" / "TASK_QUEUE.json").read_text(encoding="utf-8"))
    normalized = "CHANGES_REQUESTED" if verdict == "CHANGES_REQUIRED" else verdict
    task_line = f"task_id: {task_id}\n" if task_id else ""
    return (
        "---\nschema_version: 1\n"
        f"review_type: {review_type}\nverdict: {normalized}\n{task_line}"
        f"reviewed_commit: {queue['base_commit']}\n"
        f"reviewed_plan_hash: sha256:{queue['plan_sha256']}\n---\n{body}"
    )

def _setup(tmp_path):
    ws = vs.init_workspace(tmp_path / "changes", "demo", "standard", "t")
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
    evidence_sha = hashlib.sha256(
        (ws / "exploration" / "EVIDENCE_MANIFEST.yaml").read_bytes()
    ).hexdigest()
    plan_text = f"""---
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
base_commit: {sha}
spec_hash: sha256:{hashlib.sha256((ws / "SPEC.md").read_bytes()).hexdigest()}
evidence_hash: sha256:{evidence_sha}
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


def test_review_plan_approved(tmp_path):
    ws, _ = _setup(tmp_path)
    def runner(prompt):
        # Extract output file path from a marker or similar logic in real implementation
        out = ws / "review_output.txt"
        out.write_text(_review(
            ws, "plan",
            # repo-relative POSIX anchor (matches the other review bodies); an
            # absolute OS path here would embed Windows backslashes and fail the
            # posix _FILE_PATH anchor extraction on Windows.
            body="## Counter-evidence\n- src/a.py:1 — confirmed in current source\n" + REVIEW_TRACE,
        ))
        return 0, ""
    assert vd.review_plan(ws, runner, output_path=ws / "review_output.txt") == "APPROVED"


def test_review_plan_findings(tmp_path):
    ws, _ = _setup(tmp_path)
    def runner(prompt):
        out = ws / "review_output.txt"
        out.write_text("VERDICT: FINDINGS\n- stub")
        return 0, ""
    assert vd.review_plan(ws, runner, output_path=ws / "review_output.txt") == "FINDINGS"


def test_review_plan_missing_output(tmp_path):
    ws, _ = _setup(tmp_path)
    def runner(prompt):
        return 1, "failed"
    assert vd.review_plan(ws, runner, output_path=ws / "review_output.txt") == "FINDINGS"


def _runner_for_w3(ws, calls, *, first_review="APPROVED"):
    review_verdicts = [first_review]

    def runner(prompt):
        calls.append(prompt)
        markers = dict(
            line.split(": ", 1) for line in prompt.splitlines() if ": " in line
        )
        dispatch_type = markers["DISPATCH_TYPE"]
        task_id = markers.get("TASK_ID", "TASK-001")
        output = Path(markers["OUTPUT_FILE"])
        output.parent.mkdir(parents=True, exist_ok=True)
        if dispatch_type in {"implementation", "fix"}:
            (ws.parents[1] / "src" / "b.py").write_text("B = 1\n", encoding="utf-8")
            output.write_text(
                "\n".join([
                    f"task_id: {task_id}",
                    "status: success",
                    "files:",
                    "  create: [src/b.py]",
                    "verification:",
                    "  passed: true",
                    "  output: ok",
                    "consumed:",
                    "  evidence_ids: [CODE-001]",
                    "  knowledge_ids: []",
                    "",
                ]),
                encoding="utf-8",
            )
        elif dispatch_type == "task_review":
            verdict = review_verdicts.pop(0) if review_verdicts else "APPROVED"
            body = ""
            if verdict == "APPROVED":
                body = "## Counter-evidence\n- src/b.py:1 — behavior confirmed in current source\n" + REVIEW_TRACE
            output.write_text(_review(ws, "task", verdict, body, task_id), encoding="utf-8")
        elif dispatch_type == "final_review":
            output.write_text(_review(
                ws, "final", body="## Counter-evidence\n- src/b.py:1 — verified\n" + REVIEW_TRACE
            ), encoding="utf-8")
            (output.parent / "KNOWLEDGE_IMPACT.yaml").write_text(
                "stale_entries: []\nsuperseded_decisions: []\nnew_candidates: []\n"
                "graph_refresh_required: false\nmemory_updates: []\n",
                encoding="utf-8",
            )
        return 0, "ok"

    return runner


def test_run_queue_uses_fresh_dispatches_and_reviews_every_task(tmp_path):
    ws, root = _setup(tmp_path)
    calls = []
    runner = _runner_for_w3(ws, calls)

    out = vd.run_queue(ws, root, runner, max_retries=1)

    assert out["status"] == "done"
    q = json.loads((ws / "generated" / "TASK_QUEUE.json").read_text(encoding="utf-8"))
    assert q["tasks"][0]["status"] == "done"
    assert q["tasks"][0]["review_path"] == "reviews/TASK-001.md"
    assert (ws / "reviews" / "FINAL_REVIEW.md").exists()
    assert [p.splitlines()[0] for p in calls] == [
        "DISPATCH_TYPE: implementation",
        "DISPATCH_TYPE: task_review",
        "DISPATCH_TYPE: final_review",
    ]


def test_run_queue_blocks_when_exit_zero_has_no_result_file(tmp_path):
    ws, root = _setup(tmp_path)

    out = vd.run_queue(ws, root, lambda prompt: (0, "no artifact"), max_retries=0)

    assert out["status"] == "blocked"
    assert out["task_id"] == "TASK-001"
    q = json.loads((ws / "generated" / "TASK_QUEUE.json").read_text(encoding="utf-8"))
    assert q["tasks"][0]["status"] == "blocked"


def test_run_queue_routes_evidence_update_request_without_blind_retry(tmp_path):
    ws, root = _setup(tmp_path)
    calls = []

    def runner(prompt):
        calls.append(prompt)
        request = ws / "results" / "TASK-001.EVIDENCE_UPDATE_REQUEST.yaml"
        request.write_text(
            "task_id: TASK-001\nstatus: STALE_KNOWLEDGE\n"
            "reason: source hash changed\naffected_evidence: [CODE-001]\n",
            encoding="utf-8",
        )
        return 0, "reground"

    out = vd.run_queue(ws, root, runner, max_retries=2)
    assert out["status"] == "blocked"
    assert out["reason"] == "EVIDENCE_UPDATE_REQUEST"
    assert len(calls) == 1
    task = json.loads((ws / "generated" / "TASK_QUEUE.json").read_text())["tasks"][0]
    assert task["evidence_update_request"].endswith("EVIDENCE_UPDATE_REQUEST.yaml")


def test_run_queue_dispatches_fix_after_task_review_findings(tmp_path):
    ws, root = _setup(tmp_path)
    calls = []
    review_verdicts = ["CHANGES_REQUIRED", "APPROVED"]

    def runner(prompt):
        calls.append(prompt)
        markers = dict(
            line.split(": ", 1) for line in prompt.splitlines() if ": " in line
        )
        dispatch_type = markers["DISPATCH_TYPE"]
        task_id = markers.get("TASK_ID", "TASK-001")
        output = Path(markers["OUTPUT_FILE"])
        output.parent.mkdir(parents=True, exist_ok=True)
        if dispatch_type in {"implementation", "fix"}:
            (ws.parents[1] / "src" / "b.py").write_text("B = 1\n", encoding="utf-8")
            output.write_text(
                f"""task_id: {task_id}
status: success
files:
  create: [src/b.py]
verification:
  passed: true
  output: ok
consumed:
  evidence_ids: [CODE-001]
  knowledge_ids: []
""",
                encoding="utf-8",
            )
        elif dispatch_type == "task_review":
            verdict = review_verdicts.pop(0)
            body = ""
            if verdict == "APPROVED":
                body = "## Counter-evidence\n- src/b.py:1 — confirmed in source\n" + REVIEW_TRACE
            output.write_text(_review(ws, "task", verdict, body, task_id), encoding="utf-8")
        elif dispatch_type == "final_review":
            output.write_text(_review(
                ws, "final", body="## Counter-evidence\n- src/b.py:1 — verified\n" + REVIEW_TRACE
            ), encoding="utf-8")
            (output.parent / "KNOWLEDGE_IMPACT.yaml").write_text(
                "stale_entries: []\nsuperseded_decisions: []\nnew_candidates: []\n"
                "graph_refresh_required: false\nmemory_updates: []\n",
                encoding="utf-8",
            )
        return 0, "ok"

    out = vd.run_queue(ws, root, runner, max_retries=1)

    assert out["status"] == "done"
    assert [p.splitlines()[0] for p in calls] == [
        "DISPATCH_TYPE: implementation",
        "DISPATCH_TYPE: task_review",
        "DISPATCH_TYPE: fix",
        "DISPATCH_TYPE: task_review",
        "DISPATCH_TYPE: final_review",
    ]


def test_run_queue_resumes_reviewing_task_without_reimplementation(tmp_path):
    ws, root = _setup(tmp_path)
    (root / "src" / "b.py").write_text("B = 1\n", encoding="utf-8")
    q_path = ws / "generated" / "TASK_QUEUE.json"
    q = json.loads(q_path.read_text(encoding="utf-8"))
    q["tasks"][0]["status"] = "reviewing"
    q["tasks"][0]["attempts"] = 0
    q_path.write_text(json.dumps(q, indent=2), encoding="utf-8")
    (ws / "results" / "TASK-001.yaml").write_text(
        """task_id: TASK-001
status: success
files:
  create: [src/b.py]
verification:
  passed: true
  output: ok
consumed:
  evidence_ids: [CODE-001]
  knowledge_ids: []
""",
        encoding="utf-8",
    )
    calls = []

    def runner(prompt):
        calls.append(prompt)
        markers = dict(
            line.split(": ", 1) for line in prompt.splitlines() if ": " in line
        )
        output = Path(markers["OUTPUT_FILE"])
        output.parent.mkdir(parents=True, exist_ok=True)
        if markers["DISPATCH_TYPE"] == "task_review":
            output.write_text(_review(
                ws, "task", body="## Counter-evidence\n- src/b.py:1 — confirmed in source\n" + REVIEW_TRACE,
                task_id="TASK-001",
            ), encoding="utf-8")
        elif markers["DISPATCH_TYPE"] == "final_review":
            output.write_text(_review(
                ws, "final", body="## Counter-evidence\n- src/b.py:1 — verified\n" + REVIEW_TRACE
            ), encoding="utf-8")
            (output.parent / "KNOWLEDGE_IMPACT.yaml").write_text(
                "stale_entries: []\nsuperseded_decisions: []\nnew_candidates: []\n"
                "graph_refresh_required: false\nmemory_updates: []\n",
                encoding="utf-8",
            )
        return 0, "ok"

    out = vd.run_queue(ws, root, runner, max_retries=1)

    assert out["status"] == "done"
    assert [p.splitlines()[0] for p in calls] == [
        "DISPATCH_TYPE: task_review",
        "DISPATCH_TYPE: final_review",
    ]


def test_run_queue_resumes_changes_required_task_with_fix_dispatch(tmp_path):
    ws, root = _setup(tmp_path)
    q_path = ws / "generated" / "TASK_QUEUE.json"
    q = json.loads(q_path.read_text(encoding="utf-8"))
    q["tasks"][0]["status"] = "changes_required"
    q["tasks"][0]["attempts"] = 0
    q["tasks"][0]["review_path"] = "reviews/TASK-001.md"
    q_path.write_text(json.dumps(q, indent=2), encoding="utf-8")
    (ws / "reviews" / "TASK-001.md").write_text(
        "TASK_ID: TASK-001\nVERDICT: CHANGES_REQUIRED\n", encoding="utf-8"
    )
    calls = []
    runner = _runner_for_w3(ws, calls)

    out = vd.run_queue(ws, root, runner, max_retries=1)

    assert out["status"] == "done"
    assert [p.splitlines()[0] for p in calls] == [
        "DISPATCH_TYPE: fix",
        "DISPATCH_TYPE: task_review",
        "DISPATCH_TYPE: final_review",
    ]


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
