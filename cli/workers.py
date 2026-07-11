"""Worker execution strategy selection + safe argv construction.

Selection is capability-driven and explainable. Fresh-process commands are
structured argv (the caller must use ``shell=False``); dangerous permission
flags never appear by default — only on explicit opt-in.
"""

from __future__ import annotations

from typing import List

NATIVE_SUBAGENT = "native_subagent"
FRESH_PROCESS = "fresh_process"
INLINE = "inline"
DISABLED = "disabled"
STRATEGIES = (NATIVE_SUBAGENT, FRESH_PROCESS, INLINE, DISABLED)


def build_fresh_process_argv(platform, prompt_file: str, *, allow_dangerous: bool = False) -> List[str]:
    """Structured argv for a fresh-process worker.

    The prompt file is a single argv element regardless of spaces/metacharacters
    (never shell-interpreted). A dangerous permission flag is appended only when
    the caller explicitly opts in.
    """
    if not platform.worker_binary:
        raise ValueError(f"{platform.name} has no fresh-process worker binary")
    argv = [platform.worker_binary, *platform.worker_base_args]
    if allow_dangerous and platform.dangerous_permission_flag:
        argv.append(platform.dangerous_permission_flag)
    argv.append(prompt_file)
    return argv


def _profile(strategy: str, *, executable=None, args=None, allow_dangerous=False, reason="") -> dict:
    return {
        "strategy": strategy,
        "executable": executable,
        "args": args or [],
        "allow_dangerous": allow_dangerous,
        "reason": reason,
    }


def select_worker_strategy(platform, detection: dict, *, user_choice=None,
                           allow_dangerous: bool = False) -> dict:
    """Pick a worker strategy for a platform given its detection result.

    Order: explicit user choice > verified native subagent > detected fresh-process
    CLI > safe inline fallback.
    """
    if user_choice in STRATEGIES:
        return _profile(user_choice, reason=f"explicit user choice: {user_choice}")

    capabilities = detection.get("capabilities", {})
    if capabilities.get("subagent") == "verified":
        return _profile(NATIVE_SUBAGENT, reason="verified native subagent")

    binary = detection.get("binary", {})
    version = detection.get("version", {})
    if platform.worker_binary and binary.get("found") and version.get("ok"):
        return _profile(
            FRESH_PROCESS,
            executable=platform.worker_binary,
            args=list(platform.worker_base_args),
            allow_dangerous=allow_dangerous,
            reason=f"detected CLI: {platform.worker_binary}",
        )

    return _profile(INLINE, reason="no verified subagent or detected CLI; safe inline fallback")
