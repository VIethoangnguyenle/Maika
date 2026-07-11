---
name: intent-analysis
version: '3.0'
description: 'Dùng khi một request/ticket mới vào hoặc workspace resume thiếu INTENT.md:
  recall lịch sử, tra Author DNA/convention, tìm source touchpoint, nhận diện tín
  hiệu rủi ro, phân loại change và sinh QUERY_PLAN.yaml trước khi thiết kế.'
routing:
  mode: workflow
  actions:
  - start
  states:
  - NONE
  classes:
  - trivial
  - small
  - standard
  - architectural
capabilities:
  required:
  - business_knowledge_retrieval
  - convention_retrieval
  - exact_source_inspection
  - historical_context_retrieval
outputs:
  required:
  - CHANGE.yaml
  - STATE.yaml
  optional:
  - INTENT.md
  - exploration/QUERY_PLAN.yaml
  - TASK.yaml
  - EVIDENCE.yaml
  - RESULT.yaml
gates:
- intent
---
# Intent Analysis

## Mục tiêu
Biến request thô thành change record cụ thể (`CHANGE.yaml`, `INTENT.md`) và sinh
`QUERY_PLAN.yaml` — classification có confidence, dựa trên recall lịch sử và tín
hiệu source/rủi ro, không thiết kế giải pháp.

## Khi nào sử dụng
Dùng khi một `/task` mới bắt đầu, khi workspace resume thiếu `INTENT.md`, hoặc khi
implementation phát hiện scope có thể reclassify change.

## Khi nào KHÔNG sử dụng
- Khi đã có `INTENT.md` + `QUERY_PLAN.yaml` hợp lệ cho change hiện tại.
- Để đề xuất kiến trúc hay viết application code.

## Đầu vào
- Text request/ticket.
- `CHANGE.yaml`/`INTENT.md` hiện có (nếu resume).
- Durable knowledge (`knowledge/long-term/`), current source (touchpoint).

## Câu hỏi tri thức
- Change tương tự từng làm/từng fail chưa? (historical_context_retrieval)
- Author DNA/convention nào liên quan sớm? (convention_retrieval)
- Request chạm module/file nào đầu tiên? (exact_source_inspection)
- Có tín hiệu persistence/async/security/public-contract không?

## Loại evidence bắt buộc
- `incident_reference`, `decision_reference` (zero-result hợp lệ).
- `author_dna_rule`, `convention_rule`.
- `file_symbol` (touchpoint ban đầu).

## Chính sách capability
Capability IDs: `historical_context_retrieval`, `convention_retrieval`,
  `business_knowledge_retrieval`, `exact_source_inspection`.
Recall lịch sử là bắt buộc cho change standard and architectural trước khi chốt class.

## Quy trình truy xuất
1. Recall Agent Memory theo từ khoá request (history-first).
2. Tra Author DNA/convention liên quan.
3. Trace touchpoint source ban đầu để ước lượng blast radius.
4. Tổng hợp tín hiệu rủi ro.

## Thứ tự authority và precedence
current source > business contract hiện hành > durable knowledge > historical memory
> inference. Memory nâng risk lên, không hạ xuống.

## Kết quả bắt buộc
- `CHANGE.yaml`: `change_id`, `class` ∈ {trivial,small,standard,architectural}, `title`, `created_at`.
- `INTENT.md`: summary, lý do class, non-goals, blocker đã biết, confidence.
- `QUERY_PLAN.yaml`: câu hỏi + required_capabilities + required_evidence_types.
- Change standard and architectural được route sang `grounding-explorer`.

## Bất biến
- Không đề xuất kiến trúc. Không viết application code.
- Không hạ thấp rủi ro public contract/persistence/security/migration.

## Yêu cầu evidence
Classification cite text request chính xác hoặc inference tường minh. Nếu memory hoặc
source cho thấy blast radius lớn hơn → **tăng** class.

## Freshness và confidence
Ghi confidence của classification. Recall rỗng nhưng provider khỏe = evidence hợp lệ,
ghi lại; không coi là "không có rủi ro".

## Quy trình degradation
Nếu Agent Memory/knowledge không khỏe → ghi degradation trong `INTENT.md`, hạ
confidence, và mặc định phân loại thận trọng (không hạ class).

## Quy trình
1. Recall + tra DNA/convention + tìm touchpoint (Quy trình truy xuất).
2. Nhận diện tín hiệu persistence/async/security/public-contract.
3. Phân loại + ghi confidence.
4. Sinh `CHANGE.yaml`, `INTENT.md`, `QUERY_PLAN.yaml`.
5. Chạy gate `intent` (+ `query-plan` khi standard/architectural).

## Điều kiện dừng
- Request mâu thuẫn/thiếu tới mức không phân loại được → hỏi user/BA.
- Phát hiện quyết định public-contract/security chỉ user chốt.

## Tác động lên knowledge
Không ghi durable knowledge; chỉ tạo change record + query plan. Ghi lại recall đã
chạy (kể cả zero-result) để reviewer kiểm.

## Đầu ra
`CHANGE.yaml`, `INTENT.md`, `exploration/QUERY_PLAN.yaml`.

## Handoff tiếp theo
`grounding-explorer` (standard/architectural) hoặc `writing-plan` (small).
