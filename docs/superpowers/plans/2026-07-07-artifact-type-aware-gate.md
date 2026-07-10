# Artifact-type-aware Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Gate `handoff-slice` / `implementation-context` fail khi rule-id trong `## Applicable DNA/Conventions` không tồn tại trong `knowledge-index.yaml` hoặc sai `artifact_type`; đồng thời fix `_load_index_rule_ids` bỏ rơi global rules.

**Architecture:** Mở rộng đường index-aware sẵn có của cli.py (đang chỉ wire cho `knowledge-checkpoint`) sang 2 gate còn lại. Validators trong gates.py nhận kwarg `valid_rule_ids=None` — không truyền = behavior cũ (backward compatible). Strict-in-section: chỉ quét section `## Applicable DNA/Conventions`, mọi rule-id trong đó phải thuộc slice. Slice rỗng → CLI không truyền kwarg (legacy) + WARN.

**Tech Stack:** Python 3 stdlib + PyYAML (đã dùng sẵn), pytest. Test bằng `/usr/bin/python3 -m pytest` (venv không có pytest).

**Spec:** `docs/superpowers/specs/2026-07-07-artifact-type-aware-gate-design.md`

**Bối cảnh cho engineer mới:**
- `.maika/tools/gate-check/gates.py` — validators thuần (nhận text, trả `Result(ok, reason)`), không đọc file.
- `.maika/tools/gate-check/cli.py` — CLI mỏng: đọc file, load index, gọi validator, exit 0/1. `--index`/`--artifact-type` đã có trong argparse nhưng chỉ dùng cho gate `knowledge-checkpoint`.
- Tests load module bằng `importlib.util.spec_from_file_location` (xem đầu `tests/test_gates.py`) vì tool không phải package cài đặt.
- Semantics slice chuẩn (đã chốt trong `.maika/procedures/context-loader.md` dòng 46–48): entry match khi `artifact_type in applies_to` **hoặc** `applies_to` rỗng (global).

---

### Task 1: Strict slice validation trong gates.py (cả 2 validators)

**Files:**
- Modify: `.maika/tools/gate-check/gates.py` (validate_handoff_slice ~dòng 127, validate_implementation_context ~dòng 134)
- Test: `.maika/tools/gate-check/tests/test_gates.py` (append cuối file)

- [x] **Step 1: Viết failing tests**

Append vào cuối `.maika/tools/gate-check/tests/test_gates.py`:

```python
# ── artifact_type-aware strict slice (spec 2026-07-07) ──────────────────

_IMPL_OK_BODY = (
    "## Evidence\n"
    "domain_overview: user service layer\n"
    "node_id: svc.UserService#42\nblast-radius: 2 nodes\n"
    "## Allowed Files\n- src/main/java/App.java\n"
)


def test_handoff_slice_strict_accepts_slice_rule_ids():
    text = "## Applicable DNA/Conventions\n- SP-6\n- HP-1\n"
    assert g.validate_handoff_slice(text, valid_rule_ids={"SP-6", "HP-1"}).ok is True


def test_handoff_slice_strict_rejects_wrong_artifact_type_rule():
    # RC-2 tồn tại trong index nhưng thuộc slice của artifact-type khác.
    text = "## Applicable DNA/Conventions\n- SP-6\n- RC-2\n"
    res = g.validate_handoff_slice(text, valid_rule_ids={"SP-6", "HP-1"})
    assert res.ok is False
    assert "RC-2" in res.reason


def test_handoff_slice_strict_rejects_nonexistent_rule_id():
    text = "## Applicable DNA/Conventions\n- XX-99\n"
    res = g.validate_handoff_slice(text, valid_rule_ids={"SP-6"})
    assert res.ok is False
    assert "XX-99" in res.reason


def test_handoff_slice_legacy_unchanged_without_valid_set():
    # Không truyền valid_rule_ids → behavior cũ: chỉ cần ≥1 rule-id.
    text = "## Applicable DNA/Conventions\n- XX-99\n"
    assert g.validate_handoff_slice(text).ok is True


def test_handoff_slice_strict_ignores_rule_ids_outside_section():
    # Prose ở section khác nhắc PR-33 không được gây false-fail.
    text = (
        "## Applicable DNA/Conventions\n- SP-6\n"
        "## Constraints\nsee PR-33 discussion\n"
    )
    assert g.validate_handoff_slice(text, valid_rule_ids={"SP-6"}).ok is True


def test_implementation_context_strict_rejects_foreign_rule_ids():
    text = "## Applicable DNA/Conventions\n- SP-6\n- RC-2\n" + _IMPL_OK_BODY
    res = g.validate_implementation_context(text, valid_rule_ids={"SP-6"})
    assert res.ok is False
    assert "RC-2" in res.reason


def test_implementation_context_strict_accepts_slice_rule_ids():
    text = "## Applicable DNA/Conventions\n- SP-6\n" + _IMPL_OK_BODY
    assert g.validate_implementation_context(text, valid_rule_ids={"SP-6"}).ok is True


def test_implementation_context_legacy_unchanged_without_valid_set():
    text = "## Applicable DNA/Conventions\n- XX-99\n" + _IMPL_OK_BODY
    assert g.validate_implementation_context(text).ok is True
```

