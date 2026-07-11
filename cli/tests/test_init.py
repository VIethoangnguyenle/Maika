"""Tests for maika init."""

import sys
import types
from pathlib import Path

import pytest

from cli.commands.init import (
    parse_multi_values,
    prompt_multi_checkbox,
    prompt_single_checkbox,
    resolve_init_choices,
    resolve_ua_mcp_dir,
    run_init,
)
from cli.scaffold import load_manifest


def _interactive(
    monkeypatch,
    platform_key,
    mcps=("codebase-memory-mcp", "confluence", "db-remote"),
    language="python",
    inputs=("y",),
):
    """Drive the interactive init/update prompts: the questionary wrappers return
    canned selections, and the remaining input() calls (UA dir, scaffold confirm)
    come from `inputs`. Default mcps include codebase-memory-mcp so the
    code_exploration capability (and the grounding-explorer skill) is scaffolded."""
    from cli.platforms import get_platform

    singles = iter([get_platform(platform_key).display_name, language])
    monkeypatch.setattr(
        "cli.commands.init.prompt_single_checkbox", lambda *a, **k: next(singles)
    )
    monkeypatch.setattr(
        "cli.commands.init.prompt_multi_checkbox", lambda *a, **k: list(mcps)
    )
    in_it = iter(inputs)
    monkeypatch.setattr("builtins.input", lambda *a, **k: next(in_it))


def _fake_questionary(monkeypatch, ask_return=None, ask_raises=None):
    """Inject a fake `questionary` module so the prompt wrappers can be unit-tested
    without the real dependency installed in the test runner.

    NOTE: this fake accepts any call args, so it verifies wrapper *behavior*
    (passthrough, cancel/EOF -> SystemExit) but NOT that init.py calls questionary
    with a valid signature. That call shape is locked separately by
    test_questionary_call_shapes_match_init_usage (skipped when questionary is
    absent)."""
    fake = types.ModuleType("questionary")

    class _Prompt:
        def ask(self):
            if ask_raises is not None:
                raise ask_raises
            return ask_return

    fake.select = lambda *a, **k: _Prompt()
    fake.checkbox = lambda *a, **k: _Prompt()
    fake.Choice = lambda title=None, value=None: value
    monkeypatch.setitem(sys.modules, "questionary", fake)


def test_prompt_single_checkbox_returns_questionary_answer(monkeypatch):
    _fake_questionary(monkeypatch, "B")
    assert prompt_single_checkbox("Choose", ["A", "B"], default=1) == "B"


def test_prompt_single_checkbox_aborts_on_cancel(monkeypatch):
    _fake_questionary(monkeypatch, None)
    with pytest.raises(SystemExit):
        prompt_single_checkbox("Choose", ["A", "B"], default=0)


def test_prompt_multi_checkbox_returns_questionary_answer(monkeypatch):
    choices = [{"key": "a", "display": "A"}, {"key": "b", "display": "B"}]
    _fake_questionary(monkeypatch, ["a", "b"])
    assert prompt_multi_checkbox("MCPs", choices) == ["a", "b"]


def test_prompt_multi_checkbox_empty_selection(monkeypatch):
    choices = [{"key": "a", "display": "A"}]
    _fake_questionary(monkeypatch, [])
    assert prompt_multi_checkbox("MCPs", choices) == []


def test_prompt_multi_checkbox_aborts_on_cancel(monkeypatch):
    _fake_questionary(monkeypatch, None)
    with pytest.raises(SystemExit):
        prompt_multi_checkbox("MCPs", [{"key": "a", "display": "A"}])


def test_prompt_aborts_on_eof(monkeypatch):
    # Closed / non-TTY stdin makes questionary raise EOFError; must abort cleanly.
    _fake_questionary(monkeypatch, ask_raises=EOFError())
    with pytest.raises(SystemExit):
        prompt_single_checkbox("Choose", ["A", "B"], default=0)


