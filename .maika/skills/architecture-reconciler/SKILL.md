---
name: architecture-reconciler
version: '3.0'
description: 'Dùng khi gói grounding đã có evidence đa nguồn cần đối chiếu: dựng claim
  matrix giữa UA/CBM/source/memory/DB/durable knowledge, phân loại và giải quyết conflict
  theo thứ tự authority trước khi brainstorming/spec.'
routing:
  mode: workflow
  actions:
  - reconcile
  states:
  - RECONCILING
  classes:
  - standard
  - architectural
capabilities:
  required:
  - architecture_discovery
  - dependency_analysis
  - exact_source_inspection
  - historical_context_retrieval
outputs:
  required:
  - RECONCILIATION.md
  - exploration/CONFLICTS.yaml
gates:
- conflicts
- knowledge-trace
---
# Architecture Reconciler

## Mục tiêu
Đối chiếu evidence (không chỉ tóm tắt): dựng claim matrix đa nguồn, phân loại
conflict, resolve theo thứ tự authority, chốt `CONFLICTS.yaml` + `RECONCILIATION.md`
trước khi thiết kế.

## Khi nào sử dụng
Dùng khi `grounding-explorer` trả gói grounding cho change standard/architectural và
tồn tại evidence từ nhiều nguồn cần đối chiếu.

## Khi nào KHÔNG sử dụng
- Change nhỏ, một nguồn evidence, không có conflict.
- Để đề xuất approach (đó là brainstorming).

## Đầu vào
- `GROUNDING.yaml`, `EVIDENCE_MANIFEST.yaml`, `CONFLICTS.yaml`, `TOOL_HEALTH.yaml`.
- Current source (trọng tài exact fact), `DATABASE_CONTEXT.yaml` (nếu có).

## Câu hỏi tri thức
- Các nguồn có đồng thuận về cùng một claim không?
- Nếu lệch: do stale graph, stale memory, source drift, database drift, business
  ambiguity, convention conflict, hay mâu thuẫn kiến trúc thật?

## Loại evidence bắt buộc
- Claim từ ≥2 nguồn cho mỗi material fact khi có thể.
- `exact_code_fact` (verify), `database_object` (nếu persistence).

## Chính sách capability
Capability IDs: `exact_source_inspection`, `dependency_analysis`,
  `architecture_discovery`, `historical_context_retrieval`.
Dùng để re-probe khi cần xác nhận claim mâu thuẫn.

## Quy trình truy xuất
1. Dựng claim matrix: hàng = claim, cột = UA/CBM/source/memory/DB/durable.
2. Với claim lệch, re-fetch node detail + verify bằng current source.

## Thứ tự authority và precedence
live runtime/DB state > current source > business contract hiện hành > fresh graph >
durable knowledge > historical memory > inference (R-Know-2).

## Kết quả bắt buộc
- Mọi conflict material được phân loại + resolved/deferred-có-lý-do.
- `CONFLICTS.yaml` không còn conflict `open` material.

## Bất biến
- Không resolve conflict bằng cách chọn nguồn tiện nhất — theo authority.
- Không thiết kế giải pháp.

## Yêu cầu evidence
Mỗi resolution ghi `resolved_by` (claim thắng) + lý do. Conflict deferred ghi lý do +
điều kiện xử lý.

## Freshness và confidence
Stale graph/memory bị hạ dưới current source. Confidence của claim đã reconcile ghi
theo số nguồn đồng thuận sau khi loại nguồn stale.

## Quy trình degradation
Nếu không verify được bằng source (tool health kém) → đánh dấu claim `unverified`, ghi
degradation, và không dùng claim đó làm nền quyết định high-risk.

## Quy trình
1. Dựng claim matrix.
2. Phân loại từng conflict.
3. Resolve theo authority; ghi `CONFLICTS.yaml` + `RECONCILIATION.md`.
4. Chạy gate `conflicts`.

## Điều kiện dừng
- Mâu thuẫn kiến trúc thật làm thay đổi target architecture → dừng, báo.
- Business ambiguity chỉ user/BA chốt.

## Tác động lên knowledge
Đánh dấu stale graph/memory để refresh; đề xuất supersede claim sai (curator xử lý).

## Đầu ra
`exploration/CONFLICTS.yaml` (resolved) + `RECONCILIATION.md`.

## Handoff tiếp theo

Mỗi resolution material phải emit canonical `Knowledge Trace` với `decision.id`,
`statement`, `type`, `knowledge_questions`, `evidence_ids`, `authority`, `conflicts`,
`assumptions`, `confidence`, `freshness`, `verdict`; unresolved conflict block handoff.
`grounded-brainstorming`.
