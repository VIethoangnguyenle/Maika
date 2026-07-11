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
import shutil
from pathlib import Path
from typing import List

from cli.install import backup, ownership

_WRITE_KINDS = {"create", "replace", "managed_markdown", "merge_json"}


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

    # ─── preflight ───

    def _preflight(self, plan: dict) -> None:
        for action in plan["actions"]:
            rel, kind, own = action["path"], action["kind"], action.get("ownership")
            if own == ownership.PROJECT and kind in {"replace", "delete_framework_file"}:
                raise ValueError(f"refusing to {kind} project-owned path: {rel}")
            if kind in _WRITE_KINDS and not (self.staging / rel).exists():
                raise FileNotFoundError(f"missing staged source for {kind}: {rel}")

    # ─── apply ───

    def apply(self, plan: dict, *, dry_run: bool = False) -> dict:
        self._preflight(plan)
        journal = {"operation": plan.get("operation"), "dry_run": dry_run, "applied": []}
        if dry_run:
            return journal
        try:
            for action in plan["actions"]:
                self._execute(action)
        except BaseException:
            self._rollback()
            raise
        journal["applied"] = list(self._applied)
        return journal

    def _execute(self, action: dict) -> None:
        rel, kind = action["path"], action["kind"]
        dest = self.target / rel
        if kind == "delete_framework_file":
            if dest.exists():
                self._backups[rel] = backup.backup_file(dest, self.backup_root, rel)
                dest.unlink()
                self._applied.append(action)
            return
        # write kinds
        existed = dest.exists()
        if existed:
            self._backups[rel] = backup.backup_file(dest, self.backup_root, rel)
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
            if kind == "delete_framework_file" or rel in self._backups:
                backup.restore_file(self._backups[rel], dest)
            else:  # newly created file
                if dest.exists():
                    dest.unlink()
        for directory in reversed(self._created_dirs):
            try:
                directory.rmdir()  # only removes if empty
            except OSError:
                pass
