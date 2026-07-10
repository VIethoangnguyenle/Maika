# Maika vNext W0 — Baseline, Inventory, Ledger, Capability Matrix — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Thực thi Wave 0 của Master Plan v2 — baseline xanh có ghi nhận, inventory toàn bộ artifact/consumer, khởi tạo enforcement ledger + platform capability matrix (có validator cơ học), retro-dogfood classification, và đề xuất PR sửa R3.

**Architecture:** W0 là wave documentation + audit: mọi deliverable là file dưới `docs/refactor/maika-vnext/`, cộng đúng **một** module test mới (`cli/tests/test_vnext_w0_artifacts.py`) làm mechanical consumer cho 4 YAML artifact (thỏa R1 — consumer cùng PR). Không đổi behavior runtime nào.

**Tech Stack:** Python 3.11 (pytest, PyYAML — đều là dependency sẵn của `cli/`), git, grep.

## Global Constraints

- Nguồn thẩm quyền: `MAIKA_VNEXT_MASTER_REFACTOR_PLAN.md` (v2) §26 W0 + Design Spec Rev 2 (`docs/superpowers/specs/2026-07-10-vnext-plan-restructure-design.md`).
- **Không đổi behavior runtime.** Diff chỉ gồm: `docs/refactor/maika-vnext/*`, `docs/superpowers/plans/*` (file này), `cli/tests/test_vnext_w0_artifacts.py`, và (trên branch riêng) `DEVELOPMENT_RULES.md`.
- Pytest local chạy bằng `/usr/bin/python3 -m pytest` (`.venv` thiếu jsonschema — đã có tiền lệ; không thêm dependency mới, chỉ dùng `yaml` + assert thuần).
- **Chỉ `git add` đích danh từng file.** Không bao giờ `git add -A` (working tree có thể còn thay đổi ngoài phạm vi).
- Prose trong các doc deliverable viết tiếng Việt, identifier/kỹ thuật giữ tiếng Anh; YAML artifact dùng key tiếng Anh.
- Commit message theo convention repo: `docs(vnext-w0): ...` / `test(vnext-w0): ...`, kết bằng `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.
- Mọi claim "file X dòng Y" trong deliverable phải verify bằng lệnh trước khi ghi (R4/code-evidence tinh thần).

**Preconditions của toàn plan (kiểm ở Task 1, không tự xử lý):**

1. PR của branch `docs/vnext-plan-restructure` (chứa Master Plan v2) đã merge vào `main`.
2. Working tree sạch — đặc biệt 81 file `docs/superpowers/{plans,specs}/` đang bị xóa un-staged phải được user quyết (restore hoặc commit riêng) **trước** khi tạo branch W0.

---

### Task 1: Branch W0 + hồ sơ branch đang mở

**Files:**
- Create: `docs/refactor/maika-vnext/current-state-audit.md` (khung + §1 Branch inventory)

**Interfaces:**
- Produces: branch `refactor/maika-vnext`; file `current-state-audit.md` với heading `## 1. Branch inventory`, `## 2. Baseline test record`, `## 3. Inventory`, `## 4. Retro-classification dogfood`, `## 5. Exit criteria` (các task sau điền §2–§5).

- [ ] **Step 1: Kiểm preconditions**

```bash
git checkout main && git pull
git log --oneline -3          # phải thấy commit merge của docs/vnext-plan-restructure
git status --short             # phải RỖNG; nếu còn ' D docs/superpowers/...' → DỪNG, báo user
```

Expected: status rỗng; nếu không → status `BLOCKED`, reason `environment`, dừng plan.

- [ ] **Step 2: Tạo branch**

```bash
git checkout -b refactor/maika-vnext
```

- [ ] **Step 3: Liệt kê branch đang mở đụng vùng nhạy cảm W0**

```bash
git branch -a --no-merged main
for b in $(git branch --no-merged main --format='%(refname:short)'); do
  echo "== $b"; git log main..$b --name-only --format= | sort -u | \
    grep -E '\.maika/(tools/gate-check|tools/microloop-orchestrator|workflows|rules|knowledge)|cli/' | head -5
done
```

- [ ] **Step 4: Tạo khung audit doc và điền §1**

Tạo `docs/refactor/maika-vnext/current-state-audit.md`:

