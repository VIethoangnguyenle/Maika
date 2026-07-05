---
name: architecture-reviewer
version: '1.1'
description: >
  Đối chiếu REQUIREMENT với kiến trúc + codebase thực tế (DB + code), phát hiện xung đột và rủi ro.
  Dùng khi cần đánh giá impact kiến trúc, phát hiện breaking changes, hoặc review contract design.
  KHÔNG dùng cho: chuẩn hoá yêu cầu (→ requirement-analyst),
  khám phá code chi tiết (→ codebase-explorer), validate spec đã sinh (→ spec-validator).
pre_conditions:
  - file: "{{ platform.framework_root }}/knowledge/active/REQUIREMENT.md"
    condition: not_skeleton
    on_fail: "ABORT — chạy requirement-analyst trước"
  - file: "{{ platform.framework_root }}/knowledge/active/EXPLORE_CONTEXT.md"
    condition: not_skeleton
    on_fail: "WARN — EXPLORE_CONTEXT thiếu, độ tin cậy kiến trúc sẽ là TRUNG BÌNH — cân nhắc chạy db-explorer / codebase-explorer trước"
  - file: "{{ platform.framework_root }}/knowledge/long-term/conventions.yaml"
    condition: exists
    on_fail: "WARN — conventions.yaml chưa có, đánh giá boundary không đầy đủ"
    load_scope: full  # override selective loading — arch-reviewer cần toàn bộ design_patterns
  - file: "{{ platform.framework_root }}/knowledge/long-term/author-dna.yaml"
    condition: exists
    on_fail: "WARN — author-dna.yaml chưa có, hard principles không được áp dụng"
    load_scope: hard_principles+complexity_thresholds  # pattern_preferences không cần ở Pha 1
---

# Architecture Reviewer — Đánh giá kiến trúc dựa trên trạng thái thực tế

## Mục tiêu

- Đối chiếu REQUIREMENT với kiến trúc hiện tại: service/module, DB, integration, boundary.
- Phát hiện xung đột kiến trúc, data risk, coupling, NFR risk.
- Ghi kết quả LOW / MEDIUM / HIGH / BLOCKER kèm Độ tin cậy.

Skill này không thiết kế kiến trúc mới từ đầu. Nó soi yêu cầu so với kiến trúc hiện hữu và nêu điểm cần xử lý trước khi spec/apply.

## Khi nào dùng

- REQUIREMENT.md đã tương đối ổn định.
- Đã có db-explorer/codebase-explorer hoặc limitation được ghi rõ.
- Trước OpenSpec `/opsx:propose` hoặc trước khi giao implementation.

## Khi nào KHÔNG sử dụng

- Không dùng như công cụ refactor code chi tiết.
- Không thay thế quyết định kiến trúc cấp tổ chức.
- Không dùng khi chưa có REQUIREMENT.md.
- Không dùng để validate spec đã sinh (→ spec-validator).

## Input / Output

Input chính:
- `{{ platform.framework_root }}/knowledge/active/REQUIREMENT.md`
- `{{ platform.framework_root }}/knowledge/active/EXPLORE_CONTEXT.md`
- `{{ platform.framework_root }}/knowledge/long-term/knowledge-snapshot.md`
- `{{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md`

Output: cập nhật `EXPLORE_CONTEXT.md` với section `### Đánh giá kiến trúc cho yêu cầu hiện tại (architecture-reviewer)`.

## Nguyên tắc Độ tin cậy

- UA + db-explorer + codebase-explorer đều chạy ổn → có thể CAO nếu evidence đủ.
- UA thiếu → tối đa TRUNG BÌNH cho topology/boundary.
- db-explorer thiếu → tối đa TRUNG BÌNH cho dữ liệu.
- Cả UA và db-explorer thiếu → không được đặt confidence CAO.

## UA-first invariant

Kết luận về boundary/topology/cross-service/async phải dùng Understand-Anything trước:

- Chạy `{{ tools.domain_relationships }}` để xác định ownership và dependency xuyên service.
- Chạy `{{ tools.domain_flow }}` để xác định topology REST/gRPC/Kafka/job.
- Chỉ dùng Codebase Memory sau khi UA đã định vị node/flow, nhằm đọc chi tiết source.
- Chỉ dùng grep như fallback. Codebase Memory lỗi không có nghĩa là UA unavailable.
- UA là probe chủ động cho topology/boundary, không chỉ là cờ confidence.
- Codebase Memory và grep KHÔNG được định hình kiến trúc cross-service; chúng chỉ xác minh code-fact nội-service sau UA.

Đọc [references/ua-boundary-doctrine.md](references/ua-boundary-doctrine.md) trước khi kết luận về topology, async, Kafka, gRPC, hoặc cross-service.

## Quy trình mỏng

1. Kiểm tra trạng thái tool và đặt confidence ceiling.
2. Tóm tắt kiến trúc hiện tại từ REQUIREMENT, EXPLORE_CONTEXT, snapshot.
3. So sánh As-is / To-be với kiến trúc hiện tại.
4. Review boundary, ownership, topology, và coupling theo UA-first.
5. Review tác động dữ liệu dựa trên evidence từ db-explorer.
6. Review tác động NFR: performance, reliability, observability.
7. Ghi đánh giá kiến trúc và đề xuất next action.

Đọc [references/review-flow-guide.md](references/review-flow-guide.md) khi cần chạy đầy đủ review flow.

## Check tùy chọn

- Đọc [references/infra-tdd-trigger.md](references/infra-tdd-trigger.md) khi review phát hiện tác động HIGH/BLOCKER tới infrastructure, platform, integration, DB, hoặc contract.
- Đọc [references/contract-completeness-check.md](references/contract-completeness-check.md) khi REQUIREMENT.md có Technical Design Contract.
- Đọc [references/gotchas.md](references/gotchas.md) khi xuất hiện câu hỏi về confidence, conventions, contract, hoặc upstream library.
