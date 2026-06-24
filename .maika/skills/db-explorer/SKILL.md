---
name: db-explorer
version: '1.0'
description: >
  Khám phá logic tầng database (SQL + NoSQL) bằng MCP {{ tools.db_query }} để cập nhật EXPLORE_CONTEXT.
  Dùng khi cần hiểu schema, constraint, data flow ở tầng DB cho task hiện tại.
  KHÔNG dùng cho: khám phá code/module (→ codebase-explorer),
  review kiến trúc tổng thể (→ architecture-reviewer), viết tài liệu (→ document-writer).
pre_conditions:
  - file: "{{ platform.framework_root }}/knowledge/active/REQUIREMENT.md"
    condition: not_skeleton
    on_fail: "ABORT — chạy requirement-analyst trước"
---

# DB Explorer — Database → EXPLORE_CONTEXT

## 1. Mục tiêu

- Hiểu rõ **tầng database thực tế đang làm gì**, không chỉ dừng ở schema lý thuyết.
- Phát hiện logic nghiệp vụ ẩn trong:
  - Trigger.
  - Stored procedure / function / package.
  - Constraint (PRIMARY KEY / FOREIGN KEY / UNIQUE / CHECK).
  - View, sequence, index đặc biệt.
- Biến các phát hiện này thành **bức tranh dễ đọc trong `EXPLORE_CONTEXT`** để các skill khác (architecture-reviewer, OpenSpec, codebase-explorer) dùng lại.

Skill này tập trung **khảo sát & ghi nhận**, KHÔNG sinh lệnh DDL/DML, KHÔNG chỉnh sửa data.

---

## 2. Khi nào dùng

Dùng `db-explorer` khi:

- REQUIREMENT có chạm tới dữ liệu:
  - Thêm / sửa / xoá bản ghi.
  - Thay đổi trạng thái, số dư, hạn mức, lịch sử, báo cáo, tổng hợp.
- Có nguy cơ ảnh hưởng tới:
  - Transaction / tính toàn vẹn (integrity).
  - Dữ liệu lịch sử / số liệu tổng hợp.
- Trước khi:
  - Chạy `architecture-reviewer` cho feature/change/refactor lớn.
  - Đề xuất chỉnh sửa schema / logic tầng data trong spec.

> [!IMPORTANT]
> **Quy tắc Chống Hallucination & Thiết kế Bảng mới:**
> 1. Đối với các bảng ĐÃ TỒN TẠI: Tuyệt đối không được đoán mò (hallucinate) cấu trúc. Phải lấy cấu trúc chính xác từ MCP `{{ tools.db_query }}` hoặc thông qua các file JPA `@Entity` từ `codebase-explorer`. Nếu `@Entity` không có cột đó, không được giả định là DB có.
> 2. Đối với các bảng MỚI: Yêu cầu tính năng mới thường đi kèm thiết kế bảng mới. Tuy nhiên, trước khi thiết kế, PHẢI khám phá kỹ các bảng liên quan (bảng cha/con, hoặc bảng có chức năng tương tự) để học hỏi "góc nhìn" và "convention" thiết kế (ví dụ: cách đặt tên, các cột audit bắt buộc, quan hệ khóa ngoại). Không thiết kế bảng lệch tông so với hệ thống hiện tại.

---

## Khi nào KHÔNG sử dụng

- Khi cần khám phá code/module, dependency (→ codebase-explorer).
- Khi cần review kiến trúc tổng thể, phát hiện xung đột (→ architecture-reviewer).
- Khi cần viết tài liệu kỹ thuật (→ document-writer).
- Khi cần sinh spec kỹ thuật chi tiết (→ openspec-propose).
- Khi không có REQUIREMENT.md chuẩn hoá — chạy requirement-analyst trước.

---

## 3. Input

- `{{ platform.framework_root }}/knowledge/active/REQUIREMENT.md`:
  - Entity/khái niệm dữ liệu chính.
  - Luồng xử lý chạm tới dữ liệu.
- (Tuỳ chọn) `{{ platform.framework_root }}/knowledge/active/EXPLORE_CONTEXT.md` và `{{ platform.framework_root }}/knowledge/long-term/knowledge-snapshot.md`:
  - Thông tin database đã từng được khám phá.
- Khả năng truy cập database qua MCP `{{ tools.db_query }}` (hoặc provider tương tự):
  - Ít nhất phải có quyền **đọc metadata** (schema, catalog, system views).
  - Đọc sample data chỉ khi an toàn và được phép.

---

## 4. Công cụ

Sử dụng MCP `{{ tools.db_query }}` (hoặc MCP tương đương) ở mức tổng quát:

- **Đối với SQL database** (ví dụ: Oracle, PostgreSQL, MySQL, SQL Server...):
  - Liệt kê database/schema.
  - Liệt kê bảng, view.
  - Lấy danh sách cột, kiểu dữ liệu, constraint, index.
  - Đọc system catalog / system views để tìm:
    - Trigger.
    - Stored procedure / function / package.
    - Sequence, view đặc biệt.
