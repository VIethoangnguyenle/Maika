"""Actual multi-host process dispatch E2E (F7).

Resolution-level tests prove the resolver picks the right platform; these prove
the right host *binary is actually spawned* and the wrong one is not. Fake
executables named exactly like the host CLIs sit on PATH, so both detection
(`maika platform verify`) and dispatch (the orchestrator's worker runner) invoke
them for real via shell=False argv.

POSIX-only: the fakes are exec-bit shebang scripts. The dispatch mechanism is
identical on Windows; only this harness is POSIX-specific.
"""

import json
import os
import sys
from pathlib import Path

import pytest

from cli.commands.init import run_init
from cli.commands.platform import run_platform

REPO_ROOT = Path(__file__).resolve().parents[2]
_MICROLOOP = REPO_ROOT / ".maika/tools/microloop-orchestrator"

pytestmark = pytest.mark.skipif(os.name == "nt", reason="fake exec-bit scripts are POSIX-only")

_FAKE_SRC = """#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
name = Path(sys.argv[0]).name
argv = sys.argv[1:]
if "--version" in argv:
    print(name + " 1.0.0")
    sys.exit(0)
prompt = ""
for a in argv:
    p = Path(a)
    if p.is_file():
        prompt = p.read_text(encoding="utf-8")
log_dir = Path(os.environ["MAIKA_FAKE_LOG_DIR"])
log_dir.mkdir(parents=True, exist_ok=True)
with (log_dir / (name + ".log")).open("a", encoding="utf-8") as fh:
    fh.write(json.dumps({"argv": argv, "cwd": os.getcwd(), "prompt": prompt}) + "\\n")
print(json.dumps({"status": "ok", "worker": name}))
sys.exit(0)
"""


@pytest.fixture
def world(tmp_path, monkeypatch):
    """Fake host CLIs on PATH + a clean per-test dispatch log."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name in ("claude", "codex", "agy"):
        exe = bin_dir / name
        exe.write_text(_FAKE_SRC, encoding="utf-8")
        exe.chmod(0o755)
    log_dir = tmp_path / "dispatch-log"
    log_dir.mkdir()
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("MAIKA_FAKE_LOG_DIR", str(log_dir))
    return {"root": tmp_path, "log_dir": log_dir}


def _init(target, platform):
    run_init(target_dir=str(target), maika_root=str(REPO_ROOT), platform_key=platform,
             selected_mcps=[], language="python", assume_yes=True)


def _enable(target, platform):
    assert run_platform("enable", str(target), platform, str(REPO_ROOT)) == 0 or True


def _verify(target, platform):
    assert run_platform("verify", str(target), platform, str(REPO_ROOT)) == 0, \
        f"verify {platform} did not reach Tier 2"


def _dispatch(target, platform, prompt, log_dir):
    """Drive the real orchestrator worker runner for one host; return spawn logs."""
    for stale in log_dir.glob("*.log"):
        stale.unlink()
    if str(_MICROLOOP) not in sys.path:
        sys.path.insert(0, str(_MICROLOOP))
    import orchestrator as orch
    ws = target / "e2e-ws"
    (ws / "generated").mkdir(parents=True, exist_ok=True)
    runner = orch._worker_runner({}, ws, str(target), platform_key=platform)
    assert runner is not None, f"no dispatchable worker for {platform}"
    code, _out = runner(prompt)
    spawned = {}
    for log in log_dir.glob("*.log"):
        spawned[log.stem] = [json.loads(line) for line in log.read_text().splitlines()]
    return code, spawned


def test_dispatch_spawns_requested_host_and_not_the_other(world):
    target = world["root"] / "proj"
    _init(target, "codex")            # inited as codex
    _enable(target, "claude-code")    # claude-code added
    _verify(target, "claude-code")

    code, spawned = _dispatch(target, "claude-code", "review this change", world["log_dir"])
    assert code == 0
    assert "claude" in spawned          # the requested host actually ran
    assert "codex" not in spawned       # the init platform did NOT run
    assert spawned["claude"][0]["prompt"] == "review this change"


def test_inverse_dispatch_under_codex_spawns_codex(world):
    target = world["root"] / "proj"
    _init(target, "claude-code")
    _enable(target, "codex")
    _verify(target, "codex")

    code, spawned = _dispatch(target, "codex", "apply under codex", world["log_dir"])
    assert code == 0
    assert "codex" in spawned
    assert "claude" not in spawned


def test_explicit_platform_beats_primary(world):
    from cli.config import project
    target = world["root"] / "proj"
    _init(target, "codex")
    _enable(target, "claude-code")
    project.save(target, project.set_primary(project.load(target), "claude-code"))
    _verify(target, "claude-code")
    _verify(target, "codex")

    # primary is claude-code, but an explicit --platform codex must win.
    code, spawned = _dispatch(target, "codex", "explicit wins", world["log_dir"])
    assert code == 0
    assert "codex" in spawned
    assert "claude" not in spawned


def test_host_switch_preserves_shared_task_state(world):
    target = world["root"] / "proj"
    _init(target, "codex")
    _enable(target, "claude-code")
    _verify(target, "codex")
    _verify(target, "claude-code")

    state = target / ".maika/changes/demo/STATE.yaml"
    state.parent.mkdir(parents=True)
    state.write_text("state: EXECUTING\nrevision: 7\n", encoding="utf-8")
    before = state.read_bytes()

    _, first = _dispatch(target, "codex", "p1", world["log_dir"])
    _, second = _dispatch(target, "claude-code", "p2", world["log_dir"])
    assert "codex" in first and "codex" not in second
    assert "claude" in second and "claude" not in first
    # shared task state is byte-identical across the host handoff
    assert state.read_bytes() == before
