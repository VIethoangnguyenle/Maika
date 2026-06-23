"""Guard: architecture-reviewer uses UA as an active probe for topology, never raw UA names."""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL = REPO_ROOT / ".maika" / "skills" / "architecture-reviewer" / "SKILL.md"

RAW_UA = re.compile(r"mcp__understand-anything__|mcp_understand-anything_")


def _text():
    return SKILL.read_text(encoding="utf-8")


def test_step4_uses_ua_domain_ops_as_active_probe():
    text = _text()
    # boundary/topology/coupling questions must actively call UA, not just flag it
    assert "{{ tools.domain_relationships }}" in text, "Bước 4 không gọi UA domain_relationships"
    assert "{{ tools.domain_flow }}" in text, "Bước 4/6 không gọi UA domain_flow"


def test_no_raw_ua_tool_names():
    assert RAW_UA.search(_text()) is None, "skill hardcodes raw UA MCP tool name"


def test_ua_described_as_active_probe_not_only_flag():
    text = _text()
    assert "probe chủ động" in text, "UA vẫn bị mô tả chỉ là cờ confidence"


def test_codebase_must_not_shape_architecture():
    text = _text()
    assert "KHÔNG" in text and "định hình" in text, "thiếu doctrine: codebase không định hình kiến trúc"