def test_questionary_call_shapes_match_init_usage():
    """Real-signature guard, skipped when questionary is absent (e.g. the CI
    runner): mirror init.py's exact questionary calls so a dependency major bump
    that changes the signature is caught on developer machines."""
    questionary = pytest.importorskip("questionary")
    try:
        questionary.select("platform", choices=["A", "B"], default="A")
        questionary.checkbox("mcps", choices=[questionary.Choice(title="A", value="a")])
    except Exception as exc:
        if exc.__class__.__name__ == "NoConsoleScreenBufferError":
            pytest.skip("questionary cannot create prompts on Windows CI without a console")
        raise


def test_parse_multi_values_accepts_repeated_and_comma_values():
    assert parse_multi_values(["codebase-memory-mcp,confluence", "db-remote"]) == [
        "codebase-memory-mcp",
        "confluence",
        "db-remote",
    ]


def test_resolve_init_choices_accepts_complete_non_interactive_options(maika_root):
    manifest = load_manifest(maika_root)

    platform_key, selected_mcps, language = resolve_init_choices(
        manifest,
        platform_key="generic",
        selected_mcps=["codebase-memory-mcp", "confluence"],
        language="python",
        assume_yes=True,
    )

    assert platform_key == "generic"
    assert selected_mcps == ["codebase-memory-mcp", "confluence"]
    assert language == "python"


def test_resolve_init_choices_honors_explicit_empty_mcps_without_prompt(
    maika_root, monkeypatch
):
    manifest = load_manifest(maika_root)

    def fail_if_prompted(*args, **kwargs):
        raise AssertionError("prompt_multi_checkbox should not be called")

    monkeypatch.setattr("cli.commands.init.prompt_multi_checkbox", fail_if_prompted)

    platform_key, selected_mcps, language = resolve_init_choices(
        manifest,
        platform_key="generic",
        selected_mcps=[],
        language="python",
        assume_yes=False,
    )

    assert platform_key == "generic"
    assert selected_mcps == []
    assert language == "python"


def test_resolve_init_choices_rejects_yes_with_missing_required_options(maika_root):
    manifest = load_manifest(maika_root)

    with pytest.raises(ValueError) as exc:
        resolve_init_choices(
            manifest,
            platform_key="generic",
            selected_mcps=[],
            language=None,
            assume_yes=True,
        )

    assert "--yes requires --platform and --language" in str(exc.value)


def test_resolve_init_choices_rejects_invalid_platform(maika_root):
    manifest = load_manifest(maika_root)

    with pytest.raises(ValueError) as exc:
        resolve_init_choices(
            manifest,
            platform_key="unknown",
            selected_mcps=[],
            language="python",
            assume_yes=True,
        )

    assert "Unknown platform" in str(exc.value)


def test_resolve_init_choices_accepts_agent_memory(maika_root):
    manifest = load_manifest(maika_root)

    platform_key, selected_mcps, language = resolve_init_choices(
        manifest,
        platform_key="generic",
        selected_mcps=["agent-memory"],
        language="python",
        assume_yes=True,
    )

    assert selected_mcps == ["agent-memory"]


def test_run_init_records_agent_memory_in_resolved_config(tmp_path, maika_root):
    from cli.scaffold import load_resolved_config

    target = tmp_path / "proj"
    run_init(
        target_dir=str(target),
        maika_root=str(maika_root),
        platform_key="generic",
        selected_mcps=["agent-memory"],
        language="other",
        assume_yes=True,
    )

    resolved = load_resolved_config(target)
    assert "agent-memory" in resolved["mcps"]


def test_run_init_non_interactive_generic(tmp_path, maika_root):
    target = tmp_path / "proj"

    run_init(
        target_dir=str(target),
        maika_root=str(maika_root),
        platform_key="generic",
        selected_mcps=[],
        language="other",
        assume_yes=True,
    )

    assert (target / ".maika" / "resolved-config.yaml").exists()
    assert (target / "AGENTS.md").exists()


