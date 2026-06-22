# Thiết kế: Quy trình phối hợp UA ↔ Codebase Memory MCP

**Ngày:** 2026-06-22
**Trạng thái:** Approved (brainstorming) — chờ implementation plan
**Phạm vi sửa đổi:** `.maika/skills/codebase-explorer/SKILL.md` (nhà chính) + cập nhật mỏng `.maika/workflows/task.md` Pha 1

> Nguồn gốc phân tích: ghi chú cá nhân `mcp_synergy_report.md` (không commit). Spec này là **nguồn chính thức** cho phần nâng cấp.

---

## 1. Mục tiêu

Dạy agent dùng **hai MCP bổ trợ nhau — không thay thế nhau** để hiểu source code trước khi làm việc:

- **Understand-Anything (UA):** bản đồ top-down theo domain / business flow / ranh giới async.
- **Codebase Memory:** ống kính bottom-up theo symbol / AST / đọc code / static trace.

Vấn đề hiện tại: `codebase-explorer` + `task.md` Pha 1 coi Codebase Memory là *nguồn chính* (structured-first), UA chỉ *bổ sung*. Báo cáo phân tích đề xuất phối hợp xen kẽ. Spec này hòa giải hai góc nhìn thành một quy trình thống nhất, **adaptive theo độ phức tạp**, **degrade mềm** khi thiếu công cụ.

### Không nằm trong phạm vi

- Tạo lệnh/command mới (vd `/analyze-flow`). Quyết định: nâng cấp luồng hiện có.
- Thay đổi cơ chế GATE check graph freshness hiện có (chỉ tham chiếu, không viết lại).
- Encode domain nghiệp vụ cụ thể vào skill/workflow (giữ generic theo §4 task.md).

---

## 2. Nguyên tắc cốt lõi — Định tuyến theo độ cao (Altitude Routing)

"Structured-first" (Codebase chính) và "UA-first" (báo cáo) **đều đúng ở độ cao khác nhau**. Không lật ngược — tinh chỉnh.

| Độ cao | Chủ sở hữu chính | Lý do |
|---|---|---|
| Domain / business flow / entry point / ranh giới async (Kafka/gRPC) | **UA** (top-down map) | Codebase Memory không có khái niệm domain; trace tĩnh đứt ở async |
| Tìm class/method, đọc code, static call-chain, blast radius theo file | **Codebase Memory** (bottom-up lens) | BM25 nhanh, AST chuẩn, snippet chính xác |

**Tinh chỉnh guidance "structured-first" hiện có:** static call-chain vẫn dùng `trace_path` của Codebase làm chính; **nhưng** khi luồng đứt ở ranh giới async → *leo thang* sang UA domain-flow. Đây là điểm "bổ trợ", không phải thay thế.

---

## 3. Cổng độ phức tạp (Adaptive Trigger)

Agent chạy **full golden path 5 bước** khi task chạm **bất kỳ** điều kiện nào:

- Flow nghiệp vụ end-to-end chưa hiểu rõ
- Tương tác cross-module / cross-service
- Nghi ngờ có async / event-driven (Kafka / gRPC / queue)
- Requirement mơ hồ / chưa biết vị trí code

Ngược lại (task localized, đã biết file/symbol, sửa 1 hàm) → **bỏ qua UA top-down**, dùng Codebase Memory trực tiếp (`search_graph` → `get_code_snippet`).

→ Agent ghi vào `AGENT_TRANSPARENCY.md`: chọn nhánh nào + lý do (1 dòng).

---

## 4. Golden Path 5 bước — chuỗi handoff bổ trợ

Mấu chốt "liên kết chặt": **mỗi bước tiêu thụ output của bước trước**, nên hai tool khóa vào nhau.

| Bước | Tool (golden path) | Input (từ bước trước) | Output (seed cho bước sau) |
|---|---|---|---|
| 1. Định vị bối cảnh | UA `get_domain_overview` | tên feature / requirement | **tên domain** → thu hẹp vùng tìm |
| 2. Tìm diện rộng | Codebase `search_graph` | domain + keyword (B1) | **danh sách class/method + file** ứng viên |
| 3. Chiết xuất luồng | UA `get_domain_flow_detail` | domain (B1) + class names (B2) | **entry point** (REST/gRPC/Kafka) + các step |
| 4. Đọc mã | Codebase `get_code_snippet` | symbol/file ưu tiên (B2+B3) | logic chi tiết (lib, error-handling, threading) |
| 5. Verify liên kết | Codebase `trace_path` + UA `get_relationships` | symbol đã đọc (B4) | bịt lỗ hổng: interface→nhiều impl, điểm đứt async |

**Điểm bổ trợ rõ nhất:**
- **B2 ↔ B3:** Codebase tìm *cái gì tồn tại*, UA giải thích *chúng nối với nhau ra sao qua async*.
- **B5:** hai tool cross-check lẫn nhau (trace tĩnh Codebase + relationship/domain UA).

> **Tên tool cụ thể** resolve theo manifest/templating CLI (`{{ tools.* }}`) lúc implement — xác minh khi viết plan, không chốt cứng trong design.

---

## 5. Bản đồ năng lực theo ý định (chống "thu hẹp tool")

Golden path chỉ nêu ~6 tool, nhưng mỗi MCP có ~12-14 tool. Để agent **không hiểu nhầm đó là whitelist**, skill chứa bảng nhóm tool theo *ý định* (minh họa, **không khóa phiên bản**):

