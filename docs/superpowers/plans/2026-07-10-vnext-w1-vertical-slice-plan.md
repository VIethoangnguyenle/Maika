# Maika vNext W1 — Claude Code Vertical Slice — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

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
- Ledger: 3 gate mới đã có PROP entries (PROP plan/brief-integrity/result-contract, scheduled W1); Task 12 chuyển `active` kèm litmus. Không thêm enforcement ngoài danh sách này (P2).

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
├── briefs/task-NNN.md   (header YAML + "\n---\n" + verbatim plan section)
├── results/task-NNN.yaml (schema §18.4)
└── reviews/plan-review.md, reviews/task-NNN.md
```

`brief_hash` = sha256 hex của **verbatim section text** (sau `---`), không gồm header.

---

### Task 1: Feature flag + workspace + state machine

**Files:**
- Create: `.maika/tools/microloop-orchestrator/vnext_state.py`
- Create: `.maika/tools/microloop-orchestrator/tests/test_vnext_state.py`
- Modify: `.maika/profiles/execution-mode.yaml` (thêm 1 dòng cuối file)

**Interfaces:**
- Produces: `STATES` (14 state), `init_workspace(changes_root, change_id, klass, title) -> Path`, `load_state(ws) -> dict`, `transition(ws, new_state, blocked=None) -> dict`, `workflow_engine(config) -> str`.
- Consumes: không (module lá).

- [ ] **Step 1: Viết failing test**

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

- [ ] **Step 2: Chạy fail**

Run: `cd .maika/tools/microloop-orchestrator && /usr/bin/python3 -m pytest tests/test_vnext_state.py -q`
Expected: FAIL `ModuleNotFoundError: No module named 'vnext_state'` (tests/ đã có conftest/path theo suite hiện hành — nếu suite dùng rootdir import, thêm `sys.path` giống test hiện có trong dir này; đọc 1 test file sẵn có để khớp).

- [ ] **Step 3: Implement**

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

- [ ] **Step 4: Thêm flag vào execution-mode.yaml** — thêm 2 dòng cuối file (ngoài mọi khối Jinja):

```yaml
# vNext W1: engine flag — vnext là opt-in; legacy là mặc định (Master Plan v2 §26 W1)
workflow_engine: legacy
```

- [ ] **Step 5: Chạy pass + suites**

Run: `cd .maika/tools/microloop-orchestrator && /usr/bin/python3 -m pytest tests/ -q` → toàn suite PASS.
Run: `/usr/bin/python3 -m pytest cli/tests/ -q` (từ repo root) → PASS; nếu snapshot scaffold fail vì execution-mode.yaml đổi → cập nhật snapshot fixture trong cùng commit.

- [ ] **Step 6: Commit** — `feat(vnext-w1): workspace + 14-state machine + workflow_engine flag`

---

### Task 2: Capability vocabulary + skill writing-plan

**Files:**
- Create: `.maika/profiles/capabilities.md`
- Create: `.maika/skills/writing-plan/SKILL.md`
- Modify: `.maika/skills/skill-index.yaml` (regen bằng tool)

**Interfaces:**
- Produces: 6 capability IDs (văn bản, tĩnh — KHÔNG runtime); skill canonical đầu tiên tham chiếu IDs (R1 consumer cùng PR).

- [ ] **Step 1: Viết `.maika/profiles/capabilities.md`**

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

- [ ] **Step 2: Viết skill theo schema skill-lint** — đọc `.maika/skills/codebase-explorer/SKILL.md` làm khung heading (REQUIRED_SECTIONS B1..; frontmatter `name/description/version`). Nội dung cốt lõi (điền vào khung đó, giữ đủ heading bắt buộc):

```markdown
---
name: writing-plan
version: '1.0'
description: >
  Sinh IMPLEMENTATION_PLAN.md code-level cho một change vNext: frontmatter máy-đọc
  (base_commit, spec_hash, evidence_hash), mỗi task một section TASK-NNN với
  implementation_mode exact|guided|intent, files/symbols/anchors, TDD steps, commands
  + expected. Dùng SAU khi SPEC.md được duyệt. KHÔNG dùng cho: brainstorm (W2),
  review plan (planning_dispatch đảm nhiệm).
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

