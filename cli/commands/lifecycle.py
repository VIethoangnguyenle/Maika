"""maika migrate / repair / uninstall — lifecycle commands (W9).

All mutation reuses the W2 transaction engine (delete plan → Transaction), the
W3 shared-host strip, and the W5 doctor findings — no parallel mutator. User
data (knowledge, changes, archive, loops, local config) is preserved by default;
purge and legacy cleanup require explicit confirmation.
"""

from __future__ import annotations

import json
import hashlib
import shutil
import tempfile
from pathlib import Path
from typing import Optional

from cli.install import ownership
from cli.install.planner import build_plan
from cli.install.transaction import Transaction
from cli.scaffold import (
    load_resolved_config,
    remove_maika_json_entry,
    strip_managed_markdown,
)

_SHARED_HOST = ("AGENTS.md", "CLAUDE.md", ".claude/settings.json",
                ".codex/hooks.json", ".agents/hooks.json")
_LEGACY_ROOTS = (".maika", ".agents", ".claude")
_USER_DATA_DIRS = frozenset({"knowledge", "changes", "archive", "loops"})


def _result(status: str, *, mutation: bool, transaction_id: Optional[str] = None,
            exit_code: Optional[int] = None) -> dict:
    """Command result semantics (F10c): exit code aligns with mutation outcome.

    status ∈ {no-op, committed, blocked, partial-safe}. no-op/committed exit 0;
    blocked/partial-safe exit non-zero. A blocked command must report
    mutation=False so callers can trust nothing was written. ``exit_code`` may be
    given explicitly to preserve a command's own contract (repair uses 2 for a
    config/CLI error, per the vNext exit-code contract).
    """
    if exit_code is None:
        exit_code = 0 if status in {"no-op", "committed"} else 1
    return {"status": status, "mutation": mutation, "transaction_id": transaction_id,
            "exit_code": exit_code}


def _framework_root(target: Path) -> str:
    return (load_resolved_config(target) or {}).get("framework_root", ".maika")


def _purge_actions(target: Path, framework_root: str) -> list[dict]:
    """Full-scope delete actions for a purge, covering every top-level entry under
    the core EXCEPT ``runtime`` (which holds the live transaction journal/backups
    and is removed only after commit). Everything here is inside the transaction,
    so a mid-purge failure rolls back the entire core (F10a)."""
    root = target / framework_root
    actions: list[dict] = []
    if not root.is_dir():
        return actions
    for entry in sorted(root.iterdir()):
        if entry.name == "runtime":
            continue
        rel = entry.relative_to(target).as_posix()
        if entry.is_dir():
            own = ownership.PROJECT if entry.name in _USER_DATA_DIRS else ownership.FRAMEWORK
            actions.append({"kind": "delete_directory", "path": rel,
                            "ownership": own, "explicit_project_delete": True})
        elif entry.is_file():
            actions.append({"kind": "delete_file", "path": rel,
                            "ownership": ownership.FRAMEWORK, "explicit_project_delete": True})
    return actions


def _framework_delete_plan(target: Path, framework_root: str) -> dict:
    """A delete_framework_file action per framework-owned file under the core.

    ownership.classify keeps project-owned paths (knowledge/active, long-term,
    skill-evolution, changes, archive, loops) out of the plan, and the
    transaction preflight independently refuses to delete any project-owned path.
    """
    root = target / framework_root
    actions = []
    if root.is_dir():
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(target).as_posix()
            if ownership.classify(rel, framework_root) == ownership.FRAMEWORK:
                actions.append({"kind": "delete_framework_file", "path": rel,
                                "ownership": ownership.FRAMEWORK})
    return {"version": 1, "operation": "uninstall", "actions": actions}


