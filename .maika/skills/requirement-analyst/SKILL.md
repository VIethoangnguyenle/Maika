---
name: requirement-analyst
version: '1.1'
standard: SP3
description: >
  Phân tích ticket/tài liệu thành REQUIREMENT.md chuẩn hoá, rõ scope và Acceptance Criteria.
  Dùng khi có ticket link hoặc tài liệu PRD rõ ràng cần chuẩn hoá.
  KHÔNG dùng cho: ideation thô chưa thành ticket (→ openspec-explore),
  extract từ wiki/Confluence dài nhiều trang (→ spec-extract),
  review kiến trúc hoặc đánh giá rủi ro (→ architecture-reviewer).
pre_conditions:
  - file: "{{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md"
    condition: exists
    on_fail: "ABORT — bootstrap chưa chạy, gọi `/task` trước"
---

# Requirement Analyst — Chuẩn hoá REQUIREMENT từ ticket + tài liệu

## UA-first invariant

Trước khi hỏi user, câu hỏi code-trả-lời-được phải tự giải bằng UA-first probe (`{{ tools.domain_overview }}` / `{{ tools.domain_flow }}`). Chỉ unknown nghiệp vụ thật mới hỏi user. Codebase Memory chỉ hỗ trợ đọc logic node sau khi UA đã định vị flow.

## Mục tiêu

Biến ticket/tài liệu/chat thành `{{ platform.framework_root }}/knowledge/active/REQUIREMENT.md` rõ scope, AC, As-is/To-be, contract, assumption, và open question.

## Khi nào dùng

- `/task` Pha 1 với input HAS_TICKET.
- User yêu cầu chuẩn hóa requirement từ ticket/tài liệu.
- Có tài liệu rời rạc nhưng chưa có REQUIREMENT.md chuẩn.

## Khi nào KHÔNG sử dụng

- Ideation thô (→ openspec-explore).
- Wiki/Confluence dài nhiều trang cần extract trước (→ spec-extract).
- Architecture review (→ architecture-reviewer).
- Technical spec generation (→ openspec-propose).

## Input / Output

Input: ticket, linked doc, clarification từ user, và codebase evidence từ UA-first probe.

Output: `{{ platform.framework_root }}/knowledge/active/REQUIREMENT.md`.

Đọc [references/output-schema.md](references/output-schema.md) khi viết full structure của REQUIREMENT.md.

## Quy trình mỏng

1. Thu thập nguồn.
2. Phân loại task: `feature | fixbug | changerequest | refactor`.
3. Viết business context.
4. Chạy UA-first codebase probe.
5. Viết As-is / To-be.
6. Xác định in-scope và out-of-scope.
7. Chuẩn hoá Acceptance Criteria.
8. Viết Technical Design Contract.
9. Lọc assumption và open question.
10. Finalise REQUIREMENT.md.

Đọc [references/process-guide.md](references/process-guide.md) khi cần chạy đầy đủ quy trình.
Đọc [references/ua-open-question-filter.md](references/ua-open-question-filter.md) trước khi hỏi user một open question.
Đọc [references/gotchas.md](references/gotchas.md) khi parse file hiện có hoặc tài liệu ngoài.

## Cập nhật AGENT_TRANSPARENCY

Ghi `[x] REQUIREMENT.md`, `[x] requirement-analyst`, các nguồn đã đọc, limitation lớn, và confidence CAO/TRUNG BÌNH/THẤP.
