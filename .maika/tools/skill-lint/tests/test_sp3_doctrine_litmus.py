#!/usr/bin/env python3
"""L2/L3 — litmus tái hiện sự cố bao_cao_loi.md (UA-skip)."""
from pathlib import Path

SKILLS = Path(__file__).resolve().parents[3] / "skills"
RULES = Path(__file__).resolve().parents[3] / "rules" / "rules-tool.md"

def _read(p): return p.read_text(encoding="utf-8")

def test_l3_nc2_codebase_error_not_ua_down():
    # Lỗi Codebase MCP ≠ UA chết — phải có trong codebase-explorer + doctrine
    ce = _read(SKILLS / "codebase-explorer" / "SKILL.md")
    assert "≠ UA" in ce or "không khả dụng" in ce
    assert "≠ UA" in _read(RULES) or "không fallback grep cả hai" in _read(RULES)

def test_l2_requirement_analyst_has_probe_and_filter():
    ra = _read(SKILLS / "requirement-analyst" / "SKILL.md")
    assert "Đối chiếu codebase" in ra            # bước probe
    assert "Code-trả-lời-được" in ra              # bộ lọc Open-Q
    assert "domain_overview" in ra

def test_l2_explore_paths_consult_before_ask():
    for name in ("openspec-explore", "spec-extract"):
        body = _read(SKILLS / name / "SKILL.md")
        assert "standard: SP3" in body
        assert "UA-first" in body or "UA probe" in body
