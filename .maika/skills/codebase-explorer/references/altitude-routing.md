# Altitude Routing — Chi tiết (codebase-explorer)

## Mục lục

- Cue Cards (phản xạ theo triệu chứng — CUE → ROUTINE → REWARD)
- Bản đồ năng lực (theo ý định — minh họa, KHÔNG whitelist)
- Ví dụ áp dụng
- Output format đầy đủ (EXPLORE_CONTEXT section)
- Operations đầy đủ (Codebase Memory)
- Bước 6b — DB cross-reference (chi tiết)
- Bước 8 — AGENT_TRANSPARENCY checklist đầy đủ

Tài liệu hỗ trợ cho [SKILL.md](../SKILL.md) §2. Đây là chi tiết bổ sung cho doctrine UA-first
đã nêu trong reflex block — không lặp lại nguyên tắc, chỉ minh hoạ cụ thể.

## Cue Cards (phản xạ theo triệu chứng — CUE → ROUTINE → REWARD)

Thói quen được kích bằng triệu chứng gặp *trong lúc làm*, không bằng nguyên tắc trừu tượng:

| CUE (agent nhận ra) | ROUTINE (phản xạ) | REWARD |
|---|---|---|
| Sắp `{{ tools.trace_flow }}`/`{{ tools.get_dependencies }}` vào **base/abstract class nhiều impl** (BaseHandler…) | DỪNG codebase → `{{ tools.domain_flow }}` (UA) | Flow human-readable, bỏ qua hàng chục lớp con nhiễu |
| Call-chain vừa chạm `@KafkaListener`/gRPC stub rồi **đứt lạnh** | Leo thang `{{ tools.domain_flow }}` / `{{ tools.domain_relationships }}` (UA) | Thấy service nói chuyện với nhau ra sao |
| **Chưa biết entry point** (REST? gRPC? Kafka?) | `{{ tools.domain_overview }}` → `{{ tools.domain_flow }}` (UA) **trước** mọi grep | Định vị entry đúng, không suy luận từ Controller |
| Cần quan hệ/blast-radius ở độ cao kiến trúc (service nói chuyện ra sao, ai sở hữu domain) | `{{ tools.domain_relationships }}` (UA) **trước** | Blast-radius đúng tầng, không bị giới hạn bởi method-call nội-service |
| Đã có **node UA cụ thể**, chỉ cần đọc logic trong 1 hàm | Codebase thẳng (`{{ tools.search_code }}` → `{{ tools.get_symbol }}` → `{{ tools.read_file }}`) | Không tốn UA overhead cho việc đọc logic |

Codebase Memory **không** dùng để định hình/kết luận kiến trúc; UA luôn ưu tiên cho câu hỏi kiến trúc,
quan hệ, và blast-radius ở độ cao domain/service. Codebase chỉ extract logic trong thân hàm tại node UA
đã định vị, và đọc code.

## Bản đồ năng lực (theo ý định — minh họa, KHÔNG whitelist)

| Ý định | UA (luôn trước cho kiến trúc) | Codebase Memory (hỗ trợ, sau — đọc logic) |
|---|---|---|
| Map domain / business flow | `{{ tools.domain_overview }}`, `{{ tools.domain_flow }}` | — |
| Quan hệ / blast-radius kiến trúc | `{{ tools.domain_relationships }}` | — |
| Tìm symbol (rộng) | — | `{{ tools.search_code }}`, `{{ tools.list_symbols }}` |
| Truy vấn cấu trúc tùy ý | — | `{{ tools.get_dependencies }}` + `{{ tools.graph_stats }}` |
| Extract logic trong hàm / đọc code | — | `{{ tools.get_symbol }}`, `{{ tools.read_file }}` |
| Xác nhận code-fact nội-service (không định hình kiến trúc) | — | `{{ tools.trace_flow }}`, `{{ tools.find_blast_radius }}` |

> Golden Path là **sàn, không phải trần**. Bảng trên minh họa, KHÔNG đầy đủ — cả hai MCP tự expose
> danh sách tool đầy đủ lúc runtime. Ngoài Golden Path, chọn tool theo **ý định**; truy vấn lạ thì dùng
> `{{ tools.graph_stats }}` học schema rồi viết Cypher qua `{{ tools.get_dependencies }}`.

## Ví dụ áp dụng

