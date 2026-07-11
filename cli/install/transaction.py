"""Transactional apply engine for install plans.

Applies a planner action list to the target so that any failure restores the
exact pre-operation state:

- preflight validates every source before the first target write;
- files a write will overwrite (and every deleted file) are backed up first;
- writes go through a same-directory temp file + ``os.replace`` (atomic);
- a journal records applied actions and directories the engine created;
- on any error, rollback runs in reverse: created files removed, backed-up
  files restored, and directories the engine created are removed when empty.

Project-owned paths are never replacement/delete targets (defense in depth;
the planner already excludes them).
"""

from __future__ import annotations

import os
import re
import json
import shutil
from pathlib import Path
from typing import List

import yaml

from cli.install import backup, ownership

_WRITE_KINDS = {"create", "replace", "managed_markdown", "merge_json",
                "write_yaml", "metadata_update"}
_DELETE_KINDS = {"delete_framework_file", "delete_file"}
_SUPPORTED_KINDS = _WRITE_KINDS | _DELETE_KINDS | {
    "create_directory", "delete_directory", "remove_managed_block",
    "remove_namespaced_json_node", "migrate_file",
}


def _atomic_write(dest: Path, data: bytes, mode_src: Path | None = None) -> None:
    """Write bytes to dest via a same-directory temp file + os.replace."""
    tmp = dest.with_name(dest.name + ".maika-tmp")
    try:
        with open(tmp, "wb") as handle:
            handle.write(data)
        if mode_src is not None:
            shutil.copystat(mode_src, tmp)
        os.replace(tmp, dest)
    finally:
        if tmp.exists():
            tmp.unlink()


