# .maika/tools/microloop-orchestrator/tests/test_loop_engineer.py
"""Loop Engineer: observe → policy → open → diagnose(root cause) → route(role).

The engineer only diagnoses and routes; it never writes spec/plan/code. It opens
at most one change loop per change and refuses to recurse into a second.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import loop_engineer
import loop_state
import vnext_state as vs


def _ws(tmp_path):
    vs.init_workspace(tmp_path / "changes", "C-1", "small", "t")
    return tmp_path / "changes" / "C-1"


def test_scope_escape_opens_and_routes_to_implementer(tmp_path):
    ws = _ws(tmp_path)
    loop = loop_engineer.observe(ws, "C-1", {
        "trigger": "scope_escape", "outside_scope": ["src/x.py"],
        "evidence_refs": ["src/x.py"],
    })
    assert loop is not None
    assert loop["state"] == "routed"
    assert loop["root_cause"] == "implementation_gap"
    assert loop["route"] == "implementer"
    assert loop["trigger"]["evidence_refs"] == ["src/x.py"]
    assert vs.active_loop_id(ws) == loop["loop_id"]


def test_repeated_failure_after_budget_routes_to_verifier(tmp_path):
    ws = _ws(tmp_path)
    loop = loop_engineer.observe(ws, "C-1", {
        "trigger": "repeated_failure", "retries_exhausted": True,
        "evidence_refs": ["retry budget exhausted"],
    })
    assert loop is not None
    assert loop["root_cause"] == "verification_gap"
    assert loop["route"] == "verification-specialist"


def test_first_failure_creates_no_loop(tmp_path):
    ws = _ws(tmp_path)
    loop = loop_engineer.observe(ws, "C-1", {
        "trigger": "repeated_failure", "retries_exhausted": False, "evidence_refs": [],
    })
    assert loop is None
    assert not (ws / "LOOP.yaml").exists()
    assert vs.active_loop_id(ws) is None


def test_recursive_open_denied(tmp_path):
    ws = _ws(tmp_path)
    loop_engineer.observe(ws, "C-1", {
        "trigger": "scope_escape", "outside_scope": ["a.py"], "evidence_refs": ["a.py"],
    })
    second = loop_engineer.observe(ws, "C-1", {
        "trigger": "repeated_failure", "retries_exhausted": True, "evidence_refs": ["x"],
    })
    assert second is None  # one active loop invariant holds
    assert loop_state.load_loop(ws)["trigger"]["type"] == "scope_escape"