- **"Flow đặt hàng bắt đầu từ đâu?"** → `{{ tools.domain_overview }}` ra domain `order`, rồi
  `{{ tools.domain_flow }}` ra entry point (REST `POST /orders`) + các bước. Codebase Memory
  chỉ vào sau để đọc logic validate/persist trong từng bước.
- **"Service nào sở hữu domain `payment`?"** → `{{ tools.domain_relationships }}` (UA) trước;
  KHÔNG dùng `{{ tools.get_dependencies }}` (Codebase) để suy luận ownership — nó chỉ thấy
  method-call nội-service, không thấy boundary domain.
- **"Đã biết `OrderService.cancel()`, cần sửa logic 1 dòng"** → node UA coi như đã định vị
  (đã có symbol cụ thể) → đi thẳng Codebase: `{{ tools.get_symbol }}` → `{{ tools.read_file }}`.

## Output format đầy đủ (EXPLORE_CONTEXT section)

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

Ghi kèm `identifier` cho mỗi component quan trọng. **identifier kiểu UA** (tên domain / flow /
entry-point) đứng **ngang hàng** `node_id` — mục *Entry points* và *Integration / event / job* ghi
nguồn từ UA là hợp lệ và được khuyến khích. Với component cần đọc code chi tiết downstream, vẫn
nên kèm `node_id`/file-path để `architecture-reviewer` và OpenSpec gọi `{{ tools.read_file }}(identifier)`
trực tiếp.

## Operations đầy đủ (Codebase Memory)

| Operation | Mục đích |
|-----------|----------|
| `{{ tools.code_status }}` | **Luôn gọi đầu tiên** — kiểm tra index health, freshness |
| `{{ tools.search_code }}` | Tìm module/file/class/function liên quan đến REQUIREMENT |
| `{{ tools.get_symbol }}` | Xem chi tiết component: layer, complexity, tags |
| `{{ tools.read_file }}` | **Đọc source code thực tế** — thay thế việc mở file riêng |
| `{{ tools.get_dependencies }}` | Hiểu dependency giữa components |
| `{{ tools.trace_flow }}` | Trace execution flow từ entry point |
| `{{ tools.find_blast_radius }}` | Impact analysis — xem thay đổi ảnh hưởng gì |

## Bước 6b — DB cross-reference (chi tiết)

Khi Bước 4–5 phát hiện code **chạm tới config tables, transaction metadata, hoặc state management**
— nhận diện qua các pattern sau:
- **Factory / Repository / DAO** đọc từ bảng config (`CONFIG_*`, `SYS_*`, `PARAM_*`…)
- **Entity / Model** map sang bảng transaction hoặc metadata
- **Enum / Definition** resolve từ giá trị trong DB (ví dụ: `TypeDefinition.fromCode()`)
- **Adapter / Client** gọi external service dựa trên config DB

→ Agent **PHẢI** gọi `db-explorer` hoặc dùng MCP `{{ tools.db_query }}` trực tiếp để **verify data
thực tế** trước khi ghi kết luận gap vào EXPLORE_CONTEXT. Không kết luận gap chỉ từ code nếu gap đó
có thể được verify bằng DB.

**Checklist tối thiểu khi trigger**:
1. Xác định bảng config/data liên quan từ Factory/Entity name.
2. Dùng `{{ tools.db_query }}` kiểm tra: bảng có tồn tại không, data đã được seed chưa, constraint có phù hợp không.
3. Ghi kết quả verify vào EXPLORE_CONTEXT — rõ ràng phân biệt "đã có trong DB" vs "cần thêm/sửa".

**Nếu không thể kết nối DB** (MCP unavailable, thiếu quyền…): ghi rõ hạn chế vào AGENT_TRANSPARENCY,
hạ độ tin cậy section DB xuống THẤP, không được kết luận gap dựa trên suy luận khi có thể verify bằng DB.

## Bước 8 — AGENT_TRANSPARENCY checklist đầy đủ

Trong `{{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md`, đánh dấu đã dùng:
- `codebase-explorer`
- Provider đã chọn cho `code_exploration` (ghi tên + confidence level)
- Các operations đã gọi: `[ ] {{ tools.code_status }}`, `[ ] search_code`, `[ ] {{ tools.read_file }}`,
  `[ ] get_dependencies / trace_flow`, `[ ] find_blast_radius`

Ghi rõ: provider nào đang active, operations nào không khả dụng (mapping = null), confidence level
của kết quả.
