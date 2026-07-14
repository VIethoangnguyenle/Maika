"""Tests for maika update."""

from cli.commands.init import run_init
from cli.commands.update import run_update


def _interactive(
    monkeypatch,
    platform_key,
    mcps=("codebase-memory-mcp", "confluence", "db-access"),
    language="python",
    inputs=("y",),
):
    """Drive the interactive init/update prompts: the questionary wrappers return
    canned selections, and the remaining input() calls (UA dir, scaffold confirm)
    come from `inputs` (reconfigure has no confirm, so pass inputs=()). Default
    mcps include codebase-memory-mcp so the grounding-explorer skill is scaffolded."""
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


def test_update_uses_resolved_framework_root(tmp_path, maika_root, monkeypatch):
    target = tmp_path / "proj"
    _interactive(monkeypatch, "antigravity")
    run_init(target_dir=str(target), maika_root=str(maika_root))

    skill = target / ".maika" / "skills" / "grounding-explorer" / "SKILL.md"
    skill.write_text("tampered\n", encoding="utf-8")

    run_update(target_dir=str(target), maika_root=str(maika_root))

    assert "tampered" not in skill.read_text(encoding="utf-8")
    assert (target / ".maika").exists()


def test_update_aborts_when_no_config(tmp_path, maika_root, capsys):
    target = tmp_path / "empty"
    target.mkdir()
    run_update(target_dir=str(target), maika_root=str(maika_root))
    assert "No Maika installation" in capsys.readouterr().out


def test_update_preserves_live_skill_evolution_history(tmp_path, maika_root):
    target = tmp_path / "proj"
    run_init(
        target_dir=str(target), maika_root=str(maika_root), platform_key="generic",
        selected_mcps=[], language="python", assume_yes=True,
    )
    store = target / ".maika" / "knowledge" / "skill-evolution"
    candidate = store / "candidates" / "SC-LIVE.yaml"
    accepted = store / "accepted" / "SC-OLD.yaml"
    candidate.write_text("candidate_id: SC-LIVE\n", encoding="utf-8")
    accepted.write_text("candidate_id: SC-OLD\n", encoding="utf-8")

    run_update(target_dir=str(target), maika_root=str(maika_root))

    assert candidate.read_text(encoding="utf-8") == "candidate_id: SC-LIVE\n"
    assert accepted.read_text(encoding="utf-8") == "candidate_id: SC-OLD\n"


def test_reconfigure_to_claude_keeps_canonical_core(
    tmp_path, maika_root, monkeypatch, capsys,
):
    target = tmp_path / "proj"
    _interactive(monkeypatch, "generic")
    run_init(target_dir=str(target), maika_root=str(maika_root))
    assert (target / ".maika").exists()

    _interactive(monkeypatch, "claude-code", inputs=())
    run_update(target_dir=str(target), maika_root=str(maika_root), reconfigure=True)

    assert (target / ".maika" / "resolved-config.yaml").exists()
    assert (target / ".maika" / "skills" / "intent-analysis" / "SKILL.md").exists()
    assert (target / ".maika").exists()


def test_reconfigure_reemits_mcp_setup_for_ua(tmp_path, maika_root, monkeypatch):
    target = tmp_path / "proj"
    run_init(
        target_dir=str(target), maika_root=str(maika_root),
        platform_key="codex", selected_mcps=[], language="python", assume_yes=True,
    )
    assert not (target / ".maika" / "MCP_SETUP.md").exists()

    # reconfigure: platform codex, mcps understand-anything (triggers UA dir prompt)
    _interactive(
        monkeypatch, "codex", mcps=["understand-anything"], inputs=("/srv/ua-mcp",)
    )
    run_update(target_dir=str(target), maika_root=str(maika_root), reconfigure=True)

    setup_md = target / ".maika" / "MCP_SETUP.md"
    assert setup_md.exists()
    assert "/srv/ua-mcp" in setup_md.read_text(encoding="utf-8")


def test_update_refreshes_every_enabled_adapter_in_one_project(tmp_path, maika_root):
    from cli.commands.platform import run_platform

    run_init(str(tmp_path), str(maika_root), "codex", [], "python", True)
    for key in ("claude-code", "antigravity"):
        assert run_platform("enable", str(tmp_path), key, str(maika_root)) == 0
    hook_paths = [
        tmp_path / ".codex/hooks.json",
        tmp_path / ".claude/settings.json",
        tmp_path / ".agents/hooks.json",
    ]
    for path in hook_paths:
        path.write_text('{"hooks": {}}\n', encoding="utf-8")

    run_update(str(tmp_path), str(maika_root))

    for path in hook_paths:
        text = path.read_text(encoding="utf-8")
        assert "maika.write-gate.v1" in text
        assert "--platform" in text
