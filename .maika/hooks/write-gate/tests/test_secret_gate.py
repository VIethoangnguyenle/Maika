"""RED-first tests for secret-gate integration inside write_gate.py.

Covers: scope (framework-artifact only), block+reason, masked degradation
record, path_glob allowlist, on_error fail mode, and main() wiring.
"""
import importlib.util
import json
from pathlib import Path

import pytest


MOD = Path(__file__).resolve().parents[1] / "write_gate.py"
spec = importlib.util.spec_from_file_location("write_gate", MOD)
wg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wg)


AWS_KEY = "AKIAIOSFODNN7EXAMPLE"
FR = ".maika"


def _write_payload(rel_path: str, content: str) -> dict:
    return {"tool_name": "Write", "tool_input": {"file_path": rel_path, "content": content}}


def _target(root: Path, rel: str) -> Path:
    return (root / rel).resolve()


def test_blocks_secret_in_framework_artifact(tmp_path):
    rel = ".maika/knowledge/active/NOTES.md"
    payload = _write_payload(rel, f"log line\naws_key = {AWS_KEY}\n")
    d = wg.evaluate_secret_gate(
        tmp_path, [_target(tmp_path, rel)], payload,
        framework_root=FR, config={"enabled": True, "on_error": "block"},
    )
    assert d is not None and not d.ok
    assert "aws-access-key" in d.reason
    assert AWS_KEY not in d.reason  # only masked preview may appear


def test_allows_clean_framework_artifact(tmp_path):
    rel = ".maika/knowledge/active/NOTES.md"
    payload = _write_payload(rel, "just some ordinary notes, nothing here\n")
    d = wg.evaluate_secret_gate(
        tmp_path, [_target(tmp_path, rel)], payload,
        framework_root=FR, config={"enabled": True},
    )
    assert d is None


def test_ignores_non_framework_target(tmp_path):
    rel = "src/App.py"
    payload = _write_payload(rel, f"KEY = '{AWS_KEY}'\n")
    d = wg.evaluate_secret_gate(
        tmp_path, [_target(tmp_path, rel)], payload,
        framework_root=FR, config={"enabled": True},
    )
    assert d is None  # out of scope: application source, not a Maika artifact


def test_respects_path_glob_allowlist(tmp_path):
    rel = "docs/superpowers/specs/example.md"
    payload = _write_payload(rel, 'api_key = "s3cr3t_value_1234567890"\n')
    config = {
        "enabled": True,
        "allowlist": [
            {"path_glob": "docs/superpowers/specs/**",
             "rule_ids": ["generic-assignment"],
             "reason": "documented example tokens in spec fixtures"},
        ],
    }
    d = wg.evaluate_secret_gate(
        tmp_path, [_target(tmp_path, rel)], payload, framework_root=FR, config=config,
    )
    assert d is None


def test_writes_masked_degradation_record(tmp_path):
    rel = ".maika/knowledge/active/NOTES.md"
    payload = _write_payload(rel, f"aws_key = {AWS_KEY}\n")
    wg.evaluate_secret_gate(
        tmp_path, [_target(tmp_path, rel)], payload,
        framework_root=FR, config={"enabled": True, "on_error": "block"},
    )
    record = tmp_path / FR / "logs" / "secret-gate.jsonl"
    assert record.exists()
    text = record.read_text(encoding="utf-8")
    assert "aws-access-key" in text
    assert AWS_KEY not in text  # raw secret must never be persisted
    row = json.loads(text.strip().splitlines()[-1])
    assert row["gate"] == "secret-gate"
    assert row["action"] == "blocked"


def test_on_error_block_fails_closed(tmp_path, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("scanner exploded")
    monkeypatch.setattr(wg, "_secret_scan", boom)
    rel = ".maika/knowledge/active/NOTES.md"
    payload = _write_payload(rel, f"aws_key = {AWS_KEY}\n")
    d = wg.evaluate_secret_gate(
        tmp_path, [_target(tmp_path, rel)], payload,
        framework_root=FR, config={"enabled": True, "on_error": "block"},
    )
    assert d is not None and not d.ok


def test_on_error_allow_fails_open(tmp_path, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("scanner exploded")
    monkeypatch.setattr(wg, "_secret_scan", boom)
    rel = ".maika/knowledge/active/NOTES.md"
    payload = _write_payload(rel, f"aws_key = {AWS_KEY}\n")
    d = wg.evaluate_secret_gate(
        tmp_path, [_target(tmp_path, rel)], payload,
        framework_root=FR, config={"enabled": True, "on_error": "allow"},
    )
    assert d is None


def test_disabled_config_is_noop(tmp_path):
    rel = ".maika/knowledge/active/NOTES.md"
    payload = _write_payload(rel, f"aws_key = {AWS_KEY}\n")
    d = wg.evaluate_secret_gate(
        tmp_path, [_target(tmp_path, rel)], payload,
        framework_root=FR, config={"enabled": False},
    )
    assert d is None


def test_main_honors_secret_gate_block(monkeypatch):
    # Isolate wiring: base write-gate allows, secret-gate blocks → exit 2 (claude).
    monkeypatch.setattr(wg, "evaluate_write", lambda *a, **k: wg.Decision(True))
    monkeypatch.setattr(
        wg, "evaluate_secret_gate",
        lambda *a, **k: wg.Decision(False, "[R-Guard-3] secret-gate: blocked"),
    )
    payload = _write_payload(".maika/knowledge/active/NOTES.md", "x")
    code = wg.main(["--runtime", "claude"], stdin_text=json.dumps(payload))
    assert code == 2
