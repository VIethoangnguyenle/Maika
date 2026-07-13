"""Provider invocation evidence producer + `maika provider record` (plan §7/§12, B3)."""

import importlib.util
import json
from pathlib import Path

import pytest
import yaml

from cli.commands.provider import run_provider
from cli.mcp.integration.base import (
    append_invocation,
    build_invocation_record,
    hash_payload,
)

REPO = Path(__file__).resolve().parents[2]

_G = REPO / ".maika" / "tools" / "gate-check" / "gates.py"
_spec = importlib.util.spec_from_file_location("gates_for_provider_tests", _G)
gates = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(gates)

REAL_REGISTRY = yaml.safe_load(
    (REPO / ".maika" / "config" / "provider-registry.yaml").read_text(encoding="utf-8")
)


def _record(**over):
    base = dict(
        change_id="C-1", role="grounding", provider_id="understand-anything",
        tool="get_graph_metadata", request_payload=b'{"project": "maika"}',
        response_payload=b'{"graph_commit": "abc"}', status="success",
        started_at="2026-07-14T08:00:00Z", ended_at="2026-07-14T08:00:01Z",
    )
    base.update(over)
    return build_invocation_record(**base)


def test_hash_payload_is_deterministic_sha256():
    first = hash_payload(b"payload")
    assert first == hash_payload("payload")
    assert first.startswith("sha256:") and len(first) == 71


def test_built_record_passes_the_gate_with_real_registry():
    record = _record()
    result = gates.validate_provider_invocations(
        json.dumps(record), provider_registry=REAL_REGISTRY
    )
    assert result.ok, result.reason


def test_build_rejects_unknown_status():
    with pytest.raises(ValueError, match="status"):
        _record(status="maybe")


def test_build_rejects_missing_role():
    with pytest.raises(ValueError, match="missing required fields"):
        _record(role="")


def test_append_produces_one_json_line_per_record(tmp_path):
    path = tmp_path / "PROVIDER_INVOCATIONS.jsonl"
    append_invocation(path, _record())
    append_invocation(path, _record(tool="get_graph_stats"))
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[1])["tool"] == "get_graph_stats"


# ── maika provider record (CLI) ──────────────────────────────────────────────

def _target(tmp_path: Path) -> Path:
    target = tmp_path / "proj"
    config = target / ".maika" / "config"
    config.mkdir(parents=True)
    registry = {
        "version": 1,
        "providers": {
            "understand-anything": {
                "display_name": "UA", "kind": "structured_code_graph",
                "tool_contract": {"tools": ["get_graph_metadata"]},
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
    (tmp_path / "req.json").write_text('{"q": 1}', encoding="utf-8")
    (tmp_path / "res.json").write_text('{"a": 2}', encoding="utf-8")
    return target


def _run(tmp_path, **over):
    kwargs = dict(
        target_dir=str(_target(tmp_path)) if "target_dir" not in over else over.pop("target_dir"),
        change_id="C-9", provider_id="understand-anything", tool="get_graph_metadata",
        role="grounding", request_file=str(tmp_path / "req.json"),
        response_file=str(tmp_path / "res.json"),
    )
    kwargs.update(over)
    return run_provider("record", **kwargs)


def test_cli_record_appends_gate_valid_record(tmp_path, capsys):
    assert _run(tmp_path) == 0
    out = capsys.readouterr().out
    assert "request_hash=sha256:" in out
    path = (tmp_path / "proj" / ".maika" / "changes" / "C-9"
            / "exploration" / "PROVIDER_INVOCATIONS.jsonl")
    result = gates.validate_provider_invocations(
        path.read_text(encoding="utf-8"),
        provider_registry=yaml.safe_load(
            (tmp_path / "proj" / ".maika" / "config" / "provider-registry.yaml")
            .read_text(encoding="utf-8")
        ),
    )
    assert result.ok, result.reason


def test_cli_rejects_unknown_provider(tmp_path):
    assert _run(tmp_path, provider_id="graph-oracle") == 1


def test_cli_rejects_tool_outside_snapshot(tmp_path):
    assert _run(tmp_path, tool="hallucinate_graph") == 1


def test_cli_rejects_missing_workspace(tmp_path):
    assert _run(tmp_path, change_id="C-404") == 1


def test_cli_requires_payload_files(tmp_path):
    assert _run(tmp_path, request_file=str(tmp_path / "absent.json")) == 1
