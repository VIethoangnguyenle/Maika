# Design: Tái cấu trúc Master Plan Maika vNext

- **Ngày:** 2026-07-10
- **Trạng thái:** Đã duyệt (user duyệt từng phần trong session brainstorm)
- **Đối tượng:** `MAIKA_VNEXT_MASTER_REFACTOR_PLAN.md` (v1, commit `437ae91`)
- **Kết quả:** bản v2 của master plan, viết lại theo các quyết định dưới đây

## 1. Bối cảnh

Master plan vNext (v1) đặt mục tiêu refactor Maika thành hệ evidence-driven, plan-first,
subagent-dispatched: bỏ OpenSpec, port phương pháp Superpowers thành skill native, thêm
evidence manifest + plan compiler + dispatcher. Session brainstorm này phản biện v1 và
chốt cách tái cấu trúc. **Đích đến (AD-1..AD-9, acceptance criteria §28) giữ nguyên;
lộ trình và khối lượng cơ chế thay đổi.**

## 2. Phản biện đã thống nhất

1. **Vi phạm R3/R7 của `DEVELOPMENT_RULES.md`:** v1 đề xuất 17 gates, 18 states,
   6 dispatch classes, claim-level SHA256, file locks, router cost/risk/sensitivity —
   phần lớn không gắn với observed failure nào. Luật repo: enforcement mới phải có
   bypass đã log hoặc litmus tái hiện được.
2. **Giá trị dồn về cuối:** Waves 0–8 toàn hạ tầng, dogfood ở Wave 12 — bẫy waterfall;
   nếu dừng giữa chừng sẽ để lại hai hệ song song dở dang (điều non-goals cấm).
3. **Thiếu Change Classification:** sơ đồ §4 có box nhưng không mục nào định nghĩa.
   Không có nó, bug 1-file đi qua ~10+ dispatch → người dùng bypass → hệ chết.
4. **Vi phạm R4 ở Wave 7:** dispatcher + model tiers giả định cơ chế platform
   (subagent spawn, model selection) tồn tại trên cả 3 platform mà chưa verify.
5. **Determinism bảo vệ khâu rẻ:** hash/schema/DAG canh đoạn plan→brief (ít rò nhất),
   trong khi plan-sai-mà-hợp-lệ chỉ có 1 LLM reviewer chốt. Compiler + verbatim brief
   là lõi, claim-level hash là mạ vàng.
6. **Mâu thuẫn nội bộ:** AD-4 cấm provider name trong canonical doc nhưng §7.2 nêu
   thẳng UA/CBM; §15 gọi là "extend microloop" nhưng thực chất là migrate contract
   markdown→JSON; 17 gates chồng lắp trái R5.
7. **Đánh giá thấp chi phí test:** 3 fixture repos (gồm banking multi-module) +
   8 dogfood scenarios dựng sẵn là một dự án con trá hình.
8. **Wave 11 dashboard là YAGNI:** `ACTIVITY_LOG.jsonl` + `maika dashboard serve` đã có.

**Những gì v1 làm đúng, giữ nguyên:** bỏ OpenSpec khỏi core; một workspace canonical;
verbatim brief (không LLM paraphrase giữa plan và executor); "exit code 0 ≠ done";
symbol anchor > line number; status contract (`NEEDS_CONTEXT`/`STALE_PLAN`...);
AD-9 extend chokepoints; rollback + feature flag `workflow_engine`; phân loại evidence
`verified/inferred/conflicting`.

## 3. Năm nguyên tắc lộ trình (P1–P5)

Thêm vào đầu master plan, ngang cấp "Execution rule":

- **P1 — Dogfood-first:** mỗi wave kết thúc bằng dogfood checkpoint chạy change thật
  (repo Maika hoặc dự án downstream thật). Observed failures ghi vào enforcement
  ledger và quyết định nội dung wave sau.
- **P2 — Enforcement ledger (thực thi R3):** mọi gate/hook/validator phải có dòng
  trong `docs/refactor/maika-vnext/enforcement-ledger.yaml`: link observed failure /
  litmus, hoặc status `deferred`. Không có evidence → không code gate đó.
