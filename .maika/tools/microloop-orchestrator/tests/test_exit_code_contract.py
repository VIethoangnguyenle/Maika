"""Phase 4 — exit-code contract (plan §8.1) and blocked semantics.

  0 success   1 runtime/blocked   2 config/CLI   3 human required
  4 budget exhausted   5 stale artifact/contract
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import orchestrator as orch


def test_exit_code_constants_match_contract():
    assert orch.EXIT_OK == 0
    assert orch.EXIT_BLOCKED == 1
    assert orch.EXIT_CONFIG == 2
    assert orch.EXIT_HUMAN == 3
    assert orch.EXIT_BUDGET == 4
    assert orch.EXIT_STALE == 5


def test_classify_block_budget():
    reason, code, exit_code = orch._classify_block("small worker-call budget exhausted; escalate or block")
    assert code == "budget_exhausted"
    assert exit_code == orch.EXIT_BUDGET
    assert reason in orch_block_reasons()


def test_classify_block_stale():
    for text in ("EVIDENCE_UPDATE_REQUEST", "stale capsule: evidence_manifest_hash != current", "stale_plan"):
        reason, code, exit_code = orch._classify_block(text)
        assert code == "stale_contract", text
        assert exit_code == orch.EXIT_STALE, text
        assert reason == "stale_plan"


def test_classify_block_human():
    reason, code, exit_code = orch._classify_block("human confirmation required for docker")
    assert code == "human_required"
    assert exit_code == orch.EXIT_HUMAN
    assert reason == "user_input"


def test_classify_block_generic_default():
    reason, code, exit_code = orch._classify_block("worker result invalid")
    assert code == "blocked"
    assert exit_code == orch.EXIT_BLOCKED
    assert reason in orch_block_reasons()


def orch_block_reasons():
    import vnext_state as vs
    return vs.BLOCK_REASONS


def _blocked_workspace(tmp_path):
    import vnext_state as vs
    fw = tmp_path / ".maika"
    (fw / "profiles").mkdir(parents=True)
    (fw / "profiles" / "execution-mode.yaml").write_text("workflow_engine: vnext\n", encoding="utf-8")
    ws = vs.init_workspace(fw / "changes", "demo", "standard", "t")
    vs.transition(ws, "PLANNING")
    vs.transition(ws, "PLAN_REVIEW")
    vs.transition(ws, "EXECUTING")
    vs.transition(ws, "BLOCKED", blocked={"reason": "verification", "code": "blocked",
                                          "resume_state": "EXECUTING"})
    return ws


def test_resume_transitions_blocked_to_resume_state(tmp_path):
    import vnext_state as vs
    ws = _blocked_workspace(tmp_path)
    rc = orch.main(["vnext-resume", "--workspace", str(ws), "--repo-root", str(tmp_path)])
    assert rc == orch.EXIT_OK
    assert vs.load_state(ws)["state"] == "EXECUTING"


def test_resume_refused_when_not_blocked(tmp_path):
    import vnext_state as vs
    ws = _blocked_workspace(tmp_path)
    orch.main(["vnext-resume", "--workspace", str(ws), "--repo-root", str(tmp_path)])  # -> EXECUTING
    rc = orch.main(["vnext-resume", "--workspace", str(ws), "--repo-root", str(tmp_path)])
    assert rc == orch.EXIT_CONFIG
    assert vs.load_state(ws)["state"] == "EXECUTING"