def _host_strip_actions(target: Path, staging: Path) -> list[dict]:
    actions = []
    for rel in _SHARED_HOST:
        path = target / rel
        if not path.is_file():
            continue
        if rel.endswith(".json"):
            cleaned = json.dumps(
                remove_maika_json_entry(json.loads(path.read_text(encoding="utf-8"))),
                indent=2,
            ) + "\n"
        else:
            cleaned = strip_managed_markdown(path.read_text(encoding="utf-8"))
        if cleaned.strip() in {"", "{}"}:
            actions.append({"kind": "delete_file", "path": rel, "ownership": ownership.SHARED_HOST})
        else:
            staged = staging / rel
            staged.parent.mkdir(parents=True, exist_ok=True)
            staged.write_text(cleaned, encoding="utf-8")
            actions.append({"kind": "replace", "path": rel, "ownership": ownership.SHARED_HOST})
    return actions


def run_uninstall(target_dir: str, purge_project_data: bool = False) -> dict:
    target = Path(target_dir).resolve()
    framework_root = _framework_root(target)

    staging = Path(tempfile.mkdtemp(prefix="maika-uninstall-"))
    backups = Path(tempfile.mkdtemp(prefix="maika-uninstall-bak-"))
    journal = {}
    try:
        if purge_project_data:
            # Full-scope purge, entirely inside the transaction: every top-level
            # core entry except runtime/ is a delete action, so a mid-purge
            # failure rolls the whole core back. No blind post-transaction rmtree.
            plan = {"version": 1, "operation": "uninstall-purge",
                    "actions": _host_strip_actions(target, staging) + _purge_actions(target, framework_root)}
            purged = [a["path"] for a in plan["actions"] if a["path"].startswith(framework_root + "/")
                      or a["path"] == framework_root]
        else:
            plan = _framework_delete_plan(target, framework_root)
            plan["actions"].extend(_host_strip_actions(target, staging))
            purged = []
        if not plan["actions"]:
            return _result("no-op", mutation=False)
        journal = Transaction(staging, target, backups).apply(plan)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
        shutil.rmtree(backups, ignore_errors=True)

    if purge_project_data:
        for path in purged:
            print(f"    • purged {path}")
        # Only the transaction's own runtime skeleton (journal + backups) remains
        # under the core — the recovery marker is intentionally the terminal
        # removal, once the transaction has committed.
        shutil.rmtree(target / framework_root / "runtime", ignore_errors=True)
        try:
            (target / framework_root).rmdir()
        except OSError:
            pass
        print(f"  Uninstalled Maika and purged project data under {framework_root}")
    else:
        print(f"  Uninstalled Maika core; preserved knowledge/changes/archive/loops "
              f"under {framework_root}")
    return _result("committed", mutation=True, transaction_id=journal.get("transaction_id"))


