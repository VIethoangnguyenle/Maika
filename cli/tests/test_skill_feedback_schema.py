import yaml

from cli.knowledge_control import validate_skill_feedback


def test_skill_feedback_requires_verified_change_and_observation_evidence():
    valid = yaml.safe_dump({
        "version": 1, "change_id": "A", "verified": True,
        "observations": [{
            "id": "OBS-1", "skill": "writing-plan", "category": "behavioral",
            "severity": "important", "statement": "missed capsule",
            "evidence": ["reviews/TASK-1.md"], "recurrence_key": "capsule-miss",
            "recommendation": "require capsule",
        }],
    })
    assert validate_skill_feedback(valid).ok
    assert not validate_skill_feedback(valid.replace("verified: true", "verified: false")).ok

