from cli.knowledge_control import validate_skill_regression


def test_skill_change_cannot_weaken_control_plane_invariants():
    baseline = "current source authority evidence verification write gate knowledge-native capability IDs"
    assert validate_skill_regression(baseline, baseline + " capsule").ok
    assert not validate_skill_regression(baseline, "helpful implementation instructions").ok

