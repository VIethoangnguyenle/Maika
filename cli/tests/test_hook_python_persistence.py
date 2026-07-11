"""hook_python must round-trip through resolved-config (eng review 1A + 8A).

Regression: a `py -3`-only Windows box installs correctly, then a bare
`maika update` (no --hook-python) must NOT reset hooks to `python`.
"""

import pytest

from cli.platforms import get_platform
from cli.scaffold import generate_resolved_config, load_resolved_config


def test_generate_resolved_config_persists_hook_python(tmp_path):
    platform = get_platform("claude-code")
    generate_resolved_config(tmp_path, platform, [], "python", hook_python="py -3")
    resolved = load_resolved_config(tmp_path)
    assert resolved["hook_python"] == "py -3"


def test_generate_resolved_config_omits_hook_python_when_none(tmp_path):
    platform = get_platform("claude-code")
    generate_resolved_config(tmp_path, platform, [], "python")
    raw = (tmp_path / ".maika" / "resolved-config.yaml").read_text(encoding="utf-8")
    assert "hook_python" not in raw


@pytest.fixture
def windows_host(monkeypatch):
    """Force scaffold-time OS detection to Windows regardless of test host."""
    monkeypatch.setattr("cli.platforms.base._platform.system", lambda: "Windows")


def _init_project(tmp_path, hook_python):
    from cli.commands.init import run_init

    run_init(
        target_dir=str(tmp_path),
        platform_key="claude-code",
        selected_mcps=[],
        language="python",
        assume_yes=True,
        hook_python=hook_python,
    )


def test_init_renders_and_persists_launcher(tmp_path, windows_host):
    _init_project(tmp_path, "py -3")
    settings = (tmp_path / ".claude" / "settings.json").read_text(encoding="utf-8")
    assert '"command": "py -3 ' in settings
    assert load_resolved_config(tmp_path)["hook_python"] == "py -3"


def test_bare_update_preserves_hook_python(tmp_path, windows_host):
    from cli.commands.update import run_update

    _init_project(tmp_path, "py -3")
    run_update(target_dir=str(tmp_path))
    settings = (tmp_path / ".claude" / "settings.json").read_text(encoding="utf-8")
    assert '"command": "py -3 ' in settings
    assert '"command": "python ' not in settings


def test_update_with_flag_overrides_and_repersists(tmp_path, windows_host):
    from cli.commands.update import run_update

    _init_project(tmp_path, "py -3")
    run_update(target_dir=str(tmp_path), hook_python="python")
    settings = (tmp_path / ".claude" / "settings.json").read_text(encoding="utf-8")
    assert '"command": "python ' in settings
    assert load_resolved_config(tmp_path)["hook_python"] == "python"
