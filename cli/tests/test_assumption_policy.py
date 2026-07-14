"""Assumption taxonomy — policy-driven gate enforcement (PR 11, plan §16)."""

import importlib.util
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
FRAMEWORK = REPO / ".maika"
SPEC = importlib.util.spec_from_file_location(
    "gates_assumptions", FRAMEWORK / "tools" / "gate-check" / "gates.py"
)
GATES = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GATES)

BLOCKING_TYPES = ("behavior_changing", "public_contract", "persistence_destructive",
                  "security", "migration")


def _trace(assumptions, confidence="medium"):
    return yaml.safe_dump({"decision": {
        "id": "DEC-1", "statement": "Do the thing.", "type": "architecture",
        "knowledge_questions": ["q"], "evidence_ids": ["EV-1"],
        "authority": "current source", "conflicts": [], "assumptions": assumptions,
        "confidence": confidence, "freshness": "fresh", "verdict": "accepted",
    }})


def _record(atype, **extra):
    base = {"id": "AS-1", "type": atype, "statement": "x is absent",
            "evidence_gap": "no row in DB", "expiry_condition": "backfill lands"}
    base.update(extra)
    return base


def test_policy_file_covers_all_ssot_types():
    doc = yaml.safe_load(
        (FRAMEWORK / "config" / "assumption-policy.yaml").read_text(encoding="utf-8")
    )
    assert set(doc["types"]) == {"non_material", "operational_environment",
                                 "behavior_changing", "public_contract",
                                 "persistence_destructive", "security", "migration"}


def test_untyped_assumption_rejected():
    result = GATES.validate_knowledge_trace(_trace(["freeform string assumption"]))
    assert not result.ok
    assert "typed record" in result.reason


def test_unknown_type_rejected():
    result = GATES.validate_knowledge_trace(_trace([_record("vibes")]))
    assert not result.ok
    assert "unknown assumption type" in result.reason


def test_non_material_continues_but_caps_confidence():
    assert GATES.validate_knowledge_trace(_trace([_record("non_material")])).ok
    capped = GATES.validate_knowledge_trace(_trace([_record("non_material")], confidence="high"))
    assert not capped.ok
    assert "caps decision confidence" in capped.reason


def test_operational_environment_requires_degradation_fields():
    missing = GATES.validate_knowledge_trace(_trace([_record("operational_environment")]))
    assert not missing.ok
    assert "failed_probe" in missing.reason
    ok = GATES.validate_knowledge_trace(_trace([_record(
        "operational_environment", failed_probe="cbm probe timeout",
        fallback="current-source grep", affected_claims=["dependency blast radius"],
    )]))
    assert ok.ok


def test_risky_types_block_until_human_decision():
    for atype in BLOCKING_TYPES:
        extra = {}
        if atype == "migration":
            extra["rollback"] = "restore from snapshot"
        if atype == "persistence_destructive":
            extra["database_evidence"] = "DATABASE_CONTEXT.yaml#tbl"
        blocked = GATES.validate_knowledge_trace(_trace([_record(atype, **extra)]))
        assert not blocked.ok, atype
        assert "human" in blocked.reason
        approved = GATES.validate_knowledge_trace(
            _trace([_record(atype, human_decision="approved", **extra)])
        )
        assert approved.ok, (atype, approved.reason)


def test_migration_requires_rollback():
    result = GATES.validate_knowledge_trace(
        _trace([_record("migration", human_decision="approved")])
    )
    assert not result.ok
    assert "rollback" in result.reason
