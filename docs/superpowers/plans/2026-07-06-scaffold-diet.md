# Scaffold Diet Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scaffold chỉ mang sang downstream những artifact có consumer cơ học — cắt `tests/` của framework (~784K), cắt `skill-lint`, vá 2 broken ref (`skills/skill-index.yaml`, `tools/README.md`), wire lệnh gọi `knowledge-index` tường minh.

**Architecture:** Mở rộng exclude-list mặc định trong `copy_and_render_directory` (không thêm field manifest); chỉnh `cli/plugin-manifest.yaml`; sửa nội dung `.maika/*.md` liên quan; regen 4 snapshot. Spec: `docs/superpowers/specs/2026-07-06-scaffold-diet-design.md`.

**Tech Stack:** Python 3, pytest (`/usr/bin/python3 -m pytest` — KHÔNG dùng venv python), Jinja2, YAML manifest.

**Nhánh:** `refactor/scaffold-diet` (đã có commit `3587f02` — WIP knowledge-index framework-side, đã commit trước).

**Script regen snapshot** (dùng ở nhiều task — lưu tại `<scratchpad>/regen_snapshots.py`, chạy từ repo root):

```python
import tempfile
from pathlib import Path

from cli.commands.init import run_init

PLATFORM_OPTIONS = {
    "antigravity": {"mcps": ["codebase-memory-mcp", "confluence", "db-remote"], "language": "python"},
    "codex":       {"mcps": ["codebase-memory-mcp", "confluence", "db-remote"], "language": "python"},
    "claude-code": {"mcps": ["codebase-memory-mcp", "confluence", "db-remote"], "language": "python"},
    "generic":     {"mcps": [], "language": "other"},
}

def snapshot_tree(root: Path) -> str:
    entries = []
    for path in sorted(root.rglob("*"), key=lambda p: p.relative_to(root).parts):
        rel = path.relative_to(root).as_posix()
        if "__pycache__" in rel:
            continue
        entries.append(f"{rel}{'/' if path.is_dir() else ''}")
    return "\n".join(entries) + "\n"

repo = Path.cwd()
for key, opt in sorted(PLATFORM_OPTIONS.items()):
    with tempfile.TemporaryDirectory() as td:
        target = Path(td) / "proj"
        run_init(target_dir=str(target), maika_root=str(repo), platform_key=key,
                 selected_mcps=opt["mcps"], language=opt["language"], assume_yes=True)
        (repo / "cli" / "tests" / "snapshots" / f"{key}.txt").write_text(
            snapshot_tree(target), encoding="utf-8")
    print("regenerated", key)
```

Chạy: `PYTHONPATH=. /usr/bin/python3 <scratchpad>/regen_snapshots.py`
(PLATFORM_OPTIONS/snapshot_tree cố tình lặp lại từ `cli/tests/test_snapshots.py` — script vứt đi, không import test module.)

---

### Task 1: Renderer — exclude dir `tests` mặc định (D1)

**Files:**
- Modify: `cli/renderer.py:112-119` (default exclude list)
- Test: `cli/tests/test_render.py` (thêm test mới cuối file)
- Regen: `cli/tests/snapshots/*.txt`

- [x] **Step 1: Viết failing test** — thêm vào cuối `cli/tests/test_render.py`:

```python
def test_directory_render_excludes_framework_test_dirs(tmp_path, jinja_env, claude_context):
    # Framework CI tests (tools/*/tests, hooks/write-gate/tests) never ship
    # downstream — no scaffolded file invokes them (scaffold-diet audit 2026-07-06).
    src = tmp_path / "src"
    (src / "tests" / "fixtures").mkdir(parents=True)
    (src / "cli.py").write_text("code\n", encoding="utf-8")
    (src / "tests" / "test_cli.py").write_text("test\n", encoding="utf-8")
    (src / "tests" / "fixtures" / "sample.md").write_text("fx\n", encoding="utf-8")
    dst = tmp_path / "dst"
    copy_and_render_directory(jinja_env, src, dst, claude_context)
    assert (dst / "cli.py").exists()
    assert not (dst / "tests").exists()
```

