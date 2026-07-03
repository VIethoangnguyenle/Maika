from pathlib import Path
import json
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
import orchestrator  # noqa: E402


VALID_HANDOFF = (
    "# TASK_HANDOFF.napas-human\n"
    "## Task Objective\nCreate human SRS\n"
    "## Applicable DNA/Conventions\n- SP-6: staircase\n"
    "## Evidence\n- UA evidence: domain_overview=Payment, domain_flow=Transfer\n"
    "## Allowed Files\n- src/NapasHuman.java\n"
    "## Verification\n- pytest\n"
)


def test_runtime_contract_emits_queue_handoff_result_and_events(tmp_path):
    active = tmp_path / ".agents" / "knowledge" / "active"
    active.mkdir(parents=True)
    tasks = [
        {"id": "napas-agent", "desc": "Create agent SRS", "depends_on": ["napas-human"]},
        {"id": "napas-human", "desc": "Create human SRS", "depends_on": []},
    ]

    queue = orchestrator.initialize_runtime_queue(
        active,
        ticket_id="SME-TRANSFER-002",
        spec_path="openspec/changes/sme-transfer-002/tasks.md",
        tasks=tasks,
        framework_root=".agents",
    )
    orchestrator.record_parent_event(
        active,
        "phase_changed",
        phase="phase-3-in-progress",
        summary="Parent entered apply phase.",
        ticket_id="SME-TRANSFER-002",
    )
    orchestrator.write_parent_brain(
        active,
        "Human asked for parent progress from the IDE brain.",
        source="antigravity-brain",
        ticket_id="SME-TRANSFER-002",
    )
    orchestrator.write_task_handoff(active, "napas-human", VALID_HANDOFF)
    orchestrator.write_task_handoff(
        active,
        "napas-agent",
        VALID_HANDOFF.replace("napas-human", "napas-agent").replace(
            "src/NapasHuman.java", "src/NapasAgent.java"
        ),
    )
    orchestrator.update_task_status(active, "napas-human", "in_progress", event="subagent_started")
    orchestrator.write_task_result(active, "napas-human", "# TASK_RESULT.napas-human\n\nstatus: done\n")

    loaded = orchestrator.load_runtime_queue(active)
    statuses = {task["id"]: task["status"] for task in loaded["tasks"]}
    events = [
        json.loads(line)
        for line in (active / "microloop" / "ACTIVITY_LOG.jsonl").read_text(encoding="utf-8").splitlines()
    ]

    assert [task["id"] for task in queue["tasks"]] == ["napas-human", "napas-agent"]
    assert statuses == {"napas-human": "done", "napas-agent": "pending"}
    assert (active / "TASK_HANDOFF.napas-human.md").exists()
    assert "source: antigravity-brain" in (active / "PARENT_BRAIN.md").read_text(encoding="utf-8")
    assert (active / "microloop" / "TASK_RESULT.napas-human.md").exists()
    assert loaded["tasks"][0]["handoff_path"] == ".agents/knowledge/active/TASK_HANDOFF.napas-human.md"
    assert loaded["tasks"][0]["result_path"] == ".agents/knowledge/active/microloop/TASK_RESULT.napas-human.md"
    assert [event["event"] for event in events] == [
        "task_queue_created",
        "phase_changed",
        "parent_brain_updated",
        "subagent_spawned",
        "subagent_spawned",
        "subagent_started",
        "result_written",
        "subagent_done",
    ]
    assert events[0]["actor"] == "parent"
    assert events[1]["actor"] == "parent"
    assert events[2]["actor"] == "parent"
    assert events[2]["source"] == "antigravity-brain"
    assert events[3]["actor"] == "subagent"


def test_write_task_handoff_rejects_missing_knowledge_slice(tmp_path):
    active = tmp_path / ".agents" / "knowledge" / "active"
    active.mkdir(parents=True)
    try:
        orchestrator.write_task_handoff(active, "empty", "# TASK_HANDOFF.empty\n")
    except ValueError as exc:
        assert "implementation context" in str(exc)
    else:
        raise AssertionError("expected handoff without knowledge slice to be rejected")


def test_update_task_status_rejects_unknown_task(tmp_path):
    active = tmp_path / ".agents" / "knowledge" / "active"
    active.mkdir(parents=True)
    orchestrator.initialize_runtime_queue(
        active,
        ticket_id="X",
        spec_path="p",
        tasks=[{"id": "T1", "desc": "one", "depends_on": []}],
        framework_root=".agents",
    )

    try:
        orchestrator.update_task_status(active, "NOPE", "done")
    except ValueError as exc:
        assert "not in queue" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_initialize_runtime_queue_requires_framework_root(tmp_path):
    active = tmp_path / ".agents" / "knowledge" / "active"
    active.mkdir(parents=True)
    try:
        orchestrator.initialize_runtime_queue(
            active,
            ticket_id="X",
            spec_path="p",
            tasks=[{"id": "T1", "desc": "one", "depends_on": []}],
        )
    except TypeError:
        pass
    else:
        raise AssertionError("expected TypeError when framework_root is omitted")
