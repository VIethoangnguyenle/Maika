# rules-tool.md — Tool Rules (MCP & Tool Permissions)

> Sub-file của RULES.md. Đọc qua manifest `RULES.md`.

---

## 3. Tool Rules — Quyền với MCP & tool

### [CRITICAL] R-Tool-1: db-explorer chỉ đọc

- `db-explorer` chỉ được:
  - Đọc metadata (schema, constraint, trigger/procedure, index, view…).
  - Đọc sample data **không PII**, với limit nhỏ.
- Cấm:
  - Sinh hoặc chạy lệnh DDL/DML thay đổi dữ liệu/schema từ skill này.

### [CRITICAL] R-Tool-2: codebase access an toàn

- `codebase-explorer` và Codebase Memory chỉ được:
  - Đọc file, tìm symbol, call graph.
- Mọi thao tác **ghi** vào code phải đi qua:
  - Spec đã được chấp thuận.
  - Pha `/task apply`.

### [CRITICAL] R-Tool-3: OpenSpec apply có kiểm soát

- `/opsx:apply` chỉ được gọi khi:
  - Có spec tương ứng với ticket (sinh từ `/task spec`).
  - User đã được tóm tắt file/module bị chạm và xác nhận rõ ràng.

> R-Tool-4 và R-Tool-5b đã collapse vào R-Tool-5 (xem `docs/superpowers/plans/2026-06-18-decision-point-gates.md`) — numbering giữ nguyên để không gãy reference.

### [CRITICAL] R-Tool-5: Codebase-knowledge qua MCP — evidence gate

- MCP-status (bootstrap + transparency) hợp lệ CHỈ KHI nhúng số thật từ probe
  (`{{ tools.graph_stats }}`: nodes/edges/freshness). "Runtime Ready" rỗng = invalid.
  Pass: `python3 {{ platform.framework_root }}/tools/gate-check/cli.py mcp-status <file>`.
- Khi cần codebase-facts: bằng chứng trong KNOWLEDGE_CHECKPOINT (node_id + blast-radius)
  tự khắc buộc dùng KG tools (`{{ tools.search_code }}`/`{{ tools.read_file }}`/`{{ tools.trace_flow }}`/`{{ tools.find_blast_radius }}`);
  KG không có → dòng degrade "KG unavailable — grep fallback, MEDIUM" + hạ confidence kiến trúc.
- **Thứ tự nguồn khi trace code (UA-first):**
  1. **UA + kinh nghiệm** (`agent-memory` R-Tool-6, `knowledge-snapshot`) — LUÔN trước.
     UA là bản đồ node (class/func/domain/flow/quan hệ/entry-point), **không chứa logic** →
     dùng để trace/định vị/map. Blast-radius độ cao kiến trúc: UA (`{{ tools.find_blast_radius }}`/`{{ tools.domain_relationships }}`) trước.
  2. **Codebase Memory** — hỗ trợ UA, vào SAU: extract **logic trong thân hàm**
     (`{{ tools.read_file }}`) tại node UA đã định vị.
  3. **grep** — fallback cuối; KG/UA vắng → dòng degrade + hạ confidence.
  - Lỗi Codebase Memory MCP ≠ UA không khả dụng → vẫn thử UA độc lập, không fallback grep cả hai.
  - *Identifier trong EXPLORE_CONTEXT* vẫn phân theo fact-type: architecture-facts → UA identifier
    (domain/flow/entry-point); code-facts → `node_id`. (Đây là phân loại *nhãn lưu*, không phải *thứ tự dùng*.)
  - Mâu thuẫn ở code-fact: surface vào `AGENT_TRANSPARENCY`, knowledge chính thắng (R-KL-3), không suppress.
- `{{ tools.read_file }}` tuân thủ R-Data-1 (không log raw PII vào context files).
- Khi ghi `EXPLORE_CONTEXT.md`, luôn kèm identifier cho component quan trọng — `node_id` cho code-facts, hoặc UA identifier (domain/flow/entry-point) cho architecture-facts (`node_id` không bắt buộc với nguồn UA); cho phép downstream `{{ tools.read_file }}(node_id)` hoặc đọc theo identifier UA.
- KHÔNG bịa kết quả cho tool không khả dụng.
- (Infra: thiếu mcp_config.json theo runtime là việc của `maika doctor`, ngoài rule này.)

#### Bridge fallback

`{{ platform.framework_root }}/tools/mcp-bridge/mcp_client.py` chỉ được dùng khi:

