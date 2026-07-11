"""Locked trusted current-session record and active-platform resolution."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import os
from pathlib import Path
import time
from typing import Optional
import uuid

import yaml

from cli.config import project


SESSION_VERSION = 1
SESSION_RELATIVE_PATH = Path(".maika/runtime/current-session.yaml")
TRUSTED_SOURCES = frozenset({"native-hook", "explicit-cli", "verified-launcher"})
DEFAULT_STALE_AFTER_SECONDS = 30 * 60


class SessionError(ValueError):
    pass


class SessionConflictError(SessionError):
    pass


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
    return isinstance(record, dict) and record.get("version") == SESSION_VERSION \
        and record.get("source") in TRUSTED_SOURCES \
        and isinstance(record.get("session_id"), str) and bool(record["session_id"]) \
        and isinstance(record.get("platform"), str)


def load_current_session(project_root: Path) -> Optional[dict]:
    path = Path(project_root) / SESSION_RELATIVE_PATH
    if not path.is_file():
        return None
    try:
        record = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return None
    return record if _trusted(record) else None


@contextmanager
def _session_lock(project_root: Path, timeout_seconds: float = 5.0):
    lock_path = Path(project_root) / ".maika/runtime/current-session.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout_seconds
    fd = None
    while fd is None:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.write(fd, f"{os.getpid()}\n".encode("ascii"))
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise SessionError("timed out acquiring current-session lock")
            time.sleep(0.02)
    try:
        yield
    finally:
        os.close(fd)
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


def record_session(
    project_root: Path,
    platform_key: str,
    *,
    source: str,
    session_id: Optional[str] = None,
    stale_after_seconds: int = DEFAULT_STALE_AFTER_SECONDS,
) -> dict:
    if source not in TRUSTED_SOURCES:
        raise SessionError(f"untrusted session source: {source}")
    cfg = project.load(Path(project_root))
    if platform_key not in cfg["platforms"]["enabled"]:
        raise SessionError(f"platform {platform_key} is not enabled for this project")
    session_id = session_id or str(uuid.uuid4())
    path = Path(project_root) / SESSION_RELATIVE_PATH
    with _session_lock(Path(project_root)):
        existing = load_current_session(Path(project_root))
        if existing and _fresh(existing, stale_after_seconds) \
                and existing["platform"] != platform_key and source != "explicit-cli":
            raise SessionConflictError(
                f"active {existing['platform']} session conflicts with {platform_key}; "
                "use explicit --platform to select the intended host"
            )
        now = _now().isoformat()
        started = existing.get("started_at") if existing \
            and existing["platform"] == platform_key else now
        record = {
            "version": SESSION_VERSION,
            "session_id": session_id,
            "platform": platform_key,
            "source": source,
            "started_at": started,
            "last_seen_at": now,
        }
        tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        tmp.write_text(yaml.safe_dump(record, sort_keys=False), encoding="utf-8")
        os.replace(tmp, path)
        return record


def resolve_active_platform(
    project_root: Path,
    *,
    explicit_platform: Optional[str] = None,
    hook_platform: Optional[str] = None,
    stale_after_seconds: int = DEFAULT_STALE_AFTER_SECONDS,
) -> tuple[str, str]:
    """Resolve explicit → hook → fresh trusted session → primary, or block."""
    cfg = project.load(Path(project_root))
    enabled = cfg["platforms"]["enabled"]
    if explicit_platform is not None:
        if explicit_platform not in enabled:
            raise SessionError(f"explicit platform {explicit_platform} is not enabled")
        return explicit_platform, "explicit-cli"
    if hook_platform is not None:
        if hook_platform not in enabled:
            raise SessionError(f"hook platform {hook_platform} is not enabled")
        return hook_platform, "native-hook"
    current = load_current_session(Path(project_root))
    if current and current["platform"] in enabled and _fresh(current, stale_after_seconds):
        return current["platform"], "current-session"
    primary = cfg["platforms"]["primary"]
    if primary in enabled:
        return primary, "primary"
    raise SessionError("cannot resolve runtime platform; enable a platform or pass --platform")
