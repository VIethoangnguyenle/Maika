from pathlib import Path
import importlib.util

import yaml


ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("gates_context", ROOT / "tools" / "gate-check" / "gates.py")
GATES = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GATES)


def test_context_loader_is_a_structured_knowledge_router():
    text = (ROOT / "procedures" / "context-loader.md").read_text(encoding="utf-8")
    for key in (
        "role", "state", "change class", "artifact type", "knowledge questions",
        "required evidence", "provider health", "token budget",
        "loaded_artifacts", "knowledge_slice", "memory_slice", "source_anchors",
        "database_slice", "missing_context", "degradation", "confidence",
    ):
        assert key in text
    assert "full-history" in text


def test_context_package_gate_blocks_missing_required_context_without_degradation():
    package = {
        "role": "implementation", "change_id": "A", "state": "EXECUTING",
        "loaded_artifacts": ["briefs/TASK-1.md"], "knowledge_slice": [],
        "memory_slice": [], "source_anchors": [], "database_slice": [],
        "missing_context": ["DB evidence"], "degradation": [], "confidence": "medium",
        "freshness": {"repository_commit": "abc", "generated_at": "2026-07-11T00:00:00Z"},
    }
    result = GATES.validate_context_package(yaml.safe_dump(package))
    assert not result.ok and "degradation" in result.reason
