"""End-to-end mechanical TRACE_EVIDENCE production via `maika provider` (M4).

record (UA metadata) -> graph block + observation; record (CBM + trigger) ->
support call; verify-source -> re-hashable verification. The produced file plus
worker-authored traversals must pass the trace-evidence gate against the
recorded invocations.
"""

import importlib.util
import json
from pathlib import Path

import yaml

from cli.commands.provider import run_provider

REPO = Path(__file__).resolve().parents[2]
_G = REPO / ".maika" / "tools" / "gate-check" / "gates.py"
_spec = importlib.util.spec_from_file_location("gates_for_trace_flow", _G)
gates = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(gates)


def _target(tmp_path: Path) -> Path:
    target = tmp_path / "proj"
    config = target / ".maika" / "config"
    config.mkdir(parents=True)
    registry = {
        "version": 1,
        "providers": {
            "understand-anything": {
                "display_name": "UA", "kind": "structured_code_graph",
                "tool_contract": {"tools": ["get_graph_metadata", "trace_call_chain"]},
            },
            "codebase-memory-mcp": {"display_name": "CBM", "kind": "semantic_code_index"},
        },
    }
    config.joinpath("provider-registry.yaml").write_text(
        yaml.safe_dump(registry), encoding="utf-8"
    )
    workspace = target / ".maika" / "changes" / "C-9"
    workspace.mkdir(parents=True)
    workspace.joinpath("CHANGE.yaml").write_text("id: C-9\n", encoding="utf-8")
    (target / "svc.py").write_text("def dispatch():\n    return 1\n", encoding="utf-8")
    return target


def _record(target: Path, tmp_path: Path, *, provider, tool, response: str, **over):
    request_file = tmp_path / "req.json"
    request_file.write_text('{"q": 1}', encoding="utf-8")
    response_file = tmp_path / f"res-{tool}.json"
    response_file.write_text(response, encoding="utf-8")
    return run_provider(
        "record", target_dir=str(target), change_id="C-9", provider_id=provider,
        tool=tool, role="grounding", request_file=str(request_file),
        response_file=str(response_file), **over,
    )


def test_full_mechanical_trace_flow(tmp_path):
    target = _target(tmp_path)
    metadata = json.dumps({
        "project": "proj", "graph_commit": "abc123",
        "repository_head": "abc123", "freshness": "FRESH", "health": "HEALTHY",
    })
    assert _record(target, tmp_path, provider="understand-anything",
                   tool="get_graph_metadata", response=metadata) == 0
    assert _record(target, tmp_path, provider="understand-anything",
                   tool="trace_call_chain", response="dispatch -> runner -> gate") == 0
    assert _record(target, tmp_path, provider="codebase-memory-mcp",
                   tool="semantic_search", response="3 anchors found",
                   trigger="graph_gap", reason="missing consumer edge") == 0
    assert run_provider(
        "verify-source", target_dir=str(target), change_id="C-9",
        file="svc.py", symbol="dispatch",
    ) == 0

    workspace = target / ".maika" / "changes" / "C-9"
    evidence_path = workspace / "exploration" / "TRACE_EVIDENCE.yaml"
    doc = yaml.safe_load(evidence_path.read_text(encoding="utf-8"))
    assert doc["graph"]["graph_commit"] == "abc123"
    assert len(doc["provider_observations"]) == 2
    assert doc["support_calls"][0]["trigger"] == "graph_gap"
    assert doc["source_verifications"][0]["sha256"].startswith("sha256:")

    # Worker authors traversal bound to the recorded observation hash.
    trace_hash = next(
        obs["response_hash"] for obs in doc["provider_observations"]
        if obs["tool"] == "trace_call_chain"
    )
    doc["traversals"] = [{"capability": "call_chain_trace",
                          "observations": [trace_hash],
                          "summary": "dispatch -> runner"}]
    doc["confidence"] = "high"
    doc["complete"] = True
    evidence_path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")

    request = {
        "version": 1, "change_id": "C-9",
        "questions": [{"id": "Q1", "question": "flow?",
                       "required_capabilities": ["call_chain_trace"]}],
        "anchors": [],
        "required_capabilities": ["exact_source_inspection"],
        "one_of": {"structured_trace": ["call_chain_trace"]},
        "conditional": {"semantic_code_search": {"triggers": ["graph_gap"]}},
        "freshness_requirement": "graph_commit_current_or_scoped_stale",
        "source_verification_requirement": "material_exact_facts_source_verified",
    }
    invocations = (workspace / "exploration" / "PROVIDER_INVOCATIONS.jsonl").read_text(
        encoding="utf-8"
    )
    result = gates.validate_trace_evidence(
        evidence_path.read_text(encoding="utf-8"),
        request_text=yaml.safe_dump(request),
        invocations_text=invocations,
        repo_root=str(target),
    )
    assert result.ok, result.reason


def test_cbm_record_without_trigger_warns_and_writes_no_support_call(tmp_path, capsys):
    target = _target(tmp_path)
    assert _record(target, tmp_path, provider="codebase-memory-mcp",
                   tool="semantic_search", response="anchors") == 0
    assert "without --trigger" in capsys.readouterr().out
    evidence_path = (target / ".maika" / "changes" / "C-9"
                     / "exploration" / "TRACE_EVIDENCE.yaml")
    assert not evidence_path.exists()


def test_verify_source_rejects_wrong_symbol(tmp_path):
    target = _target(tmp_path)
    assert run_provider(
        "verify-source", target_dir=str(target), change_id="C-9",
        file="svc.py", symbol="no_such_symbol",
    ) == 1
