from cli.knowledge_control import candidate_triggered


def test_recurrence_threshold_requires_three_occurrences_two_changes():
    assert candidate_triggered([
        {"recurrence_key": "x", "change_id": "A", "verified": True},
        {"recurrence_key": "x", "change_id": "A", "verified": True},
        {"recurrence_key": "x", "change_id": "B", "verified": True},
    ])
    assert not candidate_triggered([
        {"recurrence_key": "x", "change_id": "A", "verified": True},
        {"recurrence_key": "x", "change_id": "B", "verified": True},
    ])


def test_explicit_safe_triggers_and_unverified_feedback_rules():
    assert candidate_triggered([{"critical_incident": True, "verified": True}])
    assert candidate_triggered([{"user_directive": True, "verified": True}])
    assert candidate_triggered([{"dogfood_failure": True, "reproducible": True, "verified": True}])
    assert not candidate_triggered([{"critical_incident": True, "verified": False}])

