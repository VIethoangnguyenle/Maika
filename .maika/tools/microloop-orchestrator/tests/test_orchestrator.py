"""Unit tests for orchestrator.py: the cross-platform worker runner (Phase 7)
and the exit-code contract + blocked/resume semantics (Phase 4)."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import orchestrator as orch


# ── cross-platform worker runner (Phase 7): shell=False, structured argv,
#    prompt passed verbatim (no shell quoting), optional prompt-file ───────────

def _record_arg_worker(tmp_path):
    """Worker that copies its prompt argument (argv[2]) to a file (argv[1])."""
    w = tmp_path / "record_arg_worker.py"
    w.write_text(
        "import sys\n"
        "from pathlib import Path\n"
        "Path(sys.argv[1]).write_text(sys.argv[2], encoding='utf-8')\n",
        encoding="utf-8",
    )
    return w


def _record_file_worker(tmp_path):
    """Worker that copies the contents of its prompt-file (argv[2]) to a file (argv[1])."""
    w = tmp_path / "record_file_worker.py"
    w.write_text(
        "import sys\n"
        "from pathlib import Path\n"
        "Path(sys.argv[1]).write_text(Path(sys.argv[2]).read_text(encoding='utf-8'), encoding='utf-8')\n",
        encoding="utf-8",
    )
    return w


def _ws(tmp_path):
    ws = tmp_path / "ws"
    (ws / "generated").mkdir(parents=True)
    return ws


def test_worker_runner_passes_prompt_file_as_single_argv_without_shell(tmp_path):
    worker = _record_file_worker(tmp_path)
    out = tmp_path / "seen.txt"
    ws = _ws(tmp_path)
    cfg = {"executable": sys.executable, "args": [str(worker), str(out), "{prompt_file}"]}
    runner = orch.make_worker_runner(cfg, ws, tmp_path)
    # Contains shell metacharacters and newlines: a shell would mangle these.
    tricky = "line1\n\"double\" and 'single' & $HOME | rm -rf / ; `whoami`\nline3"
    code, _out = runner(tricky)
    assert code == 0
    assert out.read_text(encoding="utf-8") == tricky  # survived verbatim -> shell=False


def test_worker_runner_rejects_unknown_placeholder(tmp_path):
    ws = _ws(tmp_path)
    with pytest.raises(ValueError):
        orch.make_worker_runner({"executable": "echo", "args": ["{bogus_placeholder}"]}, ws, tmp_path)


def test_worker_runner_prompt_file_is_written_then_cleaned(tmp_path):
    worker = _record_file_worker(tmp_path)
    out = tmp_path / "seen.txt"
    ws = _ws(tmp_path)
    cfg = {"executable": sys.executable, "args": [str(worker), str(out), "{prompt_file}"]}
    runner = orch.make_worker_runner(cfg, ws, tmp_path)
    code, _out = runner("hello from a prompt file\nsecond line")
    assert code == 0
    assert out.read_text(encoding="utf-8") == "hello from a prompt file\nsecond line"
    assert list((ws / "generated" / "prompts").glob("*")) == []  # cleaned up


def test_worker_runner_substitutes_context_placeholders(tmp_path):
    worker = _record_arg_worker(tmp_path)
    out = tmp_path / "seen.txt"
    ws = _ws(tmp_path)
    cfg = {"executable": sys.executable,
           "args": [str(worker), str(out), "{task_id}", "{prompt_file}"]}
    runner = orch.make_worker_runner(cfg, ws, tmp_path)
    code, _out = runner("ignored")
    assert code == 0
    assert out.read_text(encoding="utf-8") == ws.name  # {task_id} -> workspace name


# ── exit-code contract (Phase 4, §8.1) ───────────────────────────────────────
#   0 ok   1 blocked/runtime   2 config/CLI   3 human   4 budget   5 stale

def _block_reasons():
    import vnext_state as vs
    return vs.BLOCK_REASONS


def test_exit_code_constants_match_contract():
    assert (orch.EXIT_OK, orch.EXIT_BLOCKED, orch.EXIT_CONFIG,
            orch.EXIT_HUMAN, orch.EXIT_BUDGET, orch.EXIT_STALE) == (0, 1, 2, 3, 4, 5)


def test_classify_block_budget():
    reason, code, exit_code = orch._classify_block("small worker-call budget exhausted; escalate or block")
    assert (code, exit_code) == ("budget_exhausted", orch.EXIT_BUDGET)
    assert reason in _block_reasons()


def test_classify_block_stale():
    for text in ("EVIDENCE_UPDATE_REQUEST", "stale capsule: evidence_manifest_hash != current", "stale_plan"):
        reason, code, exit_code = orch._classify_block(text)
        assert (reason, code, exit_code) == ("stale_plan", "stale_contract", orch.EXIT_STALE), text


def test_classify_block_human():
    reason, code, exit_code = orch._classify_block("human confirmation required for docker")
    assert (reason, code, exit_code) == ("user_input", "human_required", orch.EXIT_HUMAN)


def test_classify_block_generic_default():
    reason, code, exit_code = orch._classify_block("worker result invalid")
    assert (code, exit_code) == ("blocked", orch.EXIT_BLOCKED)
    assert reason in _block_reasons()


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
