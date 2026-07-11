"""Canonical runtime-policy loader (F4).

The shared execution config nests runtime policy under ``runtime_policy:``
(``.maika/profiles/execution-mode.yaml`` v2). Every consumer must read it through
this loader so a nested config is never parsed as a legacy top-level mapping —
doing so silently drops ``command_policy`` allowlists and ``token_budget``
overrides, turning operator configuration into decoration.

This module is the single source of truth for the runtime-policy shape. The
scaffolded microloop tools (``.maika/tools/microloop-orchestrator``) re-export
``RuntimePolicy``/``DEFAULT_TOKEN_BUDGET`` from here rather than defining their
own, exactly as ``orchestrator.py`` already imports ``cli.runtime.*``.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass

TASK_CLASSES = ("trivial", "small", "standard", "architectural")

DEFAULT_TOKEN_BUDGET = {
    "version": 1,
    "trivial": {"max_context_tokens": 8000, "max_worker_calls": 1, "max_evidence_items": 5},
    "small": {"max_context_tokens": 20000, "max_worker_calls": 2, "max_evidence_items": 12},
    "standard": {"max_context_tokens": 60000, "max_worker_calls": 6, "max_evidence_items": 30},
    "architectural": {"max_context_tokens": 120000, "max_worker_calls": 12, "max_evidence_items": 60},
}

# Keys that identify a legacy top-level (pre-``runtime_policy:``) layout.
_LEGACY_KEYS = ("token_budget", "command_policy", "worker_timeout_seconds", "max_retries")


class RuntimePolicyError(ValueError):
    """Raised when a runtime-policy mapping is present but structurally invalid."""


@dataclass(frozen=True)
class RuntimePolicy:
    token_budget: dict
    command_policy: dict
    worker_timeout_seconds: int = 900
    max_retries: int = 2

    @classmethod
    def from_config(cls, config: dict | None = None) -> "RuntimePolicy":
        """Back-compat alias; :func:`load_runtime_policy` is the canonical entry."""
        return load_runtime_policy(config)


def runtime_policy_mapping(config: dict | None) -> dict:
    """Return the runtime-policy sub-mapping from a full config.

    Canonical configs nest the policy under ``runtime_policy:``. A legacy config
    that still carries the policy keys at the top level is honored for one
    compatibility window, with a ``DeprecationWarning`` so it gets migrated.
    """
    config = config or {}
    nested = config.get("runtime_policy")
    if isinstance(nested, dict):
        return nested
    if any(key in config for key in _LEGACY_KEYS):
        warnings.warn(
            "runtime policy read from top-level config keys; nest them under "
            "`runtime_policy:` in execution-mode.yaml — the flat layout is "
            "deprecated and will stop being read in a future release",
            DeprecationWarning,
            stacklevel=2,
        )
        return config
    return {}


def _coerce_int(mapping: dict, key: str, default: int, minimum: int) -> int:
    if key not in mapping:
        return default
    value = mapping[key]
    if isinstance(value, bool):  # bool is an int subclass; reject it explicitly.
        raise RuntimePolicyError(f"runtime_policy.{key} must be an integer, got {value!r}")
    try:
        result = int(value)
    except (TypeError, ValueError):
        raise RuntimePolicyError(f"runtime_policy.{key} must be an integer, got {value!r}")
    if result < minimum:
        raise RuntimePolicyError(f"runtime_policy.{key} must be >= {minimum}, got {result}")
    return result


def load_runtime_policy(config: dict | None = None) -> RuntimePolicy:
    """Build a :class:`RuntimePolicy` from a full project/execution config.

    Reads the nested ``runtime_policy:`` mapping (legacy top-level tolerated with
    a warning), merges ``token_budget`` overrides onto the canonical defaults per
    task class, and fails closed on structurally invalid numeric fields.
    """
    mapping = runtime_policy_mapping(config)

    override = mapping.get("token_budget") or {}
    if not isinstance(override, dict):
        raise RuntimePolicyError("runtime_policy.token_budget must be a mapping")
    budgets = {name: dict(DEFAULT_TOKEN_BUDGET[name]) for name in TASK_CLASSES}
    for task_class in TASK_CLASSES:
        class_override = override.get(task_class)
        if isinstance(class_override, dict):
            budgets[task_class].update(class_override)

    command_policy = mapping.get("command_policy") or {}
    if not isinstance(command_policy, dict):
        raise RuntimePolicyError("runtime_policy.command_policy must be a mapping")

    return RuntimePolicy(
        token_budget=budgets,
        command_policy=dict(command_policy),
        # timeout of 0 is meaningless; retries of 0 (single attempt) is valid.
        worker_timeout_seconds=_coerce_int(mapping, "worker_timeout_seconds", 900, minimum=1),
        max_retries=_coerce_int(mapping, "max_retries", 2, minimum=0),
    )
