import importlib.util
import json
import subprocess
from pathlib import Path


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


def test_allows_framework_and_openspec_artifact_writes(tmp_path):
    assert wg.evaluate_write(tmp_path, Path(".maika/knowledge/active/KNOWLEDGE_CHECKPOINT.md")).ok is True
    assert wg.evaluate_write(tmp_path, Path("openspec/changes/x/specs/foo/spec.md")).ok is True


def test_blocks_app_write_without_checkpoint(tmp_path):
    result = wg.evaluate_write(tmp_path, Path("src/App.java"))
    assert result.ok is False
    assert "KNOWLEDGE_CHECKPOINT" in result.reason


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


def test_main_allows_absolute_framework_knowledge_write_without_checkpoint(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    target = tmp_path / ".maika" / "knowledge" / "long-term" / "author-dna.yaml"
    payload = {"tool_name": "Write", "tool_input": {"file_path": str(target)}}
    code = wg.main(["--framework-root", ".maika"], stdin_text=json.dumps(payload))
    assert code == 0


def test_bash_write_to_documentation_allowed(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    payload = {"tool_name": "Bash", "tool_input": {"command": "echo x > docs/ARCHITECTURE.md"}}
    code = wg.main(["--framework-root", ".maika"], stdin_text=json.dumps(payload))
    assert code == 0


def test_allows_app_write_with_valid_checkpoint(tmp_path):
    framework = tmp_path / ".maika"
    checkpoint = framework / "knowledge" / "active" / "KNOWLEDGE_CHECKPOINT.md"
    checkpoint.parent.mkdir(parents=True)
    checkpoint.write_text(
        "## DNA\nSP-6 staircase\n"
        "## Codebase evidence\nnode_id: svc.UserService#42\nblast-radius: 3 nodes\n",
        encoding="utf-8",
    )
    (framework / "knowledge" / "active" / "AGENT_TRANSPARENCY.md").write_text(
        "Pha 1 DONE\nPha 2 DONE\n", encoding="utf-8"
    )
    _write_valid_implementation_context(framework / "knowledge" / "active", "src/App.java")

    result = wg.evaluate_write(tmp_path, Path("src/App.java"), framework_root=".maika")
    assert result.ok is True


def test_blocks_app_write_without_implementation_context(tmp_path):
    active = tmp_path / ".maika" / "knowledge" / "active"
    _write_valid_checkpoint(active)
    (active / "AGENT_TRANSPARENCY.md").write_text(
        "Pha 1 DONE\nPha 2 DONE\n", encoding="utf-8"
    )
    result = wg.evaluate_write(tmp_path, Path("src/App.java"), framework_root=".maika")
    assert result.ok is False
    assert "implementation context" in result.reason


def test_blocks_app_write_when_implementation_context_targets_other_file(tmp_path):
    active = tmp_path / ".maika" / "knowledge" / "active"
    _write_valid_checkpoint(active)
    (active / "AGENT_TRANSPARENCY.md").write_text(
        "Pha 1 DONE\nPha 2 DONE\n", encoding="utf-8"
    )
    _write_valid_implementation_context(active, "src/Other.java")
    result = wg.evaluate_write(tmp_path, Path("src/App.java"), framework_root=".maika")
    assert result.ok is False
    assert "src/App.java" in result.reason


def test_blocks_app_write_when_checkpoint_ruleid_not_in_index(tmp_path):
    framework = tmp_path / ".maika"
    checkpoint = framework / "knowledge" / "active" / "KNOWLEDGE_CHECKPOINT.md"
    checkpoint.parent.mkdir(parents=True)
    checkpoint.write_text(
        "## DNA\nISO-9001\n"
        "## Codebase evidence\nnode_id: svc.UserService#42\nblast-radius: 3 nodes\n",
        encoding="utf-8",
    )
    index = framework / "knowledge" / "long-term" / "knowledge-index.yaml"
    index.parent.mkdir(parents=True)
    index.write_text(
        "entries:\n"
        "  - id: SP-6\n"
        "    store: author-dna\n"
        "    title: staircase\n"
        "    applies_to: [Constructor]\n",
        encoding="utf-8",
    )

    result = wg.evaluate_write(tmp_path, Path("src/App.java"), framework_root=".maika")
    assert result.ok is False
    assert "valid rule-id" in result.reason


def test_main_blocks_with_exit_2_for_claude_pretooluse(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    payload = {"tool_name": "Write", "tool_input": {"file_path": "src/App.java"}}
    code = wg.main(["--framework-root", ".claude"], stdin_text=json.dumps(payload))
    captured = capsys.readouterr()
    assert code == 2
    assert "KNOWLEDGE_CHECKPOINT" in captured.err


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
    assert unresolved is False


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
    assert unresolved is False


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
    assert "KNOWLEDGE_CHECKPOINT" in captured.err


def test_bash_write_to_code_allows_with_valid_checkpoint(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    checkpoint = tmp_path / ".maika" / "knowledge" / "active" / "KNOWLEDGE_CHECKPOINT.md"
    checkpoint.parent.mkdir(parents=True)
    checkpoint.write_text(
        "## DNA\nSP-6 staircase\n"
        "## Codebase evidence\nnode_id: svc.UserService#42\nblast-radius: 3 nodes\n",
        encoding="utf-8",
    )
    (tmp_path / ".maika" / "knowledge" / "active" / "AGENT_TRANSPARENCY.md").write_text(
        "Pha 1 DONE\nPha 2 DONE\n", encoding="utf-8"
    )
    _write_valid_implementation_context(
        tmp_path / ".maika" / "knowledge" / "active", "src/App.java"
    )
    payload = {"tool_name": "Bash", "tool_input": {"command": "tee src/App.java"}}
    code = wg.main(["--framework-root", ".maika"], stdin_text=json.dumps(payload))
    assert code == 0


def test_bash_readonly_command_allowed_fail_open(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    payload = {"tool_name": "Bash", "tool_input": {"command": "grep -r foo src && ls"}}
    code = wg.main(["--framework-root", ".maika"], stdin_text=json.dumps(payload))
    assert code == 0


def test_bash_write_to_gitignored_path_allowed(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    subprocess.run(["git", "init", "-q"], cwd=str(tmp_path), check=True)
    (tmp_path / ".gitignore").write_text("coverage/\n", encoding="utf-8")
    payload = {"tool_name": "Bash", "tool_input": {"command": "echo x > coverage/lcov.info"}}
    code = wg.main(["--framework-root", ".maika"], stdin_text=json.dumps(payload))
    assert code == 0


def test_bash_write_to_framework_artifact_allowed(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    payload = {"tool_name": "Bash", "tool_input": {"command": "echo x > .maika/knowledge/active/REQUIREMENT.md"}}
    code = wg.main(["--framework-root", ".maika"], stdin_text=json.dumps(payload))
    assert code == 0


def test_bash_dynamic_write_warns_and_allows(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    payload = {"tool_name": "Bash", "tool_input": {"command": 'tee "$TARGET"'}}
    code = wg.main(["--framework-root", ".maika"], stdin_text=json.dumps(payload))
    captured = capsys.readouterr()
    assert code == 0
    assert "unresolved" in captured.err.lower()


def test_bash_stderr_redirect_to_code_blocks_without_checkpoint(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    payload = {"tool_name": "Bash", "tool_input": {"command": "npm run build 2> src/App.java"}}
    code = wg.main(["--framework-root", ".maika"], stdin_text=json.dumps(payload))
    captured = capsys.readouterr()
    assert code == 2
    assert "KNOWLEDGE_CHECKPOINT" in captured.err


def _write_valid_checkpoint(active_dir):
    active_dir.mkdir(parents=True, exist_ok=True)
    (active_dir / "KNOWLEDGE_CHECKPOINT.md").write_text(
        "## DNA\nSP-6 staircase\n"
        "## Codebase evidence\nnode_id: svc.UserService#42\nblast-radius: 3 nodes\n",
        encoding="utf-8",
    )


def _write_valid_implementation_context(active_dir, allowed_file):
    active_dir.mkdir(parents=True, exist_ok=True)
    (active_dir / "TASK_HANDOFF.node-1.md").write_text(
        "# TASK_HANDOFF.node-1\n"
        "## Task Objective\nImplement the assigned node.\n"
        "## Applicable DNA/Conventions\n- SP-6: staircase\n"
        "## Evidence\n"
        "- UA evidence: domain_overview=User, domain_flow=UpdateUser\n"
        "## Allowed Files\n"
        f"- {allowed_file}\n"
        "## Verification\n- pytest\n",
        encoding="utf-8",
    )


def test_blocks_app_write_when_transparency_missing(tmp_path):
    _write_valid_checkpoint(tmp_path / ".maika" / "knowledge" / "active")
    result = wg.evaluate_write(tmp_path, Path("src/App.java"), framework_root=".maika")
    assert result.ok is False
    assert "AGENT_TRANSPARENCY" in result.reason


def test_blocks_app_write_with_checkpoint_but_no_pha2(tmp_path):
    active = tmp_path / ".maika" / "knowledge" / "active"
    _write_valid_checkpoint(active)
    (active / "AGENT_TRANSPARENCY.md").write_text("Pha 1 DONE\n", encoding="utf-8")
    result = wg.evaluate_write(tmp_path, Path("src/App.java"), framework_root=".maika")
    assert result.ok is False
    assert "Pha 2 DONE" in result.reason


def test_blocks_app_write_with_open_blocker(tmp_path):
    active = tmp_path / ".maika" / "knowledge" / "active"
    _write_valid_checkpoint(active)
    (active / "AGENT_TRANSPARENCY.md").write_text(
        "Pha 1 DONE\nPha 2 DONE\n[BLOCKER-ARCH] coupling risk\n", encoding="utf-8"
    )
    result = wg.evaluate_write(tmp_path, Path("src/App.java"), framework_root=".maika")
    assert result.ok is False


def test_allows_app_write_with_checkpoint_and_apply_evidence(tmp_path):
    active = tmp_path / ".maika" / "knowledge" / "active"
    _write_valid_checkpoint(active)
    (active / "AGENT_TRANSPARENCY.md").write_text(
        "Pha 1 DONE\nPha 2 DONE\n", encoding="utf-8"
    )
    _write_valid_implementation_context(active, "src/App.java")
    result = wg.evaluate_write(tmp_path, Path("src/App.java"), framework_root=".maika")
    assert result.ok is True
