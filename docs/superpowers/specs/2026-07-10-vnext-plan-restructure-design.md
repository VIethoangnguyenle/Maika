# Design: Tái cấu trúc Master Plan Maika vNext

- **Ngày:** 2026-07-10
- **Trạng thái:** Rev 2 — đã áp 4 sửa đổi bắt buộc từ review của user (W2 ba lens grounding, capability vocabulary trước W4, classification không hỏi mọi lúc, schema enforcement ledger). Chờ duyệt lần cuối trước khi viết master plan v2.
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
- **P2 — Enforcement ledger (thực thi R3):** mọi gate/hook/validator phải có entry
  trong `docs/refactor/maika-vnext/enforcement-ledger.yaml` theo schema §4. Một cơ chế
  chỉ được implement khi entry của nó có ít nhất một trong: observed failure, litmus
  tái hiện được, yêu cầu bên ngoài (external requirement), hoặc nó bảo vệ safety /
  destructive-action boundary. Không thỏa điều nào → status phải là `deferred`.
  **Ngoại lệ quan trọng:** write boundary và destructive-action protection không
  chờ sự cố production mới được xây.
- **P3 — R4 pre-flight:** wave thiết kế trên cơ chế platform phải mở đầu bằng bảng
  "Cơ chế tồn tại tại `<file:line>` / `<command>`" cho từng platform được claim.
  Thiếu → wave BLOCK ở khâu plan.
- **P4 — Single-platform-first:** vertical slice chạy Claude Code trước (tier
  `subagent` đã hoạt động); Codex/Antigravity theo sau qua adapter khi contract đã
  ổn định qua dogfood.
- **P5 — Fixture thật thay fixture dựng:** dogfood dùng repo Maika + dự án Java thật.
  Không dựng banking fixture; CI e2e dùng 1 fixture Python tối giản.

## 4. Enforcement ledger — schema

File: `docs/refactor/maika-vnext/enforcement-ledger.yaml`. Schema tối thiểu:

```yaml
version: 1

entries:
  - id: ENF-001
    mechanism: code-evidence
    type: gate            # gate | hook | validator
    status: active

    failure:
      classification: observed_failure
      reference: docs/incidents/example.md
      summary: Agent used grep despite a healthy indexed provider.

    litmus:
      command: python3 ...
      expected_without_enforcement: pass
      expected_with_enforcement: fail

    implementation:
      files:
        - .maika/tools/gate-check/gates.py
      consumers:
        - .maika/workflows/task.md

    scope:
      change_classes:
        - standard
        - architectural

    reviewed_at: 2026-07-10
```

Status hợp lệ:

```text
proposed | active | deferred | superseded | removed
```

Evidence classification hợp lệ:

```text
observed_failure | reproducible_litmus | external_requirement | safety_boundary
```

Điều kiện implement (ít nhất một):

1. Có observed failure.
2. Có litmus tái hiện được.
3. Yêu cầu bên ngoài bắt buộc (external requirement).
4. Bảo vệ safety / destructive-action boundary.

Không thỏa → status giữ `deferred`. Gate-check của v2 sẽ validate schema này
(entry đó tự ghi vào ledger với classification `safety_boundary` hoặc litmus riêng).

**Ghi chú so với R3:** classification `external_requirement` và `safety_boundary` là
phần mở rộng có chủ đích so với câu chữ R3 (chỉ nêu observed failure / litmus).
Master plan v2 phải ghi rõ ngoại lệ này; nếu được chấp nhận lâu dài thì cập nhật
`DEVELOPMENT_RULES.md` trong một PR riêng (R6 — không sửa lặng lẽ).

## 5. Capability vocabulary (có trước W4)

Registry + router runtime vẫn nằm ở W4, nhưng **vocabulary trừu tượng phải tồn tại
từ W1** để skill canonical W1/W2 không viết theo tên MCP cụ thể rồi refactor lại
ở W4. Tối thiểu 6 capability ID:

```text
architecture_discovery
exact_source_inspection
dependency_analysis
business_knowledge_retrieval
convention_retrieval
runtime_verification
```

Quy tắc:

