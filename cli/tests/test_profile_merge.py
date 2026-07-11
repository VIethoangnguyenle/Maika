"""Runtime profile merge/preserve contract (F3).

`maika update` (and re-enable) must regenerate only framework-owned fields and
preserve runtime-observed detection/verification when the framework identity
(fingerprint) is unchanged — and invalidate verification safely when it changes.
"""

import copy
from pathlib import Path

import yaml

from cli.commands.init import run_init
from cli.commands.update import run_update
from cli.runtime.platform_profile import (
    build_platform_runtime_profile,
    merge_platform_runtime_profile,
    profile_fingerprint,
)

REPO = Path(__file__).resolve().parents[2]


def _verified(profile: dict) -> dict:
    """Return a copy of profile with a completed verification simulated."""
    p = copy.deepcopy(profile)
    p["detection"] = {
        "binary": {"path": "/usr/bin/x", "version": "2.0", "found": True, "version_supported": True},
        "authentication": {"state": "detected"},
        "last_detected_at": "2026-01-01T00:00:00+00:00",
    }
    p["capabilities"]["fresh_session"] = "verified"
    p["verification"] = {
        "hook_smoke_test": "pass", "worker_smoke_test": "pass",
        "last_verified_at": "2026-01-01T00:00:00+00:00",
    }
    return p


# --- fingerprint ------------------------------------------------------------

def test_fingerprint_stable_across_rebuild():
    assert profile_fingerprint(build_platform_runtime_profile("codex")) == \
        profile_fingerprint(build_platform_runtime_profile("codex"))


def test_fingerprint_changes_with_worker_identity():
    base = build_platform_runtime_profile("codex")
    args_changed = copy.deepcopy(base)
    args_changed["worker"]["args"] = [*base["worker"]["args"], "--extra"]
    exe_changed = copy.deepcopy(base)
    exe_changed["worker"]["executable"] = "codex-next"
    assert profile_fingerprint(args_changed) != profile_fingerprint(base)
    assert profile_fingerprint(exe_changed) != profile_fingerprint(base)


def test_fingerprint_ignores_enabled_and_runtime_observed():
    enabled = build_platform_runtime_profile("codex", enabled=True)
    disabled = build_platform_runtime_profile("codex", enabled=False)
    assert profile_fingerprint(enabled) == profile_fingerprint(disabled)
    observed = _verified(enabled)
    assert profile_fingerprint(observed) == profile_fingerprint(enabled)


# --- merge ------------------------------------------------------------------

def test_merge_no_existing_returns_generated_with_fingerprint():
    generated = build_platform_runtime_profile("codex")
    merged = merge_platform_runtime_profile(None, generated)
    assert merged["profile_fingerprint"] == profile_fingerprint(generated)
    assert merged["verification"]["worker_smoke_test"] == "not-run"


def test_merge_preserves_runtime_observed_when_fingerprint_unchanged():
    generated = build_platform_runtime_profile("claude-code")
    existing = _verified(generated)  # same framework fields → same fingerprint
    merged = merge_platform_runtime_profile(existing, generated)
    assert merged["verification"]["worker_smoke_test"] == "pass"
    assert merged["verification"]["last_verified_at"] == "2026-01-01T00:00:00+00:00"
    assert merged["capabilities"]["fresh_session"] == "verified"
    assert merged["detection"]["binary"]["version"] == "2.0"
    assert "verification_invalidated_reason" not in merged


def test_merge_invalidates_verification_when_worker_changes():
    generated = build_platform_runtime_profile("claude-code")
    existing = _verified(generated)
    existing["worker"]["args"] = ["--old-flag", "{prompt_file}"]  # a prior version's worker
    existing.pop("profile_fingerprint", None)  # force recompute from framework fields
    merged = merge_platform_runtime_profile(existing, generated)
    assert merged["verification"]["worker_smoke_test"] == "not-run"
    assert merged["verification"]["last_verified_at"] is None
    assert merged["capabilities"]["fresh_session"] == "degraded"
    assert "worker args changed" in merged["verification_invalidated_reason"]
    # detection survives for diagnostics; framework fields come from generated
    assert merged["detection"]["binary"]["found"] is True
    assert merged["worker"]["args"] == generated["worker"]["args"]


def test_merge_never_invents_verification():
    generated = build_platform_runtime_profile("codex", enabled=False)
    existing = copy.deepcopy(generated)  # never verified
    merged = merge_platform_runtime_profile(existing, generated)
    assert merged["verification"]["worker_smoke_test"] == "not-run"
    assert "verified" not in set(merged["capabilities"].values())


# --- command-level F3 regression --------------------------------------------

def test_update_preserves_verified_runtime_profile(tmp_path):
    target = tmp_path / "proj"
    run_init(
        target_dir=str(target), maika_root=str(REPO), platform_key="claude-code",
        selected_mcps=[], language="python", assume_yes=True,
    )
    profile_file = target / ".maika/runtime/platforms/claude-code.yaml"
    fresh = yaml.safe_load(profile_file.read_text(encoding="utf-8"))
    profile_file.write_text(yaml.safe_dump(_verified(fresh), sort_keys=False), encoding="utf-8")

    run_update(str(target), str(REPO))

    merged = yaml.safe_load(profile_file.read_text(encoding="utf-8"))
    # runtime-observed verification survived a full re-render (F3)
    assert merged["verification"]["worker_smoke_test"] == "pass"
    assert merged["verification"]["last_verified_at"] == "2026-01-01T00:00:00+00:00"
    assert merged["capabilities"]["fresh_session"] == "verified"
    assert merged["detection"]["binary"]["found"] is True
    # framework-owned fields are still authoritative
    assert merged["worker"]["executable"] == "claude"
    assert "profile_fingerprint" in merged