- [x] **Step 2: Chạy tests, verify fail đúng chỗ**

Run: `/usr/bin/python3 -m pytest .maika/tools/gate-check/tests/test_gates.py -v -k "strict or legacy_unchanged"`
Expected: các test `*_strict_rejects_*` FAIL với `TypeError: ... unexpected keyword argument 'valid_rule_ids'`; các test legacy PASS (regression guard).

- [x] **Step 3: Implement trong gates.py**

Thêm helper ngay sau `validate_apply_gate` (trước `validate_handoff_slice`):

```python
def _foreign_rule_ids(section: str, valid_rule_ids) -> list:
    """Rule-ids cited in a slice section but absent from the index slice."""
    return sorted(set(_RULE_ID.findall(section)) - set(valid_rule_ids))
```

Thay `validate_handoff_slice` bằng:

```python
def validate_handoff_slice(text: str, valid_rule_ids=None) -> Result:
    m = re.search(r"##\s+Applicable DNA/Conventions[ \t]*\n(.*?)(?=\n##\s|\Z)", text, re.DOTALL)
    if not m or not _RULE_ID.search(m.group(1)):
        return Result(False, "handoff missing non-empty 'Applicable DNA/Conventions' with rule-ids")
    if valid_rule_ids is not None:
        foreign = _foreign_rule_ids(m.group(1), valid_rule_ids)
        if foreign:
            return Result(False, "handoff cites rule-ids not in knowledge-index slice: " + ", ".join(foreign))
    return Result(True)
```

Trong `validate_implementation_context`, đổi signature thành `def validate_implementation_context(text: str, valid_rule_ids=None) -> Result:` và chèn ngay SAU block check `applicable` (sau dòng `return Result(False, "implementation context missing Applicable DNA/Conventions rule-ids")`):

```python
    if valid_rule_ids is not None:
        foreign = _foreign_rule_ids(applicable, valid_rule_ids)
        if foreign:
            return Result(
                False,
                "implementation context cites rule-ids not in knowledge-index slice: " + ", ".join(foreign),
            )
```

- [x] **Step 4: Chạy toàn bộ test_gates.py, verify pass**

Run: `/usr/bin/python3 -m pytest .maika/tools/gate-check/tests/test_gates.py -v`
Expected: ALL PASS (test cũ + 8 test mới).

- [x] **Step 5: Commit**

```bash
git add .maika/tools/gate-check/gates.py .maika/tools/gate-check/tests/test_gates.py
git commit -m "feat(gate-check): strict slice validation for handoff-slice/implementation-context"
```

---

### Task 2: cli.py — fix global rules + wire index-aware cho 2 gate

**Files:**
- Modify: `.maika/tools/gate-check/cli.py` (`_load_index_rule_ids` dòng 35–44, `main` dòng 62–71)
- Create: `.maika/tools/gate-check/tests/test_cli_index.py`

- [x] **Step 1: Viết failing tests**

Tạo `.maika/tools/gate-check/tests/test_cli_index.py`:

