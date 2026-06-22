"""Guard: codebase-explorer protocol uses abstract ops, never raw UA tool names."""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL = REPO_ROOT / ".maika" / "skills" / "codebase-explorer" / "SKILL.md"

# Raw provider tool names must NOT appear in operational skill prose.
RAW_UA = re.compile(r"mcp__understand-anything__|mcp_understand-anything_")


def _text():
    return SKILL.read_text(encoding="utf-8")


def test_skill_references_ua_domain_ops_via_template():
    text = _text()
    for op in ("domain_overview", "domain_flow", "domain_relationships"):
        assert "{{ tools.%s }}" % op in text, f"missing {{{{ tools.{op} }}}}"


def test_skill_has_no_raw_ua_tool_names():
    assert RAW_UA.search(_text()) is None, "skill hardcodes raw UA MCP tool name"


def test_skill_has_protocol_sections():
    text = _text()
    for marker in (
        "Định tuyến theo độ cao",
        "Cổng độ phức tạp",
        "Golden Path",
        "Bản đồ năng lực",
        "Degradation",
        "Source attribution",
    ):
        assert marker in text, f"missing section: {marker}"
