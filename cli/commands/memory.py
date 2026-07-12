"""Explicit non-task preference storage."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import subprocess
import uuid

import yaml

from cli.scaffold import load_resolved_config

PREFERENCE_TYPES = {
    "coding_style", "naming", "architecture_preference", "workflow_preference",
}


def _framework_dir(target: Path) -> Path:
    resolved = load_resolved_config(target)
    return target / ((resolved or {}).get("framework_root", ".maika"))


def _store_path(framework: Path, scope: str) -> Path:
    if scope == "project":
        return framework / "knowledge/preferences/project-preferences.yaml"
    if scope == "session":
        return framework / "runtime/session-preferences.yaml"
    raise ValueError("global scope is unavailable: no safe global storage convention is configured")


def _load(path: Path) -> dict:
    if not path.exists():
        return {"version": 1, "entries": []}
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict) or not isinstance(doc.get("entries"), list):
        raise ValueError(f"invalid preference store: {path}")
    return doc


def _save(path: Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8",
    )


def _repository_commit(target: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=target, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else "unavailable"


def remember(statement: str, *, target_dir: str = ".", scope: str = "project",
             preference_type: str = "coding_style") -> tuple[int, str | None]:
    statement = statement.strip()
    if not statement:
        print("Refused: preference statement must not be empty")
        return 2, None
    if preference_type not in PREFERENCE_TYPES:
        print(f"Refused: unknown preference type {preference_type!r}")
        return 2, None
    target = Path(target_dir).resolve()
    framework = _framework_dir(target)
    try:
        path = _store_path(framework, scope)
        doc = _load(path)
    except ValueError as exc:
        print(f"Refused: {exc}")
        return 2, None
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    preference_id = "PREF-" + uuid.uuid4().hex[:12].upper()
    doc["entries"].append({
        "id": preference_id,
        "statement": statement,
        "scope": scope,
        "type": preference_type,
        "source": "explicit_user",
        "status": "active",
        "created_at": now,
        "confirmed": True,
        "provenance": {
            "user_statement": statement,
            "repository_commit": _repository_commit(target),
        },
        "promotion": {"target": None, "promoted_at": None},
    })
    _save(path, doc)
    print(f"remembered {preference_id} ({scope}, {preference_type})")
    return 0, preference_id


def _selected_stores(framework: Path, scope: str | None) -> list[Path]:
    if scope:
        return [_store_path(framework, scope)]
    return [_store_path(framework, "project"), _store_path(framework, "session")]


def run_memory(action: str, *, target_dir: str = ".", preference_id: str | None = None,
               scope: str | None = None, promotion_target: str | None = None) -> int:
    target = Path(target_dir).resolve()
    framework = _framework_dir(target)
    try:
        stores = _selected_stores(framework, scope)
    except ValueError as exc:
        print(f"Refused: {exc}")
        return 2
    if action == "list":
        found = 0
        for path in stores:
            for entry in _load(path)["entries"]:
                print(f"{entry['id']}\t{entry['scope']}\t{entry['status']}\t{entry['statement']}")
                found += 1
        if not found:
            print("no preferences")
        return 0
    if not preference_id:
        print(f"Refused: memory {action} requires --id")
        return 2
    if action == "promote" and not promotion_target:
        print("Refused: memory promote requires --promotion-target")
        return 2
    for path in stores:
        doc = _load(path)
        for entry in doc["entries"]:
            if entry.get("id") != preference_id:
                continue
            if action == "forget":
                entry["status"] = "forgotten"
            elif action == "promote":
                entry["status"] = "promoted"
                entry["promotion"] = {
                    "target": promotion_target,
                    "promoted_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                }
            else:
                print(f"Unknown memory action: {action}")
                return 2
            _save(path, doc)
            print(f"{action}d {preference_id}")
            return 0
    print(f"Refused: preference not found: {preference_id}")
    return 1
