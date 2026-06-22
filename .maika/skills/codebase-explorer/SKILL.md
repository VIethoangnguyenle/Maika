---
name: codebase-explorer
version: '1.0'
description: >
  Khám phá codebase bằng Codebase Memory + Understand-Anything để map REQUIREMENT → module/service/file liên quan.
  Dùng khi cần tìm module, file, dependency liên quan đến requirement hiện tại.
  KHÔNG dùng cho: khám phá DB schema (→ db-explorer),
  review kiến trúc/rủi ro (→ architecture-reviewer), sinh spec (→ openspec-propose).
pre_conditions:
  - file: "{{ platform.framework_root }}/knowledge/active/REQUIREMENT.md"
    condition: not_skeleton
    on_fail: "ABORT — chạy requirement-analyst trước"
  - file: "{{ platform.framework_root }}/knowledge/active/EXPLORE_CONTEXT.md"
    condition: exists
    on_fail: "WARN — EXPLORE_CONTEXT chưa có, tạo skeleton trước khi ghi"
---

# Codebase Explorer

## 1. Mục tiêu

- Trả lời câu hỏi: **“Yêu cầu này chạm vào những phần code nào?”** ở mức module, service, file, symbol.
- Xây dựng bức tranh high-level về kiến trúc code liên quan tới REQUIREMENT để hỗ trợ:
  - `architecture-reviewer`
  - OpenSpec / propose
  - Ước lượng effort và rủi ro

Skill này chỉ tập trung vào **khảo sát và ghi nhận bối cảnh code**, không thay đổi code và không đề xuất giải pháp chi tiết.

---

## 2. Khi nào dùng

Dùng `codebase-explorer` khi:

- `/task` Pha 1 với input `HAS_TICKET` hoặc requirement đã tương đối rõ
- Nhánh ideation khi cần hiểu codebase hiện tại đang xử lý domain/use case nào
- Trước khi chạy:
  - `architecture-reviewer`
  - OpenSpec `/opsx:propose`

### Structured-first cases

Nếu truy vấn thuộc một trong các nhóm sau, agent **phải dùng provider có cấu trúc (priority cao) trước** rồi mới dùng fallback:

- Hỏi về flow nghiệp vụ end-to-end → `{{ tools.trace_flow }}`, `{{ tools.get_symbol }}`
- Hỏi về cross-module hoặc cross-service interaction → `{{ tools.get_dependencies }}`
- Hỏi về dependency chain hoặc high-level execution flow → `{{ tools.trace_flow }}`, `{{ tools.find_blast_radius }}`

Trong các trường hợp này, **provider có structured query là nguồn chính** để hiểu flow và dependency.
Provider có priority thấp hơn chỉ là bước follow-up để xác nhận chi tiết implementation.

Agent không được tự ý bỏ qua structured provider chỉ vì grep/search cho cảm giác nhanh hơn.

---

## Khi nào KHÔNG sử dụng

- Khi cần khám phá DB schema, constraint, trigger (→ db-explorer).
- Khi cần review kiến trúc, phát hiện xung đột, đánh giá rủi ro (→ architecture-reviewer).
- Khi cần sinh spec kỹ thuật chi tiết (→ openspec-propose).
- Khi chưa có REQUIREMENT.md chuẩn hoá — chạy requirement-analyst trước.
- Khi chỉ cần viết tài liệu mà không cần khám phá code (→ document-writer).

---

## 3. Input

- `{{ platform.framework_root }}/knowledge/active/REQUIREMENT.md`
- (Tuỳ chọn) `{{ platform.framework_root }}/knowledge/active/EXPLORE_CONTEXT.md`
- `{{ platform.framework_root }}/knowledge/long-term/knowledge-snapshot.md` (nếu có)
- Trạng thái tool:
  - Codebase Memory có khả dụng không
  - Repo có sử dụng Understand-Anything không
  - Graph UA đã được build trước đó chưa và còn tin cậy không

---

## 4. Output

Cập nhật `{{ platform.framework_root }}/knowledge/active/EXPLORE_CONTEXT.md` với section:

```md
### Kiến trúc code hiện tại (codebase-explorer)

#### Entry points
- [node_id] Tên — mô tả ngắn

#### Service / module chính
- [node_id] Tên — vai trò [Synchronous API / Background Worker]

#### Data access / adapter
- [node_id] Tên — bảng/collection liên quan

#### Integration / event / job
- [node_id] Tên — loại (Kafka/gRPC/REST)

#### Quan hệ quan trọng
- source_node → relation → target_node

#### Độ tin cậy
- CAO / TRUNG BÌNH / THẤP, kèm giải thích ngắn
```

