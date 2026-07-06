"""Tests for the Jinja2 renderer."""

import pytest
from jinja2 import TemplateSyntaxError

from cli.renderer import (
    create_renderer,
    render_string,
    copy_and_render_directory,
)


def test_render_string_resolves_tool_names(jinja_env, claude_context):
    out = render_string(jinja_env, "use {{ tools.read_file }}", claude_context)
    assert out == "use Read"


def test_malformed_template_raises_not_swallowed(jinja_env, claude_context):
    # Unclosed tag must raise, never silently pass through.
    with pytest.raises(TemplateSyntaxError):
        render_string(jinja_env, "broken {{ tools.read_file ", claude_context)


def test_directory_render_propagates_template_errors(tmp_path, jinja_env, claude_context):
    src = tmp_path / "src"
    src.mkdir()
    (src / "good.md").write_text("ok {{ tools.read_file }}", encoding="utf-8")
    (src / "bad.md").write_text("broken {{ tools.read_file ", encoding="utf-8")
    dst = tmp_path / "dst"
    with pytest.raises(TemplateSyntaxError):
        copy_and_render_directory(jinja_env, src, dst, claude_context)


def test_directory_render_excludes_instance_and_build_artifacts(tmp_path, jinja_env, claude_context):
    # The scaffold must never ship a dev's local instance/build artifacts;
    # only templates/seeds ship. (Also keeps test_snapshots.py hermetic.)
    src = tmp_path / "src"
    (src / "generated").mkdir(parents=True)
    (src / "persona.template.yaml").write_text("seed\n", encoding="utf-8")
    (src / "persona.yaml").write_text("dev local\n", encoding="utf-8")
    (src / "generated" / ".gitkeep").write_text("", encoding="utf-8")
    (src / "generated" / "rules.json").write_text("{}", encoding="utf-8")
    (src / "generated" / "checkstyle.generated.xml").write_text("<x/>", encoding="utf-8")
    dst = tmp_path / "dst"
    copy_and_render_directory(jinja_env, src, dst, claude_context)
    assert (dst / "persona.template.yaml").exists()      # seed ships
    assert (dst / "generated" / ".gitkeep").exists()     # empty-dir marker ships
    assert not (dst / "persona.yaml").exists()           # dev instance excluded
    assert not (dst / "generated" / "rules.json").exists()
    assert not (dst / "generated" / "checkstyle.generated.xml").exists()


def test_directory_render_excludes_framework_test_dirs(tmp_path, jinja_env, claude_context):
    # Framework CI tests (tools/*/tests, hooks/write-gate/tests) never ship
    # downstream — no scaffolded file invokes them (scaffold-diet audit 2026-07-06).
    src = tmp_path / "src"
    (src / "tests" / "fixtures").mkdir(parents=True)
    (src / "cli.py").write_text("code\n", encoding="utf-8")
    (src / "tests" / "test_cli.py").write_text("test\n", encoding="utf-8")
    (src / "tests" / "fixtures" / "sample.md").write_text("fx\n", encoding="utf-8")
    dst = tmp_path / "dst"
    copy_and_render_directory(jinja_env, src, dst, claude_context)
    assert (dst / "cli.py").exists()
    assert not (dst / "tests").exists()
