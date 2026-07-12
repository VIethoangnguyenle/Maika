"""Load and validate the session interaction router."""

from __future__ import annotations

from pathlib import Path

import yaml

ROUTER_REL = "config/interaction-router.yaml"
PRECEDENCE = (
    "explicit_native_command",
    "explicit_maika_command",
    "natural_language_classification",
)
HANDLERS = {
    "task-workflow",
    "native-or-provider-query",
    "external-workflow",
    "learning-store",
    "framework-command",
}
MUTABILITIES = {
    "task_scoped",
    "read_or_report",
    "registered_artifacts_only",
    "learning_store_only",
    "framework_scoped",
}


def load_interaction_router(framework_dir: Path) -> dict:
    path = Path(framework_dir) / ROUTER_REL
    if not path.exists():
        raise FileNotFoundError(str(path))
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValueError(f"{path}: router must be a mapping")
    return doc


def validate_interaction_router(doc: dict) -> list[str]:
    errors: list[str] = []
    if not isinstance(doc.get("version"), int):
        errors.append("version: required integer field")
    precedence = doc.get("precedence")
    if precedence != list(PRECEDENCE):
        errors.append(f"precedence: must be exactly {list(PRECEDENCE)!r}")
    routes = doc.get("routes")
    if not isinstance(routes, dict) or not routes:
        return errors + ["routes: required non-empty mapping"]
    workspace_routes = []
    for name, spec in routes.items():
        if not isinstance(spec, dict):
            errors.append(f"routes.{name}: must be a mapping")
            continue
        handler = spec.get("handler")
        if handler not in HANDLERS:
            errors.append(f"routes.{name}: unknown handler {handler!r}")
        mutability = spec.get("mutability")
        if mutability not in MUTABILITIES:
            errors.append(f"routes.{name}: unknown mutability {mutability!r}")
        creates = spec.get("creates_change_workspace")
        if not isinstance(creates, bool):
            errors.append(f"routes.{name}: creates_change_workspace must be boolean")
        elif creates:
            workspace_routes.append(name)
    if workspace_routes != ["task_change"]:
        errors.append("task_change must be the only route creating a change workspace")
    if "default" in routes or "fallback" in doc:
        errors.append("default-to-task fallback is forbidden")
    return errors
