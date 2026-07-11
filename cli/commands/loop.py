"""maika loop — operate a change-level Loop Engineer loop without editing YAML.

    maika loop status   --id <change>
    maika loop inspect  --id <change>
    maika loop approve  --id <change> --decision <decision-id>
    maika loop reject   --id <change> --decision <decision-id>
    maika loop resume   --id <change>
    maika loop close    --id <change> [--proposal-only]

Governance and the trusted-approval record live in the project's own
``loop_governance``; this command only orchestrates them. A human-approval
decision (e.g. scope expansion) may resume only with a trusted CLI-authored
approval — never an agent-authored boolean.
"""

from __future__ import annotations

import getpass
import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml

from cli.scaffold import load_resolved_config


def _framework_root(target: Path) -> str:
    resolved = load_resolved_config(target)
    return (resolved or {}).get("framework_root", ".maika")


def _load_module(target: Path, framework_root: str, name: str):
    module_path = target / framework_root / "tools" / "microloop-orchestrator" / f"{name}.py"
    if not module_path.exists():
        raise RuntimeError(f"loop module unavailable: {module_path}")
    spec = importlib.util.spec_from_file_location(f"maika_target_{name}", module_path)
    module = importlib.util.module_from_spec(spec)
    module_dir = str(module_path.parent)
    inserted = module_dir not in sys.path
    if inserted:
        sys.path.insert(0, module_dir)
    try:
        spec.loader.exec_module(module)
    finally:
        if inserted:
            sys.path.remove(module_dir)
    return module


def _workspace(target: Path, framework_root: str, change_id: str) -> Path:
    return target / framework_root / "changes" / change_id


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_loop(action: str, target_dir: str, change_id: Optional[str] = None,
             decision_id: Optional[str] = None, proposal_only: bool = False) -> int:
    if change_id is None:
        print("maika loop requires --id <change>")
        return 2
    target = Path(target_dir).resolve()
    framework_root = _framework_root(target)
    ws = _workspace(target, framework_root, change_id)

    try:
        ls = _load_module(target, framework_root, "loop_state")
        gov = _load_module(target, framework_root, "loop_governance")
        vs = _load_module(target, framework_root, "vnext_state")
    except RuntimeError as exc:
        print(f"not a Maika loop runtime: {exc}")
        return 2

    loop = ls.load_loop(ws)
    if loop is None:
        print(f"no active change loop for {change_id}")
        return 2
    decision = gov.decision_for(loop)
    approval_path = ws / "approvals" / f"{decision['id']}.yaml"

    if action == "status":
        print(f"loop {loop['loop_id']} state={loop['state']} "
              f"trigger={loop['trigger']['type']} route={loop['route']}")
        print(f"decision {decision['id']} type={decision['type']} "
              f"requires_approval={decision['requires_approval']} "
              f"status={loop.get('decision_status', 'pending')}")
        return 0

    if action == "inspect":
        approved = gov.trusted_loop_approval_matches(
            approval_path, change_id, loop["loop_id"], decision["id"])
        print(yaml.safe_dump({"loop": loop, "decision": decision, "approved": approved},
                             sort_keys=False, allow_unicode=True))
        return 0

    if action in ("approve", "reject"):
        if decision_id != decision["id"]:
            print(f"unknown decision {decision_id!r}; this loop's decision is {decision['id']}")
            return 2
        if action == "approve":
            approval_path.parent.mkdir(parents=True, exist_ok=True)
            approval_path.write_text(yaml.safe_dump({
                "version": 1, "source": "cli-user-action",
                "change_id": change_id, "loop_id": loop["loop_id"], "decision_id": decision["id"],
                "decision_hash": gov.loop_decision_hash(change_id, loop["loop_id"], decision["id"]),
                "approved_by": getpass.getuser(), "approved_at": _now(),
            }, sort_keys=False), encoding="utf-8")
            ls.set_decision_status(ws, "approved")
            print(f"approved decision {decision['id']}")
        else:
            ls.set_decision_status(ws, "rejected")
            print(f"rejected decision {decision['id']}")
        return 0

    if action == "resume":
        if decision["requires_approval"] and not gov.trusted_loop_approval_matches(
                approval_path, change_id, loop["loop_id"], decision["id"]):
            print(f"refused: decision {decision['id']} requires a trusted human approval")
            return 3
        state = vs.load_state(ws)
        if state.get("state") == "BLOCKED":
            resume_state = (state.get("blocked") or {}).get("resume_state")
            if not resume_state:
                print("refused: no recorded resume state")
                return 2
            vs.transition(ws, resume_state)
        ls.mark_resumed(ws)
        print(f"resumed {change_id} to {vs.load_state(ws)['state']}")
        return 0

    if action == "close":
        if not proposal_only and vs.load_state(ws).get("state") == "BLOCKED":
            print("refused: close needs an evidence-backed resolution "
                  "(resume first) or --proposal-only")
            return 2
        ls.close_loop(ws, proposal_only=proposal_only,
                      resolution=None if proposal_only else "resolved after resume")
        print(f"closed loop {loop['loop_id']}")
        return 0

    print(f"unknown loop action: {action}")
    return 2
