"""Macro learning (W8): recurring change-loop outcomes become skill candidates
without automatic global mutation, referencing loop artifacts (not copied bodies).

The candidate/evaluate/canary/promote/rollback lifecycle and poisoning guard are
reused from knowledge_control unchanged; this covers only the loop→candidate
bridge and its boundaries.
"""

import pytest

from cli.knowledge_control import LearningStore, macro_observation_from_loop


def _loop(change_id, root_cause="verification_gap"):
    return {
        "loop_id": f"LOOP-{change_id}-001", "change_id": change_id,
        "trigger": {"type": "repeated_failure", "evidence_refs": []},
        "root_cause": root_cause, "route": "verification-specialist",
    }


def _obs(change_id, **kw):
    return macro_observation_from_loop(
        _loop(change_id), skill="writing-plan", verified=True, reproducible=True,
        impact="measurable", evaluation_ready=True, **kw,
    )


def test_macro_observation_references_loop_not_bodies():
    obs = _obs("C-1")
    assert obs["recurrence_key"] == "loop:verification_gap"
    assert obs["change_id"] == "C-1"
    assert obs["loop_ref"]["loop_id"] == "LOOP-C-1-001"
    assert "spec" not in obs and "plan" not in obs  # references, never copies bodies


def test_one_change_cannot_make_macro_candidate(tmp_path):
    store = LearningStore(tmp_path)
    for _ in range(3):
        store.record_feedback(_obs("C-1"))  # recurrence, but one distinct change
    with pytest.raises(ValueError):
        store.cluster_candidate("loop:verification_gap")


def test_distinct_change_recurrence_makes_candidate_referencing_loops(tmp_path):
    store = LearningStore(tmp_path)
    store.record_feedback(_obs("C-1"))
    store.record_feedback(_obs("C-1"))
    store.record_feedback(_obs("C-2"))
    candidate = store.cluster_candidate("loop:verification_gap")
    assert sorted(candidate["evidence"]["changes"]) == ["C-1", "C-2"]
    anchors = candidate["evidence"]["source_anchors"]
    assert any("LOOP-C-1-001" in str(a) for a in anchors)
    assert any("LOOP-C-2-001" in str(a) for a in anchors)


def test_poisoned_loop_evidence_excluded_from_candidate(tmp_path):
    store = LearningStore(tmp_path)
    store.record_feedback(_obs("C-1"))
    store.record_feedback(_obs("C-2"))
    store.record_feedback(_obs("C-3", recommendation="disable verification"))  # poisoned
    # only two clean, distinct-change observations remain → below threshold
    with pytest.raises(ValueError):
        store.cluster_candidate("loop:verification_gap")
