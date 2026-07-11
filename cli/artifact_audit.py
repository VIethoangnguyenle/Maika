"""CI-enforced validation of the canonical artifact registry."""

from __future__ import annotations

from datetime import date
import fnmatch
from pathlib import Path
import re

import yaml


ALLOWED_TYPES = {"runtime", "adapter", "config", "template", "documentation",
                 "test", "historical", "migration"}
ALLOWED_STATUS = {"active", "compatibility", "deprecated", "historical", "candidate-delete"}

# Patterns that indicate dynamic file dispatch in production code.
_DISPATCH_PATTERNS = [
    # spec_from_file_location(..., <path ending in name.py>)
    r'spec_from_file_location\s*\([^)]*["\'](?:[^"\']*[/\\])?{name}\.py["\']',
    # _sibling("name")
    r'_sibling\s*\(\s*["\'](?:{name})["\']',
    # _load("name", ...) or _load("name", "name.py")
    r'_load\s*\(\s*["\'](?:{name})["\']',
    # _load_module(..., "name")
    r'_load_module\s*\([^)]*["\'](?:{name})["\']',
    # string containing the module path
    r'["\'](?:[^"\']*[/\\])?{name}\.py["\']',
]

# Directories containing text documents that serve as CLI entrypoint consumers.
_ENTRYPOINT_DIRS = ("procedures", "skills", "workflows", "rules")


def _finding(check: str, path: str, message: str, severity: str = "high") -> dict:
    return {"check": check, "path": path, "message": message, "severity": severity}


def _production_texts(root: Path):
    roots = [root / "cli", root / ".maika", root / "scripts", root / ".github",
             root / "README.md", root / "docs/architecture", root / "docs/tdd"]
    for base in roots:
        paths = [base] if base.is_file() else sorted(base.rglob("*")) if base.exists() else []
        for path in paths:
            if not path.is_file() or "tests" in path.parts or "__pycache__" in path.parts:
                continue
            rel = path.relative_to(root).as_posix()
            if rel in {"cli/artifact_audit.py", ".maika/config/artifact-registry.yaml"}:
                continue
            if path.suffix.lower() not in {".py", ".md", ".yaml", ".yml", ".json", ".ps1", ".sh"}:
                continue
            try:
                yield rel, path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue


def _check_tool_consumers(
    root: Path,
    production_texts: list[tuple[str, str]],
    dynamic_consumers: list[dict],
    manifest: dict,
) -> tuple[list[dict], list[dict]]:
    """Check each .maika/tools/**/*.py module for a real consumer.

    Returns (findings, consumer_report) where consumer_report is a list of
    dicts {path, consumed_by} for the audit report.
    """
    tools_dir = root / ".maika" / "tools"
    if not tools_dir.exists():
        return [], []

    # Collect all non-test .py modules under .maika/tools/
    tool_modules = []
    for py_file in sorted(tools_dir.rglob("*.py")):
        if "tests" in py_file.parts or "__pycache__" in py_file.parts:
            continue
        if py_file.name.startswith("test_"):
            continue
        tool_modules.append(py_file)

    # Pre-compute production .py texts (non-test) for import/dispatch checks
    py_texts = [(rel, text) for rel, text in production_texts if rel.endswith(".py")]

    # Pre-compute entrypoint reference texts from procedures/skills/workflows
    entrypoint_texts: list[tuple[str, str]] = []
    for dirname in _ENTRYPOINT_DIRS:
        ep_dir = root / ".maika" / dirname
        if not ep_dir.exists():
            continue
        for md_file in sorted(ep_dir.rglob("*")):
            if not md_file.is_file():
                continue
            try:
                entrypoint_texts.append(
                    (md_file.relative_to(root).as_posix(),
                     md_file.read_text(encoding="utf-8")))
            except (OSError, UnicodeDecodeError):
                continue

    findings: list[dict] = []
    consumer_report: list[dict] = []

    for py_file in tool_modules:
        rel = py_file.relative_to(root).as_posix()
        basename = py_file.stem  # e.g. "gates", "loop_state"
        evidences: list[str] = []

        # Package markers are structural Python artifacts, not executable
        # runtime modules, and are exempt from consumer requirements.
        if py_file.name == "__init__.py":
            consumer_report.append({"path": rel, "consumed_by": "package-marker-exemption"})
            continue

        # ── Mechanism 1: Python import ──
        import_pattern = re.compile(
            rf"(?:^|\n)\s*(?:import\s+{re.escape(basename)}\b"
            rf"|from\s+{re.escape(basename)}\s+import)"
        )
        for src_rel, src_text in py_texts:
            if src_rel == rel:
                continue
            if import_pattern.search(src_text):
                evidences.append(f"python-import:{src_rel}")
                break

        # ── Mechanism 2: String file-dispatch ──
        for src_rel, src_text in py_texts:
            if src_rel == rel:
                continue
            for pat_template in _DISPATCH_PATTERNS:
                pat = pat_template.format(name=re.escape(basename))
                if re.search(pat, src_text):
                    evidences.append(f"file-dispatch:{src_rel}")
                    break
            else:
                continue
            break

        # ── Mechanism 3: CLI entrypoint in procedures/skills/workflows ──
        try:
            source_text = py_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            source_text = ""
        has_main = 'if __name__' in source_text and '__main__' in source_text
        if has_main:
            # Check if the module path or basename is referenced in entrypoint docs
            for ep_rel, ep_text in entrypoint_texts:
                if rel in ep_text or f"{basename}.py" in ep_text:
                    evidences.append(f"cli-entrypoint:{ep_rel}")
                    break

        # ── Mechanism 4: dynamic_consumers registry ──
        for entry in dynamic_consumers:
            pattern = entry.get("pattern", "")
            loader = entry.get("loader", "")
            if fnmatch.fnmatch(rel, pattern):
                # A registry declaration is evidence only when the loader also
                # contains an actual dispatch reference for this module.
                loader_path = root / loader
                loader_text = loader_path.read_text(encoding="utf-8") if loader_path.is_file() else ""
                if loader_path.is_file() and (basename in loader_text or rel in loader_text):
                    evidences.append(f"dynamic-consumer:{loader}:{entry.get('reason', '')}")
                break

        consumed_by = "; ".join(evidences) if evidences else "NONE"
        consumer_report.append({"path": rel, "consumed_by": consumed_by})

        if not evidences:
            findings.append(_finding(
                "dead-tool-module", rel,
                "tool module has no real production consumer "
                "(not imported, not file-dispatched, not a CLI entrypoint, "
                "not in a verified dynamic consumer mapping)"))

    return findings, consumer_report


