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

## Bước 2 — Xác định loại task

Phân loại là `feature`, `fixbug`, `changerequest`, hoặc `refactor`. Nếu chưa chắc, đánh dấu tentative.

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
