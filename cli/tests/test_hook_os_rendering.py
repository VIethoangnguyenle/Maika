"""Host hook command is a single OS-agnostic stable CLI call.

After the W5 hook-CLI collapse, every host renders the identical command
`maika hook write-gate --runtime <r>` on both Linux and Windows — no python
launcher, no path anchoring, no `is_windows` branch. The write-gate policy is
reached through the installed `maika` executable, not a per-OS python invocation.
"""

import json

import pytest

from cli.platforms import get_platform
from cli.renderer import render_string


# (template path relative to repo root, platform key, runtime)
HOOKS = [
    (".maika/hooks/claude-code/settings.json", "claude-code", "claude"),
    (".maika/hooks/codex/hooks.json", "codex", "codex"),
    (".maika/hooks/antigravity/hooks.json", "antigravity", "antigravity"),
]

STABLE_COMMAND = {
    "claude": "maika hook write-gate --runtime claude",
    "codex": "maika hook write-gate --runtime codex",
    "antigravity": "maika hook write-gate --runtime antigravity",
}


def _context(platform_key, is_windows):
    ctx = get_platform(platform_key).build_render_context([], "python")
    ctx["is_windows"] = is_windows  # deterministic regardless of test host OS
    return ctx


def _command(jinja_env, maika_root, template_rel, platform_key, is_windows):
    text = (maika_root / template_rel).read_text(encoding="utf-8")
    rendered = render_string(jinja_env, text, _context(platform_key, is_windows))
    data = json.loads(rendered)  # must stay valid JSON
    return data["hooks"]["PreToolUse"][0]["hooks"][0]["command"]


@pytest.mark.parametrize("template_rel,platform_key,runtime", HOOKS)
def test_command_is_stable_cli(jinja_env, maika_root, template_rel, platform_key, runtime):
    cmd = _command(jinja_env, maika_root, template_rel, platform_key, is_windows=False)
    assert cmd == STABLE_COMMAND[runtime]


@pytest.mark.parametrize("template_rel,platform_key,runtime", HOOKS)
def test_command_identical_across_os(jinja_env, maika_root, template_rel, platform_key, runtime):
    linux = _command(jinja_env, maika_root, template_rel, platform_key, is_windows=False)
    windows = _command(jinja_env, maika_root, template_rel, platform_key, is_windows=True)
    assert linux == windows == STABLE_COMMAND[runtime]


@pytest.mark.parametrize("template_rel,platform_key,runtime", HOOKS)
def test_no_os_specific_launcher_tokens(jinja_env, maika_root, template_rel, platform_key, runtime):
    forbidden = (
        "python3", "/usr/bin/python3", "write_gate.py",
        "$(git rev-parse", "%CLAUDE_PROJECT_DIR%", "$CLAUDE_PROJECT_DIR",
    )
    for is_win in (False, True):
        cmd = _command(jinja_env, maika_root, template_rel, platform_key, is_windows=is_win)
        for token in forbidden:
            assert token not in cmd, f"{token} leaked into {platform_key} hook command"


@pytest.mark.parametrize("template_rel,platform_key,runtime", HOOKS)
def test_both_branches_valid_json(jinja_env, maika_root, template_rel, platform_key, runtime):
    for is_win in (True, False):
        text = (maika_root / template_rel).read_text(encoding="utf-8")
        rendered = render_string(jinja_env, text, _context(platform_key, is_win))
        json.loads(rendered)  # raises if invalid
