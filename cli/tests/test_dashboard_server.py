"""Tests for the dashboard SSE server."""
import json
import os
import threading
import textwrap
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from cli.dashboard import registry, server
from cli.dashboard.reader import RunState


def _make_maika_project(tmp_path, name="p"):
    proj = tmp_path / name
    active = proj / ".maika" / "knowledge" / "active"
    active.mkdir(parents=True)
    (proj / ".maika" / "resolved-config.yaml").write_text(
        "resolved:\n"
        "  platform: antigravity\n"
        "  framework_root: .maika\n"
        "  language: python\n"
        "  framework_version: '3.0'\n",
        encoding="utf-8",
    )
    (proj / "AGENTS.md").write_text("# agents\n", encoding="utf-8")
    return proj, active


def test_serialize_includes_name_and_progress():
    s = RunState(
        project_path="/tmp/projX",
        phase_state="phase-3-in-progress",
        tasks_total=4,
        tasks_done=2,
        active_task="wire DI",
    )
    d = server.serialize(s)
    assert d["name"] == "projX"
    assert d["progress_pct"] == 50
    assert d["phase_state"] == "phase-3-in-progress"
    assert d["active_task"] == "wire DI"
    assert d["project_path"] == "/tmp/projX"


def test_sse_format_framing():
    assert server.sse_format('{"a":1}') == b'data: {"a":1}\n\n'


def test_snapshot_empty_registry(tmp_path):
    assert server.snapshot(tmp_path / "none.yaml") == []


def test_snapshot_non_maika_project_is_idle(tmp_path):
    reg = tmp_path / "projects.yaml"
    proj = tmp_path / "p"
    proj.mkdir()
    registry.register(reg, str(proj))
    runs = server.snapshot(reg)
    assert len(runs) == 1
    assert runs[0]["name"] == "p"
    assert runs[0]["phase_state"] is None
    assert runs[0]["tasks_total"] == 0


def test_snapshot_includes_subagent_handoff_prompts(tmp_path):
    reg = tmp_path / "projects.yaml"
    proj, active = _make_maika_project(tmp_path)
    human = active / "TASK_HANDOFF.napas-human.md"
    agent = active / "TASK_HANDOFF.napas-agent.md"
    human.write_text(
        textwrap.dedent(
            """\
            # TASK_HANDOFF.napas-human

            ## Task Objective
            Create the human SRS.
            """
        ),
        encoding="utf-8",
    )
    agent.write_text(
        "# TASK_HANDOFF.napas-agent\n\n## Task Objective\nCreate the agent SRS.\n",
        encoding="utf-8",
    )
    # Force distinct mtimes: both writes can land in the same kernel tick,
    # and _collect_artifacts orders by (mtime, name) for chronological intent.
    now = time.time()
    os.utime(human, (now - 10, now - 10))
    os.utime(agent, (now, now))
    registry.register(reg, str(proj))

    runs = server.snapshot(reg)

    assert [a["id"] for a in runs[0]["subagents"]] == ["napas-human", "napas-agent"]
    assert "Create the human SRS" in runs[0]["subagents"][0]["prompt"]
    assert runs[0]["subagents"][1]["name"] == "napas agent"


def test_snapshot_includes_parent_brain_mirror(tmp_path):
    reg = tmp_path / "projects.yaml"
    proj, active = _make_maika_project(tmp_path)
    (active / "PARENT_BRAIN.md").write_text(
        textwrap.dedent(
            """\
            # PARENT_BRAIN

            source: antigravity-brain

            Human asked why parent progress is invisible.
            Parent decided to mirror IDE brain into dashboard.
            """
        ),
        encoding="utf-8",
    )
    registry.register(reg, str(proj))

    run = server.snapshot(reg)[0]

    assert run["parent_brain"]["source"] == "antigravity-brain"
    assert run["parent_brain"]["path"].endswith("PARENT_BRAIN.md")
    assert "mirror IDE brain" in run["parent_brain"]["content"]
    assert run["parent_brain"]["updated_at"]


