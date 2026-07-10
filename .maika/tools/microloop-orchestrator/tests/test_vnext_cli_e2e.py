import json
import subprocess
import sys
from pathlib import Path
import yaml
import pytest


def _write_valid_reasoning(ws):
    (ws / "INTENT.md").write_text("Summary: Implement standard reasoning validation.\n", encoding="utf-8")
    (ws / "exploration" / "GROUNDING.yaml").write_text(
        yaml.safe_dump({
            "version": 1,
            "codebase": {
                "entry_points": ["orchestrator.py"],
                "current_flow": ["CODE-001"],
                "extension_seams": ["gate-check"],
                "related_tests": ["tests/test_vnext_cli_e2e.py"],
                "data_models": [],
                "dependencies": [],
                "blast_radius": ["microloop-orchestrator"],
                "uncertainties": [],
            },
            "business": {
                "terminology": ["change"],
                "actors": ["developer"],
                "rules": ["BUS-001"],
                "states_and_transitions": ["EXPLORING -> RECONCILING"],
                "permissions": [],
                "exceptions": [],
                "temporal_rules": [],
                "unresolved_questions": [],
                "evidence_sources": ["INTENT.md"],
            },
            "conventions": {
                "applicable_rule_ids": ["R1"],
                "architecture_patterns": ["gate-check"],
                "naming_patterns": ["vnext-*"],
                "testing_patterns": ["pytest"],
                "transaction_boundaries": [],
                "error_handling": [],
                "observability": [],
                "audit": [],
                "conflicts": [],
            },
        }, sort_keys=False),
        encoding="utf-8",
    )
    (ws / "exploration" / "EVIDENCE_MANIFEST.yaml").write_text(
        yaml.safe_dump({
            "version": 1,
            "change_id": "demo",
            "claims": [{
                "id": "CODE-001",
                "statement": "The orchestrator has vNext commands.",
                "category": "exact_code_fact",
                "status": "verified",
                "sources": [{
                    "type": "file_symbol",
                    "file": ".maika/tools/microloop-orchestrator/orchestrator.py",
                    "symbol": "main",
                    "file_hash": "sha256:" + "a" * 64,
                }],
            }],
        }, sort_keys=False),
        encoding="utf-8",
    )


def _write_small_spec(ws):
    (ws / "SPEC.md").write_text("""# SPEC

## Goal
Validate the W2 path.

## Context
The CLI is validating W2.

## Current Behavior
The path is not validated.

## Desired Behavior
The path is validated.

## Actors
Developer.

## Functional Requirements
- Validate reasoning and spec.

## Business Rules
- BR-001: Validation must gate planning.

## States and Transitions
- SPEC_REVIEW -> PLANNING.

## Architecture
Use existing gate-check.

## Components and Boundaries
orchestrator and gate-check.

## Data Flow
Workspace files into validators.

## API and Contract Changes
None.

## Persistence Changes
None.

## Event and Async Behavior
None.

## Error Handling
Return non-zero on failed validation.

## Security and Authorization
No change.

## Observability and Audit
Write generated validation JSON.

## Migration
No migration.

## Rollback
Revert the command changes.

## Testing Strategy
Use pytest.

## Acceptance Criteria
- AC-001: W2 validation runs.

## Non-goals
- Execute tasks.

## Risks
- Stale artifacts.

## Evidence References
- CODE-001
""", encoding="utf-8")


