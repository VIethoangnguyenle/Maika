"""Canonical worker resolution and argv semantics (A2/B1)."""

from pathlib import Path

import pytest
import yaml

from cli.runtime.platform_profile import write_platform_runtime_profile
from cli.runtime.worker_resolver import (
    DISABLED,
    FRESH_PROCESS,
    WorkerResolutionError,
    build_worker_argv,
    resolve_worker_profile,
)
from cli.runtime.binary_identity import binary_identity
from cli.runtime.platform_profile import profile_fingerprint


def _verified_profile(root: Path, platform: str) -> None:
    path = write_platform_runtime_profile(root, platform)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    executable = root / f"fake-{platform}"
    executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    executable.chmod(0o755)
    data["worker"]["executable"] = str(executable)
    data["profile_fingerprint"] = profile_fingerprint(data)
    data["detection"]["binary"].update({"found": True, "version_supported": True,
                                         "path": str(executable), "version": "1.0"})
    data["capabilities"]["fresh_session"] = "verified"
    data["verification"]["worker_smoke_test"] = "pass"
    data["verification"]["worker_binary"] = binary_identity(str(executable), version="1.0")
    data["verification"]["verified_worker_profile_fingerprint"] = data["profile_fingerprint"]
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def test_verified_fresh_process_uses_profile_for_requested_platform(tmp_path):
    _verified_profile(tmp_path, "codex")
    profile = resolve_worker_profile(tmp_path, "codex")
    assert profile.platform == "codex"
    assert profile.strategy == FRESH_PROCESS
    assert Path(profile.executable).is_absolute()
    assert profile.dangerous_permissions is False


def test_unverified_worker_is_disabled_not_shadow_inline(tmp_path):
    # An advertised-only, unverified profile must resolve to a truthful disabled
    # state with remediation — never a shadow inline strategy with no executor.
    write_platform_runtime_profile(tmp_path, "claude-code")
    profile = resolve_worker_profile(tmp_path, "claude-code")
    assert profile.strategy == DISABLED
    assert profile.executable is None
    assert "maika platform verify claude-code" in profile.reason


def test_override_is_bound_to_requested_platform(tmp_path):
    write_platform_runtime_profile(tmp_path, "codex")
    with pytest.raises(WorkerResolutionError, match="bound to claude-code"):
        resolve_worker_profile(tmp_path, "codex", {
            "platform": "claude-code", "strategy": "fresh_process",
            "executable": "claude", "args": ["{prompt_file}"],
        })


def test_dangerous_permission_requires_all_three_gates(tmp_path):
    _verified_profile(tmp_path, "claude-code")
    path = tmp_path / ".maika/runtime/platforms/claude-code.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["worker"]["dangerous_permissions"] = True
    data["profile_fingerprint"] = profile_fingerprint(data)
    data["verification"]["verified_worker_profile_fingerprint"] = data["profile_fingerprint"]
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    profile = resolve_worker_profile(tmp_path, "claude-code")
    assert "--dangerously-skip-permissions" not in build_worker_argv(profile, "/tmp/prompt.txt")
    with pytest.raises(WorkerResolutionError, match="audit event"):
        build_worker_argv(profile, "/tmp/prompt.txt", command_opt_in=True)
    argv = build_worker_argv(
        profile, "/tmp/prompt.txt", command_opt_in=True, audit_event_recorded=True,
    )
    assert "--dangerously-skip-permissions" in argv


def test_prompt_path_with_spaces_and_unicode_is_one_argv_element(tmp_path):
    _verified_profile(tmp_path, "codex")
    profile = resolve_worker_profile(tmp_path, "codex")
    prompt = str(tmp_path / "thư mục có space" / "prompt.txt")
    argv = build_worker_argv(profile, prompt)
    assert argv[-1] == prompt
    assert argv.count(prompt) == 1
    assert all("{prompt_file}" not in arg for arg in argv)


def test_unknown_override_key_fails_closed(tmp_path):
    write_platform_runtime_profile(tmp_path, "codex")
    with pytest.raises(WorkerResolutionError, match="unknown override fields"):
        resolve_worker_profile(tmp_path, "codex", {
            "platform": "codex", "strategy": "inline", "shell": True,
        })
