"""provider-invocations gate — host-delegated MCP call records (plan §7/§12, B3).

Standalone like the other gate tests: records are inline dicts, the provider
registry is the real repository registry, and no cli package import is needed.
"""
import importlib.util
import json
from pathlib import Path

import yaml

_G = Path(__file__).resolve().parents[1] / "gates.py"
spec = importlib.util.spec_from_file_location("gates", _G)
gates = importlib.util.module_from_spec(spec); spec.loader.exec_module(gates)

REGISTRY = yaml.safe_load(
    (Path(__file__).resolve().parents[3] / "config" / "provider-registry.yaml")
    .read_text(encoding="utf-8")
)

GOOD = {
    "trace_id": "t-1",
    "change_id": "C-1",
    "role": "grounding",
    "provider_id": "understand-anything",
    "tool": "get_graph_metadata",
    "invocation_mode": "host_mcp",
    "request_hash": "sha256:" + "a" * 64,
    "response_hash": "sha256:" + "b" * 64,
    "started_at": "2026-07-14T08:00:00Z",
    "ended_at": "2026-07-14T08:00:01Z",
    "status": "success",
    "normalized_artifact": "",
    "trigger": "",
    "reason": "",
}


def _text(*records):
    return "\n".join(json.dumps(record) for record in records) + "\n"


def _fail(record_over: dict):
    record = {**GOOD, **record_over}
    return gates.validate_provider_invocations(_text(record), provider_registry=REGISTRY)


def test_valid_record_passes():
    result = gates.validate_provider_invocations(_text(GOOD), provider_registry=REGISTRY)
    assert result.ok, result.reason


def test_empty_file_fails():
    result = gates.validate_provider_invocations("", provider_registry=REGISTRY)
    assert not result.ok
    assert "no provider invocation records" in result.reason


def test_invalid_json_line_fails():
    result = gates.validate_provider_invocations("{broken", provider_registry=REGISTRY)
    assert not result.ok


def test_missing_response_hash_fails():
    result = _fail({"response_hash": ""})
    assert not result.ok and "missing fields" in result.reason


def test_malformed_hash_fails():
    result = _fail({"request_hash": "sha256:short"})
    assert not result.ok and "sha256:<64 hex>" in result.reason


def test_unknown_provider_fails():
    result = _fail({"provider_id": "graph-oracle"})
    assert not result.ok and "unknown provider" in result.reason


def test_tool_outside_tested_snapshot_fails():
    """Mutation #16 (plan §21): unknown provider tool appears."""
    result = _fail({"tool": "hallucinate_graph"})
    assert not result.ok and "tested tool snapshot" in result.reason


def test_cbm_without_snapshot_accepts_any_tool_name():
    """CBM tool names are deliberately unverified (no snapshot in registry)."""
    result = _fail({"provider_id": "codebase-memory-mcp", "tool": "semantic_search"})
    assert result.ok, result.reason


def test_non_host_mcp_mode_fails():
    result = _fail({"invocation_mode": "self_reported"})
    assert not result.ok and "host_mcp" in result.reason


def test_unknown_status_fails():
    result = _fail({"status": "probably-fine"})
    assert not result.ok


def test_bad_timestamp_fails():
    result = _fail({"started_at": "yesterday"})
    assert not result.ok and "ISO-8601" in result.reason


def test_gate_registered_in_cli_validators():
    cli_path = Path(__file__).resolve().parents[1] / "cli.py"
    spec_cli = importlib.util.spec_from_file_location("gate_cli", cli_path)
    gate_cli = importlib.util.module_from_spec(spec_cli); spec_cli.loader.exec_module(gate_cli)
    assert gate_cli.VALIDATORS["provider-invocations"] == "validate_provider_invocations"
