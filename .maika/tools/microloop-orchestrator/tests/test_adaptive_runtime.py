import sys
import subprocess
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import adaptive_runtime as ar
import vnext_state as vs


def _git_repo(root: Path):
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
    (root / "seed.txt").write_text("seed\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "seed"], cwd=root, check=True)


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


@pytest.mark.parametrize(("klass", "expected"), [
    ("trivial", {"spec_loop": "skipped", "plan_loop": "skipped", "plan_mode": "none", "audit_spec": False, "audit_plan": False, "human_gate": False}),
    ("small", {"spec_loop": "skipped", "plan_loop": "micro", "plan_mode": "none", "audit_spec": False, "audit_plan": False, "human_gate": False}),
    ("standard", {"spec_loop": "conditional", "plan_loop": "compact", "plan_mode": "fast", "audit_spec": False, "audit_plan": False, "human_gate": False}),
    ("architectural", {"spec_loop": "required", "plan_loop": "full", "plan_mode": "deep", "audit_spec": True, "audit_plan": True, "human_gate": True}),
])
def test_workflow_requirements_follow_task_class(klass, expected):
    workflow = ar.classify_workflow_requirements(klass)
    assert workflow["dev_loop"] == "required"
    assert workflow["execution_contract"] == "required"
    for key, value in expected.items():
        assert workflow[key] == value


def test_ambiguity_enables_spec_without_forcing_full_plan():
    workflow = ar.classify_workflow_requirements("small", ambiguity=True)
    assert workflow["spec_loop"] == "required"
    assert workflow["plan_loop"] == "micro"
    assert workflow["plan_mode"] == "none"


def test_workspace_persists_consumable_workflow_contract(tmp_path):
    ws = vs.init_workspace(tmp_path, "small", "small", "Small")
    task = yaml.safe_load((ws / "TASK.yaml").read_text(encoding="utf-8"))
    assert task["workflow"] == ar.classify_workflow_requirements("small")
    change = yaml.safe_load((ws / "CHANGE.yaml").read_text(encoding="utf-8"))
    assert change["workflow"] == ar.classify_workflow_requirements("small")


@pytest.mark.parametrize(("path", "expected", "signal"), [
    ("docs/guide.md", "trivial", None),
    ("src/service.py", "small", "application_code_changed"),
    ("src/api/controller.py", "standard", "public_contract_changed"),
    ("db/migrations/001.sql", "architectural", "migration_required"),
    ("src/security/auth.py", "architectural", "security_changed"),
])
def test_repo_derived_risk_classification(tmp_path, path, expected, signal):
    target = tmp_path / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("content\n", encoding="utf-8")
    task = {"scope": {"files": {"modify": [path]}}}
    signals = ar.derive_risk_signals(task, tmp_path)
    result = ar.classify_risk(signals)["classification"]["proposed_class"]
    assert result == expected
    if signal:
        assert signals[signal] is True


def test_repo_derived_module_count_uses_gradle_registry(tmp_path):
    (tmp_path / "settings.gradle").write_text("include ':service-a', ':service-b'\n", encoding="utf-8")
    for path in ("service-a/src/a.py", "service-b/src/b.py"):
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("x\n", encoding="utf-8")
    signals = ar.derive_risk_signals({
        "scope": {"files": {"modify": ["service-a/src/a.py", "service-b/src/b.py"]}}
    }, tmp_path)
    assert signals["affected_modules"] == 2
    assert signals["affected_module_names"] == ["service-a", "service-b"]


def test_repo_risk_rules_can_be_overridden(tmp_path):
    target = tmp_path / "contracts" / "internal.txt"
    target.parent.mkdir()
    target.write_text("x\n", encoding="utf-8")
    signals = ar.derive_risk_signals(
        {"scope": {"files": {"modify": ["contracts/internal.txt"]}}},
        tmp_path,
        rules={"public_contract": ["contracts/**"]},
    )
    assert signals["public_contract_changed"] is True


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


def test_runtime_policy_merges_project_budget_override():
    policy = ar.RuntimePolicy.from_config({
        "token_budget": {"small": {"max_worker_calls": 7, "max_evidence_items": 2}},
        "worker_timeout_seconds": 12, "max_retries": 4,
    })
    assert policy.token_budget["small"]["max_worker_calls"] == 7
    assert policy.token_budget["small"]["max_context_tokens"] == 20000
    assert policy.worker_timeout_seconds == 12
    assert policy.max_retries == 4


def test_evidence_budget_is_deterministic_and_required_items_survive():
    items = [
        {"id": "B", "authority": "small"},
        {"id": "REQ", "authority": "trivial", "required": True},
        {"id": "A", "authority": "architectural"},
    ]
    selected, metrics = ar.select_evidence(items, 2)
    assert [item["id"] for item in selected] == ["REQ", "A"]
    assert metrics == {"evidence_selected": 2, "evidence_omitted": 1}
    with pytest.raises(ar.BudgetExceeded, match="required evidence"):
        ar.select_evidence([{**item, "required": True} for item in items], 2)


def test_context_budget_blocks_before_worker_and_records_estimate(tmp_path):
    ws = vs.init_workspace(tmp_path, "small-budget", "small", "Small")
    task = yaml.safe_load((ws / "TASK.yaml").read_text(encoding="utf-8"))
    task["scope"]["files"]["modify"] = ["src/a.py"]
    (ws / "TASK.yaml").write_text(yaml.safe_dump(task), encoding="utf-8")
    evidence = yaml.safe_load((ws / "EVIDENCE.yaml").read_text(encoding="utf-8"))
    evidence["items"] = [{"id": "E-1", "statement": "required context"}]
    (ws / "EVIDENCE.yaml").write_text(yaml.safe_dump(evidence), encoding="utf-8")
    called = []
    policy = ar.RuntimePolicy.from_config({
        "token_budget": {"small": {"max_context_tokens": 1}},
    })
    result = ar.execute_lightweight(ws, lambda prompt: called.append(prompt), policy=policy)
    assert result["status"] == "blocked"
    assert "context budget exceeded" in result["reason"]
    assert called == []
    assert result["runtime_metrics"]["estimated_tokens"] > 1
    assert result["runtime_metrics"]["total_tokens"] == "unavailable"


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


def test_lightweight_contract_hashes_scope_and_detects_actual_scope_escape(tmp_path):
    _git_repo(tmp_path)
    ws = vs.init_workspace(tmp_path / ".maika" / "changes", "small", "small", "Small")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("old\n", encoding="utf-8")
    (tmp_path / "src" / "b.py").write_text("old\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "workspace"], cwd=tmp_path, check=True)
    task = yaml.safe_load((ws / "TASK.yaml").read_text(encoding="utf-8"))
    task["scope"]["files"]["modify"] = ["src/a.py"]
    (ws / "TASK.yaml").write_text(yaml.safe_dump(task), encoding="utf-8")

    contract = ar.build_lightweight_execution_contract(
        ws, tmp_path, task, vs.load_state(ws), ar.RuntimeOwner(pid=7, host="test", lease_seconds=60)
    )
    assert contract["status"] == "active"
    assert contract["task_hash"].startswith("sha256:")
    assert contract["scope"]["modify"] == ["src/a.py"]
    (tmp_path / "src" / "a.py").write_text("allowed\n", encoding="utf-8")
    (tmp_path / "src" / "b.py").write_text("escaped\n", encoding="utf-8")

    observed = ar.inspect_lightweight_changes(tmp_path, contract)
    assert observed["allowed"] == ["src/a.py"]
    assert observed["outside_scope"] == ["src/b.py"]


def test_lightweight_contract_rejects_empty_scope(tmp_path):
    _git_repo(tmp_path)
    ws = vs.init_workspace(tmp_path / ".maika" / "changes", "small", "small", "Small")
    task = yaml.safe_load((ws / "TASK.yaml").read_text(encoding="utf-8"))
    with pytest.raises(ValueError, match="non-empty declared scope"):
        ar.build_lightweight_execution_contract(ws, tmp_path, task, vs.load_state(ws))


def test_lightweight_contract_rejects_scope_path_escape(tmp_path):
    _git_repo(tmp_path)
    ws = vs.init_workspace(tmp_path / ".maika" / "changes", "small", "small", "Small")
    task = yaml.safe_load((ws / "TASK.yaml").read_text(encoding="utf-8"))
    task["scope"]["files"]["modify"] = ["../outside.py"]
    (ws / "TASK.yaml").write_text(yaml.safe_dump(task), encoding="utf-8")
    with pytest.raises(ValueError, match="repo-relative POSIX"):
        ar.build_lightweight_execution_contract(ws, tmp_path, task, vs.load_state(ws))
