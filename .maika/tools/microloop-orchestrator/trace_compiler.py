"""Deterministic TRACE_REQUEST compiler (harness plan §7; blocker B2/B6 lineage).

The orchestrator — not the worker — compiles the trace request from
QUERY_PLAN.yaml plus the grounding skill contract, so the capability
requirements a worker must satisfy are never self-authored. Conditional
capabilities carry their trigger vocabulary from the skill contract
(capability-requirements semantics folded in per execution errata E1).
"""

from __future__ import annotations

from pathlib import Path

import yaml

FRESHNESS_REQUIREMENT = "graph_commit_current_or_scoped_stale"
SOURCE_VERIFICATION_REQUIREMENT = "material_exact_facts_source_verified"
GROUNDING_SKILL = "grounding-explorer"
# Capabilities in trace scope are the code-graph/code-index ones; memory, DB and
# runtime capabilities have their own gates (tool-health, memory-recall,
# database-context) and never enter TRACE_REQUEST.required_capabilities.
_TRACE_FRESHNESS_KEYS = {"code_graph", "code_index"}


def _skill_contract(framework_path: Path, name: str) -> dict:
    index = yaml.safe_load(
        (Path(framework_path) / "skills" / "skill-index.yaml").read_text(encoding="utf-8")
    ) or {}
    for entry in index.get("skills") or []:
        if entry.get("name") == name:
            return entry
    raise ValueError(f"skill {name!r} not found in skill-index.yaml")


def _trace_scope(framework_path: Path) -> set[str]:
    registry_path = Path(framework_path) / "profiles" / "capability-registry.yaml"
    if not registry_path.exists():
        registry_path = (Path(__file__).resolve().parents[2]
                         / "profiles" / "capability-registry.yaml")
    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
    return {
        capability
        for capability, spec in (registry.get("capabilities") or {}).items()
        if set((spec or {}).get("freshness") or []) & _TRACE_FRESHNESS_KEYS
    }


def compile_trace_request(ws: Path, framework_path: Path) -> dict:
    ws = Path(ws)
    query_plan = yaml.safe_load(
        (ws / "exploration" / "QUERY_PLAN.yaml").read_text(encoding="utf-8")
    ) or {}
    change = yaml.safe_load((ws / "CHANGE.yaml").read_text(encoding="utf-8")) or {}
    contract = _skill_contract(framework_path, GROUNDING_SKILL)
    capabilities = contract.get("capabilities") or {}
    one_of = {
        group: list(members)
        for group, members in (capabilities.get("one_of") or {}).items()
    }
    one_of_members = {member for members in one_of.values() for member in members}
    conditional = {
        capability: {"triggers": list((spec or {}).get("triggers") or [])}
        for capability, spec in (capabilities.get("conditional") or {}).items()
    }

    questions = []
    question_caps: set[str] = set()
    for q in query_plan.get("questions") or []:
        questions.append({
            "id": q.get("id"),
            "question": q.get("question"),
            "required_capabilities": list(q.get("required_capabilities") or []),
        })
        question_caps.update(q.get("required_capabilities") or [])

    # Required for THIS trace: question capabilities in trace scope that are
    # neither one_of members nor conditional (the worker cannot drop a
    # question's capability by classifying it away). Non-trace capabilities
    # (memory/DB/runtime) keep their own gates.
    trace_scope = _trace_scope(framework_path)
    required = sorted(
        (question_caps & trace_scope) - one_of_members - set(conditional)
    )

    anchors = [
        anchor
        for q in (query_plan.get("questions") or [])
        for anchor in (q.get("anchors") or [])
    ]

    return {
        "version": 1,
        "change_id": change.get("change_id") or change.get("id"),
        "questions": questions,
        "anchors": anchors,
        "required_capabilities": required,
        "one_of": one_of,
        "conditional": conditional,
        "freshness_requirement": FRESHNESS_REQUIREMENT,
        "source_verification_requirement": SOURCE_VERIFICATION_REQUIREMENT,
    }


def compile_database_request(ws: Path) -> dict:
    """Skeleton DATABASE_REQUEST from the QUERY_PLAN's DB questions (plan §7).

    environment/database stay empty on purpose: the worker must declare them
    explicitly and the database-request gate rejects empty values (mutation #8
    — DB evidence must be environment-bound, never assumed)."""
    ws = Path(ws)
    query_plan = yaml.safe_load(
        (ws / "exploration" / "QUERY_PLAN.yaml").read_text(encoding="utf-8")
    ) or {}
    change = yaml.safe_load((ws / "CHANGE.yaml").read_text(encoding="utf-8")) or {}
    db_capabilities = {"database_schema_inspection", "database_dependency_analysis"}
    questions = []
    required = set()
    for q in query_plan.get("questions") or []:
        caps = set(q.get("required_capabilities") or []) & db_capabilities
        if caps:
            questions.append({"id": q.get("id"), "question": q.get("question"),
                              "required_capabilities": sorted(caps)})
            required |= caps
    return {
        "version": 1,
        "change_id": change.get("change_id") or change.get("id"),
        "environment": None,
        "database": None,
        "questions": questions,
        "objects": [],
        "required_capabilities": sorted(required or {"database_schema_inspection"}),
        "allowed_lane": "exploration",
        "data_probe_required": False,
        "source_anchors": [],
        "migration_refs": [],
    }


def write_database_request(ws: Path) -> Path:
    path = Path(ws) / "exploration" / "DATABASE_REQUEST.yaml"
    if path.exists():  # never clobber a worker-completed request
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(compile_database_request(ws), sort_keys=False,
                       allow_unicode=True),
        encoding="utf-8",
    )
    return path


def write_trace_request(ws: Path, framework_path: Path) -> Path:
    request = compile_trace_request(ws, framework_path)
    path = Path(ws) / "exploration" / "TRACE_REQUEST.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(request, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
    return path
