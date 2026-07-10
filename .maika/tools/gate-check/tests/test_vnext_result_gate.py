# .maika/tools/gate-check/tests/test_vnext_result_gate.py
import importlib.util
import json
import subprocess
from pathlib import Path
import yaml

_G = Path(__file__).resolve().parents[1] / "gates.py"
spec = importlib.util.spec_from_file_location("gates", _G)
gates = importlib.util.module_from_spec(spec); spec.loader.exec_module(gates)

QUEUE_DOC = {
    "tasks": [
        {
            "id": "TASK-001",
            "evidence_ids": ["CODE-001"],
            "files": {
                "create": ["src/b.py"],
                "modify": ["src/a.py"],
                "delete": ["src/old.py"],
                "test": ["tests/test_a.py"],
            }
        }
    ]
}

RESULT_OK = """
task_id: TASK-001
status: success
files:
  create: [src/b.py]
  modify: [src/a.py]
  delete: [src/old.py]
  test: [tests/test_a.py]
verification:
  passed: true
  output: "1 passed"
"""

def test_result_contract_passes():
    res = gates.validate_result_contract(RESULT_OK, queue_doc=QUEUE_DOC, task_id="TASK-001")
    assert res.ok


def test_missing_task_id_fails():
    res = gates.validate_result_contract(RESULT_OK.replace("task_id: TASK-001", "task_id: TASK-002"), queue_doc=QUEUE_DOC, task_id="TASK-001")
    assert not res.ok and "mismatch" in res.reason


def test_status_failure_fails():
    res = gates.validate_result_contract(RESULT_OK.replace("status: success", "status: failure"), queue_doc=QUEUE_DOC, task_id="TASK-001")
    assert not res.ok and "success" in res.reason


def test_non_mapping_yaml_result_fails_without_crashing():
    res = gates.validate_result_contract("stub result", queue_doc=QUEUE_DOC, task_id="TASK-001")
    assert not res.ok and "mapping" in res.reason


def test_verification_failed_fails():
    res = gates.validate_result_contract(RESULT_OK.replace("passed: true", "passed: false"), queue_doc=QUEUE_DOC, task_id="TASK-001")
    assert not res.ok and "verification" in res.reason


def test_files_mismatch_fails():
    bad = RESULT_OK.replace("create: [src/b.py]", "create: [src/c.py]")
    res = gates.validate_result_contract(bad, queue_doc=QUEUE_DOC, task_id="TASK-001")
    assert not res.ok and "files mismatch" in res.reason


def test_deleted_files_mismatch_fails():
    bad = RESULT_OK.replace("delete: [src/old.py]", "delete: []")
    res = gates.validate_result_contract(bad, queue_doc=QUEUE_DOC, task_id="TASK-001")
    assert not res.ok and "files mismatch" in res.reason


def test_task_review_contract_passes():
    review = ("TASK_ID: TASK-001\nVERDICT: APPROVED\n\n"
              "## Counter-evidence\n- src/a.py:10 — behavior confirmed in source\n\n"
              "## Knowledge Trace\n```yaml\ndecision:\n"
              "  id: DEC-REVIEW-001\n  statement: Approve verified behavior.\n"
              "  type: verification_claim\n  knowledge_questions: [\"Does source satisfy the task?\"]\n"
              "  evidence_ids: [CODE-001]\n  authority: current source\n"
              "  conflicts: []\n  assumptions: []\n  confidence: high\n"
              "  freshness: verified\n  verdict: approved\n```\n")
    res = gates.validate_task_review(review, queue_doc=QUEUE_DOC, task_id="TASK-001")
    assert res.ok


def test_task_review_approved_requires_counter_evidence():
    review = "TASK_ID: TASK-001\nVERDICT: APPROVED\n"
    res = gates.validate_task_review(review, queue_doc=QUEUE_DOC, task_id="TASK-001")
    assert not res.ok and "Counter-evidence" in res.reason


def test_task_review_requires_known_verdict():
    review = "TASK_ID: TASK-001\nVERDICT: LOOKS_FINE\n"
    res = gates.validate_task_review(review, queue_doc=QUEUE_DOC, task_id="TASK-001")
    assert not res.ok and "verdict" in res.reason


def test_knowledge_impact_valid():
    doc = ("stale_entries: [ARCH-004]\nsuperseded_decisions: []\nnew_candidates: []\n"
           "graph_refresh_required: true\nmemory_updates: [save incident lesson]\n")
    assert gates.validate_knowledge_impact(doc).ok


def test_knowledge_impact_missing_lane_fails():
    doc = "stale_entries: []\nsuperseded_decisions: []\ngraph_refresh_required: false\n"
    res = gates.validate_knowledge_impact(doc)
    assert not res.ok and "missing lanes" in res.reason


def test_knowledge_impact_graph_refresh_must_be_bool():
    doc = ("stale_entries: []\nsuperseded_decisions: []\nnew_candidates: []\n"
           "graph_refresh_required: maybe\nmemory_updates: []\n")
    res = gates.validate_knowledge_impact(doc)
    assert not res.ok and "boolean" in res.reason


def test_final_review_requires_reviewed_tasks():
    queue = {
        "tasks": [
            {"id": "TASK-001", "status": "done", "review_path": "reviews/TASK-001.md"},
            {"id": "TASK-002", "status": "done"},
        ]
    }
    review = "VERDICT: APPROVED\n"
    res = gates.validate_final_review(review, queue_doc=queue)
    assert not res.ok and "lacks review" in res.reason
