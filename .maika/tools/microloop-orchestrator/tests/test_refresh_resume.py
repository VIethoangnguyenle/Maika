# tests/test_refresh_resume.py — durable BLOCKED -> new evidence -> resume (M9)
#
# Covers fixtures F13/F14 and mutations #12 (workflow request must enter
# BLOCKED), #13 (refresh fulfilled without new evidence fails) and #14
# (explicit empty request_only stays empty).
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import vnext_dispatch as vd
import vnext_state as vs

OLD_HASH = "sha256:" + "a" * 64
NEW_HASH = "sha256:" + "b" * 64


def _workspace(tmp_path):
    ws = vs.init_workspace(tmp_path / "changes", "C-1", "standard", "refresh test")
    vs.start_exploration(ws)
    (ws / "exploration").mkdir(exist_ok=True)
    (ws / "exploration" / "TRACE_EVIDENCE.yaml").write_text(yaml.safe_dump({
        "version": 1, "change_id": "C-1",
        "graph": {"project": "demo", "graph_commit": "old", "repository_head": "new",
                  "freshness": "VERY_STALE", "health": "HEALTHY",
                  "observation": OLD_HASH},
    }), encoding="utf-8")
    return ws


def _invocation(response_hash, provider="understand-anything",
                tool="get_graph_metadata", status="success"):
    return json.dumps({
        "trace_id": "t", "change_id": "C-1", "role": "grounding",
        "provider_id": provider, "tool": tool, "invocation_mode": "host_mcp",
        "request_hash": "sha256:" + "0" * 64, "response_hash": response_hash,
        "started_at": "2026-07-14T09:00:00Z", "ended_at": "2026-07-14T09:00:01Z",
        "status": status,
    }) + "\n"


REQUEST = {
    "request_type": "external_workflow", "workflow": "understand",
    "reason": "relevant graph files stale", "required_for": ["Q1"],
    "observed_freshness": "VERY_STALE", "resume_role": "grounding",
    "affected_claims": [],
}


def test_workflow_request_enters_durable_blocked(tmp_path):
    """Mutation #12: workflow request must enter BLOCKED with a persisted blocker."""
    ws = _workspace(tmp_path)
    blocked = vd.block_on_refresh_request(ws, "grounding", REQUEST, vs,
                                          "external_workflow")
    state = vs.load_state(ws)
    assert state["state"] == "BLOCKED"
    persisted = state["blocked"]
    assert persisted["code"] == "external_workflow"
    assert persisted["request_file"] == "EXTERNAL_WORKFLOW_REQUEST.yaml"
    assert persisted["resume_state"] == "EXPLORING"
    assert persisted["resume_action"] == "vnext-dispatch-role --role grounding"
    request = yaml.safe_load(
        (ws / "EXTERNAL_WORKFLOW_REQUEST.yaml").read_text(encoding="utf-8"))
    assert request["baseline_evidence_hash"] == OLD_HASH
    assert blocked["remediation"].startswith("run /understand")


def test_fulfill_refuses_without_new_evidence(tmp_path):
    """Mutation #13 / F13 negative half: same-hash or absent evidence never fulfills."""
    ws = _workspace(tmp_path)
    vd.block_on_refresh_request(ws, "grounding", REQUEST, vs, "external_workflow")
    ok, reason = vd.fulfill_blocked_request(ws, vs)
    assert not ok and "NEW understand-anything evidence" in reason
    # A record with the SAME hash as the baseline is not new evidence.
    invocations = ws / "exploration" / "PROVIDER_INVOCATIONS.jsonl"
    invocations.write_text(_invocation(OLD_HASH), encoding="utf-8")
    ok, _ = vd.fulfill_blocked_request(ws, vs)
    assert not ok
    # An error probe is not fulfillment either.
    invocations.write_text(_invocation(NEW_HASH, status="error"), encoding="utf-8")
    ok, _ = vd.fulfill_blocked_request(ws, vs)
    assert not ok
    assert vs.load_state(ws)["state"] == "BLOCKED"


def test_fulfill_with_new_evidence_resumes_original_role(tmp_path):
    """F13: UA refresh -> BLOCKED -> new get_graph_metadata evidence -> resume."""
    ws = _workspace(tmp_path)
    vd.block_on_refresh_request(ws, "grounding", REQUEST, vs, "external_workflow")
    (ws / "exploration" / "PROVIDER_INVOCATIONS.jsonl").write_text(
        _invocation(OLD_HASH) + _invocation(NEW_HASH), encoding="utf-8")
    ok, detail = vd.fulfill_blocked_request(ws, vs)
    assert ok, detail
    assert detail["resolution"]["evidence_hash"] == NEW_HASH
    assert detail["role"] == "grounding"
    assert detail["resume_action"] == "vnext-dispatch-role --role grounding"
    assert vs.load_state(ws)["state"] == "EXPLORING"
    assert not (ws / "EXTERNAL_WORKFLOW_REQUEST.yaml").exists()
    result = yaml.safe_load(Path(detail["result_file"]).read_text(encoding="utf-8"))
    assert result["resolved"]["evidence_hash"] == NEW_HASH


def test_db_reprobe_lifecycle(tmp_path):
    ws = _workspace(tmp_path)
    reprobe = {"request_type": "db_reprobe", "reason": "environment changed",
               "environment": "staging", "database": "orders_db",
               "resume_role": "database"}
    ok, reason, doc = vd.validate_db_reprobe_request(yaml.safe_dump(reprobe))
    assert ok, reason
    vd.block_on_refresh_request(ws, "database", doc, vs, "db_reprobe")
    state = vs.load_state(ws)
    assert state["blocked"]["request_file"] == "DB_REPROBE_REQUEST.yaml"
    ok, _ = vd.fulfill_blocked_request(ws, vs)
    assert not ok
    (ws / "exploration" / "PROVIDER_INVOCATIONS.jsonl").write_text(
        _invocation(NEW_HASH, provider="db-access", tool="sql_list_tables"),
        encoding="utf-8")
    ok, detail = vd.fulfill_blocked_request(ws, vs)
    assert ok, detail
    assert detail["resume_action"] == "vnext-dispatch-role --role database"
    assert vs.load_state(ws)["state"] == "EXPLORING"


def test_db_reprobe_request_requires_environment():
    bad = {"request_type": "db_reprobe", "reason": "x", "database": "d",
           "resume_role": "database"}
    ok, reason, _ = vd.validate_db_reprobe_request(yaml.safe_dump(bad))
    assert not ok and "environment" in reason


def test_explicit_empty_request_only_stays_empty():
    """Mutation #14 / F14: request_only: [] must not regain defaults."""
    contract = vd.external_workflow_contract(
        {"external_workflows": {"allowed": [], "request_only": []}})
    assert contract == {"allowed": [], "request_only": []}
    defaulted = vd.external_workflow_contract({})
    assert defaulted["request_only"] == vd.DEFAULT_EXTERNAL_WORKFLOWS["request_only"]
