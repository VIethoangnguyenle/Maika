"""Artifact authority registry — one authority per agent-facing decision (PR 1)."""

from pathlib import Path

from cli.agent_content.authority import load_registry, validate_registry

REPO = Path(__file__).resolve().parents[2]
FRAMEWORK = REPO / ".maika"


def test_in_tree_registry_is_valid():
    doc = load_registry(FRAMEWORK)
    assert validate_registry(doc) == []


def test_in_tree_registry_covers_critical_decisions():
    doc = load_registry(FRAMEWORK)
    decisions = set(doc["authorities"])
    required = {
        "current_change", "current_state", "intent", "exploration",
        "reconciliation", "specification", "implementation_plan",
        "task_queue", "verification", "durable_knowledge", "archive",
        "bootstrap_report",
    }
    missing = required - decisions
    assert not missing, f"registry misses critical decisions: {sorted(missing)}"


def test_in_tree_registry_deprecates_legacy_active_files():
    doc = load_registry(FRAMEWORK)
    deprecated = {entry["path"] for entry in doc["deprecated"]}
    for legacy in (
        "knowledge/active/REQUIREMENT.md",
        "knowledge/active/EXPLORE_CONTEXT.md",
        "knowledge/active/AGENT_TRANSPARENCY.md",
        "knowledge/active/TOKEN_LOG.md",
    ):
        assert legacy in deprecated, f"{legacy} must be listed as deprecated"


def _minimal_doc():
    return {
        "version": 1,
        "authorities": {
            "current_state": {"source": "changes/<change-id>/STATE.yaml"},
            "intent": {"source": "changes/<change-id>/INTENT.md"},
        },
        "deprecated": [
            {"path": "knowledge/active/REQUIREMENT.md",
             "replacement": "changes/<change-id>/INTENT.md"},
        ],
    }


def test_duplicate_authority_source_rejected():
    doc = _minimal_doc()
    doc["authorities"]["shadow_state"] = {"source": "changes/<change-id>/STATE.yaml"}
    errors = validate_registry(doc)
    assert any("shadow_state" in err and "current_state" in err for err in errors)


def test_authority_requires_source():
    doc = _minimal_doc()
    doc["authorities"]["broken"] = {}
    errors = validate_registry(doc)
    assert any("broken" in err for err in errors)


def test_deprecated_requires_path():
    doc = _minimal_doc()
    doc["deprecated"].append({"replacement": "changes/<change-id>/INTENT.md"})
    errors = validate_registry(doc)
    assert any("path" in err for err in errors)


def test_deprecated_path_must_not_be_an_authority_source():
    doc = _minimal_doc()
    doc["deprecated"].append({"path": "changes/<change-id>/STATE.yaml",
                              "replacement": "changes/<change-id>/INTENT.md"})
    errors = validate_registry(doc)
    assert any("both deprecated and an authority source" in err for err in errors)


def test_replacement_must_reference_known_authority_source():
    doc = _minimal_doc()
    doc["deprecated"].append({"path": "knowledge/active/GHOST.md",
                              "replacement": "changes/<change-id>/GHOST_NEW.md"})
    errors = validate_registry(doc)
    assert any("GHOST_NEW" in err for err in errors)


def test_replacement_none_means_discarded():
    doc = _minimal_doc()
    doc["deprecated"].append({"path": "knowledge/active/TOKEN_LOG.md", "replacement": None})
    assert validate_registry(doc) == []


def test_cli_validate_authority_on_repo(capsys):
    from cli.commands.content import run_content
    assert run_content("validate-authority", target_dir=str(REPO)) == 0
    out = capsys.readouterr().out
    assert "authority registry valid" in out


def test_cli_validate_authority_rejects_broken_registry(tmp_path, capsys):
    from cli.commands.content import run_content
    framework = tmp_path / ".maika" / "config"
    framework.mkdir(parents=True)
    (framework / "artifact-authority.yaml").write_text(
        "version: 1\nauthorities:\n  broken: {}\n", encoding="utf-8"
    )
    assert run_content("validate-authority", target_dir=str(tmp_path)) == 1
    assert "broken" in capsys.readouterr().out


def test_cli_validate_authority_missing_registry(tmp_path):
    from cli.commands.content import run_content
    assert run_content("validate-authority", target_dir=str(tmp_path)) == 2
