"""Tests for maika status."""

from cli.commands.status import run_status


def test_status_reads_skills_from_agents_root(tmp_path, capsys):
    root = tmp_path / ".agents"
    (root / "skills" / "intent-analysis").mkdir(parents=True)
    (root / "workflows").mkdir(parents=True)
    (root / "workflows" / "task.md").write_text("# task\n", encoding="utf-8")
    (root / "knowledge" / "active").mkdir(parents=True)
    (root / "knowledge" / "archive").mkdir(parents=True)
    (root / "knowledge" / "long-term").mkdir(parents=True)
    (root / "knowledge" / "long-term" / "author-dna.yaml").write_text(
        "meta:\n  status: approved\n", encoding="utf-8"
    )
    (root / "resolved-config.yaml").write_text(
        "resolved:\n"
        "  platform: antigravity\n"
        "  framework_root: .agents\n"
        "  mcps: []\n"
        "  language: python\n"
        "  framework_version: '3.0'\n",
        encoding="utf-8",
    )
    (tmp_path / "AGENTS.md").write_text("# agents\n", encoding="utf-8")

    run_status(str(tmp_path))

    out = capsys.readouterr().out
    assert "Platform:  antigravity" in out
    assert "intent-analysis" in out
    assert "/task" in out
    assert "Author DNA: approved" in out


def test_status_detects_legacy_install(tmp_path, capsys):
    target = tmp_path / "legacy"
    target.mkdir()
    (target / "AGENTS.md").write_text("# legacy\n", encoding="utf-8")

    run_status(target_dir=str(target))

    out = capsys.readouterr().out
    assert "No Maika installation" not in out
    assert "legacy installation" in out
