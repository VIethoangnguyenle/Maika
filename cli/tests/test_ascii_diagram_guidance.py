"""Regression tests for ASCII diagram guidance in Maika skills/templates."""

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent.parent


def read_text(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def test_writing_spec_requires_ascii_diagram_capture():
    readme = read_text("README.md")
    skill = read_text(".maika/skills/writing-spec/SKILL.md")
    requirement_template = read_text(".maika/knowledge/templates/REQUIREMENT.tpl.md")

    assert "#### ASCII Flow / State Diagram" in skill
    assert "flow, state, integration, callback, job, hoặc data path" in skill
    assert "Diagram phải đánh dấu `unknown`, `assumption`, hoặc `needs BA/PO confirmation`" in skill
    assert "~~~md" in skill
    assert "```text" in skill
    assert "writing-spec" in readme
    assert "ASCII Flow / State Diagram" in readme
    assert "## Flow / State Diagram" in requirement_template
    assert "Bắt buộc khi task có flow, state, integration, callback, job, hoặc data path" in requirement_template


def test_grounded_brainstorming_uses_visual_stance_and_capture():
    skill = read_text(".maika/skills/grounded-brainstorming/SKILL.md")
    explore_template = read_text(".maika/knowledge/templates/EXPLORE_CONTEXT.tpl.md")

    assert "Brainstorming là stance, không phải workflow cứng" in skill
    assert "Visualize tự do" in skill
    assert "capture insight đó vào `RECONCILIATION.md`" in skill
    assert "Do visualize" in skill
    assert "ASCII diagram bắt buộc khi có flow/state/data path" in skill
    assert "vấn đề user nêu" in skill
    assert "ASCII diagram bắt buộc khi có flow/state/data path" in explore_template
    assert "Danh sách module chỉ đủ khi không có sequence hoặc boundary đáng kể" in explore_template
