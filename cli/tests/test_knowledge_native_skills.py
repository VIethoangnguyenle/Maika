"""W3: every canonical reasoning skill follows the knowledge-native contract
and passes skill-lint (Vietnamese SP2 schema + capability boundary).

This test is the mechanical consumer (R1) that makes the knowledge-native skill
rewrite legal and keeps future edits from silently dropping the contract."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / ".maika" / "skills"

REASONING_SKILLS = [
    "intent-analysis", "grounding-explorer", "database-explorer",
    "architecture-reconciler", "grounded-brainstorming", "writing-spec",
    "writing-plan", "validating-plan", "executing-task", "reviewing-task",
    "reviewing-change", "verification-before-completion", "knowledge-retriever", "knowledge-recorder", "knowledge-promoter",
    "author-dna-builder", "convention-intelligence-builder", "infra-tdd",
]

KNOWLEDGE_NATIVE_SECTIONS = [
    "## Câu hỏi tri thức",
    "## Loại evidence bắt buộc",
    "## Chính sách capability",
    "## Quy trình truy xuất",
    "## Thứ tự authority",
    "## Freshness và confidence",
    "## Quy trình degradation",
    "## Tác động lên knowledge",
]


def test_all_reasoning_skills_exist():
    for name in REASONING_SKILLS:
        assert (SKILLS / name / "SKILL.md").exists(), name


def test_reasoning_skills_have_knowledge_native_sections():
    missing = {}
    for name in REASONING_SKILLS:
        path = SKILLS / name / "SKILL.md"
        if not path.exists():
            missing[name] = ["<missing skill>"]
            continue
        body = path.read_text(encoding="utf-8")
        gaps = [s for s in KNOWLEDGE_NATIVE_SECTIONS if s not in body]
        if gaps:
            missing[name] = gaps
    assert not missing, f"skills missing knowledge-native sections: {missing}"