```python
import importlib.util
from pathlib import Path

CLI = Path(__file__).resolve().parents[1] / "cli.py"
spec = importlib.util.spec_from_file_location("gate_cli", CLI)
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)

INDEX = """\
entries:
  - id: SP-6
    applies_to: [java-service]
  - id: HP-1
    applies_to: []
  - id: RC-2
    applies_to: [react-component]
"""

# Index không có global rule và không có entry nào cho java-service.
INDEX_NO_MATCH = """\
entries:
  - id: RC-2
    applies_to: [react-component]
"""

HANDOFF = "## Applicable DNA/Conventions\n- SP-6\n## Allowed Files\n- src/App.java\n"


def _write(tmp_path, name, content):
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return str(p)


def test_load_index_includes_global_rules_for_artifact_type(tmp_path):
    idx = _write(tmp_path, "knowledge-index.yaml", INDEX)
    ids, empty = cli._load_index_rule_ids(idx, "java-service")
    assert ids == {"SP-6", "HP-1"}  # HP-1 global (applies_to rỗng) phải nằm trong slice
    assert empty is False


def test_load_index_without_artifact_type_returns_all(tmp_path):
    idx = _write(tmp_path, "knowledge-index.yaml", INDEX)
    ids, empty = cli._load_index_rule_ids(idx, None)
    assert ids == {"SP-6", "HP-1", "RC-2"}
    assert empty is False


def test_cli_handoff_slice_strict_pass(tmp_path, capsys):
    idx = _write(tmp_path, "knowledge-index.yaml", INDEX)
    handoff = _write(tmp_path, "TASK_HANDOFF.node-1.md", HANDOFF)
    rc = cli.main(["handoff-slice", handoff, "--index", idx, "--artifact-type", "java-service"])
    assert rc == 0
    assert "PASS" in capsys.readouterr().out


def test_cli_handoff_slice_strict_fail_wrong_type(tmp_path, capsys):
    idx = _write(tmp_path, "knowledge-index.yaml", INDEX)
    handoff = _write(
        tmp_path, "TASK_HANDOFF.node-1.md",
        "## Applicable DNA/Conventions\n- SP-6\n- RC-2\n",
    )
    rc = cli.main(["handoff-slice", handoff, "--index", idx, "--artifact-type", "java-service"])
    assert rc == 1
    assert "RC-2" in capsys.readouterr().out


def test_cli_empty_slice_falls_back_to_legacy_with_warn(tmp_path, capsys):
    idx = _write(tmp_path, "knowledge-index.yaml", INDEX_NO_MATCH)
    handoff = _write(tmp_path, "TASK_HANDOFF.node-1.md", HANDOFF)
    rc = cli.main(["handoff-slice", handoff, "--index", idx, "--artifact-type", "java-service"])
    out = capsys.readouterr().out
    assert rc == 0          # legacy: ≥1 rule-id là đủ
    assert "WARN" in out    # nhưng phải cảnh báo slice rỗng


def test_cli_legacy_mode_without_index(tmp_path, capsys):
    handoff = _write(
        tmp_path, "TASK_HANDOFF.node-1.md",
        "## Applicable DNA/Conventions\n- XX-99\n",
    )
    rc = cli.main(["handoff-slice", handoff])
    assert rc == 0  # không --index → behavior cũ giữ nguyên


def test_cli_implementation_context_strict_fail_nonexistent(tmp_path, capsys):
    idx = _write(tmp_path, "knowledge-index.yaml", INDEX)
    impl = _write(
        tmp_path, "IMPLEMENTATION_CONTEXT.md",
        "## Applicable DNA/Conventions\n- XX-99\n"
        "## Evidence\ndomain_overview: user service\n"
        "node_id: svc.User#1\nblast-radius: 2 nodes\n"
        "## Allowed Files\n- src/App.java\n",
    )
    rc = cli.main(["implementation-context", impl, "--index", idx, "--artifact-type", "java-service"])
    assert rc == 1
    assert "XX-99" in capsys.readouterr().out
```

- [x] **Step 2: Chạy tests, verify fail đúng chỗ**

