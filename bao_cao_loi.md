# Báo cáo sự cố — Bỏ qua UA khi Explore Codebase

> **Status:** RESOLVED by `docs/superpowers/specs/2026-06-24-ua-first-business-analysis-design.md` (2026-06-24).

| Field | Value |
|---|---|
| **Ngày** | 2026-06-24 |
| **Phiên** | `727c1e4a-84b0-44ae-b100-3c2b692466fd` |
| **Task** | Brainstorm luồng 2.2 Hủy lệnh (SRS QLGD) |
| **Skill vi phạm** | [codebase-explorer/SKILL.md](file:///home/zane/Desktop/vietbank-sme-omni/.agents/skills/codebase-explorer/SKILL.md) |
| **Mức nghiêm trọng** | TRUNG BÌNH — kết quả brainstorm vẫn đúng hướng nhưng thiếu backing evidence, lãng phí round-trip, vi phạm observability |

---

## 1. Mô tả sự cố

Khi thực hiện brainstorm luồng Hủy lệnh, agent cần explore codebase để hiểu cách approve/reject hiện tại xử lý race condition, lock, complete flow. Agent đã **bỏ qua hoàn toàn Understand-Anything (UA) MCP** trong lượt explore đầu tiên, chỉ dùng `grep` + `view_file` trực tiếp.

Khi user hỏi _"em có sử dụng UA để trace flow không"_, agent mới bắt đầu gọi UA bổ sung — nhưng đúng ra UA phải đi **trước** theo Golden Path.

---

## 2. Timeline chi tiết

| # | Thời điểm | Hành động thực tế | Đúng ra phải làm | Đánh giá |
|---|---|---|---|---|
| 1 | Nhận lệnh brainstorm | Nhận diện explore mode, bắt đầu tìm code | Đọc [codebase-explorer/SKILL.md](file:///home/zane/Desktop/vietbank-sme-omni/.agents/skills/codebase-explorer/SKILL.md), evaluate Cổng độ phức tạp | ❌ Bỏ qua |
| 2 | Tìm code approve/reject | `grep BaseInitTransReqActionHandler` | Golden Path B1: `get_domain_overview` (UA) | ❌ Sai thứ tự |
| 3 | Codebase Memory MCP lỗi | `search_graph` → `project not found` → **bỏ luôn cả hai MCP** | Codebase Memory ≠ UA, phải thử UA riêng | ❌ Đánh đồng |
| 4 | Grep tìm được file | `grep` → `view_file` đọc 6 file handler/factory | Golden Path B2→B3: `search_code` → `get_domain_flow_detail` | ❌ Thiếu B3 |
| 5 | Viết brainstorm artifact | Artifact dựa trên grep + view_file | Cần UA verify cross-service flow, impact analysis | ❌ Thiếu B5 |
| 6 | User hỏi "có dùng UA không" | Bắt đầu gọi UA bổ sung | Phải đã dùng UA từ bước 2 | ❌ Quá muộn |
| 7 | Chạy UA bổ sung | `query_nodes` → `trace_call_chain` → `find_impact` → `get_domain_overview` → `get_domain_detail` → `get_domain_flow_detail` → `get_class_hierarchy` → `get_relationships` | Đúng nhưng muộn, phải update artifact | ⚠️ Bù đắp |

---

## 3. Nguyên nhân gốc rễ

### NC-1: Không đọc SKILL.md trước khi explore code

Agent nhận lệnh "brainstorm" → xử lý theo bản năng, **KHÔNG** mở `codebase-explorer/SKILL.md` để xem quy trình.

[AGENTS.md](file:///home/zane/Desktop/vietbank-sme-omni/AGENTS.md) §3 ghi rõ: _"Chọn skill đúng vai trò, không gộp nhiều vai trò vào một skill."_

System prompt Skills section ghi: _"you MUST read its SKILL.md instructions using view_file before proceeding"_.

Agent bỏ qua cả hai chỉ dẫn.

### NC-2: Đánh đồng Codebase Memory MCP với Understand-Anything MCP

Khi `codebase-memory-mcp` trả lỗi `project not found`, agent kết luận rằng "MCP graph tools không hoạt động" → fallback grep toàn bộ. Thực tế:

```
codebase-memory-mcp (bottom-up, symbol-level)  ← LỖI project name
         ≠
understand-anything (top-down, domain/flow)     ← HOẠT ĐỘNG BÌNH THƯỜNG
                                                   10735 nodes, 17081 edges
```

Hai MCP **hoàn toàn độc lập**. Lỗi một cái không ảnh hưởng cái kia. Agent không thử UA lấy một lần trước khi fallback.

### NC-3: Thiên kiến "grep nhanh hơn"

Agent có pattern xử lý mặc định: `keyword → grep → view_file → kết luận`. Pattern này hiệu quả cho task localized (sửa 1 hàm, tìm 1 symbol), nhưng task Hủy lệnh là **cross-service flow**:

- `approval-service` ↔ `transfer-service` qua gRPC
- `TransactionConfirmConsumer` nhận Kafka event
- `ConfirmTransReqHandler` implement `IGrpcHandler`
- 12 processors trong SelectorChain

→ Thuộc **độ cao UA** theo Altitude Routing. Grep không đủ.

SKILL.md §7 viết:

> _"Với truy vấn flow/cross-service, không bỏ qua UA chỉ vì grep cho cảm giác nhanh hơn; với truy vấn symbol/static-trace, không bỏ qua Codebase Memory. Không thay structured provider bằng grep chỉ vì nhanh."_

Agent rơi đúng vào anti-pattern được cảnh báo.

### NC-4: Không nhận diện Cue Cards

SKILL.md §2 định nghĩa **Cue Cards** — phản xạ khi gặp triệu chứng cụ thể. Task Hủy lệnh trigger ít nhất 3 cue:

| Cue (triệu chứng) | Có trigger? | Agent nhận ra? | Routine đúng |
|---|---|---|---|
| _"Sắp trace vào base/abstract class nhiều impl"_ — `BaseInitTransReqActionHandler` có 4 subclass (AppInitApprove, AppInitReject, WebInitApprove, WebInitReject) | ✅ | ❌ | DỪNG → `get_domain_flow_detail` (UA) |
| _"Call-chain chạm gRPC stub rồi đứt lạnh"_ — `ConfirmTransReqHandler` implement `IGrpcHandler`, flow xuyên qua gRPC bridge | ✅ | ❌ | Leo thang `get_domain_flow_detail` / `get_relationships` (UA) |
| _"Chưa biết entry point (REST? gRPC? Kafka?)"_ — Flow confirm đi qua `TransactionConfirmConsumer` (Kafka) | ✅ | ❌ | `get_domain_overview` → `get_domain_flow_detail` (UA) **trước** mọi grep |

Cả 3 cue đều chỉ về: **DỪNG grep → leo thang UA**. Agent bỏ qua cả 3.

### NC-5: Không chạy Cổng độ phức tạp (Complexity Gate)

SKILL.md §2 quy định chạy **full Golden Path 5 bước** khi task chạm **BẤT KỲ** điều kiện nào:

| Điều kiện | Task Hủy lệnh | Kết luận |
|---|---|---|
| Flow nghiệp vụ end-to-end chưa rõ | ✅ Chưa biết cancel flow connect services ra sao | Trigger |
| Cross-module / cross-service | ✅ approval-service ↔ transfer-service | Trigger |
| Nghi async/event-driven (Kafka/gRPC/queue) | ✅ Kafka confirm consumer, gRPC handler | Trigger |
| Requirement mơ hồ / chưa biết vị trí code | ✅ Cancel chưa tồn tại trong codebase | Trigger |

Task chạm **cả 4/4 điều kiện** → bắt buộc Golden Path 5 bước. Agent không evaluate gate này.

---

## 4. Quy trình đúng vs thực tế

### Golden Path 5 bước (đúng ra)

```
B1. get_domain_overview (UA)
    → "approval-maker-checker" domain
    → 12-processor SelectorChain, 3-layer locking, Active/Completed split
    → Cross-domain: gRPC bridge, Kafka consumer

B2. search_code / search_graph (Codebase Memory)
    → Tìm BaseTransReqActionProcessor, ConfirmTransReqHandler, CompanyTransReqFactory
    → Danh sách class/method ứng viên

B3. get_domain_flow_detail (UA)
    → "Phê duyệt Đơn lẻ" flow: Kafka event → SelectorChain → gRPC bridge
    → Entry point: TransactionConfirmConsumer
    → 3 steps rõ ràng

B4. get_code_snippet / view_file (Codebase)
    → Đọc logic chi tiết: lock mechanism, buildActiveTransReqModel, completeActiveTransReq

B5. trace_path + get_relationships (verify)
    → find_impact(ConfirmTransReqHandler) = 0 dependants → terminal node, safe to extend
    → get_relationships(BaseInitTransReqActionHandler) = 4 subclasses, 21 imports
```

### Thực tế agent làm

```
❌ B1. BỎ QUA
❌ B2. Dùng grep thay (Codebase Memory lỗi → bỏ luôn)
❌ B3. BỎ QUA
✅ B4. view_file đọc code (đúng)
❌ B5. BỎ QUA
```

---

## 5. Đánh giá hệ quả

| Hệ quả | Mức độ | Giải thích |
|---|---|---|
| Brainstorm thiếu domain context | **TRUNG BÌNH** | Không biết có 12 processors, 14 domains cho đến khi UA bổ sung. Kết luận "cần thêm processor" dựa trên suy luận thay vì evidence |
| Không phát hiện ConfirmTransReqHandler là terminal node | **THẤP** | `find_impact()` = 0 dependants → safe to extend. Kết luận vẫn đúng nhưng thiếu UA backing |
| Không ghi AGENT_TRANSPARENCY | **TRUNG BÌNH** | Vi phạm observability, mất traceability cho skill downstream |
| Lãng phí context window | **THẤP** | Grep trước → UA sau → update artifact = thêm ~15 tool calls không cần thiết |
| Kết quả brainstorm cuối cùng | **THẤP** | Sau khi bổ sung UA, kết quả vẫn consistent — không có sai lệch nghiêm trọng |

**Đánh giá tổng: Quy trình SAI, kết quả ĐÚNG nhưng tốn cost.**

---

## 6. Biện pháp khắc phục

| # | Biện pháp | Trigger | Kỳ vọng |
|---|---|---|---|
| 1 | **Luôn đọc SKILL.md** trước khi thực hiện task thuộc scope skill | Bắt đầu bất kỳ explore, review, propose | Không bỏ sót quy trình |
| 2 | **Evaluate Cổng độ phức tạp** (4 câu hỏi: e2e flow? cross-service? async? mơ hồ?) | Trước bước explore đầu tiên | Chọn đúng nhánh: Golden Path vs Codebase-only |
| 3 | **Scan Cue Cards** khi đang grep/trace | Trong quá trình explore, khi gặp abstract class nhiều impl / gRPC stub / unknown entry point | DỪNG grep → leo thang UA kịp thời |
| 4 | **Phân biệt rõ** Codebase Memory MCP ≠ UA MCP | Khi gặp MCP error | Lỗi một cái → thử cái kia, không fallback grep cả hai |
| 5 | **Ghi AGENT_TRANSPARENCY** ngay sau mỗi pha explore | Sau mỗi pha | Đầy đủ traceability |
