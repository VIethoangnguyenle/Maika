import yaml

from cli.knowledge_control import validate_skill_candidate


def candidate():
    return {
        "version": 1, "candidate_id": "SC-1", "target_skill": "writing-plan",
        "status": "proposed", "classification": "behavioral",
        "problem": {"statement": "missed capsule", "recurrence_key": "capsule-miss", "severity": "important", "occurrences": 3},
        "evidence": {"changes": ["A", "B"], "reviews": ["A/r", "B/r"], "incidents": [], "source_anchors": [], "verified": True},
        "proposed_change": {"sections": ["Output"], "summary": "require capsule", "before": "optional", "after": "required"},
        "expected_effect": {"improvements": ["grounding"], "risks": ["tokens"], "token_impact": "small", "behavior_change": True},
        "compatibility": {"capability_ids_changed": False, "output_contract_changed": False, "runtime_consumer_changed": False, "migration_required": False},
        "validation": {"required_tests": ["test_capsule"], "dogfood_scenarios": ["two tasks"], "regression_risks": ["prompt size"]},
    }


def test_candidate_schema_is_deterministic():
    assert validate_skill_candidate(yaml.safe_dump(candidate())).ok
    bad = candidate(); del bad["validation"]
    assert not validate_skill_candidate(yaml.safe_dump(bad)).ok