> [!IMPORTANT]
> Luôn ghi kèm `identifier` (node_id hoặc file path) cho mỗi component quan trọng.
> Điều này cho phép `architecture-reviewer` và OpenSpec dùng `{{ tools.read_file }}(identifier)` để đọc code thực tế mà không cần search lại.

Chỉ ghi những gì cần để skill khác hiểu bối cảnh. Không dump toàn bộ call graph hoặc copy nguyên nội dung file.

---

## 5. Công cụ — Pre-resolved Tools

Các tool đã được resolve tại thời điểm `maika init` — agent gọi trực tiếp, không cần runtime lookup.

### Operations sử dụng

| Operation | Mục đích |
|-----------|----------|
| `{{ tools.code_status }}` | **Luôn gọi đầu tiên** — kiểm tra index health, freshness |
| `{{ tools.search_code }}` | Tìm module/file/class/function liên quan đến REQUIREMENT |
| `{{ tools.get_symbol }}` | Xem chi tiết component: layer, complexity, tags |
| `{{ tools.read_file }}` | **Đọc source code thực tế** — thay thế việc mở file riêng |
| `{{ tools.get_dependencies }}` | Hiểu dependency giữa components |
| `{{ tools.trace_flow }}` | Trace execution flow từ entry point |
| `{{ tools.find_blast_radius }}` | Impact analysis — xem thay đổi ảnh hưởng gì |

**Workflow điển hình**:
```
{{ tools.code_status }} → {{ tools.search_code }}(keyword) → {{ tools.get_symbol }}(id)
                                                            → {{ tools.read_file }}(id)  ⭐ đọc code
                                                            → {{ tools.get_dependencies }}(id)
                                                            → {{ tools.trace_flow }}(id)
```

> [!NOTE]
> Nếu tool không khả dụng (MCP chưa setup hoặc index chưa build),
> agent phải ghi hạn chế và hạ Độ tin cậy tương ứng.
> Không được bịa kết quả cho tool không khả dụng.

---

## 6. Quy trình

### Bước 1 — Chuẩn bị từ REQUIREMENT

Đọc `{{ platform.framework_root }}/knowledge/active/REQUIREMENT.md` và trích:

- Use case chính
- Entity/khái niệm chính
- Hành động chính liên quan tới code

Dùng các mục này làm từ khoá truy vấn.

### Bước 2 — Xác định phạm vi codebase

- Nếu monorepo:
  - Khoanh vùng module/service có khả năng liên quan dựa trên tên thư mục, tài liệu, `knowledge-snapshot.md`
- Nếu single service:
  - Ưu tiên các thư mục code chính như `src`, `app`, `domain`
- **Quan trọng**: Phân loại rõ tính chất của module/service liên quan là phục vụ API (Synchronous) hay xử lý nền (Background Worker / Kafka / Job) để các skill sau dễ dàng check Topology.

Ghi phạm vi khảo sát vào `{{ platform.framework_root }}/knowledge/active/EXPLORE_CONTEXT.md`.

### Bước 3 — Kiểm tra trạng thái công cụ

1. Gọi `{{ tools.code_status }}` để kiểm tra provider:
   - Provider có available không
   - Dữ liệu có đủ mới không
2. Nếu provider OK → dùng làm nguồn chính (Bước 4)
3. Nếu provider không available:
   - Ghi hạn chế vào AGENT_TRANSPARENCY
   - Dùng provider tiếp theo trong detection_order với confidence thấp hơn

Không mặc định yêu cầu rebuild graph/index cho mọi task.

### Bước 4 — Khảo sát codebase

Nếu truy vấn thuộc nhóm `Structured-first`, bước này là **bắt buộc**.

Dùng abstract operations để:

- `{{ tools.search_code }}(keyword)` → tìm module/file/class liên quan đến REQUIREMENT
- `{{ tools.get_symbol }}(id)` → xem metadata component
- `{{ tools.read_file }}(id)` → **đọc code thực tế** để verify logic
- `{{ tools.get_dependencies }}(id)` → hiểu dependency
- `{{ tools.trace_flow }}(id)` → trace flow từ entry point

Nếu cần câu hỏi open-ended, fallback sang `/understand-chat`.

### Bước 5 — Khảo sát bổ sung (nếu cần)

Dùng provider bổ sung để:

- Xác nhận entry point cụ thể
- Tìm file, symbol, call site chính
- Làm rõ phần implementation
- Tìm impact area chi tiết hơn

Nếu truy vấn không thuộc nhóm `Structured-first`, provider bổ sung có thể là điểm bắt đầu.
Nếu thuộc nhóm `Structured-first`, chỉ dùng làm follow-up.

### Bước 6 — Cross-check: Code thủ công + DB cross-reference

#### 6a — Đọc code thủ công (tuỳ chọn)

