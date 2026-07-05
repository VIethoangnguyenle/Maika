# REQUIREMENT Output Schema

> Tài liệu tham khảo cho `requirement-analyst`. Đọc khi viết hoặc kiểm final shape của REQUIREMENT.md.

## Mục lục

- Section bắt buộc
- Technical Design Contract
- Integrations & Field Mapping

## Section bắt buộc

- Metadata task.
- Business context & động lực.
- As-is / To-be.
- Scope: in-scope và out-of-scope.
- Acceptance Criteria.
- Technical Design Contract.
- Integrations & Field Mapping.
- Assumption.
- Requirement issue / open question.
- Source note khi cần traceability.

## Technical Design Contract

Định nghĩa protocol, endpoint/topic/service, request/message schema, response/event schema, và architecture constraint.

## Integrations & Field Mapping

Với third-party API work, ghi integration name, direction, protocol/auth, endpoint/source doc, field mapping từ third-party field sang canonical field, transform intent, và unmapped field được mirror vào open question.
