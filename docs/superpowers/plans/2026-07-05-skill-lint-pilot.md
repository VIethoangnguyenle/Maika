# Skill-Lint + Pilot Migrate — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Một pytest lint (`cli/tests/test_skill_standard.py`) enforce cơ học rubric BP-01..BP-08 cho mọi SKILL.md; hai skill nặng nhất (`infra-tdd`, `spec-extract`) migrate xuống ≤ 300 dòng body qua progressive disclosure — nội dung chỉ DI CHUYỂN, không đổi ngữ nghĩa.

**Architecture:** Lint là các hàm check thuần + test parametrize trên `.maika/skills/*`, chạy trong CI matrix sẵn có (ubuntu+windows) qua `cli/tests/`. Không hạ tầng mới, không scaffold xuống downstream. Migrate = tách section sâu từ SKILL.md sang `references/` (link 1 tầng + điều kiện đọc + mục lục nếu > 100 dòng), giữ trong SKILL.md phần trigger/checklist/output/self-check.

**Tech Stack:** Python 3.10+ (stdlib + PyYAML đã có), pytest (`--import-mode=importlib`).

**Spec:** `docs/superpowers/specs/2026-07-05-skill-lint-pilot-design.md`
**Rubric nguồn (chuẩn):** `docs/superpowers/specs/2026-07-04-anthropic-bp-rubric.md` (BP-01..BP-09)

## Global Constraints

- **Tiếng Việt** cho văn bản/docstring/message mới; identifier kỹ thuật tiếng Anh; giữ NGUYÊN VĂN placeholder `{{ platform.framework_root }}` / `{% if %}` trong file `.maika/`.
- **Không dependency mới**; chỉ stdlib + PyYAML.
- **Cross-OS**: lint đọc file bằng `pathlib`, không lệnh POSIX-only, không `/proc`. Đường dẫn dùng `/`.
- **Máy dev này**: chạy pytest bằng `/usr/bin/python3` (venv `.venv` thiếu jsonschema). Trong doc/scaffold vẫn viết `python3`.
- **Migrate = di chuyển, KHÔNG viết lại**: mọi đoạn xóa hẳn (không chuyển đi đâu) phải liệt kê trong report kèm lý do (trùng lặp / dạy điều model đã biết — BP-05). Claude review diff cũ↔mới từng dòng.
- Commit message convention repo + trailer co-author theo agent thực thi.
- Branch: `feat/skill-standard-lint` (đã checkout — KHÔNG đổi branch).

### Dữ liệu vi phạm đã đo trước (nguồn sự thật cho Task 2)

Đo bằng `/usr/bin/python3` trên body-only (sau frontmatter), 2026-07-05:

- **L2 (description 80..1024 ký tự)**: 0 vi phạm (toàn bộ 262–478 ký tự).
- **L3 (body ≤ 300 dòng)**: 7 vi phạm — `architecture-reviewer` (389), `infra-tdd` (464), `knowledge-curator` (396), `openspec-explore` (343), `requirement-analyst` (362), `spec-extract` (444), `spec-validator` (343).
  - **Hiệu chỉnh so với spec §3.1**: spec liệt kê allowlist 6 skill theo TỔNG dòng (gồm frontmatter); đo body-only cho kết quả khác — `db-explorer` body ≤ 300 (rớt khỏi allowlist), `openspec-explore` vào. Allowlist đúng = 7 skill trên (gồm 2 pilot). Con số body-only là chuẩn (BP-03 nói "SKILL.md body").
- **L6 (references > 100 dòng thiếu Mục lục)**: 8 file — `author-dna-builder/references/{code-evidence-scan.md(178), dna-usage-guide.md(153)}`, `codebase-explorer/references/altitude-routing.md(120)`, `convention-intelligence-builder/references/conventions-draft-template.md(211)`, `infra-tdd/references/{adr-guide.md(252), diagrams-guide.md(115), socratic-deep-dive.md(188)}`, `knowledge-curator/references/m7-memory-push.md(130)`.
- **L1, L4, L5, L7, L8**: 0 vi phạm (frontmatter đủ, index sync, không orphan/dangling/nested ref, không TODO/TBD/FIXME).

---

### Task 1: skill-lint core + self-fixture tests (TDD)

**Files:**
- Create: `cli/tests/test_skill_standard.py`

**Interfaces:**
- Produces (module-level, dùng lại ở Task 2): `parse_skill(path) -> (fm: dict|None, body: str)`; các check thuần `check_frontmatter/description/body_lines/references/no_todo(...) -> list[str]`; hằng `MAX_BODY_LINES = 300`, `BODY_LINE_ALLOWLIST: set[str]`.

