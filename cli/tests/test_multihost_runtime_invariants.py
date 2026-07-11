"""Multi-host runtime invariants (Workstream A, Phase A0).

These lock in the architecture Workstream A must reach: a project's runtime
worker is resolved from the CURRENT host, never from the platform that happened
to run ``maika init``.

Two kinds of test live here:

* **Passing guards** — invariants that already hold today. They must never
  regress (e.g. the canonical core is always ``.maika``; a project may enable
  several platforms at once).

* **Runtime targets** — host-bound expectations exercised through the canonical
  resolver. These began as strict xfails in A0; A2 made them pass without
  weakening their expectations.

The test → production-impact mapping lives in
``docs/refactor/master-v2/multihost-runtime-failures.md``.
"""

from pathlib import Path

import pytest

from cli.commands.init import run_init
from cli.commands.platform import run_platform
from cli.config import project

REPO_ROOT = Path(__file__).resolve().parents[2]

def _init(target: Path, platform_key: str) -> None:
    run_init(target_dir=str(target), maika_root=str(REPO_ROOT),
             platform_key=platform_key, selected_mcps=[], language="python",
             assume_yes=True)


def _enable(target: Path, platform_key: str) -> None:
    run_platform(action="enable", target_dir=str(target), platform_key=platform_key,
                 maika_root=str(REPO_ROOT))


@pytest.fixture(scope="module")
def codex_project_with_claude(tmp_path_factory) -> Path:
    """Real project: inited as codex, then claude-code enabled and made primary.

    Mirrors the plan's Phase A0 integration scenario exactly:
        init codex → enable claude-code → set primary claude-code.
    """
    target = tmp_path_factory.mktemp("codex_init_claude")
    _init(target, "codex")
    _enable(target, "claude-code")
    cfg = project.set_primary(project.load(target), "claude-code")
    project.save(target, cfg)
    return target


# ── Passing guards: invariants already true today ──────────────────────────

def test_canonical_core_is_always_maika():
    assert project.CORE_ROOT == ".maika"
    assert project.load(Path("/nonexistent"))["framework"]["core_root"] == ".maika"


def test_project_can_enable_multiple_platforms():
    cfg = project.enable(project.enable(project._default(), "codex"), "claude-code")
    assert set(cfg["platforms"]["enabled"]) == {"codex", "claude-code"}
    # First-enabled stays primary until explicitly changed.
    assert cfg["platforms"]["primary"] == "codex"


# ── Runtime targets: host, not init-platform, decides the worker ───────────

def test_worker_resolves_by_active_host_not_init_platform(codex_project_with_claude):
    from cli.runtime.worker_resolver import resolve_worker_profile

    profile = resolve_worker_profile(codex_project_with_claude, "claude-code")
    assert profile.platform == "claude-code"


def test_runtime_ignores_init_rendered_worker_executable(codex_project_with_claude):
    from cli.runtime.worker_resolver import resolve_worker_profile

    # Inited as codex, so the scaffold-rendered execution-mode worker is `codex`.
    # Resolving under the claude-code host must not return that baked executable.
    profile = resolve_worker_profile(codex_project_with_claude, "claude-code")
    assert profile.executable != "codex"


def test_primary_is_only_a_fallback_not_runtime_truth(codex_project_with_claude):
    from cli.runtime.worker_resolver import resolve_worker_profile

    # primary is claude-code, yet an explicit active platform wins over primary.
    profile = resolve_worker_profile(codex_project_with_claude, "codex")
    assert profile.platform == "codex"


def test_inverse_worker_resolves_codex_under_codex_host(tmp_path):
    from cli.runtime.worker_resolver import resolve_worker_profile

    _init(tmp_path, "claude-code")
    _enable(tmp_path, "codex")
    profile = resolve_worker_profile(tmp_path, "codex")
    assert profile.platform == "codex"


def test_multihost_handoff_preserves_shared_task_state(tmp_path):
    from cli.runtime.session import record_session, resolve_active_platform
    from cli.runtime.session_registry import set_active_platform
    from cli.runtime.worker_resolver import resolve_worker_profile

    _init(tmp_path, "codex")
    _enable(tmp_path, "claude-code")
    state = tmp_path / ".maika/changes/demo/STATE.yaml"
    state.parent.mkdir(parents=True)
    state.write_text("state: EXECUTING\nrevision: 7\n", encoding="utf-8")
    before = state.read_bytes()

    record_session(tmp_path, "codex", source="native-hook", session_id="codex-session")
    assert resolve_active_platform(tmp_path)[0] == "codex"
    assert resolve_worker_profile(tmp_path, "codex").platform == "codex"
    # Handoff: select claude-code via active-platform (avoids ambiguity)
    set_active_platform(tmp_path, "claude-code")
    assert resolve_active_platform(tmp_path)[0] == "claude-code"
    assert resolve_worker_profile(tmp_path, "claude-code").platform == "claude-code"
    assert state.read_bytes() == before
