"""Deterministic adaptive workflow policy for Maika vNext.

This module owns risk classification, escalation decisions, and class budgets so
CLI/orchestrator paths cannot drift into parallel policy implementations.
"""

from __future__ import annotations

import hashlib
import fnmatch
import json
import os
import re
import socket
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml


CLASS_ORDER = ("trivial", "small", "standard", "architectural")
AUTHORITY_RANK = {name: index for index, name in enumerate(CLASS_ORDER)}
STANDARD_SIGNALS = (
    "public_contract_changed", "database_changed", "event_contract_changed",
    "transaction_changed", "concurrency_changed",
)
ARCHITECTURAL_SIGNALS = (
    "security_changed", "migration_required", "infrastructure_changed",
    "cross_service_architecture",
)
SOURCE_SUFFIXES = {".java", ".kt", ".kts", ".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".cs", ".cpp", ".c", ".sql"}
DEFAULT_RISK_RULES = {
    "public_contract": ["**/controller/**", "**/controllers/**", "**/api/**", "**/openapi/**", "**/*.proto"],
    "database": ["**/migration/**", "**/migrations/**", "**/repository/**", "**/repositories/**", "**/*.sql"],
    "event": ["**/kafka/**", "**/event/**", "**/events/**", "**/consumer/**", "**/producer/**"],
    "security": ["**/security/**", "**/auth/**", "**/permission/**", "**/permissions/**"],
    "infrastructure": ["**/terraform/**", "**/k8s/**", "**/kubernetes/**", "**/Dockerfile", "**/docker-compose.yml"],
}
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


@dataclass(frozen=True)
class RuntimePolicy:
    token_budget: dict
    command_policy: dict
    worker_timeout_seconds: int = 900
    max_retries: int = 2

    @classmethod
    def from_config(cls, config: dict | None = None) -> "RuntimePolicy":
        config = config or {}
        budgets = {name: dict(DEFAULT_TOKEN_BUDGET[name]) for name in CLASS_ORDER}
        override = config.get("token_budget") or {}
        for task_class in CLASS_ORDER:
            if isinstance(override.get(task_class), dict):
                budgets[task_class].update(override[task_class])
        return cls(
            token_budget=budgets,
            command_policy=dict(config.get("command_policy") or {}),
            worker_timeout_seconds=int(config.get("worker_timeout_seconds", 900)),
            max_retries=int(config.get("max_retries", 2)),
        )


def estimate_tokens(text: str) -> int:
    return (len(text) + 3) // 4


def select_evidence(items: list[dict], maximum: int) -> tuple[list[dict], dict]:
    """Select evidence deterministically, preserving required items first."""
    def field(item, name, default=None):
        return item.get(name, default) if isinstance(item, dict) else default
    ranked = sorted(items, key=lambda item: (
        not bool(field(item, "required", False)),
        -AUTHORITY_RANK.get(str(field(item, "authority", "trivial")), 0),
        str(field(item, "id", "") or item),
    ))
    selected = ranked[:maximum]
    omitted = ranked[maximum:]
    if any(field(item, "required", False) for item in omitted):
        raise BudgetExceeded("required evidence exceeds evidence budget")
    return selected, {"evidence_selected": len(selected), "evidence_omitted": len(omitted)}


@dataclass(frozen=True)
class RuntimeOwner:
    pid: int = field(default_factory=os.getpid)
    host: str = field(default_factory=socket.gethostname)
    lease_seconds: int = 900


def _sha256_bytes(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _canonical_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return _sha256_bytes(payload.encode("utf-8"))


def _git(repo_root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=repo_root, capture_output=True, text=True,
        encoding="utf-8", errors="replace", check=False,
    )


def _worktree_snapshot(repo_root: Path) -> dict[str, str]:
    """Return hashes for the paths currently reported dirty by Git."""
    probe = _git(repo_root, "status", "--porcelain", "-z", "--untracked-files=all")
    if probe.returncode != 0:
        raise RuntimeError(f"cannot inspect Git worktree: {probe.stderr.strip()}")
    paths: set[str] = set()
    records = probe.stdout.split("\0")
    index = 0
    while index < len(records):
        record = records[index]
        index += 1
        if not record:
            continue
        status, path = record[:2], record[3:]
        if status[0] in {"R", "C"} and index < len(records):
            paths.add(records[index])
            index += 1
        paths.add(path)
    snapshot = {}
    for rel in sorted(paths):
        target = repo_root / rel
        if target.is_file():
            snapshot[rel] = _sha256_bytes(target.read_bytes())
        elif target.exists():
            snapshot[rel] = "directory"
        else:
            snapshot[rel] = "deleted"
    return snapshot


def _scope_from_task(task: dict) -> dict:
    files = (task.get("scope") or {}).get("files") or {}
    scope = {}
    for key in ("create", "modify", "delete", "test"):
        normalized = []
        for raw in files.get(key) or []:
            if not isinstance(raw, str) or not raw.strip():
                raise ValueError(f"invalid {key} scope path")
            path = Path(raw)
            if path.is_absolute() or ".." in path.parts or "\\" in raw:
                raise ValueError(f"scope path must be repo-relative POSIX path: {raw}")
            normalized.append(path.as_posix())
        scope[key] = sorted(set(normalized))
    return scope


def _atomic_yaml(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            yaml.safe_dump(value, handle, sort_keys=False, allow_unicode=True)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def build_lightweight_execution_contract(
    workspace: Path, repo_root: Path, task: dict, state: dict,
    owner: RuntimeOwner | None = None,
) -> dict:
    """Build the trusted execution envelope before a lightweight worker starts."""
    workspace, repo_root = Path(workspace), Path(repo_root)
    owner = owner or RuntimeOwner()
    task_class = task.get("class")
    if task_class not in {"trivial", "small"}:
        raise ValueError("lightweight execution contract only supports trivial/small")
    if state.get("state") != "INTAKE":
        raise ValueError("lightweight execution contract requires INTAKE state")
    scope = _scope_from_task(task)
    if not any(scope.values()):
        raise ValueError("lightweight execution contract requires non-empty declared scope")
    task_path = workspace / "TASK.yaml"
    if not task_path.is_file():
        raise ValueError("TASK.yaml is missing")
    evidence_path = workspace / "EVIDENCE.yaml"
    if task_class == "small" and not evidence_path.is_file():
        raise ValueError("small lightweight execution requires EVIDENCE.yaml")
    now = datetime.now(timezone.utc)
    head = _git(repo_root, "rev-parse", "HEAD")
    if head.returncode != 0:
        raise RuntimeError(f"cannot resolve Git HEAD: {head.stderr.strip()}")
    baseline = _worktree_snapshot(repo_root)
    change_id = task.get("change_id") or workspace.name
    contract = {
        "version": 1,
        "change_id": change_id,
        "task_class": task_class,
        "execution_id": f"EXEC-{change_id}-{os.getpid()}-{int(now.timestamp())}",
        "state": "EXECUTING",
        "task_hash": _sha256_bytes(task_path.read_bytes()),
        "evidence_hash": (
            _sha256_bytes(evidence_path.read_bytes()) if task_class == "small" else None
        ),
        "scope_hash": _canonical_hash(scope),
        "role": "application-implementer",
        "workspace_path": workspace.resolve().relative_to(repo_root.resolve()).as_posix(),
        "scope": scope,
        "base_revision": {
            "git_head": head.stdout.strip(),
            "worktree_digest": _canonical_hash(baseline),
            "dirty_paths": baseline,
        },
        "runtime": {
            "owner_pid": owner.pid,
            "owner_host": owner.host,
            "started_at": now.isoformat(),
            "lease_expires_at": (now + timedelta(seconds=owner.lease_seconds)).isoformat(),
        },
        "status": "active",
    }
    _atomic_yaml(workspace / "generated" / "LIGHTWEIGHT_EXECUTION.yaml", contract)
    return contract


def inspect_lightweight_changes(repo_root: Path, contract: dict) -> dict:
    """Mechanically identify files changed after the contract baseline."""
    repo_root = Path(repo_root)
    before = (contract.get("base_revision") or {}).get("dirty_paths") or {}
    after = _worktree_snapshot(repo_root)
    touched = sorted(path for path in set(before) | set(after) if before.get(path) != after.get(path))
    workspace_path = str(contract.get("workspace_path") or "").rstrip("/")
    if workspace_path:
        touched = [path for path in touched if path != workspace_path and not path.startswith(workspace_path + "/")]
    allowed = {path for values in (contract.get("scope") or {}).values() for path in (values or [])}
    return {
        "touched_files": touched,
        "allowed": sorted(set(touched) & allowed),
        "outside_scope": sorted(set(touched) - allowed),
    }


def invalidate_lightweight_execution_contract(workspace: Path, status: str) -> None:
    path = Path(workspace) / "generated" / "LIGHTWEIGHT_EXECUTION.yaml"
    if not path.exists():
        return
    contract = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    contract["status"] = status
    contract["invalidated_at"] = datetime.now(timezone.utc).isoformat()
    _atomic_yaml(path, contract)


def _rank(klass: str) -> int:
    if klass not in CLASS_ORDER:
        raise ValueError(f"unknown task class: {klass}")
    return CLASS_ORDER.index(klass)


def derive_risk_signals(task: dict, repo_root: Path, rules: dict | None = None) -> dict:
    """Derive conservative, reproducible risk signals from declared scope and repo content."""
    repo_root = Path(repo_root)
    scope = _scope_from_task(task)
    paths = sorted({path for values in scope.values() for path in values})
    create_paths = set(scope["create"])
    segments = {part.lower() for path in paths for part in Path(path).parts}
    suffixes = {Path(path).suffix.lower() for path in paths}
    text_parts = []
    unknown = 0
    for rel in paths:
        target = repo_root / rel
        if target.is_file():
            try:
                text_parts.append(target.read_text(encoding="utf-8", errors="replace")[:262144])
            except OSError:
                unknown += 1
        elif rel not in create_paths:
            unknown += 1
    text = "\n".join(text_parts).lower()
    resolved_rules = {key: list(value) for key, value in DEFAULT_RISK_RULES.items()}
    for key, patterns in (rules or {}).items():
        if key in resolved_rules and isinstance(patterns, list):
            resolved_rules[key] = [str(pattern) for pattern in patterns]

    def matches(category: str) -> bool:
        return any(
            fnmatch.fnmatch(path, pattern) or
            (pattern.startswith("**/") and fnmatch.fnmatch(path, pattern[3:]))
            for path in paths for pattern in resolved_rules[category]
        )

    module_names: set[str] = set()
    for settings_name in ("settings.gradle", "settings.gradle.kts"):
        settings = repo_root / settings_name
        if settings.is_file():
            body = settings.read_text(encoding="utf-8", errors="replace")
            module_names.update(item.replace(":", "/").strip("/") for item in re.findall(r"['\"]:([^'\"]+)['\"]", body))
    pom = repo_root / "pom.xml"
    if pom.is_file():
        module_names.update(re.findall(r"<module>\s*([^<]+?)\s*</module>", pom.read_text(encoding="utf-8", errors="replace")))
    affected = set()
    for path in paths:
        matched = next((module for module in sorted(module_names, key=len, reverse=True)
                        if path == module or path.startswith(module.rstrip("/") + "/")), None)
        affected.add(matched or ("." if Path(path).parts[:1] and Path(path).parts[0].lower() in
                                  {"src", "test", "tests", "docs", "scripts", ".maika"}
                                  else (Path(path).parts[0] if Path(path).parts else ".")))

    public_contract = matches("public_contract")
    database = matches("database")
    event = matches("event")
    security = matches("security")
    migration = bool(segments & {"migration", "migrations"} or "alter table" in text or "create index" in text)
    infrastructure = matches("infrastructure")
    return {
        "estimated_files": len(paths),
        "affected_modules": len(affected),
        "public_contract_changed": public_contract,
        "database_changed": database,
        "event_contract_changed": event or "@kafkalistener" in text,
        "transaction_changed": "@transactional" in text or "transaction" in text,
        "concurrency_changed": any(token in text for token in ("synchronized", "mutex", "semaphore", "atomic", "concurrent")),
        "security_changed": security or any(token in text for token in ("permission", "authorize", "authentication")),
        "migration_required": migration,
        "infrastructure_changed": infrastructure,
        "cross_service_architecture": bool(".proto" in suffixes and len(affected) > 1),
        "application_code_changed": bool(suffixes & SOURCE_SUFFIXES),
        "unknown_count": unknown,
        "affected_module_names": sorted(affected),
        "evidence_paths": paths,
    }


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
        if signals.get("application_code_changed") is True:
            proposed = "small"
            evidence.append("application_code_changed")
        elif files <= 1 and modules <= 1 and unknown == 0:
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
    estimated_tokens: int = 0
    prompt_bytes: int = 0
    evidence_selected: int = 0
    evidence_omitted: int = 0

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
            "estimated_tokens": self.estimated_tokens,
            "estimation_method": "chars_div_4" if self.total_tokens == "unavailable" else None,
            "prompt_bytes": self.prompt_bytes,
            "worker_calls": self.worker_calls,
            "tool_calls": self.tool_calls,
            "evidence_selected": self.evidence_selected,
            "evidence_omitted": self.evidence_omitted,
        }


def execute_lightweight(ws: Path, runner, policy: RuntimePolicy | None = None) -> dict:
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

    policy = policy or RuntimePolicy.from_config()
    tracker = BudgetTracker(klass, config=policy.token_budget)
    try:
        selected, evidence_counts = select_evidence(evidence, int(tracker.limits["max_evidence_items"]))
    except BudgetExceeded as exc:
        return {"status": "blocked", "reason": str(exc), "runtime_metrics": tracker.metrics()}
    tracker.evidence_selected = evidence_counts["evidence_selected"]
    tracker.evidence_omitted = evidence_counts["evidence_omitted"]
    evidence_rel = None
    if klass == "small":
        evidence_rel = "generated/LIGHTWEIGHT_EVIDENCE.yaml"
        _atomic_yaml(ws / evidence_rel, {"version": 1, "items": selected, **evidence_counts})
    result_path = ws / "RESULT.yaml"
    output_contract = (
        f"OUTPUT_FILE: {result_path}\nRespect declared scope and write a versioned RESULT.yaml."
        if klass == "small" else
        "OUTPUT_MODE: exit-status-only\nRespect declared documentation scope; do not create workflow artifacts."
    )
    prompt = (
        f"DISPATCH_TYPE: implementation\nTASK_CLASS: {klass}\n"
        f"ARTIFACT_FILE: {ws / 'TASK.yaml'}\n"
        f"EVIDENCE_FILE: {ws / evidence_rel if evidence_rel else 'inline-task-evidence'}\n"
        f"{output_contract}\n"
    )
    tracker.prompt_bytes = len(prompt.encode("utf-8"))
    tracker.estimated_tokens = estimate_tokens(prompt)
    if tracker.estimated_tokens > int(tracker.limits["max_context_tokens"]):
        return {"status": "blocked", "reason": (
            f"{klass} context budget exceeded ({tracker.estimated_tokens}/"
            f"{tracker.limits['max_context_tokens']} estimated tokens)"
        ), "runtime_metrics": tracker.metrics()}
    tracker.record_worker_call()
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
