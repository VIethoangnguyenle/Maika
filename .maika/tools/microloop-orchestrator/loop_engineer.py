"""Change-level Loop Engineer (W6).

Observes runtime friction, and when it has crossed the micro-retry boundary
opens exactly one evidence-backed change loop, diagnoses a root cause, and
routes it to a single specialist role. It diagnoses and routes only — it never
writes spec, plan, application code, or a shared skill.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _sibling(name):
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError:
        path = Path(__file__).with_name(f"{name}.py")
        spec = importlib.util.spec_from_file_location(f"maika_{name}", path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module


loop_policy = _sibling("loop_policy")
loop_router = _sibling("loop_router")
loop_state = _sibling("loop_state")

# Deterministic, evidence-backed diagnosis for the two wired triggers.
_ROOT_CAUSE = {
    "scope_escape": "implementation_gap",   # worker wrote outside declared scope
    "repeated_failure": "verification_gap",  # verification stayed red past the budget
}


def diagnose(trigger_type: str, evidence_refs) -> str:
    """Map a trigger + its evidence to exactly one root cause."""
    return _ROOT_CAUSE[trigger_type]


def observe(ws, change_id, observation: dict):
    """Entry point called at orchestrator friction points. Returns the routed
    loop dict, or None when the event stays a micro loop or a loop is already
    active (the one-active invariant forbids recursion)."""
    open_it, _reason = loop_policy.should_open_loop(observation)
    if not open_it:
        return None
    try:
        loop = loop_state.create_loop(
            ws, change_id, observation["trigger"], observation.get("evidence_refs", []),
        )
    except loop_state.LoopExists:
        return None
    root_cause = diagnose(observation["trigger"], loop["trigger"]["evidence_refs"])
    role = loop_router.route(root_cause)
    return loop_state.record_diagnosis(ws, root_cause, role)