def test_snapshot_merges_queue_result_and_activity_log(tmp_path):
    reg = tmp_path / "projects.yaml"
    proj, active = _make_maika_project(tmp_path)
    microloop = active / "microloop"
    microloop.mkdir()
    (active / "TASK_HANDOFF.napas-human.md").write_text(
        "# TASK_HANDOFF.napas-human\n\nPrompt human.\n", encoding="utf-8"
    )
    (active / "TASK_HANDOFF.napas-agent.md").write_text(
        "# TASK_HANDOFF.napas-agent\n\nPrompt agent.\n", encoding="utf-8"
    )
    (microloop / "TASK_RESULT.napas-human.md").write_text(
        "# TASK_RESULT.napas-human\n\nstatus: done\n\n## Summary\nHuman done.\n",
        encoding="utf-8",
    )
    (microloop / "TASK_QUEUE.md").write_text(
        textwrap.dedent(
            """\
            ticket_id: SME-TRANSFER-002
            execution_mode: subagent
            tasks:
              - id: napas-human
                desc: Create human SRS
                status: done
                handoff_path: .maika/knowledge/active/TASK_HANDOFF.napas-human.md
                result_path: .maika/knowledge/active/microloop/TASK_RESULT.napas-human.md
              - id: napas-agent
                desc: Create agent SRS
                status: in_progress
                handoff_path: .maika/knowledge/active/TASK_HANDOFF.napas-agent.md
            """
        ),
        encoding="utf-8",
    )
    (microloop / "ACTIVITY_LOG.jsonl").write_text(
        '{"ts":"2026-06-19T23:49:00+07:00","actor":"parent","event":"phase_changed","summary":"Parent entered apply","phase":"phase-3-in-progress"}\n'
        '{"ts":"2026-06-19T23:50:00+07:00","event":"subagent_spawned","task_id":"napas-human"}\n'
        '{"ts":"2026-06-19T23:51:00+07:00","event":"subagent_started","task_id":"napas-agent"}\n',
        encoding="utf-8",
    )
    registry.register(reg, str(proj))

    run = server.snapshot(reg)[0]

    assert run["tasks_total"] == 2
    assert run["tasks_done"] == 1
    assert run["active_task"] == "Create agent SRS"
    assert [a["status"] for a in run["subagents"]] == ["done", "in_progress"]
    assert run["subagents"][0]["result"].startswith("# TASK_RESULT.napas-human")
    assert run["subagents"][1]["result"] is None
    assert [e["event"] for e in run["events"]] == [
        "phase_changed",
        "subagent_spawned",
        "subagent_started",
    ]
    assert run["events"][0]["actor"] == "parent"
    assert run["events"][0]["summary"] == "Parent entered apply"
    assert run["errors"] == []


def test_snapshot_bad_activity_log_marks_stale(tmp_path):
    reg = tmp_path / "projects.yaml"
    proj, active = _make_maika_project(tmp_path)
    microloop = active / "microloop"
    microloop.mkdir()
    (microloop / "ACTIVITY_LOG.jsonl").write_text('{"event":"ok"}\nnot-json\n', encoding="utf-8")
    registry.register(reg, str(proj))

    run = server.snapshot(reg)[0]

    assert run["stale"] is True
    assert run["events"] == [{"event": "ok"}]
    assert "ACTIVITY_LOG.jsonl:2" in run["errors"][0]


def test_snapshot_bad_task_queue_marks_stale(tmp_path):
    reg = tmp_path / "projects.yaml"
    proj, active = _make_maika_project(tmp_path)
    microloop = active / "microloop"
    microloop.mkdir()
    (microloop / "TASK_QUEUE.md").write_text("tasks: [unterminated\n", encoding="utf-8")
    registry.register(reg, str(proj))

    run = server.snapshot(reg)[0]

    assert run["stale"] is True
    assert run["subagents"] == []
    assert "TASK_QUEUE.md" in run["errors"][0]


def test_snapshot_task_queue_tasks_not_a_list_marks_stale(tmp_path):
    reg = tmp_path / "projects.yaml"
    proj, active = _make_maika_project(tmp_path)
    microloop = active / "microloop"
    microloop.mkdir()
    (microloop / "TASK_QUEUE.md").write_text("tasks: not-a-list\n", encoding="utf-8")
    registry.register(reg, str(proj))

    run = server.snapshot(reg)[0]

    assert run["stale"] is True
    assert "tasks must be a list" in run["errors"][0]


def test_snapshot_reader_stale_survives_runtime_merge(tmp_path):
    # AGENT_TRANSPARENCY present but unparseable -> read_run marks stale.
    # read_runtime never reads that file, so its stale=False must NOT clobber
    # the reader's flag when the two dicts are merged in snapshot().
    reg = tmp_path / "projects.yaml"
    proj, active = _make_maika_project(tmp_path)
    (active / "AGENT_TRANSPARENCY.md").write_text("not valid frontmatter\n", encoding="utf-8")
    registry.register(reg, str(proj))

    run = server.snapshot(reg)[0]

    assert run["stale"] is True
    assert run["errors"] == []


@pytest.fixture
def running_server(tmp_path):
    reg = tmp_path / "projects.yaml"
    proj = tmp_path / "p"
    proj.mkdir()
    registry.register(reg, str(proj))
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.DashboardHandler)
    httpd.daemon_threads = True
    httpd.registry_file = reg
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    port = httpd.server_address[1]
    yield f"http://127.0.0.1:{port}"
    httpd.shutdown()
    httpd.server_close()


def test_index_served(running_server):
    with urllib.request.urlopen(running_server + "/", timeout=5) as r:
        body = r.read().decode()
        assert r.status == 200
        assert r.headers["Cache-Control"] == "no-store"
        assert "Maika" in body
        assert "view result" in body
        assert "parent brain" in body
        assert "event-parent" in body


def test_api_runs_json(running_server):
    with urllib.request.urlopen(running_server + "/api/runs", timeout=5) as r:
        assert r.status == 200
        data = json.loads(r.read())
        assert isinstance(data, list)
        assert data[0]["name"] == "p"


def test_unknown_path_404(running_server):
    with pytest.raises(urllib.error.HTTPError) as exc:
        urllib.request.urlopen(running_server + "/nope", timeout=5)
    assert exc.value.code == 404


def test_events_first_message_is_snapshot(running_server):
    req = urllib.request.urlopen(running_server + "/events", timeout=5)
    line = req.readline()  # b"data: [...]\n"
    req.close()
    assert line.startswith(b"data: ")
    payload = json.loads(line[len(b"data: "):].decode())
    assert isinstance(payload, list)
