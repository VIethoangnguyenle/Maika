"""`maika loop status|inspect|approve|reject|resume|close --id <change>` (W7).

Approval reuses the trusted-approval record (source: cli-user-action + bound
hash); a scope-expansion decision needs it, an in-scope correction does not.
Resume returns the blocked change to its recorded resume state; close needs an
evidence-backed resolution (resume first) or an explicit --proposal-only.
"""

import shutil
import sys
from pathlib import Path

from cli.commands.loop import run_loop

REPO = Path(__file__).resolve().parents[2]
SRC_TOOLS = REPO / ".maika" / "tools" / "microloop-orchestrator"
DECISION_ID = "LOOP-C-1-001-D1"


def _target(tmp_path, trigger="scope_escape", root_cause="implementation_gap",
            route="implementer", blocked_resume="INTAKE"):
    target = tmp_path / "proj"
    fr = target / ".maika"
    (fr / "tools").mkdir(parents=True)
    shutil.copytree(SRC_TOOLS, fr / "tools" / "microloop-orchestrator")
    (fr / "resolved-config.yaml").write_text(
        "resolved:\n  platform: generic\n  framework_root: .maika\n", encoding="utf-8"
    )
    if str(SRC_TOOLS) not in sys.path:
        sys.path.insert(0, str(SRC_TOOLS))
    import loop_state as ls
    import vnext_state as vs

    ch = fr / "changes"
    vs.init_workspace(ch, "C-1", "small", "t")
    ws = ch / "C-1"
    evidence = ["src/evil.py"] if trigger == "scope_escape" else ["retry budget exhausted"]
    ls.create_loop(ws, "C-1", trigger, evidence)
    ls.record_diagnosis(ws, root_cause, route)
    vs.transition(ws, "EXECUTING")
    vs.transition(ws, "BLOCKED", blocked={"reason": "verification", "resume_state": blocked_resume})
    return target, ws, vs, ls


def test_status_prints_loop_and_decision(tmp_path, capsys):
    target, *_ = _target(tmp_path)
    assert run_loop("status", str(target), "C-1") == 0
    out = capsys.readouterr().out
    assert "LOOP-C-1-001" in out
    assert "requires_approval=True" in out


def test_resume_refused_without_approval(tmp_path):
    target, ws, vs, _ = _target(tmp_path)  # scope_escape → requires approval
    assert run_loop("resume", str(target), "C-1") == 3
    assert vs.load_state(ws)["state"] == "BLOCKED"  # unchanged


def test_approve_then_resume_restores_recorded_state(tmp_path):
    target, ws, vs, _ = _target(tmp_path, blocked_resume="INTAKE")
    assert run_loop("approve", str(target), "C-1", decision_id=DECISION_ID) == 0
    assert run_loop("resume", str(target), "C-1") == 0
    assert vs.load_state(ws)["state"] == "INTAKE"


def test_tampered_approval_rejected_on_resume(tmp_path):
    target, ws, vs, _ = _target(tmp_path)
    approval = ws / "approvals" / f"{DECISION_ID}.yaml"
    approval.parent.mkdir(parents=True, exist_ok=True)
    approval.write_text(  # agent-authored + wrong hash
        "version: 1\nsource: agent\nchange_id: C-1\nloop_id: LOOP-C-1-001\n"
        f"decision_id: {DECISION_ID}\ndecision_hash: sha256:deadbeef\n",
        encoding="utf-8",
    )
    assert run_loop("resume", str(target), "C-1") == 3
    assert vs.load_state(ws)["state"] == "BLOCKED"


def test_close_requires_resolution_or_proposal_only(tmp_path):
    target, ws, vs, ls = _target(tmp_path)
    assert run_loop("close", str(target), "C-1") == 2          # still BLOCKED, no flag
    assert run_loop("close", str(target), "C-1", proposal_only=True) == 0
    assert ls.load_loop(ws)["state"] == "closed"
    assert vs.active_loop_id(ws) is None


def test_automatic_decision_resumes_without_approval(tmp_path):
    # repeated_failure → local_code_correction → automatic (no approval needed)
    target, ws, vs, _ = _target(tmp_path, trigger="repeated_failure",
                                root_cause="verification_gap", route="verification-specialist",
                                blocked_resume="EXECUTING")
    assert run_loop("resume", str(target), "C-1") == 0
    assert vs.load_state(ws)["state"] == "EXECUTING"


def test_recursive_open_denied_via_state(tmp_path):
    # one active loop invariant holds at the state layer
    target, ws, vs, ls = _target(tmp_path)
    import pytest
    with pytest.raises(ls.LoopExists):
        ls.create_loop(ws, "C-1", "repeated_failure", ["x"])
