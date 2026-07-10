"""Mechanical consumers for the Maika vNext W2 reasoning-layer cutover."""

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / ".maika" / "skills"

TARGET_SKILLS = {
    "intent-analysis",
    "grounding-explorer",
    "database-explorer",
    "architecture-reconciler",
    "grounded-brainstorming",
    "writing-spec",
    "writing-plan",
    "validating-plan",
    "executing-task",
    "reviewing-task",
    "reviewing-change",
    "verification-before-completion",
    "knowledge-curator",
    "author-dna-builder",
    "convention-intelligence-builder",
    "infra-tdd",
}

# Knowledge-native contract headings (kn-w3): supersedes the old English W2 set.
REQUIRED_HEADINGS = (
    "Mục tiêu",
    "Khi nào sử dụng",
    "Khi nào KHÔNG sử dụng",
    "Đầu vào",
    "Câu hỏi tri thức",
    "Loại evidence bắt buộc",
    "Chính sách capability",
    "Quy trình truy xuất",
    "Kết quả bắt buộc",
    "Quy trình",
    "Điều kiện dừng",
    "Đầu ra",
    "Handoff tiếp theo",
)

REMOVED = [
    "architecture" + "-reviewer",
    "codebase" + "-explorer",
    "db" + "-explorer",
    "document" + "-writer",
    "open" + "spec" + "-[a-z-]+",
    "requirement" + "-analyst",
    "spec" + "-extract",
    "spec" + "-validator",
]
REMOVED_SKILLS = re.compile(r"\b(" + "|".join(REMOVED) + r")\b")
RAW_PROVIDER_TOOLS = re.compile(
    r"\bmcp__(?:understand-anything|codebase_memory|agent_memory)|"
    r"\bmcp_understand-anything_|\bmemory_(?:smart_search|recall|save|sessions|audit)\b"
)


def _real_skill_dirs():
    return {
        p.name for p in SKILLS.iterdir()
        if p.is_dir() and (p / "SKILL.md").exists()
    }


def _skill_texts():
    for skill in sorted(TARGET_SKILLS):
        path = SKILLS / skill / "SKILL.md"
        yield path, path.read_text(encoding="utf-8")
        ref_dir = SKILLS / skill / "references"
        if ref_dir.exists():
            for ref in sorted(ref_dir.glob("*.md")):
                yield ref, ref.read_text(encoding="utf-8")


def test_target_skill_directories_exact():
    assert _real_skill_dirs() == TARGET_SKILLS


def test_skill_index_exactly_matches_target_skills():
    index = yaml.safe_load((SKILLS / "skill-index.yaml").read_text(encoding="utf-8"))
    assert {entry["name"] for entry in index["skills"]} == TARGET_SKILLS


def test_plugin_manifest_ships_only_target_skills():
    manifest = yaml.safe_load((ROOT / "cli" / "plugin-manifest.yaml").read_text(encoding="utf-8"))
    skill_plugins = {
        plugin["name"] for plugin in manifest["plugins"]
        if plugin.get("type") == "skill" and plugin["name"] != "skill-index-data"
    }
    assert skill_plugins == TARGET_SKILLS


def test_all_target_skills_have_w2_contract_headings():
    for skill in sorted(TARGET_SKILLS):
        text = (SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")
        for heading in REQUIRED_HEADINGS:
            assert f"## {heading}" in text, f"{skill} missing {heading}"


def test_target_skills_do_not_reference_deleted_skills_or_raw_provider_tools():
    offenders = []
    for path, text in _skill_texts():
        for lineno, line in enumerate(text.splitlines(), 1):
            if REMOVED_SKILLS.search(line) or RAW_PROVIDER_TOOLS.search(line):
                offenders.append(f"{path.relative_to(ROOT)}:{lineno}: {line.strip()}")
    assert offenders == []


def test_vnext_is_default_workflow_engine():
    profile = (ROOT / ".maika" / "profiles" / "execution-mode.yaml").read_text(encoding="utf-8")
    assert "workflow_engine: vnext" in profile
    assert "workflow_engine: " + "leg" + "acy" not in profile
