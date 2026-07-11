"""Inspect and explicitly select the current host runtime."""

from dataclasses import asdict
import json
from pathlib import Path

from cli.runtime.session import SessionError, record_session, resolve_active_platform
from cli.runtime.worker_resolver import WorkerResolutionError, resolve_worker_profile


def run_runtime(action: str, target_dir: str = ".", platform_key: str | None = None) -> int:
    target = Path(target_dir).resolve()
    try:
        if action == "set-platform":
            if not platform_key:
                raise SessionError("runtime set-platform requires a platform")
            record_session(target, platform_key, source="explicit-cli",
                           session_id=f"explicit-{platform_key}")
            print(json.dumps({"platform": platform_key, "source": "explicit-cli"}))
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
