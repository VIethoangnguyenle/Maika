#!/usr/bin/env python3
"""Tests cho validate_skills.py — SP2 Skill Lint."""

import sys
import textwrap
from pathlib import Path

import pytest

# Thêm parent vào path để import module
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from validate_skills import (
    parse_frontmatter,
    check_f1_name,
    check_f2_description,
    check_f3_version,
    check_f4_pre_conditions,
    check_f5_outputs,
    check_body_section,
    validate_skill,
    validate_all,
)
from validate_skills import check_s1_reflex_upfront
from validate_skills import check_s2_flowchart
from validate_skills import check_s3_core_budget, SP3_CORE_MAX_LINES
from validate_skills import check_w4_capability_boundary


# ─── Frontmatter Parser ──────────────────────────────────────────────

class TestParseFrontmatter:
    def test_valid_frontmatter(self):
        content = textwrap.dedent("""\
            ---
            name: test-skill
            version: '1.0'
            description: Dùng khi cần test
            ---

            # Body content
        """)
        fm, body = parse_frontmatter(content)
        assert fm is not None
        assert fm["name"] == "test-skill"
        assert "Body content" in body

    def test_no_frontmatter(self):
        content = "# Just a heading\n\nSome content"
        fm, body = parse_frontmatter(content)
        assert fm is None
        assert body == content

    def test_invalid_yaml(self):
        content = "---\n: : : invalid\n---\n\nbody"
        fm, body = parse_frontmatter(content)
        assert fm is None


# ─── F1: Name ─────────────────────────────────────────────────────────

class TestF1Name:
    def test_valid_kebab_case(self):
        assert check_f1_name({"name": "intent-analysis"})[0] is True

    def test_single_word(self):
        assert check_f1_name({"name": "validator"})[0] is True

    def test_missing(self):
        passed, msg = check_f1_name({})
        assert passed is False
        assert "thiếu" in msg

    def test_not_kebab_case(self):
        passed, msg = check_f1_name({"name": "RequirementAnalyst"})
        assert passed is False
        assert "kebab-case" in msg

    def test_underscore_invalid(self):
        passed, _ = check_f1_name({"name": "requirement_analyst"})
        assert passed is False

    def test_starts_with_number(self):
        passed, _ = check_f1_name({"name": "1-skill"})
        assert passed is False


# ─── F2: Description ─────────────────────────────────────────────────

class TestF2Description:
    def test_valid_vietnamese(self):
        desc = "Dùng khi cần phân tích yêu cầu từ ticket. KHÔNG dùng cho brainstorm."
        assert check_f2_description({"description": desc})[0] is True

    def test_valid_english(self):
        desc = "Use when a ticket exists and needs standardization into REQUIREMENT.md."
        assert check_f2_description({"description": desc})[0] is True

    def test_missing(self):
        passed, _ = check_f2_description({})
        assert passed is False

    def test_too_short(self):
        passed, msg = check_f2_description({"description": "Ngắn"})
        assert passed is False
        assert "quá ngắn" in msg

    def test_no_trigger(self):
        passed, msg = check_f2_description(
            {"description": "Phân tích yêu cầu từ ticket, chuẩn hoá thành REQUIREMENT.md"}
        )
        assert passed is False
        assert "trigger" in msg


# ─── F3: Version ──────────────────────────────────────────────────────

class TestF3Version:
    def test_valid(self):
        assert check_f3_version({"version": "1.0"})[0] is True
        assert check_f3_version({"version": "2.1"})[0] is True

    def test_missing(self):
        passed, _ = check_f3_version({})
        assert passed is False

    def test_invalid_format(self):
        passed, _ = check_f3_version({"version": "1"})
        assert passed is False
        passed, _ = check_f3_version({"version": "1.0.0"})
        assert passed is False


# ─── W4: Capability Boundary ─────────────────────────────────────────

class TestW4CapabilityBoundary:
    def test_known_capability_ids_pass(self):
        body = "- Capability IDs: `runtime_verification`, `review_dispatch`.\n"
        passed, msg = check_w4_capability_boundary(
            body, {"runtime_verification", "review_dispatch"}
        )
        assert passed is True
        assert msg == ""

    def test_provider_name_fails(self):
        body = "Use agent-memory directly.\n"
        passed, msg = check_w4_capability_boundary(body, {"runtime_verification"})
        assert passed is False
        assert "provider name" in msg

    def test_unknown_capability_id_fails(self):
        body = "- Capability IDs: `runtime_verification`, `telepathy`.\n"
        passed, msg = check_w4_capability_boundary(body, {"runtime_verification"})
        assert passed is False
        assert "telepathy" in msg


# ─── F4: Pre-conditions ──────────────────────────────────────────────

