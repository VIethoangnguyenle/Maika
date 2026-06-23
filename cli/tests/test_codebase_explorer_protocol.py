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


TASK_WF = REPO_ROOT / ".maika" / "workflows" / "task.md"


def test_taskmd_phase1_points_to_altitude_protocol():
    text = TASK_WF.read_text(encoding="utf-8")
    assert "altitude" in text.lower() or "độ cao" in text.lower(), (
        "task.md Pha 1 chưa trỏ tới altitude-routing protocol"
    )


def test_taskmd_transparency_lists_ua_domain_ops():
    text = TASK_WF.read_text(encoding="utf-8")
    for op in ("domain_overview", "domain_flow", "domain_relationships"):
        assert "{{ tools.%s }}" % op in text, f"checklist thiếu {{{{ tools.{op} }}}}"


def test_taskmd_has_no_raw_ua_tool_names():
    assert RAW_UA.search(TASK_WF.read_text(encoding="utf-8")) is None


def test_skill_has_cue_cards_block():
    text = _text()
    assert "Cue Cards" in text, "missing Cue Cards habit block"
    # cue table must bind a base-class rabbit-hole symptom to a UA routine
    assert "base/abstract class" in text or "BaseHandler" in text
    assert "{{ tools.domain_flow }}" in text


def test_skill_dropped_structured_first_hedge():
    text = _text()
    assert 'Quy tắc tinh chỉnh "structured-first"' not in text, (
        "old structured-first hedge still present — it pulls agent back to codebase"
    )


def test_output_schema_allows_ua_identifier():
    text = _text()
    # entry-point / integration components may be sourced from UA, not only node_id
    assert "identifier kiểu UA" in text or "UA identifier" in text