- **Đối với NoSQL database** (ví dụ: MongoDB, Document DB, key-value store có MCP driver):
  - Liệt kê database/namespace.
  - Liệt kê collection/bucket.
  - Lấy thông tin schema (schema sample / inferred schema).
  - Đọc sample document an toàn (không log PII).

Tên lệnh cụ thể (`list_databases`, `sql_list_tables`, `mongo_list_collections`…) phụ thuộc vào implementation của MCP server, nhưng **quy trình vẫn giữ generic**.

---

## 5. Output

Cập nhật `{{ platform.framework_root }}/knowledge/active/EXPLORE_CONTEXT.md` với section:

```md
### Tầng Database (db-explorer)

#### Database / schema liên quan
- ...

#### Bảng / collection chính
- ...

#### Constraint & index đáng chú ý
- ...

#### Trigger / stored procedure / function
- ...

#### View / sequence / cơ chế đặc biệt khác
- ...

#### Nhận xét & rủi ro
- ...

#### Độ tin cậy
- CAO / TRUNG BÌNH / THẤP (và lý do)
```

Ngoài ra:

- Nếu phát hiện logic nghiệp vụ quan trọng nằm ở DB nhưng REQUIREMENT không nhắc tới → thêm **cảnh báo**.
- Không lưu raw data nhạy cảm; chỉ mô tả cấu trúc và hành vi.

---

## 6. Quy trình tổng quát

### Bước 1 — Chuẩn bị từ REQUIREMENT

1. Từ `{{ platform.framework_root }}/knowledge/active/REQUIREMENT.md`, trích ra:
   - Entity dữ liệu chính (ví dụ: “đơn hàng”, “giao dịch”, “tài liệu”…).
   - Hành động liên quan tới dữ liệu (tạo, cập nhật trạng thái, ghi log, tổng hợp báo cáo…).
2. Ghi danh sách entity/hành động này vào một subsection tạm trong `{{ platform.framework_root }}/knowledge/active/EXPLORE_CONTEXT.md` để dùng làm từ khoá khi tìm kiếm trong DB.

---

### Bước 2 — Xác định database / schema liên quan

1. Dùng MCP `{{ tools.db_query }}` để:
   - Liệt kê database / schema / namespace sẵn có.
2. Kết hợp với:
   - `{{ platform.framework_root }}/knowledge/long-term/knowledge-snapshot.md` (nếu có).
   - Tên/ghi chú của database/schema.
3. Chọn ra tập database/schema **nhiều khả năng liên quan** đến requirement.
4. Ghi vào `{{ platform.framework_root }}/knowledge/active/EXPLORE_CONTEXT.md` một bảng ngắn:
   - Tên database/schema.
   - Loại (OLTP/OLAP nếu nhận định được).
   - Mức độ liên quan (cao / vừa / thấp).

---

### Bước 3 — Khám phá cấu trúc bảng/collection

#### Với SQL database

1. Cho từng database/schema đã chọn:
   - Liệt kê bảng và view.
2. Lọc ra các bảng/view **có tên gợi ý liên quan tới entity/hành động** từ Bước 1.
3. Với từng bảng liên quan:
   - Lấy danh sách cột + kiểu dữ liệu + nullable.
   - Đánh dấu:
     - Khóa chính.
     - Khóa ngoại.
     - Cột trạng thái, cột số liệu quan trọng (số tiền, số lượng, điểm, hạn mức…).
     - Cột thời gian (ngày tạo, ngày cập nhật, hiệu lực…).

#### Với NoSQL database

1. Cho từng database/namespace đã chọn:
   - Liệt kê collection.
2. Lọc collection theo tên gợi ý liên quan tới entity/hành động.
3. Với từng collection liên quan:
   - Gọi lệnh schema (hoặc sample-based schema) để hiểu:
     - Các field chính.
     - Document lồng nhau (embedded document) quan trọng.
     - Mẫu field trạng thái, timestamp, số liệu quan trọng.

---

### Bước 4 — Khám phá constraint, index, trigger, stored procedure

#### Constraint & index (SQL)

1. Lấy danh sách constraint cho các bảng liên quan:
   - PRIMARY KEY, FOREIGN KEY, UNIQUE, CHECK.
2. Đặc biệt chú ý:
   - CHECK thể hiện business rule (ví dụ: trạng thái hợp lệ, range giá trị).
   - FOREIGN KEY với hành vi cascade / restrict.
3. Lấy danh sách index:
   - Cột được index.
   - Index đặc biệt (unique index, composite index).

#### Trigger (SQL)

1. Liệt kê trigger gắn với các bảng liên quan:
   - Bảng, sự kiện (INSERT/UPDATE/DELETE), thời điểm (BEFORE/AFTER).
2. Nếu cần hiểu rõ:
   - Đọc body hoặc tóm tắt logic (theo mức khái quát).
3. Ghi lại:
   - Trigger nào có logic nghiệp vụ rõ ràng (ví dụ: tự động tính toán, cập nhật bảng khác, ghi log quan trọng).