- [x] **Step 2: Chạy test, xác nhận FAIL**

Run: `/usr/bin/python3 -m pytest cli/tests/test_render.py::test_directory_render_excludes_framework_test_dirs -v`
Expected: FAIL — `assert not (dst / "tests").exists()` sai (tests đang bị copy).

- [x] **Step 3: Implement** — trong `cli/renderer.py`, thêm `"tests",` vào default list:

```python
    exclude = exclude_patterns or [
        "__pycache__", ".pytest_cache", "*.pyc", ".git",
        # Framework CI artifacts — no scaffolded consumer downstream:
        "tests",               # tools/*/tests, hooks/write-gate/tests
        # Per-project instance / build artifacts that must never be scaffolded
        # from the framework source (only their templates/seeds ship):
        "persona.yaml",        # ship persona.template.yaml; user creates persona.yaml
        "rules.json",          # rule-projector build output (regenerated per project)
        "*.generated.xml",     # rule-projector checkstyle output
    ]
```

- [x] **Step 4: Chạy test, xác nhận PASS**

Run: `/usr/bin/python3 -m pytest cli/tests/test_render.py -v`
Expected: PASS toàn bộ file.

- [x] **Step 5: Regen snapshots + full suite**

Run: `PYTHONPATH=. /usr/bin/python3 <scratchpad>/regen_snapshots.py`
Rồi: `/usr/bin/python3 -m pytest cli/tests -q`
Expected: PASS (292 passed, 1 skipped). Diff snapshot chỉ **xóa** các dòng `*/tests/*` (tools + hooks/write-gate).

- [x] **Step 6: Commit**

```bash
git add cli/renderer.py cli/tests/test_render.py cli/tests/snapshots/
git commit -m "refactor(scaffold): exclude framework tests/ dirs from copy_dir scaffolding"
```

---

### Task 2: Cắt `skill-lint` khỏi manifest + sửa ref downstream (D2)

**Files:**
- Modify: `cli/plugin-manifest.yaml:325-330` (xóa entry `skill-lint`)
- Modify: `.maika/rules/rules-knowledge.md:119-126` (R-Skill-2)
- Modify: `.maika/meta-prompt.md:252` và `.maika/meta-prompt.md:60-61`
- Modify: `.maika/tools/README.md:47-50` (§skill-lint), `:56-58` (§skill-index)
- Test: `cli/tests/test_scaffold.py` (thêm test manifest mới)
- Regen: `cli/tests/snapshots/*.txt`

- [x] **Step 1: Viết failing test** — thêm vào `cli/tests/test_scaffold.py` (mirror style test line 189):

```python
def test_manifest_omits_framework_dev_only_tools(maika_root):
    # skill-lint là tool authoring của repo framework (R7; skill-lint-pilot
    # design đã chốt lint không scaffold xuống downstream).
    manifest = load_manifest(maika_root)
    by_name = {p["name"]: p for p in manifest["plugins"]}
    assert "skill-lint" not in by_name
```

- [x] **Step 2: Chạy test, xác nhận FAIL**

Run: `/usr/bin/python3 -m pytest cli/tests/test_scaffold.py::test_manifest_omits_framework_dev_only_tools -v`
Expected: FAIL — `skill-lint` đang có trong manifest.

- [x] **Step 3: Xóa entry khỏi `cli/plugin-manifest.yaml`** (6 dòng):

```yaml
  - name: skill-lint
    type: tool
    source: tools/skill-lint/
    template: false
    output: "{{ platform.framework_root }}/tools/skill-lint/"
    copy_dir: true
```

- [x] **Step 4: Sửa R-Skill-2 trong `.maika/rules/rules-knowledge.md`** — thay block lines 119-126 bằng:

