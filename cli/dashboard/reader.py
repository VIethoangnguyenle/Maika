"""Maika dashboard reader: parse vNext task workspaces into a RunState.

Token parsing (TOKEN_LOG.md markdown tables) is out of slice scope; `tokens`
stays None.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml

from cli import CANONICAL_FRAMEWORK_ROOT
from cli.scaffold import load_resolved_config


@dataclass
class RunState:
    project_path: str
    ticket_id: Optional[str] = None
    phase_state: Optional[str] = None
    tasks_total: int = 0
    tasks_done: int = 0
    active_task: Optional[str] = None
    tokens: Optional[dict] = None  # deferred; always None in the slice
    stale: bool = False
    updated_at: Optional[str] = None

    @property
    def progress_pct(self) -> int:
        if self.tasks_total == 0:
            return 0
        return round(100 * self.tasks_done / self.tasks_total)


def active_dir(project_path: str, resolved: Optional[dict] = None) -> Optional[Path]:
    """Resolve {project}/{framework_root}/knowledge/active, or None if not an Maika project.

    Shared by the reader, the SSE server, and the brain sync so config is
    resolved once per project per poll instead of once per consumer.
    """
    if resolved is None:
        resolved = load_resolved_config(Path(project_path))
    if resolved is None:
        return None
    return Path(project_path) / resolved.get("framework_root", CANONICAL_FRAMEWORK_ROOT) / "knowledge" / "active"


def _framework_dir(project_path: str) -> Optional[Path]:
    resolved = load_resolved_config(Path(project_path))
    if resolved is None:
        return None
    return Path(project_path) / resolved.get("framework_root", CANONICAL_FRAMEWORK_ROOT)


def _latest_workspace(framework: Path) -> Optional[Path]:
    candidates = [
        path.parent
        for path in (framework / "changes").glob("*/STATE.yaml")
        if path.is_file()
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda path: (path / "STATE.yaml").stat().st_mtime)


def read_run(project_path: str, active: Optional[Path] = None) -> RunState:
    state = RunState(project_path=str(project_path))

    framework = active.parents[1] if active is not None else _framework_dir(project_path)
    if framework is None:
        return state  # not an Maika project → idle

    ws = _latest_workspace(framework)
    if ws is None:
        return state

    mtimes: list[float] = []
    state_path = ws / "STATE.yaml"
    try:
        state_doc = yaml.safe_load(state_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        state.stale = True
        state_doc = {}
    state.phase_state = state_doc.get("state")
    state.ticket_id = state_doc.get("change_id") or ws.name
    mtimes.append(state_path.stat().st_mtime)

    tq_path = ws / "generated" / "TASK_QUEUE.json"
    if tq_path.exists():
        try:
            queue = json.loads(tq_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            queue = None
            state.stale = True
        if isinstance(queue, dict):
            tasks = queue.get("tasks", [])
            if isinstance(tasks, list):
                state.tasks_total = len(tasks)
                state.tasks_done = sum(1 for t in tasks if isinstance(t, dict) and t.get("status") == "done")
                for t in tasks:
                    if isinstance(t, dict) and t.get("status") == "in_progress":
                        state.active_task = t.get("title") or t.get("desc") or t.get("id")
                        break
            if state.ticket_id is None:
                state.ticket_id = queue.get("change_id")
            mtimes.append(tq_path.stat().st_mtime)

    if mtimes:
        state.updated_at = datetime.fromtimestamp(max(mtimes), timezone.utc).isoformat()
    return state
