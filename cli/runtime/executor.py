"""Worker strategy → executor capability registry (single source of truth).

The platform-profile schema advertises four worker strategies, but only some are
executable this release. A strategy the resolver could return with no executor
to run it is a *shadow strategy* (F6); this registry is the mechanical guard that
prevents one, consumed by the resolver (which only selects executable strategies)
and by doctor (which never reports a shadow as usable).

Execution bindings:

* ``fresh_process``    — executed by the microloop orchestrator's
  ``make_worker_runner`` (shell=False structured argv). The only strategy that
  actually runs a worker process.
* ``disabled``         — terminal: dispatch is refused, nothing executes.
* ``inline``           — advertised-only: no ``InlineWorkerExecutor`` exists.
* ``native_subagent``  — advertised-only: requires an adapter-provided executor
  callback that no adapter implements yet.

Per the framework's net-negative-complexity rule, no empty executor classes are
declared for the advertised-only strategies — the registry, not a stub class, is
the enforcement mechanism. A concrete executor is added here (and moved into
``SELECTABLE_STRATEGIES``) only when its execution binding actually exists.
"""

from __future__ import annotations

NATIVE_SUBAGENT = "native_subagent"
FRESH_PROCESS = "fresh_process"
INLINE = "inline"
DISABLED = "disabled"

#: Every strategy the platform-profile schema may advertise.
STRATEGIES = frozenset({NATIVE_SUBAGENT, FRESH_PROCESS, INLINE, DISABLED})
#: Strategies the resolver may select: ``fresh_process`` actually executes, and
#: ``disabled`` is the terminal refused state. Both are safe to return.
SELECTABLE_STRATEGIES = frozenset({FRESH_PROCESS, DISABLED})
#: Advertised in the schema but not selectable — no executor exists this release.
ADVERTISED_ONLY_STRATEGIES = STRATEGIES - SELECTABLE_STRATEGIES


def strategy_is_selectable(strategy: str) -> bool:
    """True if the resolver is allowed to return ``strategy`` for a task."""
    return strategy in SELECTABLE_STRATEGIES


def strategy_executes(strategy: str) -> bool:
    """True only for strategies that actually run a worker process."""
    return strategy == FRESH_PROCESS
