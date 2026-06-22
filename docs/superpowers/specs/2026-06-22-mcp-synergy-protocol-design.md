# Thiết kế: Quy trình phối hợp UA ↔ Codebase Memory MCP

**Ngày:** 2026-06-22
**Trạng thái:** Approved (brainstorming) — binding UA tool = Option A (§9)
**Phạm vi sửa đổi:** `.maika/skills/codebase-explorer/SKILL.md` (nhà chính) + cập nhật mỏng `.maika/workflows/task.md` Pha 1 + platform tool-mapping layer (`base.py` + 4 adapter, do binding Option A §9).

> Nguồn gốc phân tích: ghi chú cá nhân `mcp_synergy_report.md` (không commit). Spec này là **nguồn chính thức**.

---

## 1. Mục tiêu

Dạy agent dùng **hai MCP bổ trợ nhau — không thay thế nhau** để hiểu source code trước khi làm việc:

- **Understand-Anything (UA):** bản đồ top-down theo domain / business flow / ranh giới async.
- **Codebase Memory:** ống kính bottom-up theo symbol / AST / đọc code / static trace.

Vấn đề hiện tại: `codebase-explorer` + `task.md` Pha 1 coi Codebase Memory là *nguồn chính* (structured-first), UA chỉ *bổ sung*. Spec này hòa giải hai góc nhìn thành một quy trình thống nhất, **adaptive theo độ phức tạp**, **degrade mềm** khi thiếu công cụ.

### Không nằm trong phạm vi

- Tạo lệnh/command mới (vd `/analyze-flow`). Quyết định: nâng cấp luồng hiện có.
- Thay đổi cơ chế GATE check graph freshness của Codebase Memory hiện có (chỉ tham chiếu).
- Encode domain nghiệp vụ cụ thể vào skill/workflow (giữ generic theo §4 task.md).

---

## 2. Kiến trúc tích hợp hai MCP (làm rõ — tránh nhầm khái niệm)

Điểm dễ nhầm nhất: "UA" thực chất là **hai thứ tách biệt**, đừng gộp.

### 2.1 UA plugin/skill engine (sinh graph)

- Plugin `understand-anything@Egonex-AI`, gọi qua command:
  - `/understand` → sinh **code graph** `.understand-anything/knowledge-graph.json`.
  - `/understand-domain` → sinh **domain graph** `.understand-anything/domain-graph.json`.
- Đây là **bộ sinh dữ liệu**, không phải nguồn tool truy vấn cho agent.
- Manifest gate sự tồn tại bằng `engine_check` per-platform (plugin đã cài chưa) + `graph_artifacts` (file graph đã sinh chưa).

### 2.2 UA MCP custom (expose graph thành tool)

- MCP custom của user: `VIethoangnguyenle/Understand-Anything-MCP`.
- Manifest key `understand-anything`, `provides: code_exploration`, `server: uv run server.py` (env `PROJECT_ROOTS`).
- **Đây mới là nguồn tool** mà agent gọi để khai thác graph: `get_domain_overview`, `get_domain_flow_detail`, `get_relationships`, `find_impact`, `trace_call_chain`, `get_node_source`…
- Báo cáo synergy (`mcp_understand-anything_*`) nói về **UA MCP này**, không phải plugin engine ở §2.1.

### 2.3 Codebase Memory MCP

- MCP `codebase-memory-mcp`, `provides: code_exploration`.
- Tool: `search_code`, `search_graph`, `get_code_snippet`, `query_graph`, `trace_path`, `detect_changes`, `get_graph_schema`, `index_status`…

### 2.4 Abstract op layer — hiện route 1 chiều về Codebase Memory

- Skill viết theo **abstract operation** `{{ tools.X }}`, resolve per-platform lúc `maika init` (`cli/platforms/*.py`).
- `REQUIRED_TOOL_KEYS` (`base.py`) hiện map **toàn bộ** op code-exploration → `codebase-memory-mcp`:
  - `search_code`, `get_symbol`(→get_code_snippet), `trace_flow`(→trace_path), `get_dependencies`(→query_graph), `find_blast_radius`(→detect_changes), `list_symbols`(→search_graph), `code_status`, `graph_stats`(→get_graph_schema)…