def test_init_antigravity_uses_canonical_framework_root(tmp_path, maika_root, monkeypatch):
    target = tmp_path / "proj"
    _interactive(monkeypatch, "antigravity")

    run_init(target_dir=str(target), maika_root=str(maika_root))

    assert (target / ".maika" / "resolved-config.yaml").exists()
    assert (target / ".maika" / "rules" / "RULES.md").exists()
    assert (target / ".maika" / "skills" / "intent-analysis" / "SKILL.md").exists()
    assert (target / ".maika" / "knowledge" / "long-term" / "author-dna.yaml").exists()
    assert (target / ".maika" / "knowledge" / "long-term" / "knowledge-index.yaml").exists()
    assert (target / "AGENTS.md").exists()


def test_init_codex_uses_canonical_framework_root(tmp_path, maika_root, monkeypatch):
    target = tmp_path / "proj"
    _interactive(monkeypatch, "codex")

    run_init(target_dir=str(target), maika_root=str(maika_root))

    assert (target / ".maika" / "resolved-config.yaml").exists()
    assert (target / ".maika" / "skills" / "intent-analysis" / "SKILL.md").exists()


def test_init_claude_uses_canonical_framework_root(tmp_path, maika_root, monkeypatch):
    target = tmp_path / "proj"
    _interactive(monkeypatch, "claude-code")

    run_init(target_dir=str(target), maika_root=str(maika_root))

    assert (target / ".maika" / "resolved-config.yaml").exists()
    assert (target / ".maika" / "rules" / "RULES.md").exists()
    assert (target / ".maika" / "skills" / "intent-analysis" / "SKILL.md").exists()
    assert (target / "CLAUDE.md").exists()


def test_init_generic_keeps_maika_framework_root(tmp_path, maika_root, monkeypatch):
    target = tmp_path / "proj"
    _interactive(monkeypatch, "generic")

    run_init(target_dir=str(target), maika_root=str(maika_root))

    assert (target / ".maika" / "resolved-config.yaml").exists()
    assert (target / ".maika" / "skills" / "intent-analysis" / "SKILL.md").exists()
    assert not (target / ".agents").exists()
    assert not (target / ".claude" / "skills").exists()


def test_init_aborts_on_unresolved_marker(tmp_path, maika_root, monkeypatch):
    target = tmp_path / "proj"

    def fake_scaffold(plugins, maika, write_root, *a, **k):
        (write_root / "bad.md").write_text("{{ leftover }}\n", encoding="utf-8")
        return {"rendered": 0, "copied": 1, "dirs": 0, "skipped": 0}

    monkeypatch.setattr("cli.commands.init.scaffold_plugins", fake_scaffold)
    _interactive(monkeypatch, "claude-code")

    run_init(target_dir=str(target), maika_root=str(maika_root))

    assert not (target / "CLAUDE.md").exists()
    assert not (target / ".claude").exists()
    assert not (target / ".maika").exists()


def test_init_templatizes_entry_point_references(tmp_path, maika_root, monkeypatch):
    target = tmp_path / "proj"
    _interactive(monkeypatch, "claude-code")

    run_init(target_dir=str(target), maika_root=str(maika_root))

    entry = (target / "CLAUDE.md").read_text(encoding="utf-8")
    assert "{{ " not in entry

    rules = (target / ".maika" / "rules" / "RULES.md").read_text(encoding="utf-8")
    assert "CLAUDE.md" in rules
    assert "AGENTS.md" not in rules

    boot = (target / ".maika" / "procedures" / "bootstrap.md").read_text(encoding="utf-8")
    assert "AGENTS.md" not in boot


def test_antigravity_rendered_framework_files_do_not_reference_active_maika_paths(
    tmp_path, maika_root, monkeypatch,
):
    target = tmp_path / "proj"
    _interactive(monkeypatch, "antigravity")

    run_init(target_dir=str(target), maika_root=str(maika_root))

    offenders = []
    for path in target.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".md", ".yaml", ".yml", ".txt"} and path.name != "AGENTS.md":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if ".agents/knowledge/" in text or ".claude/knowledge/" in text:
            offenders.append(path.relative_to(target).as_posix())
    assert offenders == []


