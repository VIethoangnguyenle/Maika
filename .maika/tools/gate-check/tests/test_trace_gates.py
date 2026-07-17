"""trace-request + trace-evidence gates (harness plan §7/§14, M4).

Covers the M4 half of the mutation suite: UA trace without invocation record
(#3), truncated response claiming complete (#17), missing source verification
hash (#18), one_of unsatisfied, conditional use without trigger.
"""
import hashlib
import importlib.util
import json
from pathlib import Path

import yaml

_G = Path(__file__).resolve().parents[1] / "gates.py"
spec = importlib.util.spec_from_file_location("gates", _G)
gates = importlib.util.module_from_spec(spec); spec.loader.exec_module(gates)

CAPS = {
    "architecture_discovery", "domain_flow_trace", "call_chain_trace",
    "impact_analysis", "historical_context_retrieval", "exact_source_inspection",
}
TRIGGERS = {"graph_gap", "ua_unavailable", "blast_radius_required"}

REQUEST = {
    "version": 1,
    "change_id": "C-1",
    "questions": [{"id": "Q1", "question": "How does dispatch flow?",
                   "required_capabilities": ["call_chain_trace"]}],
    "anchors": [],
    "required_capabilities": ["exact_source_inspection"],
    "one_of": {"structured_trace": ["call_chain_trace", "domain_flow_trace"]},
    "conditional": {"historical_context_retrieval": {"triggers": ["graph_gap", "ua_unavailable"]},
                    "impact_analysis": {"triggers": ["blast_radius_required"]}},
    "freshness_requirement": "graph_commit_current_or_scoped_stale",
    "source_verification_requirement": "material_exact_facts_source_verified",
}

UA_HASH = "sha256:" + "1" * 64
ACME_HASH = "sha256:" + "2" * 64
TOOL_HASH = "sha256:" + "f" * 64
REQUEST_HASH = "sha256:" + "0" * 64


def _observation(provider="understand-anything", tool="trace_call_chain",
                 response_hash=UA_HASH, **over):
    doc = {
        "contract_version": 1,
        "provider_id": provider,
        "provider_runtime_version": "fixture-1",
        "tool": tool,
        "tool_contract_hash": TOOL_HASH,
        "request_hash": REQUEST_HASH,
        "response_hash": response_hash,
        "project": "maika",
        "source_revision": "abc123",
        "working_tree_state": "clean",
        "provider_snapshot": {},
        "observed_at": "2026-07-14T08:00:01Z",
        "status": "success",
        "degradation_reasons": [],
        "authority": "structured_graph_trace",
        "canonical": False,
        "truncated": False,
    }
    doc.update(over)
    return doc


def _invocation(provider, tool, response_hash, trace_id):
    return json.dumps({
        "trace_id": trace_id, "change_id": "C-1", "role": "grounding",
        "provider_id": provider, "tool": tool, "invocation_mode": "host_mcp",
        "request_hash": REQUEST_HASH, "response_hash": response_hash,
        "started_at": "2026-07-14T08:04:00Z",
        "ended_at": "2026-07-14T08:04:01Z", "status": "success",
    })

INVOCATIONS = "\n".join([
    json.dumps({"trace_id": "t1", "change_id": "C-1", "role": "grounding",
                "provider_id": "understand-anything", "tool": "trace_call_chain",
                "invocation_mode": "host_mcp", "request_hash": "sha256:" + "0" * 64,
                "response_hash": UA_HASH, "started_at": "2026-07-14T08:00:00Z",
                "ended_at": "2026-07-14T08:00:01Z", "status": "success"}),
    json.dumps({"trace_id": "t2", "change_id": "C-1", "role": "grounding",
                "provider_id": "acme-index", "tool": "search_graph",
                "invocation_mode": "host_mcp", "request_hash": "sha256:" + "0" * 64,
                "response_hash": ACME_HASH, "started_at": "2026-07-14T08:00:02Z",
                "ended_at": "2026-07-14T08:00:03Z", "status": "success"}),
])


def _evidence(tmp_path, **over):
    source = tmp_path / "svc.py"
    source.write_text("def dispatch():\n    return 1\n", encoding="utf-8")
    sha = "sha256:" + hashlib.sha256(source.read_bytes()).hexdigest()
    doc = {
        "version": 1,
        "change_id": "C-1",
        "provider_observations": [
            _observation(),
        ],
        "graph": {"project": "maika", "graph_commit": "abc123",
                  "repository_head": "abc123", "freshness": "FRESH",
                  "health": "HEALTHY", "observation": UA_HASH},
        "anchors": ["svc.dispatch"],
        "traversals": [
            {"capability": "call_chain_trace", "observations": [UA_HASH],
             "summary": "dispatch -> runner"},
        ],
        "impact": [],
        "support_calls": [],
        "source_verifications": [
            {"file": "svc.py", "sha256": sha, "symbol": "dispatch"},
        ],
        "limitations": [],
        "confidence": "high",
        "complete": True,
    }
    doc.update(over)
    return doc