- **Chưa có op nào trỏ UA MCP.** Cả hai MCP cùng khai báo `provides: code_exploration` (mô hình "provider thay thế"), nhưng synergy lại cần dùng **đồng thời, bổ trợ** → đây chính là khoảng trống binding (§9).

### 2.5 Hệ quả cho availability/degradation

- **UA khả dụng** = plugin engine_check pass **và** `domain-graph.json` tồn tại **và** UA MCP server chạy.
- **Codebase khả dụng** = graph index tồn tại + đủ mới (GATE `code_status` hiện có).
- Thiếu một bên → degrade mềm (§7), không block.

---

## 3. Nguyên tắc cốt lõi — Định tuyến theo độ cao (Altitude Routing)

"Structured-first" (Codebase chính) và "UA-first" (báo cáo) **đều đúng ở độ cao khác nhau**. Không lật ngược — tinh chỉnh.

| Độ cao | Chủ sở hữu chính | Lý do |
|---|---|---|
| Domain / business flow / entry point / ranh giới async (Kafka/gRPC) | **UA** (top-down map) | Codebase Memory không có khái niệm domain; trace tĩnh đứt ở async |
| Tìm class/method, đọc code, static call-chain, blast radius theo file | **Codebase Memory** (bottom-up lens) | BM25 nhanh, AST chuẩn, snippet chính xác |

**Tinh chỉnh "structured-first" hiện có:** static call-chain vẫn dùng `{{ tools.trace_flow }}` (Codebase) làm chính; **nhưng** khi luồng đứt ở ranh giới async → *leo thang* sang UA domain-flow. Bổ trợ, không thay thế.

---

## 4. Cổng độ phức tạp (Adaptive Trigger)

Agent chạy **full golden path 5 bước** khi task chạm **bất kỳ** điều kiện nào:

- Flow nghiệp vụ end-to-end chưa hiểu rõ
- Tương tác cross-module / cross-service
- Nghi ngờ có async / event-driven (Kafka / gRPC / queue)
- Requirement mơ hồ / chưa biết vị trí code

Ngược lại (task localized, đã biết file/symbol, sửa 1 hàm) → **bỏ qua UA top-down**, dùng Codebase Memory trực tiếp (`{{ tools.search_code }}` → `{{ tools.get_symbol }}`).

→ Agent ghi vào `AGENT_TRANSPARENCY.md`: chọn nhánh nào + lý do (1 dòng).

---

## 5. Golden Path 5 bước — chuỗi handoff bổ trợ

Mấu chốt "liên kết chặt": **mỗi bước tiêu thụ output của bước trước**.

| Bước | Codebase op / UA tool | Input (từ bước trước) | Output (seed cho bước sau) |
|---|---|---|---|
| 1. Định vị bối cảnh | UA `get_domain_overview` *(binding §9)* | tên feature / requirement | **tên domain** → thu hẹp vùng tìm |
| 2. Tìm diện rộng | `{{ tools.search_code }}` / `{{ tools.list_symbols }}` | domain + keyword (B1) | **danh sách class/method + file** ứng viên |
| 3. Chiết xuất luồng | UA `get_domain_flow_detail` *(binding §9)* | domain (B1) + class names (B2) | **entry point** (REST/gRPC/Kafka) + các step |
| 4. Đọc mã | `{{ tools.get_symbol }}` / `{{ tools.read_file }}` | symbol/file ưu tiên (B2+B3) | logic chi tiết (lib, error-handling, threading) |
| 5. Verify liên kết | `{{ tools.trace_flow }}` + UA `get_relationships` *(binding §9)* | symbol đã đọc (B4) | bịt lỗ hổng: interface→nhiều impl, điểm đứt async |

**Điểm bổ trợ rõ nhất:**
- **B2 ↔ B3:** Codebase tìm *cái gì tồn tại*, UA giải thích *chúng nối nhau ra sao qua async*.
- **B5:** hai tool cross-check (trace tĩnh Codebase + relationship/domain UA).

