"""Change-loop governance (W7): decision classification + trusted approval.

Which remediation a loop proposes, and whether it may proceed automatically or
needs human sign-off, is decided here — never by an agent-authored boolean.
Approval reuses the trusted-approval pattern (``source: cli-user-action`` + a
bound hash) already used by ``runtime_hardening.trusted_approval_matches``, but
binds the change/loop/decision triple instead of a verification command.

Automatic (in the plan's automatic set): a first-class in-scope code correction,
a replan inside an unchanged approved contract, or rerunning an approved safe
verification profile. Human approval: reopening spec, public-contract/security/
migration changes, scope expansion, shared-skill patch/promotion, budget
extension. An unrecognized trigger fails safe → requires approval.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml

# (decision type, requires_human_approval) keyed by the wired trigger.
_DECISION = {
    "scope_escape": ("scope_expansion", True),        # expanding declared scope
    "repeated_failure": ("local_code_correction", False),  # in-scope fix
}


def decision_for(loop: dict) -> dict:
    """Derive the single remediation decision this loop proposes."""
    trigger = (loop.get("trigger") or {}).get("type")
    dtype, requires = _DECISION.get(trigger, ("unclassified", True))
    return {"id": f"{loop['loop_id']}-D1", "type": dtype, "requires_approval": requires}


def loop_decision_hash(change_id: str, loop_id: str, decision_id: str) -> str:
    payload = json.dumps(
        {"change_id": change_id, "loop_id": loop_id, "decision_id": decision_id},
        sort_keys=True, separators=(",", ":"),
    )
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def trusted_loop_approval_matches(path, change_id: str, loop_id: str, decision_id: str) -> bool:
    """True only for a CLI-user-authored approval bound to this exact triple."""
    try:
        approval = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return False
    return (
        approval.get("version") == 1
        and approval.get("source") == "cli-user-action"
        and approval.get("change_id") == change_id
        and approval.get("loop_id") == loop_id
        and approval.get("decision_id") == decision_id
        and approval.get("decision_hash") == loop_decision_hash(change_id, loop_id, decision_id)
    )
