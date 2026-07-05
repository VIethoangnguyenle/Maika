# Archive Rotation

> Tài liệu tham khảo cho `knowledge-curator`. Đọc khi số archive vượt retention threshold hoặc khi cần cross-repo snapshot reference.

## Mục lục

- Restore from archive
- Rotate archive
- Rotate transparency log
- Cross-repo snapshot reference
- Gotchas

## Restore from archive

`restore_from_archive(ticket_id)` — điền lại `active/` từ `archive/{ticket_id}/` khi resume task cũ:

1. Kiểm tra `archive/{ticket_id}/` tồn tại → nếu không: ERROR "Không tìm thấy archive cho ticket {ticket_id}".
2. Kiểm tra `active/` có context đang active không → nếu có: WARN và hỏi user có muốn archive trước không.
3. Copy `REQUIREMENT.md`, `EXPLORE_CONTEXT.md`, `AGENT_TRANSPARENCY.md`, và `ideation/` (nếu có) từ archive về `active/`.
4. Thêm note vào `AGENT_TRANSPARENCY.md`: "Restored from archive at <timestamp> — Tiếp tục task {ticket_id}".
5. Báo: "Context restored for ticket {ticket_id}. Ready to continue."

## Rotate archive

Giữ `keep_n=20` ticket folder gần nhất. Với folder cũ hơn, append metadata vào `ARCHIVE_LOG.md`, rồi chỉ xoá folder cũ sau khi ghi log thành công.

## Rotate transparency log

Khi archive chạy, compact các bootstrap entry lặp lại trong active AGENT_TRANSPARENCY nhưng vẫn giữ full log trong archive.

## Cross-repo snapshot reference

Dùng relative path từ project root. Không copy nội dung cross-repo snapshot.

## Gotchas

- Sanitize ticket ID trước khi tạo folder.
- Regex cho bootstrap entry phải support cả format cũ và mới.
- Reset không được clear ideation draft trừ khi đã archive rõ ràng hoặc user yêu cầu.
