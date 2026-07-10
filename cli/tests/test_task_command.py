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


def _complete_workspace(root: Path, state: str = "FINAL_REVIEW") -> Path:
    ws = root / ".maika" / "changes" / "demo"
    (ws / "generated").mkdir(exist_ok=True)
    (ws / "results").mkdir(exist_ok=True)
    (ws / "reviews").mkdir(exist_ok=True)
    (ws / "SPEC.md").write_text("# Spec\n", encoding="utf-8")
    (ws / "generated" / "PLAN_VALIDATION.json").write_text(
        json.dumps({"verdict": "APPROVED"}),
        encoding="utf-8",
    )
    (ws / "generated" / "TASK_QUEUE.json").write_text(
        json.dumps({
            "tasks": [{
                "id": "TASK-001",
                "status": "done",
                "result_path": "results/TASK-001.yaml",
                "review_path": "reviews/TASK-001.md",
            }],
        }),
        encoding="utf-8",
    )
    (ws / "results" / "TASK-001.yaml").write_text(
        "task_id: TASK-001\nstatus: done\nchanges:\n  modify: []\n",
        encoding="utf-8",
    )
    (ws / "reviews" / "TASK-001.md").write_text("VERDICT: APPROVED\n", encoding="utf-8")
    (ws / "reviews" / "FINAL_REVIEW.md").write_text("VERDICT: APPROVED\n", encoding="utf-8")
    (ws / "reviews" / "KNOWLEDGE_IMPACT.yaml").write_text(
        "stale_entries: []\nsuperseded_decisions: []\nnew_candidates: []\n"
        "graph_refresh_required: false\nmemory_updates: []\n",
        encoding="utf-8",
    )
    (ws / "STATE.yaml").write_text(f"change_id: demo\nstate: {state}\n", encoding="utf-8")
    return ws


def test_task_verify_writes_evidence_and_completes_workspace(tmp_path):
    root = _target(tmp_path)
    run_task("start", target_dir=str(root), change_id="demo", title="Demo")
    ws = _complete_workspace(root)

    code = run_task("verify", target_dir=str(root), change_id="demo")

    assert code == 0
    state = yaml.safe_load((ws / "STATE.yaml").read_text(encoding="utf-8"))
    assert state["state"] == "COMPLETED"
    commands = yaml.safe_load((ws / "verification" / "COMMANDS.yaml").read_text(encoding="utf-8"))
    assert {item["name"] for item in commands["commands"]} >= {
        "final-review-approved",
        "task-results-reviewed",
        "dead-reference-scan",
    }
    report = (ws / "verification" / "VERIFICATION_REPORT.md").read_text(encoding="utf-8")
    assert "VERDICT: VERIFIED" in report


def test_task_verify_runs_real_declared_commands(tmp_path):
    root = _target(tmp_path)
    run_task("start", target_dir=str(root), change_id="demo", title="Demo")
    ws = _complete_workspace(root)
    (ws / "verification").mkdir(exist_ok=True)
    (ws / "verification" / "COMMANDS.yaml").write_text(
        "declared:\n"
        "  - name: smoke\n"
        "    command: \"python -c 'print(\\\"1 passed\\\")'\"\n"
        "    expected: \"1 passed\"\n",
        encoding="utf-8",
    )

    code = run_task("verify", target_dir=str(root), change_id="demo")

    assert code == 0
    commands = yaml.safe_load((ws / "verification" / "COMMANDS.yaml").read_text(encoding="utf-8"))
    smoke = next(c for c in commands["commands"] if c["name"] == "smoke")
    assert smoke["interpretation"] == "pass"
    assert "1 passed" in smoke["observed_output"]      # real observed output, not a marker
    assert smoke["exit_code"] == 0


def test_task_verify_fails_when_declared_command_fails(tmp_path, capsys):
    root = _target(tmp_path)
    run_task("start", target_dir=str(root), change_id="demo", title="Demo")
    ws = _complete_workspace(root)
    (ws / "verification").mkdir(exist_ok=True)
    (ws / "verification" / "COMMANDS.yaml").write_text(
        "declared:\n  - name: failing\n    command: \"python -c 'import sys; sys.exit(3)'\"\n",
        encoding="utf-8",
    )

    code = run_task("verify", target_dir=str(root), change_id="demo")

    assert code == 1
    assert yaml.safe_load((ws / "STATE.yaml").read_text(encoding="utf-8"))["state"] == "FINAL_REVIEW"
    assert "declared verification command failed" in capsys.readouterr().out


def test_task_verify_refuses_unapproved_final_review(tmp_path, capsys):
    root = _target(tmp_path)
    run_task("start", target_dir=str(root), change_id="demo", title="Demo")
    ws = _complete_workspace(root)
    (ws / "reviews" / "FINAL_REVIEW.md").write_text("VERDICT: CHANGES_REQUESTED\n", encoding="utf-8")

    code = run_task("verify", target_dir=str(root), change_id="demo")

    assert code == 1
    assert yaml.safe_load((ws / "STATE.yaml").read_text(encoding="utf-8"))["state"] == "FINAL_REVIEW"
    assert "final review" in capsys.readouterr().out


def test_task_archive_moves_completed_workspace_and_refreshes_knowledge_index(tmp_path):
    root = _target(tmp_path)
    run_task("start", target_dir=str(root), change_id="demo", title="Demo")
    ws = _complete_workspace(root)
    assert run_task("verify", target_dir=str(root), change_id="demo") == 0

    code = run_task("archive", target_dir=str(root), change_id="demo")

    assert code == 0
    archived = root / ".maika" / "archive" / "demo"
    assert archived.exists()
    assert not ws.exists()
    state = yaml.safe_load((archived / "STATE.yaml").read_text(encoding="utf-8"))
    assert state["state"] == "ARCHIVED"
    manifest = yaml.safe_load((archived / "ARCHIVE_MANIFEST.yaml").read_text(encoding="utf-8"))
    assert manifest["change_id"] == "demo"
    assert manifest["verification_report"] == "verification/VERIFICATION_REPORT.md"
    assert "knowledge_lifecycle" in manifest
    assert manifest["knowledge_lifecycle"]["graph_refresh_requested"] is False
    assert (root / ".maika" / "knowledge" / "long-term" / "knowledge-index.yaml").exists()


def test_task_archive_requires_knowledge_impact(tmp_path, capsys):
    root = _target(tmp_path)
    run_task("start", target_dir=str(root), change_id="demo", title="Demo")
    ws = _complete_workspace(root)
    assert run_task("verify", target_dir=str(root), change_id="demo") == 0
    (ws / "reviews" / "KNOWLEDGE_IMPACT.yaml").unlink()

    code = run_task("archive", target_dir=str(root), change_id="demo")

    assert code == 1
    assert "KNOWLEDGE_IMPACT.yaml" in capsys.readouterr().out


def test_task_archive_requires_completed_workspace(tmp_path, capsys):
    root = _target(tmp_path)
    run_task("start", target_dir=str(root), change_id="demo", title="Demo")
    _complete_workspace(root, state="FINAL_REVIEW")

    code = run_task("archive", target_dir=str(root), change_id="demo")

    assert code == 1
    assert "COMPLETED" in capsys.readouterr().out