def _check(tmp_path, request=REQUEST, invocations=INVOCATIONS, **over):
    return gates.validate_trace_evidence(
        yaml.safe_dump(_evidence(tmp_path, **over)),
        request_text=yaml.safe_dump(request),
        invocations_text=invocations,
        repo_root=str(tmp_path),
    )


# ── trace-request ────────────────────────────────────────────────────────────

def test_trace_request_valid():
    result = gates.validate_trace_request(
        yaml.safe_dump(REQUEST), valid_capabilities=CAPS, trigger_vocabulary=TRIGGERS
    )
    assert result.ok, result.reason


def test_trace_request_rejects_unknown_capability():
    bad = {**REQUEST, "required_capabilities": ["mind_reading"]}
    result = gates.validate_trace_request(
        yaml.safe_dump(bad), valid_capabilities=CAPS, trigger_vocabulary=TRIGGERS
    )
    assert not result.ok and "mind_reading" in result.reason


def test_trace_request_rejects_unknown_trigger():
    bad = {**REQUEST, "conditional": {"historical_context_retrieval": {"triggers": ["vibes"]}}}
    result = gates.validate_trace_request(
        yaml.safe_dump(bad), valid_capabilities=CAPS, trigger_vocabulary=TRIGGERS
    )
    assert not result.ok and "vibes" in result.reason


def test_trace_request_rejects_required_conditional_overlap():
    bad = {**REQUEST,
           "required_capabilities": ["historical_context_retrieval", "exact_source_inspection"]}
    result = gates.validate_trace_request(
        yaml.safe_dump(bad), valid_capabilities=CAPS, trigger_vocabulary=TRIGGERS
    )
    assert not result.ok and "both required and conditional" in result.reason


# ── trace-evidence ───────────────────────────────────────────────────────────

def test_trace_evidence_valid_chain(tmp_path):
    result = _check(tmp_path)
    assert result.ok, result.reason


def test_observation_without_invocation_record_fails(tmp_path):
    """Mutation #3: UA trace has no provider invocation."""
    result = _check(tmp_path, invocations="")
    assert not result.ok and "no provider invocation record" in result.reason


def test_observation_without_evidence_envelope_fails(tmp_path):
    result = _check(tmp_path, provider_observations=[
        {"provider_id": "understand-anything", "tool": "trace_call_chain",
         "response_hash": UA_HASH},
    ])
    assert not result.ok and "evidence envelope" in result.reason


def test_observation_provider_mismatch_fails(tmp_path):
    result = _check(tmp_path, provider_observations=[
        _observation(provider="acme-index")])
    assert not result.ok and "disagree" in result.reason


def test_traversal_referencing_unrecorded_observation_fails(tmp_path):
    result = _check(tmp_path, traversals=[
        {"capability": "call_chain_trace",
         "observations": ["sha256:" + "9" * 64], "summary": "ghost"}])
    assert not result.ok and "unrecorded" in result.reason


def test_conditional_capability_without_trigger_fails(tmp_path):
    result = _check(tmp_path, traversals=[
        {"capability": "call_chain_trace", "observations": [UA_HASH], "summary": "x"},
        {"capability": "impact_analysis", "observations": [UA_HASH], "summary": "y"}])
    assert not result.ok and "requires trigger + reason" in result.reason


def test_one_of_group_unsatisfied_fails(tmp_path):
    result = _check(tmp_path, traversals=[], complete=False)
    assert not result.ok and "one_of group structured_trace unsatisfied" in result.reason


def test_required_capability_uncovered_fails(tmp_path):
    result = _check(tmp_path, source_verifications=[], complete=False)
    assert not result.ok and "uncovered" in result.reason


def test_truncated_observation_cannot_claim_complete(tmp_path):
    """Mutation #17: truncated response claims complete."""
    result = _check(tmp_path, provider_observations=[
        _observation(truncated=True)])
    assert not result.ok and "truncated" in result.reason


def test_source_verification_hash_mismatch_fails(tmp_path):
    """Mutation #18: source verification hash missing/stale."""
    result = _check(tmp_path, source_verifications=[
        {"file": "svc.py", "sha256": "sha256:" + "e" * 64, "symbol": "dispatch"}])
    assert not result.ok and "mismatch" in result.reason


def test_graph_conflict_requires_current_source_resolution(tmp_path):
    result = _check(tmp_path, conflicts=[{
        "claim": "A calls B", "providers": ["understand-anything", "current-source"],
        "resolution": "merged_graph_claim", "source_verifications": [],
    }])
    assert not result.ok and "current-source verification" in result.reason


def test_graph_conflict_accepts_referenced_current_source_resolution(tmp_path):
    result = _check(tmp_path, conflicts=[{
        "claim": "A calls B", "providers": ["understand-anything", "current-source"],
        "resolution": "current_source_verified", "source_verifications": ["svc.py"],
    }])
    assert result.ok, result.reason


