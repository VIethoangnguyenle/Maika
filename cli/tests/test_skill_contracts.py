"""Typed skill contracts — validation + router agreement (PR 4, plan §10)."""

import re
from pathlib import Path

import yaml

from cli.agent_content.skill_contract import (
    load_contracts,
    parse_contract,
    validate_skill_contracts,
)

REPO = Path(__file__).resolve().parents[2]
FRAMEWORK = REPO / ".maika"
SKILLS = FRAMEWORK / "skills"


def test_in_tree_contracts_are_valid():
    assert validate_skill_contracts(FRAMEWORK) == []


def test_every_skill_has_typed_routing():
    for name, contract in load_contracts(FRAMEWORK).items():
        assert contract is not None, name
        routing = contract.get("routing")
        assert isinstance(routing, dict), f"{name}: prose-only trigger is dead (plan §10)"
        assert routing.get("mode") in ("workflow", "dispatch", "conditional"), name
        assert (contract.get("capabilities") or {}).get("required"), name


def test_router_and_skills_agree_bidirectionally():
    """Break one side and the validator must flag the other."""
    contract_path = SKILLS / "writing-plan" / "SKILL.md"
    original = contract_path.read_text(encoding="utf-8")
    try:
        contract_path.write_text(
            original.replace("  - plan\n", "  - explore\n"), encoding="utf-8"
        )
        errors = validate_skill_contracts(FRAMEWORK)
        assert any("writing-plan" in err for err in errors)
    finally:
        contract_path.write_text(original, encoding="utf-8")


def test_unknown_capability_rejected():
    contract_path = SKILLS / "writing-spec" / "SKILL.md"
    original = contract_path.read_text(encoding="utf-8")
    try:
        contract_path.write_text(
            original.replace("business_knowledge_retrieval", "mind_reading"),
            encoding="utf-8",
        )
        errors = validate_skill_contracts(FRAMEWORK)
        assert any("mind_reading" in err for err in errors)
    finally:
        contract_path.write_text(original, encoding="utf-8")


def _with_mutation(skill: str, old: str, new: str) -> list[str]:
    """Apply one frontmatter mutation, validate, restore. Returns validator errors."""
    contract_path = SKILLS / skill / "SKILL.md"
    original = contract_path.read_text(encoding="utf-8")
    assert old in original, f"mutation anchor missing in {skill}: {old!r}"
    try:
        contract_path.write_text(original.replace(old, new, 1), encoding="utf-8")
        return validate_skill_contracts(FRAMEWORK)
    finally:
        contract_path.write_text(original, encoding="utf-8")


def test_unknown_trigger_rejected():
    errors = _with_mutation(
        "grounding-explorer", "- blast_radius_required", "- gut_feeling"
    )
    assert any("unknown trigger gut_feeling" in err for err in errors)


def test_capability_in_required_and_conditional_rejected():
    # historical_context_retrieval is already required for grounding-explorer;
    # redeclaring it as conditional creates the required+conditional conflict.
    errors = _with_mutation(
        "grounding-explorer",
        "  conditional:\n    symbolic_code_navigation:",
        "  conditional:\n    historical_context_retrieval:\n      triggers:\n"
        "      - reviewer_counter_evidence\n    symbolic_code_navigation:",
    )
    assert any(
        "historical_context_retrieval cannot be both required and conditional" in err
        for err in errors
    )


def test_capability_in_one_of_and_conditional_rejected():
    # historical_context_retrieval is added to both one_of and conditional so the
    # same capability is declared in two mutually exclusive groups.
    errors = _with_mutation(
        "grounding-explorer",
        "    - call_chain_trace\n  conditional:\n    symbolic_code_navigation:",
        "    - call_chain_trace\n    - historical_context_retrieval\n  conditional:\n"
        "    historical_context_retrieval:\n      triggers:\n"
        "      - reviewer_counter_evidence\n    symbolic_code_navigation:",
    )
    assert any("cannot be both one_of and conditional" in err for err in errors)


def test_empty_one_of_group_rejected():
    errors = _with_mutation(
        "grounding-explorer",
        "  one_of:\n    structured_trace:\n    - architecture_discovery\n"
        "    - domain_flow_trace\n    - call_chain_trace\n",
        "  one_of:\n    structured_trace: []\n",
    )
    assert any("one_of group structured_trace must be a non-empty list" in err
               for err in errors)


def test_conditional_without_triggers_rejected():
    errors = _with_mutation(
        "grounding-explorer",
        "    impact_analysis:\n      triggers:\n      - blast_radius_required\n",
        "    impact_analysis: {}\n",
    )
    assert any("impact_analysis must declare >=1 trigger" in err for err in errors)


def test_unknown_capabilities_key_rejected():
    errors = _with_mutation("grounding-explorer", "  one_of:\n", "  one_off:\n")
    assert any("unknown capabilities keys ['one_off']" in err for err in errors)


def test_output_without_authority_rejected():
    contract_path = SKILLS / "writing-spec" / "SKILL.md"
    original = contract_path.read_text(encoding="utf-8")
    try:
        contract_path.write_text(
            original.replace("- SPEC.md", "- GHOST.md"), encoding="utf-8"
        )
        errors = validate_skill_contracts(FRAMEWORK)
        assert any("GHOST.md" in err for err in errors)
    finally:
        contract_path.write_text(original, encoding="utf-8")


def test_skill_index_v2_carries_typed_contract():
    index = yaml.safe_load((SKILLS / "skill-index.yaml").read_text(encoding="utf-8"))
    by_name = {entry["name"]: entry for entry in index["skills"]}
    assert set(by_name) == set(load_contracts(FRAMEWORK))
    for name, contract in load_contracts(FRAMEWORK).items():
        entry = by_name[name]
        assert entry.get("routing") == contract.get("routing"), name
        assert entry.get("capabilities") == contract.get("capabilities"), name
        assert entry.get("outputs") == contract.get("outputs"), name
        assert entry.get("gates") == contract.get("gates"), name


def test_index_regeneration_is_deterministic(tmp_path):
    from cli.knowledge_control import _regenerate_skill_index

    staging = tmp_path / "fw" / "skills"
    for skill_dir in SKILLS.iterdir():
        if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
            dest = staging / skill_dir.name
            dest.mkdir(parents=True)
            (dest / "SKILL.md").write_text(
                (skill_dir / "SKILL.md").read_text(encoding="utf-8"), encoding="utf-8"
            )
    generated = _regenerate_skill_index(tmp_path / "fw").read_text(encoding="utf-8")
    committed = (SKILLS / "skill-index.yaml").read_text(encoding="utf-8")
    assert generated == committed, "skill-index.yaml is stale; regenerate it"


def test_cli_validate_skills(capsys):
    from cli.commands.content import run_content

    assert run_content("validate-skills", target_dir=str(REPO)) == 0
    assert "skill contracts valid" in capsys.readouterr().out


def test_version_bump_regex_still_matches_new_frontmatter():
    # promote_skill_candidate rewrites the version line with this regex.
    pattern = re.compile(r"(?m)^version:\s*['\"]?[^'\"\n]+['\"]?\s*$")
    for skill_md in SKILLS.glob("*/SKILL.md"):
        assert pattern.search(skill_md.read_text(encoding="utf-8")), skill_md