| Ý định | UA | Codebase Memory |
|---|---|---|
| Map domain / business flow | `get_domain_overview`, `get_domain_flow_detail` | — |
| Quan hệ / phân cấp / impact logic | `get_relationships`, `find_impact`, `trace_call_chain` | — |
| Tìm symbol (rộng) | — | `search_graph`, `search_code` |
| Truy vấn cấu trúc tùy ý | — | `query_graph` (Cypher) + `get_graph_schema` |
| Đọc code / kiến trúc | `get_node_source` | `get_code_snippet`, `get_architecture` |
| Trace / dependency / impact file | `trace_call_chain` | `trace_path`, `detect_changes` |
| Quyết định / ADR | — | `manage_adr` |

**Lời nhắc tường minh trong skill:**

> 5 bước golden path là điểm khởi đầu cho ca phổ biến — **không phải whitelist**. Bảng trên là **minh họa, không đầy đủ**; cả hai MCP tự expose danh sách tool đầy đủ lúc runtime. Với nhu cầu ngoài golden path, chọn tool theo **ý định**; khi cần truy vấn lạ, dùng `get_graph_schema` để học schema rồi tự viết `query_graph` (Cypher). Golden path là **sàn**, không phải **trần**.

---

## 6. Ma trận degradation (degrade mềm + ghi confidence)

| Tình huống | Hành xử | Confidence ghi vào AGENT_TRANSPARENCY |
|---|---|---|
| UA thiếu / chưa index | Bỏ B1, B3 (top-down). Chạy Codebase-only (B2, B4, B5 một phần) | "Thiếu domain map — **rủi ro sót liên kết async** (Kafka/gRPC), confidence ↓" |
| Graph Codebase stale/thiếu | Gợi ý `/understand` rebuild. Tạm: UA + grep/read | "Thiếu structured search — dựa text, confidence ↓" (khớp GATE hiện có) |
| Thiếu cả hai | Fallback grep/read thuần | Confidence **THẤP**, khuyến nghị index trước khi đi tiếp |

Nguyên tắc: **luôn chạy được** với thông tin trung thực về độ tin cậy. Không block.

---

## 7. Source attribution (định tính)

Trong `AGENT_TRANSPARENCY.md`, thêm dòng ngắn dạng định tính (**không ép số % cứng**):

> *"Domain & flow async: từ UA. Class/method, code logic, static trace: từ Codebase. Bước nào tool nào chủ lực."*

Đồng thời **mở rộng checklist tool đã gọi** trong `task.md` Pha 1 §6 để liệt kê tường minh các UA domain tool (hiện chỉ ghi "UA skills (nếu có)").

---

## 8. Nơi sửa (giữ lean — theo `.maika/DEVELOPMENT_RULES.md`)

1. **`.maika/skills/codebase-explorer/SKILL.md`** — *nhà chính của protocol*:
   - Tinh chỉnh mục "Structured-first cases" → altitude routing (§2).
   - Thêm: cổng độ phức tạp (§3), golden path 5 bước handoff (§4), bản đồ năng lực + lời nhắc "không whitelist" (§5), ma trận degradation (§6), source attribution (§7).
2. **`.maika/workflows/task.md` Pha 1 §1.4 bước 3** — cập nhật **mỏng**:
   - Mô tả lời gọi `codebase-explorer` trỏ tới protocol (altitude routing + golden path), không nhân đôi chi tiết.
   - §6 checklist transparency: bổ sung UA domain tool tường minh.
   - **Không** viết lại GATE check graph freshness hiện có — chỉ tham chiếu.

`task.md` là orchestrator → chi tiết nằm ở skill, tránh duplicate.

---

## 9. Tiêu chí thành công (verifiable)

- [ ] `codebase-explorer/SKILL.md` mô tả altitude routing thay cho "structured-first" thuần, **không** lật ngược thành "UA luôn trước".
- [ ] Có cổng độ phức tạp rõ ràng: task nhỏ → Codebase trực tiếp (bỏ UA top-down); agent ghi nhánh + lý do.
- [ ] Golden path 5 bước thể hiện handoff (input mỗi bước = output bước trước).
- [ ] Bản đồ năng lực có lời nhắc "minh họa, không whitelist; runtime expose full list" + đề cập `get_graph_schema`/`query_graph`.
- [ ] Ma trận degradation phủ 3 tình huống, luôn ghi confidence, không block.
- [ ] Source attribution định tính được mô tả; checklist tool trong `task.md` §6 liệt kê UA domain tool.
- [ ] `task.md` Pha 1 chỉ thay đổi mỏng (trỏ tới skill), không duplicate chi tiết, không viết lại GATE.
- [ ] Snapshot/test CLI (nếu có) vẫn pass sau khi sửa prose skill/workflow.

---

## 10. Quyết định đã chốt (brainstorming)

| Câu hỏi | Quyết định |
|---|---|
| Hình hài | Nâng cấp luồng hiện có (skill + task.md), không tạo lệnh mới |
| Phạm vi áp dụng | Adaptive theo độ phức tạp |
| Thiếu MCP | Degrade mềm + ghi confidence (không block) |
| Phần phụ | Có cả source attribution + bước verify liên kết |
| Capability map | Map theo ý định, không khóa phiên bản |
| `mcp_synergy_report.md` | Không commit, chỉ tham chiếu (spec này là nguồn chính thức) |
