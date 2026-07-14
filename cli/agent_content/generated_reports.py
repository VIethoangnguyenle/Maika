"""Generated-analysis report paths and frontmatter validation."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
import re

import yaml

SCHEMA_REL = "config/generated-report.schema.yaml"
_SAFE_PART = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")


def load_report_schema(framework_dir: Path) -> dict:
    path = Path(framework_dir) / SCHEMA_REL
    if not path.exists():
        raise FileNotFoundError(str(path))
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValueError(f"{path}: schema must be a mapping")
    return doc


def validate_report_schema(schema: dict) -> list[str]:
    errors: list[str] = []
    if not isinstance(schema.get("version"), int):
        errors.append("version: required integer field")
    required = schema.get("required")
    properties = schema.get("properties")
    if not isinstance(required, list) or not required:
        errors.append("required: must be a non-empty list")
    if not isinstance(properties, dict):
        errors.append("properties: must be a mapping")
        properties = {}
    for field in required or []:
        if field not in properties and field not in {
            "provider", "workflow", "question", "generated_at",
            "repository_commit", "graph_commit",
        }:
            errors.append(f"required field {field!r} has no property contract")
    return errors


def parse_frontmatter(text: str) -> tuple[dict | None, str | None]:
    if not text.startswith("---\n"):
        return None, "report must start with YAML frontmatter"
    marker = text.find("\n---\n", 4)
    if marker < 0:
        return None, "report frontmatter is not closed"
    try:
        doc = yaml.safe_load(text[4:marker])
    except yaml.YAMLError as exc:
        return None, f"invalid YAML frontmatter: {exc}"
    if not isinstance(doc, dict):
        return None, "report frontmatter must be a mapping"
    return doc, None


def validate_report_document(text: str, schema: dict) -> list[str]:
    frontmatter, parse_error = parse_frontmatter(text)
    if parse_error:
        return [parse_error]
    errors: list[str] = []
    for field in schema.get("required") or []:
        if field not in frontmatter or frontmatter[field] in (None, ""):
            errors.append(f"missing required frontmatter field {field!r}")
    for field, contract in (schema.get("properties") or {}).items():
        if field not in frontmatter:
            continue
        if "const" in contract and frontmatter[field] != contract["const"]:
            errors.append(f"{field}: must equal {contract['const']!r}")
        if "enum" in contract and frontmatter[field] not in contract["enum"]:
            errors.append(f"{field}: unknown value {frontmatter[field]!r}")
    return errors


def report_path(workflow: str, slug: str, *, generated_at: datetime | None = None,
                active_change_id: str | None = None) -> PurePosixPath:
    """Return a normalized repo-relative report path; never the repository root."""
    if not _SAFE_PART.fullmatch(workflow) or not _SAFE_PART.fullmatch(slug):
        raise ValueError("workflow and slug must be safe path components")
    if active_change_id is not None:
        if not _SAFE_PART.fullmatch(active_change_id):
            raise ValueError("active change id must be a safe path component")
        name = f"{workflow}_{slug}".upper().replace("-", "_") + ".md"
        return PurePosixPath(".maika", "changes", active_change_id, "exploration", name)
    stamp = (generated_at or datetime.now(timezone.utc)).strftime("%Y%m%dT%H%M%SZ")
    return PurePosixPath(".maika", "reports", workflow, f"{slug}-{stamp}.md")


def validate_report_files(framework_dir: Path) -> list[str]:
    framework = Path(framework_dir)
    schema = load_report_schema(framework)
    errors = [f"schema: {error}" for error in validate_report_schema(schema)]
    report_paths = list((framework / "reports").glob("**/*.md"))
    report_paths += list((framework / "changes").glob("*/exploration/*REPORT*.md"))
    report_paths += list((framework / "changes").glob("*/exploration/UNDERSTAND_CHAT_*.md"))
    for path in sorted(set(report_paths)):
        for error in validate_report_document(path.read_text(encoding="utf-8"), schema):
            errors.append(f"{path.relative_to(framework)}: {error}")
    return errors
