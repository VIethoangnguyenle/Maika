# [M7] Hook đẩy Agent Memory sau task

> Reference file — extracted from SKILL.md for progressive disclosure.

## Mục lục

- Trigger
- 3 tầng lọc chất lượng
- Gọi `{{ tools.dynamic_memory_save }}`
- Hướng dẫn chọn kind
- Chống trùng (dedup-by-search, KHÔNG upsert)
- Ghi AGENT_TRANSPARENCY

## Trigger

Gọi SAU `update_knowledge_snapshot` và TRƯỚC `reset_active_context`.
Chỉ khi `status == "completed"` (không push cho stashed/cancelled).
Push tự động ngay từ task hoàn thành đầu tiên — không có giai đoạn làm quen.
User có thể từ chối push trực tiếp trong phiên (nói rõ trước khi curator chạy).

## 3 tầng lọc chất lượng

Trước khi gọi `{{ tools.dynamic_memory_save }}`, curator PHẢI đi qua 3 tầng:

### Tầng 0 — Pre-check (agent-memory có cấu hình không?)

Đọc `resolved-config.yaml → mcps`. Nếu KHÔNG chứa `agent-memory`:
→ Bỏ qua toàn bộ memory push, ghi vào AGENT_TRANSPARENCY: `[M7-SKIP] agent-memory chưa cấu hình`.
→ KHÔNG gọi `{{ tools.dynamic_memory_search }}` hay `{{ tools.dynamic_memory_save }}`.

Nếu có `agent-memory` → tiếp sang Tầng 1.

### Tầng 1 — Gate (CÓ nên lưu không?)

| Câu hỏi | Nếu KHÔNG → hành động |
|---------|----------------------|
| Kiến thức đã verified bằng evidence (code merged, test pass, production ok)? | ❌ **KHÔNG LƯU** — chỉ là suy đoán |
| Có value cho task tương lai không? Có khả năng tái sử dụng? | ❌ **KHÔNG LƯU** — chỉ đúng cho task này |
| Có PII, credential, hoặc sensitive data không? | ❌ **KHÔNG LƯU** — vi phạm R-Data-1 |

Nếu cả 3 điều kiện đều đạt → tiếp sang Tầng 2.
Nếu bất kỳ điều kiện nào KHÔNG đạt → bỏ qua memory push, ghi vào AGENT_TRANSPARENCY: `[M7-SKIP] Lý do: {reason}`

### Tầng 2 — Dedup (đã có record cùng topic chưa?)

```
CALL: {{ tools.dynamic_memory_search }}(query="<project> <topic_summary>", limit=3)

NẾU kết quả trả về có record cùng topic (similarity cao):
  → Kiến thức KHÔNG đổi → BỎ QUA, không lưu trùng.
  → Kiến thức CÓ cập nhật → lưu bản mới, ghi rõ đầu `content`:
     "Cập nhật kiến thức trước: {lý do}".

NẾU không có record tương tự:
  → Lưu bản mới.
```

> `{{ tools.dynamic_memory_search }}` (agentmemory) **không có tham số lọc project** → đưa tên project vào
> đầu `query` để ưu tiên đúng phạm vi (xem Recall guidance ở `rules-tool`).
> Lưu ý: Bước search này KHÔNG tính vào memory budget Pha 3 (nó là một phần của curator hook, không phải reasoning).

### Tầng 3 — Quota

- Tối đa **1 `{{ tools.dynamic_memory_save }}` call** per task (R-Exec-3).
- Nếu task có nhiều bài học → chọn **1 cái quan trọng nhất**, tổng hợp các cái khác vào `content`.

## Gọi `{{ tools.dynamic_memory_save }}`

```
{{ tools.dynamic_memory_save }}(
  content  = "<topic 1-dòng> — <kiến thức cô đọng, chỉ fact đã verified>. "
             "[ticket:<ticket-id> · author:<persona.yaml user_info.name|git user.name> · confidence:<high|medium|low>]",
  type     = "<chọn từ kind selection guide bên dưới>",
  project  = "<project identifier from REQUIREMENT.md>",
  concepts = "<keywords phẩy-phân-cách: module/table/service/topic — searchable>",
  files    = "<đường dẫn file liên quan, phẩy-phân-cách — optional>"
)
```

> **Map contract cũ → agentmemory:** `kind`→`type`, `project_id`→`project`;
> `topic`/`author`/`confidence`/`ticket_id` gộp vào `content`+`concepts`.
> `{{ tools.dynamic_memory_save }}` (agentmemory) chỉ nhận `content*, type, concepts, files, project` —
> field lạ bị **drop** (whitelist), nên KHÔNG truyền `ticket_id`/`author`/`confidence` như param rời.

## Hướng dẫn chọn kind

| kind | Khi nào dùng |
|------|-------------|
| `bug_fix` | Task sửa bug — root cause + giải pháp đã xác nhận |
| `architecture_decision` | Quyết định kiến trúc/kỹ thuật quan trọng đã áp dụng |
| `pattern` | Pattern tái sử dụng đã phát hiện hoặc áp dụng |
| `convention` | Quy ước đặt tên/code mới được thiết lập |
| `gotcha` | Bẫy không rõ ràng, pitfall đã gặp và giải quyết |
| `investigation` | Kết quả nghiên cứu **đã xác nhận** (không phải suy đoán) |
| `requirement` | Nhận thức nghiệp vụ quan trọng đã xác thực |
| `deployment` | Bài học vận hành/deploy đã xác nhận |
| `other` | Bất kỳ kiến thức nào đáng nhớ không thuộc các loại trên |

## Chống trùng (dedup-by-search, KHÔNG upsert)

- `{{ tools.dynamic_memory_save }}` (agentmemory) **append-only** — không có khóa idempotency; mỗi call tạo bản ghi mới.
- Vì vậy **Tầng 2 (search-before-save) là bắt buộc** — đây là cơ chế chống trùng duy nhất.
- `ticket_id` chỉ là metadata truy vết nhồi trong `content`/`concepts`, KHÔNG phải primary key.

## Ghi AGENT_TRANSPARENCY

Sau khi push (hoặc bỏ qua), ghi vào AGENT_TRANSPARENCY.md:

```
[M7-MEMORY] Đẩy Agent Memory:
  - Hành động: <đã_đẩy | bỏ_qua | lưu_mới_kèm_note_cập_nhật>
  - ticket_id: <ticket-id>
  - type: <kind>
  - topic: <topic>
  - Kiểm tra chất lượng: <ĐẠT | BỎ_QUA lý_do>
  - Kiểm tra trùng lặp: <không_trùng | bỏ_qua_trùng | lưu_mới_kèm_note>
```
