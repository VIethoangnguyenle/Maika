"""vNext change workspace + state machine (Master Plan v2 §8, §9).

BLOCKED mang metadata reason; class ghi ở CHANGE.yaml; 14 states.
"""
from datetime import datetime, timezone
import importlib.util
import os
from pathlib import Path
import sys
import tempfile

import yaml

try:
    from adaptive_runtime import classify_risk
except ModuleNotFoundError:  # importlib callers may not place this directory on sys.path
    _adaptive_path = Path(__file__).with_name("adaptive_runtime.py")
    _adaptive_spec = importlib.util.spec_from_file_location("maika_adaptive_runtime", _adaptive_path)
    _adaptive_module = importlib.util.module_from_spec(_adaptive_spec)
    sys.modules[_adaptive_spec.name] = _adaptive_module
    _adaptive_spec.loader.exec_module(_adaptive_module)
    classify_risk = _adaptive_module.classify_risk

STATES = [
    "INTAKE", "EXPLORING", "RECONCILING", "BRAINSTORMING", "SPEC_REVIEW",
    "PLANNING", "PLAN_REVIEW", "EXECUTING", "VERIFYING", "FINAL_REVIEW",
    "COMPLETED", "ARCHIVED", "BLOCKED", "CANCELLED",
]
CLASSES = {"trivial", "small", "standard", "architectural"}
CLASS_RANK = {name: index for index, name in enumerate(("trivial", "small", "standard", "architectural"))}
BLOCK_REASONS = {"grounding", "stale_plan", "capability", "user_input", "environment", "verification"}

# W1: chỉ các transition mà slice này dùng + BLOCKED/CANCELLED từ mọi state.
ALLOWED = {
    "INTAKE": {"EXPLORING", "PLANNING", "EXECUTING"},
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
    "BLOCKED": set(),
    "ARCHIVED": set(), "CANCELLED": set(),
}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _load_yaml(path):
    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}


