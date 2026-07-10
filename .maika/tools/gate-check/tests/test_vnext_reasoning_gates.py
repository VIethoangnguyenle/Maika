import hashlib
import importlib.util
import subprocess
from pathlib import Path

import yaml

_G = Path(__file__).resolve().parents[1] / "gates.py"
spec = importlib.util.spec_from_file_location("gates", _G)
gates = importlib.util.module_from_spec(spec); spec.loader.exec_module(gates)

_PP = Path(__file__).resolve().parents[2] / "microloop-orchestrator" / "plan_parser.py"
spec2 = importlib.util.spec_from_file_location("plan_parser", _PP)
pp = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(pp)


def _repo(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "src" / "a.py").write_text("class A:\n    pass\n", encoding="utf-8")
    (tmp_path / "tests" / "test_a.py").write_text("def test_a():\n    assert True\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "base"],
        cwd=tmp_path, check=True,
    )
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=tmp_path, capture_output=True, text=True).stdout.strip()


def _grounding():
    return yaml.safe_dump(
        {
            "version": 1,
            "codebase": {
                "entry_points": ["cli.maika"],
                "current_flow": ["CODE-001"],
                "extension_seams": ["planner"],
                "related_tests": ["tests/test_a.py"],
                "data_models": [],
                "dependencies": [],
                "blast_radius": ["cli"],
                "uncertainties": [],
            },
            "business": {
                "terminology": ["change"],
                "actors": ["developer"],
                "rules": ["BUS-001"],
                "states_and_transitions": ["INTAKE -> PLANNING"],
                "permissions": [],
                "exceptions": [],
                "temporal_rules": [],
                "unresolved_questions": [],
                "evidence_sources": ["INTENT.md"],
            },
            "conventions": {
                "applicable_rule_ids": ["R1"],
                "architecture_patterns": ["gate-check"],
                "naming_patterns": ["vnext_*"],
                "testing_patterns": ["pytest"],
                "transaction_boundaries": [],
                "error_handling": [],
                "observability": [],
                "audit": [],
                "conflicts": [],
            },
        },
        sort_keys=False,
    )


def _evidence():
    return yaml.safe_dump(
        {
            "version": 1,
            "change_id": "demo",
            "claims": [
                {
                    "id": "CODE-001",
                    "statement": "A exists.",
                    "category": "exact_code_fact",
                    "status": "verified",
                    "sources": [
                        {
                            "type": "file_symbol",
                            "file": "src/a.py",
                            "symbol": "A",
                            "file_hash": "sha256:" + "a" * 64,
                        }
                    ],
                }
            ],
        },
        sort_keys=False,
    )


def _small_spec():
    return """# SPEC

## Goal
Do the thing.

## Current Behavior
Old behavior.

## Desired Behavior
New behavior.

## Acceptance Criteria
- AC-001: The thing works.

## Relevant Evidence
- CODE-001

## Evidence References
- CODE-001
"""


def _plan(base_sha, spec_hash, evidence_hash):
    return f"""---
change_id: demo
plan_version: 1
base_commit: {base_sha}
spec_hash: sha256:{spec_hash}
evidence_hash: sha256:{evidence_hash}
---

# Plan

### TASK-001: Implement AC

```yaml
task:
  id: TASK-001
  implementation_mode: guided
  depends_on: []
  files:
    modify: [src/a.py]
    test: [tests/test_a.py]
  symbols:
    src/a.py: [A]
  verification:
    command: pytest tests/test_a.py -q
    expected: "1 passed"
```

Acceptance criteria:
- AC-001: The thing works.
"""


def test_intent_gate_requires_standard_intent():
    change = "change_id: demo\nclass: standard\ntitle: Demo\ncreated_at: now\n"
    assert gates.validate_intent("Summary: Implement vNext reasoning.\n", change).ok
    res = gates.validate_intent("\n", change)
    assert not res.ok and "intent" in res.reason
    scaffold = "# Intent\n\nChange: demo\n\nSummary:\n"
    stub = gates.validate_intent(scaffold, change)
    assert not stub.ok and "summary" in stub.reason