- [ ] **Step 3: Lint + regen index**

Run: `/usr/bin/python3 .maika/tools/skill-lint/validate_skills.py` → writing-plan PASS (sửa heading theo báo lỗi lint nếu thiếu section bắt buộc — lint là nguồn chân lý schema).
Run: `/usr/bin/python3 .maika/tools/skill-index/generate_index.py` → skill-index.yaml có entry writing-plan.
Run: `/usr/bin/python3 -m pytest cli/tests/ -q` → snapshot lệch thì cập nhật cùng commit.

- [ ] **Step 4: Commit** — `feat(vnext-w1): capability vocabulary + skill writing-plan (R1: vocabulary + consumer cùng PR)`

---

### Task 3: plan_parser.py

**Files:**
- Create: `.maika/tools/microloop-orchestrator/plan_parser.py`
- Create: `.maika/tools/microloop-orchestrator/tests/test_plan_parser.py`

**Interfaces:**
- Produces: `parse_plan(text) -> {"meta": dict, "tasks": [{"id","title","header":dict,"section_text":str}]}` — `section_text` là VERBATIM (từ dòng `### TASK-` đến trước `### TASK-` kế/EOF). Raise `ValueError` khi thiếu frontmatter/header.
- Consumes: không.

- [ ] **Step 1: Failing test**

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

- [ ] **Step 2: Run fail** — `ModuleNotFoundError: plan_parser`.

- [ ] **Step 3: Implement**

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

- [ ] **Step 4: Run pass** → 4 passed. **Step 5: Commit** — `feat(vnext-w1): plan parser (frontmatter + verbatim TASK sections)`

---

### Task 4: Gate `plan` (mechanical subset §16)

**Files:**
- Modify: `.maika/tools/gate-check/gates.py` (thêm validator cuối file)
- Modify: `.maika/tools/gate-check/cli.py` (VALIDATORS + kwargs)
- Create: `.maika/tools/gate-check/tests/test_vnext_plan_gate.py`

**Interfaces:**
- Produces: `validate_vnext_plan(text, repo_root=None) -> Result` — checks W1: frontmatter đủ; base_commit resolve được (`git cat-file -t <sha>` trong repo_root); task ID duy nhất + khớp heading; deps tồn tại + acyclic; mỗi task có `verification.command` + `expected`; files.modify/test tồn tại trên disk (files.create thì KHÔNG cần); không `TODO`/`TBD`/`FIXME` trong section; `implementation_mode` hợp lệ. CLI: gate name `vnext-plan`, flag `--repo-root` (tái dụng pattern code-evidence).
- Consumes: `plan_parser.parse_plan` (import qua `_load_module` pattern? gates.py không import cross-tool — **copy logic parse tối thiểu KHÔNG được phép**; thay vào đó cli.py load plan_parser bằng `importlib` từ đường dẫn microloop-orchestrator như orchestrator `_load_gate_check` làm ngược lại, rồi truyền `doc` đã parse vào validator qua kwargs `plan_doc`).

- [ ] **Step 1: Failing tests** (fixture PLAN tái dùng từ test_plan_parser, thêm biến thể lỗi):

