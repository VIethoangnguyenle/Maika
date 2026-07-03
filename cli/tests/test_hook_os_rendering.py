"""Hook command strings must render OS-correctly and keep Linux byte-identical."""

import json

import pytest

from cli.platforms import get_platform
from cli.renderer import render_string


# (template path relative to repo root, platform key, runtime, framework_root)
HOOKS = [
    (".maika/hooks/claude-code/settings.json", "claude-code", "claude", ".claude"),
    (".maika/hooks/codex/hooks.json", "codex", "codex", ".agents"),
    (".maika/hooks/antigravity/hooks.json", "antigravity", "antigravity", ".agents"),
]


def _context(platform_key, is_windows):
    ctx = get_platform(platform_key).build_render_context([], "python")
    ctx["is_windows"] = is_windows  # deterministic regardless of test host OS
    return ctx


def _command(jinja_env, maika_root, template_rel, platform_key, is_windows):
    text = (maika_root / template_rel).read_text(encoding="utf-8")
    rendered = render_string(jinja_env, text, _context(platform_key, is_windows))
    data = json.loads(rendered)  # must stay valid JSON on both branches
    return data["hooks"]["PreToolUse"][0]["hooks"][0]["command"]


# Exact Linux command strings (post-render). Byte-identical guard.
LINUX_EXPECTED = {
    "claude": 'python3 "$CLAUDE_PROJECT_DIR"/.claude/hooks/write-gate/write_gate.py --framework-root .claude --runtime claude',
    "codex": '/usr/bin/python3 "$(git rev-parse --show-toplevel)/.agents/hooks/write-gate/write_gate.py" --framework-root .agents --runtime codex',
    "antigravity": '/usr/bin/python3 "$(git rev-parse --show-toplevel)/.agents/hooks/write-gate/write_gate.py" --framework-root .agents --runtime antigravity',
}


# Exact Windows command strings (post-render). Claude anchors via
# %CLAUDE_PROJECT_DIR% (cwd-drift, claude-code#50960); codex/antigravity stay
# cwd-relative until their Windows runtimes are validated (review 2B).
WINDOWS_EXPECTED = {
    "claude": '{hp} "%CLAUDE_PROJECT_DIR%/.claude/hooks/write-gate/write_gate.py" --framework-root .claude --runtime claude',
    "codex": "{hp} .agents/hooks/write-gate/write_gate.py --framework-root .agents --runtime codex",
    "antigravity": "{hp} .agents/hooks/write-gate/write_gate.py --framework-root .agents --runtime antigravity",
}


@pytest.mark.parametrize("template_rel,platform_key,runtime,root", HOOKS)
def test_linux_command_byte_identical(jinja_env, maika_root, template_rel, platform_key, runtime, root):
    cmd = _command(jinja_env, maika_root, template_rel, platform_key, is_windows=False)
    assert cmd == LINUX_EXPECTED[runtime]


@pytest.mark.parametrize("template_rel,platform_key,runtime,root", HOOKS)
def test_windows_command_portable(jinja_env, maika_root, template_rel, platform_key, runtime, root):
    cmd = _command(jinja_env, maika_root, template_rel, platform_key, is_windows=True)
    assert cmd == WINDOWS_EXPECTED[runtime].format(hp="python")
    # No Unix-only shell tokens survive on Windows.
    assert "/usr/bin/python3" not in cmd
    assert "$(git rev-parse" not in cmd
    assert "$CLAUDE_PROJECT_DIR" not in cmd  # %VAR% form is not the $VAR form


@pytest.mark.parametrize("template_rel,platform_key,runtime,root", HOOKS)
def test_both_branches_valid_json(jinja_env, maika_root, template_rel, platform_key, runtime, root):
    for is_win in (True, False):
        text = (maika_root / template_rel).read_text(encoding="utf-8")
        rendered = render_string(jinja_env, text, _context(platform_key, is_win))
        json.loads(rendered)  # raises if invalid


@pytest.mark.parametrize("template_rel,platform_key,runtime,root", HOOKS)
def test_windows_command_honors_hook_python(jinja_env, maika_root, template_rel, platform_key, runtime, root):
    ctx = get_platform(platform_key).build_render_context([], "python", hook_python="py -3")
    ctx["is_windows"] = True
    text = (maika_root / template_rel).read_text(encoding="utf-8")
    cmd = json.loads(render_string(jinja_env, text, ctx))["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
    assert cmd == WINDOWS_EXPECTED[runtime].format(hp="py -3")
