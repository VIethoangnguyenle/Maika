from pathlib import Path

import yaml

from cli.platforms import probe
from cli.runtime.platform_profile import load_platform_runtime_profile, write_platform_runtime_profile


def test_detected_binary_does_not_claim_verified(monkeypatch):
    monkeypatch.setattr(probe, "detect_binary", lambda name: probe.BinaryProbe(
        name=name, found=True, path=f"/usr/bin/{name}", version="1.2.3",
        version_supported=True,
    ))
    result = probe.probe_platform("claude-code")
    assert result.binary.found is True
    assert "verified" not in result.capabilities.values()
    assert all(state in {"advertised", "detected", "unavailable", "unknown", "unsupported"}
               for state in result.capabilities.values())


def test_probe_persists_detected_facts_and_tier_one(tmp_path, monkeypatch):
    write_platform_runtime_profile(tmp_path, "codex")
    (tmp_path / "AGENTS.md").write_text("# Maika managed", encoding="utf-8")
    (tmp_path / ".codex").mkdir()
    (tmp_path / ".codex/hooks.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(probe, "detect_binary", lambda name: probe.BinaryProbe(
        name=name, found=True, path=f"/bin/{name}", version="1.0",
        version_supported=True,
    ))
    result = probe.probe_and_persist(tmp_path, "codex", verify=False)
    loaded = load_platform_runtime_profile(tmp_path, "codex")
    assert loaded.detection["binary"]["found"] is True
    assert loaded.capabilities["fresh_session"] == "detected"
    assert result.support_tier == 1


def test_verify_promotes_only_successful_smoke_paths(tmp_path, monkeypatch):
    write_platform_runtime_profile(tmp_path, "codex")
    # The hook smoke drives the real `maika hook write-gate` command, which
    # resolves the project + enabled platforms from canonical config.
    from cli.config import project as project_cfg
    project_cfg.save(tmp_path, project_cfg.enable(project_cfg._default(), "codex"))
    (tmp_path / "AGENTS.md").write_text("# entry", encoding="utf-8")
    hook = tmp_path / ".codex/hooks.json"
    hook.parent.mkdir()
    hook.write_text('{"hooks": {"PreToolUse": [{"hooks": ['
                    '{"id": "maika.write-gate.v1", "command": '
                    '"maika hook write-gate --runtime codex --platform codex"}]}]}}',
                    encoding="utf-8")
    import shutil
    source = Path(__file__).resolve().parents[2] / ".maika/hooks/write-gate/write_gate.py"
    evaluator = tmp_path / ".maika/hooks/write-gate/write_gate.py"
    evaluator.parent.mkdir(parents=True)
    shutil.copy2(source, evaluator)
    fake_binary = tmp_path / "codex"
    fake_binary.write_text("#!/bin/sh\necho MAIKA_WORKER_SMOKE_OK\n", encoding="utf-8")
    fake_binary.chmod(0o755)
    profile_path = tmp_path / ".maika/runtime/platforms/codex.yaml"
    profile_doc = yaml.safe_load(profile_path.read_text())
    profile_doc["worker"]["executable"] = str(fake_binary)
    from cli.runtime.platform_profile import profile_fingerprint
    profile_doc["profile_fingerprint"] = profile_fingerprint(profile_doc)
    profile_path.write_text(yaml.safe_dump(profile_doc, sort_keys=False))
    monkeypatch.setattr(probe, "detect_binary", lambda name: probe.BinaryProbe(
        name=name, found=True, path=str(fake_binary), version="1.0",
        version_supported=True,
    ))
    result = probe.probe_and_persist(
        tmp_path, "codex", verify=True,
        smoke_runner=lambda *_args, **_kwargs: {"state": "verified", "returncode": 0, "output": "ok"},
    )
    assert result.verification["entrypoint"] == "verified"
    assert result.verification["hook"] == "verified"
    assert result.verification["worker"] == "verified"
    assert result.support_tier >= 2
    from cli.runtime.worker_resolver import resolve_worker_profile
    assert resolve_worker_profile(tmp_path, "codex").strategy == "fresh_process"


def test_failed_worker_smoke_never_promotes_fresh_session(tmp_path, monkeypatch):
    write_platform_runtime_profile(tmp_path, "codex")
    monkeypatch.setattr(probe, "detect_binary", lambda name: probe.BinaryProbe(
        name=name, found=True, path=f"/bin/{name}", version="1.0",
        version_supported=True,
    ))
    result = probe.probe_and_persist(
        tmp_path, "codex", verify=True,
        smoke_runner=lambda *_args, **_kwargs: {"state": "degraded", "returncode": 1, "output": "no auth"},
    )
    assert result.capabilities["fresh_session"] == "degraded"
    profile = yaml.safe_load((tmp_path / ".maika/runtime/platforms/codex.yaml").read_text())
    assert profile["verification"]["worker_smoke_test"] == "fail"
