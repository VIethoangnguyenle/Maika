# Kế hoạch thực hiện: Agent-Facing Architecture Refactor

> SSOT nội dung: `upgrade/maika-agent-facing-architecture-refactor-plan.md` (16 PR, §26).
> Doc này quyết định **thứ tự thi công, amendment bắt buộc, và evidence-gate** cho từng PR —
> không lặp lại nội dung SSOT.
> Branch: `master-v2`, làm trong working tree. Baseline HEAD `0cdea05` (merge PR #49).

## 1. Kết quả thẩm định plan (2026-07-12)

Cả 11 problem statement (§2) đã được verify trực tiếp trên code — plan chẩn đoán đúng:

| Claim | Bằng chứng |
|---|---|
| 2.1 Hai task-memory model | `knowledge/active` còn được tham chiếu ở 13 file (rules-flow, bootstrap, task.py, lifecycle.py…) song song `changes/<id>` |
| 2.2 Fixed-flow mâu thuẫn adaptive | `rules/rules-flow.md:17` [CRITICAL] chuỗi cố định vs `workflows/task.md:11-16` adaptive |
| 2.3 Routing bằng prose | `skills/skill-index.yaml` chỉ có name/version/description |
| 2.4 Lightweight thiếu skill contract | Không có skill `lightweight-change`; 16 skill hiện tại giả định SPEC/PLAN |
| 2.5 Command không dispatch skill | `cli/commands/task.py:40-41` — chỉ `review`/`apply` requires_worker; explore/spec/plan = transition/validate/compile |
| 2.6 rules_loaded = file presence | `cli/commands/bootstrap.py:47-49` |
| 2.7 Always-on quá lớn | meta-prompt 214 + rules 559 + bootstrap.md 231 ≈ 1000+ dòng |
| 2.11 Chưa có behavior suite | 92 test file toàn runtime/CI, 0 fixture agent behavior |

Hạ tầng có sẵn mà plan chưa ghi nhận (giảm effort đáng kể):

- `vnext_dispatch.py` đã có `build_prompt()` cho 11 role (intent→final_review) + `review_plan()` chạy runner → **PR 10 là wiring, không phải green-field**.
- `bootstrap.py:50-51` đã resolve active change từ `changes/*/STATE.yaml` → PR 6/7 là dọn legacy, không phải xây mới.
- `docs/refactor/maika-vnext/enforcement-ledger.yaml` đã tồn tại → đường tuân thủ R3 có sẵn.

## 2. Amendment bắt buộc trước khi thi công (lỗi nội tại của SSOT)

Sửa vào SSOT plan trong PR tương ứng (đóng dấu ngày sửa):

- **A1 — Trivial deadlock trong router (§8.2):** `apply.success_state: REVIEWING` cho mọi class,
  nhưng `review.classes` không có `trivial` và `verify.allowed_from` không có `REVIEWING`
  → trivial kẹt vĩnh viễn ở REVIEWING. Fix: `success_state_by_class` cho `apply`
  (trivial → VERIFYING). *(sửa trong PR 3)*
- **A2 — Gap SPEC_REVIEW → PLANNING (§8.2):** `spec.success_state: SPEC_REVIEW` nhưng không
  action nào `allowed_from: [SPEC_REVIEW]`. Cần action `validate-spec` (hoặc approve-spec). *(PR 3)*
- **A3 — `reviewing-change` không được route (§8.2 vs §9.3):** standard route có "final review"
  nhưng router không có action `final-review` dispatch `reviewing-change`. Thêm action. *(PR 3)*
- **A4 — File-map thiếu (§27):** mọi file `.maika/` mới phải ship qua scaffold →
  `cli/scaffold.py`, `cli/assets.py`, `cli/install/ownership.py` (classify path mới),
  và 4 snapshot trong `cli/tests/snapshots/` PHẢI nằm trong Modify list. *(mọi PR đụng `.maika/`)*
- **A5 — §23.3 vs PR 16:** compatibility window N+2 release nghĩa là PR 16 không được nằm
  cùng đợt với PR 6. Giữ PR 16 ở wave cuối, chỉ chạy khi window đã qua (user quyết định
  độ dài "release" cho repo này).

## 3. Xung đột với DEVELOPMENT_RULES và cách xử lý

`.maika/DEVELOPMENT_RULES.md` R1/R3/R4/R7 bind mọi PR. Ba PR của SSOT hiện là **đầu cơ**
theo chuẩn đó — không hủy, nhưng phải **evidence-gate**:

- **PR 8 Evidence Broker:** chưa có observed failure về duplicate provider call. Thực tế
  hiện providers gần như không hoạt động (cbm 0 project indexed, UA graph chưa build) —
  broker sẽ quản lý những call chưa từng xảy ra. **Gate:** chỉ build khi harness/dogfood
  (PR 14) ghi được `duplicate_query_avoided > 0` tiềm năng thật, tức ≥N duplicate call
  trong trace thật. Ledger entry `observed_failure` bắt buộc (R3).
- **PR 9 Context package v2 + token budget enforce:** chưa có cơ chế token-count nào được
  verify tồn tại trên các platform (R4 — "verify trigger trước, design sau"). **Gate:**
  PR 14 trace phải chứng minh đo được `token_estimate` trước khi enforce budget.
- **PR 15 Cross-host matrix:** phụ thuộc quota codex (hay chết) + agy. Chạy manual/nightly
  như SSOT nói; **không** đưa vào release gate cho tới khi chạy ổn ≥2 tuần.

Riêng PR 1–7, 10–14: hợp lệ theo R3 — mâu thuẫn/lỗ hổng đều đã observed (bảng §1).

## 4. Thứ tự thi công (5 wave — khác thứ tự SSOT có chủ đích)

Deviation chính so với SSOT: **kéo việc xóa fixed-flow contradiction (§15.4) từ PR 13 lên
PR 3** — đây là bug agent-facing nguy hiểm nhất (agent bị compact sẽ ưu tiên [CRITICAL]
fixed chain), phải chết ngay khi router ra đời, không đợi rules-JIT-split.

### Wave A — Nền + khử mâu thuẫn (PR 1 → 2 → 3)

| PR | Phạm vi | Điểm cần lưu ý ngoài SSOT |
|---|---|---|
| 1 | artifact-authority.yaml + inventory + contradiction/overlap report | R1: validator đọc authority.yaml (mầm của `authority-conflict-check`) phải nằm CÙNG PR — không khai báo YAML mồ côi |
| 2 | KERNEL.md ≤150 dòng, rút meta-prompt.md (214 dòng) | Kernel viết "theo route của workflow-router.yaml" trừu tượng (router chưa tồn tại tới PR 3); sửa `test_meta_prompt_constitution.py`, `test_meta_prompt_bootstrap_requirement.py`, snapshots |
| 3 | workflow-router.yaml + validator + `maika task route` dry-run | Áp A1/A2/A3; **rewrite `rules-flow.md` R-Flow-2** trỏ router (kéo §15.4 lên); shadow-routing Stage 1 (§29) bắt đầu từ đây |

**Exit Wave A:** mọi action/class/state resolve duy nhất; fixed chain đã chết trong rules;
route dry-run giải thích được quyết định; CI xanh.

### Wave B — Contracts (PR 4 → 5 → 6 → 7)

| PR | Phạm vi | Lưu ý |
|---|---|---|
| 4 | skill-contract.schema + generator v2 + linter + migrate 16 skill frontmatter | `skill-lint/` cũ đã bị XÓA (runtime-stabilization PR9, unwired) — linter mới phải wire vào `scripts/run_ci.py` cùng PR (R1/R2). Migration 16 skill = việc cơ học tốt cho agy, nhưng review từng skill (bài học agy gaming) |
| 5 | lightweight-change skill + routes trivial/small | Micro-plan trong TASK.yaml đã là doctrine (`task.md:84-85`) — skill mới phải khớp `_verify_lightweight` có sẵn (`task.py:403`) |
| 6 | changes/<id> authority + migration command + warnings | BOOTSTRAP_REPORT.yaml đang ghi vào `knowledge/active/` (`bootstrap.py:70`) → dời sang `runtime/`; legacy-reference-scan ra đời ở đây |
| 7 | Bootstrap split env-report/agent-ack + resume rewrite | `gates.py:1138` gate `bootstrap-complete` require `rules_loaded` → đổi cùng PR; `>1 active → require explicit id` là behavior change so với `bootstrap.py:66-67` hiện tại |

**Exit Wave B:** STATE.yaml là state authority duy nhất; skill index v2 typed; zero
prose-only trigger; `rules_present` thay `rules_loaded`.

### Wave C — Execution semantics (PR 10 → 11 → 12)

- **PR 10** dispatch explore/reconcile/brainstorm/spec/plan qua `vnext_dispatch` (mở rộng
  `action_requires_worker` + COMMAND_MAP trong `task.py:28-41`). Đây là behavior change lớn
  nhất với user — cần dogfood A (§30) ngay sau.
- **PR 11** assumption-policy.yaml + validator (thay thế R-Flow-4 "ghi assumption và tiếp
  tục" hiện hành — sửa `rules-flow.md:38` cùng PR).
- **PR 12** tách knowledge-curator → retriever/recorder/promoter + candidate capture
  `changes/<id>/learning/`.

**Exit Wave C:** public command thực sự execute skill; assumption phân loại theo risk;
không durable write trước VERIFIED.

### Wave D — Rules diet + đo lường (PR 13 → 14)

- **PR 13** rules core/jit split + load matrix. Churn lớn nhất về test/snapshot
  (mọi test hardcode `rules-*.md` list — ví dụ `test_task_command.py:27`).
- **PR 14** behavior harness: fixture schema + trace schema + fixtures A–J static + runner.
  Đây là **nguồn evidence** quyết định số phận Wave E.

**Exit Wave D:** always-on giảm ≥60% (đo được vì kernel+core rules đếm dòng được);
fixtures A–J chạy static; behavior metrics sinh ra trace thật.

### Wave E — Evidence-gated (PR 8 → 9 → 15 → 16, theo gate §3)

Chỉ mở từng PR khi gate tương ứng pass. Nếu sau 2 tuần dogfood không có evidence
(duplicate call, context overflow) → **không build** (R7: "có thể hữu ích sau" = lý do
từ chối), đóng dấu deferred vào SSOT.

## 5. Cadence & gate mỗi PR (giữ nguyên pattern các đợt trước)

1. Regression/litmus test viết TRƯỚC (test-first, tái hiện đúng gap).
2. Implement tối thiểu; mọi file `.maika/` mới → cập nhật scaffold/assets/ownership/snapshots (A4).
3. `/usr/bin/python3 scripts/run_ci.py` xanh (baseline ~923+, không skip mới) + `git diff --check`.
4. Checklist DEVELOPMENT_RULES 7 mục; enforcement mới → entry `enforcement-ledger.yaml`.
5. Commit local per PR trên `master-v2`; push cuối mỗi wave (như cadence 2026-07-11).

Worker fleet: giao agy các việc cơ học lớn (PR 4 skill migration, PR 14 fixture authoring)
sau `worker-health`; review diff + chạy test trước khi nhận (bài học PR9 gaming).

## 6. Định nghĩa xong (rút từ SSOT §28, §32)

Wave A–D xong = 100 acceptance criteria nhóm Authority/Workflow/Skills/Bootstrap/Rules/CI
pass (trừ nhóm Evidence/Context/Cross-host thuộc Wave E). Toàn chương trình xong theo §32 —
cần behavior evidence thật, không phải chỉ CI xanh.
