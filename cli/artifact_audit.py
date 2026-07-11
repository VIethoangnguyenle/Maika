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


def _finding(check: str, path: str, message: str, severity: str = "high") -> dict:
    return {"check": check, "path": path, "message": message, "severity": severity}


def _production_texts(root: Path):
    roots = [root / "cli", root / ".maika", root / "scripts", root / ".github",
             root / "README.md", root / "docs/architecture", root / "docs/tdd"]
    for base in roots:
        paths = [base] if base.is_file() else base.rglob("*") if base.exists() else []
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


def audit_artifacts(root: Path) -> list[dict]:
    root = Path(root).resolve()
    registry_path = root / ".maika/config/artifact-registry.yaml"
    if not registry_path.is_file():
        return [_finding("registry", str(registry_path), "canonical artifact registry is missing", "critical")]
    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
    artifacts = registry.get("artifacts") or []
    defaults = registry.get("manifest_consumer_defaults") or {}
    groups = registry.get("artifact_groups") or []
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