def test_codex_rendered_framework_files_do_not_reference_active_maika_paths(
    tmp_path, maika_root, monkeypatch,
):
    target = tmp_path / "proj"
    _interactive(monkeypatch, "codex")

    run_init(target_dir=str(target), maika_root=str(maika_root))

    offenders = []
    for path in target.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".md", ".yaml", ".yml", ".txt"} and path.name != "AGENTS.md":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if ".agents/knowledge/" in text or ".claude/knowledge/" in text:
            offenders.append(path.relative_to(target).as_posix())
    assert offenders == []


def test_claude_code_rendered_framework_files_do_not_reference_active_maika_paths(
    tmp_path, maika_root, monkeypatch,
):
    target = tmp_path / "proj"
    _interactive(monkeypatch, "claude-code")

    run_init(target_dir=str(target), maika_root=str(maika_root))

    offenders = []
    for path in target.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".md", ".yaml", ".yml", ".txt"} and path.name != "AGENTS.md":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if ".agents/knowledge/" in text or ".claude/knowledge/" in text:
            offenders.append(path.relative_to(target).as_posix())
    assert offenders == []


def test_init_next_steps_use_platform_framework_root(tmp_path, maika_root, monkeypatch, capsys):
    target = tmp_path / "proj"
    _interactive(monkeypatch, "antigravity")

    run_init(target_dir=str(target), maika_root=str(maika_root))

    out = capsys.readouterr().out
    assert "Customize .maika/knowledge/long-term/persona.yaml" in out


def test_init_preserves_existing_entrypoint_outside_managed_block(
    tmp_path, maika_root, monkeypatch,
):
    target = tmp_path / "proj"
    target.mkdir()
    entrypoint = target / "AGENTS.md"
    entrypoint.write_text("# Team rules\n\nKeep this line.\n", encoding="utf-8")
    _interactive(monkeypatch, "codex")

    run_init(target_dir=str(target), maika_root=str(maika_root))

    body = entrypoint.read_text(encoding="utf-8")
    assert body.startswith("# Team rules\n\nKeep this line.\n")
    assert body.count("<!-- maika:begin -->") == 1
    assert body.count("<!-- maika:end -->") == 1


def test_reinit_replaces_managed_entrypoint_block_without_duplication(
    tmp_path, maika_root,
):
    target = tmp_path / "proj"
    for _ in range(2):
        run_init(
            target_dir=str(target), maika_root=str(maika_root),
            platform_key="codex", selected_mcps=[], language="python", assume_yes=True,
        )

    body = (target / "AGENTS.md").read_text(encoding="utf-8")
    assert body.count("<!-- maika:begin -->") == 1
    assert body.count("<!-- maika:end -->") == 1


def test_init_scaffolds_mcp_bridge_when_platform_supports_tools(tmp_path, maika_root):
    target = tmp_path / "proj"
    run_init(
        target_dir=str(target),
        maika_root=str(maika_root),
        platform_key="antigravity",
        selected_mcps=["codebase-memory-mcp"],
        language="python",
        assume_yes=True,
    )

    assert (target / ".maika" / "tools" / "mcp-bridge" / "mcp_client.py").exists()


def test_init_prints_mcp_doctor_hint_when_mcps_selected(tmp_path, maika_root, capsys):
    target = tmp_path / "proj"
    run_init(
        target_dir=str(target),
        maika_root=str(maika_root),
        platform_key="codex",
        selected_mcps=["codebase-memory-mcp"],
        language="python",
        assume_yes=True,
    )

    captured = capsys.readouterr()
    assert "maika doctor mcp --target" in captured.out


