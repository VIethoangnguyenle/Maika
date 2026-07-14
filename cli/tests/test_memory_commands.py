from pathlib import Path

import yaml

from cli.commands.memory import remember, run_memory


def _entries(target: Path):
    path = target / ".maika/knowledge/preferences/project-preferences.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))["entries"]


def test_remember_without_active_change_creates_no_task_workspace(tmp_path):
    code, preference_id = remember(
        "Validation chain classes use the Processor suffix.", target_dir=str(tmp_path),
        scope="project", preference_type="naming",
    )
    assert code == 0
    assert preference_id.startswith("PREF-")
    assert not (tmp_path / ".maika/changes").exists()
    entry = _entries(tmp_path)[0]
    assert entry["source"] == "explicit_user"
    assert entry["confirmed"] is True
    assert entry["provenance"]["user_statement"].startswith("Validation")


def test_list_and_forget_preference(tmp_path, capsys):
    _, preference_id = remember("Prefer small adapters.", target_dir=str(tmp_path))
    assert run_memory("list", target_dir=str(tmp_path)) == 0
    assert preference_id in capsys.readouterr().out
    assert run_memory("forget", target_dir=str(tmp_path), preference_id=preference_id) == 0
    assert _entries(tmp_path)[0]["status"] == "forgotten"


def test_promotion_records_intent_but_does_not_mutate_core_rules(tmp_path):
    rules = tmp_path / ".maika/rules/RULES.md"
    rules.parent.mkdir(parents=True)
    rules.write_text("original", encoding="utf-8")
    _, preference_id = remember("Prefer Processor suffix.", target_dir=str(tmp_path))
    assert run_memory(
        "promote", target_dir=str(tmp_path), preference_id=preference_id,
        promotion_target="project-conventions-review",
    ) == 0
    entry = _entries(tmp_path)[0]
    assert entry["status"] == "promoted"
    assert entry["promotion"]["target"] == "project-conventions-review"
    assert rules.read_text(encoding="utf-8") == "original"


def test_global_scope_is_rejected_without_safe_convention(tmp_path):
    code, preference_id = remember("Global preference", target_dir=str(tmp_path), scope="global")
    assert code == 2
    assert preference_id is None
