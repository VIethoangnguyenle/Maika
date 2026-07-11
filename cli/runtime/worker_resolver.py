"""The single worker-strategy policy used by runtime, doctor, and smoke tests."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import Any, Mapping, Optional

from cli.platforms import PLATFORMS, get_platform
from cli.runtime.executor import (  # canonical strategy constants + selectability
    DISABLED,
    FRESH_PROCESS,
    STRATEGIES,
    strategy_is_selectable,
)
from cli.runtime.platform_profile import (
    PlatformProfileError,
    load_platform_runtime_profile,
)


_OVERRIDE_FIELDS = frozenset({
    "platform", "strategy", "executable", "args", "timeout_seconds",
    "dangerous_permissions", "reason",
})


class WorkerResolutionError(ValueError):
    """No safe worker can be selected from the trusted runtime facts."""


@dataclass(frozen=True)
class WorkerProfile:
    platform: str
    strategy: str
    executable: Optional[str]
    args: tuple[str, ...]
    timeout_seconds: int
    dangerous_permissions: bool
    reason: str


def validate_worker_profile(profile: WorkerProfile) -> WorkerProfile:
    if profile.platform not in PLATFORMS:
        raise WorkerResolutionError(f"unknown worker platform: {profile.platform}")
    if profile.strategy not in STRATEGIES:
        raise WorkerResolutionError(f"unknown worker strategy: {profile.strategy}")
    if profile.strategy == FRESH_PROCESS and (
        not isinstance(profile.executable, str) or not profile.executable.strip()
    ):
        raise WorkerResolutionError("fresh_process requires an executable")
    if profile.executable is not None and ("\x00" in profile.executable or "\n" in profile.executable):
        raise WorkerResolutionError("worker executable must be one safe argv value")
    if any(not isinstance(arg, str) or "\x00" in arg for arg in profile.args):
        raise WorkerResolutionError("worker args must be safe argv strings")
    if "{prompt}" in profile.args or any("{prompt}" in arg for arg in profile.args):
        raise WorkerResolutionError("prompt text argv is forbidden; use {prompt_file}")
    if profile.strategy == FRESH_PROCESS and not any("{prompt_file}" in arg for arg in profile.args):
        raise WorkerResolutionError("fresh_process args must contain {prompt_file}")
    if not isinstance(profile.timeout_seconds, int) or isinstance(profile.timeout_seconds, bool) \
            or profile.timeout_seconds <= 0:
        raise WorkerResolutionError("worker timeout must be a positive integer")
    return profile


def _override_profile(platform_key: str, override: Mapping[str, Any]) -> WorkerProfile:
    unknown = set(override) - _OVERRIDE_FIELDS
    if unknown:
        raise WorkerResolutionError(f"unknown override fields: {', '.join(sorted(unknown))}")
    bound = override.get("platform", platform_key)
    if bound != platform_key:
        raise WorkerResolutionError(
            f"worker override is bound to {bound}, not requested platform {platform_key}"
        )
    strategy = override.get("strategy", FRESH_PROCESS if override.get("executable") else DISABLED)
    if not strategy_is_selectable(strategy):
        raise WorkerResolutionError(
            f"worker override strategy {strategy!r} has no executor this release; "
            "use fresh_process with an executable"
        )
    args = tuple(override.get("args") or ())
    return validate_worker_profile(WorkerProfile(
        platform=platform_key,
        strategy=strategy,
        executable=override.get("executable"),
        args=args,
        timeout_seconds=override.get("timeout_seconds", 900),
        dangerous_permissions=bool(override.get("dangerous_permissions", False)),
        reason=override.get("reason", "trusted explicit worker override"),
    ))


def resolve_worker_profile(
    project_root: Path,
    platform_key: str,
    user_override: Optional[Mapping[str, Any]] = None,
) -> WorkerProfile:
    """Resolve one platform's worker from trusted input and verified facts.

    Explicit overrides are already trusted by the CLI caller and remain bound to
    the requested platform.  Persisted profile facts must be verified before a
    high-trust strategy is selected.
    """
    if platform_key not in PLATFORMS:
        raise WorkerResolutionError(f"unknown platform: {platform_key}")
    if user_override is not None:
        if not isinstance(user_override, Mapping):
            raise WorkerResolutionError("worker override must be a mapping")
        return _override_profile(platform_key, user_override)

    try:
        runtime = load_platform_runtime_profile(Path(project_root), platform_key)
    except PlatformProfileError as exc:
        raise WorkerResolutionError(str(exc)) from exc
    if not runtime.adapter.enabled:
        return WorkerProfile(platform_key, DISABLED, None, (), runtime.worker.timeout_seconds,
                             False, "platform adapter is disabled")

    # native_subagent is advertised-only (no executor callback exists yet), so it
    # is never selected here — doing so would be a shadow strategy (F6).
    binary = runtime.detection.get("binary", {})
    worker_verified = runtime.verification.get("worker_smoke_test") == "pass"
    fresh_verified = runtime.capabilities.get("fresh_session") == "verified"
    if runtime.worker.strategy == FRESH_PROCESS and binary.get("found") \
            and binary.get("version_supported") and fresh_verified and worker_verified:
        return validate_worker_profile(WorkerProfile(
            platform_key, FRESH_PROCESS, runtime.worker.executable, runtime.worker.args,
            runtime.worker.timeout_seconds, runtime.worker.dangerous_permissions,
            "verified fresh-process CLI",
        ))

    # No verified fresh_process worker and no other executable strategy: refuse
    # cleanly (disabled) with actionable remediation rather than advertise an
    # inline fallback that has no executor.
    return validate_worker_profile(WorkerProfile(
        platform_key, DISABLED, None, (), runtime.worker.timeout_seconds,
        False, f"no verified worker; run `maika platform verify {platform_key}`",
    ))


def build_worker_argv(
    profile: WorkerProfile,
    prompt_file: str,
    *,
    context: Optional[Mapping[str, str]] = None,
    command_opt_in: bool = False,
    audit_event_recorded: bool = False,
) -> list[str]:
    """Build portable structured argv.  Callers must execute with shell=False."""
    validate_worker_profile(profile)
    if profile.strategy != FRESH_PROCESS:
        raise WorkerResolutionError(f"strategy {profile.strategy} does not produce process argv")
    values = {"{prompt_file}": str(prompt_file)}
    for key, value in (context or {}).items():
        token = key if key.startswith("{") else "{" + key + "}"
        values[token] = str(value)

    def render(arg: str) -> str:
        result = arg
        for token, value in values.items():
            result = result.replace(token, value)
        if "{" in result or "}" in result:
            raise WorkerResolutionError(f"unknown or unresolved worker placeholder in {arg!r}")
        return result

    argv = [profile.executable, *(render(arg) for arg in profile.args)]
    if profile.dangerous_permissions and command_opt_in:
        if not audit_event_recorded:
            raise WorkerResolutionError("dangerous permission opt-in requires an audit event")
        flag = get_platform(profile.platform).dangerous_permission_flag
        if flag:
            argv.insert(len(argv) - 1, flag)
    return argv


def run_worker_smoke_test(profile: WorkerProfile, prompt_file: Path) -> dict:
    """Run a no-shell worker probe and return structured evidence without raising."""
    try:
        argv = build_worker_argv(profile, str(prompt_file))
        proc = subprocess.run(
            argv, shell=False, capture_output=True, text=True,
            timeout=profile.timeout_seconds, check=False,
        )
        return {"state": "verified" if proc.returncode == 0 else "degraded",
                "returncode": proc.returncode, "output": (proc.stdout or proc.stderr or "")[-2000:]}
    except (OSError, subprocess.TimeoutExpired, WorkerResolutionError) as exc:
        return {"state": "unavailable", "returncode": None, "output": str(exc)}
