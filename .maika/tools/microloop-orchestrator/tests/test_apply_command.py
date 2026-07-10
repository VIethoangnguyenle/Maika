import json
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
import orchestrator  # noqa: E402


def _scaffold(tmp_path, *, mode="fresh-session", worker_command="stub {prompt}",
              tasks=None, with_checkpoint=True, with_handoffs=True):
    """Dựng cây scaffold tối thiểu cho driver: profiles/ + knowledge/active/ + queue."""
    fw = tmp_path / ".maika"
    active = fw / "knowledge" / "active"
    active.mkdir(parents=True)
    (fw / "profiles").mkdir()
    (fw / "profiles" / "execution-mode.yaml").write_text(
        yaml.safe_dump({
            "execution_mode": mode,
            "worker_command": worker_command,
            "max_retries": 1,
            "worker_timeout_seconds": 60,
        }),
        encoding="utf-8",
    )
    if with_checkpoint:
        (active / "KNOWLEDGE_CHECKPOINT.md").write_text("ok", encoding="utf-8")
    if tasks is None:
        tasks = [
            {"id": "T1", "desc": "node 1", "depends_on": []},
            {"id": "T2", "desc": "node 2", "depends_on": ["T1"]},
        ]
    if tasks:
        orchestrator.initialize_runtime_queue(
            active, "TICKET-1", "spec.md", tasks,
            execution_mode=mode, framework_root=".maika",
        )
    if with_handoffs:
        for t in tasks:
            (active / f"TASK_HANDOFF.{t['id']}.md").write_text(
                f"handoff {t['id']}", encoding="utf-8"
            )
    return active


def _ok_runner(tmp_path):
    """Stub worker: trích result_path từ prompt và ghi TASK_RESULT như worker thật."""
    def runner(prompt):
        for token in prompt.split():
            if "TASK_RESULT" in token:
                path = tmp_path / token.rstrip(".")
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("done", encoding="utf-8")
                return 0, "ok"
        return 1, "no result path in prompt"
    return runner


def test_load_execution_config_prefers_local_override(tmp_path):
    active = _scaffold(tmp_path)
    profiles = active.parents[1] / "profiles"
    (profiles / "execution-mode.local.yaml").write_text(
        yaml.safe_dump({
            "execution_mode": "fresh-session",
            "worker_command": "local {prompt}",
            "max_retries": 3,
            "worker_timeout_seconds": 15,
        }),
        encoding="utf-8",
    )

    config = orchestrator.load_execution_config(active)

    assert config["worker_command"] == "local {prompt}"
    assert config["max_retries"] == 3


def test_apply_command_happy_two_nodes(tmp_path):
    active = _scaffold(tmp_path)
    summary = orchestrator.apply_command(active, runner=_ok_runner(tmp_path))
    assert summary["status"] == "done"
    assert summary["done"] == 2
    queue = orchestrator.load_runtime_queue(active)
    assert [t["status"] for t in queue["tasks"]] == ["done", "done"]
    log = (active / "microloop" / "ACTIVITY_LOG.jsonl").read_text(encoding="utf-8")
    events = [json.loads(line)["event"] for line in log.splitlines()]
    assert events.count("subagent_started") == 2


def test_apply_command_blocked_stops_at_failing_node(tmp_path):
    active = _scaffold(tmp_path)
    summary = orchestrator.apply_command(active, runner=lambda p: (1, "boom"))
    assert summary["status"] == "blocked"
    assert summary["task_id"] == "T1"
    queue = orchestrator.load_runtime_queue(active)
    by_id = {t["id"]: t["status"] for t in queue["tasks"]}
    assert by_id == {"T1": "blocked", "T2": "pending"}


def test_apply_command_resumes_after_unblock(tmp_path):
    active = _scaffold(tmp_path)
    orchestrator.apply_command(active, runner=lambda p: (1, "boom"))
    queue = orchestrator.load_runtime_queue(active)
    queue["tasks"][0]["status"] = "pending"
    orchestrator.save_runtime_queue(active, queue)
    summary = orchestrator.apply_command(active, runner=_ok_runner(tmp_path))
    assert summary["status"] == "done"
    assert summary["done"] == 2


def test_apply_command_refuses_without_queue(tmp_path):
    active = _scaffold(tmp_path)
    (active / "microloop" / "TASK_QUEUE.md").unlink()
    summary = orchestrator.apply_command(active, runner=_ok_runner(tmp_path))
    assert summary["status"] == "refused"
    assert "TASK_QUEUE" in summary["reason"]


def test_apply_command_refuses_missing_handoff(tmp_path):
    active = _scaffold(tmp_path, with_handoffs=False)
    summary = orchestrator.apply_command(active, runner=_ok_runner(tmp_path))
    assert summary["status"] == "refused"
    assert "TASK_HANDOFF" in summary["reason"]


def test_apply_command_refuses_wrong_mode(tmp_path):
    active = _scaffold(tmp_path, mode="subagent")
    summary = orchestrator.apply_command(active, runner=_ok_runner(tmp_path))
    assert summary["status"] == "refused"
    assert "fresh-session" in summary["reason"]


def test_apply_command_refuses_empty_worker_command(tmp_path):
    active = _scaffold(tmp_path, worker_command="")
    summary = orchestrator.apply_command(active, runner=_ok_runner(tmp_path))
    assert summary["status"] == "refused"
    assert "worker_command" in summary["reason"]


def test_apply_command_refuses_without_checkpoint(tmp_path):
    active = _scaffold(tmp_path, with_checkpoint=False)
    summary = orchestrator.apply_command(active, runner=_ok_runner(tmp_path))
    assert summary["status"] == "refused"
    assert "KNOWLEDGE_CHECKPOINT" in summary["reason"]


def test_apply_command_worker_ok_but_no_result_is_blocked(tmp_path):
    active = _scaffold(tmp_path)
    summary = orchestrator.apply_command(active, runner=lambda p: (0, "ok"))
    assert summary["status"] == "blocked"
    assert "TASK_RESULT" in summary["reason"]


def test_apply_command_litmus_real_subprocess(tmp_path):
    """Litmus R3: driver end-to-end với worker subprocess thật (fake worker python)."""
    active = _scaffold(tmp_path, tasks=[{"id": "T1", "desc": "node", "depends_on": []}])
    script = tmp_path / "fake_worker.py"
    script.write_text(
        "import sys, pathlib\n"
        f"base = pathlib.Path({str(tmp_path)!r})\n"
        "for token in sys.argv[1].split():\n"
        "    if 'TASK_RESULT' in token:\n"
        "        p = base / token\n"
        "        p.parent.mkdir(parents=True, exist_ok=True)\n"
        "        p.write_text('done', encoding='utf-8')\n",
        encoding="utf-8",
    )
    config = {
        "execution_mode": "fresh-session",
        "worker_command": f'"{sys.executable}" "{script}" {{prompt}}',
        "max_retries": 0,
        "worker_timeout_seconds": 60,
    }
    summary = orchestrator.apply_command(active, config=config)
    assert summary["status"] == "done"
    assert summary["done"] == 1


def test_main_apply_refused_exit_code(tmp_path, capsys):
    active = _scaffold(tmp_path, mode="subagent")
    code = orchestrator.main(["apply", "--active-dir", str(active)])
    assert code == 2
    assert "Từ chối" in capsys.readouterr().out
