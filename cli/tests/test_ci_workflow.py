"""Static guards for GitHub Actions workflow portability."""

from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CI = REPO_ROOT / ".github" / "workflows" / "ci.yml"


def test_ci_workflow_forces_utf8_python_output():
    workflow = yaml.safe_load(CI.read_text(encoding="utf-8"))
    assert workflow["env"]["PYTHONIOENCODING"] == "utf-8"


def test_install_e2e_asserts_canonical_write_gate_contract():
    """The Windows install E2E must assert the canonical host-hook contract in
    the rendered settings.json — the `maika hook write-gate` command carrying id
    `maika.write-gate.v1` — not the legacy hard-coded `write_gate.py` evaluator
    filename (F1). The rendered settings no longer contain that filename, so the
    old assertion always throws on Windows."""
    text = CI.read_text(encoding="utf-8")
    assert "maika hook write-gate" in text
    # id assertion appears as an escaped PowerShell regex (literal dots).
    assert r"maika\.write-gate\.v1" in text
    assert "--platform claude-code" in text
    # The stale filename-based assertion must not gate the E2E anymore.
    assert "write_gate.py" not in text


def test_ci_runs_on_stabilization_branch():
    """During master-v2 stabilization, pushes to master-v2 (not only main) must
    trigger CI so the branch's Windows/Linux behavior is proven pre-merge."""
    workflow = yaml.safe_load(CI.read_text(encoding="utf-8"))
    # PyYAML 1.1 parses the bare `on:` key as boolean True; accept either form.
    triggers = workflow.get("on")
    if triggers is None:
        triggers = workflow.get(True, {})
    push_branches = triggers.get("push", {}).get("branches", [])
    assert "main" in push_branches
    assert "master-v2" in push_branches


def test_required_ci_jobs_present():
    """Release-gate jobs exist: cross-OS tests + both install E2Es. The remaining
    plan-required columns (wheel isolation, multi-host dispatch, artifact audit,
    transaction fault injection) run inside the `tests` job via run_ci — proven by
    test_gate_columns_have_real_coverage."""
    workflow = yaml.safe_load(CI.read_text(encoding="utf-8"))
    jobs = workflow["jobs"]
    assert set(jobs["tests"]["strategy"]["matrix"]["os"]) == {"ubuntu-latest", "windows-latest"}
    assert "install-ps1-e2e" in jobs       # install-windows-e2e
    assert "install-linux-e2e" in jobs


def test_gate_columns_have_real_coverage():
    """Plan-required gate columns that run inside the tests job must have a real
    test surface, not just a claimed job name."""
    tests = REPO_ROOT / "cli" / "tests"
    assert (tests / "test_multihost_dispatch_e2e.py").is_file()   # multihost-dispatch-e2e
    assert (tests / "test_wheel_install.py").is_file()            # wheel-isolation-e2e
    assert (tests / "test_install_transaction.py").is_file()      # transaction-fault-injection
    # artifact-audit runs first inside scripts/run_ci.py
    assert "audit_artifacts" in (REPO_ROOT / "scripts" / "run_ci.py").read_text(encoding="utf-8")
