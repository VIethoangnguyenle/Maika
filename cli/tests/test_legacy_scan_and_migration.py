"""Legacy active-memory scan + migration (PR 6, plan §23)."""

from pathlib import Path

import yaml

from cli.agent_content.legacy import (
    apply_legacy_migration,
    plan_legacy_migration,
    scan_legacy_references,
)

REPO = Path(__file__).resolve().parents[2]
FRAMEWORK = REPO / ".maika"


def test_agent_facing_content_is_legacy_clean():
    findings = scan_legacy_references(FRAMEWORK)
    assert findings == [], "\n".join(
        f"{f['file']}:{f['line']} references {f['token']}" for f in findings
    )


def test_scan_flags_seeded_reference(tmp_path):
    fw = tmp_path / ".maika"
    (fw / "rules" / "core").mkdir(parents=True)
    (fw / "rules" / "core" / "flow.md").write_text(
        "Đọc knowledge/active/REQUIREMENT.md trước khi spec\n", encoding="utf-8"
    )
    findings = scan_legacy_references(fw)
    assert any(f["token"] == "REQUIREMENT.md" for f in findings)


def test_scan_flags_legacy_template_files(tmp_path):
    fw = tmp_path / ".maika"
    templates = fw / "knowledge" / "templates"
    templates.mkdir(parents=True)
    (templates / "TOKEN_LOG.tpl.md").write_text("| pha | token |\n", encoding="utf-8")
    findings = scan_legacy_references(fw)
    assert any("template file" in f["token"] for f in findings)


def _legacy_target(tmp_path, with_active_change=True):
    fw = tmp_path / ".maika"
    active = fw / "knowledge" / "active"
    active.mkdir(parents=True)
    (active / "REQUIREMENT.md").write_text("# yêu cầu cũ\n", encoding="utf-8")
    (active / "EXPLORE_CONTEXT.md").write_text("# explore cũ\n", encoding="utf-8")
    (active / "AGENT_TRANSPARENCY.md").write_text("Pha 2 DONE\n", encoding="utf-8")
    (active / "TOKEN_LOG.md").write_text("| pha | 12K |\n", encoding="utf-8")
    if with_active_change:
        ws = fw / "changes" / "C-9"
        ws.mkdir(parents=True)
        (ws / "STATE.yaml").write_text(
            yaml.safe_dump({"version": 1, "change_id": "C-9", "state": "EXECUTING"}),
            encoding="utf-8",
        )
    return fw


def test_migration_plan_maps_into_single_active_change(tmp_path):
    fw = _legacy_target(tmp_path)
    moves = {m["source"].name: m["target"] for m in plan_legacy_migration(fw)}
    ws = fw / "changes" / "C-9"
    assert moves["REQUIREMENT.md"] == ws / "INTENT.md"
    assert moves["EXPLORE_CONTEXT.md"] == ws / "exploration" / "LEGACY_IMPORT.md"
    assert moves["AGENT_TRANSPARENCY.md"] == ws / "generated" / "LEGACY_EVENT_LOG.md"
    assert "legacy-active-import" in str(moves["TOKEN_LOG.md"])


def test_migration_never_overwrites_existing_intent(tmp_path):
    fw = _legacy_target(tmp_path)
    ws = fw / "changes" / "C-9"
    (ws / "INTENT.md").write_text("# intent thật\n", encoding="utf-8")
    moves = {m["source"].name: m["target"] for m in plan_legacy_migration(fw)}
    assert moves["REQUIREMENT.md"] == ws / "INTENT.legacy.md"


def test_migration_without_active_change_archives(tmp_path):
    fw = _legacy_target(tmp_path, with_active_change=False)
    for move in plan_legacy_migration(fw):
        assert "legacy-active-import" in str(move["target"])


def test_apply_moves_files(tmp_path):
    fw = _legacy_target(tmp_path)
    moves = plan_legacy_migration(fw)
    apply_legacy_migration(moves)
    assert not (fw / "knowledge" / "active" / "REQUIREMENT.md").exists()
    assert (fw / "changes" / "C-9" / "INTENT.md").read_text(encoding="utf-8") == "# yêu cầu cũ\n"
    assert (fw / "archive" / "legacy-active-import" / "TOKEN_LOG.md").exists()


def test_cli_scan_legacy_and_migrate(tmp_path, capsys):
    from cli.commands.content import run_content

    assert run_content("scan-legacy", target_dir=str(REPO)) == 0
    assert "legacy-clean" in capsys.readouterr().out

    fw = _legacy_target(tmp_path)
    assert run_content("migrate-legacy", target_dir=str(tmp_path)) == 0
    out = capsys.readouterr().out
    assert "dry-run" in out
    assert (fw / "knowledge" / "active" / "REQUIREMENT.md").exists()  # dry-run không mutate

    assert run_content("migrate-legacy", target_dir=str(tmp_path), apply=True) == 0
    assert not (fw / "knowledge" / "active" / "REQUIREMENT.md").exists()
