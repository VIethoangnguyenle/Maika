import importlib.util
import hashlib
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml


MOD = Path(__file__).resolve().parents[1] / "write_gate.py"
spec = importlib.util.spec_from_file_location("write_gate", MOD)
wg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wg)


def test_extracts_file_path_from_claude_write_payload():
    payload = {"tool_name": "Write", "tool_input": {"file_path": "src/App.java"}}
    assert wg.extract_target_paths(payload) == [Path("src/App.java")]


def test_extracts_paths_from_codex_apply_patch_payload():
    payload = {
        "tool_name": "apply_patch",
        "tool_input": {
            "command": "*** Begin Patch\n"
            "*** Update File: src/App.java\n"
            "@@\n"
            "-old\n"
            "+new\n"
            "*** Add File: docs/superpowers/specs/x.md\n"
            "+# Spec\n"
            "*** End Patch\n"
        },
    }
    assert wg.extract_target_paths(payload) == [
        Path("src/App.java"),
        Path("docs/superpowers/specs/x.md"),
    ]


def test_extracts_path_from_antigravity_toolcall_payload():
    payload = {
        "toolCall": {
            "name": "replace_file_content",
            "args": {"file_path": "src/App.java"},
        }
    }
    assert wg.extract_target_paths(payload) == [Path("src/App.java")]


def test_extracts_targetfile_from_antigravity_toolcall_payload():
    payload = {
        "toolCall": {
            "name": "replace_file_content",
            "args": {"TargetFile": "src/App.java"},
        }
    }
    assert wg.extract_target_paths(payload) == [Path("src/App.java")]


def test_extracts_targetfile_from_antigravity_tool_input_payload():
    payload = {
        "tool_name": "write_to_file",
        "tool_input": {"TargetFile": "src/App.java"},
    }
    assert wg.extract_target_paths(payload) == [Path("src/App.java")]


def test_framework_artifacts_require_an_authorized_role_and_retired_specs_block(tmp_path):
    assert wg.evaluate_write(tmp_path, Path(".maika/changes/demo/STATE.yaml")).ok is False
    retired = "".join(("open", "spec")) + "/changes/x/specs/foo/spec.md"
    result = wg.evaluate_write(tmp_path, Path(retired))
    assert result.ok is False
    assert "vNext" in result.reason


def test_blocks_app_write_without_vnext_scope(tmp_path):
    result = wg.evaluate_write(tmp_path, Path("src/App.java"))
    assert result.ok is False
    assert "vNext" in result.reason


def test_allows_documentation_write_without_checkpoint(tmp_path):
    for doc in ("docs/ARCHITECTURE.md", "ANALYSIS.md", "notes/x.markdown", "a.txt", "b.rst"):
        assert wg.evaluate_write(tmp_path, Path(doc)).ok is True, doc


def test_documentation_exemption_is_case_insensitive(tmp_path):
    assert wg.evaluate_write(tmp_path, Path("README.MD")).ok is True


