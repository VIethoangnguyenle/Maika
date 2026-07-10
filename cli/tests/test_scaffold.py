"""Tests for the shared scaffolding core."""

import pytest
from jinja2 import TemplateSyntaxError, UndefinedError

from cli.scaffold import (
    generate_resolved_config,
    load_manifest,
    load_resolved_config,
    resolved_config_candidates,
    has_capability,
    get_ownership,
    resolve_source_path,
    scaffold_plugin,
    scaffold_plugins,
    verify_no_unresolved,
)


def test_get_ownership_defaults_to_framework():
    assert get_ownership({"name": "x"}) == "framework"
    assert get_ownership({"name": "x", "ownership": "user"}) == "user"


def test_load_manifest_has_plugins(maika_root):
    manifest = load_manifest(maika_root)
    assert len(manifest["plugins"]) > 0
    assert "mcp_capabilities" in manifest


def test_has_capability(maika_root):
    manifest = load_manifest(maika_root)
    caps = manifest["mcp_capabilities"]
    assert has_capability(["codebase-memory-mcp"], caps, "code_exploration") is True
    assert has_capability([], caps, "code_exploration") is False


def test_manifest_declares_agent_memory_capability(maika_root):
    manifest = load_manifest(maika_root)
    caps = manifest["mcp_capabilities"]
    assert "agent-memory" in caps
    assert caps["agent-memory"]["provides"] == "memory"


def test_has_capability_recognizes_memory(maika_root):
    manifest = load_manifest(maika_root)
    caps = manifest["mcp_capabilities"]
    assert has_capability(["agent-memory"], caps, "memory") is True
    assert has_capability([], caps, "memory") is False


def test_resolve_source_path_maps_skills(maika_root):
    p = resolve_source_path(maika_root, "skills/grounding-explorer/")
    assert p == maika_root / ".maika/skills/grounding-explorer/"


def test_resolve_source_path_maps_meta_prompt(maika_root):
    p = resolve_source_path(maika_root, "meta-prompt.md")
    assert p == maika_root / ".maika/meta-prompt.md"


def test_resolve_source_path_maps_hooks(maika_root):
    p = resolve_source_path(maika_root, "hooks/write-gate/")
    assert p == maika_root / ".maika/hooks/write-gate/"


def test_scaffold_plugin_renders_template_source(tmp_path, jinja_env, claude_context):
    source_path = tmp_path / "x.md"
    source_path.write_text("use {{ tools.read_file }}", encoding="utf-8")
    target_path = tmp_path / "out" / "x.md"
    plugin = {"name": "x", "source": "x.md", "output": "x.md"}

    result = scaffold_plugin(plugin, source_path, target_path, claude_context, jinja_env)

    assert result["action"] == "rendered"
    assert target_path.exists()
    content = target_path.read_text(encoding="utf-8")
    assert "Read" in content
    assert "{{" not in content
    assert "}}" not in content


def test_scaffold_plugin_malformed_template_raises_not_swallowed(
    tmp_path, jinja_env, claude_context
):
    source_path = tmp_path / "x.md"
    source_path.write_text("broken {{ tools.read_file ", encoding="utf-8")
    target_path = tmp_path / "out" / "x.md"
    plugin = {"name": "x", "source": "x.md", "output": "x.md"}

    with pytest.raises(TemplateSyntaxError):
        scaffold_plugin(plugin, source_path, target_path, claude_context, jinja_env)


def test_scaffold_plugin_unknown_tool_key_raises_before_target_write(
    tmp_path, jinja_env, claude_context
):
    source_path = tmp_path / "x.md"
    source_path.write_text("use {{ tools.not_a_real_tool }}", encoding="utf-8")
    target_path = tmp_path / "out" / "x.md"
    plugin = {"name": "x", "source": "x.md", "output": "x.md"}

    with pytest.raises(UndefinedError):
        scaffold_plugin(plugin, source_path, target_path, claude_context, jinja_env)

    assert not target_path.exists()


