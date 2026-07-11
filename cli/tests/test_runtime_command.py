import json

from cli.commands.runtime import run_runtime
from cli.config import project


def _project(root):
    cfg = project.enable(project._default(), "codex")
    project.save(root, cfg)


def test_runtime_set_and_current(tmp_path, capsys):
    _project(tmp_path)
    assert run_runtime("set-platform", str(tmp_path), "codex") == 0
    capsys.readouterr()
    assert run_runtime("current", str(tmp_path), None) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["platform"] == "codex"
    assert payload["source"] == "active-platform"


def test_runtime_worker_profile_reports_canonical_selection(tmp_path, capsys):
    from cli.runtime.platform_profile import write_platform_runtime_profile

    _project(tmp_path)
    write_platform_runtime_profile(tmp_path, "codex")
    assert run_runtime("worker-profile", str(tmp_path), "codex") == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["platform"] == "codex"
    # An unverified worker resolves to a truthful disabled state (no shadow
    # inline fallback); the reason carries the verify remediation (F6).
    assert payload["strategy"] == "disabled"
    assert "maika platform verify codex" in payload["reason"]