class TestF4PreConditions:
    def test_not_present_is_skip(self):
        passed, _ = check_f4_pre_conditions({})
        assert passed is None  # optional → skip

    def test_valid(self):
        fm = {
            "pre_conditions": [
                {
                    "file": ".maika/knowledge/active/REQUIREMENT.md",
                    "condition": "not_skeleton",
                    "on_fail": "ABORT — chạy intent-analysis trước",
                }
            ]
        }
        assert check_f4_pre_conditions(fm)[0] is True

    def test_phase_target(self):
        fm = {
            "pre_conditions": [
                {
                    "phase": "pha-1",
                    "condition": "phase_done",
                    "on_fail": "ABORT — Pha 1 chưa hoàn thành",
                }
            ]
        }
        assert check_f4_pre_conditions(fm)[0] is True

    def test_missing_condition(self):
        fm = {
            "pre_conditions": [
                {"file": "some/path", "on_fail": "ABORT"}
            ]
        }
        passed, msg = check_f4_pre_conditions(fm)
        assert passed is False
        assert "condition" in msg

    def test_missing_target(self):
        fm = {
            "pre_conditions": [
                {"condition": "exists", "on_fail": "ABORT"}
            ]
        }
        passed, msg = check_f4_pre_conditions(fm)
        assert passed is False
        assert "file" in msg or "phase" in msg

    def test_not_list(self):
        fm = {"pre_conditions": "not a list"}
        passed, _ = check_f4_pre_conditions(fm)
        assert passed is False


# ─── F5: Outputs ──────────────────────────────────────────────────────

class TestF5Outputs:
    def test_not_present_is_skip(self):
        passed, _ = check_f5_outputs({})
        assert passed is None

    def test_valid(self):
        fm = {
            "outputs": [
                {"path": ".maika/knowledge/active/REQUIREMENT.md", "action": "write"}
            ]
        }
        assert check_f5_outputs(fm)[0] is True

    def test_missing_action(self):
        fm = {"outputs": [{"path": "some/file"}]}
        passed, msg = check_f5_outputs(fm)
        assert passed is False
        assert "action" in msg

    def test_not_list(self):
        fm = {"outputs": "not a list"}
        passed, _ = check_f5_outputs(fm)
        assert passed is False


# ─── Body Sections ────────────────────────────────────────────────────

class TestBodySections:
    FULL_BODY = textwrap.dedent("""\
        # Skill Name

        ## Mục tiêu
        Nội dung mục tiêu.

        ## Khi nào sử dụng
        Trigger conditions.

        ## Khi nào KHÔNG sử dụng
        Anti-patterns.

        ## Quy trình
        Step-by-step.

        ## Đầu ra
        Output format.
    """)

    def test_all_sections_present(self):
        for section_id in ["B1", "B2", "B3", "B4", "B5"]:
            passed, _ = check_body_section(self.FULL_BODY, section_id)
            assert passed is True, f"{section_id} should pass"

    def test_missing_section(self):
        body_without_output = self.FULL_BODY.replace("## Đầu ra\nOutput format.\n", "")
        passed, msg = check_body_section(body_without_output, "B5")
        assert passed is False
        assert "Đầu ra" in msg

    def test_numbered_heading_variant(self):
        body = "## 1. Mục tiêu\nNội dung."
        passed, _ = check_body_section(body, "B1")
        assert passed is True

    def test_alternative_heading_variant(self):
        body = "## Khi nào dùng\nContent."
        passed, _ = check_body_section(body, "B2")
        assert passed is True

    def test_english_variant(self):
        body = "## When to Use\nContent."
        passed, _ = check_body_section(body, "B2")
        assert passed is True

    def test_process_variant(self):
        body = "## Quy trình thực hiện\nSteps."
        passed, _ = check_body_section(body, "B4")
        assert passed is True


# ─── S1: Reflex Upfront (opt-in SP3) ──────────────────────────────────

class TestS1ReflexUpfront:
    def test_sp3_with_reflex_upfront_passes(self):
        fm = {"standard": "SP3"}
        body = "## Quy tắc cốt lõi (reflex)\n\n> UA-first...\n\n## Mục tiêu\n"
        passed, _ = check_s1_reflex_upfront(fm, body)
        assert passed is True

    def test_sp3_without_reflex_fails(self):
        fm = {"standard": "SP3"}
        body = "## Mục tiêu\n\nNội dung dài...\n" + "x\n" * 50
        passed, _ = check_s1_reflex_upfront(fm, body)
        assert passed is False

    def test_sp3_reflex_too_deep_fails(self):
        fm = {"standard": "SP3"}
        body = "filler\n" * 40 + "## Quy tắc cốt lõi (reflex)\n"
        passed, _ = check_s1_reflex_upfront(fm, body)
        assert passed is False

    def test_non_sp3_skipped(self):
        fm = {"standard": None}
        body = "## Mục tiêu\n"
        passed, _ = check_s1_reflex_upfront(fm, body)
        assert passed is None


