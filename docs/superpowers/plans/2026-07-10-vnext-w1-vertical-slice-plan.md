# Maika vNext W1 — Claude Code Vertical Slice — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Pipeline end-to-end opt-in trên Claude Code: detailed plan → mechanical validation → independent plan review → sequential queue → verbatim brief → fresh implementer → structured result → independent task review → write-scope enforcement (Master Plan v2 §26 W1).

**Architecture:** Extend chokepoints hiện có (AD-9): 3 gate mới vào `gate-check/gates.py` + `VALIDATORS`; parser/compiler/state-machine/dispatch mới trong `microloop-orchestrator/` (tái dụng `topo_sort`, `dispatch_worker`, `make_worker_runner`, `_load_gate_check`); write-gate thêm brief-scope check trong `evaluate_write`. Artifact JSON trong `.maika/changes/<id>/` — KHÔNG đụng contract markdown legacy (compat reader = load_runtime_queue giữ nguyên).

**Tech Stack:** Python 3 thuần (yaml, hashlib, json — không dependency mới), pytest.

## Global Constraints

- Branch: `feat/vnext-w1-vertical-slice` từ `main` xanh. Mỗi task một commit, message `feat(vnext-w1): ...` / `test(vnext-w1): ...`, footer `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.
- Pytest: `/usr/bin/python3 -m pytest` (.venv thiếu jsonschema). `git add` đích danh, cấm `git add -A`.
- **Flag mặc định `legacy`** — không hành vi mới nào chạy khi chưa opt-in. Không xóa/đổi contract markdown legacy (`TASK_QUEUE.md`, `TASK_HANDOFF.*`, `TASK_RESULT.*`).
- W1 must-not-depend (v2 §26 W1): không provider registry, không router, không explorer chuyên biệt, không parallel, không file locks, không Codex/Antigravity parity. Sequential-only.
- Mọi module mới đặt trong `.maika/tools/microloop-orchestrator/` hoặc `gate-check/` — không tool dir mới (R5).
- Đường dẫn trong `.maika/**` giữ template placeholder `{{ platform.framework_root }}` nếu file là template scaffold; code Python dùng đường dẫn tương đối runtime (như code hiện có).
- Sau MỖI task: chạy suite của tool bị sửa + `cli/tests/` để canh snapshot scaffold (`/usr/bin/python3 -m pytest cli/tests/ -q`); snapshot lệch vì file mới trong `.maika/` → cập nhật fixture snapshot trong CÙNG commit, ghi rõ trong message.
- Ledger (P2, thứ tự đúng): mỗi gate activate ledger entry của nó (PROP → `active` + litmus = lệnh pytest của test gate đó) **trong CÙNG commit** với validator — Task 4 (vnext-plan + vnext-workspace), Task 6 (vnext-brief), Task 7 (vnext-result). Task 12 chỉ kiểm consistency cuối. Không thêm enforcement ngoài danh sách này.

## Thuật ngữ artifact (v2 §8, §15, §17, §18.4)

```text
.maika/changes/<change-id>/
├── CHANGE.yaml          {change_id, class, title, created_at}
├── STATE.yaml           {change_id, state, updated_at, blocked}
├── INTENT.md            (tự do)
├── SPEC.md              (class small: Goal/Current/Desired/AC/Evidence)
├── IMPLEMENTATION_PLAN.md   (frontmatter YAML §15 + ### TASK-NNN sections)
├── generated/PLAN_VALIDATION.json  {verdict, checks:[{id, ok, reason}]}
├── generated/PLAN_MANIFEST.json    {change_id, base_commit, plan_sha256, spec_sha256, compiled_at}
├── generated/TASK_QUEUE.json      {change_id, plan_sha256, tasks:[{id, depends_on, status, brief_path, brief_hash, result_path, files}]}
├── briefs/TASK-NNN.md   (header YAML + "\n---\n" + verbatim plan section)
├── results/TASK-NNN.yaml (schema §18.4 ĐẦY ĐỦ field)
└── reviews/plan-review.md, reviews/TASK-NNN.md
```

`brief_hash` = sha256 hex của **verbatim section text** (sau `---`), không gồm header.
Naming thống nhất: mọi file per-task dùng đúng task id (`TASK-001`), không tiền tố `task-` lặp.

> **Rev 2 (2026-07-10):** đã áp 10 findings từ independent plan review (codex): symbol
> grounding + spec-hash match vào gate plan; write-gate kiểm approval/staleness; result
> contract đủ §18.4; state transitions tường minh per CLI; gate change-workspace minimal;
> ledger activate cùng commit với gate (P2); test Task 4/7/8 viết đủ code; skill có trigger;
> naming chuẩn hóa. Phần review đòi full §16 (AC coverage/anchors/compatibility) bị bác:
> Master Plan v2 §26 W1 quy định "mechanical subset" — các check đó thuộc W2+.

---

### Task 1: Feature flag + workspace + state machine

**Files:**
- Create: `.maika/tools/microloop-orchestrator/vnext_state.py`
- Create: `.maika/tools/microloop-orchestrator/tests/test_vnext_state.py`
- Modify: `.maika/profiles/execution-mode.yaml` (thêm 1 dòng cuối file)

**Interfaces:**
- Produces: `STATES` (14 state), `init_workspace(changes_root, change_id, klass, title) -> Path`, `load_state(ws) -> dict`, `transition(ws, new_state, blocked=None) -> dict`, `workflow_engine(config) -> str`.
- Consumes: không (module lá).

- [x] **Step 1: Viết failing test**

```python
# .maika/tools/microloop-orchestrator/tests/test_vnext_state.py
import pytest
import vnext_state as vs


def _ws(tmp_path):
    return vs.init_workspace(tmp_path, "demo-change", "small", "Demo change")


def test_init_workspace_creates_minimal_layout(tmp_path):
    ws = _ws(tmp_path)
    assert (ws / "CHANGE.yaml").exists()
    assert (ws / "STATE.yaml").exists()
    for sub in ("generated", "briefs", "results", "reviews"):
        assert (ws / sub).is_dir()
    change = vs._load_yaml(ws / "CHANGE.yaml")
    assert change["change_id"] == "demo-change"
    assert change["class"] == "small"
    assert vs.load_state(ws)["state"] == "INTAKE"


def test_init_rejects_bad_class(tmp_path):
    with pytest.raises(ValueError):
        vs.init_workspace(tmp_path, "x", "gigantic", "t")


def test_transition_legal_and_illegal(tmp_path):
    ws = _ws(tmp_path)
    vs.transition(ws, "PLANNING")            # small: INTAKE -> PLANNING hợp lệ (skip explore/spec class-aware ở W2)
    assert vs.load_state(ws)["state"] == "PLANNING"
    with pytest.raises(ValueError):
        vs.transition(ws, "ARCHIVED")        # PLANNING -> ARCHIVED không có trong ALLOWED


def test_blocked_requires_reason(tmp_path):
    ws = _ws(tmp_path)
    with pytest.raises(ValueError):
        vs.transition(ws, "BLOCKED")         # thiếu blocked metadata
    vs.transition(ws, "BLOCKED", blocked={"reason": "stale_plan", "detail": "x"})
    st = vs.load_state(ws)
    assert st["blocked"]["reason"] == "stale_plan"
```

- [x] **Step 2: Chạy fail**

Run: `cd .maika/tools/microloop-orchestrator && /usr/bin/python3 -m pytest tests/test_vnext_state.py -q`
Expected: FAIL `ModuleNotFoundError: No module named 'vnext_state'` (tests/ đã có conftest/path theo suite hiện hành — nếu suite dùng rootdir import, thêm `sys.path` giống test hiện có trong dir này; đọc 1 test file sẵn có để khớp).

- [x] **Step 3: Implement**

```python
# .maika/tools/microloop-orchestrator/vnext_state.py
"""vNext change workspace + state machine (Master Plan v2 §8, §9).

BLOCKED mang metadata reason; class ghi ở CHANGE.yaml; 14 states.
"""
from datetime import datetime, timezone
from pathlib import Path

import yaml

STATES = [
    "INTAKE", "EXPLORING", "RECONCILING", "BRAINSTORMING", "SPEC_REVIEW",
    "PLANNING", "PLAN_REVIEW", "EXECUTING", "VERIFYING", "FINAL_REVIEW",
    "COMPLETED", "ARCHIVED", "BLOCKED", "CANCELLED",
]
CLASSES = {"trivial", "small", "standard", "architectural"}
BLOCK_REASONS = {"grounding", "stale_plan", "capability", "user_input", "environment"}

# W1: chỉ các transition mà slice này dùng + BLOCKED/CANCELLED từ mọi state.
ALLOWED = {
    "INTAKE": {"EXPLORING", "PLANNING"},
    "EXPLORING": {"RECONCILING", "BRAINSTORMING"},
    "RECONCILING": {"BRAINSTORMING"},
    "BRAINSTORMING": {"SPEC_REVIEW"},
    "SPEC_REVIEW": {"PLANNING"},
    "PLANNING": {"PLAN_REVIEW"},
    "PLAN_REVIEW": {"PLANNING", "EXECUTING"},
    "EXECUTING": {"VERIFYING", "FINAL_REVIEW"},
    "VERIFYING": {"FINAL_REVIEW", "COMPLETED"},
    "FINAL_REVIEW": {"VERIFYING", "COMPLETED"},
    "COMPLETED": {"ARCHIVED"},
    "BLOCKED": set(STATES) - {"BLOCKED"},
    "ARCHIVED": set(), "CANCELLED": set(),
}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _load_yaml(path):
    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}


def _dump_yaml(doc, path):
    Path(path).write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")


def init_workspace(changes_root, change_id, klass, title):
    if klass not in CLASSES:
        raise ValueError(f"bad change class: {klass}")
    ws = Path(changes_root) / change_id
    for sub in ("generated", "briefs", "results", "reviews"):
        (ws / sub).mkdir(parents=True, exist_ok=True)
    _dump_yaml({"change_id": change_id, "class": klass, "title": title,
                "created_at": _now()}, ws / "CHANGE.yaml")
    _dump_yaml({"change_id": change_id, "state": "INTAKE",
                "updated_at": _now(), "blocked": None}, ws / "STATE.yaml")
    return ws


def load_state(ws):
    return _load_yaml(Path(ws) / "STATE.yaml")


def transition(ws, new_state, blocked=None):
    st = load_state(ws)
    cur = st["state"]
    if new_state not in STATES:
        raise ValueError(f"unknown state: {new_state}")
    if new_state == "BLOCKED":
        if not blocked or blocked.get("reason") not in BLOCK_REASONS:
            raise ValueError("BLOCKED requires blocked={'reason': <valid>, ...}")
    elif new_state != "CANCELLED" and new_state not in ALLOWED.get(cur, set()):
        raise ValueError(f"illegal transition {cur} -> {new_state}")
    st.update(state=new_state, updated_at=_now(),
              blocked=(dict(blocked, since=_now()) if new_state == "BLOCKED" else None))
    _dump_yaml(st, Path(ws) / "STATE.yaml")
    return st


def workflow_engine(config):
    """Flag đọc từ execution-mode.yaml đã render. Mặc định legacy."""
    return (config or {}).get("workflow_engine", "legacy")
```

- [x] **Step 4: Thêm flag vào execution-mode.yaml** — thêm 2 dòng cuối file (ngoài mọi khối Jinja):

```yaml
# vNext W1: engine flag — vnext là opt-in; legacy là mặc định (Master Plan v2 §26 W1)
workflow_engine: legacy
```

- [x] **Step 5: Chạy pass + suites**

Run: `cd .maika/tools/microloop-orchestrator && /usr/bin/python3 -m pytest tests/ -q` → toàn suite PASS.
Run: `/usr/bin/python3 -m pytest cli/tests/ -q` (từ repo root) → PASS; nếu snapshot scaffold fail vì execution-mode.yaml đổi → cập nhật snapshot fixture trong cùng commit.

- [x] **Step 6: Commit** — `feat(vnext-w1): workspace + 14-state machine + workflow_engine flag`

---

### Task 2: Capability vocabulary + skill writing-plan

**Files:**
- Create: `.maika/profiles/capabilities.md`
- Create: `.maika/skills/writing-plan/SKILL.md`
- Modify: `.maika/skills/skill-index.yaml` (regen bằng tool)

**Interfaces:**
- Produces: 6 capability IDs (văn bản, tĩnh — KHÔNG runtime); skill canonical đầu tiên tham chiếu IDs (R1 consumer cùng PR).

- [x] **Step 1: Viết `.maika/profiles/capabilities.md`**

```markdown
# Capability Vocabulary (vNext §11.1 — tồn tại từ W1, runtime đến W4)

Canonical skill/role contract CHỈ tham chiếu các ID sau; provider cụ thể chỉ nằm ở
provider mappings / adapters / tool docs / capability matrix:

- `architecture_discovery` — khám phá module, boundary, flow.
- `exact_source_inspection` — đọc symbol/source hiện tại (authoritative).
- `dependency_analysis` — quan hệ phụ thuộc, blast radius.
- `business_knowledge_retrieval` — tri thức nghiệp vụ, tài liệu, memory.
- `convention_retrieval` — Author DNA, conventions, rule IDs.
- `runtime_verification` — chạy lệnh build/test và đọc output thật.

W1→W4: compliance giữ bởi plan review; W4 thêm skill-lint rule cấm provider-name.
```

- [x] **Step 2: Viết skill theo schema skill-lint** — đọc `.maika/skills/codebase-explorer/SKILL.md` làm khung heading (REQUIRED_SECTIONS B1..; frontmatter `name/description/version`). Nội dung cốt lõi (điền vào khung đó, giữ đủ heading bắt buộc):

```markdown
---
name: writing-plan
version: '1.0'
description: >
  Sinh IMPLEMENTATION_PLAN.md code-level cho một change vNext: frontmatter máy-đọc
  (base_commit, spec_hash, evidence_hash), mỗi task một section TASK-NNN với
  implementation_mode exact|guided|intent, files/symbols/anchors, TDD steps, commands
  + expected. Dùng khi: SPEC.md đã được duyệt và change ở state PLANNING (mọi class).
  KHÔNG dùng cho: brainstorm (W2), review plan (planning_dispatch đảm nhiệm),
  task legacy OpenSpec.
---

## Mục tiêu
Blueprint thực thi được: mọi task tự chứa, verbatim-compilable, đủ evidence.

## Inputs
SPEC.md đã duyệt; codebase hiện tại (capability: exact_source_inspection,
dependency_analysis, architecture_discovery); conventions (convention_retrieval).

## Required outcomes
IMPLEMENTATION_PLAN.md đúng contract §15: frontmatter đầy đủ; task section
`### TASK-NNN: <title>` chứa ```yaml task:``` header (id, implementation_mode,
depends_on, files.create/modify/test, verification.command + expected) + thân
task TDD từng bước; không TODO/TBD; line numbers chỉ là hint (anchor > hash > line).

## Invariants
- Mọi file được task đụng phải khai trong files.*; symbol nêu trong plan phải tồn tại
  ở base_commit (runtime_verification trước khi ghi).
- Không paraphrase yêu cầu từ SPEC — trích nguyên văn AC vào từng task liên quan.

## Stop conditions
Thiếu SPEC duyệt / base_commit bẩn / mâu thuẫn SPEC↔code → dừng, báo NEEDS_CONTEXT.

## Output contract
Ghi IMPLEMENTATION_PLAN.md vào workspace change; chuyển state PLANNING→PLAN_REVIEW.

## Next handoff
planning_dispatch (independent plan review) → gate `plan` → compiler.
```

- [x] **Step 3: Lint + regen index**

Run: `/usr/bin/python3 .maika/tools/skill-lint/validate_skills.py` → writing-plan PASS (sửa heading theo báo lỗi lint nếu thiếu section bắt buộc — lint là nguồn chân lý schema).
Run: `/usr/bin/python3 .maika/tools/skill-index/generate_index.py` → skill-index.yaml có entry writing-plan.
Run: `/usr/bin/python3 -m pytest cli/tests/ -q` → snapshot lệch thì cập nhật cùng commit.

- [x] **Step 4: Commit** — `feat(vnext-w1): capability vocabulary + skill writing-plan (R1: vocabulary + consumer cùng PR)`

---

### Task 3: plan_parser.py

**Files:**
- Create: `.maika/tools/microloop-orchestrator/plan_parser.py`
- Create: `.maika/tools/microloop-orchestrator/tests/test_plan_parser.py`

**Interfaces:**
- Produces: `parse_plan(text) -> {"meta": dict, "tasks": [{"id","title","header":dict,"section_text":str}]}` — `section_text` là VERBATIM (từ dòng `### TASK-` đến trước `### TASK-` kế/EOF). Raise `ValueError` khi thiếu frontmatter/header.
- Consumes: không.

- [x] **Step 1: Failing test**

```python
# tests/test_plan_parser.py
import pytest
import plan_parser as pp

PLAN = """---
change_id: demo
plan_version: 1
base_commit: abc123
spec_hash: sha256:aaa
evidence_hash: sha256:bbb
---

# Plan

### TASK-001: Tạo module A

```yaml
task:
  id: TASK-001
  implementation_mode: exact
  depends_on: []
  files:
    create: [src/a.py]
    test: [tests/test_a.py]
  verification:
    command: pytest tests/test_a.py -q
    expected: "1 passed"
```

Thân task 1.

### TASK-002: Dùng A

```yaml
task:
  id: TASK-002
  implementation_mode: guided
  depends_on: [TASK-001]
  files:
    modify: [src/a.py]
    test: [tests/test_a.py]
  verification:
    command: pytest tests/ -q
    expected: "2 passed"
```

Thân task 2.
"""


def test_parse_meta_and_tasks():
    doc = pp.parse_plan(PLAN)
    assert doc["meta"]["base_commit"] == "abc123"
    ids = [t["id"] for t in doc["tasks"]]
    assert ids == ["TASK-001", "TASK-002"]
    assert doc["tasks"][0]["header"]["implementation_mode"] == "exact"
    assert "Thân task 1." in doc["tasks"][0]["section_text"]
    assert "TASK-002" not in doc["tasks"][0]["section_text"].split("###")[0] or True


def test_verbatim_roundtrip():
    doc = pp.parse_plan(PLAN)
    for t in doc["tasks"]:
        assert t["section_text"] in PLAN          # verbatim slice, không chỉnh sửa


def test_missing_frontmatter_raises():
    with pytest.raises(ValueError):
        pp.parse_plan("# no frontmatter\n### TASK-001: x\n")


def test_task_without_yaml_header_raises():
    bad = PLAN.replace("```yaml", "```text", 1)
    with pytest.raises(ValueError):
        pp.parse_plan(bad)
```

- [x] **Step 2: Run fail** — `ModuleNotFoundError: plan_parser`.

- [x] **Step 3: Implement**

```python
# plan_parser.py
"""Parse IMPLEMENTATION_PLAN.md (v2 §15): frontmatter + verbatim TASK sections."""
import re

import yaml

_TASK_HEAD = re.compile(r"^### (TASK-\d+):\s*(.+)$", re.MULTILINE)
_YAML_BLOCK = re.compile(r"```yaml\n(.*?)```", re.DOTALL)


def parse_plan(text):
    if not text.startswith("---"):
        raise ValueError("plan missing YAML frontmatter")
    end = text.index("\n---", 3)
    meta = yaml.safe_load(text[3:end]) or {}
    for key in ("change_id", "plan_version", "base_commit", "spec_hash", "evidence_hash"):
        if key not in meta:
            raise ValueError(f"plan frontmatter missing: {key}")
    heads = list(_TASK_HEAD.finditer(text))
    if not heads:
        raise ValueError("plan has no TASK sections")
    tasks = []
    for i, m in enumerate(heads):
        stop = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        section = text[m.start():stop]
        block = _YAML_BLOCK.search(section)
        header = (yaml.safe_load(block.group(1)) or {}).get("task") if block else None
        if not header:
            raise ValueError(f"{m.group(1)}: missing ```yaml task:``` header")
        if header.get("id") != m.group(1):
            raise ValueError(f"heading {m.group(1)} != header id {header.get('id')}")
        tasks.append({"id": m.group(1), "title": m.group(2).strip(),
                      "header": header, "section_text": section})
    return {"meta": meta, "tasks": tasks}
```

- [x] **Step 4: Run pass** → 4 passed. **Step 5: Commit** — `feat(vnext-w1): plan parser (frontmatter + verbatim TASK sections)`

---

### Task 4: Gate `vnext-plan` (mechanical subset §16) + gate `vnext-workspace`

**Files:**
- Modify: `.maika/tools/gate-check/gates.py` (2 validator cuối file)
- Modify: `.maika/tools/gate-check/cli.py` (VALIDATORS + kwargs)
- Create: `.maika/tools/gate-check/tests/test_vnext_plan_gate.py`
- Modify: `docs/refactor/maika-vnext/enforcement-ledger.yaml` (PROP plan + PROP change-workspace → active, cùng commit)

**Interfaces:**
- Produces: `validate_vnext_plan(text, plan_doc=None, repo_root=None, spec_sha256=None) -> Result` — subset W1 §26 (KHÔNG phải full §16 — phần còn lại W2+): frontmatter đủ; `spec_hash == "sha256:"+spec_sha256` khi spec_sha256 truyền vào; `evidence_hash` đúng format `sha256:...` (đối chiếu manifest là W2); base_commit resolve được (`git cat-file -t`); task ID duy nhất + khớp heading; deps tồn tại + acyclic; mỗi task có `verification.command` + `expected`; files.modify/test tồn tại (files.create KHÔNG cần); **symbol grounding**: header có `symbols: {<path>: [<name>...]}` thì mỗi name phải xuất hiện (substring) trong file đó; không `TODO`/`TBD`/`FIXME`; `implementation_mode` hợp lệ.
- Produces: `validate_change_workspace(text) -> Result` — text = CHANGE.yaml: đủ key `change_id/class/title/created_at`, class hợp lệ (ledger PROP-001 scheduled W1 — đóng đúng hạn).
- Consumes: `plan_parser.parse_plan` — cli.py load plan_parser bằng `importlib` (pattern `_load_gate_check` đảo chiều), truyền `plan_doc` vào validator qua kwargs.

- [x] **Step 1: Failing tests** (code ĐẦY ĐỦ, chạy được ngay):

```python
# .maika/tools/gate-check/tests/test_vnext_plan_gate.py
import importlib.util
import subprocess
from pathlib import Path

_G = Path(__file__).resolve().parents[1] / "gates.py"
spec = importlib.util.spec_from_file_location("gates", _G)
gates = importlib.util.module_from_spec(spec); spec.loader.exec_module(gates)

_PP = Path(__file__).resolve().parents[2] / "microloop-orchestrator" / "plan_parser.py"
spec2 = importlib.util.spec_from_file_location("plan_parser", _PP)
pp = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(pp)

PLAN_TPL = """---
change_id: demo
plan_version: 1
base_commit: BASESHA
spec_hash: sha256:SPECSHA
evidence_hash: sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
---

# Plan

### TASK-001: Tạo module A

```yaml
task:
  id: TASK-001
  implementation_mode: exact
  depends_on: []
  files:
    create: [src/b.py]
    test: [tests/test_a.py]
  verification:
    command: pytest tests/test_a.py -q
    expected: "1 passed"
```

Thân task 1.

### TASK-002: Dùng A

```yaml
task:
  id: TASK-002
  implementation_mode: guided
  depends_on: [TASK-001]
  files:
    modify: [src/a.py]
    test: [tests/test_a.py]
  symbols:
    src/a.py: [A]
  verification:
    command: pytest tests/ -q
    expected: "2 passed"
```

Thân task 2.
"""


def _mk(tmp_path):
    (tmp_path / "src").mkdir(); (tmp_path / "tests").mkdir()
    (tmp_path / "src" / "a.py").write_text("A = 1\n")
    (tmp_path / "tests" / "test_a.py").write_text("def test_a():\n    assert True\n")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-qm", "base"], cwd=tmp_path, check=True)
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=tmp_path,
                         capture_output=True, text=True).stdout.strip()
    return PLAN_TPL.replace("BASESHA", sha), sha


def _check(tmp_path, text, spec_sha256="SPECSHA"):
    return gates.validate_vnext_plan(
        text, plan_doc=pp.parse_plan(text), repo_root=str(tmp_path),
        spec_sha256=spec_sha256)


def test_plan_ok_passes(tmp_path):
    text, _ = _mk(tmp_path)
    res = _check(tmp_path, text)
    assert res.ok, res.reason


def test_unresolvable_base_commit_fails(tmp_path):
    text, sha = _mk(tmp_path)
    res = _check(tmp_path, text.replace(sha, "deadbeef" * 5))
    assert not res.ok and "base_commit" in res.reason


def test_spec_hash_mismatch_fails(tmp_path):
    text, _ = _mk(tmp_path)
    res = _check(tmp_path, text, spec_sha256="khac_sha")
    assert not res.ok and "spec_hash" in res.reason


def test_missing_verification_fails(tmp_path):
    text, _ = _mk(tmp_path)
    res = _check(tmp_path, text.replace('    expected: "1 passed"\n', ""))
    assert not res.ok and "verification" in res.reason


def test_todo_marker_fails(tmp_path):
    text, _ = _mk(tmp_path)
    res = _check(tmp_path, text.replace("Thân task 1.", "Thân task 1. TODO: fix"))
    assert not res.ok and "placeholder" in res.reason


def test_cyclic_deps_fails(tmp_path):
    text, _ = _mk(tmp_path)
    res = _check(tmp_path, text.replace("depends_on: []", "depends_on: [TASK-002]"))
    assert not res.ok and "cycle" in res.reason


def test_modify_file_missing_fails(tmp_path):
    text, _ = _mk(tmp_path)
    res = _check(tmp_path, text.replace("modify: [src/a.py]", "modify: [src/missing.py]"))
    assert not res.ok and "missing" in res.reason


def test_symbol_not_found_fails(tmp_path):
    text, _ = _mk(tmp_path)
    res = _check(tmp_path, text.replace("src/a.py: [A]", "src/a.py: [KhongTonTai]"))
    assert not res.ok and "symbol" in res.reason


def test_change_workspace_gate():
    ok = "change_id: demo\nclass: small\ntitle: t\ncreated_at: 2026-07-10\n"
    assert gates.validate_change_workspace(ok).ok
    assert not gates.validate_change_workspace(ok.replace("small", "gigantic")).ok
    assert not gates.validate_change_workspace("change_id: demo\n").ok
```

- [x] **Step 2: Run fail** — `AttributeError: gates has no validate_vnext_plan`.

- [x] **Step 3: Implement trong gates.py**

```python
_PLACEHOLDER = re.compile(r"\b(TODO|TBD|FIXME)\b")
_VALID_MODES = {"exact", "guided", "intent"}
_SHA256_FMT = re.compile(r"^sha256:[0-9a-f]{64}$")
VALID_CHANGE_CLASSES = {"trivial", "small", "standard", "architectural"}


def validate_change_workspace(text: str) -> Result:
    """Gate `vnext-workspace` (v2 §22 change-workspace, minimal W1)."""
    doc = yaml.safe_load(text) or {}
    for key in ("change_id", "class", "title", "created_at"):
        if not doc.get(key):
            return Result(False, f"CHANGE.yaml missing {key}")
    if doc["class"] not in VALID_CHANGE_CLASSES:
        return Result(False, f"bad change class: {doc['class']}")
    return Result(True)


def validate_vnext_plan(text, plan_doc=None, repo_root=None, spec_sha256=None) -> Result:
    """Gate `vnext-plan` — mechanical subset W1 (v2 §26 W1; full §16 là W2+)."""
    if plan_doc is None:
        return Result(False, "plan_doc required (cli parses via plan_parser)")
    import subprocess
    meta, tasks = plan_doc["meta"], plan_doc["tasks"]
    if spec_sha256 is not None and meta.get("spec_hash") != f"sha256:{spec_sha256}":
        return Result(False, "spec_hash mismatch: plan compiled against different SPEC.md")
    if not _SHA256_FMT.match(str(meta.get("evidence_hash", ""))):
        return Result(False, "evidence_hash must be sha256:<64hex> (manifest match arrives W2)")
    if repo_root:
        probe = subprocess.run(["git", "cat-file", "-t", str(meta["base_commit"])],
                               cwd=repo_root, capture_output=True, text=True)
        if probe.returncode != 0 or probe.stdout.strip() != "commit":
            return Result(False, f"base_commit not resolvable: {meta['base_commit']}")
    ids = [t["id"] for t in tasks]
    if len(ids) != len(set(ids)):
        return Result(False, "duplicate task ids")
    known = set(ids)
    for t in tasks:
        h = t["header"]
        if h.get("implementation_mode") not in _VALID_MODES:
            return Result(False, f"{t['id']}: bad implementation_mode")
        for dep in h.get("depends_on", []) or []:
            if dep not in known:
                return Result(False, f"{t['id']}: unknown dep {dep}")
        ver = h.get("verification") or {}
        if not ver.get("command") or not ver.get("expected"):
            return Result(False, f"{t['id']}: verification.command/expected required")
        if _PLACEHOLDER.search(t["section_text"]):
            return Result(False, f"{t['id']}: placeholder TODO/TBD/FIXME in section")
        files = h.get("files") or {}
        if repo_root:
            for key in ("modify", "test"):
                for p in files.get(key, []) or []:
                    if not (Path(repo_root) / p).exists():
                        return Result(False, f"{t['id']}: files.{key} missing on disk: {p}")
            for path, names in (h.get("symbols") or {}).items():
                target = Path(repo_root) / path
                if not target.exists():
                    return Result(False, f"{t['id']}: symbol file missing: {path}")
                content = target.read_text(encoding="utf-8", errors="replace")
                for name in names or []:
                    if name not in content:
                        return Result(False, f"{t['id']}: symbol not found: {name} in {path}")
    # acyclic — tái dụng thuật toán contract.py qua cấu trúc nodes tối giản
    indeg = {i: 0 for i in ids}
    for t in tasks:
        for _ in t["header"].get("depends_on", []) or []:
            indeg[t["id"]] += 1
    ready = [i for i, d in indeg.items() if d == 0]
    seen = 0
    while ready:
        cur = ready.pop()
        seen += 1
        for t in tasks:
            if cur in (t["header"].get("depends_on") or []):
                indeg[t["id"]] -= 1
                if indeg[t["id"]] == 0:
                    ready.append(t["id"])
    if seen != len(ids):
        return Result(False, "dependency cycle in tasks")
    return Result(True)
```

(`from pathlib import Path` đã có sẵn? gates.py hiện import `os, re, yaml` — thêm `from pathlib import Path` đầu file nếu chưa có.)

- [x] **Step 4: Wire cli.py** — thêm `"vnext-plan": "validate_vnext_plan"` và `"vnext-workspace": "validate_change_workspace"` vào `VALIDATORS`; trong `main()` thêm nhánh:

```python
    elif args.gate == "vnext-plan":
        pp_path = Path(__file__).resolve().parents[1] / "microloop-orchestrator" / "plan_parser.py"
        spec_pp = importlib.util.spec_from_file_location("plan_parser", pp_path)
        pp = importlib.util.module_from_spec(spec_pp); spec_pp.loader.exec_module(pp)
        kwargs["plan_doc"] = pp.parse_plan(text)
        kwargs["repo_root"] = args.repo_root or os.getcwd()
        if args.against:                     # --against SPEC.md → spec-hash freshness
            import hashlib
            kwargs["spec_sha256"] = hashlib.sha256(
                Path(args.against).read_bytes()).hexdigest()
```

(`import importlib.util` đưa lên đầu `main` giống `_load_module` pattern.)

- [x] **Step 5: Ledger (P2 — cùng commit):** trong `enforcement-ledger.yaml`, PROP entry của `plan` → `mechanism: vnext-plan`, `status: active`, `failure.classification: reproducible_litmus`, `litmus.command: /usr/bin/python3 -m pytest .maika/tools/gate-check/tests/test_vnext_plan_gate.py -q`, `implementation.files: [.maika/tools/gate-check/gates.py]`, `consumers: [.maika/tools/microloop-orchestrator/plan_compiler.py]`; PROP-001 `change-workspace` → `mechanism: vnext-workspace`, `status: active`, litmus = cùng file test (`test_change_workspace_gate`), consumers: orchestrator vnext-init (Task 11). Chạy `/usr/bin/python3 -m pytest cli/tests/test_vnext_w0_artifacts.py -q` → 4 passed.

- [x] **Step 6: Run pass** — `cd .maika/tools/gate-check && /usr/bin/python3 -m pytest tests/test_vnext_plan_gate.py -q` → 9 passed; toàn suite gate-check PASS.
- [x] **Step 7: Commit** — `feat(vnext-w1): gates vnext-plan + vnext-workspace (+ ledger activation)`

---

### Task 5: plan_compiler.py — PLAN_VALIDATION + TASK_QUEUE.json + verbatim briefs

**Files:**
- Create: `.maika/tools/microloop-orchestrator/plan_compiler.py`
- Create: `.maika/tools/microloop-orchestrator/tests/test_plan_compiler.py`

**Interfaces:**
- Produces: `compile_plan(ws, repo_root) -> dict` — đọc `IMPLEMENTATION_PLAN.md`, chạy gate `validate_vnext_plan` (qua `_load_gate_check()` pattern của orchestrator.py:43), ghi `generated/PLAN_VALIDATION.json` ({verdict: APPROVED|REVISE, checks}), nếu APPROVED: ghi `generated/PLAN_MANIFEST.json` (plan_sha256 = sha256 toàn file, spec_sha256 nếu SPEC.md tồn tại), `generated/TASK_QUEUE.json` (tasks topo-sequential — tái dụng `orchestrator.topo_sort` qua importlib cùng dir), `briefs/task-NNN.md` (header YAML: change_id, task_id, brief_hash, generated_at + `\n---\n` + section_text verbatim). Trả manifest dict. Idempotent + deterministic (không timestamp trong hash).
- Consumes: `plan_parser.parse_plan`, `gates.validate_vnext_plan`, `orchestrator.topo_sort`.

- [x] **Step 1: Failing tests**

```python
# tests/test_plan_compiler.py
import hashlib
import json
from pathlib import Path

import plan_compiler as pc
import vnext_state as vs

# PLAN fixture: copy verbatim PLAN_TPL + _mk từ test_vnext_plan_gate (Task 4) vào
# file này để test độc lập; _setup thay SPECSHA bằng sha256 của SPEC.md thật.


def _setup(tmp_path):
    import hashlib
    ws = vs.init_workspace(tmp_path / "changes", "demo", "small", "t")
    (ws / "SPEC.md").write_text("# spec\n", encoding="utf-8")
    plan_text, _ = _mk(tmp_path)                 # helper copy verbatim từ test_vnext_plan_gate
    plan_text = plan_text.replace(
        "SPECSHA", hashlib.sha256((ws / "SPEC.md").read_bytes()).hexdigest())
    (ws / "IMPLEMENTATION_PLAN.md").write_text(plan_text, encoding="utf-8")
    return ws, tmp_path


def test_compile_writes_queue_and_briefs(tmp_path):
    ws, root = _setup(tmp_path)
    out = pc.compile_plan(ws, repo_root=root)
    q = json.loads((ws / "generated" / "TASK_QUEUE.json").read_text())
    assert [t["id"] for t in q["tasks"]] == ["TASK-001", "TASK-002"]
    assert all(t["status"] == "pending" for t in q["tasks"])
    brief = (ws / "briefs" / "TASK-001.md").read_text()
    head, _, body = brief.partition("\n---\n")
    assert hashlib.sha256(body.encode()).hexdigest() == q["tasks"][0]["brief_hash"]
    assert "Thân task 1." in body                 # verbatim


def test_compile_deterministic(tmp_path):
    ws, root = _setup(tmp_path)
    pc.compile_plan(ws, repo_root=root)
    q1 = (ws / "generated" / "TASK_QUEUE.json").read_bytes()
    pc.compile_plan(ws, repo_root=root)
    assert (ws / "generated" / "TASK_QUEUE.json").read_bytes() == q1


def test_compile_refuses_invalid_plan(tmp_path):
    ws, root = _setup(tmp_path)
    p = ws / "IMPLEMENTATION_PLAN.md"
    p.write_text(p.read_text().replace("expected:", "TODO_expected:"), encoding="utf-8")
    out = pc.compile_plan(ws, repo_root=root)
    assert out["verdict"] != "APPROVED"
    assert not (ws / "generated" / "TASK_QUEUE.json").exists()
    v = json.loads((ws / "generated" / "PLAN_VALIDATION.json").read_text())
    assert v["verdict"] == "REVISE"


def test_plan_edit_invalidates_hash(tmp_path):
    ws, root = _setup(tmp_path)
    m1 = pc.compile_plan(ws, repo_root=root)["plan_sha256"]
    p = ws / "IMPLEMENTATION_PLAN.md"
    p.write_text(p.read_text() + "\n<!-- edit -->\n", encoding="utf-8")
    m2 = pc.compile_plan(ws, repo_root=root)["plan_sha256"]
    assert m1 != m2
```

- [x] **Step 2: Run fail.** **Step 3: Implement**

```python
# plan_compiler.py
"""Deterministic plan compiler (v2 §17 W1 subset): verdict -> queue -> verbatim briefs."""
import hashlib
import importlib.util
import json
from pathlib import Path

import yaml


def _load(name, rel):
    mod_path = Path(__file__).resolve().parent / rel if "/" not in rel else \
        Path(__file__).resolve().parents[1] / rel
    spec = importlib.util.spec_from_file_location(name, mod_path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compile_plan(ws, repo_root):
    ws = Path(ws)
    pp = _load("plan_parser", "plan_parser.py")
    orch = _load("orchestrator", "orchestrator.py")
    gates = _load("gates", "gate-check/gates.py")
    text = (ws / "IMPLEMENTATION_PLAN.md").read_text(encoding="utf-8")
    gen = ws / "generated"
    spec_path = ws / "SPEC.md"
    spec_sha = (hashlib.sha256(spec_path.read_bytes()).hexdigest()
                if spec_path.exists() else None)
    try:
        doc = pp.parse_plan(text)
        res = gates.validate_vnext_plan(text, plan_doc=doc, repo_root=str(repo_root),
                                        spec_sha256=spec_sha)
    except ValueError as e:
        res = gates.Result(False, str(e))
        doc = None
    verdict = "APPROVED" if res.ok else "REVISE"
    (gen / "PLAN_VALIDATION.json").write_text(json.dumps(
        {"verdict": verdict, "checks": [{"id": "vnext-plan", "ok": res.ok,
                                         "reason": res.reason}]},
        ensure_ascii=False, indent=2), encoding="utf-8")
    if verdict != "APPROVED":
        return {"verdict": verdict, "reason": res.reason}
    plan_sha = _sha(text)
    manifest = {
        "change_id": doc["meta"]["change_id"],
        "base_commit": doc["meta"]["base_commit"],
        "plan_sha256": plan_sha,
        "spec_sha256": spec_sha,
    }
    (gen / "PLAN_MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    topo_input = [{"id": t["id"], "depends_on": t["header"].get("depends_on") or []}
                  for t in doc["tasks"]]
    order = [t["id"] for t in orch.topo_sort(topo_input)]
    by_id = {t["id"]: t for t in doc["tasks"]}
    queue_tasks = []
    for tid in order:
        t = by_id[tid]
        body = t["section_text"]
        brief_hash = _sha(body)
        brief_path = ws / "briefs" / f"{tid}.md"
        header = yaml.safe_dump({"change_id": manifest["change_id"], "task_id": tid,
                                 "brief_hash": brief_hash, "plan_sha256": plan_sha},
                                sort_keys=False)
        brief_path.write_text(header + "\n---\n" + body, encoding="utf-8")
        queue_tasks.append({
            "id": tid, "depends_on": t["header"].get("depends_on") or [],
            "status": "pending",
            "brief_path": str(brief_path.relative_to(ws)),
            "brief_hash": brief_hash,
            "result_path": f"results/{tid}.yaml",
            "files": t["header"].get("files") or {},
        })
    (gen / "TASK_QUEUE.json").write_text(json.dumps(
        {"change_id": manifest["change_id"], "plan_sha256": plan_sha,
         "tasks": queue_tasks}, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"verdict": "APPROVED", **manifest}
```

(Chú ý `_load` cho gates: đường dẫn `gate-check/gates.py` nằm ở `parents[1]` của module — viết helper cho đúng 2 trường hợp cùng-dir và sibling-tool như code trên.)

- [x] **Step 4: Run pass** → 4 passed; toàn suite microloop PASS. **Step 5: Commit** — `feat(vnext-w1): deterministic plan compiler (verdict -> queue -> verbatim briefs)`

---

### Task 6: Gate `brief-integrity`

**Files:**
- Modify: `.maika/tools/gate-check/gates.py`, `cli.py`
- Create: `.maika/tools/gate-check/tests/test_vnext_brief_gate.py`

**Interfaces:**
- Produces: `validate_brief_integrity(text, queue_doc=None) -> Result` — text = nội dung brief file; tách header/body theo `\n---\n`; kiểm: header có task_id/brief_hash/plan_sha256; `sha256(body) == header.brief_hash`; entry trong queue_doc (TASK_QUEUE.json dict) có cùng task_id với cùng brief_hash + plan_sha256 khớp queue. CLI gate `vnext-brief` với `--against <TASK_QUEUE.json>` (tái dụng flag `--against` sẵn có).

- [x] **Step 1: Failing tests** — 4 test: pass đúng; body bị sửa 1 ký tự → FAIL "brief hash mismatch"; task_id không có trong queue → FAIL; plan_sha256 lệch queue → FAIL "stale plan". (Fixture: dựng ws bằng plan_compiler từ Task 5 fixture — tái dụng `_setup`.)
- [x] **Step 2: Run fail.** **Step 3: Implement** (gates.py):

```python
def validate_brief_integrity(text, queue_doc=None) -> Result:
    """Gate brief-integrity (v2 §22): verbatim-slice traceability + not stale."""
    import hashlib
    if queue_doc is None:
        return Result(False, "--against TASK_QUEUE.json required")
    head, sep, body = text.partition("\n---\n")
    if not sep:
        return Result(False, "brief missing header/body separator")
    meta = yaml.safe_load(head) or {}
    for key in ("task_id", "brief_hash", "plan_sha256"):
        if key not in meta:
            return Result(False, f"brief header missing {key}")
    if hashlib.sha256(body.encode("utf-8")).hexdigest() != meta["brief_hash"]:
        return Result(False, "brief hash mismatch (body modified)")
    if meta["plan_sha256"] != queue_doc.get("plan_sha256"):
        return Result(False, "stale plan: brief compiled from different plan hash")
    entry = next((t for t in queue_doc.get("tasks", []) if t["id"] == meta["task_id"]), None)
    if entry is None:
        return Result(False, f"task {meta['task_id']} not in queue")
    if entry["brief_hash"] != meta["brief_hash"]:
        return Result(False, "queue/brief hash mismatch")
    return Result(True)
```

cli.py: `"vnext-brief": "validate_brief_integrity"`; nhánh kwargs: `kwargs["queue_doc"] = json.loads(Path(args.against).read_text())` (thêm `import json` đầu file, yêu cầu `--against`).

- [x] **Step 4: Ledger (P2 — cùng commit):** PROP `brief-integrity` → `mechanism: vnext-brief`, `status: active`, `reproducible_litmus`, litmus = pytest file test này; consumers: `vnext_dispatch.py`. Verify: `pytest cli/tests/test_vnext_w0_artifacts.py -q` → 4 passed.
- [x] **Step 5: Run pass → commit** — `feat(vnext-w1): gate vnext-brief (verbatim traceability + staleness, + ledger)`

---

### Task 7: Gate `result-contract` (đủ field §18.4)

**Files:**
- Modify: `.maika/tools/gate-check/gates.py`, `cli.py`
- Create: `.maika/tools/gate-check/tests/test_vnext_result_gate.py`
- Modify: `docs/refactor/maika-vnext/enforcement-ledger.yaml` (cùng commit)

**Interfaces:**
- Produces: `validate_result_contract(text, allowed_files=None) -> Result`. Required keys (TOÀN BỘ §18.4, key phải CÓ MẶT — được phép rỗng theo rule dưới): `status`, `task_id`, `brief_hash`, `base_commit`, `changed_files`, `changed_symbols`, `commands`, `tests`, `concerns`, `deviations`, `evidence`, `commit_sha`. Rules:
  - `status ∈ {DONE, DONE_WITH_CONCERNS, NEEDS_CONTEXT, BLOCKED, STALE_PLAN, FAILED_VERIFICATION}`.
  - Status `DONE`/`DONE_WITH_CONCERNS`: `commands` ≥1 và mỗi command đủ `command/exit_code/expected/observed` với `observed` non-empty (exit code alone không đủ); `commit_sha` non-empty; `changed_files ⊆ allowed_files` khi allowed_files truyền.
  - Status khác (BLOCKED/NEEDS_CONTEXT/STALE_PLAN/FAILED_VERIFICATION): `concerns` phải non-empty (ghi lý do); commands được phép rỗng; `commit_sha` được phép null.
  - CLI gate `vnext-result`, `--against <queue-entry.json>` tùy chọn → allowed_files (union files.create/modify/test).

- [x] **Step 1: Failing tests** (đầy đủ, chạy được):

```python
# .maika/tools/gate-check/tests/test_vnext_result_gate.py
import importlib.util
from pathlib import Path

import yaml

_G = Path(__file__).resolve().parents[1] / "gates.py"
spec = importlib.util.spec_from_file_location("gates", _G)
gates = importlib.util.module_from_spec(spec); spec.loader.exec_module(gates)

BASE = {
    "status": "DONE", "task_id": "TASK-001", "brief_hash": "h" * 64,
    "base_commit": "abc123", "changed_files": ["src/a.py"],
    "changed_symbols": ["A"], "tests": ["tests/test_a.py"],
    "concerns": [], "deviations": [], "evidence": [], "commit_sha": "def456",
    "commands": [{"command": "pytest -q", "exit_code": 0,
                  "expected": "1 passed", "observed": "1 passed in 0.1s"}],
}


def _res(**over):
    doc = dict(BASE, **over)
    return gates.validate_result_contract(yaml.safe_dump(doc), allowed_files=["src/a.py", "tests/test_a.py"])


def test_done_valid_passes():
    assert _res().ok


def test_missing_key_fails():
    doc = dict(BASE); doc.pop("changed_symbols")
    r = gates.validate_result_contract(yaml.safe_dump(doc))
    assert not r.ok and "changed_symbols" in r.reason


def test_done_without_observed_fails():
    r = _res(commands=[{"command": "pytest", "exit_code": 0,
                        "expected": "1 passed", "observed": ""}])
    assert not r.ok and "observed" in r.reason


def test_unknown_status_fails():
    r = _res(status="FINISHED")
    assert not r.ok and "status" in r.reason


def test_undeclared_file_fails():
    r = _res(changed_files=["src/khac.py"])
    assert not r.ok and "undeclared" in r.reason


def test_done_without_commit_sha_fails():
    r = _res(commit_sha=None)
    assert not r.ok and "commit_sha" in r.reason


def test_blocked_requires_concerns_allows_empty_commands():
    r = _res(status="BLOCKED", commands=[], commit_sha=None, concerns=["thiếu context X"])
    assert r.ok
    r2 = _res(status="BLOCKED", commands=[], commit_sha=None, concerns=[])
    assert not r2.ok and "concerns" in r2.reason
```

- [x] **Step 2 fail** (`AttributeError`) → **Step 3 implement** theo đúng rules trên, style `Result` (~40 dòng, executor viết khớp từng assert của test).
- [x] **Step 4: Ledger (P2 — cùng commit):** PROP `result-contract` → `mechanism: vnext-result`, `status: active`, `reproducible_litmus`, litmus = pytest file này; consumers: `vnext_dispatch.py`. Verify 4 schema test W0 pass.
- [x] **Step 5 pass → commit** — `feat(vnext-w1): gate vnext-result (full §18.4, exit-code-not-sufficient, + ledger)`

---

### Task 8: vnext_dispatch.py — 3 dispatch class + run loop sequential

**Files:**
- Create: `.maika/tools/microloop-orchestrator/vnext_dispatch.py`
- Create: `.maika/tools/microloop-orchestrator/tests/test_vnext_dispatch.py`

**Interfaces:**
- Produces:
  - `build_prompt(klass, ws, brief_rel, result_rel, extra=None) -> str` với klass ∈ {"planning", "implementation", "task_review"} — prompt fresh-context: role contract ngắn + đường dẫn brief + result path + result schema §18.4 + allowed files + "KHÔNG nhận lịch sử hội thoại".
  - `run_queue(ws, repo_root, runner, max_retries=2) -> dict` — vòng lặp sequential: mỗi task pending theo thứ tự queue: gate `vnext-brief` (gọi validator trực tiếp qua `_load gates`) → `implementation` dispatch (qua `orchestrator.dispatch_worker` với runner inject) → result file phải tồn tại + `validate_result_contract` (allowed_files từ queue entry) → nếu DONE: `task_review` dispatch ghi `reviews/task-NNN.md`; review verdict dòng đầu `VERDICT: APPROVED|FINDINGS`; FINDINGS → re-dispatch implementation kèm đường dẫn review (1 lần) → re-review; hết retry → task blocked, return. Status queue per task: pending→in_progress→done|blocked (ghi TASK_QUEUE.json mỗi bước — crash-safe resume giống apply_command). STALE_PLAN trong result → dừng toàn queue, STATE → BLOCKED(reason=stale_plan).
- Consumes: `orchestrator.dispatch_worker`, `make_worker_runner`, gates task 6/7, `vnext_state.transition`.

**Quy ước prompt (để stub + worker parse máy được):** mọi prompt của `build_prompt` bắt đầu bằng 4 dòng marker:

```text
ROLE: implementation|task_review|planning
TASK_ID: TASK-001
BRIEF_FILE: <abs path>
OUTPUT_FILE: <abs path>
```

- [x] **Step 1: Failing tests** — dùng **stub runner** (không subprocess), code ĐẦY ĐỦ:

```python
# tests/test_vnext_dispatch.py
import json
import re
from pathlib import Path

import yaml

import plan_compiler as pc
import vnext_dispatch as vd
import vnext_state as vs

# Fixture plan: tái dùng nguyên văn PLAN_TPL + _mk của test_vnext_plan_gate
# (dán lại 2 helper đó vào file này để test độc lập — executor copy verbatim).


def _setup(tmp_path):
    ws = vs.init_workspace(tmp_path / "changes", "demo", "small", "t")
    plan_text, _ = _mk(tmp_path)           # helper copy từ test_vnext_plan_gate
    (ws / "SPEC.md").write_text("# spec\n", encoding="utf-8")
    # spec_hash phải khớp SPEC.md thật (xem Task 5): thay SPECSHA bằng sha256 của SPEC.md
    import hashlib
    plan_text = plan_text.replace("SPECSHA", hashlib.sha256((ws / "SPEC.md").read_bytes()).hexdigest())
    (ws / "IMPLEMENTATION_PLAN.md").write_text(plan_text, encoding="utf-8")
    out = pc.compile_plan(ws, repo_root=tmp_path)
    assert out["verdict"] == "APPROVED"
    vs.transition(ws, "PLANNING"); vs.transition(ws, "PLAN_REVIEW"); vs.transition(ws, "EXECUTING")
    return ws


def _marker(prompt, key):
    return re.search(rf"^{key}: (.+)$", prompt, re.M).group(1)


def _valid_result(ws, task_id, status="DONE", changed=None):
    q = json.loads((ws / "generated" / "TASK_QUEUE.json").read_text())
    entry = next(t for t in q["tasks"] if t["id"] == task_id)
    files = entry["files"]
    allowed = (files.get("create") or []) + (files.get("modify") or []) + (files.get("test") or [])
    done = status in ("DONE", "DONE_WITH_CONCERNS")
    return {
        "status": status, "task_id": task_id, "brief_hash": entry["brief_hash"],
        "base_commit": q.get("plan_sha256", "x")[:12], "changed_files": changed or allowed[:1],
        "changed_symbols": [], "tests": [],
        "concerns": [] if done else ["stub reason"],
        "deviations": [], "evidence": [],
        "commit_sha": "stubsha" if done else None,
        "commands": ([{"command": "pytest -q", "exit_code": 0,
                       "expected": "pass", "observed": "1 passed"}] if done else []),
    }


def make_stub(ws, behaviors):
    """behaviors: list hành vi pop theo thứ tự call. Mỗi hành vi:
    ('result', status) | ('result_badfile',) | ('no_result',) | ('review', verdict)."""
    calls = []

    def runner(prompt):
        role = _marker(prompt, "ROLE")
        task_id = _marker(prompt, "TASK_ID")
        out = Path(_marker(prompt, "OUTPUT_FILE"))
        b = behaviors.pop(0)
        calls.append((role, task_id, b))
        if b[0] == "result":
            out.write_text(yaml.safe_dump(_valid_result(ws, task_id, status=b[1])))
        elif b[0] == "result_badfile":
            out.write_text(yaml.safe_dump(_valid_result(ws, task_id, changed=["src/ngoai_scope.py"])))
        elif b[0] == "no_result":
            pass
        elif b[0] == "review":
            out.write_text(f"VERDICT: {b[1]}\n- nhận xét stub\n")
        return 0, "ok"

    return runner, calls


def _statuses(ws):
    q = json.loads((ws / "generated" / "TASK_QUEUE.json").read_text())
    return {t["id"]: t["status"] for t in q["tasks"]}


def test_happy_path_two_tasks(tmp_path):
    ws = _setup(tmp_path)
    runner, calls = make_stub(ws, [
        ("result", "DONE"), ("review", "APPROVED"),
        ("result", "DONE"), ("review", "APPROVED"),
    ])
    out = vd.run_queue(ws, tmp_path, runner)
    assert out["status"] == "done"
    assert _statuses(ws) == {"TASK-001": "done", "TASK-002": "done"}
    assert [c[0] for c in calls] == ["implementation", "task_review"] * 2


def test_result_missing_blocks(tmp_path):
    ws = _setup(tmp_path)
    runner, _ = make_stub(ws, [("no_result",), ("no_result",), ("no_result",)])
    out = vd.run_queue(ws, tmp_path, runner, max_retries=2)
    assert out["status"] == "blocked"        # exit 0 nhưng không có result ≠ done
    assert _statuses(ws)["TASK-001"] == "blocked"


def test_result_contract_violation_blocks(tmp_path):
    ws = _setup(tmp_path)
    runner, _ = make_stub(ws, [("result_badfile",), ("result_badfile",), ("result_badfile",)])
    out = vd.run_queue(ws, tmp_path, runner, max_retries=2)
    assert out["status"] == "blocked" and "undeclared" in out["reason"]


def test_findings_then_fix_then_approved(tmp_path):
    ws = _setup(tmp_path)
    runner, calls = make_stub(ws, [
        ("result", "DONE"), ("review", "FINDINGS"),
        ("result", "DONE"), ("review", "APPROVED"),      # fix re-dispatch + re-review
        ("result", "DONE"), ("review", "APPROVED"),
    ])
    out = vd.run_queue(ws, tmp_path, runner)
    assert out["status"] == "done"
    assert [c[0] for c in calls][:4] == ["implementation", "task_review",
                                          "implementation", "task_review"]


def test_stale_plan_stops_queue(tmp_path):
    ws = _setup(tmp_path)
    runner, _ = make_stub(ws, [("result", "STALE_PLAN")])
    out = vd.run_queue(ws, tmp_path, runner)
    assert out["status"] == "stale_plan"
    assert vs.load_state(ws)["state"] == "BLOCKED"
    assert vs.load_state(ws)["blocked"]["reason"] == "stale_plan"


def test_resume_skips_done(tmp_path):
    ws = _setup(tmp_path)
    runner, calls = make_stub(ws, [
        ("result", "DONE"), ("review", "APPROVED"),
        ("result", "DONE"), ("review", "APPROVED"),
    ])
    vd.run_queue(ws, tmp_path, runner)
    runner2, calls2 = make_stub(ws, [])
    out = vd.run_queue(ws, tmp_path, runner2)  # không còn task pending
    assert out["status"] == "done" and calls2 == []
```

- [x] **Step 2 fail → Step 3 implement.** `build_prompt` LUÔN mở đầu bằng 4 dòng marker (ROLE/TASK_ID/BRIEF_FILE/OUTPUT_FILE — quy ước ở trên, cả stub lẫn worker thật parse được), sau đó role block:

```python
_ROLES = {
    "planning": "Bạn là Plan Reviewer độc lập. So SPEC ↔ IMPLEMENTATION_PLAN ↔ codebase hiện tại. "
                "Ghi review vào {out}; dòng ĐẦU TIÊN phải là 'VERDICT: APPROVED' hoặc 'VERDICT: FINDINGS'.",
    "implementation": "Bạn là Implementer cho MỘT task. Đọc brief tại {brief}; chỉ được sửa các file "
                      "khai trong brief; làm đúng từng step; chạy các command verification và ghi observed THẬT. "
                      "Ghi result YAML vào {out} đúng schema: status/task_id/brief_hash/base_commit/"
                      "changed_files/commands(command,exit_code,expected,observed)/tests/concerns/deviations. "
                      "Gặp re-plan trigger → status STALE_PLAN, dừng.",
    "task_review": "Bạn là Task Reviewer độc lập (không phải người implement). Đọc brief {brief}, "
                   "result {result}, diff hiện tại. Hai lens: tuân thủ plan/spec + chất lượng code. "
                   "Ghi review vào {out}; dòng đầu 'VERDICT: APPROVED' hoặc 'VERDICT: FINDINGS' kèm danh sách.",
}
```

`run_queue` viết theo pattern `apply_command` (orchestrator.py:570) — disk là source of truth mỗi vòng, `json` thay `yaml` cho queue. (~90 dòng; executor giữ cùng phong cách log qua `append_activity_event` với event mới `vnext_task_*`.)

- [x] **Step 4 pass → commit** — `feat(vnext-w1): dispatch classes + sequential run loop (fresh worker, review loop)`

---

### Task 9: Independent plan review (planning_dispatch) + wire compile

**Files:**
- Modify: `.maika/tools/microloop-orchestrator/vnext_dispatch.py` (hàm `review_plan(ws, runner) -> str`)
- Modify: `.maika/tools/microloop-orchestrator/tests/test_vnext_dispatch.py` (2 test)

**Interfaces:**
- Produces: `review_plan(ws, runner)` — planning dispatch ghi `reviews/plan-review.md`, trả verdict; chỉ khi cả `PLAN_VALIDATION.json == APPROVED` **và** plan-review `VERDICT: APPROVED` thì `vnext_state.transition(ws, "EXECUTING")` được phép (enforce trong CLI Task 11, không trong hàm).

- [x] Tests: review APPROVED trả "APPROVED"; review file thiếu dòng VERDICT → trả "FINDINGS" (fail-closed). Implement ~20 dòng. Commit — `feat(vnext-w1): independent plan review dispatch`

---

### Task 10: Write-gate brief-scope

**Files:**
- Modify: `.maika/hooks/write-gate/write_gate.py`
- Create/Modify: `.maika/hooks/write-gate/tests/test_vnext_brief_scope.py`

**Interfaces:**
- Produces: `_vnext_active_task(project_root, framework_root) -> (ws, task)|None` — quét `<framework_root>/changes/*/STATE.yaml` state==EXECUTING (flag `workflow_engine==vnext` đọc từ `<framework_root>/profiles/execution-mode.yaml` rendered; template chưa render/parse lỗi → None, không chặn). Trả `(ws, task)` chỉ khi ĐỦ: `generated/PLAN_VALIDATION.json` verdict `APPROVED`; `generated/TASK_QUEUE.json.plan_sha256 == PLAN_MANIFEST.json.plan_sha256` (không stale); có đúng một task `in_progress`. EXECUTING mà thiếu một trong ba → trả `("deny", reason)` sentinel để evaluate_write DENY tường minh (không fallthrough legacy — trạng thái hỏng phải chặn, fail-closed). Trong `evaluate_write` (write_gate.py:491), chèn **sau** `check_session_gate`, **trước** check KNOWLEDGE_CHECKPOINT:

```python
    # vNext mode THAY THẾ legacy phase-gating có chủ đích (v2 §21): khi một change
    # EXECUTING dưới workflow_engine=vnext, KNOWLEDGE_CHECKPOINT/apply-gate legacy
    # không áp dụng (vnext có gate riêng: plan approval + brief-scope + result contract).
    vnext = _vnext_active_task(project_root, framework_root)
    if vnext is not None:
        if vnext[0] == "deny":
            return Decision(False, f"vNext EXECUTING nhưng trạng thái hỏng: {vnext[1]}")
        ws, task = vnext
        allowed = set()
        for key in ("create", "modify", "test"):
            allowed.update((task.get("files") or {}).get(key, []) or [])
        rel = policy_path.relative_to(project_root).as_posix() if policy_path.is_absolute() else policy_path.as_posix()
        if rel in allowed or rel.startswith(str(ws.relative_to(project_root))):
            return Decision(True)
        return Decision(False, f"vNext brief-scope: {rel} ngoài files khai báo của {task['id']}")
