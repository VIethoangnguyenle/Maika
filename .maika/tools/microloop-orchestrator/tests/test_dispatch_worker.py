import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
import orchestrator  # noqa: E402


def test_dispatch_worker_done_on_first_success():
    result = orchestrator.dispatch_worker("do X", lambda p: (0, "ok"), retries=2)
    assert result["status"] == "done"
    assert result["attempts"] == 1


def test_dispatch_worker_retries_then_done():
    calls = []

    def runner(prompt):
        calls.append(prompt)
        return (1, "err") if len(calls) < 3 else (0, "ok")

    result = orchestrator.dispatch_worker("do X", runner, retries=2)
    assert result["status"] == "done"
    assert result["attempts"] == 3
    assert calls == ["do X"] * 3


def test_dispatch_worker_blocked_after_retry_budget():
    result = orchestrator.dispatch_worker("do X", lambda p: (1, "boom"), retries=1)
    assert result["status"] == "blocked"
    assert result["attempts"] == 2


def test_dispatch_worker_logs_activity_events(tmp_path):
    result = orchestrator.dispatch_worker(
        "do X", lambda p: (1, "boom"), retries=0,
        active_dir=tmp_path, task_id="T1",
    )
    assert result["status"] == "blocked"
    log = (tmp_path / "microloop" / "ACTIVITY_LOG.jsonl").read_text(encoding="utf-8")
    events = [json.loads(line) for line in log.splitlines()]
    assert [e["event"] for e in events] == ["subagent_started", "subagent_blocked"]
    assert events[0]["task_id"] == "T1"


def test_make_worker_runner_renders_prompt(tmp_path):
    marker = tmp_path / "prompt.txt"
    script = "import sys, pathlib; pathlib.Path(sys.argv[2]).write_text(sys.argv[1])"
    command = f'"{sys.executable}" -c "{script}" {{prompt}} "{marker}"'
    runner = orchestrator.make_worker_runner(command, timeout=60)
    exit_code, _ = runner("helloworker")
    assert exit_code == 0
    assert marker.read_text() == "helloworker"


def test_make_worker_runner_timeout_returns_124():
    command = f'"{sys.executable}" -c "import time; time.sleep(5)" {{prompt}}'
    runner = orchestrator.make_worker_runner(command, timeout=1)
    exit_code, output = runner("x")
    assert exit_code == 124
    assert "timeout" in output.lower()
