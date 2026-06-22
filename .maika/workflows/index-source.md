---
description: Lập chỉ mục mã nguồn dự án trên Socraticode MCP để có khả năng tìm kiếm ngữ nghĩa và đồ thị phụ thuộc
---

Lập chỉ mục mã nguồn dự án trên Socraticode MCP. Đây là workflow độc lập, cũng được gọi tự động trong Phase 4 của `/setup-knowledge`.

**Đầu vào**: Không cần tham số. Sử dụng thư mục dự án hiện tại.

---

## Bước 1 — Xác minh Local Index (CỔNG BẮT BUỘC)

```bash
ls .understand-anything/knowledge-graph.json 2>/dev/null
```

Nếu KHÔNG tìm thấy → **DỪNG**:
> "⚠️ Không tìm thấy knowledge graph. Chạy `/setup-knowledge` trước."

---

## Bước 2 — Kiểm tra Trạng thái Socraticode Hiện tại

Gọi `{{ tools.code_status }}(projectPath)` qua Socraticode MCP.

### Nếu đã lập chỉ mục (chunks > 0, không có indexing đang chạy):

Hiển thị trạng thái hiện tại:

```
## Trạng thái Index Source

| Chỉ số | Giá trị |
|--------|---------|
| Files | <số-file> |
| Chunks | <số-chunk> |
| Lần index cuối | <timestamp> |
| Trạng thái | ✅ Sẵn sàng |
```

**Hỏi user**: "Source đã được index. Lập chỉ mục lại? (Thao tác này sẽ xây dựng lại toàn bộ index)"

- Nếu user xác nhận → tiến tới Bước 3
- Nếu user từ chối → **DỪNG**: "Index đã cập nhật. Không thực hiện thao tác nào."

### Nếu chưa lập chỉ mục (0 chunks hoặc không có collection):

> "Source chưa được index trên Socraticode. Đang bắt đầu indexing..."

Tiến tới Bước 3.

### Nếu đang indexing:

> "⏳ Indexing đang tiến hành... X%"

Nhảy tới Bước 4 (polling).

### Nếu MCP không khả dụng:

→ **DỪNG**:
> "⚠️ Socraticode MCP không khả dụng. Kiểm tra cấu hình MCP trong mcp_config.json"

---

## Bước 3 — Kích hoạt Indexing

Gọi `{{ tools.index_code }}(projectPath)` để bắt đầu indexing.

> "⏳ Đã bắt đầu indexing..."

---

## Bước 4 — Poll cho đến khi Hoàn thành

Poll `{{ tools.code_status }}(projectPath)` mỗi **15 giây**.

Báo cáo tiến độ mỗi lần poll:
> "⏳ Đang indexing source... X% (Y/Z files)"

**Chặn** cho đến khi indexing đạt 100%.

---

## Bước 5 — Báo cáo Hoàn thành

```
## ✅ Source Đã Lập Chỉ mục

| Chỉ số | Giá trị |
|--------|---------|
| Files | <số-file> |
| Chunks | <số-chunk> |
| Thời gian | <thời-gian> |
| Trạng thái | ✅ Sẵn sàng |

Source giờ có thể tìm kiếm qua công cụ Socraticode MCP:
- `{{ tools.search_code }}` — tìm kiếm code ngữ nghĩa
- `{{ tools.get_dependencies }}` — truy vấn đồ thị phụ thuộc
- `{{ tools.semantic_search }}` — khám phá pattern và quy ước
```

---

## Rào chắn

- Local index PHẢI tồn tại trước khi lập chỉ mục Socraticode (tiên quyết setupAiIntegration)
- Luôn hỏi trước khi lập chỉ mục lại source đã được index
- Không được gián đoạn thao tác indexing đang tiến hành
- Workflow này là chỉ đọc — không sửa đổi mã nguồn hoặc file kiến thức