- [ ] **Bước 1: Viết file test với hàm lint + self-fixture (bản đầy đủ)**

Tạo `cli/tests/test_skill_standard.py`:

```python
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
```

- [ ] **Bước 2: Chạy self-fixture, xác nhận PASS**

Run: `/usr/bin/python3 -m pytest cli/tests/test_skill_standard.py -v`
Expected: 12 test PASS (không có test scan skill thật ở task này).

- [ ] **Bước 3: Commit**

```bash
git add cli/tests/test_skill_standard.py
git commit -m "test(skill-lint): check cơ học BP-01..BP-08 + self-fixture"
```

---

### Task 2: Enforce trên skill thật + fix L6 (8 file thiếu Mục lục)

**Files:**
- Modify: `cli/tests/test_skill_standard.py` (thêm test parametrize scan skill thật)
- Modify (thêm Mục lục, KHÔNG đổi nội dung khác): 8 file references đã liệt kê ở Global Constraints.

**Interfaces:**
- Consumes: `lint_skill`, `SKILLS_DIR`, `BODY_LINE_ALLOWLIST` (Task 1).

- [ ] **Bước 1: Thêm test scan skill thật (cuối file test_skill_standard.py)**

```python
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
```

- [ ] **Bước 2: Chạy, xác nhận CHỈ fail vì L6 (8 file thiếu Mục lục)**

Run: `/usr/bin/python3 -m pytest cli/tests/test_skill_standard.py -k "meets_standard or index_in_sync" -q`
Expected: các test parametrize fail đúng ở 5 skill có ref thiếu TOC (`author-dna-builder`, `codebase-explorer`, `convention-intelligence-builder`, `infra-tdd`, `knowledge-curator`); message chứa "thiếu Mục lục". L3 KHÔNG fail (7 skill quá dòng đều trong allowlist). `test_skill_index_in_sync` PASS.
Nếu có fail NGOÀI L6/allowlist: DỪNG, ghi BLOCKED + nguyên văn output (dữ liệu đo có thể đã đổi).

- [ ] **Bước 3: Thêm Mục lục vào 8 file references**

Với MỖI file dưới đây: chèn ngay sau dòng heading `#` đầu tiên (và dòng mô tả `>` nếu có) một block:

```markdown
## Mục lục

- <liệt kê các heading `##`/`###` cấp cao có sẵn trong file, nguyên văn>
```

Danh sách 8 file (đọc từng file, lấy đúng các heading cấp `##` của nó để điền Mục lục — KHÔNG thêm/xóa nội dung khác):
- `.maika/skills/author-dna-builder/references/code-evidence-scan.md`
- `.maika/skills/author-dna-builder/references/dna-usage-guide.md`
- `.maika/skills/codebase-explorer/references/altitude-routing.md`
- `.maika/skills/convention-intelligence-builder/references/conventions-draft-template.md`
- `.maika/skills/infra-tdd/references/adr-guide.md`
- `.maika/skills/infra-tdd/references/diagrams-guide.md`
- `.maika/skills/infra-tdd/references/socratic-deep-dive.md`
- `.maika/skills/knowledge-curator/references/m7-memory-push.md`

- [ ] **Bước 4: Chạy lại, xác nhận GREEN**

Run: `/usr/bin/python3 -m pytest cli/tests/test_skill_standard.py -q`
Expected: toàn bộ PASS (12 self-fixture + 14 parametrize + index_in_sync).

- [ ] **Bước 5: Commit**

```bash
git add cli/tests/test_skill_standard.py .maika/skills/*/references/*.md
git commit -m "test(skill-lint): enforce trên skill thật + thêm Mục lục 8 file references (BP-04)"
```

---

### Task 3: Pilot migrate `infra-tdd` (464 → ≤ 300 body)

**Files:**
- Modify: `.maika/skills/infra-tdd/SKILL.md` (rút xuống ≤ 300, nhắm ~200)
- Create: các file trong `.maika/skills/infra-tdd/references/` cho nội dung tách ra (đã có sẵn: `adr-guide.md`, `diagrams-guide.md`, `socratic-deep-dive.md`)
- Modify: `cli/tests/test_skill_standard.py` (xóa `infra-tdd` khỏi `BODY_LINE_ALLOWLIST`)

**Bối cảnh:** `infra-tdd` ĐÃ tách một phần (3 ref có sẵn). Body còn 464 dòng — cần tách thêm ~170 dòng. Đây là việc **degrees-of-freedom cao** (nhiều cách chia hợp lệ) — plan cho mapping + ràng buộc cứng, Claude review ngữ nghĩa.

