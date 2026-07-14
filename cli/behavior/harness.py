"""Static behavior harness — fixtures A–J (agent-facing plan §20, PR 14).

Runs the behavior suite WITHOUT a real agent: it exercises the framework's
declarative surfaces (workflow router, skill contracts, gates, rule/kernel law)
against scenario expectations and emits one trace per fixture. Any router,
contract or gate change that would alter agent-visible behavior for a scenario
fails here first. Real-agent runs (cross-host) are the evidence-gated PR 15.
"""

from __future__ import annotations

import importlib.util
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import yaml

from cli.agent_content.router import load_router, resolve_route
from cli.agent_content.skill_contract import load_contracts

SUITE_REL = "config/behavior-suite.yaml"

# Gate fixtures the suite's gate_rejects checks reference by name.
GATE_FIXTURES = {
    "open-material-conflict": yaml.safe_dump({
        "version": 1,
        "conflicts": [{"id": "CONF-1", "classification": "business ambiguity",
                       "status": "open", "statement": "contract A vs contract B"}],
    }),
    "assumption-public-contract-unapproved": None,   # built below
    "assumption-persistence-unapproved": None,
}


def _trace_fixture(atype: str, **extra) -> str:
    record = {"id": "AS-1", "type": atype, "statement": "x", "evidence_gap": "y",
              "expiry_condition": "z", **extra}
    return yaml.safe_dump({"decision": {
        "id": "DEC-1", "statement": "s", "type": "architecture",
        "knowledge_questions": ["q"], "evidence_ids": ["EV-1"],
        "authority": "current source", "conflicts": [], "assumptions": [record],
        "confidence": "medium", "freshness": "fresh", "verdict": "accepted",
    }})


GATE_FIXTURES["assumption-public-contract-unapproved"] = _trace_fixture("public_contract")
GATE_FIXTURES["assumption-persistence-unapproved"] = _trace_fixture(
    "persistence_destructive", database_evidence="DATABASE_CONTEXT.yaml#tbl"
)


