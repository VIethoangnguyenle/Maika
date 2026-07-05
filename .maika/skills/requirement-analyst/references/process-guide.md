# Requirement Analyst Process Guide

> Tài liệu tham khảo cho `requirement-analyst`. Đọc khi cần chạy detailed flow 10 bước.

## Mục lục

- Bước 1 — Thu thập nguồn
- Bước 2 — Xác định loại task
- Bước 3 — Business context
- Bước 4 — UA-first codebase probe
- Bước 5 — As-is / To-be
- Bước 6 — Scope
- Bước 7 — Acceptance Criteria
- Bước 8 — Technical Design Contract
- Bước 9 — Assumption và Requirement Issue
- Bước 10 — Finalise REQUIREMENT.md

## Bước 1 — Thu thập nguồn

Đọc ticket description, comment, attachment, linked doc, và clarification từ user. Dùng spec-extract cho tài liệu dài.

Skill KHÔNG tự ý bịa thêm requirement ngoài nguồn trên; mọi suy luận phải đánh dấu là giả định.

## Bước 2 — Xác định loại task

Phân loại theo định nghĩa:

- `feature`: hành vi mới / luồng mới / màn hình mới chưa tồn tại.
- `fixbug`: hành vi thực tế của hệ thống **sai so với kỳ vọng** (spec, AC, business rule).
- `changerequest`: hành vi hiện tại **đúng** theo thiết kế ban đầu, nhưng business muốn **thay đổi cách hoạt động**.
- `refactor`: cải thiện cấu trúc/nợ kỹ thuật, **không được đổi behaviour quan sát được**.

Nếu chưa chắc, đánh dấu tentative (vd `type: changerequest?`) + note "cần xác nhận với BA/PO". Không "nắn" requirement chỉ để khớp một loại.

## Bước 3 — Business context

Nêu ai gặp vấn đề, đang đau ở đâu, vì sao cần xử lý bây giờ, và done nghĩa là gì từ góc nhìn business.

## Bước 4 — UA-first codebase probe

Chạy `{{ tools.domain_overview }}` và `{{ tools.domain_flow }}` trước khi viết As-is hoặc open question mà code có thể trả lời.

## Bước 5 — As-is / To-be

Tách current behavior khỏi desired behavior. Dùng UA identifier khi có code evidence.

## Bước 6 — Scope

Liệt kê module, API, screen, job, event, data, và report nằm trong hoặc ngoài scope.

## Bước 7 — Acceptance Criteria

Chuẩn hoá từng AC thành precondition, behavior, và observable result.

## Bước 8 — Technical Design Contract

Định nghĩa protocol/interface và schema. Đọc conventions/snapshot trước khi assume pattern.

## Bước 9 — Assumption và Requirement Issue

Assumption là điều chưa nói rõ nhưng đang được coi là đúng. Requirement issue là unknown nghiệp vụ thật, không phải câu hỏi code-trả-lời-được.

## Bước 10 — Finalise REQUIREMENT.md

Đảm bảo đủ section bắt buộc, ngôn ngữ ngắn gọn, và source có thể trace.
