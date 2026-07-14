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
    # A fixed script (not inline `-c`, which is now denied) exercises the
    # shell-free executor + output cap.
    script = tmp_path / "emit.py"
    script.write_text("print('x' * 200)\n", encoding="utf-8")
    result = rh.execute_command({
        "version": 1, "executable": sys.executable,
        "args": [str(script)], "category": "test",
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


def test_validate_command_denies_inline_interpreter_code():
    # The plan's headline vuln: python -c "import shutil; shutil.rmtree('src')".
    with pytest.raises(rh.CommandDenied):
        rh.validate_command(
            {"version": 1, "executable": "python",
             "args": ["-c", "import shutil; shutil.rmtree('src')"], "category": "test"},
            allowed_executables={"python"},
        )
    with pytest.raises(rh.CommandDenied):
        rh.validate_command(
            {"version": 1, "executable": "node", "args": ["-e", "process.exit(0)"], "category": "test"},
            allowed_executables={"node"},
        )


def test_validate_command_denies_path_form_executable_not_allowlisted():
    # A fake interpreter dropped at /tmp/python must not pass just because its
    # basename matches an allowlisted "python".
    with pytest.raises(rh.CommandDenied):
        rh.validate_command(
            {"version": 1, "executable": "/tmp/python", "args": ["x.py"], "category": "test"},
            allowed_executables={"python"},
        )


def test_validate_command_allows_full_path_when_allowlisted_verbatim():
    # An explicit trusted full path (sys.executable, ./gradlew) is fine when the
    # allowlist names it verbatim; running a script (not -c) is allowed.
    spec = rh.validate_command(
        {"version": 1, "executable": sys.executable, "args": ["smoke.py"], "category": "test"},
        allowed_executables={sys.executable},
    )
    assert spec["executable"] == sys.executable


def test_validate_command_accepts_windows_executable_extension():
    # On Windows sys.executable's basename is "python.exe"; it must match the
    # "python" allowlist entry so verification commands are not denied there.
    spec = rh.validate_command(
        {"version": 1, "executable": "python.exe", "args": ["-m", "pytest", "-q"], "category": "test"},
        allowed_executables={"python"},
    )
    assert spec["executable"] == "python.exe"


def test_validate_command_does_not_strip_non_executable_extension():
    # Only known executable extensions (.exe/.bat/.cmd/.com) are stripped; a
    # ".py" file must not be able to masquerade as an allowlisted interpreter.
    with pytest.raises(rh.CommandDenied):
        rh.validate_command(
            {"version": 1, "executable": "python.py", "args": [], "category": "test"},
            allowed_executables={"python"},
        )


def test_sensitive_tools_require_explicit_human_confirmation(tmp_path):
    command = {"version": 1, "executable": "docker", "args": ["ps"], "category": "build"}
    with pytest.raises(rh.HumanConfirmationRequired):
        rh.validate_command(command, {"docker"}, human_confirmed=False)


def test_verification_profile_compiles_structured_argv(tmp_path):
    registry = rh.load_verification_profiles()
    command = rh.compile_verification_command({
        "profile": "pytest-paths", "parameters": {"paths": ["tests/test_unit.py"], "tests": "happy path"},
    }, registry, tmp_path)
    assert command["executable"] == "pytest"
    assert command["args"] == ["tests/test_unit.py", "-k", "happy path"]
    assert command["category"] == "test"


def test_verification_profile_rejects_unknown_and_path_escape(tmp_path):
    registry = rh.load_verification_profiles()
    with pytest.raises(rh.CommandDenied, match="unknown verification profile"):
        rh.compile_verification_command({"profile": "arbitrary"}, registry, tmp_path)
    with pytest.raises(rh.CommandDenied, match="escapes repo"):
        rh.compile_verification_command({
            "profile": "pytest-paths", "parameters": {"paths": ["../outside.py"]},
        }, registry, tmp_path)


def test_verification_profile_rejects_repo_local_fake_executable(tmp_path, monkeypatch):
    fake = tmp_path / "pytest"
    fake.write_text("fake\n", encoding="utf-8")
    fake.chmod(0o755)
    if os.name == "nt":
        # shutil.which on Windows resolves via PATHEXT, not a bare name — give the
        # repo-local fake a .bat so it is actually found (and then rejected).
        (tmp_path / "pytest.bat").write_text("@echo off\n", encoding="utf-8")
    monkeypatch.setenv("PATH", str(tmp_path))
    with pytest.raises(rh.CommandDenied, match="resolves inside repo"):
        rh.compile_verification_command({"profile": "pytest-paths", "parameters": {"paths": []}},
                                        rh.load_verification_profiles(), tmp_path)


def test_empty_config_allowlist_denies_instead_of_falling_back():
    with pytest.raises(rh.CommandDenied, match="not allowlisted"):
        rh.validate_command({"executable": "python", "args": ["--version"]}, allowed_executables=[])


def test_trusted_approval_is_hash_bound_and_ignores_forged_source(tmp_path):
    command = {"executable": "docker", "args": ["ps"]}
    approval = tmp_path / "approval.yaml"
    approval.write_text(yaml.safe_dump({
        "version": 1, "source": "agent-artifact", "change_id": "demo",
        "command_hash": rh.verification_command_hash(command),
    }), encoding="utf-8")
    assert rh.trusted_approval_matches(approval, "demo", command) is False
    doc = yaml.safe_load(approval.read_text(encoding="utf-8"))
    doc["source"] = "cli-user-action"
    approval.write_text(yaml.safe_dump(doc), encoding="utf-8")
    assert rh.trusted_approval_matches(approval, "demo", command) is True
    assert rh.trusted_approval_matches(approval, "demo", {"executable": "docker", "args": ["run"]}) is False


def test_process_alive_is_cross_platform_and_non_destructive():
    # Our own pid is alive; a very high pid is not. The check must never signal
    # or terminate the target (POSIX os.kill(pid, 0) is a probe, but on Windows
    # os.kill with a non-CTRL signal calls TerminateProcess).
    assert rh._process_alive(os.getpid()) is True
    assert rh._process_alive(99999999) is False
    assert rh._process_alive(0) is False
    assert rh._process_alive(-1) is False


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


def test_workspace_lock_remote_lease_policy_and_force_unlock_audit(tmp_path):
    lock_path = tmp_path / "generated" / "WORKSPACE.lock"
    lock_path.parent.mkdir()
    future = (rh.datetime.now(rh.timezone.utc) + rh.timedelta(minutes=5)).isoformat()
    lock_path.write_text(yaml.safe_dump({
        "version": 1, "pid": 99999999, "host": "remote-host", "task_id": "TASK-1",
        "lease": {"expires_at": future},
    }), encoding="utf-8")
    with pytest.raises(rh.WorkspaceBusy):
        rh.WorkspaceLock(lock_path, "TASK-1").acquire()

    past = (rh.datetime.now(rh.timezone.utc) - rh.timedelta(seconds=1)).isoformat()
    doc = yaml.safe_load(lock_path.read_text(encoding="utf-8"))
    doc["lease"]["expires_at"] = past
    lock_path.write_text(yaml.safe_dump(doc), encoding="utf-8")
    recovered = rh.WorkspaceLock(lock_path, "TASK-1")
    recovered.acquire()
    assert recovered.recovered_orphan is True
    recovered.release()
    lock_path.write_text(yaml.safe_dump(doc), encoding="utf-8")
    assert rh.WorkspaceLock.force_unlock(lock_path, "TASK-1") is True
    audit = (lock_path.parent / "LOCK_AUDIT.jsonl").read_text(encoding="utf-8")
    assert "recovered_expired_or_orphaned" in audit
    assert "force_unlock" in audit


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
    crlf = approved.replace("\n", "\r\n")
    assert rh.parse_review(crlf, "final", "abc", "sha256:123")["verdict"] == "APPROVED"


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


def test_canonical_knowledge_slice_rejects_stale_low_authority_and_superseded(tmp_path):
    source = tmp_path / "src.py"
    source.write_text("current\n", encoding="utf-8")
    current = "sha256:" + hashlib.sha256(source.read_bytes()).hexdigest()
    store = tmp_path / "knowledge"
    store.mkdir()
    entries = {
        "GOOD": {"authority": "standard", "source_digest": current},
        "STALE": {"authority": "standard", "source_digest": "sha256:old"},
        "LOW": {"authority": "small", "source_digest": current},
        "OLD": {"authority": "standard", "source_digest": current, "superseded_by": "GOOD"},
    }
    refs = []
    for item_id, fields in entries.items():
        item = {"version": 1, "id": item_id, "type": "convention", "status": "active",
                "statement": item_id, "source": {"file": "src.py"},
                "affected_paths": ["src/**"], **fields}
        (store / f"{item_id}.yaml").write_text(yaml.safe_dump(item), encoding="utf-8")
        refs.append({"id": item_id, "type": "convention", "status": "active",
                     "file": f"{item_id}.yaml", "affected_paths": ["src/**"]})
    index = tmp_path / "index.yaml"
    index.write_text(yaml.safe_dump({"version": 1, "entries": refs}), encoding="utf-8")

    result = rh.select_knowledge_slice(
        index, store, tmp_path, "code-change", "task", ["convention"], ["src/a.py"],
        task_class="standard",
    )
    assert result["relevant_ids"] == ["GOOD"]
    assert result["entries"][0]["reuse_decision"] == "reused"
    assert result["evidence_metrics"]["reused"] == 1
    assert result["evidence_metrics"]["rejected_stale"] == 2
    assert result["evidence_metrics"]["rejected_authority"] == 1


def test_architectural_knowledge_requires_revalidation_and_trim_is_deterministic(tmp_path):
    source = tmp_path / "src.py"
    source.write_text("current\n", encoding="utf-8")
    digest = "sha256:" + hashlib.sha256(source.read_bytes()).hexdigest()
    store = tmp_path / "knowledge"
    store.mkdir()
    refs = []
    for item_id, revalidated in (("B", True), ("A", True), ("NO", False)):
        item = {"id": item_id, "type": "decision", "status": "active",
                "source": {"file": "src.py"}, "source_digest": digest,
                "authority": "architectural", "affected_paths": ["src/**"]}
        if revalidated:
            item["revalidated_at"] = "2026-07-11T00:00:00Z"
        (store / f"{item_id}.yaml").write_text(yaml.safe_dump(item), encoding="utf-8")
        refs.append({"id": item_id, "type": "decision", "status": "active",
                     "file": f"{item_id}.yaml", "affected_paths": ["src/**"]})
    index = tmp_path / "index.yaml"
    index.write_text(yaml.safe_dump({"entries": refs}), encoding="utf-8")
    result = rh.select_knowledge_slice(
        index, store, tmp_path, "architecture", "task", ["decision"], ["src/a.py"],
        task_class="architectural", max_items=1,
    )
    assert result["relevant_ids"] == ["A"]
    assert result["evidence_metrics"]["revalidated"] == 2
    assert result["evidence_metrics"]["evidence_omitted"] == 1


def test_learning_candidate_requires_a_real_signal():
    assert rh.should_create_learning_candidate({"retry_count": 0, "human_corrections": 0}) is False
    assert rh.should_create_learning_candidate({"human_corrections": 1}) is True
    evaluation = rh.skill_evaluation("reviewing-task", "2", ["T-1"], {"retry": 2}, {"retry": 1}, "PROMOTE")
    assert evaluation["version"] == 1
    assert evaluation["skill_evaluation"]["verdict"] == "PROMOTE"
