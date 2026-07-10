from pathlib import Path
import importlib.util

import pytest

from cli.commands.init import run_init
from cli.platforms import get_platform


ROOT = Path(__file__).resolve().parents[2]
META = ROOT / ".maika" / "meta-prompt.md"
SPEC = importlib.util.spec_from_file_location(
    "gates_meta", ROOT / ".maika" / "tools" / "gate-check" / "gates.py"
)
GATES = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GATES)


def test_meta_prompt_has_constitution_and_identity():
    text = META.read_text(encoding="utf-8")
    required = [
        "Identity", "Core Mission", "Non-negotiable Principles",
        "Mandatory Bootstrap", "Canonical Knowledge Sources",
        "Authority Hierarchy", "Knowledge and MCP Operating Reflex",
        "Canonical Workflow", "Phase-specific Knowledge Obligations",
        "Context and Knowledge Slice Rules", "Role Boundaries",
        "Write Boundaries", "Evidence and Knowledge Trace",
        "Degradation and Stop Conditions", "Project Knowledge Learning Loop",
        "Skill Evolution Loop", "Load Order", "Handoff Contract",
    ]
    assert 120 <= len(text.splitlines()) <= 220
    assert all(heading in text for heading in required)
    assert "knowledge-grounded engineering agent" in text.lower()
    assert "Không có material decision" in text
    assert GATES.validate_meta_prompt_constitution(text).ok


@pytest.mark.parametrize("platform_key", ["codex", "claude-code", "antigravity", "generic"])
def test_every_platform_entry_point_receives_same_constitution(tmp_path, maika_root, platform_key):
    target = tmp_path / platform_key
    run_init(str(target), str(maika_root), platform_key, [], "python", assume_yes=True)
    entry = target / get_platform(platform_key).config_entry_point
    text = entry.read_text(encoding="utf-8")
    assert "knowledge-grounded engineering agent" in text
    assert "procedures/bootstrap.md" in text
    assert "Project Knowledge Learning Loop" in text
