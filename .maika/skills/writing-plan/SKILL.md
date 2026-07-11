---
name: writing-plan
version: '3.0'
description: 'Dùng khi SPEC.md đã duyệt và state là PLANNING: kiểm precondition, targeted
  re-grounding, dựng implementation graph (contract→producer→consumer→migration→ verification→cleanup),
  phân rã task có write scope + evidence + AC + knowledge capsule.'
routing:
  mode: workflow
  actions:
  - plan
  states:
  - PLANNING
  classes:
  - standard
  - architectural
capabilities:
  required:
  - dependency_analysis
  - exact_source_inspection
  - historical_context_retrieval
  - runtime_verification
outputs:
  required:
  - IMPLEMENTATION_PLAN.md
  optional:
  - briefs/
gates:
- vnext-plan
---
# Writing Plan

## Mục tiêu
Là implementation-planning engine: biến `SPEC.md` + evidence thành
`IMPLEMENTATION_PLAN.md` với implementation graph, task phân rã đúng doctrine, mỗi
task có write scope, evidence, AC, và một Task Knowledge Capsule.

## Khi nào sử dụng
Dùng khi `SPEC.md` đã duyệt và change state là `PLANNING`.

## Khi nào KHÔNG sử dụng
- Spec chưa duyệt hoặc grounding còn conflict material.
- Để tự viết code (đó là executing-task).

## Đầu vào
- `SPEC.md`, `EVIDENCE_MANIFEST.yaml`, `CONFLICTS.yaml`, `TOOL_HEALTH.yaml`.
- Current source (verify anchor).

## Câu hỏi tri thức
- Symbol/dependency/blast radius chính xác cho từng task là gì? (targeted re-grounding)
- Contract nào có producer + consumer nào cần migrate/cleanup?
- Task xoá có consumer nào còn sót không? (delete target consumer analysis)

## Loại evidence bắt buộc
- `file_symbol`, `dependency_path`, `blast_radius` (re-verify trước exact instruction).
- `incident_reference`, `database_object` (khi liên quan), `convention_rule`.

## Chính sách capability
Capability IDs: `exact_source_inspection`, `dependency_analysis`,
  `historical_context_retrieval`, `runtime_verification`.
Trước khi viết exact instruction, targeted re-grounding bằng source + graph.

## Quy trình truy xuất
1. Kiểm precondition: spec approved, grounding approved, conflict material resolved,
   evidence fresh, base commit hợp lệ.
2. Targeted re-grounding: re-verify symbol, dependency path, blast radius, incident,
   DB object, convention cho từng task.

## Thứ tự authority và precedence
current source > business contract > durable knowledge > memory > inference. Anchor
sai source → dừng, không viết instruction trên anchor giả.

## Kết quả bắt buộc
- Implementation graph: contract → producer → consumer → migration → verification → cleanup.
- Cross-plan dependency detection; ordering producer-trước-consumer, migration, cleanup.
- Mỗi task: một behavioral objective, independently verifiable, code+test cùng task,
  write scope, evidence, AC, expected failing/passing, allowed adaptations, re-plan triggers.
- Mapping task → knowledge capsule (author_dna/conventions/code_evidence/business_rules/
  historical_context/database_evidence/forbidden_patterns/assumptions).
- Whole-plan consistency gate: mọi AC covered, producer trước consumer, delete sau
  consumer migration, không cycle, không orphan/duplicate ownership, không placeholder.

## Bất biến
- Không task mơ hồ; không exact instruction thiếu anchor.
- Không write scope không khai; không placeholder text.
- Implementer không phải tự chọn architecture.

## Yêu cầu evidence
Mỗi task cite evidence ID + AC. File/symbol phải verify bằng current source trước khi
viết plan. Delete target phải kèm consumer analysis.

## Freshness và confidence
Spec hash + evidence hash phải khớp artifact hiện tại. Evidence stale → re-plan
trigger. Base commit phải resolve được (git).

## Quy trình degradation
Targeted re-grounding thất bại (tool health kém) cho một task → đánh dấu task
`needs-regrounding`, không compile plan cho tới khi có anchor thật.

## Quy trình
1. Kiểm precondition + targeted re-grounding.
2. Dựng implementation graph + phân rã task theo doctrine.
3. Map evidence/AC/knowledge capsule cho từng task.
4. Chạy whole-plan consistency + gate `vnext-plan`.

## Điều kiện dừng
- Spec/evidence stale.
- Anchor source bắt buộc thiếu.
- Task cần quyết định public-contract/security ngoài spec.

## Tác động lên knowledge
Ghi re-plan triggers + assumption. Task capsule là slice knowledge mang vào execution.

## Đầu ra
`IMPLEMENTATION_PLAN.md` + trả `READY_FOR_PLAN_REVIEW` hoặc `NEEDS_CONTEXT`.

## Handoff tiếp theo

Mỗi task decomposition và cross-task dependency là material decision, phải có canonical
`Knowledge Trace` và evidence IDs. Capsule ghi trace IDs được task consume.
`validating-plan`.