def emit_consumer_audit_report(root: Path, consumer_report: list[dict]) -> None:
    """Write the consumer audit report to docs/refactor/master-v2/."""
    report_path = root / "docs" / "refactor" / "master-v2" / "artifact-consumer-audit-v2.yaml"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "version": 2,
        "description": "Mechanical consumer detection for .maika/tools/**/*.py modules",
        "modules": consumer_report,
    }
    report_path.write_text(
        yaml.safe_dump(report, sort_keys=False, allow_unicode=True, default_flow_style=False),
        encoding="utf-8",
    )


def audit_artifacts(root: Path, *, write_report: bool = False,
                    check_report: bool = False) -> list[dict]:
    root = Path(root).resolve()
    registry_path = root / ".maika/config/artifact-registry.yaml"
    if not registry_path.is_file():
        return [_finding("registry", str(registry_path), "canonical artifact registry is missing", "critical")]
    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
    artifacts = registry.get("artifacts") or []
    defaults = registry.get("manifest_consumer_defaults") or {}
    groups = registry.get("artifact_groups") or []
    dynamic_consumers = registry.get("dynamic_consumers") or []
    findings = []

    manifest_path = root / "cli/plugin-manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    from cli.scaffold import resolve_source_path
    for plugin in manifest.get("plugins") or []:
        source = resolve_source_path(root, plugin.get("source", ""))
        if not source.exists():
            findings.append(_finding("manifest-source", plugin.get("source", ""),
                                     f"manifest plugin {plugin.get('name')} source is missing", "critical"))
        if not defaults.get(plugin.get("type")):
            findings.append(_finding("manifest-consumer", plugin.get("output", ""),
                                     f"no production consumer declared for plugin type {plugin.get('type')}"))

    policy_owners = {}
    production_texts = list(_production_texts(root))
    for item in artifacts:
        path = str(item.get("path") or "")
        missing = [key for key in ("type", "ownership", "producer", "consumers",
                                   "runtime_authority", "status") if key not in item]
        if missing:
            findings.append(_finding("registry-schema", path, f"missing fields: {', '.join(missing)}"))
            continue
        if item["type"] not in ALLOWED_TYPES:
            findings.append(_finding("registry-schema", path, f"unknown type: {item['type']}"))
        if item["status"] not in ALLOWED_STATUS:
            findings.append(_finding("registry-schema", path, f"unknown status: {item['status']}"))
        symbolic = "#" in path
        exists = (root / path).exists() if not symbolic else False
        if item.get("deleted"):
            if exists:
                findings.append(_finding("deleted-artifact", path, "deleted artifact exists again", "critical"))
            needle = Path(path).name
            for rel, text in production_texts:
                if needle in text or path in text:
                    findings.append(_finding("stale-reference", rel,
                                             f"references deleted artifact {path}"))
        elif item["status"] in {"active", "historical"} and not symbolic and not exists:
            findings.append(_finding("registry-source", path, "declared artifact does not exist", "critical"))
        if item["status"] in {"active", "compatibility"} and not item.get("consumers"):
            findings.append(_finding("production-consumer", path,
                                     "active artifact has no production consumer"))
        if item["type"] == "runtime" and item["status"] == "active" and path.startswith("cli/"):
            module = path[:-3].replace("/", ".") if path.endswith(".py") else ""
            imported = any(
                re.search(rf"(?:from\s+{re.escape(module)}\s+import|import\s+{re.escape(module)}\b)", text)
                for rel, text in production_texts if rel != path
            )
            if not imported:
                findings.append(_finding("production-import", path,
                                         "production module is not imported outside tests"))
        domain = item.get("policy_domain")
        if domain and item.get("runtime_authority"):
            policy_owners.setdefault(domain, []).append(path)
        if item["status"] in {"compatibility", "deprecated"}:
            expiry = item.get("expires_after")
            try:
                expired = date.fromisoformat(str(expiry)) < date.today()
            except ValueError:
                findings.append(_finding("compatibility-expiry", path, "invalid or missing expires_after"))
            else:
                if expired:
                    findings.append(_finding("compatibility-expiry", path,
                                             f"compatibility expired on {expiry}", "critical"))

    for domain, owners in policy_owners.items():
        if len(owners) > 1:
            findings.append(_finding("duplicate-policy", domain,
                                     f"multiple runtime authorities: {', '.join(owners)}", "critical"))

    # ── Tool consumer check (PR9 / F9) ──
    tool_findings, consumer_report = _check_tool_consumers(
        root, production_texts, dynamic_consumers, manifest)
    findings.extend(tool_findings)
    if consumer_report and write_report:
        emit_consumer_audit_report(root, consumer_report)
    elif consumer_report and check_report:
        report_path = root / "docs/refactor/master-v2/artifact-consumer-audit-v2.yaml"
        expected = yaml.safe_dump({
            "version": 2,
            "description": "Mechanical consumer detection for .maika/tools/**/*.py modules",
            "modules": consumer_report,
        }, sort_keys=False, allow_unicode=True, default_flow_style=False)
        actual = report_path.read_text(encoding="utf-8") if report_path.is_file() else ""
        if actual != expected:
            findings.append(_finding(
                "stale-consumer-report", report_path.relative_to(root).as_posix(),
                "consumer audit report is stale; run audit with --write-report",
            ))

    coverage_files = []
    for base, pattern in ((root / "cli", "*.py"), (root / ".maika", "*.py"),
                          (root / "scripts", "*.py"), (root / "docs", "*.md")):
        if base.exists():
            coverage_files.extend(path for path in base.rglob(pattern)
                                  if "tests" not in path.parts and "__pycache__" not in path.parts)
    exact = {str(item.get("path")) for item in artifacts if not item.get("deleted")}
    for path in coverage_files:
        rel = path.relative_to(root).as_posix()
        covered = rel in exact
        for group in groups:
            excluded = any(fnmatch.fnmatch(rel, pattern) for pattern in group.get("exclude") or [])
            if not excluded and fnmatch.fnmatch(rel, group.get("path_glob", "")):
                covered = True
                break
        if not covered:
            findings.append(_finding("registry-coverage", rel,
                                     "production artifact is not covered by registry or artifact group"))

    history_path = root / "docs/archive/implemented/index.yaml"
    history = yaml.safe_load(history_path.read_text(encoding="utf-8")) if history_path.is_file() else {}
    if history.get("runtime_authority") is not False or history.get("default_retrieval") != "exclude":
        findings.append(_finding("historical-authority", str(history_path.relative_to(root)),
                                 "implemented history must be non-authoritative and excluded by default"))
    for directory in (root / "upgrade", root / "docs/superpowers", root / "docs/archive/implemented"):
        if not directory.exists():
            continue
        for path in directory.rglob("*.md"):
            head = "\n".join(path.read_text(encoding="utf-8").splitlines()[:30])
            if re.search(r"^runtime_authority:\s*true\s*$", head, re.MULTILINE):
                findings.append(_finding(
                    "historical-authority", path.relative_to(root).as_posix(),
                    "historical document declares runtime_authority true", "critical",
                ))
    return findings
