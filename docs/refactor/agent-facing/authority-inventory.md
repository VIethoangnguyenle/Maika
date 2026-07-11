# PR 1 — Authority inventory, rule contradictions, skill overlaps

> Deliverable của PR 1 (agent-facing refactor). Registry cơ học:
> `.maika/config/artifact-authority.yaml` (validator: `maika content validate-authority`).
> Baseline: `master-v2` @ `c036175`. Không có behavior change trong PR này.

## 1. Authority map (đã chốt trong registry)

Mỗi decision có đúng MỘT source — xem `artifact-authority.yaml`. Điểm đáng chú ý:

- `bootstrap_report` hiện ở `knowledge/active/BOOTSTRAP_REPORT.yaml` (`cli/commands/bootstrap.py:70`)
  — sẽ dời sang `runtime/` + tách agent-ack ở PR 7.
- `dispatch_log` (`generated/DISPATCH_LOG.jsonl`, `vnext_dispatch.py:112`) là transparency
  authority hiện hành — thay `AGENT_TRANSPARENCY.md`.
- `TOKEN_LOG.md` deprecated không có successor (RUNTIME_METRICS.yaml thuộc PR 9, evidence-gated).

## 2. Duplicate authority / legacy path inventory

Legacy `knowledge/active/*` vẫn được tham chiếu trên normal path tại:

| File | Vai trò tham chiếu |
|---|---|
| `.maika/rules/rules-flow.md` | R-Spec-1 đọc REQUIREMENT làm spec input |
| `.maika/procedures/bootstrap.md` | resume/context flow đọc active memory |
| `.maika/procedures/context-compressor.md` | TOKEN_LOG làm overflow signal |
| `.maika/procedures/decision-gate.md` | gate context tham chiếu active |
| `cli/commands/bootstrap.py:70` | ghi BOOTSTRAP_REPORT vào knowledge/active |
| `cli/commands/task.py`, `cli/commands/lifecycle.py` | đường active-memory legacy |
| `cli/scaffold.py`, `cli/assets.py`, `cli/install/ownership.py` | scaffold/classify active tree |
| `cli/dashboard/reader.py` | đọc TOKEN_LOG/active artifacts |
| `.maika/knowledge/templates/TOKEN_LOG.tpl.md`, `ARCHIVE_META.tpl.md`, `knowledge/README.md` | template/docs legacy |

→ Xử lý dần ở PR 6 (task-memory migration) + PR 7 (bootstrap) + PR 13 (rules). PR 6 sẽ
thêm `legacy-reference-scan` cơ học từ danh sách `deprecated` trong registry.

## 3. Rule contradiction report

1. **Fixed flow vs adaptive (nghiêm trọng nhất):** `rules-flow.md:17` [CRITICAL] R-Flow-2
   "Chuỗi state cố định: start → explore → spec → plan → review → apply" mâu thuẫn
   `workflows/task.md:11-16` (trivial/small không có spec/plan). Agent bị compact sẽ ưu
   tiên [CRITICAL] → full ceremony cho task nhỏ. **Fix: PR 3** (router thành authority,
   R-Flow-2 viết lại trỏ router).
2. **Assumption-and-continue vs material-evidence-block:** `rules-flow.md:38` R-Flow-4
   ("ghi Assumption, không loop") không phân loại risk; mâu thuẫn các rule yêu cầu block
   khi thiếu material evidence (grounding/persistence). **Fix: PR 11** (assumption taxonomy).
3. **Teaching-moment write ownership:** `rules-knowledge.md` cho phép ghi ngay Author
   DNA/conventions khi có user correction; role boundary lại nói knowledge promotion thuộc
   curator sau VERIFIED. **Fix: PR 12** (candidate-first).
4. **`rules_loaded` semantics:** `cli/commands/bootstrap.py:47-49` đặt tên `rules_loaded`
   cho fact "file tồn tại". **Fix: PR 7** (`rules_present` + agent ack tách riêng).

## 4. Skill overlap report

| Overlap | Chi tiết | Xử lý |
|---|---|---|
| `knowledge-curator` 4 mode | retrieve/record/reconcile/curate trong một skill — mode `reconcile` giẫm `architecture-reconciler`; `curate` cần post-VERIFIED role | PR 12 tách retriever/recorder/promoter |
| `intent-analysis` vs `grounding-explorer` | cả hai đều sinh/own QUERY_PLAN.yaml (skill-index mô tả intent-analysis "sinh QUERY_PLAN.yaml"; router giao exploration/QUERY_PLAN.yaml cho grounding) | PR 3 route: intent sinh seed, grounding own file trong exploration/ |
| Lightweight gap | Không skill nào own trivial/small apply; `executing-task` đòi TASK_QUEUE/brief — trivial/small không có | PR 5 `lightweight-change` |
| `reviewing-change` không được dispatch | task.md có final review nhưng không command/action nào gọi nó (task.py COMMAND_MAP không có final-review) | PR 3 action `final-review` (amendment A3) |

## 5. Critical paths — không còn unknown

Toàn bộ artifact active được phân loại vào registry (13 decisions) hoặc deprecated (5
paths). Các path generated còn lại (`generated/PLAN_VALIDATION.json`, `PLAN_MANIFEST.json`,
`CONTEXT_PACKAGE.*.yaml`, `briefs/`, `results/`, `reviews/`) là derived artifacts của các
authority trên (producer: microloop-orchestrator), không phải authority độc lập — không
đưa vào registry để giữ "one authority per decision" (chúng theo `task_queue`/
`implementation_plan`/`verification`).