def test_cli_init_forwards_non_interactive_options(monkeypatch, tmp_path):
    from cli import maika

    captured = {}

    def fake_run_init(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr("cli.commands.init.run_init", fake_run_init)
    monkeypatch.setattr(
        "sys.argv",
        [
            "maika",
            "init",
            "--target",
            str(tmp_path),
            "--platform",
            "generic",
            "--mcp",
            "codebase-memory-mcp,confluence",
            "--language",
            "python",
            "--yes",
        ],
    )

    maika.main()

    assert captured["target_dir"] == str(tmp_path)
    assert captured["platform_key"] == "generic"
    assert captured["selected_mcps"] == ["codebase-memory-mcp", "confluence"]
    assert captured["language"] == "python"
    assert captured["assume_yes"] is True


def test_cli_init_preserves_omitted_mcp_as_none(monkeypatch, tmp_path):
    from cli import maika

    captured = {}

    def fake_run_init(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr("cli.commands.init.run_init", fake_run_init)
    monkeypatch.setattr(
        "sys.argv",
        [
            "maika",
            "init",
            "--target",
            str(tmp_path),
            "--platform",
            "generic",
            "--language",
            "python",
            "--yes",
        ],
    )

    maika.main()

    assert captured["selected_mcps"] is None


UA_PLACEHOLDER = "<PATH_TO_Understand-Anything-MCP>"


def test_resolve_ua_mcp_dir_uses_flag():
    assert resolve_ua_mcp_dir(["understand-anything"], "/srv/ua", assume_yes=True) == "/srv/ua"


def test_resolve_ua_mcp_dir_placeholder_when_yes_and_missing():
    assert resolve_ua_mcp_dir(["understand-anything"], None, assume_yes=True) == UA_PLACEHOLDER


def test_resolve_ua_mcp_dir_blank_when_ua_not_selected():
    assert resolve_ua_mcp_dir(["codebase-memory-mcp"], None, assume_yes=True) == ""


MAIKA_ROOT = Path(__file__).resolve().parent.parent.parent


def test_init_emits_mcp_setup_when_ua_selected(tmp_path):
    run_init(
        target_dir=str(tmp_path), maika_root=str(MAIKA_ROOT),
        platform_key="codex", selected_mcps=["understand-anything"],
        language="python", assume_yes=True, ua_mcp_dir="/srv/ua-mcp",
    )
    setup_md = tmp_path / ".maika" / "MCP_SETUP.md"
    assert setup_md.exists()
    text = setup_md.read_text(encoding="utf-8")
    assert "/srv/ua-mcp" in text
    assert "/understand-domain" in text


def test_init_no_mcp_setup_when_ua_not_selected(tmp_path):
    run_init(
        target_dir=str(tmp_path), maika_root=str(MAIKA_ROOT),
        platform_key="codex", selected_mcps=[],
        language="python", assume_yes=True,
    )
    assert not (tmp_path / ".agents" / "MCP_SETUP.md").exists()


def test_emit_mcp_setup_files_writes_then_removes_stale(tmp_path):
    from cli.commands.init import emit_mcp_setup_files
    from cli.platforms import get_platform
    from cli.scaffold import load_manifest

    platform = get_platform("codex")
    manifest = load_manifest(MAIKA_ROOT)
    (tmp_path / ".maika").mkdir()
    setup_md = tmp_path / ".maika" / "MCP_SETUP.md"

    wrote = emit_mcp_setup_files(
        tmp_path, platform, "codex", ["understand-anything"], manifest, "/srv/ua",
    )
    assert wrote is True
    assert setup_md.exists() and "/srv/ua" in setup_md.read_text(encoding="utf-8")

    wrote2 = emit_mcp_setup_files(tmp_path, platform, "codex", [], manifest, "")
    assert wrote2 is False
    assert not setup_md.exists()


def test_init_scaffold_diet_ships_only_consumed_tooling(tmp_path, maika_root):
    target = tmp_path / "proj"
    run_init(
        target_dir=str(target), maika_root=str(maika_root), platform_key="claude-code",
        selected_mcps=[], language="python", assume_yes=True,
    )
    tools = target / ".maika" / "tools"
    assert (tools / "gate-check" / "cli.py").exists()
    assert (tools / "README.md").exists()                                  # meta-prompt trỏ tới
    assert not (tools / "skill-lint").exists()                             # framework-dev only
    assert not (tools / "gate-check" / "tests").exists()                   # CI framework không ship
    assert not (target / ".claude" / "hooks" / "write-gate" / "tests").exists()
    assert (target / ".maika" / "skills" / "skill-index.yaml").exists()    # bootstrap READ