**Mapping đề xuất (giữ trong SKILL.md ↔ tách ra references/):**
- GIỮ trong SKILL.md: frontmatter; `## Mục tiêu`; `## Khi nào sử dụng` / `## Khi nào KHÔNG`; `## Triết lý cốt lõi` (rút còn ý chính); `## Quy trình` (Bước 1–8 dạng checklist đánh số súc tích, mỗi bước 1–3 dòng + lệnh nếu có); `## Đầu ra`; self-check cuối.
- TÁCH sang `references/knowledge-first-protocol.md` (MỚI, có Mục lục): toàn bộ `## Knowledge-First Protocol` + chi tiết `#### T0–T4` + `### Graceful Degradation`.
- TÁCH sang `references/cau-truc-5-tang.md` (MỚI, có Mục lục): chi tiết `## Cấu trúc 5 Tầng (Hybrid)` nếu dài.
- TÁCH sang `references/format-standards.md` (MỚI, có Mục lục nếu > 100 dòng): `## Format Standards` + chi tiết diagram/format.
- Nội dung sâu của từng Bước (nếu có) dồn vào ref tương ứng; SKILL.md chỉ giữ checklist + link "đọc khi…".

**Ràng buộc cứng:**
- Mỗi ref MỚI: SKILL.md phải nhắc `[references/<f>.md](references/<f>.md)` kèm điều kiện đọc ("Xem … khi …"); ref > 100 dòng phải có `## Mục lục`; ref KHÔNG link sang ref khác.
- Di chuyển verbatim; đoạn xóa hẳn phải ghi vào report + lý do (BP-05).
- Giữ nguyên placeholder `{{ ... }}`.

- [ ] **Bước 1: Đọc toàn bộ SKILL.md hiện tại + 3 ref có sẵn** để không tách trùng.

Run: `wc -l .maika/skills/infra-tdd/SKILL.md; ls .maika/skills/infra-tdd/references/`

- [ ] **Bước 2: Thực hiện tách** theo mapping trên. Tạo ref mới, cắt nội dung khỏi SKILL.md, thêm link + điều kiện đọc trong SKILL.md.

- [ ] **Bước 3: Xóa `infra-tdd` khỏi allowlist**

Edit `cli/tests/test_skill_standard.py` — trong `BODY_LINE_ALLOWLIST` xóa dòng:

```python
    "infra-tdd",       # pilot — xóa ở Task 3
```

- [ ] **Bước 4: Đồng bộ skill-index** (frontmatter infra-tdd KHÔNG đổi → index không đổi; chạy để chắc chắn)

Run: `/usr/bin/python3 .maika/tools/skill-index/generate_index.py`
Expected: `Successfully generated ... with 14 skills.`; `git diff --stat .maika/skills/skill-index.yaml` không có thay đổi (nếu có thay đổi ngoài dự kiến: DỪNG, báo).

- [ ] **Bước 5: Lint xanh + body ≤ 300**

Run: `/usr/bin/python3 -m pytest cli/tests/test_skill_standard.py -q`
Expected: toàn bộ PASS (infra-tdd giờ không allowlist mà vẫn ≤ 300).
Run: `/usr/bin/python3 -c "p=open('.maika/skills/infra-tdd/SKILL.md').read().split('---',2)[2]; print(len(p.splitlines()),'dòng body')"`
Expected: ≤ 300 (nhắm ~200).

- [ ] **Bước 6: Commit**

```bash
git add .maika/skills/infra-tdd/ cli/tests/test_skill_standard.py
git commit -m "refactor(infra-tdd): progressive disclosure — body ≤300, tách references (BP-03/BP-04)"
```

---

### Task 4: Pilot migrate `spec-extract` (444 → ≤ 300 body)

**Files:**
- Modify: `.maika/skills/spec-extract/SKILL.md`
- Create: `.maika/skills/spec-extract/references/*.md` (skill này CHƯA có references/)
- Modify: `cli/tests/test_skill_standard.py` (xóa `spec-extract` khỏi allowlist)

**Mapping đề xuất:**
- GIỮ trong SKILL.md: frontmatter; `## Quy tắc cốt lõi (reflex)` (ngắn); `## 1. Mục tiêu`; `## 2. Khi nào dùng` / `## Khi nào KHÔNG`; `## 3. Input / Output` (giữ Input + skeleton Output súc tích); `## 4. Quy trình chi tiết` rút thành checklist Bước 1–10 (mỗi bước 1–3 dòng); `## 5. Cập nhật AGENT_TRANSPARENCY`; `## [L3] Staleness Warning`; self-check.
- TÁCH sang `references/quy-trinh-chi-tiet.md` (MỚI, có Mục lục): toàn bộ nội dung sâu của Bước 1–10 (hiện chiếm ~260 dòng, lines ~156–417) — mô tả chi tiết mỗi bước, ví dụ, sub-rule.
- TÁCH sang `references/output-schema.md` (MỚI, có Mục lục nếu > 100 dòng): skeleton Output đầy đủ (`### Output` chi tiết) nếu dài.

