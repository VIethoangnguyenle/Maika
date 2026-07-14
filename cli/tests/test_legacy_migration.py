from pathlib import Path

import yaml

from cli.commands.lifecycle import run_migrate


def _legacy(root: Path, platform: str = "codex") -> Path:
    legacy = root / ".agents"
    (legacy / "knowledge/long-term").mkdir(parents=True)
    (legacy / "resolved-config.yaml").write_text(yaml.safe_dump({
        "resolved": {"platform": platform, "framework_root": ".agents",
                     "mcps": [], "language": "python"},
    }), encoding="utf-8")
    return legacy


def test_migrate_apply_installs_core_and_copies_project_knowledge(tmp_path):
    legacy = _legacy(tmp_path)
    (legacy / "knowledge/long-term/team.md").write_text("legacy knowledge\n", encoding="utf-8")

    assert run_migrate(str(tmp_path), apply=True)["exit_code"] == 0

    copied = tmp_path / ".maika/knowledge/long-term/team.md"
    assert copied.read_text(encoding="utf-8") == "legacy knowledge\n"
    assert (tmp_path / ".maika/config/project.yaml").is_file()
    assert (legacy / "knowledge/long-term/team.md").is_file()  # compatibility read-only


def test_migrate_preserves_divergent_conflict_for_decision(tmp_path):
    from cli.commands.init import run_init

    repo = Path(__file__).resolve().parents[2]
    run_init(str(tmp_path), str(repo), "codex", [], "python", True)
    legacy = _legacy(tmp_path)
    canonical = tmp_path / ".maika/knowledge/long-term/team.md"
    canonical.write_text("canonical\n", encoding="utf-8")
    (legacy / "knowledge/long-term/team.md").write_text("legacy\n", encoding="utf-8")

    result = run_migrate(str(tmp_path), apply=True)
    assert result["status"] == "partial-safe" and result["mutation"] is True
    assert result["diagnostic_mutation"] is True
    assert result["project_data_mutation"] is False
    assert canonical.read_text(encoding="utf-8") == "canonical\n"
    conflicts = yaml.safe_load(
        (tmp_path / ".maika/runtime/migration-conflicts.yaml").read_text(encoding="utf-8")
    )
    assert conflicts["conflicts"][0]["decision_required"] is True
    assert len(conflicts["conflicts"][0]["hashes"]) == 2


def test_conflict_blocks_without_copying_the_safe_artifact(tmp_path):
    """A conflict must block the whole migration — not commit the non-conflicting
    artifacts alongside the report (F10b: no mutate-then-block)."""
    from cli.commands.init import run_init

    repo = Path(__file__).resolve().parents[2]
    run_init(str(tmp_path), str(repo), "codex", [], "python", True)
    legacy = _legacy(tmp_path)
    # team.md diverges from canonical (a conflict); safe.md is legacy-only (safe).
    canonical = tmp_path / ".maika/knowledge/long-term/team.md"
    canonical.write_text("canonical\n", encoding="utf-8")
    (legacy / "knowledge/long-term/team.md").write_text("legacy\n", encoding="utf-8")
    (legacy / "knowledge/long-term/safe.md").write_text("safe legacy\n", encoding="utf-8")

    result = run_migrate(str(tmp_path), apply=True)

    assert result["status"] == "partial-safe" and result["diagnostic_mutation"] is True
    assert canonical.read_text(encoding="utf-8") == "canonical\n"
    # the safe artifact must NOT have been copied while the migration was blocked
    assert not (tmp_path / ".maika/knowledge/long-term/safe.md").exists()


def _blocked_conflict(tmp_path: Path):
    from cli.commands.init import run_init
    repo = Path(__file__).resolve().parents[2]
    run_init(str(tmp_path), str(repo), "codex", [], "python", True)
    legacy = _legacy(tmp_path)
    canonical = tmp_path / ".maika/knowledge/long-term/team.md"
    canonical.write_text("canonical\n", encoding="utf-8")
    (legacy / "knowledge/long-term/team.md").write_text("legacy\n", encoding="utf-8")
    assert run_migrate(str(tmp_path), apply=True)["status"] == "partial-safe"
    return canonical


def test_migrate_resolve_applies_chosen_candidate(tmp_path):
    canonical = _blocked_conflict(tmp_path)
    decision = tmp_path / "decision.yaml"
    decision.write_text(yaml.safe_dump({"version": 1, "resolutions": [
        {"logical_artifact": "knowledge/long-term/team.md",
         "choose": ".agents/knowledge/long-term/team.md"}]}), encoding="utf-8")

    result = run_migrate(str(tmp_path), resolve=str(decision))

    assert result["status"] == "committed" and result["mutation"] is True
    assert canonical.read_text(encoding="utf-8") == "legacy\n"  # resolved to chosen version


def test_migrate_resolve_rejects_non_candidate_choice(tmp_path):
    canonical = _blocked_conflict(tmp_path)
    (tmp_path / "evil.md").write_text("evil\n", encoding="utf-8")
    decision = tmp_path / "decision.yaml"
    decision.write_text(yaml.safe_dump({"version": 1, "resolutions": [
        {"logical_artifact": "knowledge/long-term/team.md", "choose": "evil.md"}]}), encoding="utf-8")

    result = run_migrate(str(tmp_path), resolve=str(decision))

    assert result["status"] == "blocked" and result["mutation"] is False
    assert canonical.read_text(encoding="utf-8") == "canonical\n"  # no injection, unchanged


def test_migrate_resolve_without_report_is_noop(tmp_path):
    from cli.commands.init import run_init
    repo = Path(__file__).resolve().parents[2]
    run_init(str(tmp_path), str(repo), "codex", [], "python", True)
    decision = tmp_path / "d.yaml"
    decision.write_text(yaml.safe_dump({"version": 1, "resolutions": []}), encoding="utf-8")
    assert run_migrate(str(tmp_path), resolve=str(decision))["status"] == "no-op"


def test_cleanup_legacy_requires_explicit_flag_and_preserves_native_config(tmp_path):
    legacy = _legacy(tmp_path)
    (legacy / "knowledge/long-term/team.md").write_text("knowledge\n", encoding="utf-8")
    (legacy / "hooks.json").write_text('{"team": true}\n', encoding="utf-8")
    assert run_migrate(str(tmp_path), apply=True)["exit_code"] == 0
    assert (legacy / "knowledge").is_dir()

    assert run_migrate(str(tmp_path), apply=True, cleanup_legacy=True)["exit_code"] == 0
    assert not (legacy / "knowledge").exists()
    assert (legacy / "hooks.json").read_text(encoding="utf-8") == '{"team": true}\n'
