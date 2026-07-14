"""Worker executor registry ↔ resolver sync (F5/F6): no shadow strategies.

The resolver may only return strategies that have an executor (or the terminal
disabled state). inline and native_subagent are advertised in the profile schema
but have no executor this release, so the resolver must never select them.
"""

import yaml

from cli.runtime import executor
from cli.runtime import worker_resolver
from cli.runtime.platform_profile import WORKER_STRATEGIES, write_platform_runtime_profile
from cli.runtime.worker_resolver import WorkerResolutionError, resolve_worker_profile
import pytest


def _write(root, platform, **verification):
    path = write_platform_runtime_profile(root, platform)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if verification.get("verified"):
        data["detection"]["binary"].update({"found": True, "version_supported": True})
        data["capabilities"]["fresh_session"] = "verified"
        data["verification"]["worker_smoke_test"] = "pass"
    for cap, state in (verification.get("capabilities") or {}).items():
        data["capabilities"][cap] = state
    if verification.get("disabled"):
        data["adapter"]["enabled"] = False
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def test_selectable_is_subset_of_all_strategies():
    assert executor.SELECTABLE_STRATEGIES <= executor.STRATEGIES
    assert executor.ADVERTISED_ONLY_STRATEGIES <= executor.STRATEGIES
    assert executor.SELECTABLE_STRATEGIES.isdisjoint(executor.ADVERTISED_ONLY_STRATEGIES)


def test_advertised_only_strategies_have_no_executor():
    assert executor.INLINE in executor.ADVERTISED_ONLY_STRATEGIES
    assert executor.NATIVE_SUBAGENT in executor.ADVERTISED_ONLY_STRATEGIES
    for strategy in executor.ADVERTISED_ONLY_STRATEGIES:
        assert not executor.strategy_is_selectable(strategy)
        assert not executor.strategy_executes(strategy)


def test_only_fresh_process_actually_executes():
    assert executor.strategy_executes(executor.FRESH_PROCESS)
    assert not executor.strategy_executes(executor.DISABLED)


def test_strategy_registries_are_synced():
    # One source of truth shared by resolver, profile schema, and this registry.
    assert worker_resolver.STRATEGIES is executor.STRATEGIES
    assert WORKER_STRATEGIES is executor.STRATEGIES


def test_resolver_never_returns_shadow_strategy(tmp_path):
    _write(tmp_path / "unverified", "codex")
    _write(tmp_path / "verified", "codex", verified=True)
    _write(tmp_path / "disabled", "codex", disabled=True)
    for name in ("unverified", "verified", "disabled"):
        profile = resolve_worker_profile(tmp_path / name, "codex")
        assert executor.strategy_is_selectable(profile.strategy), \
            f"{name} resolved to shadow strategy {profile.strategy}"


def test_native_subagent_not_selected_even_when_capability_verified(tmp_path):
    # A "verified" subagent capability must not promote the shadow native strategy.
    _write(tmp_path, "codex", capabilities={"subagent": "verified"})
    profile = resolve_worker_profile(tmp_path, "codex")
    assert profile.strategy != executor.NATIVE_SUBAGENT
    assert profile.strategy == executor.DISABLED


def test_override_to_advertised_only_strategy_fails_closed(tmp_path):
    write_platform_runtime_profile(tmp_path, "codex")
    with pytest.raises(WorkerResolutionError, match="no executor"):
        resolve_worker_profile(tmp_path, "codex", {
            "platform": "codex", "strategy": "inline",
        })