- Canonical skill và role contract chỉ tham chiếu capability ID.
- Provider name / function mapping cụ thể chỉ nằm trong: provider mappings,
  platform adapters, tool documentation, capability profiles.
- Vocabulary ship **cùng PR** với skill canonical đầu tiên tham chiếu nó (thỏa R1 —
  consumer có mặt cùng PR); mechanical consumer đầy đủ (skill-lint cấm provider-name)
  đến ở W4. Trong khoảng W1→W4, compliance do plan review giữ.
- W4 implement phần runtime: provider registry, health checks, freshness checks,
  provider mappings, skill lint, dọn `rules-tool.md`.

## 6. Change Classification (mục mới)

Bốn class, ghi vào `CHANGE.yaml` tại INTAKE; gates đọc class để biết artifact nào
bắt buộc.

| Class | Ví dụ | Pipeline |
|---|---|---|
| `trivial` | typo, doc, config 1 file, không đổi behavior | INTENT → mini-plan (1 task, mode `intent`) → implement → verify. Không explorer, không SPEC. Vẫn write-gate + result contract. |
| `small` | bug/feature 1 module, ≤ ~3 file | Grounding nhẹ (seam + tests) → SPEC ngắn (Goal/Current/Desired/AC) → plan → plan review → execute → task review (kiêm final review khi 1 task) → verify. |
| `standard` | multi-file, multi-module | Full pipeline. |
| `architectural` | đổi public contract, DB, cross-service | Full pipeline + mọi user-approval gate bắt buộc + Compatibility/Migration không được trống. |

**Xác nhận classification — không hỏi mọi lúc:**

- `trivial` và `small` rõ ràng: orchestrator phân loại, **hiển thị ngắn gọn class +
  lý do rồi tiến hành luôn** trừ khi user phản đối. Ví dụ:

  ```text
  Classified as `small`: one module, three files or fewer, no public contract,
  database, security, or cross-service impact.
  ```

- Bắt buộc hỏi xác nhận rõ ràng chỉ khi: classification mơ hồ; class đề xuất là
  `standard` hoặc `architectural`; đụng public contract; đụng persistence/database;
  hành vi nhạy cảm bảo mật; destructive migration; hoặc reclassification kéo theo
  artifact/approval gate đáng kể.
- Mọi classification (kể cả tự tiến hành) đều ghi vào `CHANGE.yaml`.

**Escalation rule:** đụng re-plan trigger vượt class (public signature, dependency
mới, module mới...) → re-classify lên và quay lại bước còn thiếu. Dùng lại danh sách
re-plan triggers §17 của v1, không thêm cơ chế mới.

## 7. Lộ trình mới: 13 waves → 8 waves

```text
W0  Baseline & inventory            (+ enforcement-ledger.yaml + platform capability matrix)
W1  Vertical slice: plan→brief→execute→review trên Claude Code (+ capability vocabulary)
      ↳ Dogfood A: 2 change class `small` trên repo Maika
W2  Grounding core: 3 lens bắt buộc (codebase + business + conventions) + spec + grounded brainstorm
      ↳ Dogfood B: 1 change `standard` trên Maika + 1 trên dự án thật
W3  Reconciliation + quyết định tách explorer chuyên biệt (theo bằng chứng Dogfood B)
W4  Capability registry runtime + skill-lint provider-name rule
W5  Cross-platform: adapter Codex/Antigravity (mở đầu bằng bảng R4 pre-flight)
W6  Cutover: task.md + commands + OpenSpec importer/removal khỏi default
W7  Hardening: dogfood mở rộng, metrics, default-switch gate
```

Điểm khác biệt chính so với v1:

- **W0** = Wave 0 cũ thu gọn + khởi tạo enforcement ledger (§4) + platform capability
  matrix (R4: subagent spawn / hook events / model selection thực tế trên Claude Code,
  Codex, Antigravity, kèm dẫn chứng). Matrix là input bắt buộc của W5; mọi claim
  cross-platform trong plan bị defer cho đến khi matrix tồn tại.
