"""Regression tests for ASCII diagram guidance in Maika skills/templates."""

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent.parent


def read_text(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def test_spec_extract_requires_ascii_diagram_capture():
    readme = read_text("README.md")
    skill = read_text(".maika/skills/spec-extract/SKILL.md")
    detail = read_text(".maika/skills/spec-extract/references/quy-trinh-chi-tiet.md")
    schema = read_text(".maika/skills/spec-extract/references/output-schema.md")
    requirement_template = read_text(".maika/knowledge/templates/REQUIREMENT.tpl.md")

    output_section = skill.split("## 3. Input / Output", 1)[1].split("## 4. Quy trình chi tiết", 1)[0]
    process_section = skill.split("## 4. Quy trình chi tiết", 1)[1].split("## 5. Cập nhật AGENT_TRANSPARENCY", 1)[0]
    step_5c_section = detail.split("### Bước 5c — Vẽ ASCII Flow / State Diagram", 1)[1].split("### Bước 6 — Trích quy tắc nghiệp vụ (Business Rules)", 1)[0]

    assert "#### ASCII Flow / State Diagram" in skill
    assert "flow, state, integration, callback, job, hoặc data path" in skill
    assert "Integrations & Field Mapping; ASCII Flow / State Diagram; Độ tin cậy tài liệu; Lỗ hổng & câu hỏi mở" in output_section
    assert "Bước 5c — Vẽ ASCII Flow / State Diagram" in process_section
    assert "Bước 5c — Vẽ ASCII Flow / State Diagram" in detail
    assert "Diagram phải đánh dấu `unknown`, `assumption`, hoặc `needs BA/PO confirmation`" in detail
    assert "~~~md" in step_5c_section
    assert "```text" in step_5c_section
    assert "spec-extract" in readme
    assert "ASCII Flow / State Diagram" in readme
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
