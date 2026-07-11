"""Install planner — compute a pure-data action list, no side effects.

Given a fully-staged desired tree and the current target, `build_plan` returns:

    {"version": 1, "operation": "init"|"update",
     "actions": [{"kind", "path", "ownership"}, ...]}

kinds: create | replace | managed_markdown | merge_json | delete_framework_file.
The transaction engine consumes this plan; the planner itself never writes.
"""

from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import List

from cli.install import ownership


def _staged_files(staging: Path) -> List[str]:
    return sorted(
        p.relative_to(staging).as_posix()
        for p in staging.rglob("*")
        if p.is_file()
    )


def _write_action(rel: str, target: Path, framework_root: str) -> dict | None:
    own = ownership.classify(rel, framework_root)
    exists = (target / rel).exists()

    if own == ownership.PROJECT:
        # Never clobber user data: create when absent, otherwise leave it.
        if exists:
            return None
        kind = "create"
    elif own == ownership.SHARED_HOST:
        kind = "merge_json" if rel.endswith(".json") else "managed_markdown"
    else:
        kind = "replace" if exists else "create"

    return {"kind": kind, "path": rel, "ownership": own}


def _orphan_actions(staged: List[str], target: Path, framework_root: str) -> List[dict]:
    """Framework files in a staged directory but absent from staging → delete.

    Scoped to directories staging actually wrote into, excluding the target root
    and the framework root itself (those mix framework output with user/generated
    files), and only ever deletes framework-owned files — project/shared-host
    paths are never removed.
    """
    staged_set = set(staged)
    managed_dirs = {PurePosixPath(rel).parent for rel in staged}
    excluded = {PurePosixPath("."), PurePosixPath(framework_root)}

    actions: List[dict] = []
    for managed in sorted(managed_dirs, key=str):
        if managed in excluded:
            continue
        target_dir = target / managed
        if not target_dir.is_dir():
            continue
        for item in sorted(target_dir.iterdir(), key=lambda p: p.name):
            if not item.is_file():
                continue
            rel = item.relative_to(target).as_posix()
            if rel in staged_set:
                continue
            if ownership.classify(rel, framework_root) != ownership.FRAMEWORK:
                continue
            actions.append({"kind": "delete_framework_file", "path": rel,
                            "ownership": ownership.FRAMEWORK})
    return actions


def build_plan(staging: Path, target: Path, operation: str,
               framework_root: str = ".maika") -> dict:
    """Compute the action plan for syncing `staging` into `target`."""
    staged = _staged_files(staging)
    actions = [a for a in (_write_action(rel, target, framework_root) for rel in staged)
               if a is not None]
    if operation == "update":
        actions.extend(_orphan_actions(staged, target, framework_root))
    return {"version": 1, "operation": operation, "actions": actions}