```markdown
# Maika vNext W0 — Current-State Audit

- **Ngày:** <YYYY-MM-DD>
- **Baseline commit:** <sha của main tại Step 1>

## 1. Branch inventory

| Branch | Đụng vùng | Quyết định (resolve / stack / ignore) | Lý do |
|---|---|---|---|
| <mỗi branch từ Step 3 một dòng; branch không đụng vùng nhạy cảm ghi "ignore"> |

## 2. Baseline test record

(Task 2 điền)

## 3. Inventory

(Task 3 điền)

## 4. Retro-classification dogfood

(Task 9 điền)

## 5. Exit criteria

(Task 10 điền)
```

Với mỗi branch đụng `gate-check`/`microloop`/`workflows`/`rules`/`knowledge`: đề xuất `resolve` (merge/đóng trước W1) hoặc `stack` (rebase lên refactor/maika-vnext), ghi lý do. Quyết định cuối do user duyệt ở Task 10.

- [ ] **Step 5: Commit**

```bash
git add docs/refactor/maika-vnext/current-state-audit.md
git commit -m "docs(vnext-w0): audit skeleton + branch inventory

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: Baseline test record — chạy đủ 7 suite

**Files:**
- Modify: `docs/refactor/maika-vnext/current-state-audit.md` (§2)

**Interfaces:**
- Consumes: khung audit từ Task 1.
- Produces: §2 với bảng 7 suite × (lệnh, passed/failed/skipped, thời gian).

- [ ] **Step 1: Chạy từng suite, ghi kết quả nguyên văn dòng tổng kết**

```bash
/usr/bin/python3 -m pytest cli/tests/ -q --tb=no | tail -2
/usr/bin/python3 -m pytest .maika/tools/gate-check/tests/ -q --tb=no | tail -2
/usr/bin/python3 -m pytest .maika/tools/microloop-orchestrator/tests/ -q --tb=no | tail -2
/usr/bin/python3 -m pytest .maika/hooks/write-gate/tests/ -q --tb=no | tail -2
/usr/bin/python3 -m pytest .maika/tools/knowledge-index/tests/ -q --tb=no | tail -2
/usr/bin/python3 -m pytest .maika/tools/rule-projector/tests/ -q --tb=no | tail -2
/usr/bin/python3 -m pytest .maika/tools/skill-lint/tests/ -q --tb=no | tail -2
```

Expected: mỗi suite in `N passed` (0 failed). **Không tin dòng tóm tắt qua proxy** — đọc dòng cuối pytest thật.

- [ ] **Step 2: Điền §2**

```markdown
## 2. Baseline test record

Baseline commit: `<sha>` — chạy ngày <YYYY-MM-DD> bằng /usr/bin/python3.

| Suite | Lệnh | Kết quả |
|---|---|---|
| cli | `pytest cli/tests/ -q` | `<nguyên văn, vd "142 passed in 3.2s">` |
| gate-check | ... | ... |
| microloop-orchestrator | ... | ... |
| write-gate | ... | ... |
| knowledge-index | ... | ... |
| rule-projector | ... | ... |
| skill-lint | ... | ... |

Ghi chú CI: `.github/workflows/ci.yml` hiện chỉ chạy `cli/tests/` — 6 suite còn lại chạy tay (khớp nhận định v2 §28).
```

Nếu bất kỳ suite nào fail → DỪNG (v2: "preserve a green baseline"), báo user với output.

- [ ] **Step 3: Commit**

```bash
git add docs/refactor/maika-vnext/current-state-audit.md
git commit -m "docs(vnext-w0): baseline test record (7 suites)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: Inventory §3 — workflows/skills/rules/procedures/tools/hooks/templates/manifest/adapters

**Files:**
- Modify: `docs/refactor/maika-vnext/current-state-audit.md` (§3)

**Interfaces:**
- Produces: §3 gồm 9 tiểu mục, mỗi dòng inventory: đường dẫn + 1 câu mô tả vai trò + cột "vNext direction" (`retain | migrate | supersede | delete-candidate`).

- [ ] **Step 1: Thu thập danh sách bằng lệnh (không chép tay từ trí nhớ)**

```bash
ls .maika/workflows/                                  # 9 file (task.md 36K là trọng tâm)
ls .maika/skills/                                     # 14 skill dir + skill-index.yaml
ls .maika/rules/                                      # RULES.md + rules-{exec,flow,guard,knowledge,tool}.md
ls .maika/procedures/
ls .maika/tools/                                      # 7 tool
ls .maika/hooks/                                      # antigravity/ claude-code/ codex/ write-gate/
find .maika/knowledge/templates -maxdepth 2 -type f | head -40
grep -c '' cli/plugin-manifest.yaml                   # đếm dòng manifest để tham chiếu
ls cli/platforms/                                     # 5 adapter + __init__.py registry
```

