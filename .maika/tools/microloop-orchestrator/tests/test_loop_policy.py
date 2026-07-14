# .maika/tools/microloop-orchestrator/tests/test_loop_policy.py
"""Change-loop policy: which observed friction crosses the micro-retry boundary.

A first/within-budget verification failure stays a micro loop (no LOOP.yaml); a
confirmed scope escape or a retry-budget-exhausted failure opens a change loop.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import loop_policy


def test_scope_escape_with_outside_files_opens():
    ok, reason = loop_policy.should_open_loop(
        {"trigger": "scope_escape", "outside_scope": ["src/x.py"]}
    )
    assert ok is True
    assert reason


def test_scope_escape_without_outside_files_stays_micro():
    ok, _ = loop_policy.should_open_loop({"trigger": "scope_escape", "outside_scope": []})
    assert ok is False


def test_repeated_failure_within_budget_stays_micro():
    ok, _ = loop_policy.should_open_loop(
        {"trigger": "repeated_failure", "retries_exhausted": False}
    )
    assert ok is False


def test_repeated_failure_after_budget_opens():
    ok, reason = loop_policy.should_open_loop(
        {"trigger": "repeated_failure", "retries_exhausted": True}
    )
    assert ok is True
    assert reason


def test_unwired_trigger_does_not_open():
    # human_correction / stale_contract are deferred — no policy, no loop.
    ok, _ = loop_policy.should_open_loop({"trigger": "human_correction"})
    assert ok is False
