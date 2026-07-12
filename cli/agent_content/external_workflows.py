"""Load and validate provider-owned external workflow effect contracts."""

from __future__ import annotations

from pathlib import Path, PurePosixPath

import yaml

REGISTRY_REL = "config/external-workflows.yaml"
KINDS = {"knowledge_query", "knowledge_maintenance"}
MUTABILITIES = {
    "read_only",
    "read_or_report",
    "registered_artifacts_only",
    "provider_index_only",
}
TASK_POLICIES = {"forbidden", "not_required"}


def load_external_workflows(framework_dir: Path) -> dict:
    path = Path(framework_dir) / REGISTRY_REL
    if not path.exists():
        raise FileNotFoundError(str(path))
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValueError(f"{path}: registry must be a mapping")
    return doc


def _application_path(pattern: str) -> bool:
    normalized = PurePosixPath(pattern).as_posix().lstrip("./")
    return normalized == "src" or normalized.startswith("src/")


def validate_external_workflows(doc: dict) -> list[str]:
    errors: list[str] = []
    if not isinstance(doc.get("version"), int):
        errors.append("version: required integer field")
    workflows = doc.get("workflows")
    if not isinstance(workflows, dict) or not workflows:
        return errors + ["workflows: required non-empty mapping"]
    for name, spec in workflows.items():
        prefix = f"workflows.{name}"
        if not isinstance(spec, dict):
            errors.append(f"{prefix}: must be a mapping")
            continue
        kind = spec.get("kind")
        mutability = spec.get("mutability")
        if kind not in KINDS:
            errors.append(f"{prefix}: unknown kind {kind!r}")
        if mutability not in MUTABILITIES:
            errors.append(f"{prefix}: unknown mutability {mutability!r}")
        if spec.get("task_workspace") not in TASK_POLICIES:
            errors.append(f"{prefix}: invalid task_workspace policy")
        writes = spec.get("allowed_writes") or []
        report_paths = spec.get("allowed_report_paths") or []
        if mutability == "read_only" and (writes or report_paths):
            errors.append(f"{prefix}: read-only workflow cannot declare writes")
        if any(_application_path(path) for path in [*writes, *report_paths]):
            errors.append(f"{prefix}: workflow cannot write application source")
        if kind == "knowledge_maintenance" and not spec.get("produces"):
            errors.append(f"{prefix}: maintenance workflow must declare outputs")
        if mutability == "registered_artifacts_only":
            if not writes:
                errors.append(f"{prefix}: registered-artifact workflow needs allowed_writes")
            missing = set(spec.get("produces") or []) - set(writes)
            if missing:
                errors.append(f"{prefix}: outputs outside allowed_writes: {sorted(missing)!r}")
            if not (spec.get("freshness") or {}).get("binds_to_repository_commit"):
                errors.append(f"{prefix}: graph maintenance must bind freshness to commit")
        promotion = spec.get("promotion") or {}
        if "generated_report" in (spec.get("output_modes") or []) and promotion.get("automatic") is not False:
            errors.append(f"{prefix}: generated reports cannot auto-promote")
    return errors
