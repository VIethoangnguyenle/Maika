# Contract Completeness Check

> Tài liệu tham khảo cho `architecture-reviewer`. Đọc sau Bước 7 và trước kết luận cuối khi REQUIREMENT.md có Technical Design Contract.

## Mục lục

- Check
- Output
- Điều kiện skip

## Check

1. Section tồn tại và có nội dung thật.
2. Nếu `conventions.yaml` tồn tại và đã approve, so sánh protocol/pattern được chọn với conventions.
3. Contract có protocol/interface, request/message schema, và response/event schema.

## Output

Tất cả M6 check chỉ ở mức WARN. Ghi `[M6] Contract Completeness: {PASS|WARN(n)} — {details}` vào `AGENT_TRANSPARENCY.md`.

## Điều kiện skip

Skip khi REQUIREMENT.md dùng template cũ không có contract section, hoặc task type là `refactor`.