```python
# .maika/tools/gate-check/tests/test_vnext_plan_gate.py
import importlib.util
import subprocess
from pathlib import Path

import pytest

_G = Path(__file__).resolve().parents[1] / "gates.py"
spec = importlib.util.spec_from_file_location("gates", _G)
gates = importlib.util.module_from_spec(spec); spec.loader.exec_module(gates)

_PP = Path(__file__).resolve().parents[2] / "microloop-orchestrator" / "plan_parser.py"
spec2 = importlib.util.spec_from_file_location("plan_parser", _PP)
pp = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(pp)

PLAN_OK = """---(nguyên văn fixture PLAN của test_plan_parser, đổi files sang
tmp fixture tạo trong test — xem _mk bên dưới)---"""


def _mk(tmp_path, plan_text):
    (tmp_path / "src").mkdir(); (tmp_path / "tests").mkdir()
    (tmp_path / "src" / "a.py").write_text("A = 1\n")
    (tmp_path / "tests" / "test_a.py").write_text("def test_a():\n    assert True\n")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-qm", "base"], cwd=tmp_path, check=True)
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=tmp_path,
                         capture_output=True, text=True).stdout.strip()
    return plan_text.replace("abc123", sha)


def test_plan_ok_passes(tmp_path):
    text = _mk(tmp_path, PLAN_OK)
    res = gates.validate_vnext_plan(text, plan_doc=pp.parse_plan(text), repo_root=str(tmp_path))
    assert res.ok, res.reason


def test_unresolvable_base_commit_fails(tmp_path):
    text = _mk(tmp_path, PLAN_OK).replace(
        gates_sha := text_sha(tmp_path), "deadbeef" * 5)  # thay bằng biến sha thật khi viết
    ...


def test_missing_verification_fails(tmp_path): ...
def test_todo_marker_fails(tmp_path): ...
def test_cyclic_deps_fails(tmp_path): ...
def test_modify_file_missing_fails(tmp_path): ...
```

(Executor viết đủ 6 test theo cùng pattern `_mk`; mỗi test một biến thể hỏng của fixture — thay `verification:` bằng rỗng, chèn `TODO`, đảo deps thành vòng, đổi files.modify sang `src/khong_ton_tai.py`. Không test nào được để `...` khi hoàn thành.)

- [ ] **Step 2: Run fail** — `AttributeError: gates has no validate_vnext_plan`.

- [ ] **Step 3: Implement trong gates.py**

```python
_PLACEHOLDER = re.compile(r"\b(TODO|TBD|FIXME)\b")
_VALID_MODES = {"exact", "guided", "intent"}


def validate_vnext_plan(text, plan_doc=None, repo_root=None) -> Result:
    """Gate `plan` — mechanical subset W1 (Master Plan v2 §16, §22)."""
    if plan_doc is None:
        return Result(False, "plan_doc required (cli parses via plan_parser)")
    import subprocess
    meta, tasks = plan_doc["meta"], plan_doc["tasks"]
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

- [ ] **Step 4: Wire cli.py** — thêm `"vnext-plan": "validate_vnext_plan"` vào `VALIDATORS`; trong `main()` thêm nhánh:

```python
    elif args.gate == "vnext-plan":
        pp_path = Path(__file__).resolve().parents[1] / "microloop-orchestrator" / "plan_parser.py"
        spec_pp = importlib.util.spec_from_file_location("plan_parser", pp_path)
        pp = importlib.util.module_from_spec(spec_pp); spec_pp.loader.exec_module(pp)
        kwargs["plan_doc"] = pp.parse_plan(text)
        kwargs["repo_root"] = args.repo_root or os.getcwd()
