"""System-model validator (harness plan §20, M10) — cross-surface link checks."""

from pathlib import Path

from cli.agent_content.system_model import validate_system_model

REPO = Path(__file__).resolve().parents[2]
FRAMEWORK = REPO / ".maika"


def test_repository_system_model_is_valid():
    assert validate_system_model(FRAMEWORK) == []


def _with_mutation(rel: str, old: str, new: str) -> list[str]:
    path = FRAMEWORK / rel
    original = path.read_text(encoding="utf-8")
    assert old in original, f"mutation anchor missing in {rel}: {old!r}"
    try:
        path.write_text(original.replace(old, new, 1), encoding="utf-8")
        return validate_system_model(FRAMEWORK)
    finally:
        path.write_text(original, encoding="utf-8")


def test_unconsumed_trigger_detected():
    errors = _with_mutation(
        "profiles/capability-registry.yaml",
        "triggers:",
        "triggers:\n  cosmic_alignment:\n    description: never consumed.",
    )
    assert any("cosmic_alignment" in e and "no skill consumes" in e for e in errors)


def test_broken_persistence_chain_detected():
    errors = _with_mutation(
        "skills/database-explorer/SKILL.md",
        "- database-request\n- database-context",
        "- database-context",
    )
    assert any("database-explorer does not declare gate 'database-request'" in e
               for e in errors)


def test_router_losing_trace_gate_detected():
    errors = _with_mutation(
        "config/workflow-router.yaml",
        "provider-invocations, trace-request, trace-evidence]",
        "provider-invocations, trace-request]",
    )
    assert any("missing completion gate 'trace-evidence'" in e for e in errors)


def test_workflow_owner_must_be_registered_provider():
    errors = _with_mutation(
        "config/external-workflows.yaml",
        "owner: codebase-memory-mcp",
        "owner: graph-oracle",
    )
    assert any("graph-oracle" in e and "not a registered provider" in e for e in errors)


def test_cli_action_registered(capsys):
    from cli.commands.content import run_content

    assert run_content("validate-system-model", target_dir=str(REPO)) == 0
    assert "system model valid" in capsys.readouterr().out
