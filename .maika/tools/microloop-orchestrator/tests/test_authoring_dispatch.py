# tests/test_authoring_dispatch.py — PR 10: public actions execute skills.
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import vnext_dispatch as vd
import vnext_state as vs


def _ws(tmp_path, klass="standard"):
    return vs.init_workspace(tmp_path / "changes", "C-1", klass, "demo change")


def _ok_validator(ws):
    return True, ""


def _fail_validator(ws):
    return False, "synthetic gate failure"


def test_grounding_dispatch_starts_exploration_and_transitions(tmp_path):
    ws = _ws(tmp_path)
    prompts = []

    def runner(prompt):
        prompts.append(prompt)
        return 0, "done"

    result = vd.run_authoring_dispatch(ws, "grounding", runner, vs, _ok_validator)
    assert result["ok"], result
    assert result["state"] == "RECONCILING"
    assert "DISPATCH_TYPE: grounding" in prompts[0]
    assert "exploration/GROUNDING.yaml" in prompts[0]
    log = (ws / "generated" / "DISPATCH_LOG.jsonl").read_text(encoding="utf-8")
    assert '"dispatch_type": "grounding"' in log


def test_gate_failure_blocks_transition(tmp_path):
    ws = _ws(tmp_path)

    result = vd.run_authoring_dispatch(ws, "grounding", lambda p: (0, ""), vs, _fail_validator)
    assert not result["ok"]
    assert "synthetic gate failure" in result["reason"]
    assert vs.load_state(ws)["state"] == "EXPLORING"  # dispatched but NOT advanced


def test_wrong_state_refused_without_worker_call(tmp_path):
    ws = _ws(tmp_path)
    calls = []

    result = vd.run_authoring_dispatch(ws, "planning", lambda p: calls.append(p) or (0, ""),
                                       vs, _ok_validator)
    assert not result["ok"]
    assert "wrong state" in result["reason"]
    assert calls == []


def test_spec_dispatch_moves_brainstorming_to_spec_review(tmp_path):
    ws = _ws(tmp_path)
    vs.transition(ws, "EXPLORING")
    vs.transition(ws, "RECONCILING")
    vs.transition(ws, "BRAINSTORMING")

    def runner(prompt):
        (ws / "SPEC.md").write_text("# Spec\n", encoding="utf-8")
        return 0, "ok"

    result = vd.run_authoring_dispatch(ws, "spec", runner, vs, _ok_validator)
    assert result["ok"]
    assert result["state"] == "SPEC_REVIEW"


def test_brainstorming_is_optional_and_stays_in_state(tmp_path):
    ws = _ws(tmp_path)
    vs.transition(ws, "EXPLORING")
    vs.transition(ws, "RECONCILING")
    vs.transition(ws, "BRAINSTORMING")

    result = vd.run_authoring_dispatch(ws, "brainstorming", lambda p: (0, ""), vs, _ok_validator)
    assert result["ok"]
    assert result["state"] == "BRAINSTORMING"


def test_missing_output_is_refused(tmp_path):
    ws = _ws(tmp_path)
    vs.transition(ws, "EXPLORING")
    vs.transition(ws, "RECONCILING")
    vs.transition(ws, "BRAINSTORMING")
    (ws / "RECONCILIATION.md").unlink()

    result = vd.run_authoring_dispatch(ws, "brainstorming", lambda p: (1, "worker crashed"),
                                       vs, _ok_validator)
    assert not result["ok"]
    assert "RECONCILIATION.md" in result["reason"]


def test_markdown_trace_block_extraction():
    text = "# R\n\n## Knowledge Trace\n\n```yaml\ndecision:\n  id: D-1\n```\n"
    block = vd.markdown_trace_block(text)
    assert yaml.safe_load(block)["decision"]["id"] == "D-1"
    assert vd.markdown_trace_block("# no trace\n") is None
