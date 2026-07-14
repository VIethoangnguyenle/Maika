---
name: knowledge-promoter
version: '1.0'
description: 'Dùng sau khi verification trả VERIFIED và trước archive: validate candidate
  (KNOWLEDGE_IMPACT + learning/TEACHING_MOMENTS), promote/reject/supersede durable knowledge,
  apply teaching moment đã user-confirm vào DNA/conventions, save episodic memory, regenerate
  index và trigger graph refresh — role duy nhất được ghi durable knowledge.'
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
# Knowledge Promoter

## Mục tiêu
Post-VERIFIED promotion: biến candidate đã capture trong change thành durable
knowledge có provenance — promote/reject/supersede, apply teaching moment đã confirm,
save memory, regenerate index, archive workspace.

## Khi nào sử dụng
Chỉ sau khi `verification-before-completion` trả `VERIFIED` và state là `COMPLETED`
(action `archive`).

## Khi nào KHÔNG sử dụng
- Verification chưa pass — không có ngoại lệ.
- Trong lúc implementation (capture là việc của `knowledge-recorder`).
- Để thêm quan sát one-off vào durable knowledge.

## Đầu vào
- `verification/VERIFICATION_REPORT.md` (VERDICT: VERIFIED), `reviews/FINAL_REVIEW.md`.
- `reviews/KNOWLEDGE_IMPACT.yaml` (new_candidates/superseded/stale/memory/graph).
- `learning/TEACHING_MOMENTS.yaml` (record đã `user_confirmed`, pending verification).

## Câu hỏi tri thức
- Candidate nào verified đủ để promote? Candidate nào reject (thiếu evidence)?
- Entry nào stale/superseded? Teaching moment nào đã user-confirm?

## Loại evidence bắt buộc
- `command_result`/`test_result` (verified), `exact_code_fact` (source cho entry mới).
- `incident_reference`, `rejected_approach` (memory save).

## Chính sách capability
Capability IDs: `historical_context_retrieval`, `convention_retrieval`,
`business_knowledge_retrieval`, `version_control`. Promote chỉ sau verified (R-Know-12).

## Quy trình truy xuất
1. Đọc KNOWLEDGE_IMPACT + learning/ candidates.
2. Đối chiếu từng candidate với current source + durable knowledge hiện có.

## Thứ tự authority và precedence
current source (sau change) > durable knowledge > memory. Entry mâu thuẫn source mới →
supersede, không giữ song song.

## Kết quả bắt buộc
- Mỗi candidate có kết quả tường minh: promoted / rejected (kèm lý do) / superseded.
- Teaching moment confirmed → apply vào author-dna/conventions/knowledge-snapshot
  đúng abstraction split. Entry `mechanically_checkable: true` → regenerate ruleset:
  `python3 {{ platform.framework_root }}/tools/rule-projector/projector.py --dna <dna> --conventions <conv> --out generated/`
  → `python3 {{ platform.framework_root }}/tools/rule-projector/backends/checkstyle.py --ir generated/rules.json --out generated/checkstyle.generated.xml`
- Save episodic memory; regenerate `knowledge-index.yaml`; trigger graph refresh.
- Archive workspace + `ARCHIVE_MANIFEST.yaml`.

## Bất biến
- Không promote candidate thiếu evidence/confidence.
- Không ghi đè user-owned knowledge thiếu evidence.
- Không archive verification failed. Direct user directive vẫn giữ provenance đầy đủ.

## Yêu cầu evidence
Mỗi knowledge update cite source file/review/verification artifact + change_id.

## Freshness và confidence
Entry promote ghi provenance + confidence + repository_commit. Refresh ghi thời điểm.

## Quy trình degradation
Agent Memory/graph không khỏe → hoãn save/refresh, ghi `pending-refresh` trong archive
report thay vì bỏ; retry khi provider phục hồi.

## Quy trình
1. Validate VERIFIED + gates (`knowledge-impact`, `skill-feedback`).
2. Promote/reject/supersede candidates; apply confirmed teaching moments.
3. Regenerate index + trigger graph refresh.
4. Archive workspace.

## Điều kiện dừng
- Verification failed; candidate thiếu evidence; archive-readiness fail.

## Tác động lên knowledge
Role DUY NHẤT ghi durable knowledge (kernel §7 Learning Boundary).

## Đầu ra
Durable knowledge cập nhật, `knowledge-index.yaml` regenerated, archive path + report.

## Handoff tiếp theo
Trạng thái change `ARCHIVED`.
