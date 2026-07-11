"""Per-session registry with active-platform resolution (F8 redesign).

Each session is stored as `.maika/runtime/sessions/<platform>/<session_id>.yaml`.
An optional `.maika/runtime/active-platform.yaml` pins the active platform
explicitly.  Multiple sessions coexist; no cross-platform conflict.
"""

from __future__ import annotations

import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import uuid

import yaml

from cli.config import project

SESSION_VERSION = 1
SESSIONS_RELATIVE_DIR = Path(".maika/runtime/sessions")
ACTIVE_PLATFORM_RELATIVE_PATH = Path(".maika/runtime/active-platform.yaml")
TRUSTED_SOURCES = frozenset({"native-hook", "explicit-cli", "verified-launcher"})
DEFAULT_STALE_AFTER_SECONDS = 30 * 60

_SESSION_ID_RE = re.compile(r"^[A-Za-z0-9._-]+$")


class SessionError(ValueError):
    pass


# ── internal helpers ──────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_time(value) -> Optional[datetime]:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _fresh(record: dict, stale_after_seconds: int) -> bool:
    seen = _parse_time(record.get("last_seen_at"))
    return seen is not None and (_now() - seen).total_seconds() <= stale_after_seconds


def _trusted(record) -> bool:
    return (isinstance(record, dict)
            and record.get("version") == SESSION_VERSION
            and record.get("source") in TRUSTED_SOURCES
            and isinstance(record.get("session_id"), str) and bool(record["session_id"])
            and isinstance(record.get("platform"), str))