def _load_gates(framework: Path):
    path = Path(framework) / "tools" / "gate-check" / "gates.py"
    spec = importlib.util.spec_from_file_location("maika_behavior_gates", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_suite(framework: Path) -> dict:
    return yaml.safe_load((Path(framework) / SUITE_REL).read_text(encoding="utf-8"))


def _run_route_walk(check: dict, router: dict) -> tuple[list[str], dict]:
    violations: list[str] = []
    klass = check["class"]
    state = "NONE"
    skills, artifacts, worker_actions = [], set(), 0
    for action in check["route"]:
        route = resolve_route(router, action, klass, state)
        if not route["allowed"]:
            violations.append(f"route: {action} not allowed from {state}: {route['reason']}")
            break
        if route["skill"]:
            skills.append(route["skill"])
        artifacts.update(route["produces"])
        if route["requires_worker"] and route["role"] == "implementation":
            worker_actions += 1
        state = route["next_state"]
    expected_skills = check.get("skills_invoked") or []
    if sorted(set(skills)) != sorted(set(expected_skills)):
        violations.append(
            f"skills: expected {sorted(set(expected_skills))}, routed {sorted(set(skills))}"
        )
    for skill in check.get("forbidden_skills") or []:
        if skill in skills:
            violations.append(f"skills: forbidden {skill} was routed")
    for artifact in check.get("required_artifacts") or []:
        if artifact not in artifacts:
            violations.append(f"artifacts: required {artifact} not produced by route")
    for artifact in check.get("forbidden_artifacts") or []:
        if artifact in artifacts:
            violations.append(f"artifacts: forbidden {artifact} produced by route")
    if state != check.get("expected_final_state"):
        violations.append(f"state: route ends at {state}, "
                          f"expected {check.get('expected_final_state')}")
    limit = check.get("max_worker_actions")
    if limit is not None and worker_actions > limit:
        violations.append(f"budget: {worker_actions} implementation dispatches > {limit}")
    trace = {"selected_class": klass, "selected_route": list(check["route"]),
             "skills_invoked": sorted(set(skills)),
             "artifacts_created": sorted(artifacts), "final_state": state}
    return violations, trace


def _run_check(check: dict, *, framework: Path, router: dict, contracts: dict,
               gates) -> tuple[list[str], dict]:
    kind = check.get("kind")
    if kind == "route_walk":
        return _run_route_walk(check, router)
    if kind == "route_skill":
        route = resolve_route(router, check["action"], check["class"], "COMPLETED"
                              if check["action"] == "archive" else "NONE")
        ok = route["skill"] == check["skill"]
        return ([] if ok else [f"route_skill: {check['action']} routes {route['skill']}, "
                               f"expected {check['skill']}"],
                {"skill": route["skill"]})
    if kind == "skill_contract":
        contract = contracts.get(check["skill"])
        violations = []
        if contract is None:
            return [f"skill_contract: {check['skill']} missing"], {}
        if (contract.get("routing") or {}).get("mode") != check.get("mode"):
            violations.append(f"skill_contract: {check['skill']} mode != {check['mode']}")
        outputs = (contract.get("outputs") or {})
        declared = list(outputs.get("required") or []) + list(outputs.get("optional") or [])
        if check.get("required_output") and check["required_output"] not in declared:
            violations.append(
                f"skill_contract: {check['skill']} missing output {check['required_output']}")
        if check.get("gate") and check["gate"] not in (contract.get("gates") or []):
            violations.append(f"skill_contract: {check['skill']} missing gate {check['gate']}")
        return violations, {"contract": check["skill"]}
    if kind == "gate_rejects":
        text = GATE_FIXTURES[check["fixture"]]
        validator = getattr(gates, {
            "conflicts": "validate_conflicts",
            "knowledge-trace": "validate_knowledge_trace",
        }[check["gate"]])
        result = validator(text)
        violations = []
        if result.ok:
            violations.append(f"gate_rejects: {check['gate']} accepted {check['fixture']}")
        elif check.get("reason_contains") and check["reason_contains"] not in result.reason:
            violations.append(
                f"gate_rejects: reason {result.reason!r} lacks {check['reason_contains']!r}")
        return violations, {"gate": check["gate"], "reason": getattr(result, "reason", "")}
    if kind == "content_marker":
        text = (Path(framework) / check["file"]).read_text(encoding="utf-8")
        missing = [marker for marker in check["must_contain"] if marker not in text]
        return ([f"content_marker: {check['file']} missing {m!r}" for m in missing],
                {"file": check["file"]})
    if kind == "poisoning_guard":
        from cli.knowledge_control import sanitize_learning_text
        _cleaned, threats = sanitize_learning_text(check["text"])
        return ([] if threats else
                ["poisoning_guard: sanitize_learning_text flagged nothing"],
                {"threats": list(threats)})
    return [f"unknown check kind: {kind}"], {}


def run_suite(framework: Path) -> dict:
    framework = Path(framework)
    suite = load_suite(framework)
    router = load_router(framework)
    contracts = load_contracts(framework)
    gates = _load_gates(framework)
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=framework.parent,
                            capture_output=True, text=True, check=False)
    traces = []
    for fixture in suite.get("fixtures") or []:
        violations, detail = [], []
        for check in fixture.get("checks") or []:
            errs, trace = _run_check(check, framework=framework, router=router,
                                     contracts=contracts, gates=gates)
            violations.extend(errs)
            detail.append({"kind": check.get("kind"), **trace})
        traces.append({
            "fixture_id": fixture["id"],
            "title": fixture.get("title"),
            "framework_commit": commit.stdout.strip() or "unavailable",
            "ts": datetime.now(timezone.utc).isoformat(),
            "checks": detail,
            "violations": violations,
            "verdict": "PASS" if not violations else "FAIL",
        })
    return {"version": 1, "mode": "static",
            "fixtures": traces,
            "verdict": "PASS" if all(t["verdict"] == "PASS" for t in traces) else "FAIL"}
