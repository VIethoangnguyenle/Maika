from cli.knowledge_control import validate_skill_promotion


def test_behavioral_promotion_requires_review_tests_dogfood_and_version_bump():
    record = {
        "classification": "behavioral", "old_version": "2.0", "new_version": "2.1",
        "independent_review": "approved", "tests_passed": True, "dogfood_passed": True,
        "human_approval": False,
    }
    assert validate_skill_promotion(record).ok
    assert not validate_skill_promotion({**record, "new_version": "2.0"}).ok


def test_contractual_promotion_requires_human_approval():
    record = {
        "classification": "contractual", "old_version": "2.0", "new_version": "3.0",
        "independent_review": "approved", "tests_passed": True, "dogfood_passed": True,
        "human_approval": False,
    }
    assert not validate_skill_promotion(record).ok
    assert validate_skill_promotion({**record, "human_approval": True}).ok