def test_different_source_revisions_require_refresh_boundary(tmp_path):
    second_hash = "sha256:" + "4" * 64
    second = _observation(response_hash=second_hash, source_revision="def456")
    invocation = json.dumps({
        "trace_id": "t4", "change_id": "C-1", "role": "grounding",
        "provider_id": "understand-anything", "tool": "trace_call_chain",
        "invocation_mode": "host_mcp", "request_hash": REQUEST_HASH,
        "response_hash": second_hash, "started_at": "2026-07-14T08:02:00Z",
        "ended_at": "2026-07-14T08:02:01Z", "status": "success",
    })
    result = _check(tmp_path, invocations=INVOCATIONS + "\n" + invocation,
                    provider_observations=[_observation(), second])
    assert not result.ok and "source revisions" in result.reason


def test_agentmemory_cannot_authorize_exact_traversal(tmp_path):
    memory_hash = "sha256:" + "5" * 64
    memory = _observation(
        provider="agent-memory", tool="memory_recall", response_hash=memory_hash,
        source_revision="unverified", authority="historical_context",
        classification="candidate", canonical=False,
        provider_snapshot={"agent_id": "worker-1", "agent_id_authorizes": False},
    )
    invocation = json.dumps({
        "trace_id": "t5", "change_id": "C-1", "role": "grounding",
        "provider_id": "agent-memory", "tool": "memory_recall",
        "invocation_mode": "host_mcp", "request_hash": REQUEST_HASH,
        "response_hash": memory_hash, "started_at": "2026-07-14T08:03:00Z",
        "ended_at": "2026-07-14T08:03:01Z", "status": "success",
    })
    result = _check(
        tmp_path, invocations=INVOCATIONS + "\n" + invocation,
        provider_observations=[_observation(), memory],
        traversals=[{"capability": "call_chain_trace", "observations": [memory_hash]}],
    )
    assert not result.ok and "cannot support authoritative capability" in result.reason


def test_unhealthy_graph_requires_limitation(tmp_path):
    result = _check(tmp_path, graph={
        "project": "maika", "graph_commit": "abc", "repository_head": "abc",
        "freshness": "UNKNOWN", "health": "UNAVAILABLE",
        "observation": UA_HASH}, complete=False)
    assert not result.ok and "limitations" in result.reason


def test_hand_written_graph_without_probe_observation_fails(tmp_path):
    """Mutation #4: worker claims fresh graph without response hash."""
    result = _check(tmp_path, graph={
        "project": "maika", "graph_commit": "abc123", "repository_head": "abc123",
        "freshness": "FRESH", "health": "HEALTHY"})
    assert not result.ok and "recorded probe observation" in result.reason


def test_prose_limitation_rejected(tmp_path):
    result = _check(tmp_path, limitations=["UA was down, trust me"], complete=False)
    assert not result.ok and "kind + detail" in result.reason


def test_limitation_excuses_one_of_group_with_incomplete_trace(tmp_path):
    result = _check(
        tmp_path, graph={}, provider_observations=[], traversals=[],
        limitations=[{"kind": "provider_unconfigured", "one_of": "structured_trace",
                      "detail": "UA MCP not configured on this host"}],
        complete=False,
    )
    assert result.ok, result.reason


def test_excused_trace_cannot_claim_complete(tmp_path):
    result = _check(
        tmp_path, graph={}, provider_observations=[], traversals=[],
        limitations=[{"kind": "provider_unconfigured", "one_of": "structured_trace",
                      "detail": "UA MCP not configured on this host"}],
        complete=True,
    )
    assert not result.ok and "not complete" in result.reason


def test_unavailable_excusal_requires_failed_probe_record(tmp_path):
    """Codex M11 review: grep-fallback needs a REAL failed probe on record."""
    excusal = [{"kind": "ua_unavailable", "one_of": "structured_trace",
                "detail": "UA down mid-exploration"}]
    result = _check(tmp_path, graph={}, provider_observations=[], traversals=[],
                    limitations=excusal, complete=False)
    assert not result.ok and "recorded failed probe" in result.reason
    failed_invocations = INVOCATIONS + "\n" + json.dumps({
        "trace_id": "t3", "change_id": "C-1", "role": "grounding",
        "provider_id": "understand-anything", "tool": "get_graph_metadata",
        "invocation_mode": "host_mcp", "request_hash": "sha256:" + "0" * 64,
        "response_hash": "sha256:" + "3" * 64,
        "started_at": "2026-07-14T08:01:00Z", "ended_at": "2026-07-14T08:01:05Z",
        "status": "error"})
    result = _check(tmp_path, invocations=failed_invocations, graph={},
                    provider_observations=[], traversals=[],
                    limitations=excusal, complete=False)
    assert result.ok, result.reason


def test_graph_backed_by_errored_probe_rejected(tmp_path):
    """Codex M11 review: an errored probe cannot claim graph health."""
    errored = INVOCATIONS.replace('"status": "success"}', '"status": "error"}', 1)
    result = _check(tmp_path, invocations=errored, complete=False)
    assert not result.ok and "non-success probe" in result.reason


def test_missing_graph_with_ua_limitation_passes(tmp_path):
    result = _check(
        tmp_path, graph={},
        limitations=[{"kind": "ua_unavailable", "detail": "provider down; probe recorded"}],
    )
    assert result.ok, result.reason