- **W1** gộp lõi Wave 1+5+6+7 cũ thành vertical slice: workspace tối thiểu
  (`CHANGE.yaml`, `INTENT.md`, `SPEC.md`, `IMPLEMENTATION_PLAN.md`,
  `generated/TASK_QUEUE.json`, `briefs/`, `results/`, `STATE.yaml`); capability
  vocabulary (§5) ship cùng skill đầu tiên; skill `writing-plan` + mechanical
  validation subset (file/symbol tồn tại, task có verification, ID duy nhất, DAG
  acyclic) + independent plan review; compiler tối thiểu (parse → sequential queue →
  verbatim brief + hash); dispatch implementer + task reviewer trên Claude Code;
  write-gate check brief-scope; feature flag `workflow_engine: vnext` opt-in từ wave
  này. **W1 không phụ thuộc bất kỳ phần nào của capability runtime W4** — chỉ dùng
  vocabulary tĩnh. Sau W1 đã có pipeline end-to-end thật, dù thô.
- **W2 — ba lens grounding bắt buộc.** Một **unified explorer** (codebase-explorer
  hiện có refactor thành grounding-explorer) sinh một artifact grounding duy nhất có
  đủ 3 section:

  ```yaml
  codebase:
    entry_points:
    current_flow:
    extension_seams:
    related_tests:
    blast_radius:

  business:
    terminology:
    known_rules:
    states_and_transitions:
    unresolved_questions:
    evidence_sources:

  conventions:
    applicable_rule_ids:
    existing_patterns:
    testing_patterns:
    error_handling:
    conflicts:
  ```

  Evidence manifest **file-level hash**. Grounding gate yêu cầu đủ 3 section có nội
  dung — **brainstorming không được đề xuất kiến trúc cuối khi thiếu bất kỳ lens
  nào**. Port grounded brainstorming + spec contract đầy đủ. Business grounding
  không bị defer — chỉ *agent chuyên biệt* mới có thể defer.
- **W3 — chuyên biệt hóa có điều kiện.** W3 quyết định tách 3 lens thành subagent
  riêng (Business Explorer / Convention Explorer như v1) **chỉ dựa trên bằng chứng
  dogfood**, ví dụ: business rules bị bỏ sót lặp lại; convention constraints bị
  thiếu; context quá lớn; business/code evidence không được reconcile; unified
  explorer cho output nông. Không có bằng chứng → giữ unified explorer, W3 chỉ còn
  reconciler + full grounding gate. Tóm tắt: `W2: ba lens bắt buộc; W3: tách agent
  là tùy chọn theo evidence`.
- **W4**: phần runtime của capability model — provider registry, health/freshness
  probe (observed failure có sẵn: UA/CBM daemon chết), provider mappings, skill-lint
  cấm provider-name trong canonical skill, refactor `rules-tool.md`. Router chỉ theo
  health/freshness. Vocabulary đã tồn tại từ W1 nên W4 không phải refactor skill.
- **W5**: adapter dispatch + write-gate parity cho Codex/Antigravity theo matrix W0;
  model tiers chỉ trên platform chọn model được thật.
- **W6** = Wave 9+10 cũ gộp: refactor `task.md` quanh state machine, commands
  `/task ...`, resume, `maika migrate-openspec`, gỡ OpenSpec khỏi default.
- **W7**: dogfood scenarios thật (thay 8 scenario dựng sẵn), metrics như v1,
  default-switch gate giữ nguyên điều kiện. Parallel execution vẫn `deferred` trong
  ledger trừ khi dogfood ghi nhận nhu cầu thật.

Mỗi wave giữ quy tắc gốc: implementation plan Superpowers-style riêng, review trước
khi code, độc lập revert được, baseline xanh.

## 8. Cắt / gộp / defer