Run: `/usr/bin/python3 -m pytest .maika/tools/gate-check/tests/test_cli_index.py -v`
Expected: `test_load_index_includes_global_rules_*` FAIL (HP-1 bị loại — bug hiện tại); `test_cli_handoff_slice_strict_fail_wrong_type` và `test_cli_implementation_context_strict_fail_nonexistent` FAIL (rc==0 vì flag bị bỏ qua); `test_cli_empty_slice_*` FAIL (không có WARN). Các test legacy PASS.

- [x] **Step 3: Implement trong cli.py**

Sửa `_load_index_rule_ids` — thêm nhánh global (khớp context-loader.md dòng 46–48):

```python
def _load_index_rule_ids(index_path, artifact_type=None):
    data = yaml.safe_load(Path(index_path).read_text(encoding="utf-8")) or {}
    entries = data.get("entries") or []
    matched = []
    for entry in entries:
        applies = entry.get("applies_to") or []
        if artifact_type is None or artifact_type in applies or not applies:
            if entry.get("id"):
                matched.append(entry["id"])
    return set(matched), len(matched) == 0
```

Trong `main()`, thay block `if args.gate == "knowledge-checkpoint" and args.index:` ... `elif args.gate in {"ac-coverage", ...}` bằng:

```python
    kwargs = {}
    if args.gate == "knowledge-checkpoint" and args.index:
        valid_rule_ids, index_empty = _load_index_rule_ids(args.index, args.artifact_type)
        kwargs["valid_rule_ids"] = valid_rule_ids
        kwargs["allow_no_knowledge"] = index_empty
    elif args.gate in {"handoff-slice", "implementation-context"} and args.index:
        valid_rule_ids, slice_empty = _load_index_rule_ids(args.index, args.artifact_type)
        if slice_empty:
            print(f"WARN — slice empty for artifact_type={args.artifact_type} — falling back to legacy check")
        else:
            if args.artifact_type is None:
                print("WARN — --index without --artifact-type: checking rule-id existence only")
            kwargs["valid_rule_ids"] = valid_rule_ids
    elif args.gate in {"ac-coverage", "integration-coverage"}:
        if not args.against:
            print("FAIL — --against is required for coverage checks")
            return 2
        kwargs["spec_text"] = Path(args.against).read_text(encoding="utf-8")
```

- [x] **Step 4: Chạy tests, verify pass**

Run: `/usr/bin/python3 -m pytest .maika/tools/gate-check/tests/test_cli_index.py .maika/tools/gate-check/tests/test_gates.py -v`
Expected: ALL PASS.

- [x] **Step 5: Commit**

```bash
git add .maika/tools/gate-check/cli.py .maika/tools/gate-check/tests/test_cli_index.py
git commit -m "feat(gate-check): wire --index/--artifact-type into handoff-slice and implementation-context; include global rules in slice"
```

---

### Task 3: Prose wiring — decision-gate.md + rules-tool.md

**Files:**
- Modify: `.maika/procedures/decision-gate.md` (dòng 9–11 và dòng 30–31)
- Modify: `.maika/rules/rules-tool.md` (dòng 165, 170)

(Không sửa `tools/microloop-orchestrator/README.md` — file này không chứa lệnh gọi gate nào; chỗ gọi của microloop dispatch chính là R-Tool-8 trong rules-tool.md.)

- [x] **Step 1: Sửa decision-gate.md**

Thay step 4 (dòng 9–11):

```markdown
4. Precondition kiểm checkpoint bằng `gate-check`:
   `python3 {{ platform.framework_root }}/tools/gate-check/cli.py <gate> <file>`
   Với `knowledge-checkpoint` / `handoff-slice` / `implementation-context`, truyền thêm
   `--index {{ platform.framework_root }}/knowledge/long-term/knowledge-index.yaml --artifact-type <type do R-Guard-2 detect>`
   để gate check rule-id đúng slice (tồn tại + đúng type hoặc global). Thiếu `--index` → check legacy.
   exit≠0 → on_fail (ABORT/degrade).
```

Trong section "Token bằng chứng BẮT BUỘC", cập nhật 2 bullet (dòng 30–31 cũ):