> Cách viết các bước UA (`get_domain_*`) trong skill phụ thuộc **binding §9** — chưa chốt.

---

## 6. Bản đồ năng lực theo ý định (chống "thu hẹp tool")

Golden path chỉ nêu ~6 tool, mỗi MCP có ~12-14 tool. Để agent **không hiểu nhầm whitelist**, skill chứa bảng nhóm tool theo *ý định* (**minh họa, không khóa phiên bản**):

| Ý định | UA MCP | Codebase Memory |
|---|---|---|
| Map domain / business flow | `get_domain_overview`, `get_domain_flow_detail` | — |
| Quan hệ / phân cấp / impact logic | `get_relationships`, `find_impact`, `trace_call_chain` | — |
| Tìm symbol (rộng) | — | `{{ tools.search_code }}`, `{{ tools.list_symbols }}` |
| Truy vấn cấu trúc tùy ý | — | `{{ tools.get_dependencies }}` (Cypher) + `{{ tools.graph_stats }}` |
| Đọc code / kiến trúc | `get_node_source` | `{{ tools.get_symbol }}`, `{{ tools.read_file }}` |
| Trace / dependency / impact file | `trace_call_chain` | `{{ tools.trace_flow }}`, `{{ tools.find_blast_radius }}` |

**Lời nhắc tường minh trong skill:**

> Golden path là điểm khởi đầu cho ca phổ biến — **không phải whitelist**. Bảng trên **minh họa, không đầy đủ**; cả hai MCP tự expose danh sách tool đầy đủ lúc runtime. Ngoài golden path, chọn tool theo **ý định**; truy vấn lạ thì dùng `{{ tools.graph_stats }}` học schema rồi tự viết Cypher qua `{{ tools.get_dependencies }}`. Golden path là **sàn**, không phải **trần**.

---

## 7. Ma trận degradation (degrade mềm + ghi confidence)

| Tình huống | Hành xử | Confidence ghi vào AGENT_TRANSPARENCY |
|---|---|---|
| UA thiếu (plugin chưa cài / `domain-graph.json` thiếu / UA MCP không chạy) | Bỏ B1, B3 (top-down). Chạy Codebase-only (B2, B4, B5 một phần) | "Thiếu domain map — **rủi ro sót liên kết async** (Kafka/gRPC), confidence ↓" |
| Graph Codebase stale/thiếu | Gợi ý `/understand` rebuild. Tạm: UA + grep/read | "Thiếu structured search — dựa text, confidence ↓" (khớp GATE hiện có) |
| Thiếu cả hai | Fallback grep/read thuần | Confidence **THẤP**, khuyến nghị index trước khi đi tiếp |

Nguyên tắc: **luôn chạy được** với thông tin trung thực về độ tin cậy. Không block.

---

## 8. Source attribution (định tính)

Trong `AGENT_TRANSPARENCY.md`, thêm dòng định tính (**không ép số % cứng**):

> *"Domain & flow async: từ UA. Class/method, code logic, static trace: từ Codebase. Bước nào tool nào chủ lực."*

Mở rộng **checklist tool đã gọi** trong `task.md` Pha 1 §6 để liệt kê tường minh UA domain tool (hiện chỉ ghi "UA skills (nếu có)").

---

## 9. Quyết định binding UA tool — ✅ CHỐT: Option A

UA MCP domain tool chưa có abstract op (§2.4). **Chọn Option A** (abstract op OPTIONAL).

**Lý do quyết định:** SKILL.md được render per-platform lúc `maika init` — chỉ `{{ tools.* }}` được resolve theo platform. Nhúng raw tool name (`mcp__understand-anything__get_domain_overview`) sẽ render **sai** trên codex/antigravity (prefix tool MCP khác claude). Vì vậy Option A đúng **portable**, không chỉ nhất quán.