Nếu cần, đọc nhanh code ở một số file/symbol quan trọng để xác nhận:

- đúng use case
- rẽ nhánh logic chính
- flag/toggle quan trọng
- adapter/integration chính

Chỉ đọc phần cần thiết, không đọc toàn bộ codebase.

#### 6b — DB cross-reference (BẮT BUỘC khi code chạm data layer)

> [!IMPORTANT]
> Khi Bước 4–5 phát hiện code **chạm tới config tables, transaction metadata, hoặc state management** — nhận diện qua các pattern sau:
> - **Factory / Repository / DAO** đọc từ bảng config (`CONFIG_*`, `SYS_*`, `PARAM_*`…)
> - **Entity / Model** map sang bảng transaction hoặc metadata
> - **Enum / Definition** resolve từ giá trị trong DB (ví dụ: `TypeDefinition.fromCode()`)
> - **Adapter / Client** gọi external service dựa trên config DB
>
> → Agent **PHẢI** gọi `db-explorer` hoặc dùng MCP `{{ tools.db_query }}` trực tiếp để **verify data thực tế** trước khi ghi kết luận gap vào EXPLORE_CONTEXT.

Không kết luận gap chỉ từ code nếu gap đó có thể được verify bằng DB.

**Checklist tối thiểu khi trigger**:
1. Xác định bảng config/data liên quan từ Factory/Entity name.
2. Dùng `{{ tools.db_query }}` kiểm tra: bảng có tồn tại không, data đã được seed chưa, constraint có phù hợp không.
3. Ghi kết quả verify vào EXPLORE_CONTEXT — rõ ràng phân biệt "đã có trong DB" vs "cần thêm/sửa".

**Nếu không thể kết nối DB** (MCP unavailable, thiếu quyền…):
- Ghi rõ hạn chế vào AGENT_TRANSPARENCY.
- Hạ độ tin cậy section DB xuống THẤP.
- Không được kết luận gap dựa trên suy luận khi có thể verify bằng DB.

### Bước 7 — Ghi vào EXPLORE_CONTEXT

Cập nhật section `Kiến trúc code hiện tại (codebase-explorer)` theo format chuẩn.

Nếu có khác biệt giữa KG và Codebase Memory:

- Ghi rõ điểm chưa nhất quán
- Đánh dấu cần kiểm tra sâu hơn
- Hạ độ tin cậy nếu cần

> [!IMPORTANT]
> Ghi kèm `identifier` (node_id hoặc file path) cho mỗi entry point, service, adapter quan trọng để các skill downstream có thể gọi `{{ tools.read_file }}(identifier)` trực tiếp.

### Bước 8 — Cập nhật AGENT_TRANSPARENCY

Trong `{{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md`:

- Đánh dấu đã dùng:
  - `codebase-explorer`
  - Provider đã chọn cho `code_exploration` (ghi tên + confidence level)
  - Các operations đã gọi:
    - `[ ] check_availability`
    - `[ ] search_code`
    - `[ ] get_source`
    - `[ ] get_dependencies / trace_flow`
    - `[ ] find_blast_radius`
- Ghi rõ:
  - Provider nào đang active
  - Operations nào không khả dụng (mapping = null)
  - Confidence level của kết quả

---

## 7. Lưu ý

- Giữ nội dung generic, không encode domain cụ thể.
- Không tự động chạy re-index hoặc thao tác nặng trên repo; chỉ gợi ý user khi cần.
- Với truy vấn flow/cross-module, không được bỏ qua structured provider chỉ vì grep/search cho cảm giác nhanh hơn.
- Ưu tiên `{{ tools.read_file }}` để đọc code thay vì mở file thủ công — giúp giữ context gọn và có identifier tracking.
- Skill này chỉ khám phá và ghi nhận codebase cho requirement hiện tại.
- Mọi đề xuất thay đổi kiến trúc hay implement chi tiết thuộc về `architecture-reviewer` và OpenSpec.
---

## Gotchas

- **[G1] Provider phải sẵn sàng trước**: Luôn gọi `check_availability` trước khi dùng operation khác. Nếu chưa sẵn sàng, gợi ý user setup (index, onboard, v.v.).
- **[G2] Identifier consistency**: Dùng cùng loại identifier (node_id hoặc file path) xuyên suốt phiên. Đoán identifier sẽ gây lỗi.
- **[G3] Provider lag**: Nếu user vừa edit code, provider có thể chưa cập nhật (<5s delay). Khi kết quả cũ cho file mới sửa, yêu cầu provider refresh.
- **[G4] Null operations**: Khi provider không hỗ trợ operation (mapping = null), không được suy luận kết quả. Ghi hạn chế rõ ràng.
