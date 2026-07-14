"""Change-loop policy — the micro-retry boundary (Loop Engineer, W6).

A change loop opens only when observed friction has already exceeded the
micro-retry boundary. Only triggers with current runtime evidence are wired:

- ``scope_escape``   — the worktree changed files outside the declared scope
  (``adaptive_runtime.inspect_lightweight_changes`` → ``outside_scope``).
- ``repeated_failure`` — a task stayed blocked after the retry budget was
  exhausted (``vnext_dispatch.run_queue`` → "retry budget exhausted").

``stale_contract`` and ``human_correction`` are deferred (no discrete runtime
signal yet); an unwired trigger never opens a loop.
"""

from __future__ import annotations

from typing import Tuple


def should_open_loop(observation: dict) -> Tuple[bool, str]:
    """Return (open, reason). ``open`` is True only past the micro boundary."""
    trigger = observation.get("trigger")
    if trigger == "scope_escape":
        if observation.get("outside_scope"):
            return True, "worker changed files outside the declared scope"
        return False, "no outside-scope files — nothing escaped"
    if trigger == "repeated_failure":
        if observation.get("retries_exhausted"):
            return True, "verification stayed blocked after the retry budget"
        return False, "within retry budget — still a micro loop"
    return False, f"no change-loop policy for trigger {trigger!r}"