def run_repair(target_dir: str, finding_id: Optional[str] = None,
               maika_root: Optional[str] = None, transaction_id: Optional[str] = None,
               all_safe: bool = False) -> dict:
    if transaction_id:
        from cli.install.transaction import repair_transaction
        try:
            result = repair_transaction(Path(target_dir).resolve(), transaction_id)
        except (OSError, ValueError) as exc:
            print(f"  ❌ {exc}")
            return _result("blocked", mutation=False, exit_code=2)
        rolled = result.get("status") == "rolled_back"
        print(f"  transaction {transaction_id}: {result['status']}")
        return _result("committed" if rolled else "no-op", mutation=rolled,
                       transaction_id=transaction_id)
    if all_safe:
        results = [run_repair(target_dir, f, maika_root)
                   for f in ("managed-entrypoint", "native-hook")]
        mutated = any(r["mutation"] for r in results)
        if any(r["exit_code"] == 1 for r in results):
            return _result("blocked", mutation=mutated, exit_code=1)
        return _result("committed" if mutated else "no-op", mutation=mutated)
    if not finding_id:
        print("  ❌ repair requires --finding, --transaction, or --all-safe")
        return _result("blocked", mutation=False, exit_code=2)
    from cli.commands.doctor import build_setup_findings

    target = Path(target_dir).resolve()
    findings = {f["id"]: f for f in build_setup_findings(target, maika_root=maika_root)}
    finding = findings.get(finding_id)
    if finding is None:
        print(f"  ❌ unknown finding: {finding_id}")
        return _result("blocked", mutation=False, exit_code=2)
    if finding["ok"]:
        print(f"  {finding_id} is already healthy — nothing to repair")
        return _result("no-op", mutation=False)

    if finding_id == "managed-entrypoint":
        from cli.commands.update import run_update
        run_update(target_dir=str(target), maika_root=maika_root)
        return _result("committed", mutation=True)
    if finding_id == "native-hook":
        from cli.commands.platform import run_platform
        from cli.config import project as project_cfg
        primary = project_cfg.load(target)["platforms"]["primary"]
        if primary is None:
            print("  ❌ no primary platform to reinstall")
            return _result("blocked", mutation=False, exit_code=2)
        rc = run_platform("enable", str(target), primary, maika_root)
        return _result("committed" if rc == 0 else "blocked", mutation=(rc == 0),
                       exit_code=None if rc == 0 else rc)
    if finding_id == "deprecated-config":
        import yaml
        path = target / ".maika/resolved-config.yaml"
        if not path.is_file():
            print("  deprecated config path is missing")
            return _result("blocked", mutation=False, exit_code=2)
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        resolved = doc.get("resolved") or {}
        resolved.pop("hook_python", None)
        staging = Path(tempfile.mkdtemp(prefix="maika-repair-config-"))
        backups = Path(tempfile.mkdtemp(prefix="maika-repair-bak-"))
        try:
            staged = staging / ".maika/resolved-config.yaml"
            staged.parent.mkdir(parents=True, exist_ok=True)
            staged.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
            plan = build_plan(staging, target, "repair-deprecated-config", ".maika")
            journal = Transaction(staging, target, backups).apply(plan)
        finally:
            shutil.rmtree(staging, ignore_errors=True)
            shutil.rmtree(backups, ignore_errors=True)
        print("  removed deprecated config keys")
        return _result("committed", mutation=True, transaction_id=journal.get("transaction_id"))

    print(f"  no safe automatic repair for {finding_id}; see `maika doctor setup`")
    return _result("blocked", mutation=False, exit_code=2)


_MIGRATION_SUBTREES = ("knowledge/active", "knowledge/long-term", "knowledge/skill-evolution",
                       "changes", "archive", "loops")


def _legacy_resolved(root: Path) -> dict:
    path = root / "resolved-config.yaml"
    if not path.is_file():
        return {}
    try:
        doc = __import__("yaml").safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, ValueError):
        return {}
    return doc.get("resolved") if isinstance(doc.get("resolved"), dict) else {}


def _migration_candidates(target: Path) -> dict[str, list[Path]]:
    candidates: dict[str, list[Path]] = {}
    for root_name in (".agents", ".claude"):
        root = target / root_name
        for subtree in _MIGRATION_SUBTREES:
            source = root / subtree
            if not source.is_dir():
                continue
            for path in source.rglob("*"):
                if path.is_file():
                    logical = path.relative_to(root).as_posix()
                    candidates.setdefault(logical, []).append(path)
    return candidates


def _cleanup_legacy_data(target: Path) -> dict:
    staging = Path(tempfile.mkdtemp(prefix="maika-migrate-cleanup-"))
    backups = Path(tempfile.mkdtemp(prefix="maika-migrate-bak-"))
    actions = []
    try:
        for root_name in (".agents", ".claude"):
            root = target / root_name
            for subtree in ("knowledge", "changes", "archive", "loops"):
                path = root / subtree
                if path.is_dir():
                    actions.append({"kind": "delete_directory",
                                    "path": path.relative_to(target).as_posix(),
                                    "ownership": ownership.FRAMEWORK})
            resolved = root / "resolved-config.yaml"
            if resolved.is_file():
                actions.append({"kind": "delete_file",
                                "path": resolved.relative_to(target).as_posix(),
                                "ownership": ownership.FRAMEWORK})
        journal = Transaction(staging, target, backups).apply({
            "version": 1, "operation": "migration-cleanup", "actions": actions,
        })
    finally:
        shutil.rmtree(staging, ignore_errors=True)
        shutil.rmtree(backups, ignore_errors=True)
    print(f"  cleaned {len(actions)} legacy project-data artifact(s); native host config preserved")
    if not actions:
        return _result("no-op", mutation=False)
    return _result("committed", mutation=True, transaction_id=journal.get("transaction_id"))


