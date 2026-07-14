from cli.knowledge_control import validate_skill_evaluation, validate_skill_promotion


def test_pending_or_empty_evaluation_cannot_promote():
    assert not validate_skill_evaluation({
        "evaluation_tasks": [], "before_metrics": {}, "after_metrics": {}, "verdict": "PENDING",
    }).ok
    assert not validate_skill_evaluation({
        "evaluation_tasks": ["A", "B"], "before_metrics": {"retry": 1},
        "after_metrics": {"retry": 1}, "verdict": "PROMOTE",
    }).ok
    assert validate_skill_evaluation({
        "evaluation_tasks": ["A", "B"], "before_metrics": {"retry": 2},
        "after_metrics": {"retry": 0}, "verdict": "PROMOTE",
    }).ok


def test_behavioral_promotion_requires_nonempty_successful_canary():
    base = {
        "classification": "behavioral", "old_version": "1.0", "new_version": "1.1",
        "independent_review": "approved", "tests_passed": True, "dogfood_passed": True,
        "human_approval": False,
    }
    assert not validate_skill_promotion({**base, "canary_passed": True, "canary_results": []}).ok
    assert not validate_skill_promotion({
        **base, "canary_passed": False, "canary_results": [{"passed": False}],
    }).ok
    assert validate_skill_promotion({
        **base, "canary_passed": True, "canary_results": [{"passed": True}],
    }).ok