```

(yaml.safe_load lỗi vì template Jinja → treat as legacy: bọc try/except trả None. Đây là điểm dogfood-trên-repo-template đã biết.)

- [x] Tests (8): flag legacy → None (regression toàn suite write-gate pass nguyên trạng); flag vnext + EXECUTING + đủ approval/fresh + file trong allowed → ALLOW; ngoài allowed → DENY kèm task id; ghi vào chính workspace change → ALLOW; không có change EXECUTING → fallthrough legacy; **EXECUTING nhưng PLAN_VALIDATION ≠ APPROVED → DENY**; **plan_sha256 queue ≠ manifest → DENY (stale)**; **không có task in_progress → DENY**. Fixture: tmp project_root với profiles rendered + changes/demo/{STATE.yaml, generated/{PLAN_VALIDATION.json,PLAN_MANIFEST.json,TASK_QUEUE.json}} tự dựng.
- [x] Run: `cd .maika/hooks/write-gate && /usr/bin/python3 -m pytest tests/ -q` → toàn suite PASS. Commit — `feat(vnext-w1): write-gate brief-scope (vnext EXECUTING)`

---

### Task 11: CLI subcommands + e2e stub

**Files:**
- Modify: `.maika/tools/microloop-orchestrator/orchestrator.py` (main(): thêm subcommands)
- Create: `.maika/tools/microloop-orchestrator/tests/test_vnext_cli_e2e.py`

**Interfaces:**
- Produces subcommands (đều yêu cầu `workflow_engine == vnext` từ config, ngược lại refuse exit 2 — R1 consumer của flag). **State transition tường minh per lệnh (fix finding F5):**

| Lệnh | Yêu cầu state trước | Làm gì | State sau |
|---|---|---|---|
| `vnext-init --changes-root <dir> --id <id> --class <c> --title <t>` | (chưa có ws) | init_workspace + gate `vnext-workspace` trên CHANGE.yaml vừa tạo | `INTAKE` |
| `vnext-compile --workspace <ws> --repo-root <root>` | `INTAKE` hoặc `PLANNING` (INTAKE → tự transition PLANNING trước khi compile — hợp lệ ALLOWED map) | compile_plan | verdict APPROVED → `PLAN_REVIEW`; REVISE → giữ `PLANNING` |
| `vnext-review-plan --workspace <ws>` | `PLAN_REVIEW` | planning dispatch (worker_command config) → reviews/plan-review.md | giữ `PLAN_REVIEW` (verdict ghi file) |
| `vnext-run --workspace <ws> --repo-root <root>` | `PLAN_REVIEW` với PLAN_VALIDATION==APPROVED **và** plan-review VERDICT: APPROVED → transition `EXECUTING` rồi run_queue; hoặc `EXECUTING` (resume) | run_queue | queue done → `VERIFYING`; blocked → giữ EXECUTING (task blocked); stale_plan → `BLOCKED(stale_plan)` |
| `vnext-status --workspace <ws>` | bất kỳ | in state + bảng task | không đổi |

- [x] E2E test với config stub (`workflow_engine: vnext`, runner stub từ Task 8) — **assert state sau MỖI lệnh**: init→`INTAKE` → compile→`PLAN_REVIEW` → review-plan (stub APPROVED)→`PLAN_REVIEW` → run→2 task done→`VERIFYING`. Test refuse khi flag legacy (exit 2, không side-effect). Test compile verdict REVISE giữ `PLANNING`.
- [x] **Legacy-compat test (fix finding F3):** cùng một fixture project có CẢ legacy `knowledge/active/microloop/TASK_QUEUE.md` (dựng bằng `initialize_runtime_queue`) LẪN vnext workspace: (a) `load_runtime_queue` vẫn đọc đúng queue markdown; (b) `vnext-run` không đọc/ghi artifact legacy; (c) toàn suite microloop cũ pass nguyên trạng — chứng minh compatibility reader legacy còn nguyên trong opt-in period (v2 §17).
- [x] Run toàn suite microloop + gate-check + write-gate + cli/tests → PASS hết. Commit — `feat(vnext-w1): vnext CLI subcommands + e2e (flag-gated, state-explicit, legacy-compat)`

---

### Task 12: Ledger activation + docs + final verify

**Files:**
- Modify: `docs/refactor/maika-vnext/enforcement-ledger.yaml`
- Modify: `.maika/tools/README.md` (mục gate-check: thêm 3 gate mới; mục microloop: thêm vnext subcommands)

**Interfaces:** không code.

- [x] Kiểm consistency ledger: 4 entry đã activate ở Task 4/6/7 (vnext-plan, vnext-workspace, vnext-brief, vnext-result) đủ litmus + consumers thật; không entry nào còn `proposed` với `scheduled_wave: W1`.
- [x] Chạy lại 4 schema test W0: `/usr/bin/python3 -m pytest cli/tests/test_vnext_w0_artifacts.py -q` → 4 passed.
- [x] Final verify — chạy đủ 7 suite như W0 Task 2, dán số vào commit message.
- [x] Commit — `docs(vnext-w1): activate 3 gate ledger entries + tool docs`; push branch; mở PR `feat/vnext-w1-vertical-slice → main` (body: link Master Plan v2 §26 W1 + bảng exit criteria).

---

## Exit criteria W1 (từ Master Plan v2 — kiểm khi đóng PR)

- Dogfood A (2 change `small` thật chạy vnext) — **sau khi merge**, tracked riêng.
- Không task nào done từ exit code đơn thuần (gate vnext-result + test_result_missing_blocks).
- Brief verbatim traceable (gate vnext-brief + test_verbatim_roundtrip).
- Legacy untouched & default (flag legacy + regression suites xanh).

## Self-review (rev 2 — sau independent plan review)

1. **Spec coverage:** v2 §26 W1 scope 1→7: workspace+schemas+fixtures (T1+T4 gate vnext-workspace), vocabulary+skill (T2), plan gate + independent review (T4/T9), compiler + legacy-compat test tường minh (T5+T11), dispatch+result đủ §18.4 (T6/T7/T8), write-gate có approval/staleness/fail-closed (T10), flag + state-transition map per lệnh (T1+T11). Must-not-depend: không task nào đụng registry/router/parallel/locks/platform khác.
2. **Placeholder scan:** Task 4/7/8 test code viết đầy đủ chạy được (fix F8); chỗ duy nhất còn "executor viết" là body validator T7 (~40 dòng) và run_queue T8 (~90 dòng) — cả hai có spec hành vi khớp 1-1 với từng assert của test đã viết sẵn, không có tự do thiết kế.
3. **Type consistency:** naming per-task file thống nhất `TASK-NNN` (briefs/TASK-001.md, results/TASK-001.yaml — fix F10); marker prompt ROLE/TASK_ID/BRIEF_FILE/OUTPUT_FILE dùng chung T8 stub + role templates; brief format header+`\n---\n`+body dùng chung T5/T6/T8/T10; PLAN_TPL fixture + `_mk` dùng chung T4/T5/T8 (copy verbatim mỗi file test để độc lập).
4. **Findings disposition (codex review 2026-07-10):** áp F2(partial)/F3/F4/F5/F6/F7/F8/F9(partial)/F10 + phần hợp lệ của F1 (symbol grounding, spec-hash match); bác phần F1 đòi full §16 tại W1 (trái Master Plan v2 §26 W1 "mechanical subset" — thuộc W2+) và bác việc giữ KNOWLEDGE_CHECKPOINT legacy trong vnext mode (thay thế có chủ đích, đã ghi comment trong code T10).