- **P3 — R4 pre-flight:** wave thiết kế trên cơ chế platform phải mở đầu bằng bảng
  "Cơ chế tồn tại tại `<file:line>` / `<command>`" cho từng platform được claim.
  Thiếu → wave BLOCK ở khâu plan.
- **P4 — Single-platform-first:** vertical slice chạy Claude Code trước (tier
  `subagent` đã hoạt động); Codex/Antigravity theo sau qua adapter khi contract đã
  ổn định qua dogfood.
- **P5 — Fixture thật thay fixture dựng:** dogfood dùng repo Maika + dự án Java thật.
  Không dựng banking fixture; CI e2e dùng 1 fixture Python tối giản.

## 4. Change Classification (mục mới)

Bốn class, ghi vào `CHANGE.yaml` tại INTAKE; gates đọc class để biết artifact nào
bắt buộc. Orchestrator đề xuất class, user xác nhận bằng một câu hỏi.

| Class | Ví dụ | Pipeline |
|---|---|---|
| `trivial` | typo, doc, config 1 file, không đổi behavior | INTENT → mini-plan (1 task, mode `intent`) → implement → verify. Không explorer, không SPEC. Vẫn write-gate + result contract. |
| `small` | bug/feature 1 module, ≤ ~3 file | Codebase exploration nhẹ (seam + tests) → SPEC ngắn (Goal/Current/Desired/AC) → plan → plan review → execute → task review (kiêm final review khi 1 task) → verify. |
| `standard` | multi-file, multi-module | Full pipeline. |
| `architectural` | đổi public contract, DB, cross-service | Full pipeline + mọi user-approval gate bắt buộc + Compatibility/Migration không được trống. |

**Escalation rule:** đụng re-plan trigger vượt class (public signature, dependency
mới, module mới...) → re-classify lên và quay lại bước còn thiếu. Dùng lại danh sách
re-plan triggers §17 của v1, không thêm cơ chế mới.

## 5. Lộ trình mới: 13 waves → 8 waves

```text
W0  Baseline & inventory            (+ enforcement-ledger.yaml + platform capability matrix)
W1  Vertical slice: plan→brief→execute→review trên Claude Code
      ↳ Dogfood A: 2 change class `small` trên repo Maika
W2  Grounding core: codebase evidence + spec + grounded brainstorm
      ↳ Dogfood B: 1 change `standard` trên Maika + 1 trên dự án thật
W3  Reconciliation + business/convention explorer (theo bằng chứng Dogfood B)
W4  Capability registry + skill-lint provider-name rule
W5  Cross-platform: adapter Codex/Antigravity (mở đầu bằng bảng R4 pre-flight)
W6  Cutover: task.md + commands + OpenSpec importer/removal khỏi default
W7  Hardening: dogfood mở rộng, metrics, default-switch gate
```

Điểm khác biệt chính so với v1:

- **W0** = Wave 0 cũ thu gọn + khởi tạo enforcement ledger (P2) + platform capability
  matrix (R4: subagent spawn / hook events / model selection thực tế trên Claude Code,
  Codex, Antigravity, kèm dẫn chứng). Matrix là input bắt buộc của W5.
- **W1** gộp lõi Wave 1+5+6+7 cũ thành vertical slice: workspace tối thiểu
  (`CHANGE.yaml`, `INTENT.md`, `SPEC.md`, `IMPLEMENTATION_PLAN.md`,
  `generated/TASK_QUEUE.json`, `briefs/`, `results/`, `STATE.yaml`); skill
  `writing-plan` + mechanical validation subset (file/symbol tồn tại, task có
  verification, ID duy nhất, DAG acyclic) + independent plan review; compiler tối
  thiểu (parse → sequential queue → verbatim brief + hash); dispatch implementer +
  task reviewer trên Claude Code; write-gate check brief-scope; feature flag
  `workflow_engine: vnext` opt-in từ wave này. **Sau W1 đã có pipeline end-to-end
  thật, dù thô.**
- **W2**: codebase-explorer vNext (refactor skill hiện có), evidence manifest
  **file-level hash**, grounding gate rút gọn (section codebase), spec contract đầy
  đủ, port grounded brainstorming.
- **W3**: business/convention explorer chỉ build như v1 nếu Dogfood B chứng minh
  thiếu loại evidence đó; nếu không thì là lens của 1 explorer. Quyết bằng ledger.
