"""Tests for the dashboard reader."""

import json

from cli.dashboard.reader import RunState, read_run


def _make_project(tmp_path, *, state="EXECUTING", queue=None):
    """Build a minimal Maika project under tmp_path with framework_root '.maika'."""
    root = tmp_path / ".maika"
    workspace = root / "changes" / "AUTH-feature"
    (workspace / "generated").mkdir(parents=True)
    (root / "resolved-config.yaml").write_text(
        "resolved:\n"
        "  platform: antigravity\n"
        "  framework_root: .maika\n"
        "  language: python\n"
        "  framework_version: '3.0'\n",
        encoding="utf-8",
    )
    (tmp_path / "AGENTS.md").write_text("# agents\n", encoding="utf-8")
    if state is not None:
        (workspace / "STATE.yaml").write_text(
            f"change_id: AUTH-feature\nstate: {state}\n",
            encoding="utf-8",
        )
        (workspace / "CHANGE.yaml").write_text(
            "change_id: AUTH-feature\ntitle: Auth feature\n",
            encoding="utf-8",
        )
    if queue is not None:
        (workspace / "generated" / "TASK_QUEUE.json").write_text(queue, encoding="utf-8")
    return tmp_path


QUEUE = json.dumps(
    {
        "change_id": "AUTH-feature",
        "tasks": [
            {"id": "T1", "title": "build login", "status": "done"},
            {"id": "T2", "title": "wire DI", "status": "in_progress"},
            {"id": "T3", "title": "tests", "status": "pending"},
        ],
    }
)


def test_full_state(tmp_path):
    proj = _make_project(tmp_path, queue=QUEUE)
    state = read_run(str(proj))
    assert state.ticket_id == "AUTH-feature"
    assert state.phase_state == "EXECUTING"
    assert state.tasks_total == 3
    assert state.tasks_done == 1
    assert state.active_task == "wire DI"
    assert state.progress_pct == 33
    assert state.stale is False


def test_missing_task_queue(tmp_path):
    proj = _make_project(tmp_path)
    state = read_run(str(proj))
    assert state.phase_state == "EXECUTING"
    assert state.tasks_total == 0
    assert state.progress_pct == 0


def test_missing_state_is_idle(tmp_path):
    proj = _make_project(tmp_path, state=None, queue=QUEUE)
    state = read_run(str(proj))
    assert state.phase_state is None
    assert state.tasks_total == 0


def test_no_active_run_is_idle(tmp_path):
    proj = _make_project(tmp_path, state=None)
    state = read_run(str(proj))
    assert state.phase_state is None
    assert state.tasks_total == 0
    assert state.progress_pct == 0


def test_malformed_queue_sets_stale(tmp_path):
    proj = _make_project(tmp_path, queue='{"tasks": [')
    state = read_run(str(proj))
    assert state.stale is True
    assert state.tasks_total == 0


def test_zero_tasks_progress_is_zero(tmp_path):
    empty_queue = json.dumps({"change_id": "AUTH-feature", "tasks": []})
    proj = _make_project(tmp_path, queue=empty_queue)
    state = read_run(str(proj))
    assert state.tasks_total == 0
    assert state.progress_pct == 0  # no ZeroDivisionError


def test_not_an_maika_project_is_idle(tmp_path):
    state = read_run(str(tmp_path))  # no resolved-config.yaml
    assert isinstance(state, RunState)
    assert state.phase_state is None
    assert state.tasks_total == 0
