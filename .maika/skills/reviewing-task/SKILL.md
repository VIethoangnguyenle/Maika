---
name: reviewing-task
version: '3.0'
description: 'Dùng khi một task result qua result-contract gate: review độc lập tìm
  counter-evidence — kiểm ít nhất một source anchor cho mỗi material behavior, public
  contract, deleted file, persistence/async/security boundary, incident, convention.'
routing:
  mode: dispatch
  states:
  - EXECUTING
  classes:
  - small
  - standard
  - architectural
capabilities:
  required:
  - exact_source_inspection
  - runtime_verification
  - review_dispatch
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
  - reviews/
gates:
- task-review
---
# Reviewing Task

## Mục tiêu
Chấp nhận/từ chối một task đã implement bằng cách **tìm counter-evidence độc lập**,
không tin planner/implementer mù quáng.

## Khi nào sử dụng
Dùng sau khi một task result qua `result-contract` gate.

## Khi nào KHÔNG sử dụng
- Result schema chưa hợp lệ.
- Để sửa application code (reviewer không sửa code).

## Đầu vào
- `briefs/TASK-NNN.md` + capsule, `results/TASK-NNN.yaml`, diff package của task.

## Câu hỏi tri thức
- Mỗi material behavior có ít nhất một source anchor xác nhận không?
- Public contract/persistence/async/security boundary có bị chạm không?
- Incident lịch sử liên quan có tái xuất hiện không?

## Loại evidence bắt buộc
- `exact_code_fact` (≥1 anchor / material behavior).
- `incident_reference`, `convention_rule`, `database_object` (nếu persistence).

## Chính sách capability
Required: `exact_source_inspection`, `runtime_verification`, `review_dispatch`.
Conditional — chỉ gọi khi trigger kích hoạt, ghi trigger + reason:
  `symbolic_code_navigation` (hidden_consumer_risk, reviewer_counter_evidence,
  relevant_graph_stale); `code_diagnostics` (language_diagnostics_required);
  `call_chain_trace` (reviewer_counter_evidence); `impact_analysis`
  (blast_radius_required); `semantic_code_search` (hidden_consumer_risk,
  dynamic_wiring_risk, reviewer_counter_evidence, ua_unavailable);
  `dependency_analysis` (graph_gap, ua_unavailable); `historical_context_retrieval`
  (reviewer_counter_evidence); `database_schema_inspection` (persistence_change).
Reviewer tự đọc source, không dựa claim của brief.
Symbol references là **scoped LSP evidence**, không phải proof của mọi
reflective/configured/event consumer; mọi material claim vẫn cần current source.

## Quy trình truy xuất
1. Đọc brief + result + diff.
2. Reinspect primary structured trace độc lập; không lặp lại nguyên trace của implementer.
3. Khi có blast-radius/hidden-consumer risk, dùng conditional symbolic/semantic
   evidence phù hợp để tìm counter-evidence và ghi trigger + support reason.
4. Independent inspect: mở current source thật cho mỗi material behavior và finding.
5. Recall incident liên quan để kiểm regression; ghi graph freshness trong review.

## Thứ tự authority và precedence
current source > result claim > brief. Result nói "pass" nhưng source mâu thuẫn →
CHANGES_REQUIRED.

## Kết quả bắt buộc
Kiểm độc lập: ≥1 source anchor / material behavior, mọi public contract, mọi deleted
production file, persistence boundary, async/event boundary, security-sensitive change,
incident lịch sử liên quan, convention áp. `reviews/TASK-NNN.md` với verdict.

## Bất biến
- Reviewer không sửa application code.
- Không re-plan im lặng.
- Không approve khi thiếu verification evidence.

## Yêu cầu evidence
Kiểm changed/deleted files, changed symbols, command + observed output, brief hash,
allowed files, AC. Finding phân loại CRITICAL/IMPORTANT/MINOR/NOTE.

## Freshness và confidence
Xác nhận diff khớp result + brief hash. Evidence stale → không approve.

## Quy trình degradation
Thiếu evidence để kiểm một boundary (vd DB) → ghi finding IMPORTANT "chưa verify được
boundary X", không cho qua bằng giả định.

## Quy trình
1. Đọc brief/capsule + result + diff.
2. Independent counter-evidence trên các boundary bắt buộc.
3. Phân loại finding; trả verdict.

## Điều kiện dừng
- Result schema invalid.
- Diff vượt allowed scope.
- Thiếu evidence khiến không review được.

## Tác động lên knowledge
Finding lặp lại (recurring review pattern) được ghi để curator lưu vào Agent Memory.

## Đầu ra
`reviews/TASK-NNN.md` với verdict `APPROVED` hoặc `CHANGES_REQUIRED`.

## Handoff tiếp theo

Review phải tìm counter-evidence và ghi canonical `Knowledge Trace` cho verdict material;
trace cite source hiện tại, capsule IDs, conflict/assumption/freshness và confidence.
Fix dispatch cho finding, hoặc orchestrator queue completion.