def _apply_migration_resolution(target: Path, decision_path: Path) -> dict:
    """Apply operator conflict decisions (F10b resolution flow).

    Reads the conflict report + a decision file and copies the chosen candidate
    into the canonical core transactionally. A chosen path is honored only if it
    is one of that conflict's recorded candidates (no arbitrary path injection).
    Decision file: {version: 1, resolutions: [{logical_artifact, choose: <candidate>}]}.
    """
    import yaml
    report_path = target / ".maika/runtime/migration-conflicts.yaml"
    if not report_path.is_file():
        print("  no migration conflict report to resolve")
        return _result("no-op", mutation=False)
    if not decision_path.is_file():
        print(f"  decision file not found: {decision_path}")
        return _result("blocked", mutation=False)
    try:
        report = yaml.safe_load(report_path.read_text(encoding="utf-8")) or {}
        decisions = yaml.safe_load(decision_path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        print(f"  cannot read conflict report or decision file: {exc}")
        return _result("blocked", mutation=False)
    allowed = {c.get("logical_artifact"): set(c.get("candidates") or [])
               for c in (report.get("conflicts") or [])}
    chosen: dict[str, Path] = {}
    for item in decisions.get("resolutions") or []:
        logical, choose = item.get("logical_artifact"), item.get("choose")
        if logical not in allowed:
            print(f"  refused: {logical!r} is not an open conflict")
            return _result("blocked", mutation=False)
        if choose not in allowed[logical]:
            print(f"  refused: {choose!r} is not a recorded candidate for {logical!r}")
            return _result("blocked", mutation=False)
        source = target / choose
        if not source.is_file():
            print(f"  refused: chosen source missing: {choose}")
            return _result("blocked", mutation=False)
        chosen[logical] = source
    if not chosen:
        print("  no resolutions to apply")
        return _result("no-op", mutation=False)
    staging = Path(tempfile.mkdtemp(prefix="maika-resolve-"))
    backups = Path(tempfile.mkdtemp(prefix="maika-resolve-bak-"))
    try:
        actions = []
        for logical, source in chosen.items():
            dest = staging / ".maika" / logical
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dest)
            actions.append({"kind": "replace", "path": f".maika/{logical}",
                            "ownership": ownership.PROJECT, "explicit_project_delete": True})
        journal = Transaction(staging, target, backups).apply(
            {"version": 1, "operation": "migration-resolve", "actions": actions})
    finally:
        shutil.rmtree(staging, ignore_errors=True)
        shutil.rmtree(backups, ignore_errors=True)
    print(f"  applied {len(chosen)} conflict resolution(s) to the canonical core")
    return _result("committed", mutation=True, transaction_id=journal.get("transaction_id"))