def test_vnext_cli_e2e(tmp_path):
    # Setup fixture
    fw_root = tmp_path / ".maika"
    fw_root.mkdir()
    prof = fw_root / "profiles"
    prof.mkdir()
    # Python script to mock the worker
    mock_worker = tmp_path / "mock_worker.py"
    mock_worker.write_text("""import sys, re
prompt = sys.argv[1]
out_path = re.search(r'^OUTPUT_FILE: (.+)$', prompt, re.M).group(1)
with open(out_path, 'w') as f:
    f.write("VERDICT: APPROVED\\n" if "plan-review" in out_path else "stub result")
""")
    (prof / "execution-mode.yaml").write_text(f"workflow_engine: vnext\nworker_command: '{sys.executable} {mock_worker} {{prompt}}'\n")
    
    ch_root = tmp_path / ".maika" / "changes"
    ch_root.mkdir()
    
    orch = Path(__file__).resolve().parents[1] / "orchestrator.py"
    cmd = [sys.executable, str(orch)]
    
    # Init
    res = subprocess.run(cmd + ["vnext-init", "--changes-root", str(ch_root), "--id", "demo", "--class", "small", "--title", "t"], capture_output=True, text=True)
    assert res.returncode == 0
    ws = ch_root / "demo"
    assert yaml.safe_load((ws / "STATE.yaml").read_text())["state"] == "INTAKE"
    
    # Need PLAN and SPEC for compile
    (ws / "SPEC.md").write_text("# spec\n")
    import hashlib
    spec_sha = hashlib.sha256((ws / "SPEC.md").read_bytes()).hexdigest()
    evidence_sha = hashlib.sha256((ws / "exploration" / "EVIDENCE_MANIFEST.yaml").read_bytes()).hexdigest()
    
    plan_text = f"""---
change_id: demo
plan_version: 1
base_commit: deadbeef
spec_hash: sha256:{spec_sha}
evidence_hash: sha256:{evidence_sha}
---

# Plan

### TASK-001: Demo

```yaml
task:
  id: TASK-001
  implementation_mode: exact
  verification:
    command: pytest
    expected: pass
```

Body
"""
    (ws / "IMPLEMENTATION_PLAN.md").write_text(plan_text)
    
    # Mock base_commit resolve in gates.py
    # Since we can't easily mock git in this E2E test, we'll bypass the git check by initializing a git repo.
    subprocess.run(["git", "init", "-q"], cwd=tmp_path)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "base"], cwd=tmp_path)
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=tmp_path, capture_output=True, text=True).stdout.strip()
    
    (ws / "IMPLEMENTATION_PLAN.md").write_text(plan_text.replace("deadbeef", sha))
    
    # Compile
    res = subprocess.run(cmd + ["vnext-compile", "--workspace", str(ws), "--repo-root", str(tmp_path)], capture_output=True, text=True)
    assert res.returncode == 0
    assert yaml.safe_load((ws / "STATE.yaml").read_text())["state"] == "PLAN_REVIEW"
    
    # Review
    res = subprocess.run(cmd + ["vnext-review-plan", "--workspace", str(ws), "--repo-root", str(tmp_path)], capture_output=True, text=True)
    assert res.returncode == 0
    assert yaml.safe_load((ws / "STATE.yaml").read_text())["state"] == "PLAN_REVIEW"
    
    # Run
    # The runner stub in orchestrator will just output stub which is invalid result, so it will block.
    res = subprocess.run(cmd + ["vnext-run", "--workspace", str(ws), "--repo-root", str(tmp_path)], capture_output=True, text=True)
    assert res.returncode == 0
    st = yaml.safe_load((ws / "STATE.yaml").read_text())["state"]
    # state should be EXECUTING because task blocked
    assert st == "EXECUTING"
    
    # Status
    res = subprocess.run(cmd + ["vnext-status", "--workspace", str(ws), "--repo-root", str(tmp_path)], capture_output=True, text=True)
    assert res.returncode == 0
    assert "State: EXECUTING" in res.stdout


