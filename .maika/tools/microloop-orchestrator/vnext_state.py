"""vNext change workspace + state machine (Master Plan v2 §8, §9).

BLOCKED mang metadata reason; class ghi ở CHANGE.yaml; 14 states.
"""
from datetime import datetime, timezone
from pathlib import Path

import yaml

STATES = [
    "INTAKE", "EXPLORING", "RECONCILING", "BRAINSTORMING", "SPEC_REVIEW",
    "PLANNING", "PLAN_REVIEW", "EXECUTING", "VERIFYING", "FINAL_REVIEW",
    "COMPLETED", "ARCHIVED", "BLOCKED", "CANCELLED",
]
CLASSES = {"trivial", "small", "standard", "architectural"}
BLOCK_REASONS = {"grounding", "stale_plan", "capability", "user_input", "environment", "verification"}

# W1: chỉ các transition mà slice này dùng + BLOCKED/CANCELLED từ mọi state.
ALLOWED = {
    "INTAKE": {"EXPLORING", "PLANNING"},
    "EXPLORING": {"RECONCILING", "BRAINSTORMING"},
    "RECONCILING": {"BRAINSTORMING"},
    "BRAINSTORMING": {"SPEC_REVIEW"},
    "SPEC_REVIEW": {"PLANNING"},
    "PLANNING": {"PLAN_REVIEW"},
    "PLAN_REVIEW": {"PLANNING", "EXECUTING"},
    "EXECUTING": {"VERIFYING", "FINAL_REVIEW"},
    "VERIFYING": {"FINAL_REVIEW", "COMPLETED"},
    "FINAL_REVIEW": {"VERIFYING", "COMPLETED"},
    "COMPLETED": {"ARCHIVED"},
    "BLOCKED": set(STATES) - {"BLOCKED"},
    "ARCHIVED": set(), "CANCELLED": set(),
}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _load_yaml(path):
    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}


def _dump_yaml(doc, path):
    Path(path).write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")


def init_workspace(changes_root, change_id, klass, title):
    if klass not in CLASSES:
        raise ValueError(f"bad change class: {klass}")
    ws = Path(changes_root) / change_id
    for sub in ("exploration", "generated", "briefs", "results", "reviews"):
        (ws / sub).mkdir(parents=True, exist_ok=True)
    _dump_yaml({"change_id": change_id, "class": klass, "title": title,
                "created_at": _now()}, ws / "CHANGE.yaml")
    _dump_yaml({"change_id": change_id, "state": "INTAKE",
                "updated_at": _now(), "blocked": None}, ws / "STATE.yaml")
    (ws / "INTENT.md").write_text(
        f"# Intent\n\nChange: {change_id}\n\nSummary:\n", encoding="utf-8"
    )
    _dump_yaml({
        "version": 1,
        "codebase": {},
        "business": {},
        "conventions": {},
    }, ws / "exploration" / "GROUNDING.yaml")
    _dump_yaml({
        "version": 1,
        "change_id": change_id,
        "claims": [],
    }, ws / "exploration" / "EVIDENCE_MANIFEST.yaml")
    (ws / "RECONCILIATION.md").write_text("# Reconciliation\n\n", encoding="utf-8")
    return ws


def load_state(ws):
    return _load_yaml(Path(ws) / "STATE.yaml")


def transition(ws, new_state, blocked=None):
    st = load_state(ws)
    cur = st["state"]
    if new_state not in STATES:
        raise ValueError(f"unknown state: {new_state}")
    if new_state == "BLOCKED":
        if not blocked or blocked.get("reason") not in BLOCK_REASONS:
            raise ValueError("BLOCKED requires blocked={'reason': <valid>, ...}")
    elif new_state != "CANCELLED" and new_state not in ALLOWED.get(cur, set()):
        raise ValueError(f"illegal transition {cur} -> {new_state}")
    st.update(state=new_state, updated_at=_now(),
              blocked=(dict(blocked, since=_now()) if new_state == "BLOCKED" else None))
    _dump_yaml(st, Path(ws) / "STATE.yaml")
    return st


def workflow_engine(config):
    """Flag đọc từ execution-mode.yaml đã render. Mặc định legacy."""
    return (config or {}).get("workflow_engine", "legacy")
