---
name: reviewing-change
version: '3.0'
description: 'Dùng khi mọi task review đã pass và trước verification: review toàn
  change, kiểm integration/deleted-reference/verification, và ghi KNOWLEDGE_IMPACT.yaml
  (stale knowledge, superseded decision, new candidate, graph refresh, memory save).'
routing:
  mode: workflow
  actions:
  - final-review
  states:
  - FINAL_REVIEW
  classes:
  - standard
  - architectural
capabilities:
  required:
  - exact_source_inspection
  - runtime_verification
  conditional:
    symbolic_code_navigation:
      triggers:
      - hidden_consumer_risk
      - reviewer_counter_evidence
      - relevant_graph_stale
    code_diagnostics:
      triggers:
      - language_diagnostics_required
    call_chain_trace:
      triggers:
      - reviewer_counter_evidence
    impact_analysis:
      triggers:
      - blast_radius_required
    semantic_code_search:
      triggers:
      - hidden_consumer_risk
      - dynamic_wiring_risk
      - reviewer_counter_evidence
      - ua_unavailable
    dependency_analysis:
      triggers:
      - graph_gap
      - ua_unavailable
    historical_context_retrieval:
      triggers:
      - reviewer_counter_evidence
    database_schema_inspection:
      triggers:
      - persistence_change
outputs:
  required:
  - reviews/FINAL_REVIEW.md
  - reviews/KNOWLEDGE_IMPACT.yaml
  optional:
  - reviews/FINDINGS.yaml
gates:
- final-review
- knowledge-impact
---
# Reviewing Change

## Mục tiêu
Review toàn bộ change (không phải một task), và chốt tác động tri thức của change vào
`reviews/KNOWLEDGE_IMPACT.yaml`.

## Khi nào sử dụng
Dùng sau khi mọi task review bắt buộc pass, trước verification/completion.

## Khi nào KHÔNG sử dụng
- Còn task chưa review.
- Để sửa application code.

## Đầu vào
- Full branch diff package, `SPEC.md`, `IMPLEMENTATION_PLAN.md`.
- Task results + reviews, `EVIDENCE_MANIFEST.yaml`, `CONFLICTS.yaml`.

## Câu hỏi tri thức
- Change làm knowledge nào stale/superseded?
- Cần graph refresh / memory save / convention hoặc Author DNA candidate mới không?
- DB evidence nào bị ảnh hưởng?

## Loại evidence bắt buộc
- `exact_code_fact` (cross-task integration), `dependency_path` (blast radius toàn change).
- `database_object` (nếu persistence), `incident_reference` (regression).

## Chính sách capability
Required: `exact_source_inspection`, `runtime_verification`.
Conditional — chỉ gọi khi trigger kích hoạt, ghi trigger + reason:
  `call_chain_trace` (reviewer_counter_evidence); `impact_analysis`
  (blast_radius_required); `semantic_code_search` (hidden_consumer_risk,
  dynamic_wiring_risk, reviewer_counter_evidence, ua_unavailable);
  `dependency_analysis` (graph_gap, ua_unavailable); `historical_context_retrieval`
  (reviewer_counter_evidence); `database_schema_inspection` (persistence_change).
Đọc diff toàn change độc lập; đối chiếu với durable knowledge.

## Quy trình truy xuất
1. Đọc spec/plan/results/reviews.
2. Verify integration boundaries bằng structured call/impact trace; ghi graph freshness,
   node IDs và relationship types.
3. Dùng `semantic_code_search` cho alternate paths/hidden consumers khi risk áp dụng;
   ghi reason, không gọi lặp nếu structured trace đã đủ.
4. Inspect current source cho material facts, full diff và deletion discipline.
5. Đối chiếu change với durable knowledge để tìm entry stale/superseded.

## Thứ tự authority và precedence
current source (sau change) > durable knowledge > memory. Knowledge mâu thuẫn với
source mới → đánh dấu stale/superseded.

## Kết quả bắt buộc
- `reviews/FINAL_REVIEW.md` + `reviews/FINDINGS.yaml` (Minor/Note chưa xử lý).
- `reviews/KNOWLEDGE_IMPACT.yaml`: stale knowledge, superseded decision, new knowledge
  candidate, graph refresh, memory save, convention candidate, Author DNA candidate,
  database evidence affected.
- Critical/Important resolved trước completion.

## Bất biến
- Không sửa application code.
- Không bỏ qua cross-task integration.
- Không approve generated artifact stale.

## Yêu cầu evidence
Dùng diff evidence, task results, final verification, deleted-reference scan, AC coverage.

## Freshness và confidence
Xác nhận generated artifact (queue/plan) không stale so với diff. Verification evidence
phải fresh.

## Quy trình degradation
Không đánh giá được một tác động tri thức (vd graph không probe được) → ghi vào
`KNOWLEDGE_IMPACT.yaml` là `needs-refresh` + degradation, không bỏ trống.

## Quy trình
1. Đọc spec/plan/results/reviews; inspect full diff.
2. Kiểm integration + deletion.
3. Phân loại finding; viết `FINAL_REVIEW.md` + `KNOWLEDGE_IMPACT.yaml`.

## Điều kiện dừng
- Task nào đó thiếu review.
- Còn Critical/Important.
- Verification evidence stale/thiếu.

## Tác động lên knowledge
`KNOWLEDGE_IMPACT.yaml` là input cho `knowledge-promoter` (promote/supersede/save/refresh).

## Đầu ra
`reviews/FINAL_REVIEW.md`, `reviews/FINDINGS.yaml`, `reviews/KNOWLEDGE_IMPACT.yaml`.

## Handoff tiếp theo

Final verdict và knowledge-impact decision phải có canonical `Knowledge Trace`; thiếu
trace hoặc còn conflict unresolved thì `CHANGES_REQUIRED`, không được approve.
`verification-before-completion`.
