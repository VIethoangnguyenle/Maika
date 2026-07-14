"""Structural guards for the ADR-001/ADR-002 executable contract fixtures.

These tests validate architecture artifacts only. They intentionally do not
change or assert the current runtime implementation.
"""

from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "docs" / "architecture" / "control-plane" / "fixtures"


def _load(name: str) -> dict:
    doc = yaml.safe_load((FIXTURES / name).read_text(encoding="utf-8"))
    assert isinstance(doc, dict)
    assert doc.get("schema_version") == 1
    return doc


def _cases(name: str) -> list[dict]:
    cases = _load(name).get("cases")
    assert isinstance(cases, list) and cases
    ids = [case.get("id") for case in cases]
    assert all(isinstance(case_id, str) and case_id for case_id in ids)
    assert len(ids) == len(set(ids))
    return cases


def test_contract_enums_and_transition_targets_are_closed():
    contract = _load("state-contract.yaml")

    for section in (contract["run"]["lifecycle"], contract["run"]["phase"], contract["worker"]):
        states = set(section["states"])
        assert set(section["transitions"]) == states
        assert all(set(targets) <= states for targets in section["transitions"].values())

    lifecycle = contract["run"]["lifecycle"]
    assert all(lifecycle["transitions"][state] == [] for state in lifecycle["terminal"])
    worker = contract["worker"]
    assert all(worker["transitions"][state] == [] for state in worker["terminal"])


def test_run_transition_cases_match_machine_readable_contract():
    contract = _load("state-contract.yaml")
    lifecycle = contract["run"]["lifecycle"]
    phase = contract["run"]["phase"]
    combinations = contract["run"]["valid_combinations"]

    for case in _cases("run-transition-cases.yaml"):
        expected = case["expected"]
        state = expected.get("state")
        if state:
            assert state["lifecycle"] in lifecycle["states"], case["id"]
            assert state["current_phase"] in phase["states"], case["id"]
            assert state["current_phase"] in combinations[state["lifecycle"]], case["id"]
            assert isinstance(state["aggregate_version"], int), case["id"]

        before = case.get("input", {}).get("state")
        operation = case.get("input", {}).get("operation", {})
        if not before or operation.get("type") not in {"change_lifecycle", "change_phase"}:
            continue
        target = operation["target"]
        if target == before.get("lifecycle") or target == before.get("current_phase"):
            assert expected.get("noop") is True
            assert expected["state"]["aggregate_version"] == before["aggregate_version"]
            continue
        if operation["type"] == "change_lifecycle":
            graph_accepts = target in lifecycle["transitions"][before["lifecycle"]]
        else:
            graph_accepts = (
                before["lifecycle"] == "ACTIVE"
                and target in phase["transitions"][before["current_phase"]]
            )
        assert expected["accepted"] is graph_accepts, case["id"]
        increment = 1 if graph_accepts else 0
        assert expected["state"]["aggregate_version"] == before["aggregate_version"] + increment


def test_worker_transition_cases_match_machine_readable_contract():
    worker = _load("state-contract.yaml")["worker"]

    for case in _cases("worker-transition-cases.yaml"):
        if "previous" in case["input"]:
            assert case["input"]["previous"]["worker_execution_id"] != case["input"]["new"]["worker_execution_id"]
            assert case["input"]["new"]["attempt"] == case["input"]["previous"]["attempt"] + 1
            continue
        before = case["input"]["state"]
        target = case["input"]["target"]
        expected = case["expected"]
        assert before in worker["states"] and target in worker["states"]
        if before == target:
            assert expected.get("noop") is True
            continue
        graph_accepts = target in worker["transitions"][before]
        assert expected["accepted"] is graph_accepts, case["id"]


def test_aggregation_cases_use_contract_states_and_ordered_outcomes():
    contract = _load("state-contract.yaml")
    run_states = set(contract["run"]["lifecycle"]["states"])
    worker_states = set(contract["worker"]["states"])
    outcomes = set(contract["aggregation"]["precedence"])

    cases = _cases("run-aggregation-cases.yaml")
    assert any(len(case["input"].get("workers", [])) > 1 for case in cases)
    assert any(case["expected"].get("error") for case in cases)
    for case in cases:
        assert case["input"]["run"]["lifecycle"] in run_states, case["id"]
        assert all(worker["state"] in worker_states for worker in case["input"].get("workers", [])), case["id"]
        expected = case["expected"]
        if "lifecycle" in expected:
            assert expected["lifecycle"] in run_states, case["id"]
        else:
            assert "ERROR" in outcomes
            assert expected["error"] == contract["aggregation"]["error"]


@pytest.mark.parametrize(
    "name",
    [
        "run-transition-cases.yaml",
        "worker-transition-cases.yaml",
        "run-aggregation-cases.yaml",
        "legacy-state-projection-cases.yaml",
    ],
)
def test_fixture_case_ids_are_globally_namespaced_by_suite(name):
    # Loading through _cases also checks non-empty, unique IDs within a suite.
    assert _cases(name)


def test_legacy_projection_is_total_for_non_cancelled_current_states():
    current_states = {
        "INTAKE", "EXPLORING", "RECONCILING", "BRAINSTORMING", "SPEC_REVIEW",
        "PLANNING", "PLAN_REVIEW", "EXECUTING", "VERIFYING", "FINAL_REVIEW",
        "COMPLETED", "ARCHIVED", "BLOCKED", "CANCELLED",
    }
    cases = _cases("legacy-state-projection-cases.yaml")
    covered = {case["input"]["state"] for case in cases}
    assert covered == current_states
    cancelled = next(case for case in cases if case["input"]["state"] == "CANCELLED")
    assert cancelled["expected"]["error"] == "INCOMPLETE_EVENT_STREAM"
