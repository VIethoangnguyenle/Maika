"""System-model validator (harness plan §20) — cross-surface link checks.

risk signal -> skill -> capability -> provider -> tool -> lane -> request
artifact -> invocation record -> evidence artifact -> gate -> state transition.

Only links NOT already covered by a dedicated validator are checked here
(R5): skill-contract, router, provider-capability and gate registration each
have their own. This validator proves the chain segments that span python
tool surfaces (dispatch roles) and YAML contracts agree.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import yaml

from cli.agent_content.skill_contract import load_contracts

DB_CAPABILITY = "database_schema_inspection"
PERSISTENCE_TRIGGER = "persistence_change"
TRACE_ARTIFACTS = ("exploration/TRACE_REQUEST.yaml", "exploration/TRACE_EVIDENCE.yaml")
TRACE_GATES = ("provider-invocations", "trace-request", "trace-evidence")


def _load_dispatch_module(framework_dir: Path):
    tool_dir = Path(framework_dir) / "tools" / "microloop-orchestrator"
    sys.path.insert(0, str(tool_dir))
    try:
        spec = importlib.util.spec_from_file_location(
            "maika_system_model_dispatch", tool_dir / "vnext_dispatch.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(tool_dir))


def validate_system_model(framework_dir: Path) -> list[str]:
    framework_dir = Path(framework_dir)
    errors: list[str] = []
    registry = yaml.safe_load(
        (framework_dir / "profiles" / "capability-registry.yaml").read_text(encoding="utf-8")
    ) or {}
    providers = (yaml.safe_load(
        (framework_dir / "config" / "provider-registry.yaml").read_text(encoding="utf-8")
    ) or {}).get("providers") or {}
    router = yaml.safe_load(
        (framework_dir / "config" / "workflow-router.yaml").read_text(encoding="utf-8")
    ) or {}
    contracts = {name: contract for name, contract in load_contracts(framework_dir).items()
                 if contract}
    dispatch = _load_dispatch_module(framework_dir)

    # Link 1 — dispatch role -> skill file -> contract (plan §20: skill link).
    for role in dispatch.AUTHORING_ROLES:
        skill = dispatch.DISPATCH_SKILLS.get(role)
        if not skill:
            errors.append(f"authoring role {role!r} has no DISPATCH_SKILLS mapping")
            continue
        if not (framework_dir / "skills" / skill / "SKILL.md").is_file():
            errors.append(f"role {role!r} maps to missing skill file {skill!r}")
        elif skill not in contracts:
            errors.append(f"role {role!r} skill {skill!r} has no parsed contract")

    # Link 2 — trigger vocabulary is fully consumed (risk signal -> capability).
    vocabulary = set(registry.get("triggers") or {})
    consumed: set[str] = set()
    for contract in contracts.values():
        for spec in ((contract.get("capabilities") or {}).get("conditional") or {}).values():
            consumed.update((spec or {}).get("triggers") or [])
    for trigger in sorted(vocabulary - consumed):
        errors.append(f"trigger {trigger!r} is declared but no skill consumes it")

    # Link 3 — persistence chain: signal -> database-explorer -> provider lane.
    db_consumers = [
        name for name, contract in contracts.items()
        if PERSISTENCE_TRIGGER in (
            ((contract.get("capabilities") or {}).get("conditional") or {})
            .get(DB_CAPABILITY, {}) or {}
        ).get("triggers", [])
    ]
    if not db_consumers:
        errors.append(f"no skill activates {DB_CAPABILITY} on {PERSISTENCE_TRIGGER}")
    explorer = contracts.get("database-explorer") or {}
    for gate in ("database-request", "database-context"):
        if gate not in (explorer.get("gates") or []):
            errors.append(f"database-explorer does not declare gate {gate!r}")
    if "database" not in dispatch.AUTHORING_ROLES:
        errors.append("no 'database' authoring dispatch role for database-explorer")
    lanes = (((providers.get("db-access") or {}).get("tool_contract") or {})
             .get("lanes") or {})
    if not (lanes.get("exploration") or {}).get("tools"):
        errors.append("db-access provider has no exploration lane tool snapshot")

    # Link 4 — trace chain: explore produces the artifacts its gates validate.
    explore = (router.get("actions") or {}).get("explore") or {}
    produces = set(explore.get("produces") or [])
    gates = set(explore.get("completion_gates") or [])
    for artifact in TRACE_ARTIFACTS:
        if artifact not in produces:
            errors.append(f"router explore does not produce {artifact}")
    for gate in TRACE_GATES:
        if gate not in gates:
            errors.append(f"router explore is missing completion gate {gate!r}")

    # Link 5 — refresh chain: blocker codes are legal state-machine reasons.
    state_path = framework_dir / "tools" / "microloop-orchestrator" / "vnext_state.py"
    spec = importlib.util.spec_from_file_location("maika_system_model_state", state_path)
    state = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(state)
    if "capability" not in state.BLOCK_REASONS:
        errors.append("BLOCK_REASONS lost 'capability' — refresh blockers cannot persist")
    workflows = yaml.safe_load(
        (framework_dir / "config" / "external-workflows.yaml").read_text(encoding="utf-8")
    ) or {}
    for name, spec_doc in (workflows.get("workflows") or {}).items():
        owner = (spec_doc or {}).get("owner")
        if owner and owner not in providers:
            errors.append(f"external workflow {name!r} owner {owner!r} is not a "
                          "registered provider")
    return errors
