"""`maika hook write-gate --runtime <r>` — the stable host-hook entrypoint.

The host PreToolUse hook invokes this one OS-agnostic command instead of a
hard-coded `python .../write_gate.py` line. The wrapper locates the project
root, reads the canonical core root, and delegates to the project's own
write-gate evaluator without duplicating any policy.
"""

import io
import shutil
from pathlib import Path

import pytest

from cli.commands.hook import run_hook_write_gate

_WRITE_GATE_SRC = (
    Path(__file__).resolve().parents[2]
    / ".maika" / "hooks" / "write-gate" / "write_gate.py"
)


def _make_project(tmp_path: Path, with_gate: bool = True) -> Path:
    root = tmp_path / "proj"
    cfg = root / ".maika" / "config"
    cfg.mkdir(parents=True)
    (cfg / "project.yaml").write_text(
        "version: 1\n"
        "framework:\n  core_root: .maika\n"
        "platforms:\n  enabled:\n  - claude-code\n  primary: claude-code\n",
        encoding="utf-8",
    )
    if with_gate:
        gate_dir = root / ".maika" / "hooks" / "write-gate"
        gate_dir.mkdir(parents=True)
        shutil.copy2(_WRITE_GATE_SRC, gate_dir / "write_gate.py")
    return root


def test_allows_documentation_write(tmp_path, monkeypatch):
    root = _make_project(tmp_path)
    monkeypatch.chdir(root)
    payload = '{"tool_name":"Write","tool_input":{"file_path":"README.md"}}'
    assert run_hook_write_gate("claude", stdin_text=payload) == 0


def test_denies_code_write_without_active_task(tmp_path, monkeypatch):
    # The gate must be found via the canonical core root and its deny must
    # surface as claude exit code 2 — proving real delegation (not a stub).
    root = _make_project(tmp_path)
    monkeypatch.chdir(root)
    payload = '{"tool_name":"Write","tool_input":{"file_path":"src/app.py"}}'
    assert run_hook_write_gate("claude", stdin_text=payload) == 2


def test_codex_runtime_emits_allow_json(tmp_path, monkeypatch, capsys):
    root = _make_project(tmp_path)
    monkeypatch.chdir(root)
    payload = '{"tool_name":"Write","tool_input":{"file_path":"README.md"}}'
    rc = run_hook_write_gate("codex", stdin_text=payload)
    out = capsys.readouterr().out
    assert rc == 0
    assert '"permissionDecision": "allow"' in out


def test_missing_gate_is_graceful_allow(tmp_path, monkeypatch, capsys):
    root = _make_project(tmp_path, with_gate=False)
    monkeypatch.chdir(root)
    payload = '{"tool_name":"Write","tool_input":{"file_path":"src/app.py"}}'
    rc = run_hook_write_gate("claude", stdin_text=payload)
    err = capsys.readouterr().err
    assert rc == 0
    assert "write-gate" in err


def test_cli_dispatch_reads_stdin_and_returns_gate_code(tmp_path, monkeypatch):
    root = _make_project(tmp_path)
    monkeypatch.chdir(root)
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO('{"tool_name":"Write","tool_input":{"file_path":"src/app.py"}}'),
    )
    monkeypatch.setattr(
        "sys.argv", ["maika", "hook", "write-gate", "--runtime", "claude"]
    )
    from cli.maika import main

    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2
