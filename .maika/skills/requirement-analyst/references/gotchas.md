# Gotcha của Requirement Analyst

> Tài liệu tham khảo cho `requirement-analyst`. Đọc khi parse REQUIREMENT file hiện có hoặc tài liệu ngoài.

## Gotchas

- CRLF/LF line ending: normalize trước khi regex parse.
- Skeleton detection: kiểm nội dung section, không chỉ kiểm heading.
- Confluence conversion: macro có thể thành text nhiễu; đọc raw trước, clean sau.
- Multi-ticket input: tạo một REQUIREMENT cho mỗi ticket hoặc hỏi user chọn một ticket. Không merge ticket không liên quan.