def test_vnext_reasoning_and_spec_validation_commands(tmp_path):
    fw_root = tmp_path / ".maika"
    fw_root.mkdir()
    prof = fw_root / "profiles"
    prof.mkdir()
    (prof / "execution-mode.yaml").write_text("workflow_engine: vnext\n", encoding="utf-8")
    ch_root = tmp_path / ".maika" / "changes"
    ch_root.mkdir()
    orch = Path(__file__).resolve().parents[1] / "orchestrator.py"
    cmd = [sys.executable, str(orch)]

    res = subprocess.run(
        cmd + ["vnext-init", "--changes-root", str(ch_root), "--id", "demo", "--class", "standard", "--title", "t"],
        capture_output=True, text=True,
    )
    assert res.returncode == 0
    ws = ch_root / "demo"
    state = yaml.safe_load((ws / "STATE.yaml").read_text(encoding="utf-8"))
    state["state"] = "EXPLORING"
    (ws / "STATE.yaml").write_text(yaml.safe_dump(state), encoding="utf-8")
    _write_valid_reasoning(ws)

    res = subprocess.run(cmd + ["vnext-validate-reasoning", "--workspace", str(ws), "--repo-root", str(tmp_path)], capture_output=True, text=True)
    assert res.returncode == 0
    assert yaml.safe_load((ws / "STATE.yaml").read_text(encoding="utf-8"))["state"] == "RECONCILING"
    assert (ws / "generated" / "EXPLORATION_VALIDATION.json").exists()

    state = yaml.safe_load((ws / "STATE.yaml").read_text(encoding="utf-8"))
    state["state"] = "SPEC_REVIEW"
    (ws / "STATE.yaml").write_text(yaml.safe_dump(state), encoding="utf-8")
    _write_small_spec(ws)

    res = subprocess.run(cmd + ["vnext-validate-spec", "--workspace", str(ws), "--repo-root", str(tmp_path)], capture_output=True, text=True)
    assert res.returncode == 0
    assert yaml.safe_load((ws / "STATE.yaml").read_text(encoding="utf-8"))["state"] == "PLANNING"
    assert (ws / "generated" / "SPEC_VALIDATION.json").exists()


def test_standard_change_cannot_compile_from_intake_without_reasoning(tmp_path):
    fw_root = tmp_path / ".maika"
    fw_root.mkdir()
    prof = fw_root / "profiles"
    prof.mkdir()
    (prof / "execution-mode.yaml").write_text("workflow_engine: vnext\n", encoding="utf-8")
    ch_root = tmp_path / ".maika" / "changes"
    ch_root.mkdir()
    orch = Path(__file__).resolve().parents[1] / "orchestrator.py"
    cmd = [sys.executable, str(orch)]

    res = subprocess.run(
        cmd + ["vnext-init", "--changes-root", str(ch_root), "--id", "demo", "--class", "standard", "--title", "t"],
        capture_output=True, text=True,
    )
    assert res.returncode == 0
    ws = ch_root / "demo"
    (ws / "SPEC.md").write_text("# spec\n", encoding="utf-8")
    (ws / "IMPLEMENTATION_PLAN.md").write_text("---\nchange_id: demo\n---\n", encoding="utf-8")

    res = subprocess.run(cmd + ["vnext-compile", "--workspace", str(ws), "--repo-root", str(tmp_path)], capture_output=True, text=True)
    assert res.returncode == 1
    assert "requires reasoning/spec validation" in res.stdout

def test_refuse_legacy(tmp_path):
    fw_root = tmp_path / ".maika"
    fw_root.mkdir()
    prof = fw_root / "profiles"
    prof.mkdir()
    (prof / "execution-mode.yaml").write_text("workflow_engine: legacy\n")
    
    ch_root = tmp_path / ".maika" / "changes"
    ch_root.mkdir()
    
    orch = Path(__file__).resolve().parents[1] / "orchestrator.py"
    cmd = [sys.executable, str(orch)]
    
    res = subprocess.run(cmd + ["vnext-init", "--changes-root", str(ch_root), "--id", "demo", "--class", "small", "--title", "t"], capture_output=True, text=True)
    assert res.returncode == 2
    assert "Refused" in res.stdout

def test_vnext_cli_prefers_local_override_over_template(tmp_path):
    fw_root = tmp_path / ".maika"
    fw_root.mkdir()
    prof = fw_root / "profiles"
    prof.mkdir()
    (prof / "execution-mode.yaml").write_text("{% if platform == 'codex' %}\nworkflow_engine: legacy\n{% endif %}\n")
    (prof / "execution-mode.local.yaml").write_text("workflow_engine: vnext\n")

    ch_root = tmp_path / ".maika" / "changes"
    ch_root.mkdir()

    orch = Path(__file__).resolve().parents[1] / "orchestrator.py"
    cmd = [sys.executable, str(orch)]

    res = subprocess.run(cmd + ["vnext-init", "--changes-root", str(ch_root), "--id", "demo", "--class", "small", "--title", "t"], capture_output=True, text=True)
    assert res.returncode == 0
    assert "Workspace initialized" in res.stdout
