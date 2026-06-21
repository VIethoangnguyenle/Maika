"""Tests for maika init."""

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


def _answers(monkeypatch, seq):
    it = iter(seq)
    monkeypatch.setattr("builtins.input", lambda *a, **k: next(it))


def test_prompt_single_checkbox_returns_default_on_enter(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda *a, **k: "")
    assert prompt_single_checkbox("Choose", ["A", "B"], default=1) == "B"


def test_prompt_single_checkbox_accepts_number(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda *a, **k: "1")
    assert prompt_single_checkbox("Choose", ["A", "B"], default=1) == "A"


def test_prompt_single_checkbox_requires_choice_when_default_is_none(monkeypatch):
    answers = iter(["", "2"])
    monkeypatch.setattr("builtins.input", lambda *a, **k: next(answers))

    assert prompt_single_checkbox("Choose", ["A", "B"], default=None) == "B"


def test_prompt_multi_checkbox_returns_empty_on_enter(monkeypatch):
    choices = [{"key": "a", "display": "A"}, {"key": "b", "display": "B"}]
    monkeypatch.setattr("builtins.input", lambda *a, **k: "")
    assert prompt_multi_checkbox("MCPs", choices) == []


def test_prompt_multi_checkbox_accepts_comma_numbers(monkeypatch):
    choices = [{"key": "a", "display": "A"}, {"key": "b", "display": "B"}]
    monkeypatch.setattr("builtins.input", lambda *a, **k: "1,2")
    assert prompt_multi_checkbox("MCPs", choices) == ["a", "b"]


def test_parse_multi_values_accepts_repeated_and_comma_values():
    assert parse_multi_values(["socraticode,confluence", "db-remote"]) == [
        "socraticode",
        "confluence",
        "db-remote",
    ]


def test_resolve_init_choices_accepts_complete_non_interactive_options(maika_root):
    manifest = load_manifest(maika_root)

    platform_key, selected_mcps, language = resolve_init_choices(
        manifest,
        platform_key="generic",
        selected_mcps=["socraticode", "confluence"],
        language="python",
        assume_yes=True,
    )

    assert platform_key == "generic"
    assert selected_mcps == ["socraticode", "confluence"]
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


def test_init_antigravity_uses_agents_as_only_framework_root(tmp_path, maika_root, monkeypatch):
    target = tmp_path / "proj"
    _answers(monkeypatch, ["1", "1,2,3", "3", "y"])

    run_init(target_dir=str(target), maika_root=str(maika_root))

    assert not (target / ".maika").exists()
    assert (target / ".agents" / "resolved-config.yaml").exists()
    assert (target / ".agents" / "rules" / "RULES.md").exists()
    assert (target / ".agents" / "skills" / "requirement-analyst" / "SKILL.md").exists()
    assert (target / ".agents" / "knowledge" / "long-term" / "author-dna.yaml").exists()
    assert (target / "AGENTS.md").exists()


def test_init_codex_uses_agents_as_only_framework_root(tmp_path, maika_root, monkeypatch):
    target = tmp_path / "proj"
    _answers(monkeypatch, ["4", "1,2,3", "3", "y"])

    run_init(target_dir=str(target), maika_root=str(maika_root))

    assert not (target / ".maika").exists()
    assert (target / ".agents" / "resolved-config.yaml").exists()
    assert (target / ".agents" / "skills" / "requirement-analyst" / "SKILL.md").exists()


def test_init_claude_uses_claude_as_only_framework_root(tmp_path, maika_root, monkeypatch):
    target = tmp_path / "proj"
    _answers(monkeypatch, ["2", "1,2,3", "3", "y"])

    run_init(target_dir=str(target), maika_root=str(maika_root))

    assert not (target / ".maika").exists()
    assert (target / ".claude" / "resolved-config.yaml").exists()
    assert (target / ".claude" / "rules" / "RULES.md").exists()
    assert (target / ".claude" / "skills" / "requirement-analyst" / "SKILL.md").exists()
    assert (target / "CLAUDE.md").exists()


def test_init_generic_keeps_maika_framework_root(tmp_path, maika_root, monkeypatch):
    target = tmp_path / "proj"
    _answers(monkeypatch, ["3", "1,2,3", "3", "y"])

    run_init(target_dir=str(target), maika_root=str(maika_root))

    assert (target / ".maika" / "resolved-config.yaml").exists()
    assert (target / ".maika" / "skills" / "requirement-analyst" / "SKILL.md").exists()
    assert not (target / ".agents").exists()
    assert not (target / ".claude" / "skills").exists()


def test_init_aborts_on_unresolved_marker(tmp_path, maika_root, monkeypatch):
    target = tmp_path / "proj"

    def fake_scaffold(plugins, maika, write_root, *a, **k):
        (write_root / "bad.md").write_text("{{ leftover }}\n", encoding="utf-8")
        return {"rendered": 0, "copied": 1, "dirs": 0, "skipped": 0}

    monkeypatch.setattr("cli.commands.init.scaffold_plugins", fake_scaffold)
    _answers(monkeypatch, ["2", "1,2,3", "3", "y"])

    run_init(target_dir=str(target), maika_root=str(maika_root))

    assert not (target / "CLAUDE.md").exists()
    assert not (target / ".claude").exists()
    assert not (target / ".maika").exists()