#### Stored procedure / function / package (SQL)

1. Liệt kê stored procedure/function/package trong schema liên quan.
2. Lọc theo từ khoá entity/hành động từ Bước 1 (nếu MCP hỗ trợ search).
3. Với các object quan trọng:
   - Ghi tên, mục đích (mô tả khái quát).
   - Không cần dump toàn bộ source; chỉ tóm lược vai trò.

#### Cơ chế đặc biệt khác

Tuỳ loại DB có thể có thêm:

- View quan trọng (tổng hợp dữ liệu, ẩn logic join phức tạp).
- Sequence / generator cho khoá chính.
- Rule/policy (row-level security, partition, retention).

Ghi nhận những cơ chế này nếu chúng ảnh hưởng tới requirement.

---

### Bước 5 — (Tuỳ chọn) Sample dữ liệu an toàn

Áp dụng **chỉ khi được phép** và tránh PII:

1. Với một vài bảng/collection quan trọng:
   - Lấy sample một số bản ghi bằng MCP (limit nhỏ, filter an toàn).
2. Mục đích:
   - Hiểu pattern giá trị (trạng thái, enum, workflow).
   - Xác nhận field nào thực sự được dùng trong thực tế.
3. Không log raw data nhạy cảm vào file:
   - Chỉ tóm tắt ở mức pattern (ví dụ: “field `status` có các giá trị chính: X, Y, Z”).

---

### Bước 6 — Map phát hiện vào EXPLORE_CONTEXT

Trong `{{ platform.framework_root }}/knowledge/active/EXPLORE_CONTEXT.md`, cập nhật section:

```md
### Tầng Database (db-explorer)

#### Database / schema liên quan
- ...

#### Bảng / collection chính
- Tên, vai trò ngắn gọn, cột/field quan trọng.

#### Constraint & index đáng chú ý
- Mô tả các rule, ràng buộc và lý do quan trọng.

#### Trigger / stored procedure / function
- Bảng/collection gắn với trigger.
- Hành vi high-level (ví dụ: tự động cập nhật status, ghi log, đồng bộ bảng khác).

#### View / sequence / cơ chế khác
- Những thành phần có tác động rõ tới dữ liệu cho requirement.

#### Nhận xét & rủi ro
- Điểm cần lưu ý khi chỉnh sửa schema hoặc logic.
- Chỗ REQUIREMENT khác biệt với hành vi hiện tại ở DB.

#### Độ tin cậy
- CAO / TRUNG BÌNH / THẤP, giải thích ngắn (ví dụ: thiếu quyền đọc một số schema).
```

Nếu có các tình huống đặc biệt:

- Logic nghiệp vụ quan trọng nằm hoàn toàn trong trigger/procedure nhưng REQUIREMENT bỏ qua.
- Constraint hiện tại mâu thuẫn với requirement mới.

→ Ghi rõ thành **cảnh báo** để architecture-reviewer & spec lưu ý.

---

## 7. Cập nhật AGENT_TRANSPARENCY

Trong `{{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md`:

- Đánh dấu:
  - `[x] db-explorer`
  - Database/engine nào đã được khảo sát (ví dụ: “SQL engine A, NoSQL engine B”).
- Ghi cảnh báo nếu:
  - Không kết nối được tới một số database/schema.
  - Không có quyền đọc system catalog / system views / schema.
  - Sample data không được phép truy cập.
- Ghi đánh giá tổng quan:
  - Mức độ hiểu biết về tầng DB cho requirement này: CAO / TRUNG BÌNH / THẤP, và lý do.

---

## 8. Lưu ý

- Không hard-code bất kỳ tên bảng/collection/domain cụ thể nào trong SKILL; mọi ví dụ nên ở dạng khái quát (`<entity>`, `<status>`, `<amount>`...).[web:120][web:170]
- Không sinh, không chạy lệnh DDL/DML thay đổi dữ liệu/schema trong scope skill này.
- Luôn ưu tiên **metadata và pattern** hơn raw data, để tránh rủi ro bảo mật và PII.
---

## Gotchas

- **[G1] Oracle schema prefix bắt buộc**: Mọi query Oracle PHẢI có schema prefix (`SCHEMA.TABLE`). Query không prefix sẽ bị MCP {{ tools.db_query }} block hoặc trả kết quả sai schema.
- **[G2] MongoDB collection names case-sensitive**: `userProfiles` ≠ `UserProfiles`. Luôn dùng `mongo_list_collections` trước khi query để lấy tên chính xác.
- **[G3] Timeout cho query nặng**: Query `sql_read` có timeout mặc định ngắn. Nếu scan bảng lớn (>100k rows), dùng `FETCH FIRST {n} ROWS ONLY` hoặc `WHERE ROWNUM <= {n}`.
- **[G4] Không thể write**: MCP {{ tools.db_query }} chỉ hỗ trợ SELECT/find. Mọi INSERT/UPDATE/DELETE/DDL sẽ bị block. Không cần thử — chỉ ghi nhận schema/data pattern.
