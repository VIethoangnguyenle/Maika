"""hook_python must round-trip through resolved-config (eng review 1A + 8A).

Since the W5 hook-CLI collapse the rendered hook command is OS-agnostic
(`maika hook write-gate --runtime <r>`) and no longer embeds a python launcher,
so it cannot regress to `python`. The `hook_python` key itself still persists
in resolved-config: `install.ps1` passes `--hook-python` and the Windows CI job
asserts it round-trips. These tests guard that persistence contract.
"""

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
