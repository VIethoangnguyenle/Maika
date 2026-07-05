"""Regression tests for ASCII diagram guidance in Maika skills/templates."""

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent.parent


def read_text(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def test_spec_extract_requires_ascii_diagram_capture():
    skill = read_text(".maika/skills/spec-extract/SKILL.md")
    detail = read_text(".maika/skills/spec-extract/references/quy-trinh-chi-tiet.md")
    schema = read_text(".maika/skills/spec-extract/references/output-schema.md")
    requirement_template = read_text(".maika/knowledge/templates/REQUIREMENT.tpl.md")

    assert "#### ASCII Flow / State Diagram" in skill
    assert "flow, state, integration, callback, job, hoặc data path" in skill
    assert "Bước 5c — Vẽ ASCII Flow / State Diagram" in detail
    assert "Diagram phải đánh dấu `unknown`, `assumption`, hoặc `needs BA/PO confirmation`" in detail
    assert "#### ASCII Flow / State Diagram" in schema
    assert "## Flow / State Diagram" in requirement_template
    assert "Bắt buộc khi task có flow, state, integration, callback, job, hoặc data path" in requirement_template


def test_openspec_explore_uses_visual_stance_and_capture():
    skill = read_text(".maika/skills/openspec-explore/SKILL.md")
    patterns = read_text(".maika/skills/openspec-explore/references/explore-patterns.md")
    explore_template = read_text(".maika/knowledge/templates/EXPLORE_CONTEXT.tpl.md")

    assert "Explore là stance, không phải workflow cứng" in skill
    assert "Visualize tự do" in skill
    assert "capture insight đó vào `EXPLORE_CONTEXT.md`" in skill
    assert "Do visualize" in skill
    assert "ASCII diagram bắt buộc khi có flow/state/data path" in patterns
    assert "vấn đề user nêu" in patterns
    assert "ASCII diagram bắt buộc khi có flow/state/data path" in explore_template
    assert "Danh sách module chỉ đủ khi không có sequence hoặc boundary đáng kể" in explore_template