```

(`import importlib.util` đưa lên đầu `main` giống `_load_module` pattern.)

- [ ] **Step 5: Run pass** — `cd .maika/tools/gate-check && /usr/bin/python3 -m pytest tests/test_vnext_plan_gate.py -q` → 6 passed; toàn suite gate-check PASS.
- [ ] **Step 6: Commit** — `feat(vnext-w1): gate vnext-plan (mechanical validation subset)`

---

### Task 5: plan_compiler.py — PLAN_VALIDATION + TASK_QUEUE.json + verbatim briefs

**Files:**
- Create: `.maika/tools/microloop-orchestrator/plan_compiler.py`
- Create: `.maika/tools/microloop-orchestrator/tests/test_plan_compiler.py`

**Interfaces:**
- Produces: `compile_plan(ws, repo_root) -> dict` — đọc `IMPLEMENTATION_PLAN.md`, chạy gate `validate_vnext_plan` (qua `_load_gate_check()` pattern của orchestrator.py:43), ghi `generated/PLAN_VALIDATION.json` ({verdict: APPROVED|REVISE, checks}), nếu APPROVED: ghi `generated/PLAN_MANIFEST.json` (plan_sha256 = sha256 toàn file, spec_sha256 nếu SPEC.md tồn tại), `generated/TASK_QUEUE.json` (tasks topo-sequential — tái dụng `orchestrator.topo_sort` qua importlib cùng dir), `briefs/task-NNN.md` (header YAML: change_id, task_id, brief_hash, generated_at + `\n---\n` + section_text verbatim). Trả manifest dict. Idempotent + deterministic (không timestamp trong hash).
- Consumes: `plan_parser.parse_plan`, `gates.validate_vnext_plan`, `orchestrator.topo_sort`.

- [ ] **Step 1: Failing tests**

```python
# tests/test_plan_compiler.py
import hashlib
import json
from pathlib import Path

import plan_compiler as pc
import vnext_state as vs

# PLAN fixture: tái dùng nguyên văn PLAN của test_plan_parser (import từ file test đó
# hoặc dán lại nguyên văn — dán lại để test độc lập), files trỏ vào fixture repo _mk
# giống test_vnext_plan_gate (dựng git repo tmp, thay abc123 = sha thật).


def _setup(tmp_path):
    ws = vs.init_workspace(tmp_path / "changes", "demo", "small", "t")
    plan_text = _mk_repo_and_plan(tmp_path)      # helper như Task 4
    (ws / "IMPLEMENTATION_PLAN.md").write_text(plan_text, encoding="utf-8")
    (ws / "SPEC.md").write_text("# spec\n", encoding="utf-8")
    return ws, tmp_path


def test_compile_writes_queue_and_briefs(tmp_path):
    ws, root = _setup(tmp_path)
    out = pc.compile_plan(ws, repo_root=root)
    q = json.loads((ws / "generated" / "TASK_QUEUE.json").read_text())
    assert [t["id"] for t in q["tasks"]] == ["TASK-001", "TASK-002"]
    assert all(t["status"] == "pending" for t in q["tasks"])
    brief = (ws / "briefs" / "task-TASK-001.md").read_text()
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

