"""Artifact authority registry — load + validate (agent-facing refactor PR 1).

The registry (``config/artifact-authority.yaml`` under the framework root)
declares ONE authoritative artifact per agent-facing decision, plus the legacy
paths that are no longer an authority for anything. It is distinct from
``config/artifact-registry.yaml``, which audits source-tree file lifecycle.
"""

from __future__ import annotations

from pathlib import Path

import yaml

REGISTRY_REL = "config/artifact-authority.yaml"


def load_registry(framework_dir: Path) -> dict:
    """Load the registry from a framework root (e.g. ``<target>/.maika``)."""
    path = Path(framework_dir) / REGISTRY_REL
    if not path.exists():
        raise FileNotFoundError(str(path))
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValueError(f"{path}: registry must be a mapping")
    return doc


def validate_registry(doc: dict) -> list[str]:
    """Return validation errors (empty list = valid)."""
    errors: list[str] = []
    if not isinstance(doc.get("version"), int):
        errors.append("version: required integer field")

    authorities = doc.get("authorities")
    sources: dict[str, str] = {}
    if not isinstance(authorities, dict) or not authorities:
        errors.append("authorities: required non-empty mapping")
        authorities = {}
    for decision, spec in authorities.items():
        source = (spec or {}).get("source") if isinstance(spec, dict) else None
        if not isinstance(source, str) or not source.strip():
            errors.append(f"authorities.{decision}: missing non-empty source")
            continue
        if source in sources:
            errors.append(
                f"authorities.{decision}: duplicate source {source!r} "
                f"already owned by {sources[source]}"
            )
            continue
        sources[source] = decision
        if decision == "generated_analysis_reports":
            if spec.get("authority") != "generated_analysis":
                errors.append("authorities.generated_analysis_reports: invalid authority")
            if spec.get("canonical") is not False:
                errors.append("authorities.generated_analysis_reports: canonical must be false")
            if spec.get("promotion_required") is not True:
                errors.append("authorities.generated_analysis_reports: promotion must be required")

    deprecated = doc.get("deprecated") or []
    if not isinstance(deprecated, list):
        errors.append("deprecated: must be a list")
        deprecated = []
    for index, entry in enumerate(deprecated):
        if not isinstance(entry, dict):
            errors.append(f"deprecated[{index}]: must be a mapping")
            continue
        path = entry.get("path")
        if not isinstance(path, str) or not path.strip():
            errors.append(f"deprecated[{index}]: missing non-empty path")
            continue
        if path in sources:
            errors.append(
                f"deprecated[{index}]: {path!r} is both deprecated and an "
                f"authority source ({sources[path]})"
            )
        if "replacement" not in entry:
            errors.append(f"deprecated[{index}] ({path}): missing replacement "
                          "(use null for discarded artifacts)")
            continue
        replacement = entry["replacement"]
        if replacement is not None and replacement not in sources:
            errors.append(
                f"deprecated[{index}] ({path}): replacement {replacement!r} "
                "is not a declared authority source"
            )
    return errors