- [ ] **Step 2: Kiểm R2 — mọi adapter nằm trong registry**

```bash
grep -n 'PLATFORMS' cli/platforms/__init__.py
ls cli/platforms/*.py | grep -v __init__
```

Expected: mọi file `cli/platforms/*.py` (trừ `base.py`, `__init__.py`) xuất hiện trong dict `PLATFORMS`. Lệch → ghi thành finding trong §3 (KHÔNG tự xóa file — chỉ ghi nhận, theo Surgical Changes).

- [ ] **Step 3: Điền §3 theo khung**

```markdown
## 3. Inventory

### 3.1 Workflows (.maika/workflows/)
| File | Vai trò | vNext direction |
|---|---|---|
| task.md | workflow chính, OpenSpec lifecycle | migrate (W6) |
| ... (đủ 9 file) |

### 3.2 Skills (.maika/skills/) — chi tiết phân loại ở skill-migration-map.yaml (Task 6)
### 3.3 Rules (.maika/rules/)
### 3.4 Procedures (.maika/procedures/)
### 3.5 Tools (.maika/tools/)
### 3.6 Hooks (.maika/hooks/)
### 3.7 Templates (.maika/knowledge/templates/)
### 3.8 CLI manifest (cli/plugin-manifest.yaml)
### 3.9 Platform adapters (cli/platforms/) + kết quả kiểm R2
```

Mỗi tiểu mục: bảng đủ mọi entry thật từ Step 1. Không được bỏ sót file nào (`ls` là nguồn, không phải trí nhớ).

- [ ] **Step 4: Commit**

```bash
git add docs/refactor/maika-vnext/current-state-audit.md
git commit -m "docs(vnext-w0): full framework inventory (9 areas + R2 check)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: Test module cho 4 YAML artifact (viết TRƯỚC — TDD cho Task 5–8)

**Files:**
- Create: `cli/tests/test_vnext_w0_artifacts.py`

**Interfaces:**
- Produces: 4 test function mà Task 5–8 phải làm pass:
  - `test_consumer_map_schema()` — đọc `docs/refactor/maika-vnext/artifact-consumer-map.yaml`
  - `test_skill_migration_map_schema()` — đọc `docs/refactor/maika-vnext/skill-migration-map.yaml`
  - `test_enforcement_ledger_schema()` — đọc `docs/refactor/maika-vnext/enforcement-ledger.yaml`
  - `test_capability_matrix_schema()` — đọc `docs/refactor/maika-vnext/platform-capability-matrix.yaml`
- Đây là **mechanical consumer** (R1) của cả 4 artifact, chạy trong CI (`cli/tests/`).

- [ ] **Step 1: Viết test (nguyên văn)**

```python
"""Schema validators for vNext W0 refactor artifacts (mechanical consumer, R1).

Master Plan v2 §5 (ledger), §26 W0 (matrix, maps). These tests ARE the
consumers that make the four YAML deliverables legal to exist.
"""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "docs" / "refactor" / "maika-vnext"

LEDGER_STATUSES = {"proposed", "active", "deferred", "superseded", "removed"}
LEDGER_CLASSIFICATIONS = {
    "observed_failure",
    "reproducible_litmus",
    "external_requirement",
    "safety_boundary",
}
MIGRATION_CLASSES = {"retain", "merge", "rewrite", "deprecate", "delete"}
PLATFORMS = {"claude-code", "codex", "antigravity"}


def _load(name: str) -> dict:
    path = ART / name
    assert path.exists(), f"missing W0 deliverable: {path}"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_consumer_map_schema():
    data = _load("artifact-consumer-map.yaml")
    assert data["version"] == 1
    artifacts = data["artifacts"]
    assert artifacts, "consumer map must not be empty"
    for name, entry in artifacts.items():
        assert entry.get("producers"), f"{name}: producers required"
        assert entry.get("consumers") is not None, f"{name}: consumers key required"
        for ref in entry["producers"] + (entry["consumers"] or []):
            assert ref.get("path"), f"{name}: every ref needs a path"


def test_skill_migration_map_schema():
    data = _load("skill-migration-map.yaml")
    assert data["version"] == 1
    entries = {e["skill"]: e for e in data["skills"]}
    on_disk = {
        p.name
        for p in (ROOT / ".maika" / "skills").iterdir()
        if p.is_dir()
    }
    assert set(entries) == on_disk, (
        f"map vs disk mismatch: only-in-map={set(entries) - on_disk} "
        f"only-on-disk={on_disk - set(entries)}"
    )
    for name, e in entries.items():
        assert e["classification"] in MIGRATION_CLASSES, name
        if e["classification"] in {"deprecate", "delete"}:
            assert "consumers" in e, f"{name}: deletion requires consumer evidence"


