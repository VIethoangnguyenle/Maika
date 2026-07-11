"""Tests for worker strategy selection + safe argv construction.

Selection is capability-driven and explainable; fresh-process commands are
structured argv (no shell), and dangerous permission flags never appear by
default — only on explicit opt-in.
"""

from cli.platforms import get_platform
from cli import workers


def _detection(*, binary_found=False, version_ok=False, native="advertised"):
    return {
        "platform": "claude-code",
        "binary": {"found": binary_found, "path": "/usr/bin/claude" if binary_found else None},
        "version": {"ok": version_ok, "raw": "1.0"},
        "capabilities": {"subagent": native},
    }


def test_fresh_process_argv_is_structured_no_shell():
    platform = get_platform("claude-code")
    tricky = "/tmp/pr ompt; rm -rf x.txt"  # spaces + shell metacharacters
    argv = workers.build_fresh_process_argv(platform, tricky)
    assert isinstance(argv, list)
    assert argv[0] == platform.worker_binary
    # The prompt path is a single argv element — never split or shell-interpreted.
    assert tricky in argv
    assert argv.count(tricky) == 1


def test_no_dangerous_flag_by_default():
    platform = get_platform("claude-code")
    argv = workers.build_fresh_process_argv(platform, "/tmp/p.txt")
    assert not any("dangerous" in tok.lower() or "bypass" in tok.lower() for tok in argv)


def test_dangerous_flag_only_when_opted_in():
    platform = get_platform("claude-code")
    argv = workers.build_fresh_process_argv(platform, "/tmp/p.txt", allow_dangerous=True)
    assert any("dangerous" in tok.lower() for tok in argv)


def test_select_prefers_verified_native():
    platform = get_platform("claude-code")
    profile = workers.select_worker_strategy(platform, _detection(native="verified", binary_found=True, version_ok=True))
    assert profile["strategy"] == workers.NATIVE_SUBAGENT


def test_detected_native_does_not_select_native():
    # 'detected' (not 'verified') native must not be used as a native subagent.
    platform = get_platform("claude-code")
    profile = workers.select_worker_strategy(platform, _detection(native="detected", binary_found=True, version_ok=True))
    assert profile["strategy"] == workers.FRESH_PROCESS


def test_select_falls_back_to_fresh_process():
    platform = get_platform("claude-code")
    profile = workers.select_worker_strategy(platform, _detection(binary_found=True, version_ok=True))
    assert profile["strategy"] == workers.FRESH_PROCESS
    assert profile["executable"] == "claude"


def test_select_falls_back_to_inline_when_nothing_available():
    platform = get_platform("claude-code")
    profile = workers.select_worker_strategy(platform, _detection(binary_found=False))
    assert profile["strategy"] == workers.INLINE


def test_user_choice_overrides_selection():
    platform = get_platform("claude-code")
    profile = workers.select_worker_strategy(
        platform, _detection(binary_found=True, version_ok=True), user_choice=workers.INLINE)
    assert profile["strategy"] == workers.INLINE


def test_profile_has_explainable_reason():
    platform = get_platform("claude-code")
    profile = workers.select_worker_strategy(platform, _detection(binary_found=False))
    assert profile["reason"]  # non-empty explanation
