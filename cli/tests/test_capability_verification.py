"""Capability verification hardening (F5): no overclaims.

Version support requires a real parsed version (not just exit 0); binary
presence is never authentication; the hook smoke drives the actual CLI command;
and a non-verifying probe never erases prior verification evidence.
"""

import os
import stat
from pathlib import Path

import pytest
import yaml

from cli.platforms import probe
from cli.runtime.platform_profile import profile_fingerprint, write_platform_runtime_profile
from cli.runtime.binary_identity import binary_identity

POSIX_ONLY = pytest.mark.skipif(os.name == "nt", reason="fake exec scripts are POSIX-only")


# ── semver version support ──────────────────────────────────────────────────

@pytest.mark.parametrize(("text", "expected"), [
    ("claude 1.2.3", (1, 2, 3)),
    ("v2.0", (2, 0, 0)),
    ("codex version 0.14.9 (build)", (0, 14, 9)),
    ("no version here", None),
    ("", None),
    (None, None),
])
def test_parse_version(text, expected):
    assert probe.parse_version(text) == expected


def _fake_bin(tmp_path, name, body):
    exe = tmp_path / name
    exe.write_text("#!/usr/bin/env python3\n" + body, encoding="utf-8")
    exe.chmod(exe.stat().st_mode | stat.S_IEXEC | stat.S_IRWXU)
    return exe


@POSIX_ONLY
def test_version_supported_requires_parseable_version(tmp_path, monkeypatch):
    _fake_bin(tmp_path, "haswins", "print('haswins 3.4.5')\n")
    _fake_bin(tmp_path, "garbage", "print('ready to go')\n")            # exit 0, no version
    _fake_bin(tmp_path, "broken", "import sys; print('9.9'); sys.exit(1)\n")  # version but exit 1
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ['PATH']}")

    assert probe.detect_binary("haswins").version_supported is True
    assert probe.detect_binary("garbage").version_supported is False   # exit 0 alone is not enough
    assert probe.detect_binary("broken").version_supported is False


# ── authentication is not binary presence ───────────────────────────────────

def test_present_binary_is_unknown_auth_not_authenticated(monkeypatch):
    monkeypatch.setattr(probe, "detect_binary", lambda name: probe.BinaryProbe(
        name=name, found=True, path=f"/bin/{name}", version="1.0", version_supported=True))
    result = probe.probe_platform("claude-code")
    assert result.authentication == "unknown"
    assert result.authentication != "authenticated"


def test_missing_binary_auth_is_unavailable(monkeypatch):
    monkeypatch.setattr(probe, "detect_binary", lambda name: probe.BinaryProbe(
        name=name, found=False, path=None, version=None, version_supported=False))
    assert probe.probe_platform("claude-code").authentication == "unavailable"


# ── verify=False must not erase prior verification (F3 tail) ─────────────────

def _verified_codex(tmp_path):
    path = write_platform_runtime_profile(tmp_path, "codex")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    executable = _fake_bin(tmp_path, "codex", "print('codex 1.0')\n")
    data["worker"]["executable"] = str(executable)
    data["profile_fingerprint"] = profile_fingerprint(data)
    data["detection"]["binary"].update({"found": True, "version_supported": True,
                                         "path": str(executable), "version": "1.0"})
    data["capabilities"]["fresh_session"] = "verified"
    data["verification"] = {
        "entrypoint_smoke_test": "pass", "hook_smoke_test": "pass",
        "worker_smoke_test": "pass", "mcp_smoke_test": "detected",
        "support_tier": 2, "last_verified_at": "2026-01-01T00:00:00+00:00",
        "worker_binary": binary_identity(str(executable), version="1.0"),
        "verified_worker_profile_fingerprint": data["profile_fingerprint"],
    }
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    (tmp_path / "AGENTS.md").write_text("# entry", encoding="utf-8")
    hook = tmp_path / ".codex/hooks.json"
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_text('{"hooks": {}}', encoding="utf-8")
    return path


def test_verify_false_preserves_prior_worker_verification(tmp_path, monkeypatch):
    path = _verified_codex(tmp_path)
    binary_path = yaml.safe_load(path.read_text())["detection"]["binary"]["path"]
    monkeypatch.setattr(probe, "detect_binary", lambda name: probe.BinaryProbe(
        name=name, found=True, path=binary_path, version="1.0", version_supported=True))

    probe.probe_and_persist(tmp_path, "codex", verify=False)  # a detect-only pass

    reloaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert reloaded["verification"]["worker_smoke_test"] == "pass"           # not reset to not-run
    assert reloaded["verification"]["last_verified_at"] == "2026-01-01T00:00:00+00:00"
    assert reloaded["capabilities"]["fresh_session"] == "verified"           # not downgraded
    assert reloaded["verification"]["support_tier"] == 2


def test_fresh_probe_verify_false_is_tier_one_not_verified(tmp_path, monkeypatch):
    write_platform_runtime_profile(tmp_path, "codex")
    (tmp_path / "AGENTS.md").write_text("# entry", encoding="utf-8")
    monkeypatch.setattr(probe, "detect_binary", lambda name: probe.BinaryProbe(
        name=name, found=True, path=f"/bin/{name}", version="1.0", version_supported=True))
    probe.probe_and_persist(tmp_path, "codex", verify=False)
    prof = yaml.safe_load((tmp_path / ".maika/runtime/platforms/codex.yaml").read_text())
    assert prof["verification"]["worker_smoke_test"] == "not-run"
    assert prof["verification"]["support_tier"] == 1
