import sys
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import adaptive_runtime as ar
import vnext_state as vs


def test_classifier_is_deterministic_and_risk_floors_are_enforced():
    low = {"estimated_files": 1, "affected_modules": 1, "unknown_count": 0}
    assert ar.classify_risk(low) == ar.classify_risk(dict(reversed(list(low.items()))))
    assert ar.classify_risk(low)["classification"]["proposed_class"] == "trivial"
    assert ar.classify_risk({**low, "estimated_files": 2})["classification"]["proposed_class"] == "small"
    for signal in ("public_contract_changed", "database_changed", "event_contract_changed",
                   "transaction_changed", "concurrency_changed"):
        result = ar.classify_risk({**low, signal: True})
        assert result["classification"]["proposed_class"] == "standard"
        assert signal in result["classification"]["evidence"]
    for signal in ("security_changed", "migration_required", "infrastructure_changed",
                   "cross_service_architecture"):
        assert ar.classify_risk({**low, signal: True})["classification"]["proposed_class"] == "architectural"


def test_classifier_never_downgrades_confirmed_class():
    result = ar.classify_risk(
        {"estimated_files": 1, "affected_modules": 1, "unknown_count": 0},
        current_class="standard",
    )
    assert result["classification"]["proposed_class"] == "standard"
    assert "monotonic_class_floor:standard" in result["classification"]["evidence"]


def test_class_specific_workspace_artifacts(tmp_path):
    trivial = vs.init_workspace(tmp_path, "docs", "trivial", "Docs")
    assert (trivial / "TASK.yaml").exists()
    assert not (trivial / "SPEC.md").exists()
    assert not (trivial / "RECONCILIATION.md").exists()
    assert not (trivial / "exploration").exists()

    small = vs.init_workspace(tmp_path, "small", "small", "Small")
    assert {path.name for path in small.iterdir() if path.is_file()} >= {
        "CHANGE.yaml", "STATE.yaml", "TASK.yaml", "EVIDENCE.yaml", "RESULT.yaml",
    }
    assert not (small / "SPEC.md").exists()
    assert not (small / "IMPLEMENTATION_PLAN.md").exists()

    standard = vs.init_workspace(tmp_path, "standard", "standard", "Standard")
    assert (standard / "INTENT.md").exists()
    assert (standard / "RECONCILIATION.md").exists()
    assert (standard / "exploration" / "EVIDENCE_MANIFEST.yaml").exists()

    for ws in (trivial, small, standard):
        change = yaml.safe_load((ws / "CHANGE.yaml").read_text(encoding="utf-8"))
        assert change["version"] == 1


def test_escalation_blocks_fast_path_and_invalidates_lightweight_gate():
    result = ar.evaluate_escalation(
        "small",
        {"expected_files": ["src/a.py"], "unknown_threshold": 1},
        {"touched_files": ["src/a.py", "src/b.py"], "public_contract_changed": True},
    )
    assert result["blocked"] is True
    assert result["target_class"] == "standard"
    assert set(result["triggers"]) >= {"outside_expected_scope", "public_contract_changed"}
    assert result["lightweight_artifacts_valid"] is False


def test_worker_budget_warns_then_blocks_without_dropping_invariants():
    budget = ar.BudgetTracker("small")
    assert budget.record_worker_call()["status"] == "ok"
    assert budget.record_worker_call()["status"] == "warning"
    with pytest.raises(ar.BudgetExceeded, match="small worker-call budget"):
        budget.record_worker_call()


def test_small_happy_path_uses_one_worker_call(tmp_path):
    ws = vs.init_workspace(tmp_path, "small-run", "small", "Small run")
    task = yaml.safe_load((ws / "TASK.yaml").read_text(encoding="utf-8"))
    task["scope"]["files"]["modify"] = ["src/a.py"]
    (ws / "TASK.yaml").write_text(yaml.safe_dump(task), encoding="utf-8")
    evidence = yaml.safe_load((ws / "EVIDENCE.yaml").read_text(encoding="utf-8"))
    evidence["items"] = [{"id": "CODE-1", "statement": "a.py exists"}]
    (ws / "EVIDENCE.yaml").write_text(yaml.safe_dump(evidence), encoding="utf-8")
    calls = []
    def runner(prompt):
        calls.append(prompt)
        (ws / "RESULT.yaml").write_text(yaml.safe_dump({
            "version": 1, "status": "success", "touched_files": ["src/a.py"],
            "observed_risk_signals": {},
        }), encoding="utf-8")
        return 0, "ok"

    result = ar.execute_lightweight(ws, runner)

    assert result["status"] == "done"
    assert result["runtime_metrics"]["worker_calls"] == 1
    assert len(calls) == 1