- `resolved-config.yaml` có MCP tương ứng;
- native MCP probe fail hoặc runtime không inject tool;
- `maika doctor mcp` đã ghi bridge evidence vào `mcp-doctor-report.md`;
- agent ghi vào `AGENT_TRANSPARENCY.md` lý do dùng bridge thay native MCP.

Bridge không thay native MCP. Bridge không được dùng để gọi tool ghi dữ liệu/schema.

### [CRITICAL] R-Tool-6: Agent Memory MCP — Ranh giới sử dụng

`agent-memory` là **lớp kinh nghiệm dài hạn** — những gì agent đã đúc kết và lưu qua
backend `agentmemory` *sau* các task trước. Dữ liệu mang tính **tham khảo/advisory** ("trước đây TỪNG
làm thế nào"), **không phải kiến thức chính** về hệ thống hiện tại.
Nó bổ sung — không bao giờ thay thế — Bootstrap Protocol, thứ tự ưu tiên context-loader
P1→P4, hay `knowledge-snapshot.md` với tư cách nguồn sự thật chính thức.
Khi mâu thuẫn với kiến thức chính (`knowledge-snapshot.md`, db-explorer, KG),
**kiến thức chính thắng tuyệt đối**.

**Bootstrap PHẢI hoàn tất (§1 {{ platform.config_entry_point }}) trước khi gọi bất kỳ memory tool nào.**

#### Danh sách tool được phép

| Tool | Quyền truy cập | Budget |
|------|----------------|--------|
| `{{ tools.dynamic_memory_search }}` | ✅ Được phép | Tính vào memory budget |
| `{{ tools.dynamic_memory_recall }}` | ✅ Được phép | Tính vào memory budget |
| `{{ tools.dynamic_memory_sessions }}` | ✅ Được phép | **Miễn** — chỉ chẩn đoán |
| `{{ tools.dynamic_memory_audit }}` | ✅ Được phép | **Miễn** — chỉ chẩn đoán |
| `{{ tools.dynamic_memory_health }}` | ✅ Được phép | **Miễn** — kiểm tra hạ tầng |
| `{{ tools.dynamic_memory_save }}` | ⛔ Chỉ qua `knowledge-curator` post-task hook | 1 lần ghi / Pha 3 |
| `{{ tools.dynamic_memory_forget }}` | ⛔ Không bao giờ (chỉ admin thủ công) | — |

`{{ tools.dynamic_memory_sessions }}`, `{{ tools.dynamic_memory_audit }}`, và `{{ tools.dynamic_memory_health }}` là diagnostic tools — không ảnh hưởng reasoning, miễn khỏi memory budget.

#### Ngữ cảnh sử dụng được phép

- **Pha 1 exploration**: agent phát hiện module/table/service trong `REQUIREMENT.md` trùng với archive cũ → đề xuất `{{ tools.dynamic_memory_search }}` trước khi thực thi; ghi tín hiệu trong `AGENT_TRANSPARENCY.md`.
- **Trước spec (Pre-spec) — BẮT BUỘC (hard gate `memory-recall`)**: `{{ tools.dynamic_memory_recall }}`
  để tra cứu quyết định kiến trúc trước đó (query prefix tên project). Ghi dòng evidence vào
  `AGENT_TRANSPARENCY.md`: `agent-memory recall — query:"<query>" · results:<N> — ảnh hưởng reasoning`.
  Gate-check `memory-recall` phải PASS trước khi gọi OpenSpec ở Pha 2 (xem `workflows/task.md`);
  không cấu hình / backend chết → dòng degrade chuẩn (mục Degrade bên dưới) cũng pass gate.
- **Sau task (Pha 3)**: `{{ tools.dynamic_memory_save }}` chỉ qua `knowledge-curator` post-task hook.

> **Phạm vi project khi recall:** `{{ tools.dynamic_memory_search }}` / `{{ tools.dynamic_memory_recall }}`
> (agentmemory) KHÔNG có tham số lọc project → luôn prefix tên project (từ `REQUIREMENT.md`)
> vào đầu `query` để tránh kéo nhầm kinh nghiệm repo khác (cross-project overlap).

#### Xử lý xung đột

Nếu kết quả từ agent-memory mâu thuẫn với `knowledge-snapshot.md`,
snapshot thắng vô điều kiện (R-KL-3).

#### Yêu cầu minh bạch (R-Obs-1)

Khi kết quả memory ảnh hưởng đến reasoning, agent PHẢI ghi vào `AGENT_TRANSPARENCY.md`:
- Tool đã gọi
- Query đã dùng
- Tóm tắt kết quả
- Độ tin cậy: `CAO | TRUNG-BÌNH | THẤP`
- Ghi chú: `agent-memory recall — ảnh hưởng reasoning`

#### Degrade khi agent-memory không cấu hình

Nếu `resolved-config.yaml → mcps` KHÔNG chứa `agent-memory`:
- Mọi `{{ tools.dynamic_memory_search }}` / `{{ tools.dynamic_memory_recall }}` bị **bỏ qua** — KHÔNG gọi, KHÔNG bịa kết quả.
- Ghi vào `AGENT_TRANSPARENCY.md`: `agent-memory unavailable — skip recall/save`.
- M7 post-task push (xem `knowledge-curator`) tự bỏ qua ở Tầng 0 (pre-check).

Đây là degrade-không-bịa, đồng dạng mô hình KG (`KG unavailable — grep fallback, MEDIUM`).

#### Bảo vệ đường ghi (Write-path guard)

Gọi `{{ tools.dynamic_memory_save }}` hoặc `{{ tools.dynamic_memory_forget }}` ngoài `knowledge-curator` post-task hook là **CẤM**.
Agent không được auto-save memory trong exploration, spec, hoặc apply phases.

---

### R-Tool-7: Pre-resolved Tools — Build-time Resolution (CLI)

Tool references đã được resolve tại thời điểm `maika init`. Agent gọi trực tiếp — không cần runtime lookup.

#### [REFERENCE] R-Adapter-1: Tool names là pre-resolved

- Tất cả tool calls trong skills/workflows đã chứa tên tool chính xác cho platform hiện tại.
- Agent **KHÔNG CẦN** đọc registry hay provider config — chỉ cần gọi tool theo tên trong file.
- Platform + MCP mapping được ghi trong `{{ platform.framework_root }}/resolved-config.yaml` (generated by `maika init`).

#### [CRITICAL] R-Adapter-2: Kiểm tra tool availability

- Verify tool availability + xử lý degrade/không-bịa: theo **R-Tool-5** (MCP-probe evidence gate).

#### [REFERENCE] R-Adapter-3: Thêm MCP / Đổi platform

- Chạy lại `maika init` để re-scaffold với tool mapping mới.
- Không sửa tool names thủ công trong skill files.

---

### [CRITICAL] R-Tool-8: Subagent dispatch gate — inject knowledge slice

Orchestrator KHÔNG được `invoke_subagent` cho tới khi `TASK_HANDOFF.<node-id>.md`
chứa section `## Applicable DNA/Conventions` (slice từ knowledge-index theo
artifact-type của node) và pass:

`python3 {{ platform.framework_root }}/tools/gate-check/cli.py handoff-slice <file>`

Trước khi executor/subagent được phép ghi code, cùng handoff đó cũng PHẢI pass
implementation preflight:

`python3 {{ platform.framework_root }}/tools/gate-check/cli.py implementation-context <file>`

Implementation context phải có `## Evidence` với UA evidence (`domain_overview`,
`domain_flow`, `domain_relationships`) hoặc explicit UA degrade/override, và
`## Allowed Files` liệt kê target repo-relative files/globs. `write-gate` sẽ
block code write nếu target file không match `Allowed Files`.

- Slice nhúng INLINE vào prompt subagent. Coding subagent KHÔNG tự đọc knowledge files,
  cũng KHÔNG gọi trực tiếp: UA/KG tools, db-explorer/DB, agent-memory, Codebase Memory search
  như nguồn khám phá chính.
- Output subagent kèm node-checkpoint ghi rule-id đã áp dụng; linter cơ học (giai đoạn
  enforcement sau) gác cửa cuối cho rule `mechanically_checkable`.
- Thiếu slice/context trong khi chạy → subagent ghi `CONTEXT_REQUEST.<node-id>.md`, KHÔNG tự explore.

Executor phải dùng knowledge slice đã verify; không tự suy đoán hoặc mở rộng blast radius.

#### Context request + orchestrator review

Nếu thiếu context trong khi chạy, subagent ghi `CONTEXT_REQUEST.<node-id>.md` và file này
phải pass:

`python3 {{ platform.framework_root }}/tools/gate-check/cli.py context-request <file>`

Orchestrator enrich context, cập nhật `TASK_HANDOFF.<node-id>.md`, rồi mới re-dispatch.
Khi subagent hoàn tất, output phải kèm `NODE_CHECKPOINT.<node-id>.md` và pass:

`python3 {{ platform.framework_root }}/tools/gate-check/cli.py node-checkpoint <file>`

Orchestrator review diff/proposal, evidence, scope, và test result trước khi accept/apply.
Subagent output không phải final chỉ vì subagent đã hoàn thành.

---
