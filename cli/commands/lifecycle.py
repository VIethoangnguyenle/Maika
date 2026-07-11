"""maika migrate / repair / uninstall — lifecycle commands (W9).

All mutation reuses the W2 transaction engine (delete plan → Transaction), the
W3 shared-host strip, and the W5 doctor findings — no parallel mutator. User
data (knowledge, changes, archive, loops, local config) is preserved by default;
purge and legacy cleanup require explicit confirmation.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import Optional

from cli.install import ownership
from cli.install.transaction import Transaction
from cli.scaffold import (
    load_resolved_config,
    remove_maika_json_entry,
    strip_managed_markdown,
)

_SHARED_HOST = ("AGENTS.md", "CLAUDE.md", ".claude/settings.json",
                ".codex/hooks.json", ".agents/hooks.json")
_LEGACY_ROOTS = (".maika", ".agents", ".claude")


def _framework_root(target: Path) -> str:
    return (load_resolved_config(target) or {}).get("framework_root", ".maika")


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


def _strip_shared_host(target: Path) -> None:
    for rel in _SHARED_HOST:
        path = target / rel
        if not path.exists():
            continue
        if rel.endswith(".json"):
            cleaned = remove_maika_json_entry(json.loads(path.read_text(encoding="utf-8")))
            path.write_text(json.dumps(cleaned, indent=2) + "\n", encoding="utf-8")
        else:
            stripped = strip_managed_markdown(path.read_text(encoding="utf-8"))
            if stripped.strip() == "":
                path.unlink()
            else:
                path.write_text(stripped, encoding="utf-8")


def run_uninstall(target_dir: str, purge_project_data: bool = False) -> int:
    target = Path(target_dir).resolve()
    framework_root = _framework_root(target)
    plan = _framework_delete_plan(target, framework_root)

    staging = Path(tempfile.mkdtemp(prefix="maika-uninstall-"))
    backups = Path(tempfile.mkdtemp(prefix="maika-uninstall-bak-"))
    try:
        Transaction(staging, target, backups).apply(plan)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
        shutil.rmtree(backups, ignore_errors=True)

    _strip_shared_host(target)

    if purge_project_data:
        shutil.rmtree(target / framework_root, ignore_errors=True)
        print(f"  Uninstalled Maika and purged project data under {framework_root}")
    else:
        print(f"  Uninstalled Maika core; preserved knowledge/changes/archive/loops "
              f"under {framework_root}")
    return 0


def run_repair(target_dir: str, finding_id: str, maika_root: Optional[str] = None) -> int:
    from cli.commands.doctor import build_setup_findings

    target = Path(target_dir).resolve()
    findings = {f["id"]: f for f in build_setup_findings(target, maika_root=maika_root)}
    finding = findings.get(finding_id)
    if finding is None:
        print(f"  ❌ unknown finding: {finding_id}")
        return 2
    if finding["ok"]:
        print(f"  {finding_id} is already healthy — nothing to repair")
        return 0

    if finding_id == "managed-entrypoint":
        from cli.commands.update import run_update
        run_update(target_dir=str(target), maika_root=maika_root)
        return 0
    if finding_id == "native-hook":
        from cli.commands.platform import run_platform
        from cli.config import project as project_cfg
        primary = project_cfg.load(target)["platforms"]["primary"]
        if primary is None:
            print("  ❌ no primary platform to reinstall")
            return 2
        return run_platform("enable", str(target), primary, maika_root)

    print(f"  no safe automatic repair for {finding_id}; see `maika doctor setup`")
    return 2


def run_migrate(target_dir: str, apply: bool = False) -> int:
    target = Path(target_dir).resolve()
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
        return 0

    if canonical_present:
        # Already on the canonical .maika core. Legacy roots are never silently
        # merged or deleted — they are preserved until the user removes them.
        print("  already on the canonical .maika core; legacy roots preserved")
        return 0
    if legacy_present:
        print("  legacy install detected but no canonical .maika core; "
              "run `maika init` to create the canonical core, then migrate")
        return 1
    print("  nothing to migrate")
    return 0
