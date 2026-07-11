"""Workflow router — machine-readable route authority (PR 3, plan §8 + A1/A2/A3)."""

import copy
from pathlib import Path

import pytest

from cli.agent_content.router import load_router, resolve_route, validate_router

REPO = Path(__file__).resolve().parents[2]
FRAMEWORK = REPO / ".maika"


@pytest.fixture(scope="module")
def router():
    return load_router(FRAMEWORK)


def test_in_tree_router_is_valid(router):
    assert validate_router(router, FRAMEWORK) == []


def test_every_class_reaches_completed(router):
    # Validator already walks the graph; assert the walk is part of validation
    # by breaking trivial's path and expecting an error.
    broken = copy.deepcopy(router)
    del broken["actions"]["verify"]
    errors = validate_router(broken, FRAMEWORK)
    assert any("COMPLETED" in err for err in errors)


def test_trivial_apply_resolves_lightweight_and_exits_to_verifying(router):
    route = resolve_route(router, "apply", "trivial", "INTAKE")
    assert route["allowed"]
    assert route["skill"] == "lightweight-change"
    assert route["next_state"] == "VERIFYING"  # A1: no REVIEWING dead-end
    follow = resolve_route(router, "verify", "trivial", route["next_state"])
    assert follow["allowed"]
    assert follow["next_state"] == "COMPLETED"


def test_standard_apply_routes_to_final_review_then_verify(router):
    route = resolve_route(router, "apply", "standard", "EXECUTING")
    assert route["allowed"]
    assert route["skill"] == "executing-task"
    assert route["next_state"] == "FINAL_REVIEW"
    final = resolve_route(router, "final-review", "standard", "FINAL_REVIEW")
    assert final["allowed"]
    assert final["skill"] == "reviewing-change"  # A3: reviewing-change is routed
    assert final["next_state"] == "VERIFYING"


def test_validate_spec_bridges_spec_review_to_planning(router):
    route = resolve_route(router, "validate-spec", "standard", "SPEC_REVIEW")
    assert route["allowed"]
    assert route["next_state"] == "PLANNING"  # A2: no SPEC_REVIEW gap


def test_trivial_never_routes_spec_or_plan(router):
    for action in ("explore", "reconcile", "brainstorm", "spec", "validate-spec",
                   "plan", "validate-plan", "final-review"):
        route = resolve_route(router, action, "trivial", "INTAKE")
        assert not route["allowed"], f"trivial must not route {action}"


def test_unknown_state_rejected(router):
    broken = copy.deepcopy(router)
    broken["actions"]["apply"]["allowed_from"] = ["REVIEWING"]  # SSOT phantom state
    errors = validate_router(broken, FRAMEWORK)
    assert any("REVIEWING" in err for err in errors)


def test_unknown_skill_rejected(router):
    broken = copy.deepcopy(router)
    broken["actions"]["spec"]["skill"] = "ghost-skill"
    errors = validate_router(broken, FRAMEWORK)
    assert any("ghost-skill" in err for err in errors)


def test_unknown_gate_rejected(router):
    broken = copy.deepcopy(router)
    broken["actions"]["verify"]["completion_gates"] = ["ghost-gate"]
    errors = validate_router(broken, FRAMEWORK)
    assert any("ghost-gate" in err for err in errors)


def test_produced_artifacts_must_have_authority(router):
    broken = copy.deepcopy(router)
    broken["actions"]["spec"]["produces"] = ["GHOST_ARTIFACT.md"]
    errors = validate_router(broken, FRAMEWORK)
    assert any("GHOST_ARTIFACT" in err for err in errors)


def test_worker_actions_declare_context_route(router):
    broken = copy.deepcopy(router)
    broken["actions"]["explore"].pop("context_route", None)
    errors = validate_router(broken, FRAMEWORK)
    assert any("context_route" in err for err in errors)


def test_failure_routes_use_real_block_reasons(router):
    broken = copy.deepcopy(router)
    broken["actions"]["explore"]["failure_routes"]["missing_context"]["reason"] = "vibes"
    errors = validate_router(broken, FRAMEWORK)
    assert any("vibes" in err for err in errors)


def test_cli_validate_router_on_repo(capsys):
    from cli.commands.content import run_content
    assert run_content("validate-router", target_dir=str(REPO)) == 0
    assert "workflow router valid" in capsys.readouterr().out


def test_task_route_dry_run(tmp_path, maika_root, capsys):
    import importlib.util
    from cli.commands.init import run_init
    from cli.commands.task import run_task

    target = tmp_path / "proj"
    run_init(str(target), str(maika_root), "generic", [], "python", assume_yes=True)
    spec = importlib.util.spec_from_file_location(
        "vs_route_test",
        target / ".maika" / "tools" / "microloop-orchestrator" / "vnext_state.py",
    )
    vs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(vs)
    vs.init_workspace(target / ".maika" / "changes", "C-1", "trivial", "rename x")

    assert run_task("route", target_dir=str(target), change_id="C-1", action_arg="apply") == 0
    out = capsys.readouterr().out
    assert "selected_skill:" in out
    assert "next_state: VERIFYING" in out

    assert run_task("route", target_dir=str(target), change_id="C-1", action_arg="spec") == 0
    out = capsys.readouterr().out
    assert "allowed: false" in out


def test_fixed_flow_rule_is_dead():
    rules_flow = (FRAMEWORK / "rules" / "rules-flow.md").read_text(encoding="utf-8")
    assert "Chuỗi state cố định" not in rules_flow
    assert "workflow-router.yaml" in rules_flow
