"""Stable identity for the exact worker executable that was verified."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
from typing import Optional


def resolve_binary(executable: Optional[str]) -> Optional[Path]:
    if not executable:
        return None
    resolved = shutil.which(executable)
    if not resolved:
        return None
    return Path(resolved).resolve()


def binary_identity(executable: Optional[str], *, version: Optional[str] = None) -> Optional[dict]:
    path = resolve_binary(executable)
    if path is None or not path.is_file():
        return None
    try:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        fingerprint = "sha256:" + digest.hexdigest()
        method = "content-sha256"
    except OSError:
        try:
            stat = path.stat()
        except OSError:
            return None
        material = f"{path}|{stat.st_dev}|{stat.st_ino}|{stat.st_size}|{stat.st_mtime_ns}"
        fingerprint = "sha256:" + hashlib.sha256(material.encode()).hexdigest()
        method = "stat-sha256"
    return {
        "path": os.path.normcase(str(path)),
        "version": version,
        "fingerprint": fingerprint,
        "fingerprint_method": method,
    }


def identities_match(left: object, right: object) -> bool:
    if not isinstance(left, dict) or not isinstance(right, dict):
        return False
    return all(left.get(key) == right.get(key) for key in ("path", "fingerprint"))