def test_enforcement_ledger_schema():
    data = _load("enforcement-ledger.yaml")
    assert data["version"] == 1
    ids = [e["id"] for e in data["entries"]]
    assert len(ids) == len(set(ids)), "duplicate ledger ids"
    for e in data["entries"]:
        assert e["status"] in LEDGER_STATUSES, e["id"]
        assert e.get("mechanism"), e["id"]
        assert e.get("type") in {"gate", "hook", "validator"}, e["id"]
        if e["status"] == "active":
            cls = e["failure"]["classification"]
            assert cls in LEDGER_CLASSIFICATIONS, e["id"]
            assert e["failure"].get("summary"), e["id"]
            assert e.get("implementation", {}).get("files"), e["id"]
        if e["status"] == "deferred":
            assert e.get("activation_condition"), (
                f"{e['id']}: deferred entries need an activation condition (v2 §5)"
            )
        if e["status"] == "proposed":
            assert e.get("scheduled_wave"), f"{e['id']}: proposed needs scheduled_wave"


def test_capability_matrix_schema():
    data = _load("platform-capability-matrix.yaml")
    assert data["version"] == 1
    assert set(data["platforms"]) == PLATFORMS
    for platform, mechanisms in data["platforms"].items():
        assert mechanisms, f"{platform}: at least one mechanism row"
        for mech, row in mechanisms.items():
            assert "supported" in row, f"{platform}.{mech}"
            assert row.get("evidence"), (
                f"{platform}.{mech}: R4 requires file:line or command evidence"
            )
            assert row.get("verified_at"), f"{platform}.{mech}: verified_at date"
```

- [ ] **Step 2: Chạy để thấy fail đúng kiểu**

```bash
/usr/bin/python3 -m pytest cli/tests/test_vnext_w0_artifacts.py -v
```

Expected: 4 FAILED, đều là `AssertionError: missing W0 deliverable: .../artifact-consumer-map.yaml` (v.v.).

- [ ] **Step 3: Commit (test đỏ có chủ đích — đi cùng artifact ở các task sau trong cùng PR)**

```bash
git add cli/tests/test_vnext_w0_artifacts.py
git commit -m "test(vnext-w0): schema validators for 4 W0 artifacts (red)

Mechanical consumers per R1; turn green in subsequent commits.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 5: artifact-consumer-map.yaml

**Files:**
- Create: `docs/refactor/maika-vnext/artifact-consumer-map.yaml`

**Interfaces:**
- Consumes: schema từ `test_consumer_map_schema` (Task 4).
- Produces: map mọi workflow artifact → producers/consumers có `path` (+ `note` tự do).

- [ ] **Step 1: Liệt kê artifact runtime cần map**

Tối thiểu phải có các artifact sau (nguồn: `.maika/tools/microloop-orchestrator/README.md`, `.maika/tools/README.md`, `workflows/task.md`):

```text
TASK_QUEUE.md  TASK_HANDOFF.md  TASK_RESULT.md  PARENT_BRAIN.md
EXTRACTION_INPUT.md  EXTRACTION_REPORT.md  ACTIVITY_LOG.jsonl
knowledge-index.yaml  skill-index.yaml  author-dna.yaml  conventions.yaml
execution-mode.yaml  resolved-config.yaml  rules.json  checkstyle.generated.xml
```

Với mỗi artifact, tìm producer/consumer bằng:

```bash
grep -rn 'TASK_QUEUE' .maika cli --include='*.py' --include='*.md' -l
# lặp cho từng tên artifact
```

- [ ] **Step 2: Viết YAML theo schema**

```yaml
version: 1

artifacts:
  TASK_QUEUE.md:
    producers:
      - path: .maika/tools/microloop-orchestrator/orchestrator.py
        note: initialize_runtime_queue
    consumers:
      - path: .maika/tools/microloop-orchestrator/orchestrator.py
        note: update_task_status / resume
      - path: cli/dashboard/
        note: dashboard đọc queue
  # ... một entry cho MỌI artifact ở Step 1; consumer rỗng thì ghi [] kèm note
  # "no mechanical consumer found" — đó chính là finding cho migration map
```

- [ ] **Step 3: Chạy test**