def run_migrate(target_dir: str, apply: bool = False, cleanup_legacy: bool = False,
                resolve: Optional[str] = None) -> dict:
    target = Path(target_dir).resolve()
    if resolve:
        return _apply_migration_resolution(target, Path(resolve))
    inventory = {}
    for root in _LEGACY_ROOTS:
        present = (target / root).is_dir()
        inventory[root] = {
            "present": present,
            "resolved_config": (target / root / "resolved-config.yaml").exists(),
        }
    canonical_present = inventory[".maika"]["present"]
    legacy_present = inventory[".agents"]["present"] or inventory[".claude"]["present"]

    print("  Maika migration inventory:")
    for root, info in inventory.items():
        mark = "present" if info["present"] else "absent"
        cfg = " (+resolved-config)" if info["resolved_config"] else ""
        print(f"    • {root}: {mark}{cfg}")

    if not apply:
        print("  dry-run: no changes made")
        return _result("no-op", mutation=False)

    if cleanup_legacy:
        if not canonical_present:
            print("  canonical core missing; cleanup refused")
            return _result("blocked", mutation=False)
        return _cleanup_legacy_data(target)

    if not canonical_present and legacy_present:
        candidates = _migration_candidates(target)
        migration_files = {}
        preflight_conflicts = []
        for logical, paths in sorted(candidates.items()):
            hashes = [hashlib.sha256(path.read_bytes()).hexdigest() for path in paths]
            if len(set(hashes)) > 1:
                preflight_conflicts.append(logical)
            elif paths:
                migration_files[logical] = paths[0]
        if preflight_conflicts:
            print("  migration refused before mutation; divergent legacy artifacts: "
                  + ", ".join(preflight_conflicts))
            return _result("blocked", mutation=False)
        resolved = next((cfg for cfg in (
            _legacy_resolved(target / ".agents"), _legacy_resolved(target / ".claude")
        ) if cfg), {})
        platform_key = resolved.get("platform", "generic")
        from cli.commands.init import run_init
        try:
            run_init(
                str(target), platform_key=platform_key,
                selected_mcps=list(resolved.get("mcps") or []),
                language=resolved.get("language", "other"), assume_yes=True,
                migration_files=migration_files,
            )
        except (OSError, ValueError) as exc:
            print(f"  canonical install failed: {exc}")
            return _result("blocked", mutation=False)
        canonical_present = True
        print(f"  migrated {len(migration_files)} logical project artifact(s) atomically; "
              "legacy roots preserved read-only")
        return _result("committed", mutation=True)
    if canonical_present and legacy_present:
        candidates = _migration_candidates(target)
        # Preflight ALL conflicts before any mutation. A divergent artifact must
        # never be silently resolved, and the presence of any conflict must not
        # commit even the non-conflicting artifacts (F10b).
        conflicts = []
        safe = {}  # logical -> source path (identical across legacy, absent canonical)
        for logical, paths in sorted(candidates.items()):
            canonical = target / ".maika" / logical
            all_paths = ([canonical] if canonical.is_file() else []) + paths
            hashes = [hashlib.sha256(path.read_bytes()).hexdigest() for path in all_paths]
            if len(set(hashes)) == 1:
                if not canonical.is_file():
                    safe[logical] = paths[0]
                continue
            conflicts.append({
                "logical_artifact": logical,
                "candidates": [path.relative_to(target).as_posix() for path in all_paths],
                "hashes": hashes,
                "decision_required": True,
            })
        if conflicts:
            # Report-only: write the conflict diagnostic; mutate NO project data.
            import yaml
            report = target / ".maika/runtime/migration-conflicts.yaml"
            report.parent.mkdir(parents=True, exist_ok=True)
            report.write_text(yaml.safe_dump({"version": 1, "conflicts": conflicts}, sort_keys=False),
                              encoding="utf-8")
            print(f"  migration blocked by {len(conflicts)} divergent artifact(s); no project data "
                  f"mutated. Resolve then re-run — see {report.relative_to(target).as_posix()}")
            return _result("blocked", mutation=False)
        if not safe:
            print("  nothing to migrate; canonical artifacts already match legacy")
            return _result("no-op", mutation=False)
        staging = Path(tempfile.mkdtemp(prefix="maika-migrate-"))
        backups = Path(tempfile.mkdtemp(prefix="maika-migrate-bak-"))
        try:
            for logical, source in safe.items():
                dest = staging / ".maika" / logical
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, dest)
            plan = build_plan(staging, target, "migration", ".maika")
            journal = Transaction(staging, target, backups).apply(plan)
        finally:
            shutil.rmtree(staging, ignore_errors=True)
            shutil.rmtree(backups, ignore_errors=True)
        print(f"  migrated {len(safe)} logical project artifact(s); legacy roots preserved read-only")
        return _result("committed", mutation=True, transaction_id=journal.get("transaction_id"))
    print("  nothing to migrate")
    return _result("no-op", mutation=False)