```markdown
- **handoff-slice:** section `## Applicable DNA/Conventions` không rỗng, chứa ≥1 rule-id dạng `XX-n`.
  Khi chạy với `--index`/`--artifact-type`: MỌI rule-id trong section phải thuộc slice
  (tồn tại trong knowledge-index và `applies_to` khớp artifact-type hoặc rỗng/global) — id lạ → FAIL.
  Slice rỗng cho artifact-type đó → tool WARN và fallback check legacy.
- **implementation-context:** `## Applicable DNA/Conventions` chứa ≥1 rule-id (strict theo slice
  khi có `--index`/`--artifact-type`, như handoff-slice), `## Evidence`
  chứa UA evidence (`domain_overview`, `domain_flow`, `domain_relationships`) hoặc dòng
  explicit UA degrade/override, và `## Allowed Files` không rỗng. Write-gate còn kiểm
  target file đang sửa phải khớp một dòng trong `Allowed Files`.
```

- [x] **Step 2: Sửa rules-tool.md (R-Tool-8)**

Dòng 165, thay:

```markdown
`python3 {{ platform.framework_root }}/tools/gate-check/cli.py handoff-slice <file> --index {{ platform.framework_root }}/knowledge/long-term/knowledge-index.yaml --artifact-type <artifact-type của node>`
```

Dòng 170, thay:

```markdown
`python3 {{ platform.framework_root }}/tools/gate-check/cli.py implementation-context <file> --index {{ platform.framework_root }}/knowledge/long-term/knowledge-index.yaml --artifact-type <artifact-type của node>`
```

Ngay sau dòng 170 (trước đoạn "Implementation context phải có `## Evidence`..."), thêm:

```markdown
Với `--index`/`--artifact-type`, mọi rule-id trong `## Applicable DNA/Conventions` phải thuộc
slice của artifact-type đó (hoặc global) — rule-id bịa hoặc sai type → gate FAIL.
```

- [x] **Step 3: Chạy toàn bộ test suite framework, verify không vỡ gì**

Run: `/usr/bin/python3 -m pytest .maika/tools/gate-check/tests/ -v`
Expected: ALL PASS.

Run: `/usr/bin/python3 -m pytest .maika/hooks/write-gate/tests/ -v`
Expected: ALL PASS (write_gate.py gọi `validate_implementation_context(text)` không kwarg — signature backward compatible nên không đổi gì).

- [x] **Step 4: Commit**

```bash
git add .maika/procedures/decision-gate.md .maika/rules/rules-tool.md
git commit -m "docs(gate-check): wire --index/--artifact-type into decision-gate and R-Tool-8 invocations"
```

---

### Task 4: Verify DoD + full suite

- [x] **Step 1: Chạy full test của repo (framework tools + cli)**

Run: `/usr/bin/python3 -m pytest .maika/tools/gate-check/tests/ .maika/hooks/write-gate/tests/ cli/ -q`
Expected: ALL PASS, không regression.

- [x] **Step 2: Smoke test CLI bằng tay trên fixture thật**

```bash
cd /tmp && mkdir -p gate-smoke && cd gate-smoke
printf 'entries:\n  - id: SP-6\n    applies_to: [java-service]\n  - id: RC-2\n    applies_to: [react-component]\n' > idx.yaml
printf '## Applicable DNA/Conventions\n- RC-2\n## Allowed Files\n- src/App.java\n' > handoff.md
/usr/bin/python3 /home/zane/Desktop/agent-memory-arch-v3/.maika/tools/gate-check/cli.py handoff-slice handoff.md --index idx.yaml --artifact-type java-service
```

Expected: `FAIL — handoff cites rule-ids not in knowledge-index slice: RC-2`, exit code 1.

- [x] **Step 3: Đối chiếu DoD trong spec — tick từng dòng**

- `implementation-context` + `handoff-slice` support `--index`/`--artifact-type` ✓ (Task 2)
- Strict-in-section; legacy mode không đổi ✓ (Task 1, 2)
- `_load_index_rule_ids` include global rules ✓ (Task 2)
- Unit tests pass ✓ (Task 1–3)
- decision-gate.md + R-Tool-8 gọi gate kèm artifact_type ✓ (Task 3)
- KHÔNG đụng dashboard/token-budget/stale-hash/write_gate.py ✓ (kiểm bằng `git diff main --stat`)