# ─── S2: Flowchart Required (opt-in SP3) ──────────────────────────────

class TestS2Flowchart:
    def test_sp3_with_dot_passes(self):
        fm = {"standard": "SP3"}
        body = "## Quy trình\n\n```dot\ndigraph{a->b}\n```\n"
        assert check_s2_flowchart(fm, body)[0] is True

    def test_sp3_with_mermaid_passes(self):
        fm = {"standard": "SP3"}
        body = "## Quy trình\n\n```mermaid\nflowchart TD\n```\n"
        assert check_s2_flowchart(fm, body)[0] is True

    def test_sp3_no_flowchart_fails(self):
        fm = {"standard": "SP3"}
        body = "## Quy trình\n\nBước 1...\n"
        assert check_s2_flowchart(fm, body)[0] is False

    def test_non_sp3_skipped(self):
        assert check_s2_flowchart({}, "## Quy trình\n")[0] is None


# ─── S3: Core Budget (opt-in SP3, WARN không FAIL) ────────────────────

class TestS3CoreBudget:
    def test_sp3_within_budget_pass(self):
        fm = {"standard": "SP3"}
        body = "x\n" * (SP3_CORE_MAX_LINES - 1)
        assert check_s3_core_budget(fm, body)[0] == "PASS"

    def test_sp3_over_budget_warn(self):
        fm = {"standard": "SP3"}
        body = "x\n" * (SP3_CORE_MAX_LINES + 5)
        assert check_s3_core_budget(fm, body)[0] == "WARN"

    def test_non_sp3_skip(self):
        body = "x\n" * (SP3_CORE_MAX_LINES + 5)
        assert check_s3_core_budget({}, body)[0] == "SKIP"


# ─── Integration: validate_skill ──────────────────────────────────────

class TestValidateSkill:
    def test_perfect_skill(self, tmp_path):
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(textwrap.dedent("""\
            ---
            name: test-skill
            version: '1.0'
            description: >
              Dùng khi cần test validation.
              KHÔNG dùng cho: production.
            pre_conditions:
              - file: some/file.md
                condition: exists
                on_fail: "ABORT"
            outputs:
              - path: output/file.md
                action: write
            ---

            # Test Skill

            ## Mục tiêu
            Test.

            ## Khi nào sử dụng
            Trigger.

            ## Khi nào KHÔNG sử dụng
            Anti-pattern.

            ## Quy trình
            Steps.

            ## Đầu ra
            Output.
        """), encoding="utf-8")

        results = validate_skill(skill_dir / "SKILL.md")

        for check_id in ["F1", "F2", "F3", "F4", "F5", "B1", "B2", "B3", "B4", "B5"]:
            passed, msg = results[check_id]
            assert passed is not False, f"{check_id} failed: {msg}"

    def test_minimal_skill_no_optional(self, tmp_path):
        """Skill chỉ có required fields, không có pre_conditions/outputs."""
        skill_dir = tmp_path / "minimal-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(textwrap.dedent("""\
            ---
            name: minimal-skill
            version: '1.0'
            description: Dùng khi cần test tối thiểu mà vẫn đủ chuẩn.
            ---

            # Minimal

            ## Mục tiêu
            Test.

            ## Khi nào sử dụng
            Trigger.

            ## Khi nào KHÔNG sử dụng
            Nothing.

            ## Quy trình
            Steps.

            ## Đầu ra
            Output.
        """), encoding="utf-8")

        results = validate_skill(skill_dir / "SKILL.md")

        # Required checks pass
        for cid in ["F1", "F2", "F3", "B1", "B2", "B3", "B4", "B5"]:
            passed, msg = results[cid]
            assert passed is True, f"{cid} failed: {msg}"
        # Optional checks are None (skip)
        assert results["F4"][0] is None
        assert results["F5"][0] is None


# ─── Integration: validate_all (unique name check) ────────────────────

class TestValidateAll:
    def test_duplicate_names_flagged(self, tmp_path):
        for dirname in ["skill-a", "skill-b"]:
            d = tmp_path / dirname
            d.mkdir()
            (d / "SKILL.md").write_text(textwrap.dedent("""\
                ---
                name: same-name
                version: '1.0'
                description: Dùng khi cần test duplicate name detection.
                ---

                # Same Name

                ## Mục tiêu
                Test.
                ## Khi nào sử dụng
                Trigger.
                ## Khi nào KHÔNG sử dụng
                Nothing.
                ## Quy trình
                Steps.
                ## Đầu ra
                Output.
            """), encoding="utf-8")

        all_results = validate_all(tmp_path)

        # Ít nhất 1 trong 2 phải fail F1 vì trùng tên
        f1_results = [all_results[s]["F1"][0] for s in all_results]
        assert False in f1_results


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
