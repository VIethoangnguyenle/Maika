---
name: knowledge-retriever
version: '1.0'
description: 'Dùng khi một phase cần recall tri thức đang có: durable knowledge
  (DNA/conventions/snapshot qua knowledge-index slice), episodic memory (incident,
  decision cũ, rejected approach) và business knowledge — trả slice nhỏ nhất liên quan
  kèm provenance/freshness, không ghi gì vào durable stores.'
routing:
  mode: conditional
  states: []
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
outputs: {}
gates: []
---
# Knowledge Retriever

## Mục tiêu
Trả về slice tri thức nhỏ nhất liên quan cho phase đang chạy — đọc thuần túy,
có provenance, không side effect.

## Khi nào sử dụng
- Đầu change (intent/grounding cần history, convention, business context).
- Trước material decision cần recall incident/decision cũ/rejected approach.

## Khi nào KHÔNG sử dụng
- Để GHI bất kỳ thứ gì (capture → `knowledge-recorder`; promote → `knowledge-promoter`).
- Khi slice đã có trong context package của phase (không recall lặp).

## Đầu vào
- Knowledge questions của phase; `knowledge-index.yaml` (entry list).

## Câu hỏi tri thức
- Durable entry nào active và applies-to phạm vi hiện tại?
- Memory nào valid / superseded / conflicting / advisory?

## Loại evidence bắt buộc
- `memory_reference`, `decision_reference`, `business_rule`, convention/DNA entry ID.

## Chính sách capability
Capability IDs: `historical_context_retrieval`, `convention_retrieval`,
`business_knowledge_retrieval`. Zero-result là evidence hợp lệ — ghi lại, không bỏ qua.

## Quy trình truy xuất
1. Map knowledge question → capability → provider ưu tiên (jit/providers.md).
2. Kéo entry qua index slice (JIT), không nạp full store.
3. Phân loại kết quả: valid / superseded / conflicting / advisory.

## Thứ tự authority và precedence
Theo R-Know-2; retrieved knowledge KHÔNG ghi đè current source.

## Kết quả bắt buộc
- Slice trả về có entry ID + provenance + freshness + confidence.
- Zero-result được ghi tường minh.

## Bất biến
- Read-only tuyệt đối với durable stores.
- Không recall lặp cùng câu hỏi trong một phase.

## Yêu cầu evidence
Mỗi item trả về cite entry ID / memory ref / doc anchor.

## Freshness và confidence
Ghi freshness state của index/graph; entry stale phải được đánh dấu.

## Quy trình degradation
Provider unavailable → degradation record + fallback đọc trực tiếp file knowledge
long-term; không giả vờ đã recall.

## Quy trình
1. Nhận knowledge questions.
2. Recall theo capability; phân loại; trả slice + provenance.

## Điều kiện dừng
- Câu hỏi ngoài phạm vi tri thức (chuyển cho grounding/source inspection).

## Tác động lên knowledge
Không — read-only.

## Đầu ra
Knowledge slice (trong context package / evidence manifest của phase gọi nó).

## Handoff tiếp theo
Phase đang chạy tiếp tục với slice đã trả.