**Ràng buộc cứng:** như Task 3 (link + điều kiện đọc + Mục lục; verbatim; ghi đoạn xóa hẳn; giữ placeholder). Đặc biệt giữ NGUYÊN `### Bước 5b — Thống kê Integration & Field Mapping` (vừa thêm ở đợt trước) — chuyển sang ref cùng các bước khác, không rơi.

- [ ] **Bước 1: Đọc toàn bộ SKILL.md hiện tại.** Run: `wc -l .maika/skills/spec-extract/SKILL.md`

- [ ] **Bước 2: Tạo `references/` + tách nội dung** theo mapping.

- [ ] **Bước 3: Xóa `spec-extract` khỏi allowlist**

Edit `cli/tests/test_skill_standard.py` — xóa dòng:

```python
    "spec-extract",     # pilot — xóa ở Task 4
```

- [ ] **Bước 4: Đồng bộ skill-index**

Run: `/usr/bin/python3 .maika/tools/skill-index/generate_index.py`
Expected: 14 skills; `skill-index.yaml` không đổi (frontmatter spec-extract giữ nguyên).

- [ ] **Bước 5: Lint xanh + body ≤ 300**

Run: `/usr/bin/python3 -m pytest cli/tests/test_skill_standard.py -q` → PASS.
Run: `/usr/bin/python3 -c "p=open('.maika/skills/spec-extract/SKILL.md').read().split('---',2)[2]; print(len(p.splitlines()),'dòng body')"` → ≤ 300.

- [ ] **Bước 6: Commit**

```bash
git add .maika/skills/spec-extract/ cli/tests/test_skill_standard.py
git commit -m "refactor(spec-extract): progressive disclosure — body ≤300, tách references (BP-03/BP-04)"
```

---

### Task 5: Snapshot refresh + regression toàn repo

**Files:**
- Modify (nếu fail): `cli/tests/snapshots/{antigravity,claude-code,codex,generic}.txt`

**Bối cảnh:** Task 3–4 tạo file references MỚI → cây scaffold đổi → snapshot test fail. Refresh cho khớp.

- [ ] **Bước 1: Chạy snapshot test, xem file mới nào cần thêm**

Run: `/usr/bin/python3 -m pytest cli/tests/test_snapshots.py -v`
Expected: FAIL 4 platform; diff cho thấy các dòng ref MỚI của infra-tdd + spec-extract.

- [ ] **Bước 2: Thêm các dòng ref mới vào 4 snapshot đúng vị trí sort**

Với mỗi file `cli/tests/snapshots/{antigravity,codex,generic,claude-code}.txt`: thêm các đường dẫn references mới (theo prefix root của từng file: `.agents` cho antigravity/codex, `.claude` cho claude-code, `.maika` cho generic) đúng thứ tự alphabet như cây thật. Lấy danh sách dòng cần thêm từ diff Bước 1.

- [ ] **Bước 3: Snapshot xanh**

Run: `/usr/bin/python3 -m pytest cli/tests/test_snapshots.py -q` → PASS 4/4.

- [ ] **Bước 4: Full regression**

Run: `/usr/bin/python3 -m pytest .maika/ cli/ -q`
Expected: **535 baseline + số test skill-lint mới**, 0 failed, 1 skipped. Ghi số chính xác vào report.

- [ ] **Bước 5: Commit**

```bash
git add cli/tests/snapshots/
git commit -m "test(snapshots): refresh scaffold tree cho references pilot infra-tdd + spec-extract"
```

---

## Ghi chú deviation so với spec

1. **Allowlist L3 = 7 skill (body-only), không phải 6 (total-line)**: spec §3.1 đếm tổng dòng gồm frontmatter; chuẩn BP-03 nói "body" → đo body-only. Hệ quả: `db-explorer` rớt khỏi allowlist (body ≤ 300), danh sách đúng gồm cả `openspec-explore`. Đã phản ánh trong `BODY_LINE_ALLOWLIST` (Task 1).
2. **`infra-tdd` đã có 3 references sẵn**: không phải migrate từ zero; Task 3 chỉ tách phần còn dư. Mục lục cho 3 ref cũ thuộc Task 2 (L6 fix).
3. **Vi phạm thực tế chỉ có L3 + L6**: L1/L2/L4/L5/L7/L8 sạch (đo trước) — Task 2 nhẹ hơn spec dự phòng ("sửa vi phạm nhỏ"), chỉ còn L6.
