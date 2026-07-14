"""Small worktree snapshots used by worker verification."""

from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess


def snapshot_worktree(project_root: Path) -> dict:
    root = Path(project_root).resolve()
    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain=v1", "--untracked-files=all"],
            cwd=root, capture_output=True, text=True, timeout=10, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        proc = None
    if proc is not None and proc.returncode == 0:
        return {"method": "git-status", "fingerprint": proc.stdout}

    digest = hashlib.sha256()
    ignored = {".git", "__pycache__", ".pytest_cache"}
    for path in sorted(p for p in root.rglob("*") if p.is_file() and not ignored.intersection(p.parts)):
        try:
            stat = path.stat()
        except OSError:
            continue
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(f"\0{stat.st_size}\0{stat.st_mtime_ns}".encode())
    return {"method": "filesystem-metadata", "fingerprint": digest.hexdigest()}