def test_scaffold_plugins_skips_platform_capability_plugin_when_absent(
    tmp_path, maika_root, jinja_env, claude_context
):
    source = maika_root / ".maika" / "knowledge" / "templates" / "TOKEN_LOG.tpl.md"
    assert source.exists()

    plugins = [{
        "name": "write-gate-settings",
        "type": "hook",
        "source": "knowledge-templates/TOKEN_LOG.tpl.md",
        "output": "{{ platform.framework_root }}/hooks/write-gate/TOKEN_LOG.tpl.md",
        "requires_platform_capability": "write_gate_hook",
    }]

    context = {
        **claude_context,
        "capabilities": {**claude_context["capabilities"], "write_gate_hook": False},
    }
    stats = scaffold_plugins(
        plugins, maika_root, tmp_path, context, jinja_env,
        mcp_capabilities={}, selected_mcps=[], verbose=False,
    )

    assert stats["skipped"] == 1
    assert not (tmp_path / ".claude" / "hooks" / "write-gate" / "TOKEN_LOG.tpl.md").exists()


def test_scaffold_plugins_includes_platform_capability_plugin_when_present(
    tmp_path, maika_root, jinja_env, claude_context
):
    plugins = [{
        "name": "write-gate-settings",
        "type": "hook",
        "source": "knowledge-templates/TOKEN_LOG.tpl.md",
        "output": "{{ platform.framework_root }}/hooks/write-gate/TOKEN_LOG.tpl.md",
        "requires_platform_capability": "write_gate_hook",
    }]

    context = {
        **claude_context,
        "capabilities": {**claude_context["capabilities"], "write_gate_hook": True},
    }
    stats = scaffold_plugins(
        plugins, maika_root, tmp_path, context, jinja_env,
        mcp_capabilities={}, selected_mcps=[], verbose=False,
    )

    assert stats["copied"] + stats["rendered"] == 1
    assert (tmp_path / ".claude" / "hooks" / "write-gate" / "TOKEN_LOG.tpl.md").exists()


def test_scaffold_plugins_skips_platform_specific_plugin_for_other_platform(
    tmp_path, maika_root, jinja_env, claude_context
):
    plugins = [{
        "name": "codex-write-gate-settings",
        "type": "hook",
        "source": "knowledge-templates/TOKEN_LOG.tpl.md",
        "output": ".codex/hooks.json",
        "requires_platform": "codex",
    }]

    stats = scaffold_plugins(
        plugins, maika_root, tmp_path, claude_context, jinja_env,
        mcp_capabilities={}, selected_mcps=[], verbose=False,
    )

    assert stats["skipped"] == 1
    assert not (tmp_path / ".codex" / "hooks.json").exists()


def test_knowledge_dirs_are_user_owned(maika_root):
    manifest = load_manifest(maika_root)
    by_name = {p["name"]: p for p in manifest["plugins"]}
    assert get_ownership(by_name["knowledge-active-skeleton"]) == "user"
    assert get_ownership(by_name["knowledge-long-term"]) == "user"
    # Templates remain framework-managed.
    assert get_ownership(by_name["knowledge-templates"]) == "framework"


def test_manifest_declares_write_gate_plugins(maika_root):
    manifest = load_manifest(maika_root)
    by_name = {p["name"]: p for p in manifest["plugins"]}
    assert by_name["write-gate-core"]["source"] == "hooks/write-gate/"
    assert by_name["write-gate-core"]["requires_platform_capability"] == "write_gate_hook"
    assert by_name["claude-code-write-gate-settings"]["requires_platform"] == "claude-code"
    assert by_name["claude-code-write-gate-settings"]["requires_platform_capability"] == "write_gate_hook"
    assert by_name["codex-write-gate-hooks"]["requires_platform"] == "codex"
    assert by_name["codex-write-gate-hooks"]["requires_platform_capability"] == "write_gate_hook"
    assert by_name["antigravity-write-gate-hooks"]["requires_platform"] == "antigravity"
    assert by_name["antigravity-write-gate-hooks"]["requires_platform_capability"] == "write_gate_hook"


def test_manifest_declares_mcp_bridge_plugin(maika_root):
    manifest = load_manifest(maika_root)
    by_name = {p["name"]: p for p in manifest["plugins"]}
    assert by_name["mcp-bridge"]["type"] == "tool"
    assert by_name["mcp-bridge"]["source"] == "tools/mcp-bridge/"
    assert by_name["mcp-bridge"]["copy_dir"] is True


def _write_resolved_config(target, content):
    config_path = target / ".maika" / "resolved-config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(content, encoding="utf-8")


