import importlib.util
from pathlib import Path

import yaml

MOD = Path(__file__).resolve().parents[1] / "gates.py"
spec = importlib.util.spec_from_file_location("gates_knowledge_trace", MOD)
gates = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gates)


def _trace(**overrides):
    decision = {
        "id": "DEC-001",
        "statement": "Use the current persistence contract",
        "type": "persistence",
        "knowledge_questions": ["What is the live contract?"],
        "evidence_ids": ["SRC-1", "DB-1"],
        "authority": "live runtime/database state",
        "conflicts": [],
        "assumptions": [],
        "confidence": "high",
        "freshness": "fresh",
        "verdict": "accepted",
    }
    decision.update(overrides)
    return yaml.safe_dump({"decision": decision}, sort_keys=False)


def test_valid_knowledge_trace_passes():
    assert gates.validate_knowledge_trace(_trace()).ok


def test_material_decision_without_evidence_or_with_conflict_blocks():
    assert not gates.validate_knowledge_trace(_trace(evidence_ids=[])).ok
    assert not gates.validate_knowledge_trace(
        _trace(conflicts=[{"status": "unresolved", "statement": "source drift"}])
    ).ok
