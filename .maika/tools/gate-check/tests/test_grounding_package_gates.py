"""W2 grounding-package gate validators (query plan, tool health, conflicts,
coverage, database context). Deterministic/pure — no I/O."""
import importlib.util
from pathlib import Path

import yaml

_G = Path(__file__).resolve().parents[1] / "gates.py"
spec = importlib.util.spec_from_file_location("gates", _G)
gates = importlib.util.module_from_spec(spec); spec.loader.exec_module(gates)

CAPS = {
    "architecture_discovery", "dependency_analysis", "exact_source_inspection",
    "historical_context_retrieval", "database_schema_inspection",
    "database_dependency_analysis",
}
EVID = {
    "architecture_node", "dependency_path", "file_symbol", "incident_reference",
    "database_object", "database_dependency",
}


# ── query-plan ──────────────────────────────────────────────────────────────

def _query_plan():
    return yaml.safe_dump({
        "version": 1,
        "change_id": "demo",
        "questions": [
            {"id": "Q-CODE-001", "question": "Where is the flow assembled?",
             "required_capabilities": ["architecture_discovery", "dependency_analysis"],
             "required_evidence_types": ["architecture_node", "dependency_path"],
             "status": "pending"},
            {"id": "Q-MEM-001", "question": "Prior incidents?",
             "required_capabilities": ["historical_context_retrieval"],
             "required_evidence_types": ["incident_reference"],
             "status": "pending", "zero_results_allowed": True},
        ],
    }, sort_keys=False)


def test_query_plan_valid():
    assert gates.validate_query_plan(_query_plan(), valid_capabilities=CAPS, coverable_evidence=EVID).ok


def test_query_plan_rejects_fake_capability():
    bad = _query_plan().replace("architecture_discovery", "telepathy")
    res = gates.validate_query_plan(bad, valid_capabilities=CAPS, coverable_evidence=EVID)
    assert not res.ok and "telepathy" in res.reason


def test_query_plan_rejects_uncoverable_evidence():
    bad = _query_plan().replace("architecture_node", "ouija_signal")
    res = gates.validate_query_plan(bad, valid_capabilities=CAPS, coverable_evidence=EVID)
    assert not res.ok and "ouija_signal" in res.reason


def test_query_plan_requires_questions():
    res = gates.validate_query_plan("version: 1\nquestions: []\n",
                                    valid_capabilities=CAPS, coverable_evidence=EVID)
    assert not res.ok and "question" in res.reason.lower()


def test_query_plan_blocked_question_needs_reason():
    doc = yaml.safe_load(_query_plan())
    doc["questions"][0]["status"] = "blocked"
    res = gates.validate_query_plan(yaml.safe_dump(doc), valid_capabilities=CAPS, coverable_evidence=EVID)
    assert not res.ok and "blocked_reason" in res.reason


# ── tool-health ─────────────────────────────────────────────────────────────

def _tool_health(**over):
    doc = {
        "version": 1,
        "providers": {
            "codebase_memory": {"configured": True, "status": "ready",
                                "indexed_commit": "abc123", "freshness": "fresh",
                                "probe": {"operation": "list_projects", "observed": "1 project"}},
            "understand_anything": {"configured": True, "status": "unavailable",
                                    "degradation": {"probe": "list_projects",
                                                    "observed": "No projects loaded",
                                                    "fallback": "current source",
                                                    "confidence_impact": "medium"}},
        },
    }
    doc["providers"].update(over)
    return yaml.safe_dump(doc, sort_keys=False)


def test_tool_health_valid():
    assert gates.validate_tool_health(_tool_health()).ok


def test_tool_health_ready_requires_real_probe():
    bad = _tool_health(codebase_memory={"configured": True, "status": "ready"})
    res = gates.validate_tool_health(bad)
    assert not res.ok and "probe" in res.reason


def test_tool_health_degraded_requires_degradation_record():
    bad = _tool_health(understand_anything={"configured": True, "status": "unavailable"})
    res = gates.validate_tool_health(bad)
    assert not res.ok and "degradation" in res.reason


