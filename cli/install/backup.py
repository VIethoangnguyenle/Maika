"""Backup and restore of target files a transaction will overwrite or delete.

Backups mirror the target's relative layout under a transaction-scoped backup
root so rollback can restore each file byte-for-byte to its original path.
"""

from __future__ import annotations

import shutil
from pathlib import Path


def backup_file(target_path: Path, backup_root: Path, rel: str) -> Path:
    """Copy an existing target file into the backup root, preserving metadata."""
    dest = backup_root / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(target_path, dest)
    return dest


def restore_file(backup_path: Path, target_path: Path) -> None:
    """Restore a backed-up file to its original target path (byte-for-byte)."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(backup_path, target_path)
