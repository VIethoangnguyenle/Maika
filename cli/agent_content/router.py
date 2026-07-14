"""Workflow router — load, validate, resolve (agent-facing refactor PR 3).

The router (``config/workflow-router.yaml``) is the single authority for which
skill/role/artifacts/gates an action uses and which state it may run from. It
is validated against the REAL runtime surfaces, never a parallel copy:

- states/transitions: ``tools/microloop-orchestrator/vnext_state.py``
- gate names:         ``tools/gate-check/cli.py`` VALIDATORS
- skill names:        ``skills/skill-index.yaml``
- artifact authority: ``config/artifact-authority.yaml``
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import yaml

from cli.agent_content.authority import load_registry

ROUTER_REL = "config/workflow-router.yaml"
CLASSES = ("trivial", "small", "standard", "architectural")


def load_router(framework_dir: Path) -> dict:
    path = Path(framework_dir) / ROUTER_REL
    if not path.exists():
        raise FileNotFoundError(str(path))
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValueError(f"{path}: router must be a mapping")
    return doc


def _load_module(framework_dir: Path, rel: str, name: str):
    path = Path(framework_dir) / rel
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _runtime_surfaces(framework_dir: Path) -> dict:
    state = _load_module(
        framework_dir, "tools/microloop-orchestrator/vnext_state.py", "maika_router_state"
    )
    gates = _load_module(framework_dir, "tools/gate-check/cli.py", "maika_router_gates")
    index = yaml.safe_load(
        (Path(framework_dir) / "skills" / "skill-index.yaml").read_text(encoding="utf-8")
    ) or {}
    skills = {entry.get("name") for entry in index.get("skills") or []}
    registry = load_registry(framework_dir)
    sources = [
        (spec or {}).get("source", "")
        for spec in (registry.get("authorities") or {}).values()
    ]
    return {
        "states": set(state.STATES),
        "allowed": state.ALLOWED,
        "block_reasons": set(state.BLOCK_REASONS),
        "gates": set(gates.VALIDATORS),
        "skills": skills,
        "authority_sources": sources,
    }


def _path_exists(allowed: dict, start: str, goal: str) -> bool:
    seen, frontier = {start}, [start]
    while frontier:
        current = frontier.pop()
        if current == goal:
            return True
        for nxt in allowed.get(current, set()):
            if nxt not in seen:
                seen.add(nxt)
                frontier.append(nxt)
    return goal in seen


def _covered(produced: str, sources: list[str]) -> bool:
    full = f"changes/<change-id>/{produced}"
    for source in sources:
        if full == source:
            return True
        if source.endswith("/") and full.startswith(source):
            return True
    return False


def _resolved_for_class(action_spec: dict, key: str, klass: str):
    by_class = action_spec.get(f"{key}_by_class")
    if isinstance(by_class, dict) and klass in by_class:
        return by_class[klass]
    return action_spec.get(key)


def validate_router(doc: dict, framework_dir: Path) -> list[str]:
    errors: list[str] = []
    if not isinstance(doc.get("version"), int):
        errors.append("version: required integer field")
    actions = doc.get("actions")
    if not isinstance(actions, dict) or not actions:
        return errors + ["actions: required non-empty mapping"]

    surfaces = _runtime_surfaces(framework_dir)
    states, allowed = surfaces["states"], surfaces["allowed"]

    for name, spec in actions.items():
        if not isinstance(spec, dict):
            errors.append(f"{name}: must be a mapping")
            continue
        classes = spec.get("classes") or []
        if not classes or not set(classes) <= set(CLASSES):
            errors.append(f"{name}: classes must be a non-empty subset of {CLASSES}")
            continue
        allowed_from = spec.get("allowed_from") or []
        for state in allowed_from:
            if state != "NONE" and state not in states:
                errors.append(f"{name}: unknown state {state} in allowed_from")
        for klass in classes:
            skill = _resolved_for_class(spec, "skill", klass)
            if skill is not None and skill not in surfaces["skills"]:
                errors.append(f"{name}: unknown skill {skill} (class {klass})")
            success = _resolved_for_class(spec, "success_state", klass)
            if success not in states:
                errors.append(f"{name}: unknown success state {success} (class {klass})")
                continue
            for state in allowed_from:
                if state == "NONE":
                    if success != "INTAKE":
                        errors.append(f"{name}: NONE may only lead to INTAKE")
                elif state == success:
                    if not spec.get("optional"):
                        errors.append(f"{name}: self-loop {state} requires optional: true")
                elif not _path_exists(allowed, state, success):
                    errors.append(
                        f"{name}: no legal transition path {state} -> {success}"
                    )
            produces = list(spec.get("produces") or [])
            produces += list((spec.get("produces_by_class") or {}).get(klass) or [])
            for artifact in produces:
                if artifact in ("CHANGE.yaml", "STATE.yaml"):
                    continue  # workspace roots, owned by start
                if not _covered(artifact, surfaces["authority_sources"]):
                    errors.append(
                        f"{name}: produced artifact {artifact} has no authority "
                        "entry in artifact-authority.yaml"
                    )
            if spec.get("requires_worker") and not _resolved_for_class(
                spec, "context_route", klass
            ):
                errors.append(f"{name}: worker action missing context_route (class {klass})")
        for gate in spec.get("completion_gates") or []:
            if gate not in surfaces["gates"]:
                errors.append(f"{name}: unknown completion gate {gate}")
        for retry in spec.get("retry_states") or []:
            if retry not in states:
                errors.append(f"{name}: unknown retry state {retry}")
        if spec.get("optional") and not spec.get("skip_when"):
            errors.append(f"{name}: optional action requires skip_when")
        for label, route in (spec.get("failure_routes") or {}).items():
            if (route or {}).get("state") != "BLOCKED":
                errors.append(f"{name}: failure route {label} must target BLOCKED")
            elif route.get("reason") not in surfaces["block_reasons"]:
                errors.append(
                    f"{name}: failure route {label} has invalid reason "
                    f"{route.get('reason')!r}"
                )

    # Every class must be able to walk NONE -> ... -> COMPLETED via routed actions.
    for klass in CLASSES:
        positions = {"NONE"}
        changed = True
        while changed:
            changed = False
            for spec in actions.values():
                if not isinstance(spec, dict) or klass not in (spec.get("classes") or []):
                    continue
                if not set(spec.get("allowed_from") or []) & positions:
                    continue
                success = _resolved_for_class(spec, "success_state", klass)
                targets = {success} | set(spec.get("retry_states") or [])
                if not targets <= positions:
                    positions |= targets
                    changed = True
        if "COMPLETED" not in positions:
            errors.append(f"class {klass}: no action path reaches COMPLETED")
    return errors


def resolve_route(doc: dict, action: str, klass: str, state: str) -> dict:
    spec = (doc.get("actions") or {}).get(action)
    if spec is None:
        raise KeyError(action)
    allowed = klass in (spec.get("classes") or []) and state in (spec.get("allowed_from") or [])
    reason = ""
    if klass not in (spec.get("classes") or []):
        reason = f"action {action} is not routed for class {klass}"
    elif state not in (spec.get("allowed_from") or []):
        reason = f"action {action} not allowed from state {state}"
    produces = list(spec.get("produces") or [])
    produces += list((spec.get("produces_by_class") or {}).get(klass) or [])
    return {
        "action": action,
        "class": klass,
        "state": state,
        "allowed": allowed,
        "reason": reason,
        "requires_worker": bool(spec.get("requires_worker")),
        "dispatch": spec.get("dispatch"),
        "optional": bool(spec.get("optional")),
        "skill": _resolved_for_class(spec, "skill", klass),
        "role": spec.get("role"),
        "context_route": _resolved_for_class(spec, "context_route", klass),
        "produces": produces,
        "completion_gates": list(spec.get("completion_gates") or []),
        "next_state": _resolved_for_class(spec, "success_state", klass),
        "retry_states": list(spec.get("retry_states") or []),
        "failure_routes": dict(spec.get("failure_routes") or {}),
    }
