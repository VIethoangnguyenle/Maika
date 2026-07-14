"""Inspect and explicitly select the current host runtime."""

from dataclasses import asdict
import json
from pathlib import Path

from cli.runtime.session import (
    SessionError,
    resolve_active_platform,
    set_active_platform,
    clear_active_platform,
    list_sessions,
    prune_sessions,
)
from cli.runtime.worker_resolver import WorkerResolutionError, resolve_worker_profile


def run_runtime(
    action: str,
    target_dir: str = ".",
    platform_key: str | None = None,
    *,
    prune: bool = False,
) -> int:
    target = Path(target_dir).resolve()
    try:
        if action == "set-platform":
            if not platform_key:
                raise SessionError("runtime set-platform requires a platform")
            set_active_platform(target, platform_key)
            print(json.dumps({"platform": platform_key, "source": "active-platform"}))
            return 0
        if action == "clear-platform":
            cleared = clear_active_platform(target)
            print(json.dumps({"cleared": cleared}))
            return 0
        if action == "sessions":
            if prune:
                removed = prune_sessions(target)
                print(json.dumps({"pruned": removed}))
            else:
                sessions = list_sessions(target)
                print(json.dumps({"sessions": sessions}))
            return 0
        if action == "current":
            platform, source = resolve_active_platform(target)
            print(json.dumps({"platform": platform, "source": source}))
            return 0
        if action == "worker-profile":
            platform, source = resolve_active_platform(
                target, explicit_platform=platform_key,
            )
            payload = asdict(resolve_worker_profile(target, platform))
            payload["selection_source"] = source
            print(json.dumps(payload, ensure_ascii=False))
            return 0
        raise SessionError(f"unknown runtime action: {action}")
    except (SessionError, WorkerResolutionError) as exc:
        print(f"Refused: {exc}")
        return 2
