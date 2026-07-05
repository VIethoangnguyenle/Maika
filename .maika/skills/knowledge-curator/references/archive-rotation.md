# Archive Rotation

> Tài liệu tham khảo cho `knowledge-curator`. Đọc khi số archive vượt retention threshold hoặc khi cần cross-repo snapshot reference.

## Mục lục

- Rotate archive
- Rotate transparency log
- Cross-repo snapshot reference
- Gotchas

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
