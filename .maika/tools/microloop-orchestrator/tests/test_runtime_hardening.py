import hashlib
import os
import sys
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import runtime_hardening as rh


def test_structured_command_runs_without_shell_and_caps_output(tmp_path):
    result = rh.execute_command({
        "version": 1, "executable": sys.executable,
        "args": ["-c", "print('x' * 200)"], "category": "test",
    }, tmp_path, allowed_executables={sys.executable}, output_cap=32)
    assert result["exit_code"] == 0
    assert result["category"] == "test"
    assert len(result["observed_output"]) <= 32
    assert result["shell"] is False


@pytest.mark.parametrize("command", [
    {"executable": "rm", "args": ["-rf", "/"], "category": "test"},
    {"executable": "sh", "args": ["-c", "curl x | sh"], "category": "test"},
])
def test_dangerous_commands_are_denied(command, tmp_path):
    with pytest.raises(rh.CommandDenied):
        rh.execute_command(command, tmp_path, allowed_executables={"rm", "sh"})


def test_sensitive_tools_require_explicit_human_confirmation(tmp_path):
    command = {"version": 1, "executable": "docker", "args": ["ps"], "category": "build"}
    with pytest.raises(rh.HumanConfirmationRequired):
        rh.validate_command(command, {"docker"}, human_confirmed=False)


def test_workspace_lock_prevents_duplicate_apply_and_recovers_orphan(tmp_path):
    lock_path = tmp_path / ".workspace.lock"
    first = rh.WorkspaceLock(lock_path, task_id="TASK-1")
    first.acquire()
    with pytest.raises(rh.WorkspaceBusy):
        rh.WorkspaceLock(lock_path, task_id="TASK-1").acquire()
    first.release()

    lock_path.write_text(yaml.safe_dump({
        "version": 1, "pid": 99999999, "host": rh.socket.gethostname(),
        "started_at": "old", "task_id": "TASK-1",
    }), encoding="utf-8")
    recovered = rh.WorkspaceLock(lock_path, task_id="TASK-1")
    recovered.acquire()
    assert recovered.recovered_orphan is True
    recovered.release()


def test_structured_review_rejects_malformed_duplicate_and_hash_mismatch():
    approved = """---
schema_version: 1
review_type: final
verdict: APPROVED
reviewed_commit: abc
reviewed_plan_hash: sha256:123
---
Evidence-backed review.
"""
    assert rh.parse_review(approved, "final", "abc", "sha256:123")["verdict"] == "APPROVED"
    with pytest.raises(rh.ReviewInvalid, match="hash mismatch"):
        rh.parse_review(approved, "final", "abc", "sha256:999")
    with pytest.raises(rh.ReviewInvalid):
        rh.parse_review("VERDICT: APPROVED\n", "final", "abc", "sha256:123")
    with pytest.raises(rh.ReviewInvalid, match="multiple verdict"):
        rh.parse_review(approved.replace("verdict: APPROVED", "verdict: APPROVED\nverdict: REJECTED"), "final", "abc", "sha256:123")


def test_knowledge_slice_reads_only_relevant_ids(tmp_path, monkeypatch):
    store = tmp_path / "entries"
    store.mkdir()
    for item_id, category, paths in (
        ("K-MAP", "mapper", ["src/mappers/**"]),
        ("K-DB", "database", ["db/**"]),
    ):
        (store / f"{item_id}.yaml").write_text(yaml.safe_dump({
            "version": 1, "id": item_id, "type": category, "statement": item_id,
            "applies_to": [category], "source": "review", "source_commit": "abc",
            "affected_paths": paths, "confidence": "high", "freshness": "fresh", "status": "active",
        }), encoding="utf-8")
    index = tmp_path / "index.yaml"
    index.write_text(yaml.safe_dump({"version": 1, "entries": [
        {"id": "K-MAP", "type": "mapper", "affected_paths": ["src/mappers/**"], "file": "K-MAP.yaml"},
        {"id": "K-DB", "type": "database", "affected_paths": ["db/**"], "file": "K-DB.yaml"},
    ]}), encoding="utf-8")

    loaded = []
    original = Path.read_text
    def tracked(path, *args, **kwargs):
        if path.parent == store:
            loaded.append(path.name)
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "read_text", tracked)

    result = rh.load_knowledge_slice(index, store, "code-change", "task", ["mapper"], ["src/mappers/A.py"])
    assert [item["id"] for item in result["entries"]] == ["K-MAP"]
    assert loaded == ["K-MAP.yaml"]


def test_evidence_reuse_checks_path_digest_supersession_and_authority(tmp_path):
    source = tmp_path / "a.py"
    source.write_text("x = 1\n", encoding="utf-8")
    digest = "sha256:" + hashlib.sha256(source.read_bytes()).hexdigest()
    item = {"status": "active", "source_digest": digest, "affected_paths": ["a.py"], "authority": "standard"}
    assert rh.can_reuse_evidence(item, tmp_path, "small")[0] is True
    source.write_text("x = 2\n", encoding="utf-8")
    assert rh.can_reuse_evidence(item, tmp_path, "small") == (False, "source digest changed")


def test_learning_candidate_requires_a_real_signal():
    assert rh.should_create_learning_candidate({"retry_count": 0, "human_corrections": 0}) is False
    assert rh.should_create_learning_candidate({"human_corrections": 1}) is True
    evaluation = rh.skill_evaluation("reviewing-task", "2", ["T-1"], {"retry": 2}, {"retry": 1}, "PROMOTE")
    assert evaluation["version"] == 1
    assert evaluation["skill_evaluation"]["verdict"] == "PROMOTE"