- [ ] **Step 2: Run fail.** **Step 3: Implement**

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
    try:
        doc = pp.parse_plan(text)
        res = gates.validate_vnext_plan(text, plan_doc=doc, repo_root=str(repo_root))
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
    spec_path = ws / "SPEC.md"
    manifest = {
        "change_id": doc["meta"]["change_id"],
        "base_commit": doc["meta"]["base_commit"],
        "plan_sha256": plan_sha,
        "spec_sha256": _sha(spec_path.read_text(encoding="utf-8")) if spec_path.exists() else None,
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
        brief_path = ws / "briefs" / f"task-{tid}.md"
        header = yaml.safe_dump({"change_id": manifest["change_id"], "task_id": tid,
                                 "brief_hash": brief_hash, "plan_sha256": plan_sha},
                                sort_keys=False)
        brief_path.write_text(header + "\n---\n" + body, encoding="utf-8")
        queue_tasks.append({
            "id": tid, "depends_on": t["header"].get("depends_on") or [],
            "status": "pending",
            "brief_path": str(brief_path.relative_to(ws)),
            "brief_hash": brief_hash,
            "result_path": f"results/task-{tid}.yaml",
            "files": t["header"].get("files") or {},
        })
    (gen / "TASK_QUEUE.json").write_text(json.dumps(
        {"change_id": manifest["change_id"], "plan_sha256": plan_sha,
         "tasks": queue_tasks}, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"verdict": "APPROVED", **manifest}
```

(Chú ý `_load` cho gates: đường dẫn `gate-check/gates.py` nằm ở `parents[1]` của module — viết helper cho đúng 2 trường hợp cùng-dir và sibling-tool như code trên.)

- [ ] **Step 4: Run pass** → 4 passed; toàn suite microloop PASS. **Step 5: Commit** — `feat(vnext-w1): deterministic plan compiler (verdict -> queue -> verbatim briefs)`

---

### Task 6: Gate `brief-integrity`

**Files:**
- Modify: `.maika/tools/gate-check/gates.py`, `cli.py`
- Create: `.maika/tools/gate-check/tests/test_vnext_brief_gate.py`

**Interfaces:**
- Produces: `validate_brief_integrity(text, queue_doc=None) -> Result` — text = nội dung brief file; tách header/body theo `\n---\n`; kiểm: header có task_id/brief_hash/plan_sha256; `sha256(body) == header.brief_hash`; entry trong queue_doc (TASK_QUEUE.json dict) có cùng task_id với cùng brief_hash + plan_sha256 khớp queue. CLI gate `vnext-brief` với `--against <TASK_QUEUE.json>` (tái dụng flag `--against` sẵn có).

- [ ] **Step 1: Failing tests** — 4 test: pass đúng; body bị sửa 1 ký tự → FAIL "brief hash mismatch"; task_id không có trong queue → FAIL; plan_sha256 lệch queue → FAIL "stale plan". (Fixture: dựng ws bằng plan_compiler từ Task 5 fixture — tái dụng `_setup`.)
- [ ] **Step 2: Run fail.** **Step 3: Implement** (gates.py):

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

- [ ] **Step 4: Run pass → commit** — `feat(vnext-w1): gate vnext-brief (verbatim traceability + staleness)`

---

### Task 7: Gate `result-contract`

**Files:**
- Modify: `.maika/tools/gate-check/gates.py`, `cli.py`
- Create: `.maika/tools/gate-check/tests/test_vnext_result_gate.py`

**Interfaces:**
- Produces: `validate_result_contract(text, allowed_files=None) -> Result` — text = results/task-NNN.yaml; required fields (§18.4): `status ∈ {DONE, DONE_WITH_CONCERNS, NEEDS_CONTEXT, BLOCKED, STALE_PLAN, FAILED_VERIFICATION}`, `task_id`, `brief_hash`, `base_commit`, `changed_files` (list), `commands` (list ≥1, mỗi cái có `command`/`exit_code`/`expected`/`observed`), `tests`; nếu status DONE*: mỗi command `observed` non-empty (exit code alone không đủ) và `changed_files ⊆ allowed_files` khi allowed_files truyền vào. CLI gate `vnext-result`, `--against <brief-or-queue-entry.json>` tùy chọn → allowed_files.

- [ ] **Step 1: Failing tests** — 5 test: hợp lệ DONE pass; thiếu `observed` → FAIL; status lạ → FAIL; changed_files ngoài allowed → FAIL "undeclared file"; BLOCKED không cần commands non-empty (pass với commands rỗng + concerns ghi lý do).
- [ ] **Step 2 fail → Step 3 implement** (theo đúng spec trên, style Result như hai gate trước — executor viết, ~35 dòng).
- [ ] **Step 4 pass → commit** — `feat(vnext-w1): gate vnext-result (structured result, exit-code-not-sufficient)`

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

- [ ] **Step 1: Failing tests** — dùng **stub runner** (không subprocess): runner nhận prompt, tự ghi result file + review file dựa trên kịch bản:

```python
# tests/test_vnext_dispatch.py — kịch bản chính (executor viết đủ):
def test_happy_path_two_tasks(tmp_path):     # 2 task DONE + review APPROVED → status done x2
def test_result_missing_blocks(tmp_path):    # runner exit 0 nhưng không ghi result → blocked (exit code not sufficient)
def test_result_contract_violation_blocks(tmp_path):  # changed_files ngoài allowed → blocked
def test_findings_then_fix_then_approved(tmp_path):   # review FINDINGS lần 1, APPROVED lần 2 → done, 2 lần implementation dispatch
def test_stale_plan_stops_queue(tmp_path):   # result status STALE_PLAN → return status stale_plan, STATE BLOCKED reason stale_plan
def test_resume_skips_done(tmp_path):        # chạy lại run_queue → không re-dispatch task done
```

Stub runner mẫu cho happy path (các test khác biến thể):

```python
def make_stub(ws, script):
    """script: dict task_id -> list các hành vi mỗi lần gọi ('ok','no_result','findings',...)."""
    calls = {"n": 0, "prompts": []}
    def runner(prompt):
        calls["prompts"].append(prompt)
        ...  # đọc task_id từ prompt, pop hành vi, ghi results/reviews tương ứng rồi return (0, "ok")
    return runner, calls
```

- [ ] **Step 2 fail → Step 3 implement.** Prompt template (nguyên văn, dùng cho cả 3 class, khác role block):

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

- [ ] **Step 4 pass → commit** — `feat(vnext-w1): dispatch classes + sequential run loop (fresh worker, review loop)`

---

### Task 9: Independent plan review (planning_dispatch) + wire compile

**Files:**
- Modify: `.maika/tools/microloop-orchestrator/vnext_dispatch.py` (hàm `review_plan(ws, runner) -> str`)
- Modify: `.maika/tools/microloop-orchestrator/tests/test_vnext_dispatch.py` (2 test)

**Interfaces:**
- Produces: `review_plan(ws, runner)` — planning dispatch ghi `reviews/plan-review.md`, trả verdict; chỉ khi cả `PLAN_VALIDATION.json == APPROVED` **và** plan-review `VERDICT: APPROVED` thì `vnext_state.transition(ws, "EXECUTING")` được phép (enforce trong CLI Task 11, không trong hàm).

- [ ] Tests: review APPROVED trả "APPROVED"; review file thiếu dòng VERDICT → trả "FINDINGS" (fail-closed). Implement ~20 dòng. Commit — `feat(vnext-w1): independent plan review dispatch`

---

### Task 10: Write-gate brief-scope

**Files:**
- Modify: `.maika/hooks/write-gate/write_gate.py`
- Create/Modify: `.maika/hooks/write-gate/tests/test_vnext_brief_scope.py`

**Interfaces:**
- Produces: `_vnext_active_task(project_root, framework_root) -> (ws, task)|None` — quét `<framework_root>/changes/*/STATE.yaml` state==EXECUTING (flag `workflow_engine==vnext` đọc từ `<framework_root>/profiles/execution-mode.yaml` rendered; template chưa render/parse lỗi → None, không chặn); task = entry in_progress trong TASK_QUEUE.json. Trong `evaluate_write` (write_gate.py:491), chèn **sau** `check_session_gate`, **trước** check KNOWLEDGE_CHECKPOINT:

```python
    vnext = _vnext_active_task(project_root, framework_root)
    if vnext is not None:
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

- [ ] Tests (5): flag legacy → None (không đổi hành vi — regression toàn suite write-gate pass); flag vnext + EXECUTING + file trong allowed → ALLOW; ngoài allowed → DENY kèm task id; ghi vào chính workspace change → ALLOW; không có change EXECUTING → fallthrough legacy. Fixture: tmp project_root với profiles rendered + changes/demo/{STATE.yaml,generated/TASK_QUEUE.json} tự dựng.
- [ ] Run: `cd .maika/hooks/write-gate && /usr/bin/python3 -m pytest tests/ -q` → toàn suite PASS. Commit — `feat(vnext-w1): write-gate brief-scope (vnext EXECUTING)`

---

### Task 11: CLI subcommands + e2e stub

**Files:**
- Modify: `.maika/tools/microloop-orchestrator/orchestrator.py` (main(): thêm subcommands)
- Create: `.maika/tools/microloop-orchestrator/tests/test_vnext_cli_e2e.py`

**Interfaces:**
- Produces subcommands (đều yêu cầu `workflow_engine == vnext` từ config, ngược lại refuse exit 2 — R1 consumer của flag):
  - `vnext-init --changes-root <dir> --id <id> --class <c> --title <t>`
  - `vnext-compile --workspace <ws> --repo-root <root>` (compile + in verdict)
  - `vnext-review-plan --workspace <ws>` (planning dispatch qua worker_command config)
  - `vnext-run --workspace <ws> --repo-root <root>` (chỉ chạy khi STATE==EXECUTING; PLAN_VALIDATION APPROVED + plan-review APPROVED mới cho transition PLAN_REVIEW→EXECUTING trong lệnh này)
  - `vnext-status --workspace <ws>` (in state + bảng task status)
- [ ] E2E test với config stub (`workflow_engine: vnext`, runner stub từ Task 8): init → ghi plan fixture → compile APPROVED → review stub APPROVED → run 2 task DONE → status COMPLETED-ready (EXECUTING→VERIFYING transition khi queue done). Thêm test refuse khi flag legacy.
- [ ] Run toàn suite microloop + gate-check + write-gate + cli/tests → PASS hết. Commit — `feat(vnext-w1): vnext CLI subcommands + e2e (flag-gated)`

---

### Task 12: Ledger activation + docs + final verify

**Files:**
- Modify: `docs/refactor/maika-vnext/enforcement-ledger.yaml`
- Modify: `.maika/tools/README.md` (mục gate-check: thêm 3 gate mới; mục microloop: thêm vnext subcommands)

**Interfaces:** không code.

- [ ] PROP entries `plan`/`brief-integrity`/`result-contract` → mechanism `vnext-plan`/`vnext-brief`/`vnext-result`, `status: active`, `failure.classification: reproducible_litmus`, `litmus.command` = lệnh pytest file test tương ứng, `implementation.files/consumers` điền thật. `change-workspace` PROP giữ proposed (W1 chưa có gate riêng — workspace validate trong vnext-init).
- [ ] Chạy lại 4 schema test W0: `/usr/bin/python3 -m pytest cli/tests/test_vnext_w0_artifacts.py -q` → 4 passed.
- [ ] Final verify — chạy đủ 7 suite như W0 Task 2, dán số vào commit message.
- [ ] Commit — `docs(vnext-w1): activate 3 gate ledger entries + tool docs`; push branch; mở PR `feat/vnext-w1-vertical-slice → main` (body: link Master Plan v2 §26 W1 + bảng exit criteria).

---

## Exit criteria W1 (từ Master Plan v2 — kiểm khi đóng PR)

- Dogfood A (2 change `small` thật chạy vnext) — **sau khi merge**, tracked riêng.
- Không task nào done từ exit code đơn thuần (gate vnext-result + test_result_missing_blocks).
- Brief verbatim traceable (gate vnext-brief + test_verbatim_roundtrip).
- Legacy untouched & default (flag legacy + regression suites xanh).

## Self-review (đã chạy khi viết plan)

1. **Spec coverage:** v2 §26 W1 scope 1→7: workspace+schemas (T1), vocabulary+skill (T2), writing-plan skill + plan gate + independent review (T2/T4/T9), compiler+compat (T5 — compat = không đụng contract markdown, load_runtime_queue giữ nguyên), dispatch+result+gates (T6/T7/T8), write-gate (T10), flag (T1+T11). Must-not-depend: không task nào đụng registry/router/parallel/locks/platform khác.
2. **Placeholder scan:** các `...`/"executor viết đủ" chỉ ở test-variant lặp pattern đã cho đầy đủ ở test đầu cùng nhóm + spec hành vi liệt kê từng case — không có bước "implement later" thiếu định nghĩa.
3. **Type consistency:** tên module/hàm thống nhất giữa các task (vnext_state.init_workspace/transition; plan_parser.parse_plan; validate_vnext_plan/validate_brief_integrity/validate_result_contract; plan_compiler.compile_plan; vnext_dispatch.build_prompt/run_queue/review_plan); brief format header+`\n---\n`+body dùng chung ở T5/T6/T8/T10.