def test_tool_health_rejects_bare_ready_without_observed():
    bad = _tool_health(codebase_memory={"configured": True, "status": "ready",
                                        "freshness": "fresh", "probe": {"operation": "x"}})
    res = gates.validate_tool_health(bad)
    assert not res.ok and "observed" in res.reason


# ── conflicts ───────────────────────────────────────────────────────────────

def test_conflicts_empty_ok():
    assert gates.validate_conflicts("version: 1\nconflicts: []\n").ok


def test_conflicts_resolved_ok():
    doc = {"conflicts": [{"id": "C-1", "claim_ids": ["CODE-004", "MEM-003"],
                          "type": "stale_memory", "status": "resolved",
                          "resolution": "source supersedes memory", "resolved_by": ["CODE-004"]}]}
    assert gates.validate_conflicts(yaml.safe_dump(doc)).ok


def test_conflicts_open_blocks():
    doc = {"conflicts": [{"id": "C-1", "claim_ids": ["A", "B"], "type": "source_drift",
                          "status": "open"}]}
    res = gates.validate_conflicts(yaml.safe_dump(doc))
    assert not res.ok and "C-1" in res.reason


def test_conflicts_resolved_requires_resolution():
    doc = {"conflicts": [{"id": "C-1", "claim_ids": ["A"], "type": "x", "status": "resolved"}]}
    res = gates.validate_conflicts(yaml.safe_dump(doc))
    assert not res.ok and "resolution" in res.reason


# ── coverage ────────────────────────────────────────────────────────────────

def test_coverage_ready_ok():
    doc = {"questions": {"total": 2, "answered": 2, "blocked": 0},
           "required_evidence": {"covered": ["architecture_node"], "missing": []},
           "verdict": "READY"}
    assert gates.validate_coverage(yaml.safe_dump(doc)).ok


def test_coverage_ready_rejected_when_missing_evidence():
    doc = {"questions": {"total": 2, "answered": 2, "blocked": 0},
           "required_evidence": {"covered": [], "missing": ["database_object"]},
           "verdict": "READY"}
    res = gates.validate_coverage(yaml.safe_dump(doc))
    assert not res.ok and "missing" in res.reason.lower()


def test_coverage_ready_rejected_when_blocked_questions():
    doc = {"questions": {"total": 2, "answered": 1, "blocked": 1},
           "required_evidence": {"covered": ["x"], "missing": []},
           "verdict": "READY"}
    res = gates.validate_coverage(yaml.safe_dump(doc))
    assert not res.ok and "blocked" in res.reason.lower()


def test_coverage_counts_must_be_consistent():
    doc = {"questions": {"total": 1, "answered": 2, "blocked": 0},
           "required_evidence": {"covered": [], "missing": []},
           "verdict": "NEEDS_CONTEXT"}
    res = gates.validate_coverage(yaml.safe_dump(doc))
    assert not res.ok


# ── database-context ────────────────────────────────────────────────────────

def test_database_context_with_objects_ok():
    doc = {"read_only": True,
           "objects": [{"name": "orders", "type": "table"}],
           "drift": "none"}
    assert gates.validate_database_context(yaml.safe_dump(doc)).ok


def test_database_context_degraded_ok():
    doc = {"read_only": True, "objects": [],
           "degradation": {"provider": "database", "probe": "psql",
                           "observed": "connection refused", "fallback": "source-declared schema",
                           "confidence_impact": "medium"}}
    assert gates.validate_database_context(yaml.safe_dump(doc)).ok


def test_database_context_requires_read_only():
    doc = {"read_only": False, "objects": [{"name": "x", "type": "table"}]}
    res = gates.validate_database_context(yaml.safe_dump(doc))
    assert not res.ok and "read_only" in res.reason


def test_database_context_empty_without_degradation_fails():
    doc = {"read_only": True, "objects": []}
    res = gates.validate_database_context(yaml.safe_dump(doc))
    assert not res.ok