def test_init_templatizes_entry_point_references(tmp_path, maika_root, monkeypatch):
    target = tmp_path / "proj"
    _answers(monkeypatch, ["2", "1,2,3", "3", "y"])

    run_init(target_dir=str(target), maika_root=str(maika_root))

    entry = (target / "CLAUDE.md").read_text(encoding="utf-8")
    assert "{{ " not in entry

    rules = (target / ".claude" / "rules" / "RULES.md").read_text(encoding="utf-8")
    assert "CLAUDE.md" in rules
    assert "AGENTS.md" not in rules

    boot = (target / ".claude" / "procedures" / "bootstrap.md").read_text(encoding="utf-8")
    assert "AGENTS.md" not in boot


def test_antigravity_rendered_framework_files_do_not_reference_active_maika_paths(
    tmp_path, maika_root, monkeypatch,
):
    target = tmp_path / "proj"
    _answers(monkeypatch, ["1", "1,2,3", "3", "y"])

    run_init(target_dir=str(target), maika_root=str(maika_root))

    offenders = []
    for path in target.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".md", ".yaml", ".yml", ".txt"} and path.name != "AGENTS.md":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if ".maika/" in text and "legacy .maika" not in text and "source repo" not in text:
            offenders.append(path.relative_to(target).as_posix())
    assert offenders == []


def test_codex_rendered_framework_files_do_not_reference_active_maika_paths(
    tmp_path, maika_root, monkeypatch,
):
    target = tmp_path / "proj"
    _answers(monkeypatch, ["4", "1,2,3", "3", "y"])

    run_init(target_dir=str(target), maika_root=str(maika_root))

    offenders = []
    for path in target.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".md", ".yaml", ".yml", ".txt"} and path.name != "AGENTS.md":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if ".maika/" in text and "legacy .maika" not in text and "source repo" not in text:
            offenders.append(path.relative_to(target).as_posix())
    assert offenders == []


def test_claude_code_rendered_framework_files_do_not_reference_active_maika_paths(
    tmp_path, maika_root, monkeypatch,
):
    target = tmp_path / "proj"
    _answers(monkeypatch, ["2", "1,2,3", "3", "y"])

    run_init(target_dir=str(target), maika_root=str(maika_root))

    offenders = []
    for path in target.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".md", ".yaml", ".yml", ".txt"} and path.name != "AGENTS.md":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if ".maika/" in text and "legacy .maika" not in text and "source repo" not in text:
            offenders.append(path.relative_to(target).as_posix())
    assert offenders == []


def test_init_next_steps_use_platform_framework_root(tmp_path, maika_root, monkeypatch, capsys):
    target = tmp_path / "proj"
    _answers(monkeypatch, ["1", "1,2,3", "3", "y"])

    run_init(target_dir=str(target), maika_root=str(maika_root))

    out = capsys.readouterr().out
    assert "Customize .agents/knowledge/long-term/persona.yaml" in out
    assert ".maika/knowledge/long-term/persona.yaml" not in out


def test_init_scaffolds_mcp_bridge_when_platform_supports_tools(tmp_path, maika_root):
    target = tmp_path / "proj"
    run_init(
        target_dir=str(target),
        maika_root=str(maika_root),
        platform_key="antigravity",
        selected_mcps=["socraticode"],
        language="python",
        assume_yes=True,
    )

    assert (target / ".agents" / "tools" / "mcp-bridge" / "mcp_client.py").exists()


def test_init_prints_mcp_doctor_hint_when_mcps_selected(tmp_path, maika_root, capsys):
    target = tmp_path / "proj"
    run_init(
        target_dir=str(target),
        maika_root=str(maika_root),
        platform_key="codex",
        selected_mcps=["socraticode"],
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
            "socraticode,confluence",
            "--language",
            "python",
            "--yes",
        ],
    )

    maika.main()

    assert captured["target_dir"] == str(tmp_path)
    assert captured["platform_key"] == "generic"
    assert captured["selected_mcps"] == ["socraticode", "confluence"]
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
    assert resolve_ua_mcp_dir(["socraticode"], None, assume_yes=True) == ""


MAIKA_ROOT = Path(__file__).resolve().parent.parent.parent


def test_init_emits_mcp_setup_when_ua_selected(tmp_path):
    run_init(
        target_dir=str(tmp_path), maika_root=str(MAIKA_ROOT),
        platform_key="codex", selected_mcps=["understand-anything"],
        language="python", assume_yes=True, ua_mcp_dir="/srv/ua-mcp",
    )
    setup_md = tmp_path / ".agents" / "MCP_SETUP.md"
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
    (tmp_path / ".agents").mkdir()
    setup_md = tmp_path / ".agents" / "MCP_SETUP.md"

    wrote = emit_mcp_setup_files(
        tmp_path, platform, "codex", ["understand-anything"], manifest, "/srv/ua",
    )
    assert wrote is True
    assert setup_md.exists() and "/srv/ua" in setup_md.read_text(encoding="utf-8")

    wrote2 = emit_mcp_setup_files(tmp_path, platform, "codex", [], manifest, "")
    assert wrote2 is False
    assert not setup_md.exists()