### Option A (đã chọn) — abstract op OPTIONAL cho UA
- Thêm `domain_overview`, `domain_flow`, `domain_relationships` vào `OPTIONAL_TOOL_KEYS` (`base.py`) — OPTIONAL vì UA luôn có thể vắng.
- Map per-platform (`cli/platforms/*.py`) sang UA MCP tool name thực tế; coi là `unsupported` khi UA vắng.
- Skill dùng `{{ tools.domain_overview }}`, `{{ tools.domain_flow }}`, `{{ tools.domain_relationships }}` → nhất quán abstraction, **degradation cơ học** (op unsupported ⇒ skip top-down, khớp §7).
- **Cần xác minh tên tool thực tế** của UA MCP (`VIethoangnguyenle/Understand-Anything-MCP` — `server.py`/README) trước khi map; tên `get_domain_*` trong spec là từ báo cáo, phải confirm lúc implement.

### Option B (loại) — raw UA MCP tool trong skill
- Render sai trên platform không phải claude; degradation phải mô tả bằng prose. Loại.

---

## 10. Nơi sửa (giữ lean — theo `.maika/DEVELOPMENT_RULES.md`)

1. **`.maika/skills/codebase-explorer/SKILL.md`** — *nhà chính*: altitude routing (§3), cổng độ phức tạp (§4), golden path handoff (§5), bản đồ năng lực + "không whitelist" (§6), degradation (§7), source attribution (§8).
2. **`.maika/workflows/task.md` Pha 1 §1.4 bước 3 + §6** — cập nhật **mỏng**: trỏ tới protocol; bổ sung UA domain tool vào checklist transparency; **không** viết lại GATE.
3. **(Option A — đã chốt §9)** `cli/platforms/base.py` (thêm 3 op vào `OPTIONAL_TOOL_KEYS`) + `cli/platforms/{claude_code,codex,antigravity,generic}.py` — map `domain_overview`/`domain_flow`/`domain_relationships` sang UA MCP tool (hoặc khai báo `unsupported` nơi không có UA). Xác minh tên tool UA MCP trước.

`task.md` là orchestrator → chi tiết ở skill, tránh duplicate.

---

## 11. Tiêu chí thành công (verifiable)

- [ ] `codebase-explorer/SKILL.md` mô tả altitude routing thay cho "structured-first" thuần; **không** lật ngược thành "UA luôn trước".
- [ ] Spec/skill phân biệt rõ UA plugin engine (§2.1) vs UA MCP (§2.2); không gộp khái niệm.
- [ ] Cổng độ phức tạp rõ ràng: task nhỏ → Codebase trực tiếp; agent ghi nhánh + lý do.
- [ ] Golden path 5 bước thể hiện handoff (input mỗi bước = output bước trước).
- [ ] Bản đồ năng lực có lời nhắc "minh họa, không whitelist; runtime expose full list".
- [ ] Ma trận degradation phủ 3 tình huống, gắn với availability ở §2.5, luôn ghi confidence, không block.
- [ ] Source attribution định tính; checklist tool trong `task.md` §6 liệt kê UA domain tool.
- [ ] Binding §9 đã chốt và phản ánh đúng vào §10; nếu Option A: `validate_tool_mapping` của mọi platform vẫn pass, test CLI xanh.
- [ ] Snapshot test (cây thư mục) vẫn pass.

---

## 12. Quyết định đã chốt (brainstorming)

| Câu hỏi | Quyết định |
|---|---|
| Hình hài | Nâng cấp luồng hiện có (skill + task.md), không tạo lệnh mới |
| Phạm vi áp dụng | Adaptive theo độ phức tạp |
| Thiếu MCP | Degrade mềm + ghi confidence (không block) |
| Phần phụ | Có cả source attribution + bước verify liên kết |
| Capability map | Map theo ý định, không khóa phiên bản |
| `mcp_synergy_report.md` | Không commit, chỉ tham chiếu |
| Phân biệt UA plugin vs UA MCP | Làm rõ trong §2 (đã bổ sung) |
| Binding UA tool (§9) | **Option A** — abstract op OPTIONAL (lý do portable render per-platform) |
