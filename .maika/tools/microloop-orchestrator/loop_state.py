"""LOOP.yaml lifecycle for the change-level Loop Engineer (W6).

One active change loop per change. The one-active invariant is held in
STATE.yaml (``active_loop_id``, owned by ``vnext_state``) so the write gate,
orchestrator, and — later — the loop CLI all read a single source of truth.
Atomic IO is reused from ``vnext_state`` (same-directory temp + ``os.replace``).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

try:
    import vnext_state as vs
except ModuleNotFoundError:  # importlib callers may not have this dir on sys.path
    _vs_path = Path(__file__).with_name("vnext_state.py")
    _vs_spec = importlib.util.spec_from_file_location("maika_vnext_state", _vs_path)
    vs = importlib.util.module_from_spec(_vs_spec)
    sys.modules[_vs_spec.name] = vs
    _vs_spec.loader.exec_module(vs)

LOOP_STATES = ("diagnosing", "routed", "approved", "rejected", "resumed", "closed")


class LoopExists(RuntimeError):
    """Raised when a change already has an active loop (one-active invariant)."""


def loop_path(ws) -> Path:
    return Path(ws) / "LOOP.yaml"


def load_loop(ws):
    path = loop_path(ws)
    if not path.exists():
        return None
    return vs._load_yaml(path)


def create_loop(ws, change_id, trigger_type, evidence_refs) -> dict:
    if vs.active_loop_id(ws) is not None:
        raise LoopExists(f"{change_id} already has an active change loop")
    loop = {
        "version": 1,
        "loop_id": f"LOOP-{change_id}-001",
        "change_id": change_id,
        "level": "change",
        "state": "diagnosing",
        "trigger": {"type": trigger_type, "evidence_refs": list(evidence_refs or [])},
        "root_cause": None,
        "route": None,
        "retry_budget": {"used": 0, "maximum": 2},
    }
    vs._dump_yaml(loop, loop_path(ws))
    vs.set_active_loop(ws, loop["loop_id"])
    return loop


def record_diagnosis(ws, root_cause: str, route: str) -> dict:
    loop = load_loop(ws)
    if loop is None:
        raise ValueError("no LOOP.yaml to diagnose")
    loop.update(state="routed", root_cause=root_cause, route=route)
    vs._dump_yaml(loop, loop_path(ws))
    return loop


def set_decision_status(ws, status: str) -> dict:
    """Record a human decision (approved/rejected) from a trusted CLI action."""
    if status not in ("approved", "rejected"):
        raise ValueError(f"bad decision status: {status}")
    loop = load_loop(ws)
    if loop is None:
        raise ValueError("no LOOP.yaml to decide")
    loop["decision_status"] = status
    loop["state"] = status
    vs._dump_yaml(loop, loop_path(ws))
    return loop


def mark_resumed(ws) -> dict:
    loop = load_loop(ws)
    if loop is None:
        raise ValueError("no LOOP.yaml to resume")
    loop["state"] = "resumed"
    vs._dump_yaml(loop, loop_path(ws))
    return loop


def close_loop(ws, proposal_only: bool = False, resolution: str = None) -> dict:
    loop = load_loop(ws)
    if loop is None:
        raise ValueError("no LOOP.yaml to close")
    loop["state"] = "closed"
    loop["proposal_only"] = proposal_only
    if resolution:
        loop["resolution"] = resolution
    vs._dump_yaml(loop, loop_path(ws))
    vs.clear_active_loop(ws)
    return loop