class Transaction:
    def __init__(self, staging: Path, target: Path, backup_root: Path):
        self.staging = Path(staging)
        self.target = Path(target)
        self.backup_root = Path(backup_root)
        self._applied: List[dict] = []
        self._created_dirs: List[Path] = []
        self._backups: dict[str, Path] = {}
        self.transaction_id: str | None = None
        self.journal_path: Path | None = None
        self._journal: dict = {}
        self._operational_dirs: List[Path] = []

    # ─── preflight ───

    def _preflight(self, plan: dict) -> None:
        for action in plan["actions"]:
            rel, kind, own = action["path"], action["kind"], action.get("ownership")
            if kind not in _SUPPORTED_KINDS:
                raise ValueError(f"unsupported transaction action: {kind}")
            if own == ownership.PROJECT and kind in {"replace", "delete_framework_file", "delete_file", "delete_directory"} \
                    and not action.get("explicit_project_delete"):
                raise ValueError(f"refusing to {kind} project-owned path: {rel}")
            if kind in _WRITE_KINDS and not (self.staging / rel).exists():
                raise FileNotFoundError(f"missing staged source for {kind}: {rel}")
            if kind == "migrate_file" and not (self.target / action.get("source_path", "")).is_file():
                raise FileNotFoundError(f"missing migration source: {action.get('source_path')}")

    # ─── apply ───

    def apply(self, plan: dict, *, dry_run: bool = False) -> dict:
        self._preflight(plan)
        journal = {"operation": plan.get("operation"), "dry_run": dry_run, "applied": []}
        if dry_run:
            return journal
        try:
            self._begin_journal(plan)
            self._backup_preexisting(plan)
            for action in plan["actions"]:
                self._journal["pending"] = action
                self._persist_journal()
                self._execute(action)
                self._journal["applied"] = list(self._applied)
                self._journal["pending"] = None
                self._persist_journal()
        except BaseException:
            if self._applied:
                self._rollback()
            self._cleanup_operational_state()
            raise
        self._journal["status"] = "committed"
        self._journal["applied"] = list(self._applied)
        self._persist_journal()
        shutil.rmtree(self.backup_root, ignore_errors=True)
        journal["applied"] = list(self._applied)
        journal["transaction_id"] = self.transaction_id
        journal["journal_path"] = self.journal_path.relative_to(self.target).as_posix()
        return journal

    def _begin_journal(self, plan: dict) -> None:
        transaction_root = self.target / ".maika-transactions"
        tx_dir = transaction_root / "journals"
        backup_base = transaction_root / "backups"
        for directory in (self.target, transaction_root, tx_dir, backup_base):
            if not directory.exists():
                directory.mkdir()
                self._operational_dirs.append(directory)
        numbers = []
        for path in tx_dir.glob("*.yaml"):
            match = re.match(r"^(\d+)-", path.name)
            if match:
                numbers.append(int(match.group(1)))
        operation = re.sub(r"[^a-z0-9-]", "-", str(plan.get("operation") or "operation").lower())
        self.transaction_id = f"{max(numbers, default=0) + 1:06d}-{operation}"
        self.journal_path = tx_dir / f"{self.transaction_id}.yaml"
        self.backup_root = backup_base / self.transaction_id
        preexisting = {}
        for action in plan["actions"]:
            path = self.target / action["path"]
            preexisting[action["path"]] = "directory" if path.is_dir() else "file" if path.exists() else "absent"
        self._journal = {
            "version": 1, "transaction_id": self.transaction_id,
            "operation": plan.get("operation"), "status": "preparing",
            "actions": plan["actions"], "preexisting": preexisting, "applied": [],
        }
        self._persist_journal()

    def _persist_journal(self) -> None:
        # JSON is a strict YAML subset and is substantially cheaper to rewrite
        # at every crash boundary for large scaffold plans.
        data = (json.dumps(self._journal, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        _atomic_write(self.journal_path, data)

    def _backup_preexisting(self, plan: dict) -> None:
        for action in plan["actions"]:
            rel = action["path"]
            source = self.target / rel
            if source.is_file():
                self._backups[rel] = backup.backup_file(source, self.backup_root, rel)
            elif source.is_dir():
                dest = self.backup_root / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(source, dest)
                self._backups[rel] = dest
        self._journal["status"] = "applying"
        self._persist_journal()

    def _execute(self, action: dict) -> None:
        rel, kind = action["path"], action["kind"]
        dest = self.target / rel
        if kind in _DELETE_KINDS:
            if dest.exists():
                dest.unlink()
                self._applied.append(action)
            return
        if kind == "create_directory":
            if not dest.exists():
                self._ensure_parents(dest / "placeholder")
                dest.mkdir(exist_ok=True)
                self._created_dirs.append(dest)
                self._applied.append(action)
            return
        if kind == "delete_directory":
            if dest.is_dir():
                shutil.rmtree(dest)
                self._applied.append(action)
            return
        if kind == "migrate_file":
            source = self.target / action["source_path"]
            self._ensure_parents(dest)
            _atomic_write(dest, source.read_bytes(), mode_src=source)
            self._applied.append(action)
            return
        if kind in {"remove_managed_block", "remove_namespaced_json_node"}:
            if not dest.is_file():
                return
            from cli.scaffold import remove_maika_json_entry, strip_managed_markdown
            if kind == "remove_managed_block":
                data = strip_managed_markdown(dest.read_text(encoding="utf-8")).encode("utf-8")
            else:
                import json
                cleaned = remove_maika_json_entry(json.loads(dest.read_text(encoding="utf-8")))
                data = (json.dumps(cleaned, indent=2) + "\n").encode("utf-8")
            _atomic_write(dest, data, mode_src=dest)
            self._applied.append(action)
            return
        # write kinds
        existed = dest.exists()
        self._ensure_parents(dest)
        _atomic_write(dest, (self.staging / rel).read_bytes(), mode_src=self.staging / rel)
        self._applied.append(action)

    def _ensure_parents(self, dest: Path) -> None:
        missing: List[Path] = []
        parent = dest.parent
        while not parent.exists():
            missing.append(parent)
            parent = parent.parent
        for directory in reversed(missing):  # top-down
            directory.mkdir()
            self._created_dirs.append(directory)

    # ─── rollback ───

    def _rollback(self) -> None:
        for action in reversed(self._applied):
            rel, kind = action["path"], action["kind"]
            dest = self.target / rel
            if rel in self._backups:
                source = self._backups[rel]
                if source.is_dir():
                    if dest.exists():
                        shutil.rmtree(dest)
                    shutil.copytree(source, dest)
                else:
                    backup.restore_file(source, dest)
            else:  # newly created file
                if dest.is_dir():
                    shutil.rmtree(dest)
                elif dest.exists():
                    dest.unlink()
        for directory in reversed(self._created_dirs):
            try:
                directory.rmdir()  # only removes if empty
            except OSError:
                pass

    def _cleanup_operational_state(self) -> None:
        if self.journal_path and self.journal_path.exists():
            self.journal_path.unlink()
        shutil.rmtree(self.backup_root, ignore_errors=True)
        for directory in reversed(self._operational_dirs):
            try:
                directory.rmdir()
            except OSError:
                pass


def repair_transaction(target: Path, transaction_id: str) -> dict:
    """Roll back a journal left in preparing/applying state after interruption."""
    if not re.fullmatch(r"\d{6}-[a-z0-9-]+", transaction_id):
        raise ValueError("invalid transaction id")
    target = Path(target)
    journal_path = target / ".maika-transactions/journals" / f"{transaction_id}.yaml"
    if not journal_path.is_file():
        legacy = target / ".maika/runtime/transactions" / f"{transaction_id}.yaml"
        journal_path = legacy if legacy.is_file() else journal_path
    if not journal_path.is_file():
        raise FileNotFoundError(f"transaction journal not found: {transaction_id}")
    journal = yaml.safe_load(journal_path.read_text(encoding="utf-8")) or {}
    if journal.get("status") == "committed":
        return journal
    backup_root = target / ".maika-transactions/backups" / transaction_id
    if not backup_root.exists():
        backup_root = target / ".maika/runtime/backups" / transaction_id
    preexisting = journal.get("preexisting") or {}
    applied = list(journal.get("applied") or [])
    if journal.get("pending"):
        applied.append(journal["pending"])
    if not applied and "applied" not in journal:  # compatibility with early journals
        applied = list(journal.get("actions") or [])
    for action in reversed(applied):
        rel = action["path"]
        dest = target / rel
        state = preexisting.get(rel, "absent")
        source = backup_root / rel
        if state == "file" and source.is_file():
            backup.restore_file(source, dest)
        elif state == "directory" and source.is_dir():
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(source, dest)
        elif state == "absent":
            if dest.is_dir():
                shutil.rmtree(dest)
            elif dest.exists():
                dest.unlink()
    journal["status"] = "rolled_back"
    _atomic_write(journal_path, yaml.safe_dump(journal, sort_keys=False).encode("utf-8"))
    return journal
