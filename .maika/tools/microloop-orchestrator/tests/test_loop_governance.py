# .maika/tools/microloop-orchestrator/tests/test_loop_governance.py
"""Change-loop governance: which decisions are automatic vs need human approval,
and the trusted-approval record binding change/loop/decision (W7)."""
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import loop_governance as gov


def _loop(trigger, root_cause, loop_id="LOOP-C-1-001"):
    return {
        "loop_id": loop_id, "change_id": "C-1",
        "trigger": {"type": trigger, "evidence_refs": []},
        "root_cause": root_cause, "route": "x",
    }


def test_scope_escape_requires_human_approval():
    d = gov.decision_for(_loop("scope_escape", "implementation_gap"))
    assert d["type"] == "scope_expansion"
    assert d["requires_approval"] is True
    assert d["id"] == "LOOP-C-1-001-D1"


def test_repeated_failure_is_automatic():
    d = gov.decision_for(_loop("repeated_failure", "verification_gap"))
    assert d["type"] == "local_code_correction"
    assert d["requires_approval"] is False


def test_unknown_trigger_defaults_to_requiring_approval():
    d = gov.decision_for(_loop("mystery", None))
    assert d["requires_approval"] is True


def _write_approval(path, **overrides):
    doc = {
        "version": 1, "source": "cli-user-action", "change_id": "C-1",
        "loop_id": "LOOP-C-1-001", "decision_id": "LOOP-C-1-001-D1",
        "decision_hash": gov.loop_decision_hash("C-1", "LOOP-C-1-001", "LOOP-C-1-001-D1"),
    }
    doc.update(overrides)
    path.write_text(yaml.safe_dump(doc), encoding="utf-8")


def test_trusted_approval_roundtrip(tmp_path):
    p = tmp_path / "a.yaml"
    _write_approval(p)
    assert gov.trusted_loop_approval_matches(p, "C-1", "LOOP-C-1-001", "LOOP-C-1-001-D1") is True


def test_agent_authored_source_rejected(tmp_path):
    p = tmp_path / "a.yaml"
    _write_approval(p, source="agent")
    assert gov.trusted_loop_approval_matches(p, "C-1", "LOOP-C-1-001", "LOOP-C-1-001-D1") is False


def test_tampered_hash_rejected(tmp_path):
    p = tmp_path / "a.yaml"
    _write_approval(p, decision_hash="sha256:deadbeef")
    assert gov.trusted_loop_approval_matches(p, "C-1", "LOOP-C-1-001", "LOOP-C-1-001-D1") is False


def test_wrong_decision_id_rejected(tmp_path):
    p = tmp_path / "a.yaml"
    _write_approval(p)  # bound to D1
    assert gov.trusted_loop_approval_matches(p, "C-1", "LOOP-C-1-001", "OTHER-D9") is False
