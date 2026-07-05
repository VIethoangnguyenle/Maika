# Snapshot Promotion

> Tài liệu tham khảo cho `knowledge-curator`. Đọc khi cập nhật `knowledge-snapshot.md` sau task đã hoàn thành.

## Mục lục

- Các bước cập nhật
- Promotion criteria
- Phân vùng store
- Stale confidence decay

## Các bước cập nhật

1. Đọc EXPLORE_CONTEXT.md và AGENT_TRANSPARENCY.md của task đã hoàn thành.
2. Phân loại từng discovery bằng bảng Promotion Criteria.
3. Promote code/DB fact có thể tái sử dụng vào `knowledge-snapshot.md` với metadata:
   `source:{ticket-id} seen:{YYYY-MM} verified:{YYYY-MM} status:active`.
4. Nếu entry cũ đã cover cùng concept:
   - Cùng fact: cập nhật `verified`.
   - Mâu thuẫn: đánh dấu entry cũ `status:superseded`, thêm entry mới, và nêu source bị supersede.
   - Chưa rõ: đánh dấu entry cũ `status:outdated` và yêu cầu verify thủ công.
5. Thêm history row với ticket, ngày, và số entry thêm/cập nhật.

## Promotion criteria

| Bucket | Điều kiện | Hành động |
|---|---|---|
| PROMOTE -> snapshot | Có DB/code evidence trực tiếp, tái sử dụng được qua nhiều task, không chỉ là context riêng của ticket, không thuộc convention/DNA | Thêm vào đúng section của snapshot cùng metadata |
| REDIRECT -> conventions | Quy tắc naming, coding style, design pattern boundary, cấu trúc folder/package | Đề xuất cập nhật `conventions.yaml` hoặc `conventions.draft.yaml` |
| REDIRECT -> author-dna | Triết lý lập trình, lý do chọn pattern, judgment principle | Đề xuất cập nhật `author-dna.yaml` hoặc `author-dna.draft.yaml` |
| ARCHIVE only | Workaround riêng cho ticket, tranh luận chưa resolve, context business hẹp | Giữ trong archive EXPLORE_CONTEXT.md |
| DISCARD | Suy luận thuần không có evidence, trùng với snapshot entry tốt hơn, PII/secret | Không lưu |

## Phân vùng store

| Loại nội dung | Store | Ví dụ |
|---|---|---|
| Sự thật về hệ thống | `knowledge-snapshot.md` | Table có column, module gọi module |
| Quy tắc viết code | `conventions.yaml` | Quy tắc naming/package/style |
| Triết lý hoặc judgment principle | `author-dna.yaml` | Vì sao prefer một pattern |
| Bài học vận hành | agent memory | Incident hoặc bài học fix |

Viết conventions/DNA ở mức pattern. Tên table/class cụ thể thuộc phần evidence, không nằm trong text rule generic. Nếu một rule chỉ áp dụng cho một table hoặc class, coi đó là snapshot fact.

## Stale confidence decay

Với mỗi active snapshot entry:

- Nếu `verified` cũ hơn 90 ngày và task hiện tại chạm vào khu vực đó, cập nhật `verified` và giữ `confidence:high`.
- Nếu `verified` cũ hơn 90 ngày và task hiện tại không chạm vào khu vực đó, đánh dấu `confidence:low` nhưng không đổi status.
- Nếu `verified` cũ hơn 180 ngày và confidence đã low, thêm `<!-- needs-reverify -->`.
- Khi dùng stale entry, nêu stale status trong output và cross-check bằng Understand-Anything trước khi dựa vào nó.