def _dump_yaml(doc, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = yaml.safe_dump(doc, sort_keys=False, allow_unicode=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        # newline="" -> no OS newline translation, so artifacts are byte-identical
        # (LF) on POSIX and Windows. Content hashes (read_bytes) then match
        # read_text-based hashes cross-platform.
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def _init_full_artifacts(ws, change_id):
    for sub in ("exploration", "generated", "briefs", "results", "reviews"):
        (ws / sub).mkdir(parents=True, exist_ok=True)
    (ws / "INTENT.md").write_text(
        f"# Intent\n\nChange: {change_id}\n\nSummary:\n", encoding="utf-8"
    )
    _dump_yaml({"version": 1, "codebase": {}, "business": {}, "conventions": {}},
               ws / "exploration" / "GROUNDING.yaml")
    _dump_yaml({"version": 1, "change_id": change_id, "claims": []},
               ws / "exploration" / "EVIDENCE_MANIFEST.yaml")
    _dump_yaml({"version": 1, "change_id": change_id, "questions": []},
               ws / "exploration" / "QUERY_PLAN.yaml")
    _dump_yaml({"version": 1, "providers": {}}, ws / "exploration" / "TOOL_HEALTH.yaml")
    _dump_yaml({"version": 1, "conflicts": []}, ws / "exploration" / "CONFLICTS.yaml")
    _dump_yaml({
        "version": 1, "questions": {"total": 0, "answered": 0, "blocked": 0},
        "required_evidence": {"covered": [], "missing": []}, "verdict": "NEEDS_CONTEXT",
    }, ws / "exploration" / "COVERAGE.yaml")
    _dump_yaml({
        "version": 1, "change_id": change_id, "verified": False, "observations": [],
    }, ws / "reviews" / "SKILL_FEEDBACK.yaml")
    (ws / "RECONCILIATION.md").write_text("# Reconciliation\n\n", encoding="utf-8")


def init_workspace(changes_root, change_id, klass, title):
    if klass not in CLASSES:
        raise ValueError(f"bad change class: {klass}")
    ws = Path(changes_root) / change_id
    ws.mkdir(parents=True, exist_ok=True)
    _dump_yaml({
        "version": 1, "change_id": change_id, "class": klass,
        "requested_class": klass, "effective_class": klass,
        "classification": {"source": "requested", "classified_at": _now(), "evidence": []},
        "title": title, "created_at": _now(),
    }, ws / "CHANGE.yaml")
    _dump_yaml({"version": 1, "change_id": change_id, "state": "INTAKE",
                "updated_at": _now(), "blocked": None}, ws / "STATE.yaml")
    if klass in {"trivial", "small"}:
        signals = {"estimated_files": 0, "affected_modules": 0, "unknown_count": 0}
        _dump_yaml({
            "version": 1, "change_id": change_id, "class": klass,
            "intent": {"summary": title},
            "risk_signals": signals,
            **classify_risk(signals, current_class=klass),
            "scope": {"files": {"modify": [], "test": []}},
            "evidence": [], "plan": [],
            "verification": {"commands": []},
            "escalation_triggers": [],
        }, ws / "TASK.yaml")
        if klass == "small":
            _dump_yaml({
                "version": 1, "change_id": change_id, "items": [],
                "evidence_metrics": {"retrieved": 0, "reused": 0, "revalidated": 0, "newly_created": 0},
            }, ws / "EVIDENCE.yaml")
            _dump_yaml({
                "version": 1, "change_id": change_id, "status": "pending", "changes": [],
                "runtime_metrics": {
                    "task_class": "small", "total_tokens": "unavailable",
                    "token_count_reason": "platform did not provide token usage",
                    "worker_calls": 0, "tool_calls": 0, "evidence_reuse_ratio": 0.0,
                    "retry_count": 0, "real_verification_commands": 0,
                    "review_findings": 0, "human_corrections": 0,
                    "knowledge_entries_created": 0, "knowledge_entries_reused": 0,
                },
            }, ws / "RESULT.yaml")
        return ws

    _init_full_artifacts(ws, change_id)
    return ws


def load_state(ws):
    return _load_yaml(Path(ws) / "STATE.yaml")


def transition(ws, new_state, blocked=None):
    st = load_state(ws)
    cur = st["state"]
    if new_state not in STATES:
        raise ValueError(f"unknown state: {new_state}")
    if cur == "BLOCKED":
        resume_state = (st.get("blocked") or {}).get("resume_state")
        if new_state not in {resume_state, "CANCELLED"}:
            raise ValueError(f"BLOCKED can only resume to {resume_state} or CANCELLED")
    if new_state == "BLOCKED":
        if not blocked or blocked.get("reason") not in BLOCK_REASONS:
            raise ValueError("BLOCKED requires blocked={'reason': <valid>, ...}")
    elif cur == "BLOCKED":
        pass
    elif new_state != "CANCELLED" and new_state not in ALLOWED.get(cur, set()):
        raise ValueError(f"illegal transition {cur} -> {new_state}")
    blocked_doc = None
    if new_state == "BLOCKED":
        blocked_doc = dict(blocked, previous_state=cur,
                           resume_state=blocked.get("resume_state", cur), since=_now())
    st.update(state=new_state, updated_at=_now(), blocked=blocked_doc)
    _dump_yaml(st, Path(ws) / "STATE.yaml")
    return st


def start_exploration(ws):
    """Start the public exploration phase; retrying the command is harmless."""
    state = load_state(ws)
    if state.get("state") == "EXPLORING":
        return state
    if state.get("state") != "INTAKE":
        raise ValueError(f"cannot start exploration from {state.get('state')}")
    return transition(ws, "EXPLORING")


def record_runtime_metrics(ws, metrics):
    state = load_state(ws)
    state["runtime_metrics"] = {"version": 1, **dict(metrics)}
    state["updated_at"] = _now()
    _dump_yaml(state, Path(ws) / "STATE.yaml")
    return state


def record_effective_class(ws, effective_class, signals, evidence):
    """Persist runtime classification while retaining `class` compatibility."""
    if effective_class not in CLASSES:
        raise ValueError(f"bad effective class: {effective_class}")
    ws = Path(ws)
    change = _load_yaml(ws / "CHANGE.yaml")
    requested = change.get("requested_class") or change.get("class")
    if CLASS_RANK[effective_class] < CLASS_RANK[requested]:
        effective_class = requested
    change.update({
        "requested_class": requested, "effective_class": effective_class, "class": effective_class,
        "classification": {"source": "runtime", "classified_at": _now(),
                           "signals": signals, "evidence": list(evidence)},
    })
    _dump_yaml(change, ws / "CHANGE.yaml")
    return change


def escalate_to_full(ws, target_class, triggers):
    if target_class not in {"standard", "architectural"}:
        raise ValueError("fast path can only escalate to standard/architectural")
    ws = Path(ws)
    change = _load_yaml(ws / "CHANGE.yaml")
    current = change.get("class")
    if current not in {"trivial", "small"}:
        raise ValueError(f"cannot escalate full workflow from {current}")
    change.update({
        "class": target_class, "effective_class": target_class,
        "requested_class": change.get("requested_class") or current,
        "classification": {"source": "runtime", "classified_at": _now(),
                           "evidence": list(triggers)},
        "escalated_from": current,
        "escalation_triggers": list(triggers), "escalated_at": _now(),
    })
    _dump_yaml(change, ws / "CHANGE.yaml")
    task = _load_yaml(ws / "TASK.yaml")
    task["classification"] = {
        "proposed_class": target_class, "evidence": list(triggers),
        "escalation_triggers": list(triggers),
    }
    task["lightweight_artifacts_valid"] = False
    _dump_yaml(task, ws / "TASK.yaml")
    _init_full_artifacts(ws, change["change_id"])
    return start_exploration(ws)


def workflow_engine(config):
    """Flag đọc từ execution-mode.yaml đã render. Mặc định legacy."""
    return (config or {}).get("workflow_engine", "legacy")