def test_exploration_evidence_requires_three_lenses_and_verified_sources():
    assert gates.validate_exploration_evidence(_grounding(), _evidence()).ok
    bad_grounding = _grounding().replace("business:", "missing_business:")
    assert not gates.validate_exploration_evidence(bad_grounding, _evidence()).ok
    bad_evidence = _evidence().replace("sources:", "missing_sources:")
    assert not gates.validate_exploration_evidence(_grounding(), bad_evidence).ok
    missing_hash = _evidence().replace('file_hash: sha256:' + "a" * 64, "file_hash: ''")
    res = gates.validate_exploration_evidence(_grounding(), missing_hash)
    assert not res.ok and "file_hash" in res.reason


def test_exploration_evidence_authenticity_rejects_fake_path_symbol_hash(tmp_path):
    _repo(tmp_path)  # creates src/a.py = "class A:\n    pass\n" + tests/test_a.py
    real_hash = "sha256:" + hashlib.sha256((tmp_path / "src" / "a.py").read_bytes()).hexdigest()

    def _ev(file="src/a.py", symbol="A", fhash=real_hash):
        return yaml.safe_dump({
            "version": 1, "change_id": "demo",
            "claims": [{
                "id": "CODE-001", "statement": "A exists.",
                "category": "exact_code_fact", "status": "verified",
                "sources": [{"type": "file_symbol", "file": file, "symbol": symbol, "file_hash": fhash}],
            }],
        }, sort_keys=False)

    assert gates.validate_exploration_evidence(_grounding(), _ev(), repo_root=str(tmp_path)).ok
    r = gates.validate_exploration_evidence(_grounding(), _ev(file="src/ghost.py"), repo_root=str(tmp_path))
    assert not r.ok and "not found" in r.reason
    r = gates.validate_exploration_evidence(_grounding(), _ev(symbol="Zzz"), repo_root=str(tmp_path))
    assert not r.ok and "symbol" in r.reason
    r = gates.validate_exploration_evidence(_grounding(), _ev(fhash="sha256:" + "a" * 64), repo_root=str(tmp_path))
    assert not r.ok and "hash mismatch" in r.reason


def test_spec_gate_requires_small_contract_and_evidence_refs():
    assert gates.validate_vnext_spec(_small_spec(), change_class="small").ok
    res = gates.validate_vnext_spec(_small_spec().replace("## Evidence References", "## Evidence"), change_class="small")
    assert not res.ok and "Evidence References" in res.reason


def test_plan_gate_checks_acceptance_criteria_and_evidence_hash(tmp_path):
    sha = _repo(tmp_path)
    evidence_hash = hashlib.sha256(_evidence().encode("utf-8")).hexdigest()
    spec_hash = hashlib.sha256(_small_spec().encode("utf-8")).hexdigest()
    text = _plan(sha, spec_hash, evidence_hash)

    res = gates.validate_vnext_plan(
        text,
        plan_doc=pp.parse_plan(text),
        repo_root=str(tmp_path),
        spec_sha256=spec_hash,
        evidence_sha256=evidence_hash,
        spec_text=_small_spec(),
    )
    assert res.ok, res.reason

    stale = gates.validate_vnext_plan(
        text,
        plan_doc=pp.parse_plan(text),
        repo_root=str(tmp_path),
        spec_sha256=spec_hash,
        evidence_sha256="b" * 64,
        spec_text=_small_spec(),
    )
    assert not stale.ok and "evidence_hash" in stale.reason

    no_ac = text.replace("AC-001: The thing works.", "AC-999: Different.")
    uncovered = gates.validate_vnext_plan(
        no_ac,
        plan_doc=pp.parse_plan(no_ac),
        repo_root=str(tmp_path),
        spec_sha256=spec_hash,
        evidence_sha256=evidence_hash,
        spec_text=_small_spec(),
    )
    assert not uncovered.ok and "acceptance" in uncovered.reason
