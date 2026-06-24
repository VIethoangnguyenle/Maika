#!/usr/bin/env python3
"""
Skill Lint — Kiểm tra SKILL.md theo schema chuẩn SP2.

Chạy:
    python validate_skills.py [đường-dẫn-thư-mục-skills]

Mặc định quét: ../../skills/ (tương đối từ vị trí script)
Exit code: 0 = tất cả pass | 1 = có lỗi
"""

import os
import re
import sys
import yaml
from pathlib import Path
from typing import Any


# ─── Schema Definition ───────────────────────────────────────────────

REQUIRED_FRONTMATTER = ["name", "description", "version"]

# Các heading bắt buộc (chấp nhận biến thể tương đương)
REQUIRED_SECTIONS = {
    "B1": {
        "label": "Mục tiêu",
        "patterns": [r"##\s+Mục tiêu", r"##\s+1\.\s*Mục tiêu"],
    },
    "B2": {
        "label": "Khi nào sử dụng",
        "patterns": [
            r"##\s+Khi nào sử dụng",
            r"##\s+Khi nào dùng",
            r"##\s+\d+\.\s*Khi nào (?:sử dụng|dùng)",
            r"##\s+When to Use",
        ],
    },
    "B3": {
        "label": "Khi nào KHÔNG sử dụng",
        "patterns": [
            r"##\s+Khi nào KHÔNG sử dụng",
            r"##\s+Khi nào KHÔNG dùng",
            r"##\s+\d+\.\s*Khi nào KHÔNG (?:sử dụng|dùng)",
            r"##\s+When NOT to Use",
        ],
    },
    "B4": {
        "label": "Quy trình",
        "patterns": [
            r"##\s+Quy trình",
            r"##\s+Quy trình thực hiện",
            r"##\s+\d+\.\s*Quy trình",
            r"##\s+The Process",
        ],
    },
    "B5": {
        "label": "Đầu ra",
        "patterns": [
            r"##\s+Đầu ra",
            r"##\s+Output",
            r"##\s+\d+\.\s*Đầu ra",
            r"##\s+\d+\.\s*Output",
        ],
    },
}


# ─── Frontmatter Parser ──────────────────────────────────────────────

def parse_frontmatter(content: str) -> tuple[dict[str, Any] | None, str]:
    """Tách frontmatter YAML và body từ nội dung SKILL.md.

    Returns:
        (frontmatter_dict | None, body_text)
    """
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", content, re.DOTALL)
    if not match:
        return None, content
    try:
        fm = yaml.safe_load(match.group(1))
        return (fm if isinstance(fm, dict) else None), match.group(2)
    except yaml.YAMLError:
        return None, content


# ─── Individual Check Functions ───────────────────────────────────────