def _atomic_write(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(data, encoding="utf-8")
    os.replace(tmp, path)


def _validate_session_id(session_id: str) -> None:
    if not _SESSION_ID_RE.match(session_id):
        raise SessionError(
            f"session_id must match [A-Za-z0-9._-]+; got: {session_id!r}"
        )


def _validate_platform_enabled(project_root: Path, platform_key: str) -> None:
    cfg = project.load(Path(project_root))
    if platform_key not in cfg["platforms"]["enabled"]:
        raise SessionError(
            f"platform {platform_key} is not enabled for this project"
        )


# ── public API ────────────────────────────────────────────────────────────

def record_session(
    project_root,
    platform_key: str,
    *,
    source: str,
    session_id: Optional[str] = None,
    stale_after_seconds: int = DEFAULT_STALE_AFTER_SECONDS,
) -> dict:
    """Write/refresh a per-session file.  No cross-platform conflict."""
    project_root = Path(project_root)
    if source not in TRUSTED_SOURCES:
        raise SessionError(f"untrusted session source: {source}")
    _validate_platform_enabled(project_root, platform_key)
    session_id = session_id or str(uuid.uuid4())
    _validate_session_id(session_id)

    path = project_root / SESSIONS_RELATIVE_DIR / platform_key / f"{session_id}.yaml"

    # Per-session-file lock (O_CREAT|O_EXCL) so concurrent hooks for different
    # sessions never serialize on one global lock or corrupt each other.
    lock_path = path.with_name(path.name + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + 5.0
    fd = None
    while fd is None:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.write(fd, f"{os.getpid()}\n".encode("ascii"))
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise SessionError(f"timed out acquiring session lock: {lock_path}")
            time.sleep(0.02)
    try:
        # Read existing record (if any) to preserve started_at
        existing = None
        if path.is_file():
            try:
                existing = yaml.safe_load(path.read_text(encoding="utf-8"))
            except (OSError, yaml.YAMLError):
                existing = None

        now = _now().isoformat()
        started = now
        if existing and isinstance(existing, dict) and existing.get("session_id") == session_id:
            started = existing.get("started_at", now)

        record = {
            "version": SESSION_VERSION,
            "session_id": session_id,
            "platform": platform_key,
            "source": source,
            "started_at": started,
            "last_seen_at": now,
        }
        _atomic_write(path, yaml.safe_dump(record, sort_keys=False))
    finally:
        os.close(fd)
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass

    return record


def list_sessions(
    project_root,
    *,
    fresh_only: bool = False,
    stale_after_seconds: int = DEFAULT_STALE_AFTER_SECONDS,
) -> list[dict]:
    """Every trusted, well-formed session record across all platforms."""
    project_root = Path(project_root)
    sessions_dir = project_root / SESSIONS_RELATIVE_DIR
    if not sessions_dir.is_dir():
        return []
    cfg = project.load(project_root)
    enabled = set(cfg["platforms"]["enabled"])
    results = []
    for platform_dir in sorted(sessions_dir.iterdir()):
        if not platform_dir.is_dir():
            continue
        for session_file in sorted(platform_dir.iterdir()):
            if session_file.suffix != ".yaml" or session_file.name.endswith(".lock"):
                continue
            try:
                record = yaml.safe_load(session_file.read_text(encoding="utf-8"))
            except (OSError, yaml.YAMLError):
                continue
            if not _trusted(record):
                continue
            if record.get("platform") not in enabled:
                continue
            is_fresh = _fresh(record, stale_after_seconds)
            record["fresh"] = is_fresh
            if fresh_only and not is_fresh:
                continue
            results.append(record)
    return results


def fresh_platforms(
    project_root,
    stale_after_seconds: int = DEFAULT_STALE_AFTER_SECONDS,
) -> set[str]:
    """Set of enabled platforms with >=1 fresh trusted session."""
    sessions = list_sessions(
        project_root, fresh_only=True, stale_after_seconds=stale_after_seconds,
    )
    return {s["platform"] for s in sessions}


def prune_sessions(
    project_root,
    stale_after_seconds: int = DEFAULT_STALE_AFTER_SECONDS,
) -> list[str]:
    """Delete stale + malformed session files (and empty platform dirs).

    Return removed relative paths, sorted.
    """
    project_root = Path(project_root)
    sessions_dir = project_root / SESSIONS_RELATIVE_DIR
    if not sessions_dir.is_dir():
        return []
    removed = []
    for platform_dir in sorted(sessions_dir.iterdir()):
        if not platform_dir.is_dir():
            continue
        for session_file in sorted(platform_dir.iterdir()):
            if session_file.name.endswith(".lock"):
                continue
            if session_file.suffix != ".yaml":
                # not a session file — skip silently
                continue
            remove = False
            try:
                record = yaml.safe_load(session_file.read_text(encoding="utf-8"))
            except (OSError, yaml.YAMLError):
                remove = True
            else:
                if not _trusted(record):
                    remove = True
                elif not _fresh(record, stale_after_seconds):
                    remove = True
            if remove:
                try:
                    session_file.unlink()
                except OSError:
                    pass
                removed.append(str(session_file.relative_to(project_root)))
        # Remove empty platform dirs
        try:
            remaining = list(platform_dir.iterdir())
            if not remaining:
                platform_dir.rmdir()
        except OSError:
            pass
    return sorted(removed)


def set_active_platform(project_root, platform_key: str) -> dict:
    """Write active-platform.yaml.  Validate enabled."""
    project_root = Path(project_root)
    _validate_platform_enabled(project_root, platform_key)
    record = {
        "version": 1,
        "platform": platform_key,
        "set_at": _now().isoformat(),
    }
    path = project_root / ACTIVE_PLATFORM_RELATIVE_PATH
    _atomic_write(path, yaml.safe_dump(record, sort_keys=False))
    return record


def clear_active_platform(project_root) -> bool:
    """Remove active-platform.yaml if present; return whether it existed."""
    path = Path(project_root) / ACTIVE_PLATFORM_RELATIVE_PATH
    if path.is_file():
        try:
            path.unlink()
        except FileNotFoundError:
            return False
        return True
    return False


def load_active_platform(project_root) -> Optional[str]:
    """Read active-platform.yaml; return platform iff well-formed AND enabled."""
    project_root = Path(project_root)
    path = project_root / ACTIVE_PLATFORM_RELATIVE_PATH
    if not path.is_file():
        return None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return None
    if not isinstance(data, dict) or data.get("version") != 1:
        return None
    platform = data.get("platform")
    if not isinstance(platform, str):
        return None
    cfg = project.load(project_root)
    if platform not in cfg["platforms"]["enabled"]:
        return None
    return platform


def resolve_active_platform(
    project_root,
    *,
    explicit_platform: Optional[str] = None,
    hook_platform: Optional[str] = None,
    stale_after_seconds: int = DEFAULT_STALE_AFTER_SECONDS,
) -> tuple[str, str]:
    """Resolution order: explicit → hook → active-platform → fresh → primary → block."""
    project_root = Path(project_root)
    cfg = project.load(project_root)
    enabled = cfg["platforms"]["enabled"]

    # 1. explicit
    if explicit_platform is not None:
        if explicit_platform not in enabled:
            raise SessionError(
                f"explicit platform {explicit_platform} is not enabled"
            )
        return explicit_platform, "explicit-cli"

    # 2. hook
    if hook_platform is not None:
        if hook_platform not in enabled:
            raise SessionError(
                f"hook platform {hook_platform} is not enabled"
            )
        return hook_platform, "native-hook"

    # 3. active-platform file
    active = load_active_platform(project_root)
    if active is not None:
        return active, "active-platform"

    # 4. fresh sessions
    fp = fresh_platforms(project_root, stale_after_seconds=stale_after_seconds)
    if len(fp) == 1:
        return next(iter(fp)), "current-session"
    if len(fp) > 1:
        raise SessionError(
            f"ambiguous active platform: {sorted(fp)}; pass --platform"
        )

    # 5. primary
    primary = cfg["platforms"]["primary"]
    if primary in enabled:
        return primary, "primary"

    # 6. block
    raise SessionError(
        "cannot resolve runtime platform; enable a platform or pass --platform"
    )
