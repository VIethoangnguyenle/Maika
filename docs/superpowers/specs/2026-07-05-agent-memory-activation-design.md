# Agent Memory Activation — Design

**Ngày:** 2026-07-05
**Trạng thái:** Đã duyệt qua brainstorming (4 phần, duyệt từng phần)
**Backend chính thức:** [rohitg00/agentmemory](https://github.com/rohitg00/agentmemory)

## 1. Bối cảnh & Vấn đề

`agent-memory` được thiết kế là **lớp kinh nghiệm dài hạn** của Maika (R-Tool-6):
đọc ở Pha 1 exploration + pre-spec, ghi duy nhất qua hook M7 của `knowledge-curator`
sau task hoàn thành. Thực tế quan sát được: **capability gần như không bao giờ chạy**,
vì tích của chuỗi gate nối tiếp ≈ 0:

1. Backend daemon (`127.0.0.1:3111`) chết mà không có gì báo — degrade âm thầm
   (1 dòng `[M7-SKIP]` trong AGENT_TRANSPARENCY).
2. Opt-in kép: chọn capability lúc `maika init` **và** tự wire MCP đúng tên `agent-memory`.
3. Trigger đọc chỉ là guidance văn bản ("đề xuất") — không có enforce máy móc.
4. Đường ghi bị staged rollout bóp: mọi project khởi đầu ở "tuần 1 = không push gì",
   graduation state machine per-project gần như không bao giờ tiến stage.
5. Shim `@agentmemory/mcp` có **fallback 7 core tools khi daemon chết** — tool vẫn
   "hiện diện" trong tool list mà không có persistence thật → dễ ngộ nhận đang sống.

## 2. Quyết định đã chốt

| Quyết định | Lựa chọn |
| --- | --- |
| Hướng đi | Giữ capability, mở các gate để nó thực sự chạy |
| Provider boundary | **Giữ nguyên**: user tự vận hành daemon; framework chỉ phát hiện + báo to. Không có setup block, không auto-start, không đưa vào `doctor --fix` |
| Đường đọc | **Hard gate** bằng gate-check trước khi viết spec |
| Đường ghi | **Bỏ staged rollout + graduation state machine**, giữ 4 tầng lọc chất lượng |
| Auto-capture hooks của upstream | Tiếp tục **né** `agentmemory connect` (12 hooks xung đột governance M7); chỉ dùng MCP shim |

## 3. Thiết kế

### Workstream A — Health/Detection

**A1. Mở rộng `maika doctor mcp`** (`cli/mcp/doctor.py`):

- Khi `agent-memory` ∈ `selected_mcps` của `resolved-config.yaml`: HTTP GET tới
  `AGENTMEMORY_URL` (đọc env, mặc định `http://localhost:3111`), timeout ~2s,
  dùng stdlib `urllib` — không thêm dependency.
- Tiêu chí "sống": nhận được **bất kỳ HTTP response nào** (kể cả 4xx) = RUNNING —
  không phụ thuộc endpoint `/health` cụ thể của upstream; connection refused /
  timeout = DOWN.
- Kết quả vào `DoctorStatus` + `render_report`:
  - Sống: `agent-memory daemon: RUNNING (http://localhost:3111)`
  - Chết: `agent-memory daemon: DOWN` + hint nguyên văn:
    `npm i -g @agentmemory/agentmemory` rồi chạy `agentmemory`
    (viewer `:3113`; chẩn đoán sâu: `agentmemory doctor`).
- `--fix` **không** khởi động daemon (boundary). Fix vẫn chỉ sửa config như hiện tại.

**A2. Làm cứng bootstrap probe** (`.maika/procedures/bootstrap.md:173-175`):

- Probe `{{ tools.dynamic_memory_health }}` (map `memory_diagnose`) chỉ được ghi
  `agent-memory: healthy` khi response **xác nhận kết nối backend thật**.
- Shim ở chế độ fallback (tool trả lời nhưng daemon chết) → ghi degrade line chuẩn
  `agent-memory unavailable — skip recall/save` + hint chạy `maika doctor mcp`.
- `validate_mcp_status` trong gate-check đã anchor đúng 2 dòng canonical này — không đổi.

**Luồng dữ liệu:** `resolved-config.yaml` → doctor/bootstrap đọc `selected_mcps` →
probe → evidence line vào report (doctor) hoặc `AGENT_TRANSPARENCY.md` (bootstrap) →
gate-check đọc evidence.

### Workstream B — Recall hard gate

**B1. Validator mới** (`.maika/tools/gate-check/gates.py` + subcommand trong `cli.py`):

- `validate_memory_recall(text)`, subcommand `memory-recall`. Kiểm **evidence content**
  trong AGENT_TRANSPARENCY.md, không kiểm "đã gọi tool hay chưa" (đúng spec §2 của gate-check).
- **Pass** khi có một trong hai:
  1. Dòng recall canonical:
     `agent-memory recall — query:"<query>" · results:<N> — ảnh hưởng reasoning`
     — regex bắt buộc `query:"..."` và `results:<số>`, bound độ dài giữa anchor
     (kỹ thuật `{0,40}` như `_DEGRADE`) để loại prose lan man.
  2. Degrade line chuẩn: `agent-memory unavailable — skip recall/save`
     (nguyên văn dòng bootstrap/Tầng 0 đã ghi).
- **Fail** khi không có dòng nào → agent phải recall (hoặc ghi degrade đúng chuẩn) trước.

**B2. Điểm cài** (`.maika/workflows/task.md`, Pha 2 `/task spec`):

- Bước chặn **trước khi gọi OpenSpec propose**:
  `python3 {{ platform.framework_root }}/tools/gate-check/cli.py memory-recall <AGENT_TRANSPARENCY.md>`
  phải exit 0. Cùng pattern gate `teaching-moment` hiện có.

**B3. `rules-tool.md`:**

- Mục "Trước spec (Pre-spec)": guidance → **bước bắt buộc**; query prefix tên project
  (mitigation cho việc `memory_recall`/`memory_smart_search` không có project filter);
  ghi dòng evidence canonical.
- Recall vẫn tính memory budget; "kiến thức chính thắng khi mâu thuẫn" (R-Tool-6) giữ nguyên.

### Workstream C — Đơn giản hóa M7 (đường ghi)

- **Xóa** khỏi `.maika/skills/knowledge-curator/references/m7-memory-push.md`:
  section "Triển khai theo giai đoạn (R-Tool-6)" — bảng tuần 1/2/3,
  hàm `check_m7_graduation()`, mục tương ứng trong Mục lục.
  Đã xác minh staged rollout không được tham chiếu ở file khác — xóa cục bộ, không vỡ liên kết.
- **Giữ nguyên** 4 tầng lọc: Tầng 0 (pre-check config) → Tầng 1 (quality gate:
  verified / tái sử dụng được / không PII) → Tầng 2 (dedup-by-search — bắt buộc vì
  backend append-only, không có idempotency key) → Tầng 3 (quota 1 save/task).
- **Hành vi mới:** save tự động từ task hoàn thành đầu tiên, vẫn chỉ qua cửa duy nhất
  knowledge-curator post-task hook. Minh bạch qua entry `[M7-MEMORY]` như cũ;
  user chặn trực tiếp trong phiên nếu muốn.

### Workstream D — Dọn docs/manifest

- `cli/plugin-manifest.yaml`: display bỏ "(Qdrant)" — phản ánh backend agentmemory.
- `rules-tool.md:69`: sửa "lưu lên Qdrant" tương tự.
- `.maika/profiles/agent-memory-mcp-only-setup.md`: cập nhật theo upstream đã xác minh
  2026-07-05 — daemon `npm i -g @agentmemory/agentmemory` + lệnh `agentmemory`
  (REST `:3111`, viewer `:3113`), shim `npx -y @agentmemory/mcp` + `AGENTMEMORY_URL`,
  cảnh báo shim fallback, né `agentmemory connect`, tên server phải đúng `agent-memory`
  (hyphen — prefix tool per-platform phụ thuộc tên này).

## 4. Error handling

- Probe doctor: timeout/connection refused → `DOWN` + hint; report vẫn sinh, exit code
  doctor không đổi.
- `AGENTMEMORY_URL` không đặt → default `http://localhost:3111`; sai format → báo trong
  report, coi như DOWN.
- Backend chết giữa phiên (bootstrap healthy, recall fail lúc chạy): agent ghi degrade
  line tại thời điểm fail → gate B pass qua degrade, dấu vết rõ.

## 5. Tiêu chí thành công

1. Unit tests pass (`/usr/bin/python3 -m pytest`):
   - `validate_memory_recall`: pass với dòng recall chuẩn / degrade chuẩn; fail khi
     thiếu evidence, prose vượt bound, dòng phủ định.
   - Doctor probe: RUNNING/DOWN đúng với mock HTTP.
2. Project test đã init với agent-memory: daemon tắt → `maika doctor mcp` báo DOWN
   kèm hint; daemon bật → RUNNING.
3. `gate-check memory-recall`: AGENT_TRANSPARENCY thiếu evidence → exit ≠ 0;
   có dòng chuẩn → exit 0.
4. `m7-memory-push.md` không còn "Tuần"/"graduation"; manifest + rules không còn "Qdrant".

## 6. Ngoài phạm vi

- Cài đặt/khởi động/quản lý vòng đời daemon agentmemory (provider boundary).
- Setup block trong manifest / auto-đăng ký MCP server lúc `maika init`.
- Dùng auto-capture hooks hoặc skills (`/recall`, `/remember`) của upstream.
- Sửa giới hạn upstream: recall không có project filter (giữ mitigation query-prefix).