def test_resolved_config_candidates_derive_from_platform_registry(tmp_path):
    from cli.platforms import PLATFORMS, get_platform

    candidates = [
        p.relative_to(tmp_path).as_posix() for p in resolved_config_candidates(tmp_path)
    ]
    # Every platform's framework_root is represented (derived, not hardcoded).
    expected_roots = {get_platform(k).framework_root for k in PLATFORMS}
    assert {c.split("/")[0] for c in candidates} == expected_roots
    # Canonical root is first → load fallback is deterministic.
    assert candidates[0] == ".maika/resolved-config.yaml"
    # Every entry is a resolved-config.yaml.
    assert all(c.endswith("/resolved-config.yaml") for c in candidates)


def test_generate_resolved_config_uses_platform_framework_root(tmp_path):
    from cli.platforms import get_platform

    platform = get_platform("antigravity")
    generate_resolved_config(tmp_path, platform, ["codebase-memory-mcp"], "python")

    config = tmp_path / ".agents" / "resolved-config.yaml"
    assert config.exists()
    assert not (tmp_path / ".maika").exists()
    body = config.read_text(encoding="utf-8")
    assert "platform: antigravity" in body
    assert "framework_root: .agents" in body


def test_load_resolved_config_reads_agents_config(tmp_path):
    config = tmp_path / ".agents" / "resolved-config.yaml"
    config.parent.mkdir(parents=True)
    config.write_text(
        "resolved:\n"
        "  platform: antigravity\n"
        "  framework_root: .agents\n"
        "  mcps: [codebase-memory-mcp]\n"
        "  language: python\n",
        encoding="utf-8",
    )

    resolved = load_resolved_config(tmp_path)
    assert resolved["platform"] == "antigravity"
    assert resolved["framework_root"] == ".agents"


def test_load_resolved_config_returns_dict_when_valid(tmp_path):
    _write_resolved_config(
        tmp_path,
        "resolved:\n  platform: claude-code\n  mcps: []\n  language: python\n",
    )
    resolved = load_resolved_config(tmp_path)
    assert resolved["platform"] == "claude-code"
    assert resolved["mcps"] == []
    assert resolved["language"] == "python"
    assert resolved["framework_root"] == ".claude"


def test_load_resolved_config_returns_none_when_missing(tmp_path):
    assert load_resolved_config(tmp_path) is None


def test_load_resolved_config_returns_none_when_empty(tmp_path):
    _write_resolved_config(tmp_path, "")
    assert load_resolved_config(tmp_path) is None


def test_load_resolved_config_returns_none_when_only_comment(tmp_path):
    _write_resolved_config(tmp_path, "# just a comment\n")
    assert load_resolved_config(tmp_path) is None


def test_load_resolved_config_returns_none_when_resolved_not_dict(tmp_path):
    _write_resolved_config(tmp_path, "resolved: 3\n")
    assert load_resolved_config(tmp_path) is None


def test_load_resolved_config_returns_none_when_malformed_yaml(tmp_path):
    _write_resolved_config(tmp_path, "resolved:\n  - [unterminated\n")
    assert load_resolved_config(tmp_path) is None


def test_load_resolved_config_reads_legacy_maika_config(tmp_path):
    _write_resolved_config(
        tmp_path,
        "resolved:\n  platform: generic\n  mcps: []\n  language: python\n",
    )

    resolved = load_resolved_config(tmp_path)
    assert resolved["platform"] == "generic"
    assert resolved["framework_root"] == ".maika"


def test_verify_no_unresolved_flags_offending_py_file(tmp_path):
    # .py is not in scaffold's single-file render allowlist, but the
    # renderer's copy_and_render_directory does render .py files — so the
    # safety gate must scan it too, or an unresolved marker in a rendered
    # .py file would slip past verify_no_unresolved undetected.
    offending = tmp_path / "hook.py"
    offending.write_text("value = {{ tools.read_file }}\n", encoding="utf-8")

    offenders = verify_no_unresolved(tmp_path)

    assert offending in offenders


def test_verify_no_unresolved_flags_platform_entry_point(tmp_path):
    offending = tmp_path / "AGENTS.md"
    offending.write_text("rules {{ platform.config_entry_point }}\n", encoding="utf-8")

    offenders = verify_no_unresolved(tmp_path)

    assert offending in offenders


from cli.scaffold import export_as_flat_command


