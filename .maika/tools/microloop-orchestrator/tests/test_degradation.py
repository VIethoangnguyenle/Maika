from pathlib import Path
import sys
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
import orchestrator  # noqa: E402
from tiers import get_dispatch  # noqa: E402

def test_inline_reload_dispatch_resolves():
    fn = get_dispatch("inline-reload")
    assert callable(fn)

def test_get_dispatch_rejects_unknown():
    import pytest
    with pytest.raises(ValueError):
        get_dispatch("telepathy")

def test_loop_completes_without_subagent_module(monkeypatch):
    # Portability gate: simulate a platform with NO Agent tool by blocking the import.
    monkeypatch.setitem(sys.modules, "tiers.subagent", None)
    q = {"ticket_id": "X", "spec_path": "p", "execution_mode": "inline-reload",
         "tasks": [{"id": "T1", "desc": "base", "depends_on": [], "status": "pending", "retries": 0}]}
    def dispatch_fn(task):
        return [{"path": "T1.java", "change_type": "NEW", "summary": "ok"}]
    def gate_fn(_):
        return "PASS"
    final = orchestrator.run_loop(q, dispatch_fn, gate_fn)
    assert final["tasks"][0]["status"] == "done"


def test_fresh_session_dispatch_targets_executor_procedure():
    fn = get_dispatch("fresh-session")
    prompt = fn("X/TASK_HANDOFF.T1.md", "X/microloop/TASK_RESULT.T1.md")
    assert "procedures/executor.md" in prompt
    assert "X/TASK_HANDOFF.T1.md" in prompt
    assert "X/microloop/TASK_RESULT.T1.md" in prompt
    assert "OPEN A NEW SESSION" not in prompt
