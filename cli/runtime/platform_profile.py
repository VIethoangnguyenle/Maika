"""Typed, fail-closed per-platform runtime profiles.

Worker commands belong to the host adapter recorded under
``.maika/runtime/platforms``.  Shared workflow policy deliberately has no
platform command data.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Mapping, Optional

import yaml

from cli.config.platforms import adapter_descriptor
from cli.platforms import PLATFORMS, get_platform


PROFILE_VERSION = 1
PROFILE_RELATIVE_DIR = Path(".maika/runtime/platforms")
CAPABILITY_STATES = frozenset({
    "unsupported", "advertised", "detected", "verified", "degraded", "unavailable",
})
WORKER_STRATEGIES = frozenset({"native_subagent", "fresh_process", "inline", "disabled"})
_PLATFORM_KEY = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class PlatformProfileError(ValueError):
    """A runtime profile is absent, untrusted, or structurally invalid."""


@dataclass(frozen=True)
class AdapterProfile:
    enabled: bool
    entrypoint: str
    native_config: Optional[str]


@dataclass(frozen=True)
class WorkerSettings:
    strategy: str
    executable: Optional[str]
    args: tuple[str, ...]
    dangerous_permissions: bool
    timeout_seconds: int


@dataclass(frozen=True)
class PlatformRuntimeProfile:
    version: int
    platform: str
    adapter: AdapterProfile
    detection: Mapping[str, Any]
    capabilities: Mapping[str, str]
    worker: WorkerSettings
    verification: Mapping[str, Any]


def profile_path(project_root: Path, platform_key: str) -> Path:
    _validate_platform_key(platform_key)
    return Path(project_root) / PROFILE_RELATIVE_DIR / f"{platform_key}.yaml"


def _validate_platform_key(platform_key: str) -> None:
    if not isinstance(platform_key, str) or not _PLATFORM_KEY.fullmatch(platform_key):
        raise PlatformProfileError(f"invalid platform key: {platform_key!r}")
    if platform_key not in PLATFORMS:
        raise PlatformProfileError(f"unknown platform key: {platform_key}")


def _mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise PlatformProfileError(f"{field} must be a mapping")
    return value


def _validate_executable(value: Any, strategy: str) -> Optional[str]:
    if value is None and strategy in {"inline", "disabled", "native_subagent"}:
        return None
    if not isinstance(value, str) or not value.strip() or "\x00" in value or "\n" in value:
        raise PlatformProfileError("worker executable must be one non-empty argv value")
    return value


def validate_platform_runtime_profile(data: Mapping[str, Any], requested_platform: str) -> PlatformRuntimeProfile:
    _validate_platform_key(requested_platform)
    if data.get("version") != PROFILE_VERSION:
        raise PlatformProfileError(f"unsupported platform runtime profile version: {data.get('version')!r}")
    platform_key = data.get("platform")
    if platform_key != requested_platform:
        raise PlatformProfileError(
            f"profile platform {platform_key!r} does not match requested platform {requested_platform!r}"
        )

    adapter = _mapping(data.get("adapter"), "adapter")
    if not isinstance(adapter.get("enabled"), bool):
        raise PlatformProfileError("adapter.enabled must be boolean")
    if not isinstance(adapter.get("entrypoint"), str) or not adapter["entrypoint"]:
        raise PlatformProfileError("adapter.entrypoint must be non-empty")

    capabilities = _mapping(data.get("capabilities", {}), "capabilities")
    for name, state in capabilities.items():
        if not isinstance(name, str) or state not in CAPABILITY_STATES:
            raise PlatformProfileError(f"invalid capability state for {name}: {state!r}")

    worker = _mapping(data.get("worker"), "worker")
    strategy = worker.get("strategy")
    if strategy not in WORKER_STRATEGIES:
        raise PlatformProfileError(f"unknown worker strategy: {strategy!r}")
    executable = _validate_executable(worker.get("executable"), strategy)
    args = worker.get("args", [])
    if not isinstance(args, list) or any(not isinstance(arg, str) or "\x00" in arg for arg in args):
        raise PlatformProfileError("worker.args must be a list of argv strings")
    dangerous = worker.get("dangerous_permissions", False)
    if not isinstance(dangerous, bool):
        raise PlatformProfileError("worker.dangerous_permissions must be boolean")
    timeout = worker.get("timeout_seconds", 900)
    if not isinstance(timeout, int) or isinstance(timeout, bool) or timeout <= 0:
        raise PlatformProfileError("worker.timeout_seconds must be a positive integer")

    native_config = adapter.get("native_config")
    if native_config is not None and not isinstance(native_config, str):
        raise PlatformProfileError("adapter.native_config must be a string or null")
    return PlatformRuntimeProfile(
        version=PROFILE_VERSION,
        platform=platform_key,
        adapter=AdapterProfile(adapter["enabled"], adapter["entrypoint"], native_config),
        detection=dict(_mapping(data.get("detection", {}), "detection")),
        capabilities=dict(capabilities),
        worker=WorkerSettings(strategy, executable, tuple(args), dangerous, timeout),
        verification=dict(_mapping(data.get("verification", {}), "verification")),
    )


def build_platform_runtime_profile(platform_key: str, *, enabled: bool = True) -> dict:
    """Build the conservative scaffold profile for one adapter.

    Scaffold data is only advertised.  Probe/verification phases may promote
    facts later; binary existence is never invented here.
    """
    _validate_platform_key(platform_key)
    platform = get_platform(platform_key)
    descriptor = adapter_descriptor(platform_key)
    executable = platform.worker_binary
    strategy = "fresh_process" if executable else "inline"
    args = [*platform.worker_base_args, "{prompt_file}"] if executable else []
    capabilities = {
        name: ("advertised" if advertised else "unavailable")
        for name, advertised in platform.capabilities.items()
    }
    data = {
        "version": PROFILE_VERSION,
        "platform": platform_key,
        "adapter": {
            "enabled": enabled,
            "entrypoint": descriptor["entrypoint"],
            "native_config": descriptor["hook_config"],
        },
        "detection": {
            "binary": {"path": None, "version": None, "found": False, "version_supported": False},
            "authentication": {"state": "unavailable"},
            "last_detected_at": None,
        },
        "capabilities": capabilities,
        "worker": {
            "strategy": strategy,
            "executable": executable,
            "args": args,
            "dangerous_permissions": False,
            "timeout_seconds": 900,
        },
        "verification": {
            "hook_smoke_test": "not-run",
            "worker_smoke_test": "not-run",
            "last_verified_at": None,
        },
    }
    validate_platform_runtime_profile(data, platform_key)
    return data


def write_platform_runtime_profile(project_root: Path, platform_key: str, *, enabled: bool = True) -> Path:
    path = profile_path(project_root, platform_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# Maika platform runtime profile\n"
        + yaml.safe_dump(build_platform_runtime_profile(platform_key, enabled=enabled), sort_keys=False),
        encoding="utf-8",
    )
    return path


def load_platform_runtime_profile(project_root: Path, platform_key: str) -> PlatformRuntimeProfile:
    path = profile_path(project_root, platform_key)
    if not path.is_file():
        raise PlatformProfileError(
            f"missing runtime profile for {platform_key}; run `maika platform enable {platform_key}` "
            "or `maika repair --all-safe`"
        )
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise PlatformProfileError(f"cannot read runtime profile for {platform_key}: {exc}") from exc
    if not isinstance(raw, dict):
        raise PlatformProfileError(f"runtime profile for {platform_key} must be a mapping")
    return validate_platform_runtime_profile(raw, platform_key)
