"""Skill-lint: enforce cơ học rubric BP-01..BP-08 cho mọi .maika/skills/*/SKILL.md.

Mỗi check gắn một mã BP (xem docs/superpowers/specs/2026-07-04-anthropic-bp-rubric.md).
Chạy trong CI matrix qua cli/tests/. Self-fixture (Task 1) chứng minh logic check;
scan skill thật (Task 2) enforce trên repo.
"""
import re
from pathlib import Path

import pytest
import yaml

SKILLS_DIR = Path(__file__).resolve().parent.parent.parent / ".maika" / "skills"

# L3 (BP-03): skill được phép vượt MAX_BODY_LINES — backlog migrate đợt 2.
# CHỈ được RÚT NGẮN (mỗi lần migrate xong một skill thì xóa khỏi đây). Không thêm.
MAX_BODY_LINES = 300
BODY_LINE_ALLOWLIST = {
    "architecture-reviewer",
    "infra-tdd",       # pilot — xóa ở Task 3
    "knowledge-curator",
    "openspec-explore",
    "requirement-analyst",
    "spec-extract",     # pilot — xóa ở Task 4
    "spec-validator",
}

_FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_NAME_RE = re.compile(r"^[a-z0-9-]{1,64}$")
_REF_MENTION_RE = re.compile(r"references/([A-Za-z0-9._-]+\.md)")
_TODO_RE = re.compile(r"\b(TODO|TBD|FIXME)\b")


def parse_skill(skill_md: Path):
    """Trả (frontmatter dict|None, body str). None nếu thiếu frontmatter."""
    text = skill_md.read_text(encoding="utf-8")
    m = _FM_RE.match(text)
    if not m:
        return None, text
    return yaml.safe_load(m.group(1)), text[m.end():]


def _md_files(skill_dir: Path):
    files = [skill_dir / "SKILL.md"]
    ref_dir = skill_dir / "references"
    if ref_dir.exists():
        files += sorted(ref_dir.glob("*.md"))
    return [f for f in files if f.exists()]


def check_frontmatter(name, fm):  # L1 (BP-01 nền)
    if fm is None:
        return [f"{name}: SKILL.md thiếu frontmatter YAML"]
    errs = []
    if fm.get("name") != name:
        errs.append(f"{name}: frontmatter name={fm.get('name')!r} != tên thư mục")
    if not _NAME_RE.match(str(fm.get("name", ""))):
        errs.append(f"{name}: name không hợp lệ (>64 ký tự hoặc ngoài [a-z0-9-])")
    return errs


def check_description(name, fm):  # L2 (BP-01/BP-02 proxy)
    desc = str((fm or {}).get("description", "")).strip()
    if not desc:
        return [f"{name}: description rỗng"]
    if len(desc) < 80:
        return [f"{name}: description {len(desc)} ký tự < 80 (thiếu trigger cụ thể?)"]
    if len(desc) > 1024:
        return [f"{name}: description {len(desc)} ký tự > 1024 (trần Anthropic)"]
    return []


def check_body_lines(name, body):  # L3 (BP-03)
    n = len(body.splitlines())
    if n > MAX_BODY_LINES and name not in BODY_LINE_ALLOWLIST:
        return [f"{name}: SKILL.md body {n} dòng > {MAX_BODY_LINES} "
                f"(migrate progressive disclosure hoặc thêm vào allowlist backlog)"]
    return []


def check_references(name, skill_dir, body):  # L4 + L5 + L6 (BP-04)
    errs = []
    ref_dir = skill_dir / "references"
    mentioned = set(_REF_MENTION_RE.findall(body))
    existing = {p.name for p in ref_dir.glob("*.md")} if ref_dir.exists() else set()
    for orphan in sorted(existing - mentioned):  # L4
        errs.append(f"{name}: references/{orphan} không được SKILL.md nhắc (orphan)")
    for dangling in sorted(mentioned - existing):  # L4
        errs.append(f"{name}: SKILL.md nhắc references/{dangling} nhưng file không tồn tại")
    for ref in sorted(ref_dir.glob("*.md")) if ref_dir.exists() else []:
        rtext = ref.read_text(encoding="utf-8")
        if re.search(r"\]\([^)]*references/", rtext):  # L5 nested
            errs.append(f"{name}: references/{ref.name} link tới references/ khác (nested 2 tầng)")
        lines = rtext.splitlines()
        if len(lines) > 100:  # L6 mục lục
            head = "\n".join(lines[:30]).lower()
            if "mục lục" not in head and "contents" not in head:
                errs.append(f"{name}: references/{ref.name} {len(lines)} dòng > 100 nhưng thiếu Mục lục ở đầu")
    return errs


def check_no_todo(name, skill_dir):  # L7 (vệ sinh)
    errs = []
    for f in _md_files(skill_dir):
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if _TODO_RE.search(line):
                errs.append(f"{name}: {f.name}:{i} chứa TODO/TBD/FIXME")
    return errs


def lint_skill(skill_dir: Path):
    name = skill_dir.name
    fm, body = parse_skill(skill_dir / "SKILL.md")
    return (
        check_frontmatter(name, fm)
        + check_description(name, fm)
        + check_body_lines(name, body)
        + check_references(name, skill_dir, body)
        + check_no_todo(name, skill_dir)
    )


# ---------- Self-fixture: chứng minh mỗi check flag đúng (không đụng skill thật) ----------