def test_main_allows_documentation_write(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    payload = {"tool_name": "Write", "tool_input": {"file_path": "docs/ARCHITECTURE.md"}}
    code = wg.main(["--framework-root", ".maika"], stdin_text=json.dumps(payload))
    assert code == 0


def test_main_blocks_absolute_framework_knowledge_write_without_curator_role(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    target = tmp_path / ".maika" / "knowledge" / "long-term" / "author-dna.yaml"
    payload = {"tool_name": "Write", "tool_input": {"file_path": str(target)}}
    code = wg.main(["--framework-root", ".maika"], stdin_text=json.dumps(payload))
    assert code == 2


def test_main_blocks_absolute_framework_knowledge_write_from_subdir_without_role(tmp_path, monkeypatch):
    _init_git_repo(tmp_path)
    subdir = tmp_path / "src"
    subdir.mkdir()
    monkeypatch.chdir(subdir)
    target = tmp_path / ".maika" / "knowledge" / "long-term" / "author-dna.yaml"
    payload = {"tool_name": "Write", "tool_input": {"file_path": str(target)}}
    code = wg.main(["--framework-root", ".maika"], stdin_text=json.dumps(payload))
    assert code == 2


def test_bash_write_to_documentation_allowed(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    payload = {"tool_name": "Bash", "tool_input": {"command": "echo x > docs/ARCHITECTURE.md"}}
    code = wg.main(["--framework-root", ".maika"], stdin_text=json.dumps(payload))
    assert code == 0


def _setup_vnext_scope(tmp_path, target="src/App.java", *, state="EXECUTING", engine="vnext"):
    framework = tmp_path / ".maika"
    profiles = framework / "profiles"
    profiles.mkdir(parents=True, exist_ok=True)
    (profiles / "execution-mode.yaml").write_text(f"workflow_engine: {engine}\n", encoding="utf-8")
    active = framework / "knowledge" / "active"
    active.mkdir(parents=True, exist_ok=True)
    (active / "AGENT_TRANSPARENCY.md").write_text("phase_state: executing\n", encoding="utf-8")
    ws = framework / "changes" / "demo"
    (ws / "generated").mkdir(parents=True, exist_ok=True)
    (ws / "STATE.yaml").write_text(f"change_id: demo\nstate: {state}\n", encoding="utf-8")
    (ws / "generated" / "PLAN_VALIDATION.json").write_text(
        json.dumps({"verdict": "APPROVED"}),
        encoding="utf-8",
    )
    (ws / "generated" / "PLAN_MANIFEST.json").write_text(
        json.dumps({"plan_sha256": "sha"}),
        encoding="utf-8",
    )
    (ws / "generated" / "TASK_QUEUE.json").write_text(
        json.dumps({
            "change_id": "demo",
            "plan_sha256": "sha",
            "tasks": [{
                "id": "TASK-001",
                "status": "in_progress",
                "files": {"create": [], "modify": [target], "delete": [], "test": []},
            }],
        }),
        encoding="utf-8",
    )
    return active


def _setup_lightweight_scope(tmp_path, target="src/App.java", *, expired=False):
    framework = tmp_path / ".maika"
    (framework / "profiles").mkdir(parents=True)
    (framework / "profiles" / "execution-mode.yaml").write_text(
        "workflow_engine: vnext\n", encoding="utf-8"
    )
    ws = framework / "changes" / "demo"
    (ws / "generated").mkdir(parents=True)
    (ws / "STATE.yaml").write_text("change_id: demo\nstate: EXECUTING\n", encoding="utf-8")
    task = {
        "version": 1, "change_id": "demo", "class": "small",
        "scope": {"files": {"modify": [target], "test": []}},
    }
    (ws / "TASK.yaml").write_text(yaml.safe_dump(task), encoding="utf-8")
    (ws / "EVIDENCE.yaml").write_text("version: 1\nitems: []\n", encoding="utf-8")
    scope = {"create": [], "modify": [target], "delete": [], "test": []}
    expires = datetime.now(timezone.utc) + timedelta(seconds=-1 if expired else 60)
    contract = {
        "version": 1, "change_id": "demo", "task_class": "small",
        "execution_id": "EXEC-demo-1", "state": "EXECUTING", "status": "active",
        "task_hash": "sha256:" + hashlib.sha256((ws / "TASK.yaml").read_bytes()).hexdigest(),
        "evidence_hash": "sha256:" + hashlib.sha256((ws / "EVIDENCE.yaml").read_bytes()).hexdigest(),
        "scope_hash": wg._canonical_hash(scope), "scope": scope,
        "role": "application-implementer", "runtime": {"lease_expires_at": expires.isoformat()},
    }
    (ws / "generated" / "LIGHTWEIGHT_EXECUTION.yaml").write_text(
        yaml.safe_dump(contract), encoding="utf-8"
    )
    return ws


def test_allows_app_write_with_vnext_scope(tmp_path):
    _setup_vnext_scope(tmp_path)
    result = wg.evaluate_write(tmp_path, Path("src/App.java"), framework_root=".maika")
    assert result.ok is True


def test_lightweight_contract_allows_declared_app_and_result_only(tmp_path):
    _setup_lightweight_scope(tmp_path)
    assert wg.evaluate_write(tmp_path, Path("src/App.java"), framework_root=".maika").ok is True
    assert wg.evaluate_write(tmp_path, Path(".maika/changes/demo/RESULT.yaml"), framework_root=".maika").ok is True
    denied = wg.evaluate_write(tmp_path, Path("src/Other.java"), framework_root=".maika")
    assert denied.ok is False
    assert "ngoài files" in denied.reason


def test_lightweight_contract_rejects_task_tamper_and_expired_lease(tmp_path):
    ws = _setup_lightweight_scope(tmp_path)
    (ws / "TASK.yaml").write_text("version: 1\nchange_id: demo\nclass: small\n", encoding="utf-8")
    assert "hash mismatch" in wg.evaluate_write(
        tmp_path, Path("src/App.java"), framework_root=".maika"
    ).reason

    other = tmp_path / "expired"
    other.mkdir()
    _setup_lightweight_scope(other, expired=True)
    assert "hết hạn" in wg.evaluate_write(
        other, Path("src/App.java"), framework_root=".maika"
    ).reason


def test_blocks_app_write_without_executing_vnext_change(tmp_path):
    _setup_vnext_scope(tmp_path, state="PLANNING")
    result = wg.evaluate_write(tmp_path, Path("src/App.java"), framework_root=".maika")
    assert result.ok is False
    assert "EXECUTING" in result.reason


def test_blocks_app_write_when_vnext_scope_targets_other_file(tmp_path):
    _setup_vnext_scope(tmp_path, target="src/Other.java")
    result = wg.evaluate_write(tmp_path, Path("src/App.java"), framework_root=".maika")
    assert result.ok is False
    assert "src/App.java" in result.reason


def test_path_prefix_helper_requires_segment_boundary():
    assert wg._is_same_or_child(".maika/changes/demo", ".maika/changes/demo") is True
    assert wg._is_same_or_child(".maika/changes/demo/results/TASK-001.yaml", ".maika/changes/demo") is True
    assert wg._is_same_or_child(".maika/changes/demo-extra/results/TASK-001.yaml", ".maika/changes/demo") is False


def test_blocks_app_write_when_workflow_engine_is_not_vnext(tmp_path):
    _setup_vnext_scope(tmp_path, engine="legacy")
    result = wg.evaluate_write(tmp_path, Path("src/App.java"), framework_root=".maika")
    assert result.ok is False
    assert "workflow_engine" in result.reason


def test_main_blocks_with_exit_2_for_claude_pretooluse(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    payload = {"tool_name": "Write", "tool_input": {"file_path": "src/App.java"}}
    code = wg.main(["--framework-root", ".claude"], stdin_text=json.dumps(payload))
    captured = capsys.readouterr()
    assert code == 2
    assert "vNext" in captured.err


def test_main_blocks_when_edit_payload_has_no_target_path(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    payload = {"tool_name": "Write", "tool_input": {"content": "x"}}
    code = wg.main(["--framework-root", ".claude"], stdin_text=json.dumps(payload))
    captured = capsys.readouterr()
    assert code == 2
    assert "Unable to identify target path" in captured.err


def test_main_blocks_with_codex_json_decision(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "apply_patch",
        "tool_input": {
            "command": "*** Begin Patch\n*** Update File: src/App.java\n@@\n-x\n+y\n*** End Patch\n"
        },
    }
    code = wg.main(["--framework-root", ".agents", "--runtime", "codex"], stdin_text=json.dumps(payload))
    captured = capsys.readouterr()
    assert code == 0
    out = json.loads(captured.out)
    assert out["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_main_blocks_with_antigravity_json_decision(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    payload = {"toolCall": {"name": "write_to_file", "args": {"file_path": "src/App.java"}}}
    code = wg.main(["--framework-root", ".agents", "--runtime", "antigravity"], stdin_text=json.dumps(payload))
    captured = capsys.readouterr()
    assert code == 0
    assert json.loads(captured.out)["decision"] == "deny"


def test_parse_redirect_write():
    paths, unresolved = wg.parse_shell_writes("echo x > src/App.java")
    assert paths == [Path("src/App.java")]
    assert unresolved is False


def test_parse_append_redirect():
    paths, _ = wg.parse_shell_writes("echo x >> src/App.java")
    assert paths == [Path("src/App.java")]


def test_parse_ignores_devnull_and_fd_redirect():
    paths, unresolved = wg.parse_shell_writes("run_tests > /dev/null 2>&1")
    assert paths == []
    assert unresolved is True


def test_parse_tee():
    paths, _ = wg.parse_shell_writes("echo x | tee src/App.java")
    assert paths == [Path("src/App.java")]


def test_parse_sed_inplace():
    paths, _ = wg.parse_shell_writes("sed -i 's/a/b/' src/App.java")
    assert paths == [Path("src/App.java")]


def test_parse_cp_and_mv_dest():
    assert wg.parse_shell_writes("cp /tmp/x src/App.java")[0] == [Path("src/App.java")]
    assert wg.parse_shell_writes("mv old.java src/App.java")[0] == [Path("src/App.java")]


def test_parse_dd_of():
    paths, _ = wg.parse_shell_writes("dd if=/tmp/x of=src/App.java")
    assert paths == [Path("src/App.java")]


def test_parse_patch_format():
    paths, _ = wg.parse_shell_writes("*** Add File: src/App.java\n+code\n")
    assert paths == [Path("src/App.java")]


def test_parse_prettier_write():
    paths, _ = wg.parse_shell_writes("prettier --write src/App.js")
    assert paths == [Path("src/App.js")]


def test_parse_readonly_command_has_no_writes():
    paths, unresolved = wg.parse_shell_writes("grep -r foo src && ls -la")
    assert paths == []
    assert unresolved is False


def test_parse_dynamic_path_is_unresolved():
    paths, unresolved = wg.parse_shell_writes('tee "$TARGET"')
    assert paths == []
    assert unresolved is True


def test_parse_git_apply_is_unresolved():
    paths, unresolved = wg.parse_shell_writes("git apply fix.patch")
    assert paths == []
    assert unresolved is True


def test_parse_gofmt_write():
    assert wg.parse_shell_writes("gofmt -w main.go")[0] == [Path("main.go")]


def test_parse_ruff_fix_and_format():
    assert wg.parse_shell_writes("ruff --fix src/app.py")[0] == [Path("src/app.py")]
    assert wg.parse_shell_writes("ruff format src/app.py")[0] == [Path("src/app.py")]


def test_parse_black_write():
    assert wg.parse_shell_writes("black src/app.py")[0] == [Path("src/app.py")]


def test_parse_install_dest():
    assert wg.parse_shell_writes("install -m 644 src/x build/x")[0] == [Path("build/x")]


def test_parse_git_checkout_and_restore():
    assert wg.parse_shell_writes("git checkout -- src/App.java")[0] == [Path("src/App.java")]
    assert wg.parse_shell_writes("git restore src/App.java")[0] == [Path("src/App.java")]


def test_parse_verb_via_absolute_path():
    assert wg.parse_shell_writes("/usr/bin/sed -i 's/a/b/' src/App.java")[0] == [Path("src/App.java")]


def test_parse_force_redirect():
    assert wg.parse_shell_writes("echo x >| src/App.java")[0] == [Path("src/App.java")]


def test_parse_stderr_redirect_to_file_is_caught():
    paths, _ = wg.parse_shell_writes("npm run build 2> src/App.java")
    assert paths == [Path("src/App.java")]


def test_parse_stdout_fd_redirect_to_file_is_caught():
    paths, _ = wg.parse_shell_writes("cmd 1> out.txt")
    assert paths == [Path("out.txt")]


def test_parse_fd_duplication_not_a_target():
    paths, unresolved = wg.parse_shell_writes("cmd 2>&1")
    assert paths == []
    assert unresolved is True


def test_parse_subshell_redirect_strips_paren():
    paths, _ = wg.parse_shell_writes("(echo x > src/App.java)")
    assert paths == [Path("src/App.java")]


def _init_git_repo(root):
    subprocess.run(["git", "init", "-q"], cwd=str(root), check=True)
    (root / ".gitignore").write_text("coverage/\ndist/\n", encoding="utf-8")


def test_git_ignored_true_for_ignored_path(tmp_path):
    _init_git_repo(tmp_path)
    assert wg._git_ignored(tmp_path, Path("coverage/lcov.info")) is True


def test_git_ignored_false_for_tracked_source(tmp_path):
    _init_git_repo(tmp_path)
    assert wg._git_ignored(tmp_path, Path("src/App.java")) is False


def test_git_ignored_false_when_not_a_git_repo(tmp_path):
    assert wg._git_ignored(tmp_path, Path("coverage/lcov.info")) is False


def test_bash_write_to_code_blocks_without_checkpoint(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    payload = {"tool_name": "Bash", "tool_input": {"command": "echo x > src/App.java"}}
    code = wg.main(["--framework-root", ".maika"], stdin_text=json.dumps(payload))
    captured = capsys.readouterr()
    assert code == 2
    assert "vNext" in captured.err


def test_bash_write_to_code_allows_with_vnext_scope(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup_vnext_scope(tmp_path)
    payload = {"tool_name": "Bash", "tool_input": {"command": "tee src/App.java"}}
    code = wg.main(["--framework-root", ".maika"], stdin_text=json.dumps(payload))
    assert code == 0


def test_bash_readonly_command_allowed_fail_open(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    payload = {"tool_name": "Bash", "tool_input": {"command": "grep -r foo src && ls"}}
    code = wg.main(["--framework-root", ".maika"], stdin_text=json.dumps(payload))
    assert code == 0


def test_bash_write_to_gitignored_path_is_still_gated(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    subprocess.run(["git", "init", "-q"], cwd=str(tmp_path), check=True)
    (tmp_path / ".gitignore").write_text("coverage/\n", encoding="utf-8")
    payload = {"tool_name": "Bash", "tool_input": {"command": "echo x > coverage/lcov.info"}}
    code = wg.main(["--framework-root", ".maika"], stdin_text=json.dumps(payload))
    assert code == 2


def test_bash_write_to_framework_artifact_requires_role(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    payload = {"tool_name": "Bash", "tool_input": {"command": "echo x > .maika/knowledge/active/REQUIREMENT.md"}}
    code = wg.main(["--framework-root", ".maika"], stdin_text=json.dumps(payload))
    assert code == 2


def test_unified_authoring_execution_allows_declared_output_without_executing_task(
    tmp_path, monkeypatch,
):
    monkeypatch.chdir(tmp_path)
    profiles = tmp_path / ".maika" / "profiles"
    profiles.mkdir(parents=True)
    (profiles / "execution-mode.yaml").write_text(
        "workflow_engine: vnext\n", encoding="utf-8"
    )
    ws = tmp_path / ".maika" / "changes" / "C-1"
    (ws / "generated").mkdir(parents=True)
    (ws / "STATE.yaml").write_text("state: EXPLORING\n", encoding="utf-8")
    expires = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
    (ws / "generated" / "ACTIVE_EXECUTION.yaml").write_text(yaml.safe_dump({
        "version": 1,
        "execution_id": "EXEC-C-1-grounding",
        "change_id": "C-1",
        "role": "grounding",
        "workflow_state": "EXPLORING",
        "status": "active",
        "allowed_outputs": ["exploration/GROUNDING.yaml"],
        "allowed_source_scope": [],
        "owner_token": "owner-1",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "lease_expires_at": expires,
        "prompt_hash": "sha256:" + "a" * 64,
    }), encoding="utf-8")
    payload = {
        "tool_name": "Write",
        "tool_input": {"file_path": ".maika/changes/C-1/exploration/GROUNDING.yaml"},
    }
    assert wg.main(["--framework-root", ".maika"], stdin_text=json.dumps(payload)) == 0


def test_expired_unified_execution_does_not_authorize_write(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    profiles = tmp_path / ".maika" / "profiles"
    profiles.mkdir(parents=True)
    (profiles / "execution-mode.yaml").write_text(
        "workflow_engine: vnext\n", encoding="utf-8"
    )
    ws = tmp_path / ".maika" / "changes" / "C-1"
    (ws / "generated").mkdir(parents=True)
    (ws / "STATE.yaml").write_text("state: EXPLORING\n", encoding="utf-8")
    expires = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    (ws / "generated" / "ACTIVE_EXECUTION.yaml").write_text(yaml.safe_dump({
        "version": 1, "execution_id": "expired", "change_id": "C-1",
        "role": "grounding", "workflow_state": "EXPLORING", "status": "active",
        "allowed_outputs": ["exploration/GROUNDING.yaml"],
        "allowed_source_scope": [], "owner_token": "owner-1",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "lease_expires_at": expires, "prompt_hash": "sha256:" + "a" * 64,
    }), encoding="utf-8")
    payload = {
        "tool_name": "Write",
        "tool_input": {"file_path": ".maika/changes/C-1/exploration/GROUNDING.yaml"},
    }
    assert wg.main(["--framework-root", ".maika"], stdin_text=json.dumps(payload)) == 2


def test_bash_dynamic_write_fails_closed_without_active_scope(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    payload = {"tool_name": "Bash", "tool_input": {"command": 'tee "$TARGET"'}}
    code = wg.main(["--framework-root", ".maika"], stdin_text=json.dumps(payload))
    captured = capsys.readouterr()
    assert code == 2
    assert "unresolved" in captured.err.lower()


@pytest.mark.parametrize("command", [
    'python -c "open(\'src/Outside.java\', \'w\').write(\'x\')"',
    'node -e "require(\'fs\').writeFileSync(\'src/Outside.java\', \'x\')"',
    "unzip payload.zip",
    "tar -xf payload.tar",
    "git reset --hard",
    "mvn spotless:apply",
])
def test_unknown_or_indirect_mutators_never_fail_open(command):
    _, unresolved = wg.parse_shell_writes(command)
    assert unresolved is True


@pytest.mark.parametrize(("command", "target"), [
    ("touch src/Outside.java", "src/Outside.java"),
    ("truncate -s 0 src/App.java", "src/App.java"),
])
def test_direct_mutators_produce_gated_targets(command, target):
    paths, unresolved = wg.parse_shell_writes(command)
    assert paths == [Path(target)]
    assert unresolved is False


def test_unknown_executable_is_unresolved_but_known_readonly_is_not():
    assert wg.parse_shell_writes("custom-tool --do-something")[1] is True
    assert wg.parse_shell_writes("rg pattern src && git status")[1] is False


def test_bash_stderr_redirect_to_code_blocks_without_checkpoint(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    payload = {"tool_name": "Bash", "tool_input": {"command": "npm run build 2> src/App.java"}}
    code = wg.main(["--framework-root", ".maika"], stdin_text=json.dumps(payload))
    captured = capsys.readouterr()
    assert code == 2
    assert "vNext" in captured.err


# ---------- SESSION-GATE (context-overflow safety net) ----------


def _setup_valid_app_context(tmp_path, target="src/App.java"):
    return _setup_vnext_scope(tmp_path, target=target)


def _write_session_state(active, identity, phase="phase-2-done"):
    (active / ".session_state.json").write_text(
        json.dumps({"phases": {phase: {"session_identity": identity, "ts": "t"}}}),
        encoding="utf-8",
    )


def test_session_gate_blocks_same_session_code_write(tmp_path):
    active = _setup_valid_app_context(tmp_path)
    _write_session_state(active, "sid:abc")
    result = wg.evaluate_write(
        tmp_path, Path("src/App.java"), framework_root=".maika",
        session_identity="sid:abc",
    )
    assert result.ok is False
    assert "[SESSION-GATE]" in result.reason


def test_session_gate_allows_new_session(tmp_path):
    active = _setup_valid_app_context(tmp_path)
    _write_session_state(active, "sid:abc")
    result = wg.evaluate_write(
        tmp_path, Path("src/App.java"), framework_root=".maika",
        session_identity="sid:xyz",
    )
    assert result.ok is True


def test_session_gate_degrades_without_identity(tmp_path):
    active = _setup_valid_app_context(tmp_path)
    _write_session_state(active, "sid:abc")
    result = wg.evaluate_write(
        tmp_path, Path("src/App.java"), framework_root=".maika",
        session_identity=None,
    )
    assert result.ok is True


def test_session_override_allows_and_logs_violation(tmp_path):
    active = _setup_valid_app_context(tmp_path)
    _write_session_state(active, "sid:abc")
    (active / "SESSION_OVERRIDE.md").write_text(
        "ticket: ABC-1\nuser-confirm: đồng ý tiếp tục cùng session\nreason: hotfix 1 dòng\n",
        encoding="utf-8",
    )
    result = wg.evaluate_write(
        tmp_path, Path("src/App.java"), framework_root=".maika",
        session_identity="sid:abc",
    )
    assert result.ok is True
    transparency = (active / "AGENT_TRANSPARENCY.md").read_text(encoding="utf-8")
    assert "[VIOLATION][SESSION-GATE]" in transparency


def test_session_override_incomplete_still_blocks(tmp_path):
    active = _setup_valid_app_context(tmp_path)
    _write_session_state(active, "sid:abc")
    (active / "SESSION_OVERRIDE.md").write_text("reason: quên format\n", encoding="utf-8")
    result = wg.evaluate_write(
        tmp_path, Path("src/App.java"), framework_root=".maika",
        session_identity="sid:abc",
    )
    assert result.ok is False


def test_record_session_state_first_writer_wins(tmp_path):
    active = tmp_path / ".maika" / "knowledge" / "active"
    active.mkdir(parents=True)
    (active / "AGENT_TRANSPARENCY.md").write_text(
        "## Phase State\nphase_state: phase-1-done\n", encoding="utf-8"
    )
    wg.record_session_state(tmp_path, ".maika", "sid:one")
    wg.record_session_state(tmp_path, ".maika", "sid:two")
    state = json.loads((active / ".session_state.json").read_text(encoding="utf-8"))
    assert state["phases"]["phase-1-done"]["session_identity"] == "sid:one"


def test_record_session_state_ignores_other_phase(tmp_path):
    active = tmp_path / ".maika" / "knowledge" / "active"
    active.mkdir(parents=True)
    (active / "AGENT_TRANSPARENCY.md").write_text(
        "phase_state: applying\n", encoding="utf-8"
    )
    wg.record_session_state(tmp_path, ".maika", "sid:one")
    assert not (active / ".session_state.json").exists()


def _write_proc_stat(proc_root, pid, comm, ppid, starttime):
    d = proc_root / str(pid)
    d.mkdir(parents=True)
    tokens = ["S", str(ppid)] + ["0"] * 17 + [str(starttime)]
    (d / "stat").write_text(f"{pid} ({comm}) " + " ".join(tokens), encoding="utf-8")


def test_process_identity_skips_shell_ancestors(tmp_path, monkeypatch):
    proc = tmp_path / "proc"
    _write_proc_stat(proc, 100, "sh", 50, 8888)     # wrapper shell của hook
    _write_proc_stat(proc, 50, "agy", 1, 4242)      # process agent runtime
    monkeypatch.setattr(wg.os, "getppid", lambda: 100)
    assert wg._process_identity(proc_root=proc) == "pid:50:4242"


def test_process_identity_none_without_proc(tmp_path, monkeypatch):
    monkeypatch.setattr(wg.os, "getppid", lambda: 100)
    assert wg._process_identity(proc_root=tmp_path / "no-proc") is None


def test_session_identity_prefers_payload_id(tmp_path):
    assert wg._session_identity({"session_id": "s-9"}, proc_root=tmp_path) == "sid:s-9"
