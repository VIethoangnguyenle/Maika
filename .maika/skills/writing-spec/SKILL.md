---
name: writing-spec
version: '3.0'
description: 'Dùng khi reconciliation/brainstorming đã xong và cần SPEC.md class-aware:
  map requirement→evidence, delta current→desired, behavior/state model, contract
  ownership, persistence/async/security impact, AC test được và evidence coverage.'
routing:
  mode: workflow
  actions:
  - spec
  states:
  - BRAINSTORMING
  classes:
  - standard
  - architectural
capabilities:
  required:
  - business_knowledge_retrieval
  - convention_retrieval
  - dependency_analysis
  - exact_source_inspection
outputs:
  required:
  - SPEC.md
  optional:
  - generated/SPEC_VALIDATION.json
gates:
- spec
- knowledge-trace
---
# Writing Spec

## Mục tiêu
Sinh `SPEC.md` từ evidence đã grounding (không từ request mơ hồ): mô tả hành vi,
ràng buộc, AC test được, và ánh xạ requirement ↔ evidence.

## Khi nào sử dụng
Dùng sau reconciliation/brainstorming (standard/architectural), hoặc sau grounding
nhẹ (small change).

## Khi nào KHÔNG sử dụng
- Chưa có evidence/grounding.
- Để liệt kê task implementation (đó là plan).

## Đầu vào
- `CHANGE.yaml`, `INTENT.md`, `RECONCILIATION.md`.
- `GROUNDING.yaml`, `EVIDENCE_MANIFEST.yaml`, `CONFLICTS.yaml`.

## Câu hỏi tri thức
- Hành vi hiện tại → mong muốn khác nhau ở đâu (delta)?
- Ai own contract bị chạm? Persistence/async impact ra sao?
- Convention nào áp? Ràng buộc lịch sử nào phải giữ?

## Loại evidence bắt buộc
- `exact_code_fact` (current behavior), `dependency_path` (contract ownership).
- `business_rule`, `convention_rule`, `incident_reference` (ràng buộc lịch sử).
- `database_object` (nếu persistence).

## Chính sách capability
Capability IDs: `exact_source_inspection`, `dependency_analysis`,
  `business_knowledge_retrieval`, `convention_retrieval`.
Chỉ dùng claim từ `EVIDENCE_MANIFEST.yaml`; không thêm fact mới không có nguồn.

## Quy trình truy xuất
1. Trích claim liên quan từ evidence manifest.
2. Re-verify current behavior bằng source khi cần chốt delta.

## Thứ tự authority và precedence
live DB state > current source > business contract > durable knowledge > memory >
inference. Fact chưa chắc phải gắn nhãn assumption + expiry.

## Kết quả bắt buộc
- Requirement-to-evidence map; delta current→desired; behavior + state model.
- Contract ownership; persistence/async impact; ràng buộc lịch sử; convention áp.
- Assumption kèm expiry; AC test được cite evidence; evidence coverage.
- Small: Goal/Current/Desired/AC/Evidence References. Standard/architectural: full contract.

## Bất biến
- Không list task implementation trong spec.
- Không material behavior claim không có nguồn.
- Section persistence/async/security/migration/rollback rõ cho architectural.

## Yêu cầu evidence
Dùng claim ID từ `EVIDENCE_MANIFEST.yaml`.
Diagram phải đánh dấu `unknown`, `assumption`, hoặc `needs BA/PO confirmation` khi fact chưa chắc.

## Freshness và confidence
Assumption ghi expiry condition + confidence. Delta dựa evidence stale → re-ground
trước khi chốt.

## Quy trình degradation
Thiếu evidence bắt buộc cho một requirement → không "đoán bừa"; ghi assumption +
đánh dấu requirement là `blocked-evidence` để re-grounding.

## Quy trình
1. Chọn contract small/full theo `CHANGE.yaml`.
2. Viết behavior + state model + ràng buộc + AC (cite evidence).
3. Thêm diagram khi task có flow, state, integration, callback, job, hoặc data path:

~~~md
#### ASCII Flow / State Diagram

```text
actor -> component -> state
```
~~~

4. Chạy gate `spec`.

## Điều kiện dừng
- Evidence bắt buộc thiếu.
- AC không test được.
- Còn quyết định chỉ user/BA chốt.

## Tác động lên knowledge
Ghi assumption + expiry để reviewer/curator theo dõi; không promote knowledge ở đây.

## Đầu ra
`SPEC.md` (+ `generated/SPEC_VALIDATION.json` khi gate chạy).

## Handoff tiếp theo

Mỗi architecture/public contract/business/persistence/security decision trong spec
phải map tới một canonical `Knowledge Trace`. Evidence reference không thay thế trace;
gate `knowledge-trace` phải pass trước `SPEC_REVIEW` được approve.
`writing-plan`.