def check_f1_name(fm: dict) -> tuple[bool, str]:
    """[F1] name — tồn tại, kebab-case."""
    name = fm.get("name")
    if not name:
        return False, "thiếu field 'name'"
    if not re.match(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$", str(name)):
        return False, f"name '{name}' không đúng kebab-case"
    return True, ""


def check_f2_description(fm: dict) -> tuple[bool, str]:
    """[F2] description — tồn tại, >= 20 ký tự, chứa trigger indicator."""
    desc = fm.get("description", "")
    if not desc:
        return False, "thiếu field 'description'"
    desc_str = str(desc).strip()
    if len(desc_str) < 20:
        return False, f"description quá ngắn ({len(desc_str)} ký tự, cần >= 20)"
    # Chấp nhận cả tiếng Việt và tiếng Anh
    has_trigger = any(
        kw in desc_str for kw in ["Dùng khi", "Use when", "Kích hoạt khi"]
    )
    if not has_trigger:
        return False, "description thiếu trigger (cần 'Dùng khi' hoặc 'Use when')"
    return True, ""


def check_f3_version(fm: dict) -> tuple[bool, str]:
    """[F3] version — tồn tại, match X.Y."""
    ver = fm.get("version")
    if not ver:
        return False, "thiếu field 'version'"
    if not re.match(r"^\d+\.\d+$", str(ver)):
        return False, f"version '{ver}' không đúng format X.Y"
    return True, ""


def check_f4_pre_conditions(fm: dict) -> tuple[bool | None, str]:
    """[F4] pre_conditions — nếu có: validate cấu trúc.

    Returns None cho cột trạng thái nếu field không tồn tại (optional).
    """
    pcs = fm.get("pre_conditions")
    if pcs is None:
        return None, ""  # optional — skip
    if not isinstance(pcs, list):
        return False, "pre_conditions phải là danh sách"
    for i, entry in enumerate(pcs):
        if not isinstance(entry, dict):
            return False, f"pre_conditions[{i}] không phải dict"
        required_keys = {"condition", "on_fail"}
        # entry cần có ít nhất (file hoặc phase) + condition + on_fail
        has_target = any(k in entry for k in ("file", "phase"))
        if not has_target:
            return False, f"pre_conditions[{i}] thiếu 'file' hoặc 'phase'"
        missing = required_keys - set(entry.keys())
        if missing:
            return False, f"pre_conditions[{i}] thiếu: {', '.join(sorted(missing))}"
    return True, ""


def check_f5_outputs(fm: dict) -> tuple[bool | None, str]:
    """[F5] outputs — nếu có: validate cấu trúc."""
    outputs = fm.get("outputs")
    if outputs is None:
        return None, ""  # optional — skip
    if not isinstance(outputs, list):
        return False, "outputs phải là danh sách"
    for i, entry in enumerate(outputs):
        if not isinstance(entry, dict):
            return False, f"outputs[{i}] không phải dict"
        missing = {"path", "action"} - set(entry.keys())
        if missing:
            return False, f"outputs[{i}] thiếu: {', '.join(sorted(missing))}"
    return True, ""


SP3_DOCTRINE_HEADING = re.compile(
    r"^\s*##\s+(Quy tắc cốt lõi|Core [Rr]ule|Reflex)", re.MULTILINE
)
SP3_REFLEX_MAX_LINE = 30  # heading reflex phải nằm trong N dòng đầu body


def check_s1_reflex_upfront(fm: dict, body: str) -> tuple[bool | None, str]:
    """[S1] SP3: heading 'Quy tắc cốt lõi/Reflex' nằm trong N dòng đầu body."""
    if fm.get("standard") != "SP3":
        return None, ""  # opt-in — chỉ áp SP3
    head = "\n".join(body.splitlines()[:SP3_REFLEX_MAX_LINE])
    if not SP3_DOCTRINE_HEADING.search(head):
        return False, (
            f"SP3 thiếu '## Quy tắc cốt lõi' trong {SP3_REFLEX_MAX_LINE} dòng đầu body"
        )
    return True, ""


SP3_FLOWCHART = re.compile(r"```(dot|mermaid)\b")


def check_s2_flowchart(fm: dict, body: str) -> tuple[bool | None, str]:
    """[S2] SP3: phải có ít nhất 1 sơ đồ ```dot hoặc ```mermaid (cho process-skill)."""
    if fm.get("standard") != "SP3":
        return None, ""
    if not SP3_FLOWCHART.search(body):
        return False, "SP3 thiếu flowchart (```dot hoặc ```mermaid)"
    return True, ""


SP3_CORE_MAX_LINES = 200


def check_s3_core_budget(fm: dict, body: str) -> tuple[str, str]:
    """[S3] SP3: core SKILL.md ≤ ngưỡng dòng (progressive disclosure). WARN, không FAIL."""
    if fm.get("standard") != "SP3":
        return "SKIP", ""
    n = len(body.splitlines())
    if n > SP3_CORE_MAX_LINES:
        return "WARN", f"SP3 core {n} dòng > {SP3_CORE_MAX_LINES} — đẩy chi tiết sang references/"
    return "PASS", ""


def check_body_section(body: str, section_id: str) -> tuple[bool, str]:
    """Kiểm tra heading bắt buộc tồn tại trong body."""
    section = REQUIRED_SECTIONS[section_id]
    for pattern in section["patterns"]:
        if re.search(pattern, body, re.IGNORECASE):
            return True, ""
    return False, f"thiếu section '## {section['label']}'"


# ─── Orchestrator ─────────────────────────────────────────────────────

def validate_skill(skill_path: Path) -> dict:
    """Validate một file SKILL.md, trả về kết quả chi tiết."""
    content = skill_path.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(content)

    results = {}

    if fm is None:
        # Không parse được frontmatter → fail toàn bộ F*
        for check_id in ["F1", "F2", "F3", "F4", "F5", "S1", "S2"]:
            results[check_id] = (False, "không parse được frontmatter YAML")
        results["S3"] = ("SKIP", "")
    else:
        results["F1"] = check_f1_name(fm)
        results["F2"] = check_f2_description(fm)
        results["F3"] = check_f3_version(fm)
        results["F4"] = check_f4_pre_conditions(fm)
        results["F5"] = check_f5_outputs(fm)
        results["S1"] = check_s1_reflex_upfront(fm, body)
        results["S2"] = check_s2_flowchart(fm, body)
        results["S3"] = check_s3_core_budget(fm, body)

    for section_id in REQUIRED_SECTIONS:
        results[section_id] = check_body_section(body, section_id)

    return results


def validate_all(skills_dir: Path) -> dict[str, dict]:
    """Validate tất cả SKILL.md trong thư mục skills."""
    all_results = {}
    skill_dirs = sorted(
        d for d in skills_dir.iterdir()
        if d.is_dir() and (d / "SKILL.md").exists()
    )

    # Collect tên để check unique (F1 bonus)
    names_seen: dict[str, str] = {}

    for skill_dir in skill_dirs:
        skill_file = skill_dir / "SKILL.md"
        skill_name = skill_dir.name
        results = validate_skill(skill_file)

        # Check unique name
        fm, _ = parse_frontmatter(skill_file.read_text(encoding="utf-8"))
        if fm and fm.get("name"):
            name_val = fm["name"]
            if name_val in names_seen:
                results["F1"] = (
                    False,
                    f"name '{name_val}' trùng với {names_seen[name_val]}",
                )
            else:
                names_seen[name_val] = skill_name

        all_results[skill_name] = results

    return all_results


# ─── Report Formatter ─────────────────────────────────────────────────

CHECK_IDS = ["F1", "F2", "F3", "F4", "F5", "S1", "S2", "B1", "B2", "B3", "B4", "B5"]


def format_status(result: tuple[bool | None, str]) -> str:
    """Chuyển kết quả check thành ký hiệu hiển thị."""
    passed, _ = result
    if passed is None:
        return "--"
    return "✅" if passed else "❌"


def print_report(all_results: dict[str, dict]) -> int:
    """In report dạng bảng, trả về exit code."""
    print("\n=== SKILL LINT REPORT ===\n")

    # Header
    header = f"  {'skill-name':<35}"
    for cid in CHECK_IDS:
        header += f" {cid:>3}"
    header += "  STATUS"
    print(header)
    print("  " + "-" * (len(header) - 2))

    total_fail = 0
    details: list[str] = []

    for skill_name, results in all_results.items():
        row = f"  {skill_name:<35}"
        fail_count = 0
        fail_msgs = []

        for cid in CHECK_IDS:
            result = results.get(cid, (None, ""))
            row += f" {format_status(result):>3}"
            passed, msg = result
            if passed is False:
                fail_count += 1
                fail_msgs.append(f"    [{cid}] {msg}")

        if fail_count > 0:
            row += f"  FAIL ({fail_count})"
            total_fail += 1
            details.append(f"\n  {skill_name}:")
            details.extend(fail_msgs)
        else:
            row += "  PASS"

        s3 = results.get("S3", ("SKIP", ""))
        if s3[0] == "WARN":
            details.append(f"\n  {skill_name}: [S3 WARN] {s3[1]}")

        print(row)

    # Summary
    total = len(all_results)
    passed = total - total_fail
    print(f"\n  Tổng: {passed}/{total} skills PASS")

    if details:
        print("\n=== CHI TIẾT LỖI ===")
        for line in details:
            print(line)

    print()
    return 0 if total_fail == 0 else 1


# ─── CLI Entry Point ─────────────────────────────────────────────────

def main() -> int:
    """Entry point — chạy lint trên thư mục skills."""
    if len(sys.argv) > 1:
        skills_dir = Path(sys.argv[1])
    else:
        # Mặc định: ../../skills/ tương đối từ script
        script_dir = Path(__file__).resolve().parent
        skills_dir = script_dir.parent.parent / "skills"

    if not skills_dir.is_dir():
        print(f"Lỗi: Không tìm thấy thư mục '{skills_dir}'", file=sys.stderr)
        return 1

    all_results = validate_all(skills_dir)
    return print_report(all_results)


if __name__ == "__main__":
    sys.exit(main())
