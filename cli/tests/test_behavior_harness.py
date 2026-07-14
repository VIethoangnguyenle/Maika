"""Static behavior harness — fixtures A–J (PR 14, plan §20)."""

from pathlib import Path

from cli.agent_content.router import load_router
from cli.behavior.harness import _run_route_walk, load_suite, run_suite

REPO = Path(__file__).resolve().parents[2]
FRAMEWORK = REPO / ".maika"


def test_suite_covers_fixtures_a_through_j():
    suite = load_suite(FRAMEWORK)
    ids = [fixture["id"][0] for fixture in suite["fixtures"]]
    assert ids == list("ABCDEFGHIJ")


def test_all_static_fixtures_pass():
    report = run_suite(FRAMEWORK)
    failing = [f"{f['fixture_id']}: {f['violations']}"
               for f in report["fixtures"] if f["verdict"] != "PASS"]
    assert report["verdict"] == "PASS", "\n".join(failing)


def test_trace_records_required_fields():
    report = run_suite(FRAMEWORK)
    for fixture in report["fixtures"]:
        assert fixture["fixture_id"]
        assert fixture["framework_commit"]
        assert fixture["verdict"] in ("PASS", "FAIL")
        assert isinstance(fixture["violations"], list)
        assert fixture["checks"], fixture["fixture_id"]


def test_route_walk_detects_forbidden_skill_and_state_drift():
    router = load_router(FRAMEWORK)
    check = {
        "class": "trivial",
        "route": ["start", "apply", "verify"],
        "skills_invoked": ["intent-analysis", "verification-before-completion"],
        "forbidden_skills": ["lightweight-change"],  # trivial apply DOES route it
        "required_artifacts": ["SPEC.md"],           # trivial never produces it
        "forbidden_artifacts": ["RESULT.yaml"],      # trivial DOES produce it
        "expected_final_state": "ARCHIVED",          # route ends at COMPLETED
    }
    violations, trace = _run_route_walk(check, router)
    joined = "\n".join(violations)
    assert "forbidden lightweight-change" in joined
    assert "required SPEC.md" in joined
    assert "forbidden RESULT.yaml" in joined
    assert "ends at COMPLETED" in joined
    assert trace["final_state"] == "COMPLETED"


def test_route_walk_detects_illegal_route_order():
    router = load_router(FRAMEWORK)
    check = {
        "class": "standard",
        "route": ["start", "plan"],  # PLANNING chưa đạt được từ INTAKE
        "skills_invoked": [],
        "expected_final_state": "PLAN_REVIEW",
    }
    violations, _trace = _run_route_walk(check, router)
    assert any("not allowed" in violation for violation in violations)


def test_cli_behavior_static(capsys):
    from cli.commands.content import run_content

    assert run_content("behavior-static", target_dir=str(REPO)) == 0
    out = capsys.readouterr().out
    assert "behavior-static verdict: PASS" in out
    assert "A-trivial-rename" in out
