import json
from pathlib import Path

import pytest
import yaml

from cli.commands.task import run_task
from cli.config import project
from cli.platforms import probe
from cli.runtime.binary_identity import binary_identity
from cli.runtime.platform_profile import profile_fingerprint, write_platform_runtime_profile
from cli.runtime.session_registry import record_session
from cli.runtime.session_registry import list_sessions
from cli.runtime.worker_resolver import (
    FRESH_PROCESS, WorkerProfile, resolve_worker_profile, run_worker_smoke_test,
)


def _task_project(root: Path):
    cfg = project.enable(project.enable(project._default(), "claude-code"), "codex")
    project.save(root, cfg)
    orch = root / ".maika/tools/microloop-orchestrator/orchestrator.py"
    orch.parent.mkdir(parents=True)
    orch.write_text("", encoding="utf-8")


def test_public_task_ambiguous_sessions_refuses_without_spawn(tmp_path, monkeypatch):
    _task_project(tmp_path)
    record_session(tmp_path, "claude-code", source="native-hook", session_id="claude")
    record_session(tmp_path, "codex", source="native-hook", session_id="codex")
    monkeypatch.setattr("cli.commands.task._bootstrap_ready", lambda *_: (True, ""))
    spawned = []
    monkeypatch.setattr("cli.commands.task._run", lambda *args: spawned.append(args) or 0)
    assert run_task("review", str(tmp_path), change_id="x") == 2
    assert spawned == []


def test_public_task_disabled_explicit_refuses(tmp_path, monkeypatch):
    project.save(tmp_path, project.enable(project._default(), "claude-code"))
    orch = tmp_path / ".maika/tools/microloop-orchestrator/orchestrator.py"
    orch.parent.mkdir(parents=True)
    orch.write_text("", encoding="utf-8")
    monkeypatch.setattr("cli.commands.task._bootstrap_ready", lambda *_: (True, ""))
    assert run_task("review", str(tmp_path), change_id="x", platform_key="codex") == 2


def test_public_task_explicit_platform_is_forwarded(tmp_path, monkeypatch):
    _task_project(tmp_path)
    monkeypatch.setattr("cli.commands.task._bootstrap_ready", lambda *_: (True, ""))
    commands = []
    monkeypatch.setattr("cli.commands.task._run", lambda command, _cwd: commands.append(command) or 0)
    assert run_task("review", str(tmp_path), change_id="x", platform_key="codex") == 0
    assert commands[0][-2:] == ["--platform", "codex"]


def test_non_worker_task_does_not_resolve_platform(tmp_path, monkeypatch):
    _task_project(tmp_path)
    monkeypatch.setattr("cli.commands.task._bootstrap_ready", lambda *_: (True, ""))
    monkeypatch.setattr("cli.runtime.session.resolve_active_platform",
                        lambda *_a, **_k: pytest.fail("non-worker action resolved platform"))
    monkeypatch.setattr("cli.commands.task._run", lambda *_: 0)
    assert run_task("explore", str(tmp_path), change_id="x") == 0


def _verified_profile(root: Path, executable: Path):
    path = write_platform_runtime_profile(root, "codex")
    doc = yaml.safe_load(path.read_text())
    doc["worker"]["executable"] = str(executable)
    doc["profile_fingerprint"] = profile_fingerprint(doc)
    doc["detection"]["binary"].update(
        found=True, version_supported=True, path=str(executable), version="1.0")
    doc["capabilities"]["fresh_session"] = "verified"
    doc["verification"].update(
        worker_smoke_test="pass",
        worker_binary=binary_identity(str(executable), version="1.0"),
        verified_worker_profile_fingerprint=doc["profile_fingerprint"],
    )
    path.write_text(yaml.safe_dump(doc, sort_keys=False))
    return path


def test_worker_binary_content_change_refuses(tmp_path):
    executable = tmp_path / "codex"
    executable.write_text("one", encoding="utf-8")
    executable.chmod(0o755)
    _verified_profile(tmp_path, executable)
    executable.write_text("two", encoding="utf-8")
    assert resolve_worker_profile(tmp_path, "codex").strategy == "disabled"


