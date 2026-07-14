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


# ── database-request + database-context v2 (harness plan §7, M6) ────────────

def _database_request(**over):
    doc = {
        "version": 1, "change_id": "C-1", "environment": "staging",
        "database": "orders_db",
        "questions": [{"id": "Q-DB1", "question": "orders schema?",
                       "required_capabilities": ["database_schema_inspection"]}],
        "objects": [], "required_capabilities": ["database_schema_inspection"],
        "allowed_lane": "exploration", "data_probe_required": False,
        "source_anchors": [], "migration_refs": [],
    }
    doc.update(over)
    return doc


def test_database_request_valid():
    assert gates.validate_database_request(yaml.safe_dump(_database_request())).ok


def test_database_request_missing_environment_fails():
    """Mutation #8: DB evidence must be environment-bound."""
    res = gates.validate_database_request(
        yaml.safe_dump(_database_request(environment=None)))
    assert not res.ok and "environment" in res.reason


def test_database_request_wrong_lane_fails():
    res = gates.validate_database_request(
        yaml.safe_dump(_database_request(allowed_lane="data_probe")))
    assert not res.ok and "exploration" in res.reason


def _database_context(**over):
    doc = {
        "version": 2, "change_id": "C-1", "read_only": True,
        "provider": {"id": "db-access", "client_key": "db-access"},
        "probe": {"invocation_mode": "host_mcp", "database": "orders_db",
                  "environment": "staging", "observed_at": "2026-07-14T08:00:00Z",
                  "status": "success"},
        "allowed_lane": "exploration",
        "allowed_tools": ["list_databases", "sql_list_tables", "sql_get_columns",
                          "sql_get_constraints"],
        "used_tools": ["sql_list_tables", "sql_get_columns"],
        "observations": [{"object": "orders", "type": "table",
                          "columns": ["id", "status"]}],
        "code_consumers": [{"object": "orders", "file": "src/repo.py",
                            "symbol": "OrderRepo"}],
        "drift": [], "degradation": [], "limitations": [],
        "confidence": "high",
    }
    doc.update(over)
    return doc


def test_database_context_v2_valid():
    result = gates.validate_database_context(yaml.safe_dump(_database_context()))
    assert result.ok, result.reason


def test_database_context_v1_rejected():
    doc = {"read_only": True, "objects": [{"name": "orders", "type": "table"}]}
    res = gates.validate_database_context(yaml.safe_dump(doc))
    assert not res.ok and "version 2" in res.reason


def test_database_context_requires_read_only():
    res = gates.validate_database_context(
        yaml.safe_dump(_database_context(read_only=False)))
    assert not res.ok and "read_only" in res.reason


def test_database_context_probe_missing_environment_fails():
    """Mutation #8: DB context omits environment."""
    ctx = _database_context()
    ctx["probe"].pop("environment")
    res = gates.validate_database_context(yaml.safe_dump(ctx))
    assert not res.ok and "environment" in res.reason


def test_database_context_unclassified_drift_fails():
    """Mutation #9: drift must be classified."""
    res = gates.validate_database_context(yaml.safe_dump(_database_context(
        drift=[{"object": "orders", "detail": "column added in source"}])))
    assert not res.ok and "classification" in res.reason


def test_database_context_classified_drift_passes():
    res = gates.validate_database_context(yaml.safe_dump(_database_context(
        drift=[{"object": "orders", "classification": "source_ahead",
                "detail": "migration V42 not applied to staging"}])))
    assert res.ok, res.reason


def test_database_context_degraded_ok_without_probe():
    res = gates.validate_database_context(yaml.safe_dump(_database_context(
        probe={}, observations=[],
        degradation=[{"kind": "provider_unreachable",
                      "detail": "db-access MCP connection refused; fallback "
                                "source-declared schema"}],
        confidence="low")))
    assert res.ok, res.reason


def test_database_context_no_probe_no_degradation_fails():
    res = gates.validate_database_context(yaml.safe_dump(_database_context(probe={})))
    assert not res.ok and "degradation" in res.reason


def test_database_context_requires_pinned_allowed_tools():
    res = gates.validate_database_context(
        yaml.safe_dump(_database_context(allowed_tools=[])))
    assert not res.ok and "allowed_tools" in res.reason


# ── M7: DB lane enforcement against the provider registry ───────────────────

_PROVIDER_REGISTRY = yaml.safe_load(
    (Path(__file__).resolve().parents[3] / "config" / "provider-registry.yaml")
    .read_text(encoding="utf-8")
)
_EXPLORATION_TOOLS = ["list_databases", "sql_list_tables", "sql_get_columns",
                      "sql_get_constraints", "mongo_list_collections",
                      "mongo_get_schema"]


def _lane_check(request_over=None, **over):
    over.setdefault("allowed_tools", list(_EXPLORATION_TOOLS))
    request = _database_request(**(request_over or {}))
    return gates.validate_database_context(
        yaml.safe_dump(_database_context(**over)),
        provider_registry=_PROVIDER_REGISTRY,
        request_text=yaml.safe_dump(request),
    )


