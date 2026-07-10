import importlib.util
import json
from pathlib import Path

import yaml


MOD = Path(__file__).resolve().parents[1] / "write_gate.py"
spec = importlib.util.spec_from_file_location("write_gate", MOD)
wg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wg)


def _write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _setup_vnext_workspace(
    root,
    *,
    engine="vnext",
    state="EXECUTING",
    verdict="APPROVED",
    queue_sha="sha-ok",
    manifest_sha="sha-ok",
    tasks=None,
):
    framework = root / ".maika"
    profiles = framework / "profiles"
    profiles.mkdir(parents=True, exist_ok=True)
    (profiles / "execution-mode.local.yaml").write_text(
        yaml.safe_dump({"workflow_engine": engine}, sort_keys=False),
        encoding="utf-8",
    )

    ws = framework / "changes" / "demo"
    ws.mkdir(parents=True, exist_ok=True)
    (ws / "STATE.yaml").write_text(
        yaml.safe_dump({"change_id": "demo", "state": state}, sort_keys=False),
        encoding="utf-8",
    )

    if tasks is None:
        tasks = [
            {
                "id": "TASK-001",
                "status": "in_progress",
                "files": {
                    "create": ["src/App.py"],
                    "modify": ["src/service.py"],
                    "test": ["tests/test_app.py"],
                },
            }
        ]

    _write_json(ws / "generated" / "PLAN_VALIDATION.json", {"verdict": verdict})
    _write_json(ws / "generated" / "PLAN_MANIFEST.json", {"plan_sha256": manifest_sha})
    _write_json(
        ws / "generated" / "TASK_QUEUE.json",
        {"change_id": "demo", "plan_sha256": queue_sha, "tasks": tasks},
    )
    return ws


def test_legacy_flag_falls_through_to_legacy_gate(tmp_path):
    _setup_vnext_workspace(tmp_path, engine="legacy")

    result = wg.evaluate_write(tmp_path, Path("src/App.py"), framework_root=".maika")

    assert result.ok is False
    assert "KNOWLEDGE_CHECKPOINT" in result.reason


def test_vnext_executing_approved_fresh_allowed_file_allows(tmp_path):
    _setup_vnext_workspace(tmp_path)

    result = wg.evaluate_write(tmp_path, Path("src/App.py"), framework_root=".maika")

    assert result.ok is True


def test_vnext_executing_prefers_local_override_over_template(tmp_path):
    _setup_vnext_workspace(tmp_path)
    profiles = tmp_path / ".maika" / "profiles"
    (profiles / "execution-mode.yaml").write_text(
        "{% if platform == 'codex' %}\nworkflow_engine: legacy\n{% endif %}\n",
        encoding="utf-8",
    )

    result = wg.evaluate_write(tmp_path, Path("src/App.py"), framework_root=".maika")

    assert result.ok is True


def test_vnext_executing_denies_file_outside_brief_scope_with_task_id(tmp_path):
    _setup_vnext_workspace(tmp_path)

    result = wg.evaluate_write(tmp_path, Path("src/Other.py"), framework_root=".maika")

    assert result.ok is False
    assert "vNext brief-scope" in result.reason
    assert "TASK-001" in result.reason


def test_vnext_executing_allows_writes_inside_change_workspace(tmp_path):
    _setup_vnext_workspace(tmp_path)

    result = wg.evaluate_write(
        tmp_path,
        Path(".maika/changes/demo/briefs/TASK-001.md"),
        framework_root=".maika",
    )

    assert result.ok is True


def test_no_executing_change_falls_through_to_legacy_gate(tmp_path):
    _setup_vnext_workspace(tmp_path, state="PLANNING")

    result = wg.evaluate_write(tmp_path, Path("src/App.py"), framework_root=".maika")

    assert result.ok is False
    assert "KNOWLEDGE_CHECKPOINT" in result.reason


def test_vnext_executing_denies_when_plan_validation_not_approved(tmp_path):
    _setup_vnext_workspace(tmp_path, verdict="REVISE")

    result = wg.evaluate_write(tmp_path, Path("src/App.py"), framework_root=".maika")

    assert result.ok is False
    assert "vNext EXECUTING" in result.reason
    assert "PLAN_VALIDATION" in result.reason


def test_vnext_executing_denies_when_task_queue_plan_sha_is_stale(tmp_path):
    _setup_vnext_workspace(tmp_path, queue_sha="old-sha", manifest_sha="new-sha")

    result = wg.evaluate_write(tmp_path, Path("src/App.py"), framework_root=".maika")

    assert result.ok is False
    assert "vNext EXECUTING" in result.reason
    assert "plan_sha256" in result.reason


def test_vnext_executing_denies_without_exactly_one_in_progress_task(tmp_path):
    _setup_vnext_workspace(
        tmp_path,
        tasks=[
            {"id": "TASK-001", "status": "pending", "files": {"modify": ["src/App.py"]}},
            {"id": "TASK-002", "status": "done", "files": {"modify": ["src/Other.py"]}},
        ],
    )

    result = wg.evaluate_write(tmp_path, Path("src/App.py"), framework_root=".maika")

    assert result.ok is False
    assert "vNext EXECUTING" in result.reason
    assert "in_progress" in result.reason
