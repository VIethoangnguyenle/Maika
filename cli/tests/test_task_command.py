"""Tests for the public `maika task` vNext command wrapper."""

import json
import sys
from pathlib import Path

import yaml

from cli.commands.task import run_task


def _target(tmp_path):
    root = tmp_path / "proj"
    fw = root / ".maika"
    tool = fw / "tools" / "microloop-orchestrator"
    profiles = fw / "profiles"
    tool.mkdir(parents=True)
    profiles.mkdir(parents=True)
    (profiles / "execution-mode.yaml").write_text("workflow_engine: vnext\n", encoding="utf-8")
    (fw / "resolved-config.yaml").write_text(
        "resolved:\n"
        "  platform: generic\n"
        "  framework_root: .maika\n"
        "  mcps: []\n"
        "  language: python\n"
        "  framework_version: '3.0'\n",
        encoding="utf-8",
    )
    script = tool / "orchestrator.py"
    script.write_text(
        "import json, pathlib, sys\n"
        "path = pathlib.Path('calls.jsonl')\n"
        "path.open('a').write(json.dumps(sys.argv[1:]) + '\\n')\n"
        "if sys.argv[1] == 'vnext-init':\n"
        "    root = pathlib.Path(sys.argv[sys.argv.index('--changes-root') + 1])\n"
        "    cid = sys.argv[sys.argv.index('--id') + 1]\n"
        "    ws = root / cid\n"
        "    ws.mkdir(parents=True, exist_ok=True)\n"
        "    (ws / 'STATE.yaml').write_text('change_id: ' + cid + '\\nstate: INTAKE\\n')\n"
        "    (ws / 'CHANGE.yaml').write_text('change_id: ' + cid + '\\ntitle: Demo\\n')\n"
        "print('ok')\n",
        encoding="utf-8",
    )
    return root


def _calls(root):
    return [
        json.loads(line)
        for line in (root / "calls.jsonl").read_text(encoding="utf-8").splitlines()
    ]


def test_task_start_invokes_vnext_init(tmp_path, capsys):
    root = _target(tmp_path)

    code = run_task("start", target_dir=str(root), change_id="demo", title="Demo")

    assert code == 0
    assert _calls(root)[0][0] == "vnext-init"
    assert (root / ".maika" / "changes" / "demo" / "STATE.yaml").exists()
    assert "ok" in capsys.readouterr().out


def test_task_plan_invokes_vnext_compile(tmp_path):
    root = _target(tmp_path)
    run_task("start", target_dir=str(root), change_id="demo", title="Demo")

    code = run_task("plan", target_dir=str(root), change_id="demo")

    assert code == 0
    assert _calls(root)[1][0] == "vnext-compile"


def test_task_status_lists_workspaces(tmp_path, capsys):
    root = _target(tmp_path)
    run_task("start", target_dir=str(root), change_id="demo", title="Demo")
    ws = root / ".maika" / "changes" / "demo"
    (ws / "generated").mkdir()
    (ws / "generated" / "TASK_QUEUE.json").write_text(
        json.dumps({"tasks": [{"id": "TASK-001", "status": "pending"}]}),
        encoding="utf-8",
    )

    code = run_task("status", target_dir=str(root))

    out = capsys.readouterr().out
    assert code == 0
    assert "demo: INTAKE" in out
    assert "TASK-001: pending" in out


def test_task_cancel_marks_workspace_cancelled(tmp_path):
    root = _target(tmp_path)
    run_task("start", target_dir=str(root), change_id="demo", title="Demo")

    code = run_task("cancel", target_dir=str(root), change_id="demo")

    assert code == 0
    state = yaml.safe_load(
        (root / ".maika" / "changes" / "demo" / "STATE.yaml").read_text(encoding="utf-8")
    )
    assert state["state"] == "CANCELLED"


def test_task_reconcile_and_brainstorm_transition_states(tmp_path):
    root = _target(tmp_path)
    run_task("start", target_dir=str(root), change_id="demo", title="Demo")
    state_path = root / ".maika" / "changes" / "demo" / "STATE.yaml"
    state_path.write_text("change_id: demo\nstate: RECONCILING\n", encoding="utf-8")

    assert run_task("reconcile", target_dir=str(root), change_id="demo") == 0
    assert yaml.safe_load(state_path.read_text(encoding="utf-8"))["state"] == "BRAINSTORMING"
    assert run_task("brainstorm", target_dir=str(root), change_id="demo") == 0
    assert yaml.safe_load(state_path.read_text(encoding="utf-8"))["state"] == "SPEC_REVIEW"


def test_task_verify_reserved_until_w6(tmp_path, capsys):
    root = _target(tmp_path)

    code = run_task("verify", target_dir=str(root), change_id="demo")

    assert code == 2
    assert "W6" in capsys.readouterr().out
