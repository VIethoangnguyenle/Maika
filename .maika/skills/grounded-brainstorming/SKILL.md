---
name: grounded-brainstorming
version: '2.0'
description: >
  Dùng khi reconciliation READY và change có nhiều thiết kế khả dĩ: so sánh các
  approach dựa trên evidence đã reconcile, mỗi approach kèm extension seam, blast
  radius, convention, historical failure, DB/migration/security impact và lý do loại.
---

# Grounded Brainstorming

## Mục tiêu
So sánh các approach có căn cứ (không suy đoán thuần model) trước khi viết spec, ghi
approach được chọn + alternatives bị loại vào `RECONCILIATION.md`.

## Khi nào sử dụng
Dùng khi `architecture-reconciler` trả verdict READY và change có nhiều thiết kế khả
dĩ, hoặc cần user duyệt cho scope standard/architectural.

## Khi nào KHÔNG sử dụng
- Change đã bị ràng buộc chặt tới một thiết kế duy nhất.
- Để viết spec/plan.

## Đầu vào
- `RECONCILIATION.md`, `GROUNDING.yaml`, `EVIDENCE_MANIFEST.yaml`, `CONFLICTS.yaml`.
- Durable knowledge (Author DNA, conventions).

## Câu hỏi tri thức
- Mỗi approach cắm vào extension seam nào?
- Approach từng bị thử và fail trong lịch sử chưa? (historical_context_retrieval)
- Approach vi phạm/thoả convention nào? Author DNA nào?

## Loại evidence bắt buộc
- `dependency_path`, `blast_radius` (mỗi approach).
- `incident_reference`, `rejected_approach` (lịch sử).
- `convention_rule`, `author_dna_rule`, `database_object` (nếu persistence).

## Chính sách capability
Capability IDs: `dependency_analysis`, `historical_context_retrieval`,
  `convention_retrieval`, `business_knowledge_retrieval`.
Approach phải dẫn từ evidence đã reconcile, không tạo từ suy đoán.

## Quy trình truy xuất
1. Đọc reconciled evidence + conflicts đã resolve.
2. Recall approach tương tự đã fail (rejected_approach).
3. Tra convention/DNA áp cho từng approach.

## Thứ tự authority và precedence
current source > business contract > durable knowledge (convention/DNA) > historical
memory > inference. Lịch sử fail loại approach, không "cho qua vì cũ".

## Kết quả bắt buộc
2–3 approach, mỗi approach nêu đủ: extension seam, supporting evidence, convention
thoả, convention vi phạm, historical failure, blast radius, database impact, migration
impact, operational risk, security impact, unknowns, confidence, rejection reason.

## Bất biến
- Brainstorming là stance, không phải workflow cứng.
- Visualize tự do; Do visualize sequence phức tạp — ASCII diagram bắt buộc khi có flow/state/data path.
- Sau khi vẽ, capture insight đó vào `RECONCILIATION.md`.
- Giữ focus vào vấn đề user nêu.
- Không approach nào hoàn toàn từ suy đoán model.
- Không viết implementation detail cấp task; không giấu conflict/unknown còn mở.

## Yêu cầu evidence
Mỗi approach cite claim ID hoặc gắn nhãn inference. Lựa chọn architecture/security/
persistence/contract cần user duyệt tường minh.

## Freshness và confidence
Mỗi approach ghi confidence. Approach dựa evidence stale bị hạ confidence và không được
chọn nếu high-risk.

## Quy trình degradation
Thiếu historical recall (provider yếu) → ghi degradation, không kết luận "chưa từng
fail"; giữ approach ở confidence thấp hơn.

## Quy trình
1. Đọc reconciliation READY.
2. Sinh 2–3 approach với đủ thuộc tính bắt buộc.
3. Vẽ ASCII flow/state khi làm rõ quyết định.
4. Ghi approach chọn + rejected alternatives + lý do vào `RECONCILIATION.md`.

## Điều kiện dừng
- Xuất hiện quyết định chỉ user/BA chốt.
- Evidence stale/conflict chưa resolve.
- User từ chối mọi approach khả dĩ.

## Tác động lên knowledge
Rejected approach + lý do được ghi để curator lưu vào Agent Memory sau completion.

## Đầu ra
`RECONCILIATION.md` cập nhật (approach chọn, decision evidence, open questions).

## Handoff tiếp theo
`writing-spec`.