```markdown
### [CRITICAL] R-Skill-2: Lint gate bắt buộc trước khi merge skill mới/sửa

- Skill authoring là hoạt động **repo framework Maika** — skills downstream là
  framework-owned, bị `maika update` ghi đè, không sửa tại downstream.
- Khi tạo skill mới hoặc sửa `SKILL.md` (repo framework), **PHẢI** chạy lint trước khi commit:
  ```
  python3 .maika/tools/skill-lint/validate_skills.py
  ```
  (tool nằm trong repo framework, không scaffold sang downstream)
- Kết quả phải là `PASS` cho skill đó. `FAIL` = không được merge.
- Spec doc (repo framework): `docs/superpowers/specs/2026-06-17-sp2-skill-standardization-design.md`
```

- [x] **Step 5: Sửa `.maika/meta-prompt.md`** — 2 chỗ:

Dòng 252, thay bằng:
```markdown
- Mọi SKILL.md tuân theo **Hybrid Schema SP2** (§15 trong rules-knowledge.md) — validate bằng `python3 .maika/tools/skill-lint/validate_skills.py` (repo framework, không scaffold sang downstream).
```

Dòng 60-61 (mục `tools/` trong cây thư mục), thay bằng:
```markdown
    ├── tools/                               ← gate-check, microloop-orchestrator, knowledge-index,
    │                                          mcp-bridge, rule-projector (xem tools/README.md;
    │                                          skill-lint & skill-index: chỉ repo framework)
```

- [x] **Step 6: Sửa `.maika/tools/README.md`** — §skill-lint (lines 47-50) thay bằng:

