"""W9 lifecycle: status --json, uninstall, repair, migrate.

Reuses the W2 transaction engine (delete plan → Transaction), W3 shared-host
strip, and W5 doctor findings. Uninstall preserves user data by default; repair
only applies safe finding-specific actions; migrate never mutates on --dry-run.
"""

import json
from pathlib import Path

from cli.commands.init import run_init
from cli.commands.lifecycle import run_migrate, run_repair, run_uninstall
from cli.commands.status import run_status

REPO = Path(__file__).resolve().parents[2]


def _init(target: Path):
    run_init(target_dir=str(target), maika_root=str(REPO), platform_key="claude-code",
             selected_mcps=[], language="python", assume_yes=True)


def test_status_json_is_parseable_snapshot(tmp_path, capsys):
    _init(tmp_path)
    capsys.readouterr()
    run_status(str(tmp_path), as_json=True)
    snap = json.loads(capsys.readouterr().out)
    assert snap["platform"] == "claude-code"
    assert snap["framework_root"] == ".maika"
    assert "writing-plans" in snap["skills"] or snap["skills"]  # some skills present
    assert snap["enabled_platforms"] == ["claude-code"]


def test_uninstall_preserves_user_data_and_strips_host(tmp_path):
    _init(tmp_path)
    note = tmp_path / ".maika" / "knowledge" / "active" / "MYNOTES.md"
    note.write_text("my work\n", encoding="utf-8")
    (tmp_path / ".maika" / "changes" / "C-1").mkdir(parents=True)
    (tmp_path / ".maika" / "changes" / "C-1" / "STATE.yaml").write_text("state: INTAKE\n", encoding="utf-8")

    result = run_uninstall(str(tmp_path))
    assert result["status"] == "committed" and result["exit_code"] == 0

    assert not (tmp_path / ".maika" / "rules" / "RULES.md").exists()   # framework removed
    assert note.exists() and note.read_text() == "my work\n"          # user data preserved
    assert (tmp_path / ".maika" / "changes" / "C-1" / "STATE.yaml").exists()
    assert "maika:begin" not in (tmp_path / "CLAUDE.md").read_text(encoding="utf-8") \
        if (tmp_path / "CLAUDE.md").exists() else True


def test_uninstall_purge_removes_everything(tmp_path):
    _init(tmp_path)
    (tmp_path / ".maika" / "knowledge" / "active" / "MYNOTES.md").write_text("x", encoding="utf-8")
    result = run_uninstall(str(tmp_path), purge_project_data=True)
    assert result["status"] == "committed" and result["mutation"] is True
    assert not (tmp_path / ".maika").exists()


def test_repair_restores_corrupted_managed_entrypoint(tmp_path):
    _init(tmp_path)
    entry = tmp_path / "CLAUDE.md"
    entry.write_text("# hand-written, block deleted\n", encoding="utf-8")
    # doctor would flag managed-entrypoint as not-ok; repair re-renders it
    assert run_repair(str(tmp_path), "managed-entrypoint", maika_root=str(REPO)) == 0
    assert "maika:begin" in entry.read_text(encoding="utf-8")


def test_repair_unknown_finding_is_refused(tmp_path):
    _init(tmp_path)
    assert run_repair(str(tmp_path), "no-such-finding", maika_root=str(REPO)) == 2


def test_migrate_dry_run_does_not_mutate(tmp_path, capsys):
    _init(tmp_path)
    before = {p.relative_to(tmp_path).as_posix(): p.read_bytes()
              for p in sorted((tmp_path / ".maika").rglob("*")) if p.is_file()}
    assert run_migrate(str(tmp_path), apply=False)["status"] == "no-op"
    after = {p.relative_to(tmp_path).as_posix(): p.read_bytes()
             for p in sorted((tmp_path / ".maika").rglob("*")) if p.is_file()}
    assert before == after
    out = capsys.readouterr().out
    assert ".maika" in out  # inventory reported
