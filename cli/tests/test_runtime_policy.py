"""Canonical runtime-policy loader tests (F4).

The shared config nests policy under ``runtime_policy:``. These tests lock the
contract that consumers read the nested mapping (not the legacy top level), so
``command_policy`` allowlists and ``token_budget`` overrides are never silently
dropped.
"""

import warnings
from pathlib import Path

import pytest
import yaml

from cli.runtime.policy import (
    DEFAULT_TOKEN_BUDGET,
    RuntimePolicy,
    RuntimePolicyError,
    load_runtime_policy,
    runtime_policy_mapping,
)

REPO = Path(__file__).resolve().parents[2]
SHARED_CONFIG = REPO / ".maika" / "profiles" / "execution-mode.yaml"


def test_nested_runtime_policy_is_read():
    config = {
        "version": 2,
        "runtime_policy": {
            "worker_timeout_seconds": 120,
            "max_retries": 5,
            "token_budget": {"small": {"max_worker_calls": 9}},
            "command_policy": {"allowed_profiles": ["pytest-paths"], "timeout_seconds": 30},
        },
    }
    policy = load_runtime_policy(config)
    assert policy.worker_timeout_seconds == 120
    assert policy.max_retries == 5
    assert policy.token_budget["small"]["max_worker_calls"] == 9
    # unspecified budget fields keep the canonical default
    assert policy.token_budget["small"]["max_context_tokens"] == 20000
    assert policy.command_policy["allowed_profiles"] == ["pytest-paths"]


def test_real_shared_config_command_policy_is_not_empty():
    """F4 regression: the checked-in nested execution-mode.yaml must surface its
    command_policy allowlists through the loader — the old top-level read
    returned {} and silently disabled every allowlist."""
    config = yaml.safe_load(SHARED_CONFIG.read_text(encoding="utf-8"))
    policy = load_runtime_policy(config)
    assert policy.command_policy.get("allowed_profiles"), "command_policy lost — F4 regressed"
    assert "pytest" in policy.command_policy.get("allowed_executables", [])
    assert policy.command_policy.get("requires_human_confirmation")
    assert policy.worker_timeout_seconds == 900


def test_legacy_top_level_config_still_read_with_warning():
    legacy = {
        "worker_timeout_seconds": 42,
        "command_policy": {"allowed_profiles": ["gradle-test"]},
    }
    with pytest.warns(DeprecationWarning):
        policy = load_runtime_policy(legacy)
    assert policy.worker_timeout_seconds == 42
    assert policy.command_policy["allowed_profiles"] == ["gradle-test"]


def test_project_override_changes_behavior():
    base = load_runtime_policy({"runtime_policy": {}})
    overridden = load_runtime_policy(
        {"runtime_policy": {"token_budget": {"architectural": {"max_worker_calls": 99}}}}
    )
    assert base.token_budget["architectural"]["max_worker_calls"] == 12
    assert overridden.token_budget["architectural"]["max_worker_calls"] == 99


def test_default_config_matches_defaults():
    empty = load_runtime_policy({})
    assert empty.command_policy == {}
    assert empty.worker_timeout_seconds == 900
    assert empty.max_retries == 2
    for task_class in ("trivial", "small", "standard", "architectural"):
        assert empty.token_budget[task_class] == DEFAULT_TOKEN_BUDGET[task_class]
    # returned budgets are copies — mutating one must not corrupt the defaults
    empty.token_budget["trivial"]["max_worker_calls"] = 999
    assert DEFAULT_TOKEN_BUDGET["trivial"]["max_worker_calls"] == 1


def test_max_retries_zero_is_valid_single_attempt():
    policy = load_runtime_policy({"runtime_policy": {"max_retries": 0}})
    assert policy.max_retries == 0


@pytest.mark.parametrize(
    "bad",
    [
        {"worker_timeout_seconds": 0},
        {"worker_timeout_seconds": -5},
        {"worker_timeout_seconds": "soon"},
        {"max_retries": -1},
        {"worker_timeout_seconds": True},
        {"token_budget": ["not", "a", "map"]},
        {"command_policy": "deny-all"},
    ],
)
def test_invalid_nested_config_fails_closed(bad):
    with pytest.raises(RuntimePolicyError):
        load_runtime_policy({"runtime_policy": bad})


def test_from_config_alias_matches_loader():
    config = {"runtime_policy": {"worker_timeout_seconds": 77}}
    assert RuntimePolicy.from_config(config) == load_runtime_policy(config)


def test_runtime_policy_mapping_prefers_nested_over_top_level():
    config = {
        "worker_timeout_seconds": 1,
        "runtime_policy": {"worker_timeout_seconds": 900},
    }
    # nested wins; no deprecation warning when the canonical key is present
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert runtime_policy_mapping(config)["worker_timeout_seconds"] == 900
