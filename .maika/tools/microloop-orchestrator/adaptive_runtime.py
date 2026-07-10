"""Deterministic adaptive workflow policy for Maika vNext.

This module owns risk classification, escalation decisions, and class budgets so
CLI/orchestrator paths cannot drift into parallel policy implementations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


CLASS_ORDER = ("trivial", "small", "standard", "architectural")
STANDARD_SIGNALS = (
    "public_contract_changed", "database_changed", "event_contract_changed",
    "transaction_changed", "concurrency_changed",
)
ARCHITECTURAL_SIGNALS = (
    "security_changed", "migration_required", "infrastructure_changed",
    "cross_service_architecture",
)
ESCALATION_SIGNALS = STANDARD_SIGNALS + ARCHITECTURAL_SIGNALS + (
    "unresolved_evidence", "unexpected_test_failure", "retry_changed",
    "timeout_changed", "permission_changed",
)

DEFAULT_TOKEN_BUDGET = {
    "version": 1,
    "trivial": {"max_context_tokens": 8000, "max_worker_calls": 1, "max_evidence_items": 5},
    "small": {"max_context_tokens": 20000, "max_worker_calls": 2, "max_evidence_items": 12},
    "standard": {"max_context_tokens": 60000, "max_worker_calls": 6, "max_evidence_items": 30},
    "architectural": {"max_context_tokens": 120000, "max_worker_calls": 12, "max_evidence_items": 60},
}


def _rank(klass: str) -> int:
    if klass not in CLASS_ORDER:
        raise ValueError(f"unknown task class: {klass}")
    return CLASS_ORDER.index(klass)


def classify_risk(risk_signals: dict | None, current_class: str | None = None) -> dict:
    """Return a stable classification from explicit signals only."""
    signals = dict(risk_signals or {})
    evidence: list[str] = []
    triggers: list[str] = []
    confirmed_standard = [name for name in STANDARD_SIGNALS if signals.get(name) is True]
    confirmed_architectural = [name for name in ARCHITECTURAL_SIGNALS if signals.get(name) is True]
    evidence.extend(confirmed_standard)
    evidence.extend(confirmed_architectural)

    if confirmed_architectural:
        proposed = "architectural"
    elif confirmed_standard:
        proposed = "standard"
    else:
        files = int(signals.get("estimated_files") or 0)
        modules = int(signals.get("affected_modules") or 0)
        unknown = int(signals.get("unknown_count") or 0)
        if files <= 1 and modules <= 1 and unknown == 0:
            proposed = "trivial"
        else:
            proposed = "small"
        evidence.extend([
            f"estimated_files:{files}", f"affected_modules:{modules}",
            f"unknown_count:{unknown}",
        ])
        if unknown > (1 if proposed == "trivial" else 3):
            proposed = "standard"
            triggers.append("unknown_count_above_threshold")

    if current_class is not None and _rank(current_class) > _rank(proposed):
        proposed = current_class
        evidence.append(f"monotonic_class_floor:{current_class}")

    triggers.extend(name for name in confirmed_standard + confirmed_architectural if name not in triggers)
    return {
        "version": 1,
        "classification": {
            "proposed_class": proposed,
            "evidence": evidence,
            "escalation_triggers": triggers,
        },
    }


def evaluate_escalation(current_class: str, task: dict, observed: dict) -> dict:
    """Fail closed when observations invalidate a lightweight task envelope."""
    triggers: list[str] = []
    expected = set(task.get("expected_files") or [])
    touched = set(observed.get("touched_files") or [])
    if expected and not touched.issubset(expected):
        triggers.append("outside_expected_scope")
    for signal in ESCALATION_SIGNALS:
        if observed.get(signal) is True:
            triggers.append(signal)
    unknown_threshold = int(task.get("unknown_threshold", 1 if current_class == "trivial" else 3))
    if int(observed.get("unknown_count") or 0) > unknown_threshold:
        triggers.append("unknown_count_above_threshold")

    combined = dict(observed)
    combined.setdefault("estimated_files", len(touched))
    combined.setdefault("affected_modules", observed.get("affected_modules", 1))
    classified = classify_risk(combined, current_class=current_class)
    target = classified["classification"]["proposed_class"]
    if triggers and _rank(target) <= _rank(current_class):
        target = "standard" if current_class in {"trivial", "small"} else current_class
    blocked = bool(triggers) and _rank(target) > _rank(current_class)
    return {
        "version": 1,
        "blocked": blocked,
        "target_class": target,
        "triggers": sorted(set(triggers)),
        "lightweight_artifacts_valid": not blocked,
    }


class BudgetExceeded(RuntimeError):
    pass


@dataclass
class BudgetTracker:
    task_class: str
    config: dict = field(default_factory=lambda: DEFAULT_TOKEN_BUDGET)
    worker_calls: int = 0
    tool_calls: int = 0
    total_tokens: int | str = "unavailable"
    token_count_reason: str = "platform did not provide token usage"

    def __post_init__(self):
        _rank(self.task_class)

    @property
    def limits(self) -> dict:
        return self.config[self.task_class]

    def record_worker_call(self) -> dict:
        maximum = int(self.limits["max_worker_calls"])
        if self.worker_calls >= maximum:
            raise BudgetExceeded(
                f"{self.task_class} worker-call budget exhausted ({self.worker_calls}/{maximum}); escalate or block"
            )
        self.worker_calls += 1
        return {
            "status": "warning" if self.worker_calls == maximum else "ok",
            "worker_calls": self.worker_calls,
            "maximum": maximum,
        }

    def record_tool_call(self) -> None:
        self.tool_calls += 1

    def metrics(self) -> dict:
        return {
            "version": 1,
            "task_class": self.task_class,
            "total_tokens": self.total_tokens,
            "token_count_reason": self.token_count_reason if self.total_tokens == "unavailable" else None,
            "worker_calls": self.worker_calls,
            "tool_calls": self.tool_calls,
        }


def execute_lightweight(ws: Path, runner) -> dict:
    """Execute a validated trivial/small brief with one fresh worker call."""
    ws = Path(ws)
    task = yaml.safe_load((ws / "TASK.yaml").read_text(encoding="utf-8")) or {}
    klass = task.get("class")
    if klass not in {"trivial", "small"}:
        raise ValueError("lightweight execution only supports trivial/small")
    evidence = task.get("evidence") or []
    if klass == "small":
        evidence_doc = yaml.safe_load((ws / "EVIDENCE.yaml").read_text(encoding="utf-8")) or {}
        evidence = evidence_doc.get("items") or evidence
    if not evidence:
        return {"status": "blocked", "reason": "lightweight path requires evidence before change"}
    classified = classify_risk(task.get("risk_signals"), current_class=klass)
    proposed = classified["classification"]["proposed_class"]
    if _rank(proposed) > _rank(klass):
        return {"status": "escalate", "target_class": proposed,
                "triggers": classified["classification"]["escalation_triggers"]}

    tracker = BudgetTracker(klass)
    tracker.record_worker_call()
    result_path = ws / "RESULT.yaml"
    output_contract = (
        f"OUTPUT_FILE: {result_path}\nRespect declared scope and write a versioned RESULT.yaml."
        if klass == "small" else
        "OUTPUT_MODE: exit-status-only\nRespect declared documentation scope; do not create workflow artifacts."
    )
    prompt = (
        f"DISPATCH_TYPE: implementation\nTASK_CLASS: {klass}\n"
        f"ARTIFACT_FILE: {ws / 'TASK.yaml'}\n{output_contract}\n"
    )
    exit_code, output = runner(prompt)
    if exit_code != 0:
        return {"status": "blocked", "reason": f"worker exit {exit_code}: {output}",
                "runtime_metrics": tracker.metrics()}
    if klass == "trivial":
        result = {"version": 1, "status": "success", "observed_risk_signals": {}}
    elif not result_path.exists():
        return {"status": "blocked", "reason": "worker did not write RESULT.yaml",
                "runtime_metrics": tracker.metrics()}
    else:
        result = yaml.safe_load(result_path.read_text(encoding="utf-8")) or {}
    if result.get("version") != 1 or result.get("status") not in {"success", "done"}:
        return {"status": "blocked", "reason": "invalid lightweight RESULT.yaml",
                "runtime_metrics": tracker.metrics()}

    observed = dict(result.get("observed_risk_signals") or {})
    observed.setdefault("touched_files", result.get("touched_files") or [])
    envelope = {
        "expected_files": [path for values in (task.get("scope", {}).get("files") or {}).values()
                           for path in (values or [])],
        "unknown_threshold": 1 if klass == "trivial" else 3,
    }
    escalation = evaluate_escalation(klass, envelope, observed)
    metrics = tracker.metrics()
    evidence_metrics = (yaml.safe_load((ws / "EVIDENCE.yaml").read_text(encoding="utf-8")) or {}).get("evidence_metrics", {}) if (ws / "EVIDENCE.yaml").exists() else {}
    retrieved = int(evidence_metrics.get("retrieved") or 0)
    metrics.update({
        "evidence_reuse_ratio": (int(evidence_metrics.get("reused") or 0) / retrieved) if retrieved else 0.0,
        "retry_count": 0, "real_verification_commands": 0, "review_findings": 0,
        "human_corrections": 0, "knowledge_entries_created": 0,
        "knowledge_entries_reused": int(evidence_metrics.get("reused") or 0),
    })
    if escalation["blocked"]:
        return {"status": "escalate", **escalation, "runtime_metrics": metrics}
    if klass == "small" and result_path.exists():
        result["runtime_metrics"] = metrics
        result_path.write_text(yaml.safe_dump(result, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return {"status": "done", "runtime_metrics": metrics}