def test_lane_full_exploration_snapshot_passes():
    result = _lane_check(used_tools=["sql_list_tables", "mongo_get_schema"])
    assert result.ok, result.reason


def test_lane_data_probe_use_without_declared_need_fails():
    """Mutation #6 / fixture F10: Database Explorer calls sql_read."""
    result = _lane_check(used_tools=["sql_list_tables", "sql_read"])
    assert not result.ok and "out-of-lane" in result.reason


def test_lane_write_tool_always_fails():
    """Mutation #7: write/script is impossible in Database Explorer context."""
    result = _lane_check(
        used_tools=["sql_write"],
        allowed_tools=_EXPLORATION_TOOLS + ["sql_write"],
    )
    assert not result.ok and "allowed_tools outside the pinned lane" in result.reason


def test_lane_data_probe_allowed_when_declared():
    result = _lane_check(
        request_over={"data_probe_required": True},
        allowed_tools=_EXPLORATION_TOOLS + ["sql_read"],
        used_tools=["sql_list_tables", "sql_read"],
    )
    assert result.ok, result.reason


def test_lane_allowed_tools_must_cover_exploration_snapshot():
    result = _lane_check(allowed_tools=["sql_list_tables"])
    assert not result.ok and "full exploration lane snapshot" in result.reason


# ── W4: capsule-integrity + evidence-update-request ─────────────────────────

def _capsule_and_queue(ev_text="claims: []\n"):
    import hashlib
    ev_hash = "sha256:" + hashlib.sha256(ev_text.encode("utf-8")).hexdigest()
    capsule = yaml.safe_dump({
        "task_id": "TASK-001",
        "knowledge_slice": {"code_evidence": ["CODE-001"], "conventions": [],
                            "author_dna": [], "business_rules": [],
                            "historical_context": [], "database_evidence": []},
        "forbidden_patterns": [], "assumptions": [],
        "freshness": {"repository_commit": "abc123", "evidence_manifest_hash": ev_hash},
        "confidence": "medium",
    }, sort_keys=False)
    chash = hashlib.sha256(capsule.encode("utf-8")).hexdigest()
    queue = {"tasks": [{"id": "TASK-001", "capsule_hash": chash}]}
    return capsule, queue, ev_text


def test_capsule_integrity_valid():
    capsule, queue, ev = _capsule_and_queue()
    assert gates.validate_capsule_integrity(capsule, queue_doc=queue, task_id="TASK-001",
                                            evidence_manifest_text=ev).ok


def test_capsule_integrity_hash_tamper_fails():
    capsule, queue, ev = _capsule_and_queue()
    res = gates.validate_capsule_integrity(capsule + "\n# edit\n", queue_doc=queue,
                                           task_id="TASK-001", evidence_manifest_text=ev)
    assert not res.ok and "capsule_hash" in res.reason


def test_capsule_integrity_stale_evidence_fails():
    capsule, queue, ev = _capsule_and_queue()
    res = gates.validate_capsule_integrity(capsule, queue_doc=queue, task_id="TASK-001",
                                           evidence_manifest_text="claims: [changed]\n")
    assert not res.ok and "stale" in res.reason.lower()


def test_evidence_update_request_valid():
    doc = yaml.safe_dump({"task_id": "TASK-003", "status": "NEEDS_REGROUNDING",
                          "reason": "source diverges from capsule", "affected_evidence": ["CODE-014"]})
    assert gates.validate_evidence_update_request(doc).ok


def test_evidence_update_request_bad_status():
    doc = yaml.safe_dump({"task_id": "T", "status": "WHATEVER", "reason": "x",
                          "affected_evidence": ["A"]})
    res = gates.validate_evidence_update_request(doc)
    assert not res.ok and "status" in res.reason


def test_evidence_update_request_requires_reason_and_evidence():
    doc = yaml.safe_dump({"task_id": "T", "status": "STALE_KNOWLEDGE"})
    assert not gates.validate_evidence_update_request(doc).ok


# ── W6: verification-report real evidence ───────────────────────────────────

def test_verification_report_valid():
    doc = yaml.safe_dump({"commands": [{
        "name": "unit", "command": "pytest -q", "expected_output": "passed",
        "observed_output": "3 passed", "exit_code": 0, "timestamp": "2026-07-10T00:00:00Z",
        "interpretation": "pass",
    }]})
    assert gates.validate_verification_report(doc).ok


def test_verification_report_requires_observed_output():
    doc = yaml.safe_dump({"commands": [{
        "name": "unit", "command": "pytest -q", "observed_output": "",
        "exit_code": 0, "timestamp": "2026-07-10T00:00:00Z", "interpretation": "pass",
    }]})
    res = gates.validate_verification_report(doc)
    assert not res.ok and "observed_output" in res.reason


def test_verification_report_requires_integer_exit_code():
    doc = yaml.safe_dump({"commands": [{
        "name": "unit", "command": "pytest -q", "observed_output": "3 passed",
        "exit_code": "zero", "timestamp": "2026-07-10T00:00:00Z", "interpretation": "pass",
    }]})
    res = gates.validate_verification_report(doc)
    assert not res.ok and "exit_code" in res.reason
