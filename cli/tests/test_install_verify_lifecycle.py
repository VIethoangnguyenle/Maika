"""Install/verify lifecycle contract (F2).

A fresh install must persist real binary detection (Tier 1) and steer the user to
`maika platform verify` before dispatching — never advertise a worker the
orchestrator would immediately refuse. `--verify-platform` runs verification
inline and reaches Tier 2 on success.
"""

from pathlib import Path

import yaml

from cli.commands.init import run_init
from cli.platforms import probe

REPO = Path(__file__).resolve().parents[2]


def _not_found(monkeypatch):
    monkeypatch.setattr(
        probe, "detect_binary",
        lambda name, timeout=5: probe.BinaryProbe(name, False, None, None, False),
    )


def _profile(target: Path, platform: str) -> dict:
    return yaml.safe_load(
        (target / ".maika/runtime/platforms" / f"{platform}.yaml").read_text(encoding="utf-8")
    )


def _init(target, platform, **kw):
    run_init(target_dir=str(target), maika_root=str(REPO), platform_key=platform,
             selected_mcps=[], language="python", assume_yes=True, **kw)


def test_fresh_install_persists_detection_and_tier_one(tmp_path, monkeypatch):
    _not_found(monkeypatch)
    target = tmp_path / "proj"
    _init(target, "claude-code")
    prof = _profile(target, "claude-code")
    # detection was actually run and persisted (not the null scaffold default)
    assert prof["detection"]["last_detected_at"] is not None
    assert prof["detection"]["binary"]["found"] is False
    # entrypoint present but worker unverified → Tier 1
    assert prof["verification"]["support_tier"] == 1
    assert prof["verification"]["worker_smoke_test"] == "not-run"


def test_fresh_install_prints_verify_remediation(tmp_path, monkeypatch, capsys):
    _not_found(monkeypatch)
    _init(tmp_path / "proj", "claude-code")
    out = capsys.readouterr().out
    assert "maika platform verify claude-code" in out


def test_generic_install_omits_verify_hint(tmp_path, monkeypatch, capsys):
    # generic has no worker binary; there is nothing to verify.
    _not_found(monkeypatch)
    _init(tmp_path / "proj", "generic")
    out = capsys.readouterr().out
    assert "platform verify" not in out


def test_verify_platform_flag_reaches_tier_two(tmp_path, monkeypatch):
    binary = tmp_path / "codex"
    binary.write_text("#!/bin/sh\necho codex 1.0\n", encoding="utf-8")
    binary.chmod(0o755)
    monkeypatch.setattr(
        probe, "detect_binary",
        lambda name, timeout=5: probe.BinaryProbe(name, True, str(binary), "1.0", True),
    )
    monkeypatch.setattr(
        probe, "run_worker_smoke_test",
        lambda profile, prompt, **_kwargs: {"state": "verified", "returncode": 0, "output": "ok"},
    )
    target = tmp_path / "proj"
    _init(target, "codex", verify_platform=True)
    prof = _profile(target, "codex")
    assert prof["verification"]["worker_smoke_test"] == "pass"
    assert prof["verification"]["last_verified_at"] is not None
    assert prof["verification"]["support_tier"] >= 2
