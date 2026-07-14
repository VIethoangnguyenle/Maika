"""Per-platform runtime profile contract (Workstream A, Phase A1)."""

from pathlib import Path

import pytest
import yaml

from cli.commands.init import run_init


REPO_ROOT = Path(__file__).resolve().parents[2]


def _init(target: Path, platform: str) -> None:
    run_init(
        target_dir=str(target), maika_root=str(REPO_ROOT), platform_key=platform,
        selected_mcps=[], language="python", assume_yes=True,
    )


def test_shared_execution_profile_is_platform_independent(tmp_path):
    rendered = []
    for platform in ("claude-code", "codex", "antigravity"):
        target = tmp_path / platform
        _init(target, platform)
        rendered.append((target / ".maika/profiles/execution-mode.yaml").read_bytes())
    assert rendered[0] == rendered[1] == rendered[2]
    assert b"executable:" not in rendered[0]
    assert b"worker:" not in rendered[0]


@pytest.mark.parametrize(
    ("platform", "executable", "args"),
    [
        ("claude-code", "claude", ["-p", "--prompt-file", "{prompt_file}"]),
        ("codex", "codex", ["exec", "{prompt_file}"]),
        ("antigravity", "agy", ["{prompt_file}"]),
    ],
)
def test_init_writes_platform_specific_runtime_profile(tmp_path, platform, executable, args):
    from cli.runtime.platform_profile import load_platform_runtime_profile

    _init(tmp_path, platform)
    profile = load_platform_runtime_profile(tmp_path, platform)
    assert profile.platform == platform
    assert profile.worker.executable == executable
    assert list(profile.worker.args) == args
    assert profile.worker.dangerous_permissions is False
    assert profile.adapter.enabled is True


def test_missing_enabled_platform_profile_blocks_with_remediation(tmp_path):
    from cli.runtime.platform_profile import PlatformProfileError, load_platform_runtime_profile

    with pytest.raises(PlatformProfileError, match=r"maika platform enable codex|maika repair"):
        load_platform_runtime_profile(tmp_path, "codex")


def test_unknown_worker_strategy_fails_closed(tmp_path):
    from cli.runtime.platform_profile import PlatformProfileError, load_platform_runtime_profile

    path = tmp_path / ".maika/runtime/platforms/codex.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(yaml.safe_dump({
        "version": 1,
        "platform": "codex",
        "adapter": {"enabled": True, "entrypoint": "AGENTS.md", "native_config": ".codex/hooks.json"},
        "capabilities": {},
        "worker": {"strategy": "shell_magic", "executable": "codex", "args": []},
    }), encoding="utf-8")

    with pytest.raises(PlatformProfileError, match="unknown worker strategy"):
        load_platform_runtime_profile(tmp_path, "codex")


def test_profile_platform_key_must_match_filename(tmp_path):
    from cli.runtime.platform_profile import PlatformProfileError, load_platform_runtime_profile

    path = tmp_path / ".maika/runtime/platforms/codex.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(yaml.safe_dump({
        "version": 1,
        "platform": "claude-code",
        "adapter": {"enabled": True, "entrypoint": "CLAUDE.md"},
        "capabilities": {},
        "worker": {"strategy": "fresh_process", "executable": "claude", "args": []},
    }), encoding="utf-8")

    with pytest.raises(PlatformProfileError, match="does not match requested platform"):
        load_platform_runtime_profile(tmp_path, "codex")