- **W4**: capability schema + health/freshness probe (observed failure: UA/CBM daemon
  chết) + lint cấm provider-name trong canonical skill + refactor `rules-tool.md`.
  Router chỉ theo health/freshness.
- **W5**: adapter dispatch + write-gate parity cho Codex/Antigravity theo matrix W0;
  model tiers chỉ trên platform chọn model được thật.
- **W6** = Wave 9+10 cũ gộp: refactor `task.md` quanh state machine, commands
  `/task ...`, resume, `maika migrate-openspec`, gỡ OpenSpec khỏi default.
- **W7**: dogfood scenarios thật (thay 8 scenario dựng sẵn), metrics như v1,
  default-switch gate giữ nguyên điều kiện.

Mỗi wave giữ quy tắc gốc: implementation plan Superpowers-style riêng, review trước
khi code, độc lập revert được, baseline xanh.

## 6. Cắt / gộp / defer

| Hạng mục v1 | Quyết định | Lý do |
|---|---|---|
| Wave 11 dashboard mở rộng | Defer — chỉ khi ledger ghi nhu cầu thật | Dashboard + `ACTIVITY_LOG.jsonl` đã có; R7 |
| Claim-level SHA256 evidence | Thu gọn → `source_hash` mức file (giữ `node_id` + `indexed_commit` cho graph) | Churn staleness; chưa có lỗi cần độ mịn claim |
| Parallel file locks + ownership + batch parallelism | Defer — queue sequential-only W1–W6 | Chưa từng chạy parallel implementers; R3 |
| Router cost / risk / data-sensitivity | Cắt — router chỉ health + freshness | Lỗi quan sát được là tool chết / index cũ |
| 3 fixture repos E2E | Thu gọn → 1 fixture Python tối giản cho CI; dogfood repo thật | P5 |
| 8 dogfood scenarios dựng sẵn | Thay bằng change thật trong Dogfood A/B + W7 | R3 |
| 17 gates (§20) | Gộp → 9: `change-workspace`, `exploration-evidence`, `spec`, `plan`, `brief-integrity`, `result-contract`, `task-review`, `final-review`, `archive-readiness` | R5: một concern một đường enforcement |
| 18 states (§6) | Gộp → 14: `GROUNDING_BLOCKED`/`STALE` → `BLOCKED` + `reason`; bỏ `READY` (transition); `TASK_REVIEW` thành status per-task trong queue | Mỗi state là chi phí resume/crash-test |
| 6 dispatch classes | Giữ khái niệm; W1 implement 3 (`implementation`, `task_review`, `planning`), còn lại vào theo W2–W3 | Vào theo nhu cầu wave |

## 7. Sửa nhất quán nội bộ

1. **AD-4 vs §7.2:** role model (§7) đổi mọi provider name cụ thể thành capability ID;
   tên cụ thể chỉ còn trong §8 provider mappings và platform adapters.
2. **§15 reframe:** "extend microloop-orchestrator" → "**migrate microloop contract**":
   contract hiện tại là markdown (`TASK_QUEUE.md`, `TASK_HANDOFF.md`, `TASK_RESULT.md`),
   vNext chuyển sang JSON + brief hash; cần đường tương thích đọc artifact cũ trong
   giai đoạn opt-in và cập nhật snapshot tests.
3. **§30 First agent instructions:** cập nhật theo lộ trình mới (W0 → W1 vertical
   slice thay vì Wave 1 schemas).
4. **§10, §14, §19, §20:** mỗi mục enforcement thêm chú thích trỏ về enforcement
   ledger (P2).

## 8. Deliverable và trình tự

1. Commit v1 master plan nguyên trạng (đã làm: `437ae91`).
2. Commit design doc này.
3. Viết lại `MAIKA_VNEXT_MASTER_REFACTOR_PLAN.md` thành v2 theo mục 3–7 (commit
   riêng — diff cho thấy chính xác thay đổi).
4. Kết thúc branch bằng PR theo quy trình chuẩn của repo.

Bản v2 phải giữ nguyên: Goal (§1), Non-goals (§2), AD-1..AD-9 (§3), acceptance
criteria (§28), rollback strategy (§29) — trừ các điểm bị mục 6–7 sửa trực tiếp.