| Hạng mục v1 | Quyết định | Lý do |
|---|---|---|
| Wave 11 dashboard mở rộng | Defer — chỉ khi ledger ghi nhu cầu thật; dashboard + `ACTIVITY_LOG.jsonl` hiện có giữ nguyên | R7 |
| Claim-level SHA256 evidence | Thu gọn → `source_hash` mức file (giữ `node_id` + `indexed_commit` cho graph) | Churn staleness; chưa có lỗi cần độ mịn claim |
| Parallel file locks + ownership + batch parallelism | Defer — sequential queue là execution mode duy nhất đến hết W6 | Chưa từng chạy parallel implementers; R3 |
| Router cost / risk / data-sensitivity | Cắt — router chỉ health + freshness | Lỗi quan sát được là tool chết / index cũ |
| 3 fixture repos E2E | Thu gọn → 1 fixture Python tối giản cho CI; dogfood repo thật | P5 |
| 8 dogfood scenarios dựng sẵn | Thay bằng change thật trong Dogfood A/B + W7 | R3 |
| 17 gates (§20) | Gộp → 9: `change-workspace`, `exploration-evidence`, `spec`, `plan`, `brief-integrity`, `result-contract`, `task-review`, `final-review`, `archive-readiness` | R5: một concern một đường enforcement |
| 18 states (§6) | Gộp → 14: `GROUNDING_BLOCKED`/`STALE` → `BLOCKED` + `reason`; bỏ `READY` (transition); `TASK_REVIEW` thành status per-task trong queue | Mỗi state là chi phí resume/crash-test |
| 6 dispatch classes | Giữ khái niệm; W1 implement 3 (`implementation`, `task_review`, `planning`), còn lại vào theo W2–W3 | Vào theo nhu cầu wave |

## 9. Sửa nhất quán nội bộ

1. **AD-4 vs §7.2:** role model (§7) đổi mọi provider name cụ thể thành capability ID
   theo vocabulary §5; tên cụ thể chỉ còn trong provider mappings và platform adapters.
2. **§15 reframe:** "extend microloop-orchestrator" → "**migrate microloop contract**":
   contract hiện tại là markdown (`TASK_QUEUE.md`, `TASK_HANDOFF.md`, `TASK_RESULT.md`),
   vNext chuyển sang JSON + brief hash; cần đường tương thích đọc artifact cũ trong
   giai đoạn opt-in và cập nhật snapshot tests.
3. **§30 First agent instructions:** cập nhật theo lộ trình mới (W0 → W1 vertical
   slice thay vì Wave 1 schemas).
4. **§10, §14, §19, §20:** mỗi mục enforcement thêm tham chiếu entry tương ứng trong
   enforcement ledger (§4).

## 10. Checklist nhất quán cho bản v2

Bản rewrite master plan v2 phải pass đủ 10 điểm (đây là acceptance criteria của
việc rewrite):

1. W1 không phụ thuộc capability runtime W4 (chỉ vocabulary tĩnh §5).
2. W2 brainstorming không thể đề xuất kiến trúc cuối khi thiếu một trong 3 lens.
3. W3 chuyên biệt hóa explorer là có điều kiện, quyết bằng evidence dogfood.
4. Không wave sớm nào giả định parallel implementers.
5. Không canonical skill nào chứa chuỗi function provider cụ thể.
6. Mọi mục gate/hook/validator đều tham chiếu enforcement ledger.
7. Mọi claim cross-platform đều đứng sau W0 R4 capability matrix.
8. `trivial`/`small` không tạo tương tác user không cần thiết.
9. Sequential queue là execution mode duy nhất đến hết W6.
10. Dashboard hiện có + `ACTIVITY_LOG.jsonl` giữ nguyên trừ khi dogfood ghi nhận
    thiếu hụt cụ thể.

## 11. Deliverable và trình tự

1. Commit v1 master plan nguyên trạng (đã làm: `437ae91`).
2. Commit design doc này (rev 1: `0eeb4b1`; rev 2: commit hiện tại).
3. Sau khi user duyệt rev 2: viết lại `MAIKA_VNEXT_MASTER_REFACTOR_PLAN.md` thành v2
   theo mục 3–10 (commit riêng — diff cho thấy chính xác thay đổi).
4. Kết thúc branch bằng PR theo quy trình chuẩn của repo.

Bản v2 phải giữ nguyên: Goal (§1), Non-goals (§2), AD-1..AD-9 (§3), acceptance
criteria (§28), rollback strategy (§29) — trừ các điểm bị mục 8–9 sửa trực tiếp.
