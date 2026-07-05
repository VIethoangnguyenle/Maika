# Nhận biết OpenSpec

> Tài liệu tham khảo cho `openspec-explore`. Đọc khi cuộc trao đổi chạm tới active OpenSpec change hoặc khi insight cần được capture vào artifact.

## Mục lục

- Kiểm tra context
- Không có active change
- Có active change
- Bảng capture

## Kiểm tra context

Chạy `openspec list --json` khi trạng thái OpenSpec có ảnh hưởng tới cuộc trao đổi.

Đồng thời kiểm tra:
- `{{ platform.framework_root }}/knowledge/active/REQUIREMENT.md`
- `{{ platform.framework_root }}/knowledge/active/EXPLORE_CONTEXT.md`
- `{{ platform.framework_root }}/knowledge/long-term/knowledge-snapshot.md`

## Không có active change

Suy nghĩ tự do. Khi insight đã rõ hình, đề xuất tạo proposal. Không gây áp lực.

## Có active change

Đọc proposal/design/tasks/spec artifact để lấy context và nhắc tới chúng tự nhiên.

## Bảng capture

| Loại insight | Nơi capture |
|---|---|
| Requirement mới | Capability spec liên quan, ví dụ `specs/billing/spec.md` |
| Quyết định design | `design.md` |
| Scope đổi | `proposal.md` |
| Việc mới | `tasks.md` |
| Assumption bị bác bỏ | artifact liên quan |