def _make_skill(tmp_path, name="good-skill", description=None, body_lines=10,
                refs=None):
    d = tmp_path / name
    d.mkdir()
    desc = description if description is not None else ("x" * 120)
    body = "\n".join(f"line {i}" for i in range(body_lines))
    (d / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: >\n  {desc}\n---\n\n# {name}\n\n{body}\n",
        encoding="utf-8",
    )
    if refs:
        rd = d / "references"
        rd.mkdir()
        for fname, content in refs.items():
            (rd / fname).write_text(content, encoding="utf-8")
    return d


def test_good_skill_passes(tmp_path):
    d = _make_skill(tmp_path)
    assert lint_skill(d) == []


def test_l1_name_mismatch_flagged(tmp_path):
    d = _make_skill(tmp_path, name="good-skill")
    (d / "SKILL.md").write_text(
        "---\nname: wrong-name\ndescription: >\n  " + "x" * 120 + "\n---\n\n# x\n\nbody\n",
        encoding="utf-8",
    )
    assert any("!= tên thư mục" in e for e in lint_skill(d))


def test_l2_short_description_flagged(tmp_path):
    d = _make_skill(tmp_path, description="quá ngắn")
    assert any("< 80" in e for e in lint_skill(d))


def test_l3_long_body_flagged(tmp_path):
    d = _make_skill(tmp_path, name="huge-skill", body_lines=400)
    assert any("> 300" in e for e in lint_skill(d))


def test_l3_allowlisted_body_ok(tmp_path, monkeypatch):
    monkeypatch.setattr("cli.tests.test_skill_standard.BODY_LINE_ALLOWLIST", {"huge-skill"})
    d = _make_skill(tmp_path, name="huge-skill", body_lines=400)
    assert lint_skill(d) == []


def test_l4_orphan_reference_flagged(tmp_path):
    d = _make_skill(tmp_path, refs={"unused.md": "nội dung\n"})
    assert any("orphan" in e for e in lint_skill(d))


def test_l4_dangling_reference_flagged(tmp_path):
    d = _make_skill(tmp_path, description="x" * 120)
    (d / "SKILL.md").write_text(
        "---\nname: good-skill\ndescription: >\n  " + "x" * 120 +
        "\n---\n\n# x\n\nXem [references/missing.md](references/missing.md).\n",
        encoding="utf-8",
    )
    assert any("không tồn tại" in e for e in lint_skill(d))


def test_l5_nested_reference_flagged(tmp_path):
    body = "# ref\n\nXem [references/other.md](references/other.md) để biết thêm.\n"
    d = _make_skill(tmp_path, refs={"a.md": body})
    # SKILL.md phải nhắc a.md để không lẫn với lỗi orphan
    (d / "SKILL.md").write_text(
        "---\nname: good-skill\ndescription: >\n  " + "x" * 120 +
        "\n---\n\n# x\n\nXem [references/a.md](references/a.md).\n",
        encoding="utf-8",
    )
    assert any("nested" in e for e in lint_skill(d))


def test_l6_long_reference_without_toc_flagged(tmp_path):
    long_ref = "# Ref\n\n" + "\n".join(f"dòng {i}" for i in range(150))
    d = _make_skill(tmp_path, refs={"big.md": long_ref})
    (d / "SKILL.md").write_text(
        "---\nname: good-skill\ndescription: >\n  " + "x" * 120 +
        "\n---\n\n# x\n\nXem [references/big.md](references/big.md).\n",
        encoding="utf-8",
    )
    assert any("thiếu Mục lục" in e for e in lint_skill(d))


def test_l6_long_reference_with_toc_ok(tmp_path):
    long_ref = "# Ref\n\n## Mục lục\n- a\n- b\n\n" + "\n".join(f"dòng {i}" for i in range(150))
    d = _make_skill(tmp_path, refs={"big.md": long_ref})
    (d / "SKILL.md").write_text(
        "---\nname: good-skill\ndescription: >\n  " + "x" * 120 +
        "\n---\n\n# x\n\nXem [references/big.md](references/big.md).\n",
        encoding="utf-8",
    )
    assert [e for e in lint_skill(d) if "Mục lục" in e] == []


def test_l7_todo_flagged(tmp_path):
    d = _make_skill(tmp_path)
    (d / "SKILL.md").write_text(
        (d / "SKILL.md").read_text(encoding="utf-8") + "\nTODO: viết nốt\n",
        encoding="utf-8",
    )
    assert any("TODO" in e for e in lint_skill(d))


# ---------- Enforce trên skill thật ----------

def _real_skill_dirs():
    return sorted(
        d for d in SKILLS_DIR.iterdir()
        if d.is_dir() and (d / "SKILL.md").exists()
    )


@pytest.mark.parametrize("skill_dir", _real_skill_dirs(), ids=lambda p: p.name)
def test_skill_meets_standard(skill_dir):
    errs = lint_skill(skill_dir)
    assert not errs, "\n".join(errs)


def test_skill_index_in_sync():  # L8 (BP-01)
    index = yaml.safe_load((SKILLS_DIR / "skill-index.yaml").read_text(encoding="utf-8"))
    indexed = {s["name"] for s in index.get("skills", [])}
    dirs = {d.name for d in _real_skill_dirs()}
    assert indexed == dirs, f"index lệch: chỉ-index={indexed - dirs}, chỉ-dir={dirs - indexed}"
