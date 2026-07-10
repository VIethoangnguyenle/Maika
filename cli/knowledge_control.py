"""Runtime consumers for Maika project learning and guarded skill evolution."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import yaml


@dataclass
class Validation:
    ok: bool
    reason: str = ""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slug(value: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip()).strip("-")
    return clean or "KNOWLEDGE"


def _yaml(text: str) -> dict:
    data = yaml.safe_load(text) or {}
    return data if isinstance(data, dict) else {}


def validate_skill_feedback(text: str) -> Validation:
    data = _yaml(text)
    if data.get("version") != 1 or not data.get("change_id") or data.get("verified") is not True:
        return Validation(False, "requires version 1, change_id, verified: true")
    fields = {"id", "skill", "category", "severity", "statement", "evidence",
              "recurrence_key", "recommendation"}
    for item in data.get("observations") or []:
        if not isinstance(item, dict) or fields - set(item) or not item.get("evidence"):
            return Validation(False, "invalid observation")
        if item.get("category") not in {"editorial", "behavioral", "contractual"}:
            return Validation(False, "invalid category")
    return Validation(True)


def validate_markdown_knowledge_trace(text: str) -> Validation:
    match = re.search(r"^##\s+Knowledge Trace\s*$.*?```yaml\s*(.*?)```", text,
                      re.MULTILINE | re.DOTALL)
    if not match:
        return Validation(False, "missing Knowledge Trace YAML")
    decision = _yaml(match.group(1)).get("decision")
    required = {"id", "statement", "type", "knowledge_questions", "evidence_ids",
                "authority", "conflicts", "assumptions", "confidence", "freshness", "verdict"}
    if not isinstance(decision, dict) or required - set(decision):
        return Validation(False, "Knowledge Trace missing required fields")
    if not decision.get("knowledge_questions") or not decision.get("evidence_ids"):
        return Validation(False, "Knowledge Trace requires questions and evidence")
    if any(isinstance(item, dict) and item.get("status") not in {"resolved", "superseded"}
           for item in decision.get("conflicts") or []):
        return Validation(False, "Knowledge Trace has unresolved conflicts")
    if decision.get("verdict") not in {"accepted", "approved", "verified"}:
        return Validation(False, "Knowledge Trace verdict not accepted")
    return Validation(True)


def validate_skill_candidate(text: str) -> Validation:
    data = _yaml(text)
    required = {"version", "candidate_id", "target_skill", "status", "classification",
                "problem", "evidence", "proposed_change", "expected_effect",
                "compatibility", "validation"}
    if required - set(data):
        return Validation(False, "missing candidate fields")
    if data.get("classification") not in {"editorial", "behavioral", "contractual"}:
        return Validation(False, "invalid classification")
    return Validation(True)


def candidate_threshold_from_document(data: dict) -> bool:
    problem, evidence = data.get("problem") or {}, data.get("evidence") or {}
    if evidence.get("critical_incident") or evidence.get("user_directive") or (
        evidence.get("dogfood_failure") and evidence.get("reproducible")
    ):
        return evidence.get("verified") is True
    return (int(problem.get("occurrences") or 0) >= 3 and
            len(set(evidence.get("changes") or [])) >= 2 and evidence.get("verified") is True)


def candidate_triggered(observations: list[dict]) -> bool:
    verified = [item for item in observations if item.get("verified") is True]
    if any(item.get("critical_incident") or item.get("user_directive") or
           (item.get("dogfood_failure") and item.get("reproducible")) for item in verified):
        return True
    explicit_signals = (
        "human_correction", "repeated_failure", "unexpected_blast_radius",
        "reusable_review_finding", "measurable_token_reduction",
    )
    if any(any(item.get(signal) for signal in explicit_signals) for item in verified):
        return True
    if any(int(item.get("observed_convention_count") or 0) >= 2 for item in verified):
        return True
    by_key: dict[str, list[dict]] = {}
    for item in verified:
        if item.get("recurrence_key"):
            by_key.setdefault(item["recurrence_key"], []).append(item)
    return any(len(items) >= 3 and len({item.get("change_id") for item in items}) >= 2
               for items in by_key.values())


_POISON = (
    "ignore rules", "disable verification", "skip mcp", "modify skill directly",
)


def sanitize_learning_text(value: str) -> tuple[str, list[str]]:
    clean, threats = value, []
    for phrase in _POISON:
        if phrase in clean.lower():
            threats.append(phrase)
            clean = re.sub(re.escape(phrase), "[UNTRUSTED_INSTRUCTION]", clean,
                           flags=re.IGNORECASE)
    return clean, threats


def sanitize_learning_payload(value):
    if isinstance(value, str):
        return sanitize_learning_text(value)
    if isinstance(value, list):
        cleaned, threats = [], []
        for item in value:
            safe, found = sanitize_learning_payload(item)
            cleaned.append(safe); threats.extend(found)
        return cleaned, threats
    if isinstance(value, dict):
        cleaned, threats = {}, []
        for key, item in value.items():
            safe, found = sanitize_learning_payload(item)
            cleaned[key] = safe; threats.extend(found)
        return cleaned, threats
    return value, []


_SKILL_INVARIANTS = (
    "current source", "evidence", "verification", "write gate", "knowledge-native",
    "capability ids",
)


def validate_skill_regression(before: str, after: str) -> Validation:
    removed = [item for item in _SKILL_INVARIANTS
               if item in before.lower() and item not in after.lower()]
    return Validation(False, "removed invariants: " + ", ".join(removed)) if removed else Validation(True)


def _version(value: str) -> tuple[int, ...]:
    try:
        return tuple(int(part) for part in str(value).split("."))
    except ValueError:
        return ()


def validate_skill_promotion(record: dict) -> Validation:
    if not _version(record.get("new_version")) > _version(record.get("old_version")):
        return Validation(False, "version must increase")
    if record.get("independent_review") != "approved" or record.get("tests_passed") is not True:
        return Validation(False, "review/tests required")
    if record.get("classification") in {"behavioral", "contractual"} and record.get("dogfood_passed") is not True:
        return Validation(False, "dogfood required")
    if record.get("classification") == "contractual" and record.get("human_approval") is not True:
        return Validation(False, "human approval required")
    return Validation(True)


class LearningStore:
    """Small deterministic store used by archive and JIT context routing."""

    def __init__(self, root: Path):
        root = Path(root)
        self.long_term = root if root.name == "long-term" else root / "knowledge" / "long-term"
        self.project = self.long_term / "project-knowledge"
        self.feedback = self.long_term.parent / "skill-evolution" / "feedback"

    def promote(self, entry: dict) -> Path:
        entry = dict(entry)
        entry.setdefault("status", "active")
        entry.setdefault("created_at", _now())
        entry.setdefault("provenance", {})
        path = self.project / f"{_slug(str(entry['id']))}.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(entry, sort_keys=False, allow_unicode=True), encoding="utf-8")
        return path

    def retrieve(self, applies_to: list[str], questions: list[str]) -> dict:
        terms = {str(item).lower() for item in applies_to}
        terms.update(word.lower() for q in questions for word in re.findall(r"[A-Za-z0-9_-]{4,}", q))
        matched = []
        for path in sorted(self.project.glob("*.yaml")):
            item = _yaml(path.read_text(encoding="utf-8"))
            if item.get("status") != "active":
                continue
            haystack = " ".join([str(item.get("id", "")), str(item.get("statement", "")),
                                 " ".join(item.get("applies_to") or [])]).lower()
            if not terms or any(term in haystack for term in terms):
                item["path"] = str(path)
                matched.append(item)
        return {"knowledge_slice": matched, "knowledge_questions": questions}

    def record_feedback(self, item: dict) -> Path:
        clean, threats = sanitize_learning_payload(dict(item))
        clean["poisoning_flags"] = sorted(set(threats))
        prefix = _slug(str(clean.get("change_id", "change")))
        sequence = 1
        path = self.feedback / f"{prefix}-{sequence}.yaml"
        while path.exists():
            sequence += 1
            path = self.feedback / f"{prefix}-{sequence}.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(clean, sort_keys=False, allow_unicode=True), encoding="utf-8")
        return path

    def cluster_candidate(self, recurrence_key: str) -> dict:
        observations = [_yaml(path.read_text(encoding="utf-8")) for path in self.feedback.glob("*.yaml")]
        observations = [item for item in observations if item.get("recurrence_key") == recurrence_key]
        if not candidate_triggered(observations):
            raise ValueError("candidate threshold not met")
        return {
            "version": 1, "candidate_id": f"SC-{_slug(recurrence_key)}",
            "target_skill": observations[0].get("skill"), "status": "proposed",
            "classification": observations[0].get("category", "behavioral"),
            "problem": {"statement": observations[0].get("statement") or recurrence_key,
                        "recurrence_key": recurrence_key, "severity": observations[0].get("severity", "important"),
                        "occurrences": len(observations)},
            "evidence": {"changes": sorted({item["change_id"] for item in observations}),
                         "reviews": [], "incidents": [], "source_anchors": [],
                         "verified": True,
                         "critical_incident": any(item.get("critical_incident") for item in observations),
                         "user_directive": any(item.get("user_directive") for item in observations),
                         "dogfood_failure": any(item.get("dogfood_failure") for item in observations),
                         "reproducible": any(item.get("reproducible") for item in observations)},
            "proposed_change": {"sections": [], "summary": observations[0].get("recommendation", ""),
                                "before": "", "after": ""},
            "expected_effect": {"improvements": [], "risks": [], "token_impact": "unknown",
                                "behavior_change": observations[0].get("category", "behavioral") != "editorial"},
            "compatibility": {"capability_ids_changed": False, "output_contract_changed": False,
                              "runtime_consumer_changed": False, "migration_required": False},
            "validation": {"required_tests": [], "dogfood_scenarios": [], "regression_risks": []},
            "skill_evaluation": {
                "skill": observations[0].get("skill"), "candidate_version": "1",
                "evaluation_tasks": [], "before_metrics": {}, "after_metrics": {},
                "verdict": "PENDING",
            },
            "rollback": {"previous_version": "current", "status": "ready"},
        }


def process_skill_feedback(target: Path, framework_root: str, ws: Path) -> dict:
    path = Path(ws) / "reviews" / "SKILL_FEEDBACK.yaml"
    if not path.exists():
        raise ValueError("missing SKILL_FEEDBACK.yaml")
    gate = validate_skill_feedback(path.read_text(encoding="utf-8"))
    if not gate.ok:
        raise ValueError("invalid SKILL_FEEDBACK.yaml: " + gate.reason)
    doc = _yaml(path.read_text(encoding="utf-8"))
    store = LearningStore(Path(target) / framework_root / "knowledge" / "long-term")
    recorded, candidates = [], []
    for observation in doc.get("observations") or []:
        item = dict(observation)
        if not item.get("recurrence_key") and (
            item.get("critical_incident") or item.get("user_directive") or item.get("dogfood_failure")
        ):
            item["recurrence_key"] = f"direct-{item.get('id') or doc['change_id']}"
        item.update(change_id=doc["change_id"], verified=True)
        recorded.append(str(store.record_feedback(item)))
    recorded_docs = [_yaml(Path(path).read_text(encoding="utf-8")) for path in recorded]
    for key in sorted({item.get("recurrence_key") for item in recorded_docs if item.get("recurrence_key")}):
        try:
            candidate = store.cluster_candidate(key)
        except ValueError:
            continue
        candidate_path = Path(target) / framework_root / "knowledge" / "skill-evolution" / "candidates" / f"{candidate['candidate_id']}.yaml"
        if not candidate_path.exists():
            candidate_path.parent.mkdir(parents=True, exist_ok=True)
            candidate_path.write_text(yaml.safe_dump(candidate, sort_keys=False, allow_unicode=True), encoding="utf-8")
            _record_evolution_transition(Path(target) / framework_root, "candidates", candidate["candidate_id"])
        candidates.append(str(candidate_path))
    return {"feedback_recorded": recorded, "candidates_created": candidates}


def _record_evolution_transition(framework: Path, lane: str, candidate_id: str) -> None:
    index_path = Path(framework) / "knowledge" / "skill-evolution" / "skill-evolution-index.yaml"
    index = _yaml(index_path.read_text(encoding="utf-8")) if index_path.exists() else {"version": 1}
    for key in ("candidates", "accepted", "rejected", "monitored"):
        index.setdefault(key, [])
        if key != lane:
            index[key] = [item for item in index[key] if item != candidate_id]
    if candidate_id not in index[lane]:
        index[lane].append(candidate_id)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(yaml.safe_dump(index, sort_keys=False, allow_unicode=True), encoding="utf-8")


def _regenerate_skill_index(framework: Path) -> Path:
    skills = Path(framework) / "skills"
    entries = []
    for skill_path in sorted(skills.glob("*/SKILL.md")):
        text = skill_path.read_text(encoding="utf-8")
        match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
        if match:
            entries.append(_yaml(match.group(1)))
    path = skills / "skill-index.yaml"
    path.write_text("# TỰ ĐỘNG TẠO BỞI SKILL EVOLUTION — KHÔNG CHỈNH SỬA THỦ CÔNG\n" +
                    yaml.safe_dump({"skills": entries}, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path


def promote_skill_candidate(target: Path, framework_root: str, candidate_path: Path,
                            review: dict, promotion: dict) -> dict:
    """Apply only an independently approved, tested candidate and version it."""
    target, candidate_path = Path(target), Path(candidate_path)
    candidate = _yaml(candidate_path.read_text(encoding="utf-8"))
    gate = validate_skill_candidate(candidate_path.read_text(encoding="utf-8"))
    if not gate.ok:
        raise ValueError(gate.reason)
    if not candidate_threshold_from_document(candidate):
        raise ValueError("candidate threshold/verified evidence not met")
    evaluation = candidate.get("skill_evaluation")
    if evaluation and evaluation.get("verdict") not in {"PROMOTE", "APPROVED"}:
        raise ValueError("candidate requires successful offline skill evaluation")
    if review.get("independent") is not True or review.get("verdict") != "approved" or review.get("guardrails_preserved") is not True:
        raise ValueError("independent approved review preserving guardrails is required")
    promotion = {**promotion, "classification": candidate["classification"]}
    promote_gate = validate_skill_promotion(promotion)
    if not promote_gate.ok:
        raise ValueError(promote_gate.reason)
    after, threats = sanitize_learning_text(str(candidate["proposed_change"].get("after") or ""))
    if threats:
        raise ValueError("candidate contains poisoned instructions")
    skill_path = target / framework_root / "skills" / candidate["target_skill"] / "SKILL.md"
    before_text = skill_path.read_text(encoding="utf-8")
    old = str(candidate["proposed_change"].get("before") or "")
    if not old or old not in before_text:
        raise ValueError("candidate before fragment does not match target skill")
    new_text = before_text.replace(old, after, 1)
    new_text = re.sub(r"(?m)^version:\s*['\"]?[^'\"\n]+['\"]?\s*$",
                      f"version: '{promotion['new_version']}'", new_text, count=1)
    regression = validate_skill_regression(before_text, new_text)
    if not regression.ok:
        raise ValueError(regression.reason)
    skill_path.write_text(new_text, encoding="utf-8")
    accepted = target / framework_root / "knowledge" / "skill-evolution" / "accepted" / candidate_path.name
    accepted.parent.mkdir(parents=True, exist_ok=True)
    candidate.update(status="accepted", review=review, promotion=promotion,
                     promoted_at=_now(), target_path=str(skill_path))
    accepted.write_text(yaml.safe_dump(candidate, sort_keys=False, allow_unicode=True), encoding="utf-8")
    candidate_path.unlink()
    _record_evolution_transition(target / framework_root, "accepted", candidate["candidate_id"])
    skill_index = _regenerate_skill_index(target / framework_root)
    return {"status": "accepted", "candidate_path": str(accepted), "skill_path": str(skill_path),
            "version": promotion["new_version"], "skill_index": str(skill_index)}


def reject_skill_candidate(target: Path, framework_root: str, candidate_path: Path,
                           review: dict) -> dict:
    candidate_path = Path(candidate_path)
    candidate = _yaml(candidate_path.read_text(encoding="utf-8"))
    if review.get("independent") is not True or review.get("verdict") != "rejected":
        raise ValueError("independent rejected review required")
    rejected = Path(target) / framework_root / "knowledge" / "skill-evolution" / "rejected" / candidate_path.name
    rejected.parent.mkdir(parents=True, exist_ok=True)
    candidate.update(status="rejected", review=review, rejected_at=_now())
    rejected.write_text(yaml.safe_dump(candidate, sort_keys=False, allow_unicode=True), encoding="utf-8")
    candidate_path.unlink()
    _record_evolution_transition(Path(target) / framework_root, "rejected", candidate["candidate_id"])
    return {"status": "rejected", "candidate_path": str(rejected)}


def _find_entry(long_term: Path, entry_id: str) -> Path | None:
    for path in long_term.rglob("*.yaml"):
        if path.name == "knowledge-index.yaml":
            continue
        data = _yaml(path.read_text(encoding="utf-8"))
        if str(data.get("id")) == str(entry_id):
            return path
    return None


def regenerate_runtime_index(long_term: Path) -> Path:
    """Index project knowledge in addition to existing DNA/convention entries."""
    long_term = Path(long_term)
    index_path = long_term / "knowledge-index.yaml"
    existing = _yaml(index_path.read_text(encoding="utf-8")) if index_path.exists() else {}
    entries = [item for item in existing.get("entries") or [] if item.get("store") != "project-knowledge"]
    project = long_term / "project-knowledge"
    for path in sorted(project.glob("*.yaml")):
        item = _yaml(path.read_text(encoding="utf-8"))
        entries.append({
            "id": item.get("id"), "store": "project-knowledge",
            "path": str(path.relative_to(long_term)),
            "title": item.get("title") or item.get("statement") or item.get("id"),
            "applies_to": item.get("applies_to") or [], "status": item.get("status"),
            "freshness": item.get("freshness", "verified"),
            "confidence": item.get("confidence", "medium"),
            "type": item.get("type"), "affected_paths": item.get("affected_paths") or [],
        })
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(
        "# TỰ ĐỘNG TẠO BỞI KNOWLEDGE CONTROL PLANE — KHÔNG CHỈNH SỬA THỦ CÔNG\n" +
        yaml.safe_dump({"version": 1, "entries": entries}, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return index_path


def apply_project_learning(
    target: Path, framework_root: str, ws: Path,
    *, memory_saver: Callable[[dict], dict] | None = None,
    graph_refresher: Callable[[dict], dict] | None = None,
) -> dict:
    """Execute verified knowledge actions and return their observed results."""
    target, ws = Path(target), Path(ws)
    report = ws / "verification" / "VERIFICATION_REPORT.md"
    if not report.exists() or "VERDICT: VERIFIED" not in report.read_text(encoding="utf-8"):
        raise ValueError("project learning requires VERIFIED report")
    impact = _yaml((ws / "reviews" / "KNOWLEDGE_IMPACT.yaml").read_text(encoding="utf-8"))
    framework = target / framework_root
    long_term = framework / "knowledge" / "long-term"
    store = LearningStore(long_term)
    result = {"verified": True, "promoted": [], "superseded": [], "stale_invalidated": [],
              "memory_saved": [], "graph_refresh": {}, "degradation": []}
    change_id = ws.name
    for raw in impact.get("new_candidates") or []:
        if not isinstance(raw, dict):
            raise ValueError("durable knowledge promotion requires structured candidate")
        entry = dict(raw)
        if not entry.get("statement") or not entry.get("evidence_ids") or entry.get("confidence") not in {"medium", "high"}:
            raise ValueError("durable knowledge candidate requires statement/evidence_ids/confidence")
        entry.setdefault("id", f"PK-{change_id}-{len(result['promoted']) + 1}")
        entry.update(status="active", repository_commit=impact.get("repository_commit"),
                     provenance={"change_id": change_id,
                                 "verification": "verification/VERIFICATION_REPORT.md",
                                 "evidence_ids": entry.get("evidence_ids") or []})
        path = store.promote(entry)
        result["promoted"].append({"id": entry["id"], "path": str(path), "verified": path.exists()})
    for raw in impact.get("superseded_decisions") or []:
        item = raw if isinstance(raw, dict) else {"id": str(raw)}
        path = _find_entry(long_term, item.get("id"))
        if not path or not item.get("superseded_by"):
            raise ValueError(f"cannot supersede missing/incomplete knowledge entry: {item.get('id')}")
        data = _yaml(path.read_text(encoding="utf-8"))
        data.update(status="superseded", superseded_by=item.get("superseded_by"), superseded_at=_now())
        path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
        result["superseded"].append({"id": item.get("id"), "path": str(path), "verified": True})
    for raw in impact.get("stale_entries") or []:
        entry_id = raw.get("id") if isinstance(raw, dict) else str(raw)
        path = _find_entry(long_term, entry_id)
        if not path:
            raise ValueError(f"cannot invalidate missing knowledge entry: {entry_id}")
        data = _yaml(path.read_text(encoding="utf-8"))
        if data.get("status") != "superseded":
            data.update(status="invalidated", invalidated_at=_now())
            path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
        result["stale_invalidated"].append({"id": entry_id, "path": str(path), "verified": True})
    for item in impact.get("memory_updates") or []:
        clean = dict(item) if isinstance(item, dict) else {"lesson": str(item)}
        clean, threats = sanitize_learning_payload(clean)
        if threats:
            result["degradation"].append({"type": "poisoning-blocked", "phrases": threats})
        if memory_saver:
            observed = memory_saver(clean)
            if not observed.get("ok"):
                result["degradation"].append({"type": "agent-memory-save-failed", "result": observed})
        else:
            outbox = framework / "knowledge" / "memory-save-outbox.jsonl"
            outbox.parent.mkdir(parents=True, exist_ok=True)
            with outbox.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps({"change_id": change_id, "payload": clean, "created_at": _now()}, ensure_ascii=False) + "\n")
            observed = {"ok": False, "status": "pending-provider", "request_path": str(outbox)}
            result["degradation"].append({"type": "agent-memory-unavailable", "action": "queued"})
        result["memory_saved"].append(observed)
    if impact.get("graph_refresh_required"):
        request = framework / "knowledge" / "refresh-requests" / f"{change_id}.yaml"
        request.parent.mkdir(parents=True, exist_ok=True)
        request.write_text(yaml.safe_dump({"change_id": change_id, "providers": ["architecture_graph", "code_graph"],
                                           "status": "requested", "created_at": _now()}, sort_keys=False), encoding="utf-8")
        if graph_refresher:
            observed = graph_refresher({"change_id": change_id, "request_path": str(request)})
            result["graph_refresh"] = {"requested": True, "request_path": str(request), **observed}
            if not observed.get("verified"):
                result["degradation"].append({"type": "graph-refresh-failed", "result": observed})
        else:
            result["graph_refresh"] = {"requested": True, "request_path": str(request),
                                       "verified": False, "status": "pending-provider"}
            result["degradation"].append({"type": "graph-provider-unavailable", "action": "queued"})
    else:
        result["graph_refresh"] = {"requested": False}
    result["graph_refresh_requested"] = result["graph_refresh"]["requested"]
    index_path = regenerate_runtime_index(long_term)
    result["knowledge_index_path"] = str(index_path)
    result["knowledge_index_sha256"] = index_hash(index_path)
    result["skill_evolution"] = process_skill_feedback(target, framework_root, ws)
    return result


def index_hash(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