```markdown
## skill-lint/ — Skill schema validator (SP2) — chỉ repo framework

Lint mọi `skills/*/SKILL.md` theo Hybrid Schema (R-Skill-1/2). Không scaffold sang
downstream — skill authoring là hoạt động repo framework.
- **Run** (repo framework): `python3 .maika/tools/skill-lint/validate_skills.py`
```

§skill-index (lines 56-58) thay bằng:

```markdown
## skill-index/ — Skill index generator — chỉ repo framework

Sinh `skills/skill-index.yaml` từ frontmatter các SKILL.md. Tool không scaffold sang
downstream; file output `skills/skill-index.yaml` thì được ship (bootstrap READ nó).
```

- [x] **Step 7: Regen snapshots + full suite**

Run: `PYTHONPATH=. /usr/bin/python3 <scratchpad>/regen_snapshots.py`
Rồi: `/usr/bin/python3 -m pytest cli/tests -q`
Expected: PASS. Diff snapshot: mất `*/tools/skill-lint/` (sau Task 1 chỉ còn 2 dòng: dir + validate_skills.py).

- [x] **Step 8: Kiểm không còn ref templated tới skill-lint**

Run: `/usr/bin/grep -rn "framework_root }}/tools/skill-lint" .maika/`
Expected: 0 kết quả.

- [x] **Step 9: Commit**

```bash
git add cli/plugin-manifest.yaml cli/tests/test_scaffold.py cli/tests/snapshots/ .maika/rules/rules-knowledge.md .maika/meta-prompt.md .maika/tools/README.md
git commit -m "refactor(scaffold): stop shipping skill-lint downstream; scope R-Skill-2 to framework repo"
```

---

### Task 3: Ship `skills/skill-index.yaml` + `tools/README.md` (D4, D5)

**Files:**
- Modify: `cli/plugin-manifest.yaml` (2 entry mới)
- Modify: `.maika/tools/README.md` (3 dòng **Test** → repo framework)
- Test: `cli/tests/test_scaffold.py`, `cli/tests/test_init.py`
- Regen: `cli/tests/snapshots/*.txt`

- [x] **Step 1: Viết failing tests**

Thêm vào `cli/tests/test_scaffold.py`:

```python
def test_manifest_ships_skill_index_data_and_tools_readme(maika_root):
    # Consumers: bootstrap.md READ skills/skill-index.yaml; meta-prompt trỏ tools/README.md (R1).
    manifest = load_manifest(maika_root)
    by_name = {p["name"]: p for p in manifest["plugins"]}
    assert by_name["skill-index-data"]["source"] == "skills/skill-index.yaml"
    assert by_name["skill-index-data"]["output"] == "{{ platform.framework_root }}/skills/skill-index.yaml"
    assert not by_name["skill-index-data"].get("copy_dir")
    assert by_name["tools-readme"]["source"] == "tools/README.md"
    assert by_name["tools-readme"]["output"] == "{{ platform.framework_root }}/tools/README.md"
```

Thêm vào `cli/tests/test_init.py` (mirror style các test init hiện có):

```python
def test_init_scaffold_diet_ships_only_consumed_tooling(tmp_path, maika_root):
    target = tmp_path / "proj"
    run_init(
        target_dir=str(target), maika_root=str(maika_root), platform_key="claude-code",
        selected_mcps=[], language="python", assume_yes=True,
    )
    tools = target / ".claude" / "tools"
    assert (tools / "gate-check" / "cli.py").exists()
    assert (tools / "README.md").exists()                                  # meta-prompt trỏ tới
    assert not (tools / "skill-lint").exists()                             # framework-dev only
    assert not (tools / "gate-check" / "tests").exists()                   # CI framework không ship
    assert not (target / ".claude" / "hooks" / "write-gate" / "tests").exists()
    assert (target / ".claude" / "skills" / "skill-index.yaml").exists()   # bootstrap READ
```

- [x] **Step 2: Chạy, xác nhận FAIL**

Run: `/usr/bin/python3 -m pytest cli/tests/test_scaffold.py::test_manifest_ships_skill_index_data_and_tools_readme cli/tests/test_init.py::test_init_scaffold_diet_ships_only_consumed_tooling -v`
Expected: cả 2 FAIL (thiếu entry manifest → KeyError / file không tồn tại).

- [x] **Step 3: Thêm 2 entry vào `cli/plugin-manifest.yaml`**

Sau entry `openspec-archive-change` (trước comment `# ─── WORKFLOWS ───`):

```yaml
  - name: skill-index-data
    type: skill
    source: skills/skill-index.yaml
    template: false
    output: "{{ platform.framework_root }}/skills/skill-index.yaml"
```

Sau entry `knowledge-index` (cuối section `# ─── TOOLS ───`):

```yaml
  - name: tools-readme
    type: tool
    source: tools/README.md
    template: false
    output: "{{ platform.framework_root }}/tools/README.md"
```

Lưu ý: `skill-index.yaml` không có frontmatter `---` → `scaffold_native_skill_exports`
tự skip (in 1 dòng ⏭️ trên platform có native export — chấp nhận được).
`tools/README.md` chứa `{{ platform.framework_root }}` → auto-render (`.md` + chứa `{{ `).

- [x] **Step 4: Sửa 3 dòng **Test** trong `.maika/tools/README.md`** (file này giờ ship downstream — đường dẫn tests phải trỏ repo framework):

Dòng 19 (rule-projector): `- **Test** (repo framework): \`python3 -m pytest .maika/tools/rule-projector/tests/ -v\``
Dòng 37 (microloop): `- **Test** (repo framework): \`python3 -m pytest .maika/tools/microloop-orchestrator/tests/ -v\``
Dòng 45 (gate-check): `- **Test** (repo framework): \`python3 -m pytest .maika/tools/gate-check/tests/ -v\``

- [x] **Step 5: Regen snapshots + full suite**

Run: `PYTHONPATH=. /usr/bin/python3 <scratchpad>/regen_snapshots.py`
Rồi: `/usr/bin/python3 -m pytest cli/tests -q`
Expected: PASS. Diff snapshot: thêm `skills/skill-index.yaml` + `tools/README.md` per platform.

- [x] **Step 6: Commit**

```bash
git add cli/plugin-manifest.yaml cli/tests/ .maika/tools/README.md
git commit -m "feat(scaffold): ship skills/skill-index.yaml and tools/README.md (fix broken downstream refs)"
```

---

### Task 4: Wire lệnh gọi knowledge-index tường minh (D3)

**Files:**
- Modify: `.maika/workflows/approve-dna.md` (Bước 3, block lines 71-83)
- Modify: `.maika/workflows/approve-conventions.md` (Bước 3, block lines 60-73)
- Modify: `.maika/procedures/bootstrap.md:133`
- Modify: `.maika/procedures/context-loader.md:34,38`

Lệnh chuẩn (verify: `generate_index.py::main` nhận argv[0] = long-term dir):
`python3 {{ platform.framework_root }}/tools/knowledge-index/generate_index.py {{ platform.framework_root }}/knowledge/long-term`

- [x] **Step 1: `approve-dna.md`** — trong code block Bước 3 (sau mục `3. Backup draft:`), thêm:

```
4. Regenerate knowledge index (bootstrap/context-loader P3 nạp entry list từ đây):
   python3 {{ platform.framework_root }}/tools/knowledge-index/generate_index.py {{ platform.framework_root }}/knowledge/long-term
```

- [x] **Step 2: `approve-conventions.md`** — trong code block Bước 3 (sau mục `3. Backup draft:`), thêm cùng nội dung mục `4.` như trên.

- [x] **Step 3: `bootstrap.md:133`** — cell P3, thay
`**WARN** — chạy knowledge-index generator; gate sẽ kéo slice JIT` bằng:
`**WARN** — chạy \`python3 {{ platform.framework_root }}/tools/knowledge-index/generate_index.py {{ platform.framework_root }}/knowledge/long-term\`; gate sẽ kéo slice JIT`

- [x] **Step 4: `context-loader.md`** — dòng 34 và 38, thay câu WARN chung chung bằng câu kèm lệnh trên (giữ nguyên phần "hạ độ tin cậy kiến trúc" / "Agent dùng generic judgment/naming").

- [x] **Step 5: Verify render + suite**

Run: `/usr/bin/python3 -m pytest cli/tests -q`
Expected: PASS (nội dung mới đi qua Jinja render trong snapshot tests — lỗi template sẽ nổ ở đây).
Run: `/usr/bin/grep -rn "chạy knowledge-index generator" .maika/` → 0 kết quả (đã thay hết bằng lệnh cụ thể).

- [x] **Step 6: Commit**

```bash
git add .maika/workflows/approve-dna.md .maika/workflows/approve-conventions.md .maika/procedures/bootstrap.md .maika/procedures/context-loader.md
git commit -m "docs(knowledge-index): wire explicit regenerate command into approve workflows and loader WARNs"
```

---

### Task 5: Verify tổng + spec/plan commit

- [x] **Step 1: Full suite lần cuối**

Run: `/usr/bin/python3 -m pytest cli/tests -q`
Expected: PASS (293+ passed, 1 skipped).

- [x] **Step 2: Init thật vào scratchpad, kiểm bằng mắt**

```bash
PYTHONPATH=. /usr/bin/python3 -c "
from cli.commands.init import run_init
run_init(target_dir='<scratchpad>/diet-proof', maika_root='.', platform_key='claude-code',
         selected_mcps=[], language='python', assume_yes=True)"
/usr/bin/find <scratchpad>/diet-proof/.claude/tools -maxdepth 2 | sort
/usr/bin/du -sh <scratchpad>/diet-proof/.claude/tools
```
Expected: không còn `tests/`, không còn `skill-lint/`, có `README.md`; tổng tools ≤ ~450K (trước ~1.3M).

- [x] **Step 3: Commit spec + plan**

```bash
git add docs/superpowers/specs/2026-07-06-scaffold-diet-design.md docs/superpowers/plans/2026-07-06-scaffold-diet.md
git commit -m "docs(scaffold-diet): spec + implementation plan"
```

---

## Deviations khi thực thi (2026-07-06)

1. **Phrasing "source repo"**: test invariant có sẵn
   `test_*_rendered_framework_files_do_not_reference_active_maika_paths` cấm file rendered
   chứa `.maika/` trừ khi file có cụm thoát `source repo` / `legacy .maika`. Các ref literal
   `.maika/tools/skill-lint/…` (Task 2) và dòng **Test** trong tools/README.md (Task 3)
   được viết thành "(source repo framework)" thay vì "(repo framework)" như plan gốc.
2. **Dòng Run của knowledge-index trong tools/README.md** được gộp vào Task 2 (sửa cùng block)
   thay vì Task 4.
3. Kết quả thực tế tốt hơn ước tính: `.claude/tools` sau diet = **192K** (ước ≤450K; trước 1.3M).
