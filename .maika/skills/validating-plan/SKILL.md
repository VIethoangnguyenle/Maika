---
name: validating-plan
version: '3.0'
description: 'Dùng khi writing-plan tạo IMPLEMENTATION_PLAN.md và trước khi compile/dispatch:
  kiểm hai tầng — mechanical (metadata/hash/anchor/DAG/AC/write-scope/capsule) và
  knowledge integrity (freshness/provider obligation/DNA/convention/incident/DB/conflict).'
routing:
  mode: workflow
  actions:
  - validate-plan
  states:
  - PLAN_REVIEW
  classes:
  - standard
  - architectural
capabilities:
  required:
  - convention_retrieval
  - dependency_analysis
  - exact_source_inspection
  - historical_context_retrieval
  - runtime_verification
outputs:
  required:
  - generated/PLAN_VALIDATION.json
  optional:
  - generated/PLAN_MANIFEST.json
  - generated/TASK_QUEUE.json
gates:
- vnext-plan
- plan-review
---
# Validating Plan

## Mục tiêu
Quyết định plan có executable không, chặn plan để implementer tự diễn giải phần mơ hồ.
Kiểm hai tầng: mechanical và knowledge integrity.

## Khi nào sử dụng
Dùng sau khi `writing-plan` tạo `IMPLEMENTATION_PLAN.md`, trước khi compile/dispatch.

## Khi nào KHÔNG sử dụng
- Chưa có plan.
- Để tự sửa plan (chỉ ra verdict + findings; sửa là việc của writing-plan).

## Đầu vào
- `SPEC.md`, `IMPLEMENTATION_PLAN.md`, `EVIDENCE_MANIFEST.yaml`, `CONFLICTS.yaml`.
- Task knowledge capsule; current source.

## Câu hỏi tri thức
- Hash/anchor/DAG/AC có khớp và hợp lệ không?
- Evidence còn fresh? Provider obligation có được tuân? DNA/convention có bị vi phạm?
- Incident lịch sử liên quan đã cover? DB coverage đủ? Conflict đã resolve?

## Loại evidence bắt buộc
- `file_symbol`, `dependency_path` (verify anchor).
- `incident_reference`, `convention_rule`, `author_dna_rule`, `database_object`.

## Chính sách capability
Capability IDs: `exact_source_inspection`, `dependency_analysis`,
  `historical_context_retrieval`, `convention_retrieval`, `runtime_verification`.
Reviewer knowledge-grounded độc lập, không tin plan mù quáng.

## Quy trình truy xuất
1. Parse plan frontmatter + task sections.
2. Re-verify anchor/symbol/delete-target bằng current source độc lập.
3. Re-check freshness evidence + incident coverage qua memory.

## Thứ tự authority và precedence
current source > business contract > durable knowledge > memory > inference. Anchor
plan sai với source → REVISE, không APPROVED.

## Kết quả bắt buộc
- Tầng mechanical: metadata, hash, base commit, file, symbol, DAG acyclic, AC coverage,
  write scope, delete target, tham chiếu task capsule.
- Tầng knowledge integrity: evidence freshness, provider obligation, DNA compliance,
  convention compliance, historical incident coverage, DB coverage, architecture
  compatibility, delete consumer analysis, conflict resolution.

## Bất biến
- Chỉ plan `APPROVED` được execute.
- Không placeholder; không undeclared write scope; không uncited contract/architecture change.

## Yêu cầu evidence
Verify source anchor, symbol, delete target, expected failing/passing test, evidence ID.
Capsule phải có hash + freshness hợp lệ.

## Freshness và confidence
Spec hash + evidence hash khớp artifact hiện tại; base commit resolve được. Evidence
stale → verdict STALE.

## Quy trình degradation
Không verify được anchor (tool health kém) → không APPROVED; trả BLOCKED với lý do,
yêu cầu re-grounding thay vì cho qua.

## Quy trình
1. Parse + verify hash/base commit.
2. Kiểm anchor file/symbol + AC coverage + DAG.
3. Kiểm knowledge integrity (freshness/obligation/DNA/convention/incident/DB/conflict).
4. Chạy `vnext-plan`; trả verdict.

## Điều kiện dừng
- Plan stale.
- Thiếu AC bắt buộc hoặc section migration/rollback/security.
- Anchor source bắt buộc thiếu.

## Tác động lên knowledge
Ghi finding về stale evidence/incident chưa cover để writing-plan/curator xử lý.

## Đầu ra
`generated/PLAN_VALIDATION.json` + verdict `APPROVED` / `REVISE` / `STALE` / `BLOCKED`.

## Handoff tiếp theo
Plan compiler, rồi `executing-task`.