def test_detect_only_binary_change_invalidates(tmp_path, monkeypatch):
    first = tmp_path / "codex-1"
    second = tmp_path / "codex-2"
    for path, text in ((first, "one"), (second, "two")):
        path.write_text(text, encoding="utf-8")
        path.chmod(0o755)
    profile_path = _verified_profile(tmp_path, first)
    doc = yaml.safe_load(profile_path.read_text())
    doc["worker"]["executable"] = str(second)
    profile_path.write_text(yaml.safe_dump(doc, sort_keys=False))
    monkeypatch.setattr(probe, "detect_binary", lambda _name: probe.BinaryProbe(
        "codex", True, str(second), "1.0", True))
    probe.probe_and_persist(tmp_path, "codex", verify=False)
    refreshed = yaml.safe_load(profile_path.read_text())
    assert refreshed["verification"]["worker_smoke_test"] == "not-run"
    assert refreshed["verification"]["last_verified_at"] is None


def test_worker_smoke_uses_project_cwd_and_requires_marker(tmp_path):
    worker = tmp_path / "worker.py"
    worker.write_text(
        "import os\nprint('MAIKA_WORKER_SMOKE_OK' if os.getcwd() == os.environ['EXPECT'] else 'BAD')\n",
        encoding="utf-8")
    prompt = tmp_path / "prompt.txt"
    prompt.write_text("smoke", encoding="utf-8")
    import sys, os
    os.environ["EXPECT"] = str(tmp_path.resolve())
    profile = WorkerProfile("codex", FRESH_PROCESS, sys.executable,
                            (str(worker), "{prompt_file}"), 5, False, "test")
    assert run_worker_smoke_test(profile, prompt, project_root=tmp_path)["state"] == "verified"


def test_worker_smoke_rejects_write(tmp_path):
    worker = tmp_path / "worker.py"
    worker.write_text("from pathlib import Path\nPath('made').write_text('x')\nprint('MAIKA_WORKER_SMOKE_OK')\n")
    prompt = tmp_path / "prompt.txt"
    prompt.write_text("smoke")
    import sys
    profile = WorkerProfile("codex", FRESH_PROCESS, sys.executable,
                            (str(worker), "{prompt_file}"), 5, False, "test")
    result = run_worker_smoke_test(profile, prompt, project_root=tmp_path)
    assert result["state"] == "degraded"
    assert result["worktree_clean"] is False


def test_hook_verification_rejects_wrong_managed_command(tmp_path):
    hook = tmp_path / ".codex/hooks.json"
    hook.parent.mkdir(parents=True)
    hook.write_text(json.dumps({"hooks": {"PreToolUse": [{"hooks": [{
        "id": "maika.write-gate.v1", "command": "maika hook write-gate --runtime claude --platform codex"
    }]}]}}))
    evaluator = tmp_path / ".maika/hooks/write-gate/write_gate.py"
    evaluator.parent.mkdir(parents=True)
    evaluator.write_text("")
    assert probe._verify_hook(tmp_path, "codex") == "degraded"


def test_security_fields_change_profile_fingerprint():
    path = {"version": 1, "platform": "codex", "adapter": {},
            "worker": {"strategy": "fresh_process", "executable": "x", "args": [],
                       "timeout_seconds": 10, "dangerous_permissions": False}}
    timeout = json.loads(json.dumps(path)); timeout["worker"]["timeout_seconds"] = 11
    danger = json.loads(json.dumps(path)); danger["worker"]["dangerous_permissions"] = True
    assert profile_fingerprint(path) != profile_fingerprint(timeout)
    assert profile_fingerprint(path) != profile_fingerprint(danger)


def test_hook_payload_session_identity_is_stable(tmp_path, monkeypatch):
    import types
    from cli.commands.hook import run_hook_write_gate
    project.save(tmp_path, project.enable(project._default(), "codex"))
    write_platform_runtime_profile(tmp_path, "codex")
    gate = tmp_path / ".maika/hooks/write-gate/write_gate.py"
    gate.parent.mkdir(parents=True)
    gate.write_text("", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("cli.commands.hook._load_write_gate",
                        lambda _path: types.SimpleNamespace(main=lambda **_kwargs: 0))
    payload = json.dumps({"sessionId": "conversation-7", "tool_name": "Write"})
    assert run_hook_write_gate("codex", "codex", payload) == 0
    assert run_hook_write_gate("codex", "codex", payload) == 0
    sessions = list_sessions(tmp_path)
    assert len(sessions) == 1
    assert sessions[0]["session_id"] == "conversation-7"
    assert sessions[0]["identity_source"] == "hook-payload"
