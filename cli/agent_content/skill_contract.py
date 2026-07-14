"""Typed skill contracts — parse + validate (agent-facing refactor PR 4).

Every skill's frontmatter carries a typed contract:

- ``routing``: mode (workflow | dispatch | conditional), actions, states, classes
- ``capabilities.required``: capability IDs (profiles/capability-registry.yaml)
- ``capabilities.one_of``: named groups; at least one member must be satisfied
  at runtime (e.g. structured_trace)
- ``capabilities.conditional``: capability -> ``{triggers: [...]}``; only
  callable when a declared trigger (registry ``triggers:`` vocabulary) fires
- ``outputs.required`` / ``outputs.optional``: artifact paths with an authority
  entry in config/artifact-authority.yaml
- ``gates``: completion gate names (tools/gate-check VALIDATORS)

Workflow skills must agree with config/workflow-router.yaml in BOTH directions:
the skill declares only actions that route it, and every skill the router
dispatches declares that action. Prose stays in the body (13 knowledge-native
headings); metadata controls routing.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from cli.agent_content.authority import load_registry
from cli.agent_content.router import _runtime_surfaces, load_router

MODES = ("workflow", "dispatch", "conditional")
CAPABILITY_KEYS = {"required", "one_of", "conditional"}
_FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_contract(skill_md: Path) -> dict | None:
    match = _FM_RE.match(skill_md.read_text(encoding="utf-8"))
    if not match:
        return None
    return yaml.safe_load(match.group(1))


def load_contracts(framework_dir: Path) -> dict[str, dict | None]:
    skills_dir = Path(framework_dir) / "skills"
    return {
        path.parent.name: parse_contract(path)
        for path in sorted(skills_dir.glob("*/SKILL.md"))
    }


def _artifact_covered(path: str, sources: list[str]) -> bool:
    candidates = (path, f"changes/<change-id>/{path}")
    for source in sources:
        for candidate in candidates:
            if candidate == source:
                return True
            if source.endswith("/") and candidate.startswith(source):
                return True
    return False


def _validate_capabilities(
    name: str, block: dict | None, capabilities: set[str], triggers_vocab: set[str]
) -> list[str]:
    """Typed capability semantics (harness plan §8): required / one_of / conditional."""
    errors: list[str] = []
    block = block or {}
    unknown_keys = set(block) - CAPABILITY_KEYS
    if unknown_keys:
        errors.append(f"{name}: unknown capabilities keys {sorted(unknown_keys)}")
    required = block.get("required") or []
    if not required:
        errors.append(f"{name}: capabilities.required must not be empty")
    for capability in required:
        if capability not in capabilities:
            errors.append(f"{name}: unknown capability {capability}")

    one_of = block.get("one_of") or {}
    if not isinstance(one_of, dict):
        errors.append(f"{name}: capabilities.one_of must map group -> capability list")
        one_of = {}
    for group, members in one_of.items():
        if not isinstance(members, list) or not members:
            errors.append(f"{name}: one_of group {group} must be a non-empty list")
            continue
        for capability in members:
            if capability not in capabilities:
                errors.append(f"{name}: unknown capability {capability} in one_of {group}")
        overlap = set(members) & set(required)
        if overlap:
            errors.append(
                f"{name}: {sorted(overlap)} cannot be both required and one_of ({group})"
            )
    one_of_members = {
        member for members in one_of.values() if isinstance(members, list)
        for member in members
    }

    conditional = block.get("conditional") or {}
    if not isinstance(conditional, dict):
        errors.append(
            f"{name}: capabilities.conditional must map capability -> {{triggers: [...]}}"
        )
        conditional = {}
    for capability, spec in conditional.items():
        if capability not in capabilities:
            errors.append(f"{name}: unknown conditional capability {capability}")
        if capability in required:
            errors.append(f"{name}: {capability} cannot be both required and conditional")
        if capability in one_of_members:
            errors.append(f"{name}: {capability} cannot be both one_of and conditional")
        spec = spec or {}
        unknown_spec = set(spec) - {"triggers"}
        if unknown_spec:
            errors.append(
                f"{name}: conditional {capability} has unknown keys {sorted(unknown_spec)}"
            )
        declared = spec.get("triggers") or []
        if not declared:
            errors.append(
                f"{name}: conditional capability {capability} must declare >=1 trigger"
            )
        for trigger in declared:
            if trigger not in triggers_vocab:
                errors.append(
                    f"{name}: unknown trigger {trigger} for conditional {capability}"
                )
    return errors


def _router_skill_actions(router: dict) -> dict[str, set[str]]:
    """skill name -> set of router actions that dispatch it."""
    mapping: dict[str, set[str]] = {}
    for action, spec in (router.get("actions") or {}).items():
        skills = set()
        if spec.get("skill"):
            skills.add(spec["skill"])
        skills.update(v for v in (spec.get("skill_by_class") or {}).values() if v)
        for skill in skills:
            mapping.setdefault(skill, set()).add(action)
    return mapping


def validate_skill_contracts(framework_dir: Path) -> list[str]:
    framework_dir = Path(framework_dir)
    errors: list[str] = []
    surfaces = _runtime_surfaces(framework_dir)
    router = load_router(framework_dir)
    registry = load_registry(framework_dir)
    sources = [
        (spec or {}).get("source", "")
        for spec in (registry.get("authorities") or {}).values()
    ]
    contracts = load_contracts(framework_dir)
    routed = _router_skill_actions(router)
    registry_doc = yaml.safe_load(
        (framework_dir / "profiles" / "capability-registry.yaml").read_text(encoding="utf-8")
    ) or {}
    capabilities = set(registry_doc.get("capabilities") or {})
    triggers_vocab = set(registry_doc.get("triggers") or {})

    for name, contract in contracts.items():
        if contract is None:
            errors.append(f"{name}: SKILL.md missing frontmatter")
            continue
        routing = contract.get("routing")
        if not isinstance(routing, dict):
            errors.append(f"{name}: missing typed routing block")
            continue
        mode = routing.get("mode")
        if mode not in MODES:
            errors.append(f"{name}: routing.mode must be one of {MODES}")
            continue
        actions = routing.get("actions") or []
        states = routing.get("states") or []
        classes = routing.get("classes") or []
        if mode == "workflow":
            if not actions:
                errors.append(f"{name}: workflow skill must declare routing.actions")
            for action in actions:
                spec = (router.get("actions") or {}).get(action)
                if spec is None:
                    errors.append(f"{name}: routing.actions references unknown action {action}")
                    continue
                if action not in routed.get(name, set()):
                    errors.append(
                        f"{name}: declares action {action} but the router does not "
                        "dispatch this skill for it"
                    )
                    continue
                allowed_from = set(spec.get("allowed_from") or [])
                bad_states = set(states) - allowed_from
                if bad_states:
                    errors.append(
                        f"{name}: states {sorted(bad_states)} not in router "
                        f"allowed_from for action {action}"
                    )
                router_gates = set(spec.get("completion_gates") or [])
                extra_gates = set(contract.get("gates") or []) - router_gates
                if extra_gates:
                    errors.append(
                        f"{name}: gates {sorted(extra_gates)} not declared as "
                        f"completion gates of router action {action}"
                    )
        else:
            if actions:
                errors.append(f"{name}: {mode} skill must not declare routing.actions")
        for state in states:
            if state != "NONE" and state not in surfaces["states"]:
                errors.append(f"{name}: unknown routing state {state}")
        for klass in classes:
            if klass not in ("trivial", "small", "standard", "architectural"):
                errors.append(f"{name}: unknown routing class {klass}")
        errors.extend(
            _validate_capabilities(
                name, contract.get("capabilities"), capabilities, triggers_vocab
            )
        )
        outputs = contract.get("outputs") or {}
        declared = list(outputs.get("required") or []) + list(outputs.get("optional") or [])
        if mode != "conditional" and not outputs.get("required"):
            errors.append(f"{name}: outputs.required must not be empty")
        for artifact in declared:
            if artifact in ("CHANGE.yaml", "STATE.yaml"):
                continue
            if not _artifact_covered(artifact, sources):
                errors.append(
                    f"{name}: output {artifact} has no authority entry in "
                    "artifact-authority.yaml"
                )
        for gate in contract.get("gates") or []:
            if gate not in surfaces["gates"]:
                errors.append(f"{name}: unknown gate {gate}")

    for skill, actions in routed.items():
        contract = contracts.get(skill)
        if contract is None:
            continue  # router validator already rejects unknown skills
        declared = set((contract.get("routing") or {}).get("actions") or [])
        missing = actions - declared
        if missing:
            errors.append(
                f"{skill}: router dispatches it for {sorted(missing)} but the "
                "skill does not declare those actions"
            )
    return errors
