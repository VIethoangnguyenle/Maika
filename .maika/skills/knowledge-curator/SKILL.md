---
name: knowledge-curator
version: '3.0'
description: 'Dùng khi cần vận hành vòng đời tri thức (trước/trong/sau implementation)
  theo bốn mode retrieve/record/reconcile/curate: promote verified knowledge, supersede
  stale, save episodic memory, update DNA/convention, regenerate index, trigger graph
  refresh.'
routing:
  mode: workflow
  actions:
  - archive
  states:
  - COMPLETED
  classes:
  - trivial
  - small
  - standard
  - architectural
capabilities:
  required:
  - business_knowledge_retrieval
  - convention_retrieval
  - historical_context_retrieval
  - version_control
outputs:
  required:
  - ARCHIVE_MANIFEST.yaml
  optional:
  - knowledge/long-term/knowledge-index.yaml
gates:
- knowledge-impact
- skill-feedback
---
# Knowledge Curator

## Mục tiêu
Vận hành vòng đời tri thức bốn mode — `retrieve`, `record`, `reconcile`, `curate` —
để tri thức hoạt động trước, trong và sau implementation, không chỉ trích xuất cuối kỳ.

## Khi nào sử dụng
Dùng khi bắt đầu change (retrieve), khi có discovery/conflict (record/reconcile), và
sau khi `verification-before-completion` trả `VERIFIED` (curate).

## Khi nào KHÔNG sử dụng
- Verification chưa pass (không curate).
- Để thêm quan sát one-off vào durable knowledge.

## Đầu vào
- `VERIFICATION_REPORT.md`, `FINAL_REVIEW.md`, `reviews/KNOWLEDGE_IMPACT.yaml`.
- `SPEC.md`, task results; durable knowledge stores.

## Câu hỏi tri thức
- Knowledge nào đã verified đủ để promote?
- Entry nào stale/superseded? Lesson nào cần save vào Agent Memory?
- Convention/Author DNA candidate nào đủ evidence?

## Loại evidence bắt buộc
- `command_result`/`test_result` (verified), `exact_code_fact` (source cho entry mới).
- `incident_reference`, `rejected_approach` (memory save).

## Chính sách capability
Capability IDs: `historical_context_retrieval`, `convention_retrieval`,
  `business_knowledge_retrieval`, `version_control`.
Promote chỉ sau verified completion (R-Know-12).

## Quy trình truy xuất
1. retrieve: recall knowledge liên quan khi change bắt đầu.
2. record/reconcile: ghi discovery + đánh dấu stale trong quá trình.

## Thứ tự authority và precedence
current source (sau change) > durable knowledge > memory. Entry mâu thuẫn source mới →
supersede, không giữ song song.

## Kết quả bắt buộc
- Promote verified knowledge; supersede stale entry (ghi `superseded_by`).
- Save episodic memory (lesson phòng incident, decision, rejected approach).
- Update Author DNA khi confirmed; update conventions khi đủ repeated evidence.
- Regenerate `knowledge-index.yaml`; trigger graph/index refresh khi cần.
- Archive workspace + archive report.

## Bất biến
- Không thêm one-off vào durable knowledge.
- Không ghi đè user-owned knowledge thiếu evidence.
- Không archive verification failed.

## Yêu cầu evidence
Mỗi knowledge update cite source file/review/verification artifact. Memory save ghi
context + lesson.

## Freshness và confidence
Entry promote ghi provenance + confidence + repository_commit. Index/graph refresh ghi
thời điểm.

## Quy trình degradation
Agent Memory/graph không khỏe → hoãn save/refresh, ghi `pending-refresh` trong archive
report thay vì bỏ; retry khi provider phục hồi.

## Quy trình
1. retrieve (đầu change) → record/reconcile (trong change).
2. curate (sau VERIFIED): promote/supersede/save/update DNA+convention.
3. Regenerate index + trigger graph refresh.
4. Chạy `archive-readiness`; archive workspace.

## Điều kiện dừng
- Verification failed.
- Knowledge update thiếu evidence.
- `archive-readiness` gate fail.

## Tác động lên knowledge
Đây là skill trực tiếp tiến hóa knowledge: promotion, supersession, memory save,
index/graph refresh.

## Đầu ra
Durable knowledge cập nhật, `knowledge-index.yaml` regenerated, archive path + report.

## Handoff tiếp theo
Trạng thái change `COMPLETED`/`ARCHIVED`.
