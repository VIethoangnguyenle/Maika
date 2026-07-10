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
            "files": {
                "create": ["src/b.py"],
                "modify": ["src/a.py"]
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


def test_verification_failed_fails():
    res = gates.validate_result_contract(RESULT_OK.replace("passed: true", "passed: false"), queue_doc=QUEUE_DOC, task_id="TASK-001")
    assert not res.ok and "verification" in res.reason


def test_files_mismatch_fails():
    bad = RESULT_OK.replace("create: [src/b.py]", "create: [src/c.py]")
    res = gates.validate_result_contract(bad, queue_doc=QUEUE_DOC, task_id="TASK-001")
    assert not res.ok and "files mismatch" in res.reason
