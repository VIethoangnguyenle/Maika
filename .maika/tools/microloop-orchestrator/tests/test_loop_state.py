# .maika/tools/microloop-orchestrator/tests/test_loop_state.py
"""LOOP.yaml lifecycle + the one-active-change-loop invariant (via STATE.yaml)."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import loop_state
import vnext_state as vs


def _ws(tmp_path):
    vs.init_workspace(tmp_path / "changes", "C-1", "small", "t")
    return tmp_path / "changes" / "C-1"


def test_create_loop_writes_schema_and_marks_active(tmp_path):
    ws = _ws(tmp_path)
    loop = loop_state.create_loop(ws, "C-1", "scope_escape", ["src/x.py"])
    assert loop["loop_id"] == "LOOP-C-1-001"
    assert loop["change_id"] == "C-1"
    assert loop["level"] == "change"
    assert loop["state"] == "diagnosing"
    assert loop["trigger"] == {"type": "scope_escape", "evidence_refs": ["src/x.py"]}
    assert loop["root_cause"] is None
    assert loop["route"] is None
    assert loop["retry_budget"] == {"used": 0, "maximum": 2}
    assert (ws / "LOOP.yaml").exists()
    assert vs.active_loop_id(ws) == "LOOP-C-1-001"


def test_second_create_denied_one_active_invariant(tmp_path):
    ws = _ws(tmp_path)
    loop_state.create_loop(ws, "C-1", "scope_escape", ["src/x.py"])
    with pytest.raises(loop_state.LoopExists):
        loop_state.create_loop(ws, "C-1", "repeated_failure", ["retry budget exhausted"])


def test_record_diagnosis_moves_to_routed(tmp_path):
    ws = _ws(tmp_path)
    loop_state.create_loop(ws, "C-1", "scope_escape", ["src/x.py"])
    loop = loop_state.record_diagnosis(ws, "implementation_gap", "implementer")
    assert loop["state"] == "routed"
    assert loop["root_cause"] == "implementation_gap"
    assert loop["route"] == "implementer"


def test_close_clears_active_and_allows_reopen(tmp_path):
    ws = _ws(tmp_path)
    loop_state.create_loop(ws, "C-1", "scope_escape", ["src/x.py"])
    closed = loop_state.close_loop(ws)
    assert closed["state"] == "closed"
    assert vs.active_loop_id(ws) is None
    # invariant is per-active-loop, so a fresh loop may open after close
    reopened = loop_state.create_loop(ws, "C-1", "repeated_failure", ["retry budget exhausted"])
    assert reopened["state"] == "diagnosing"
