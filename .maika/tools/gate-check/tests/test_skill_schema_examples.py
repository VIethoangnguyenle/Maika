"""H-run C-1 (ngac, 2026-07-12): worker artifacts failed gates because
grounding-explorer/SKILL.md described TOOL_HEALTH/QUERY_PLAN in prose only —
the worker guessed a list shape and an off-enum status. These tests pin the
SKILL.md examples to the real validators so the docs cannot drift from gates."""
import importlib.util
import re
from pathlib import Path

_G = Path(__file__).resolve().parents[1] / "gates.py"
spec = importlib.util.spec_from_file_location("gates", _G)
gates = importlib.util.module_from_spec(spec); spec.loader.exec_module(gates)

SKILLS = Path(__file__).resolve().parents[3] / "skills"
SKILL = SKILLS / "grounding-explorer" / "SKILL.md"
_FENCE = re.compile(r"```yaml\n(.*?)```", re.DOTALL)


def _example(marker: str, skill: Path = SKILL) -> str:
    text = skill.read_text(encoding="utf-8")
    for block in _FENCE.findall(text):
        first = block.strip().splitlines()[0]
        if first.startswith("#") and marker in first:
            return block
    raise AssertionError(f"no ```yaml example marked '{marker}' in {skill.name}")


def test_tool_health_example_passes_gate():
    result = gates.validate_tool_health(_example("TOOL_HEALTH.yaml"))
    assert result.ok, result.reason


def test_query_plan_example_passes_gate():
    result = gates.validate_query_plan(_example("QUERY_PLAN.yaml"))
    assert result.ok, result.reason


def test_database_context_example_passes_gate():
    result = gates.validate_database_context(
        _example("DATABASE_CONTEXT.yaml", SKILLS / "database-explorer" / "SKILL.md")
    )
    assert result.ok, result.reason
