# tests/test_trace_compiler.py — deterministic TRACE_REQUEST compilation (plan §7, M4)
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import trace_compiler as tc

FRAMEWORK = Path(__file__).resolve().parents[3]  # .maika/


def _workspace(tmp_path, questions):
    ws = tmp_path / "changes" / "C-7"
    (ws / "exploration").mkdir(parents=True)
    (ws / "CHANGE.yaml").write_text("id: C-7\nclass: standard\n", encoding="utf-8")
    (ws / "exploration" / "QUERY_PLAN.yaml").write_text(
        yaml.safe_dump({"version": 1, "questions": questions}), encoding="utf-8"
    )
    return ws


QUESTIONS = [
    {"id": "Q1", "question": "Flow lắp ráp ở đâu?",
     "required_capabilities": ["call_chain_trace", "exact_source_inspection"],
     "required_evidence_types": ["call_path"]},
    {"id": "Q2", "question": "Incident cũ?",
     "required_capabilities": ["historical_context_retrieval"],
     "required_evidence_types": ["incident_reference"]},
    {"id": "Q3", "question": "DB object nào?",
     "required_capabilities": ["database_schema_inspection"],
     "required_evidence_types": ["database_object"],
     "anchors": ["orders"]},
]


def test_compile_uses_grounding_contract_and_trace_scope(tmp_path):
    ws = _workspace(tmp_path, QUESTIONS)
    request = tc.compile_trace_request(ws, FRAMEWORK)
    assert request["version"] == 1 and request["change_id"] == "C-7"
    # exact_source_inspection is trace-scope and neither one_of nor conditional
    assert request["required_capabilities"] == ["exact_source_inspection"]
    # call_chain_trace sits in the one_of structured_trace group, not required
    assert "call_chain_trace" in request["one_of"]["structured_trace"]
    # memory capability is NOT trace-scope; DB capability is conditional
    for capability in ("historical_context_retrieval", "database_schema_inspection"):
        assert capability not in request["required_capabilities"]
    assert request["conditional"]["database_schema_inspection"]["triggers"] == [
        "persistence_change"
    ]
    assert request["anchors"] == ["orders"]
    assert [q["id"] for q in request["questions"]] == ["Q1", "Q2", "Q3"]


def test_compile_is_deterministic(tmp_path):
    ws = _workspace(tmp_path, QUESTIONS)
    first = tc.compile_trace_request(ws, FRAMEWORK)
    second = tc.compile_trace_request(ws, FRAMEWORK)
    assert first == second


def test_write_trace_request_passes_gate(tmp_path):
    import importlib.util
    gate_path = FRAMEWORK / "tools" / "gate-check" / "gates.py"
    spec = importlib.util.spec_from_file_location("gates_tc", gate_path)
    gates = importlib.util.module_from_spec(spec); spec.loader.exec_module(gates)

    ws = _workspace(tmp_path, QUESTIONS)
    path = tc.write_trace_request(ws, FRAMEWORK)
    registry = yaml.safe_load(
        (FRAMEWORK / "profiles" / "capability-registry.yaml").read_text(encoding="utf-8")
    )
    result = gates.validate_trace_request(
        path.read_text(encoding="utf-8"),
        valid_capabilities=set(registry.get("capabilities") or {}),
        trigger_vocabulary=set(registry.get("triggers") or {}),
    )
    assert result.ok, result.reason
