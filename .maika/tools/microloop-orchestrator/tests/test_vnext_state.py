# .maika/tools/microloop-orchestrator/tests/test_vnext_state.py
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import vnext_state as vs


def _ws(tmp_path):
    return vs.init_workspace(tmp_path, "demo-change", "small", "Demo change")


def test_init_workspace_creates_minimal_layout(tmp_path):
    ws = _ws(tmp_path)
    assert (ws / "CHANGE.yaml").exists()
    assert (ws / "STATE.yaml").exists()
    assert (ws / "INTENT.md").exists()
    assert (ws / "RECONCILIATION.md").exists()
    assert (ws / "exploration" / "GROUNDING.yaml").exists()
    assert (ws / "exploration" / "EVIDENCE_MANIFEST.yaml").exists()
    for art in ("QUERY_PLAN.yaml", "TOOL_HEALTH.yaml", "CONFLICTS.yaml", "COVERAGE.yaml"):
        assert (ws / "exploration" / art).exists(), art
    for sub in ("generated", "briefs", "results", "reviews"):
        assert (ws / sub).is_dir()
    change = vs._load_yaml(ws / "CHANGE.yaml")
    assert change["change_id"] == "demo-change"
    assert change["class"] == "small"
    assert vs.load_state(ws)["state"] == "INTAKE"


def test_init_rejects_bad_class(tmp_path):
    with pytest.raises(ValueError):
        vs.init_workspace(tmp_path, "x", "gigantic", "t")


def test_transition_legal_and_illegal(tmp_path):
    ws = _ws(tmp_path)
    vs.transition(ws, "PLANNING")            # small: INTAKE -> PLANNING hợp lệ (skip explore/spec class-aware ở W2)
    assert vs.load_state(ws)["state"] == "PLANNING"
    with pytest.raises(ValueError):
        vs.transition(ws, "ARCHIVED")        # PLANNING -> ARCHIVED không có trong ALLOWED


def test_blocked_requires_reason(tmp_path):
    ws = _ws(tmp_path)
    with pytest.raises(ValueError):
        vs.transition(ws, "BLOCKED")         # thiếu blocked metadata
    vs.transition(ws, "BLOCKED", blocked={"reason": "stale_plan", "detail": "x"})
    st = vs.load_state(ws)
    assert st["blocked"]["reason"] == "stale_plan"
