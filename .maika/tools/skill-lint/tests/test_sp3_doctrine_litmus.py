#!/usr/bin/env python3
"""W2 doctrine litmus for canonical reasoning skills."""
from pathlib import Path

SKILLS = Path(__file__).resolve().parents[3] / "skills"
RULES = Path(__file__).resolve().parents[3] / "rules" / "rules-tool.md"


def _read(path):
    return path.read_text(encoding="utf-8")


def test_grounding_explorer_uses_capability_ids():
    body = _read(SKILLS / "grounding-explorer" / "SKILL.md")
    assert "architecture_discovery" in body
    assert "exact_source_inspection" in body


def test_intent_analysis_routes_standard_changes_to_grounding():
    body = _read(SKILLS / "intent-analysis" / "SKILL.md")
    assert "standard and architectural" in body.lower()
    assert "grounding-explorer" in body


def test_rules_tool_declares_capability_boundary():
    body = _read(RULES)
    assert "capability IDs" in body
    assert "platform adapters" in body