def test_export_as_flat_command_strips_frontmatter_and_inlines_pre_conditions():
    skill_md = (
        "---\n"
        "name: intent-analysis\n"
        "description: Classify requests into canonical change intent.\n"
        "pre_conditions:\n"
        "  - file: .maika/knowledge/active/AGENT_TRANSPARENCY.md\n"
        "    condition: exists\n"
        "    on_fail: \"ABORT - bootstrap hasn't run\"\n"
        "---\n"
        "\n"
        "# Intent Analysis\n"
        "\n"
        "Body content here.\n"
    )

    output = export_as_flat_command(skill_md)

    assert not output.startswith("---")
    assert "name:" not in output
    assert "# intent-analysis" in output
    assert "Classify requests into canonical change intent." in output
    assert "ABORT - bootstrap hasn't run" in output
    assert "Body content here." in output


def test_export_as_flat_command_without_pre_conditions_omits_checklist():
    skill_md = (
        "---\n"
        "description: Approve and commit.\n"
        "---\n"
        "\n"
        "# /approve-conventions\n"
        "\n"
        "Body.\n"
    )

    output = export_as_flat_command(skill_md)

    assert "Pre-conditions" not in output
    assert "Approve and commit." in output
    assert "Body." in output


from cli.scaffold import scaffold_native_skill_exports


class _FakePlatform:
    def __init__(self, native_skill_export):
        self.native_skill_export = native_skill_export


def test_scaffold_native_skill_exports_noop_when_unsupported(tmp_path):
    plugins = [{"name": "intent-analysis", "type": "skill", "copy_dir": True,
                "output": ".maika/skills/intent-analysis/"}]
    platform = _FakePlatform(None)

    stats = scaffold_native_skill_exports(plugins, tmp_path, platform, verbose=False)

    assert stats == {"exported": 0, "skipped": 0}


def test_scaffold_native_skill_exports_mirrors_skill_verbatim(tmp_path):
    skill_dir = tmp_path / ".maika" / "skills" / "intent-analysis"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: intent-analysis\ndescription: Classify intent.\n---\n\nBody.\n",
        encoding="utf-8",
    )
    plugins = [{"name": "intent-analysis", "type": "skill", "copy_dir": True,
                "output": ".maika/skills/intent-analysis/"}]
    platform = _FakePlatform({"dir": ".claude/skills", "strip_frontmatter": False, "flatten": False})

    stats = scaffold_native_skill_exports(plugins, tmp_path, platform, verbose=False)

    target = tmp_path / ".claude" / "skills" / "intent-analysis" / "SKILL.md"
    assert target.exists()
    assert target.read_text(encoding="utf-8") == (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    assert stats == {"exported": 1, "skipped": 0}


def test_scaffold_native_skill_exports_inserts_name_for_workflow(tmp_path):
    workflow_path = tmp_path / ".maika" / "workflows" / "task.md"
    workflow_path.parent.mkdir(parents=True)
    workflow_path.write_text(
        "---\ndescription: Main task orchestrator.\n---\n\n# /task\n",
        encoding="utf-8",
    )
    plugins = [{"name": "workflow-task", "type": "workflow", "output": ".maika/workflows/task.md"}]
    platform = _FakePlatform({"dir": ".claude/skills", "strip_frontmatter": False, "flatten": False})

    scaffold_native_skill_exports(plugins, tmp_path, platform, verbose=False)

    target = tmp_path / ".claude" / "skills" / "task" / "SKILL.md"
    content = target.read_text(encoding="utf-8")
    assert "name: task" in content
    assert "description: Main task orchestrator." in content


def test_scaffold_native_skill_exports_flattens_and_strips_for_cursor(tmp_path):
    skill_dir = tmp_path / ".maika" / "skills" / "intent-analysis"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: intent-analysis\ndescription: Classify intent.\n---\n\nBody.\n",
        encoding="utf-8",
    )
    plugins = [{"name": "intent-analysis", "type": "skill", "copy_dir": True,
                "output": ".maika/skills/intent-analysis/"}]
    platform = _FakePlatform({"dir": ".cursor/commands", "strip_frontmatter": True, "flatten": True})

    scaffold_native_skill_exports(plugins, tmp_path, platform, verbose=False)

    target = tmp_path / ".cursor" / "commands" / "intent-analysis.md"
    content = target.read_text(encoding="utf-8")
    assert not content.startswith("---")
    assert "Classify intent." in content
    assert "Body." in content