```bash
/usr/bin/python3 -m pytest cli/tests/test_vnext_w0_artifacts.py::test_consumer_map_schema -v
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add docs/refactor/maika-vnext/artifact-consumer-map.yaml
git commit -m "docs(vnext-w0): artifact producer->consumer map

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---### Task 6: skill-migration-map.yaml + tool-coupling-report.md

**Files:**
- Create: `docs/refactor/maika-vnext/skill-migration-map.yaml`
- Create: `docs/refactor/maika-vnext/tool-coupling-report.md`

**Interfaces:**
- Consumes: `test_skill_migration_map_schema` (Task 4); v2 §25 expected direction.
- Produces: phân loại đủ 14 skill; report OpenSpec + concrete-MCP coupling có `file:line`.

- [ ] **Step 1: Xây migration map từ disk + consumer thật**

```bash
ls -d .maika/skills/*/            # 14 dir — map phải khớp 1-1 (test enforce)
grep -rn '<tên-skill>' .maika/workflows .maika/rules .maika/procedures cli/plugin-manifest.yaml -l
# lặp cho từng skill để điền consumers
```

```yaml
version: 1

skills:
  - skill: codebase-explorer
    classification: rewrite          # → grounding-explorer (v2 §25)
    target: grounding-explorer
    consumers:
      - path: .maika/workflows/task.md
  - skill: openspec-propose
    classification: delete           # sau W6
    consumers:
      - path: .maika/workflows/task.md
        note: gỡ ở W6 cutover
  # ... đủ 14 skill; classification theo v2 §25, lệch phải ghi note lý do
```

- [ ] **Step 2: Chạy test**

```bash
/usr/bin/python3 -m pytest cli/tests/test_vnext_w0_artifacts.py::test_skill_migration_map_schema -v
```

Expected: PASS (map khớp 1-1 với disk).

- [ ] **Step 3: Quét coupling cho report**

```bash
# OpenSpec dependencies
grep -rn -i 'openspec' .maika cli README.md --include='*.md' --include='*.py' --include='*.yaml' | grep -v docs/superpowers | grep -v archive
# Concrete MCP names ngoài vùng cho phép (adapters/tool docs/profiles)
grep -rn -E 'mcp__|codebase-memory|codebase_memory|understand.anything|agent-memory|socraticode' \
  .maika/workflows .maika/skills .maika/rules .maika/procedures --include='*.md'
```

- [ ] **Step 4: Viết tool-coupling-report.md**

```markdown
# W0 — Tool Coupling Report

## 1. OpenSpec dependencies (phải gỡ ở W6)
| File:line | Trích dẫn | Ghi chú |
|---|---|---|
| <mọi hit từ Step 3, nhóm theo file> |

## 2. Concrete MCP names trong canonical docs (phải capability-hóa ở W1–W4)
| File:line | Provider name | Vùng đích (mappings/adapter/tool-doc) |
|---|---|---|

## 3. Kết luận
- Số điểm coupling OpenSpec: N
- Số canonical doc chứa provider name: M
- Input cho W1 (vocabulary) và W6 (cutover).
```

- [ ] **Step 5: Commit**

```bash
git add docs/refactor/maika-vnext/skill-migration-map.yaml docs/refactor/maika-vnext/tool-coupling-report.md
git commit -m "docs(vnext-w0): skill migration map + tool coupling report

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 7: enforcement-ledger.yaml

**Files:**
- Create: `docs/refactor/maika-vnext/enforcement-ledger.yaml`

**Interfaces:**
- Consumes: `test_enforcement_ledger_schema` (Task 4); v2 §5 schema; traceability doc §Deferred.
- Produces: ledger đủ 3 nhóm entry: `active` (mọi cơ chế đang chạy), `proposed` (9 lifecycle gates v2), `deferred` (cơ chế bị hoãn + activation condition).

- [ ] **Step 1: Liệt kê cơ chế đang chạy**

```bash
grep -n 'knowledge-checkpoint\|handoff-slice\|implementation-context\|phase-chain\|mcp-status\|memory-recall\|teaching-moment\|archive-ready\|ac-coverage\|integration-coverage\|code-evidence' .maika/tools/gate-check/cli.py
ls .maika/hooks/write-gate/ .maika/tools/skill-lint/ .maika/tools/rule-projector/
```

- [ ] **Step 2: Viết ledger — seed entries nguyên văn dưới đây, phần còn lại theo cùng schema**

```yaml
version: 1

entries:
  # ---- active: cơ chế đang chạy ----
  - id: ENF-001
    mechanism: code-evidence
    type: gate
    status: active
    failure:
      classification: observed_failure
      reference: docs/superpowers/specs/2026-07-08-code-evidence-gate-design.md
      summary: Agent bịa/khai khống grep evidence thay vì probe node thật (PR #37 lineage).
    implementation:
      files: [.maika/tools/gate-check/gates.py]
      consumers: [.maika/workflows/task.md, .maika/rules/rules-tool.md]
    scope: {change_classes: [standard, architectural]}
    reviewed_at: 2026-07-10

  - id: ENF-002
    mechanism: write-gate
    type: hook
    status: active
    failure:
      classification: safety_boundary
      reference: .maika/hooks/write-gate/write_gate.py
      summary: >-
        Write boundary — đủ điều kiện theo ngoại lệ v2 §5. Bổ sung:
        observed bypass trên Antigravity IDE 1.23.2 (hooks không load,
        đã fix bằng Antigravity 2.0.1 + Tools v4.3.5).
    implementation:
      files: [.maika/hooks/write-gate/write_gate.py]
      consumers: [.maika/hooks/claude-code/, .maika/hooks/codex/, .maika/hooks/antigravity/]
    scope: {change_classes: [trivial, small, standard, architectural]}
    reviewed_at: 2026-07-10

  - id: ENF-003
    mechanism: skill-lint
    type: validator
    status: active
    failure:
      classification: observed_failure
      reference: .maika/tools/skill-lint/tests/test_sp3_doctrine_litmus.py
      summary: Skill migration kiểu rewrite âm thầm làm rơi guidance; lint schema bắt cấu trúc.
    implementation:
      files: [.maika/tools/skill-lint/validate_skills.py]
      consumers: [.maika/skills/skill-index.yaml]
    scope: {change_classes: [standard, architectural]}
    reviewed_at: 2026-07-10

  # ... một entry active cho TỪNG gate còn lại trong gate-check cli.py (Step 1),
  # rule-projector (classification: reproducible_litmus, reference: tests của nó),
  # cbm-doctrine-guard hook (observed_failure: cbm cài rule đè UA-first doctrine).

  # ---- proposed: 9 lifecycle gates của v2 §22 ----
  - id: PROP-001
    mechanism: change-workspace
    type: gate
    status: proposed
    scheduled_wave: W1
    reviewed_at: 2026-07-10
  # ... PROP-002..009 cho: exploration-evidence (W2), spec (W2), plan (W1),
  # brief-integrity (W1), result-contract (W1), task-review (W2),
  # final-review (W3), archive-readiness (W6) — scheduled_wave theo v2 §26.

  # ---- deferred: hoãn có điều kiện kích hoạt (traceability doc §Deferred) ----
  - id: DEF-001
    mechanism: parallel-execution-file-locks
    type: gate
    status: deferred
    activation_condition: >-
      Wall-clock bottleneck ghi nhận ở >=2 dogfood changes trong ledger.
    reviewed_at: 2026-07-10

  - id: DEF-002
    mechanism: claim-level-evidence-hash
    type: validator
    status: deferred
    activation_condition: >-
      Một staleness false negative mà file-level hash bỏ lọt, có ghi nhận.
    reviewed_at: 2026-07-10

  - id: DEF-003
    mechanism: routing-cost-risk-sensitivity
    type: validator
    status: deferred
    activation_condition: Observed misrouting failure do thiếu dimension.
    reviewed_at: 2026-07-10

  - id: DEF-004
    mechanism: dashboard-expansion
    type: validator
    status: deferred
    activation_condition: Dogfood ghi nhận thiếu hụt observability cụ thể.
    reviewed_at: 2026-07-10
```

- [ ] **Step 3: Chạy test**

```bash
/usr/bin/python3 -m pytest cli/tests/test_vnext_w0_artifacts.py::test_enforcement_ledger_schema -v
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add docs/refactor/maika-vnext/enforcement-ledger.yaml
git commit -m "docs(vnext-w0): enforcement ledger (active/proposed/deferred)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 8: platform-capability-matrix.yaml (R4)

**Files:**
- Create: `docs/refactor/maika-vnext/platform-capability-matrix.yaml`

**Interfaces:**
- Consumes: `test_capability_matrix_schema` (Task 4).
- Produces: matrix 3 platform × ≥4 mechanism, mỗi row có evidence thật đã verify.

- [ ] **Step 1: Thu thập evidence từng row — VERIFY, không chép trí nhớ**

```bash
grep -n 'subagent\|fresh-session\|inline-reload' .maika/profiles/execution-mode.yaml
ls .maika/hooks/claude-code/ .maika/hooks/codex/ .maika/hooks/antigravity/
cat .maika/hooks/antigravity/hooks.json | head -20     # hook events Antigravity
grep -rn 'model' cli/platforms/claude_code.py cli/platforms/codex.py cli/platforms/antigravity.py | head
agy --help 2>&1 | grep -i 'model' ; codex exec --help 2>&1 | grep -i 'model'
```

Mechanism bắt buộc mỗi platform: `subagent_spawn`, `fresh_session`, `hook_pre_tool_use`, `hook_session_start`, `model_selection`.

- [ ] **Step 2: Viết matrix**

```yaml
version: 1

platforms:
  claude-code:
    subagent_spawn:
      supported: true
      evidence: ".maika/profiles/execution-mode.yaml:<line> — tier `subagent` (Claude); Task tool"
      verified_at: 2026-07-10
    fresh_session:
      supported: true
      evidence: "<command hoặc file:line>"
      verified_at: 2026-07-10
    hook_pre_tool_use:
      supported: true
      evidence: ".maika/hooks/claude-code/<file>:<line>"
      verified_at: 2026-07-10
    hook_session_start:
      supported: true
      evidence: "<file:line>"
      verified_at: 2026-07-10
    model_selection:
      supported: true
      evidence: "<file:line hoặc output lệnh>"
      verified_at: 2026-07-10
  codex:
    # đủ 5 mechanism; supported=false vẫn phải có evidence chứng minh KHÔNG có
  antigravity:
    # đủ 5 mechanism; ghi rõ ràng buộc version (hooks chỉ fire từ 2.0.1 + Tools v4.3.5)
```

Row nào không xác minh nổi → `supported: false` + evidence là lệnh/lý do đã thử. **Không được để trống evidence** (test enforce).

- [ ] **Step 3: Chạy test — toàn bộ module phải xanh**

```bash
/usr/bin/python3 -m pytest cli/tests/test_vnext_w0_artifacts.py -v
```

Expected: 4 passed.

- [ ] **Step 4: Commit**

```bash
git add docs/refactor/maika-vnext/platform-capability-matrix.yaml
git commit -m "docs(vnext-w0): R4 platform capability matrix (verified evidence)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 9: Retro-classification dogfood (§4 audit)

**Files:**
- Modify: `docs/refactor/maika-vnext/current-state-audit.md` (§4)

**Interfaces:**
- Consumes: v2 §6 classification rules; lịch sử merge của `main`.
- Produces: §4 — 3 change gần nhất được phân loại hồi tố + misfit findings.

- [ ] **Step 1: Lấy 3 merge gần nhất**

```bash
git log --merges --oneline -3 main
git show --stat <sha1> | head -30   # lặp cho 3 sha, đếm file/module đụng
```

- [ ] **Step 2: Phân loại từng change theo v2 §6 và điền §4**

```markdown
## 4. Retro-classification dogfood

| PR / merge | Files đụng | Class theo §6 | Lý do | Misfit? |
|---|---|---|---|---|
| #37 code-evidence gate | <n files: gate-check, rules, docs> | <class> | <chiếu định nghĩa §6> | <có/không + mô tả> |
| ... 2 merge trước đó |

### Misfit findings
- <mỗi điểm luật §6 phân loại sai/mơ hồ với change thật — đây là input sửa §6 ở W1>
- Nếu không có misfit: ghi rõ "0 misfit — §6 phủ được 3 change gần nhất".
```

- [ ] **Step 3: Commit**

```bash
git add docs/refactor/maika-vnext/current-state-audit.md
git commit -m "docs(vnext-w0): retro-classification dogfood (3 merged changes)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 10: Exit criteria + PR W0

**Files:**
- Modify: `docs/refactor/maika-vnext/current-state-audit.md` (§5)

**Interfaces:**
- Consumes: mọi deliverable Task 1–9.
- Produces: §5 checklist + branch được push + PR mở, chờ user duyệt audit.

- [ ] **Step 1: Chạy lại toàn bộ verify**

```bash
/usr/bin/python3 -m pytest cli/tests/test_vnext_w0_artifacts.py -v      # 4 passed
/usr/bin/python3 -m pytest cli/tests/ -q --tb=no | tail -1              # suite cli vẫn xanh
git status --short                                                       # chỉ file trong phạm vi plan
```

- [ ] **Step 2: Điền §5**

```markdown
## 5. Exit criteria (v2 §26 W0)

- [x] Baseline commit recorded: `<sha>` (§2)
- [x] Conflicting branches resolved/stacked: quyết định tại §1 (chờ user duyệt)
- [x] Every planned deletion has known consumers: skill-migration-map.yaml + artifact-consumer-map.yaml
- [ ] Current-state audit approved: **chờ user**
- [x] Ledger + matrix exist and validate: `pytest cli/tests/test_vnext_w0_artifacts.py` → 4 passed
```

- [ ] **Step 3: Commit + push + PR**

```bash
git add docs/refactor/maika-vnext/current-state-audit.md
git commit -m "docs(vnext-w0): exit criteria checklist

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
git push -u origin refactor/maika-vnext
```

Tạo PR `refactor/maika-vnext → main`, title `docs(vnext-w0): baseline, inventory, ledger, capability matrix`, body tóm tắt 6 deliverable + link Master Plan v2 §26 W0, kết bằng footer chuẩn. (Máy không có `gh` — dùng GitHub API với `git credential fill` như tiền lệ.)

Expected: PR mở; user duyệt audit → W0 exit.

---

### Task 11: R3 amendment — branch + PR riêng (R6)

**Files:**
- Modify: `.maika/DEVELOPMENT_RULES.md` (trên branch riêng `docs/r3-amendment`, KHÔNG nằm trong PR W0)

**Interfaces:**
- Consumes: v2 §5 note về ngoại lệ R3.
- Produces: PR độc lập sửa R3, để user quyết tách biệt.

- [ ] **Step 1: Tạo branch từ main**

```bash
git checkout main && git checkout -b docs/r3-amendment
```

- [ ] **Step 2: Sửa R3 trong `.maika/DEVELOPMENT_RULES.md`**

Thay đoạn (giữ nguyên phần "Vì sao"/"Cách kiểm" hiện có, chỉ sửa câu luật và bổ sung cách kiểm):

```markdown
## R3 — Xây cho lỗi đã quan sát, không cho lỗi giả định

Enforcement mới (gate / hook / rule / validator) chỉ được thêm khi có **một bypass đã log**, **một litmus tái hiện được** lỗi đó, **một yêu cầu bên ngoài bắt buộc** (external requirement), hoặc khi nó **bảo vệ safety / destructive-action boundary** (write boundary không chờ sự cố). Không dựng cơ chế cho rủi ro chưa từng thấy fail.

- **Vì sao:** (giữ nguyên đoạn hiện có) — bổ sung: hai ngoại lệ external_requirement/safety_boundary chuẩn hóa theo enforcement ledger của vNext (Master Plan v2 §5); safety boundary có tiền lệ write-gate.
- **Cách kiểm:** PR thêm enforcement phải link tới entry trong `docs/refactor/maika-vnext/enforcement-ledger.yaml` có classification hợp lệ. Không có ⇒ defer.
```

- [ ] **Step 3: Chạy suite liên quan (không có — đây là doc), kiểm diff chỉ đúng 1 file**

```bash
git diff --stat            # đúng 1 file: .maika/DEVELOPMENT_RULES.md
```

- [ ] **Step 4: Commit + push + PR riêng**

```bash
git add .maika/DEVELOPMENT_RULES.md
git commit -m "docs(rules): R3 — thêm external_requirement + safety_boundary (vNext ledger)

Chuẩn hóa 2 ngoại lệ theo Master Plan v2 §5; đóng dấu thay đổi theo R6.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
git push -u origin docs/r3-amendment
```

Tạo PR `docs/r3-amendment → main` (độc lập với PR W0).

---

## Self-review (đã chạy khi viết plan)

1. **Spec coverage** — v2 §26 W0 scope 1→9: branch (T1), baseline (T2), inventory (T3), consumer map (T5), OpenSpec deps (T6), MCP names (T6), ledger (T7), matrix (T8), R3 amendment (T11); dogfood checkpoint (T9); exit criteria + deliverables (T10). Đủ.
2. **Placeholder scan** — các chỗ `<...>` đều là giá trị chỉ biết lúc thực thi (sha, số passed, hit grep) kèm lệnh sinh ra chúng và acceptance check; không có TBD/"handle later".
3. **Type consistency** — 4 tên file YAML và 4 tên test function nhất quán giữa Task 4 và Task 5–8; schema fields (`activation_condition`, `scheduled_wave`, `verified_at`) khớp giữa test và YAML mẫu.