def test_scaffold_native_skill_exports_skips_missing_frontmatter(tmp_path):
    workflow_path = tmp_path / ".maika" / "workflows" / "tdd.md"
    workflow_path.parent.mkdir(parents=True)
    workflow_path.write_text("# /tdd\n\nNo frontmatter here.\n", encoding="utf-8")
    plugins = [{"name": "workflow-tdd", "type": "workflow", "output": ".maika/workflows/tdd.md"}]
    platform = _FakePlatform({"dir": ".claude/skills", "strip_frontmatter": False, "flatten": False})

    stats = scaffold_native_skill_exports(plugins, tmp_path, platform, verbose=False)

    assert stats == {"exported": 0, "skipped": 1}
    assert not (tmp_path / ".claude" / "skills" / "tdd").exists()


def test_scaffold_native_skill_exports_ignores_non_skill_workflow_plugins(tmp_path):
    plugins = [{"name": "rules-manifest", "type": "rule", "output": ".maika/rules/RULES.md"}]
    platform = _FakePlatform({"dir": ".claude/skills", "strip_frontmatter": False, "flatten": False})

    stats = scaffold_native_skill_exports(plugins, tmp_path, platform, verbose=False)

    assert stats == {"exported": 0, "skipped": 0}


def test_canonical_framework_root_matches_generic_platform():
    from cli import CANONICAL_FRAMEWORK_ROOT
    from cli.platforms import get_platform

    # The canonical default must equal the base/generic platform's root so the
    # constant can never drift from the real default.
    assert CANONICAL_FRAMEWORK_ROOT == get_platform("generic").framework_root


def test_read_resolved_config_returns_none_for_top_level_scalar(tmp_path):
    # A stray same-named file whose YAML is a bare scalar must not crash.
    from cli.scaffold import _read_resolved_config

    p = tmp_path / "resolved-config.yaml"
    p.write_text("just a bare string\n", encoding="utf-8")
    assert _read_resolved_config(p) is None


def test_generate_resolved_config_sweeps_stale_maika_config(tmp_path):
    from cli.platforms import get_platform

    # Stale Maika-generated config left from a previous (generic) install.
    stale = tmp_path / ".maika" / "resolved-config.yaml"
    stale.parent.mkdir(parents=True)
    stale.write_text(
        "resolved:\n  platform: generic\n  framework_root: .maika\n",
        encoding="utf-8",
    )
    # An unrelated file that merely shares the name must be preserved.
    bystander = tmp_path / ".claude" / "resolved-config.yaml"
    bystander.parent.mkdir(parents=True)
    bystander.write_text("other: value\n", encoding="utf-8")

    generate_resolved_config(tmp_path, get_platform("antigravity"), ["codebase-memory-mcp"], "python")

    assert (tmp_path / ".agents" / "resolved-config.yaml").exists()   # active written
    assert not stale.exists()                                         # stale swept
    assert bystander.read_text(encoding="utf-8") == "other: value\n"  # bystander kept


def test_generate_resolved_config_sweep_survives_directory_at_candidate(tmp_path):
    from cli.platforms import get_platform

    # A directory sitting where a candidate resolved-config.yaml would be must
    # not crash the sweep (best-effort: unreadable/non-file candidates skipped).
    bogus = tmp_path / ".maika" / "resolved-config.yaml"
    bogus.mkdir(parents=True)

    generate_resolved_config(tmp_path, get_platform("antigravity"), ["codebase-memory-mcp"], "python")

    assert (tmp_path / ".agents" / "resolved-config.yaml").exists()  # active written
    assert bogus.is_dir()  # bogus directory left untouched


def test_manifest_omits_framework_dev_only_tools(maika_root):
    # skill-lint là tool authoring của repo framework (R7; skill-lint-pilot
    # design đã chốt lint không scaffold xuống downstream).
    manifest = load_manifest(maika_root)
    by_name = {p["name"]: p for p in manifest["plugins"]}
    assert "skill-lint" not in by_name


def test_manifest_ships_skill_index_data_and_tools_readme(maika_root):
    # Consumers: bootstrap.md READ skills/skill-index.yaml; meta-prompt trỏ tools/README.md (R1).
    manifest = load_manifest(maika_root)
    by_name = {p["name"]: p for p in manifest["plugins"]}
    assert by_name["skill-index-data"]["source"] == "skills/skill-index.yaml"
    assert by_name["skill-index-data"]["output"] == "{{ platform.framework_root }}/skills/skill-index.yaml"
    assert not by_name["skill-index-data"].get("copy_dir")
    assert by_name["tools-readme"]["source"] == "tools/README.md"
    assert by_name["tools-readme"]["output"] == "{{ platform.framework_root }}/tools/README.md"
