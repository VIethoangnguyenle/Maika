# Design: Đưa 4 MCP server thành native tool cho `agy` (Antigravity CLI)

**Ngày:** 2026-06-22
**Trạng thái:** Approved (brainstorm) → chờ implementation plan

## 1. Vấn đề

Khi dùng Antigravity CLI (`agy`), agent chỉ nhận diện **1** MCP server
(`codebase-memory-mcp`) thay vì đủ **5** server đã cấu hình. 4 server còn lại
(`atlassian`, `db-remote`, `understand-anything`, `agent-memory`) "vô hình" với
agent trong các câu hỏi đầu phiên.

Báo cáo trước đó (`mcp_tools.md`) mô tả đúng *triệu chứng* nhưng **sai cơ chế**:
nó cho rằng "CLI không tự map `~/.gemini/antigravity-cli/mcp_config.json` thành
native tools" và đề xuất shell-bridge (`mcp_client.py`) làm lối đi cửa sau.

## 2. Root cause (đã verify)

Bằng chứng thu thập trực tiếp từ config + binary:

- `agy.real` là binary Go (jetski/cortex, 172MB). `strings` cho thấy runtime
  hiểu **đầy đủ schema MCP**: stdio (`command/args/env`), HTTP
  (`serverUrl` + `headers` qua `StreamableHTTPConnector`), và `disabledTools`.
  → 4 entry có thể copy **verbatim**, không cần đổi định dạng.
- `agy` nạp MCP từ **CLI config** mà hiện chỉ chứa `codebase-memory-mcp`. Đó là
  cặp `~/.gemini/settings.json` (key `mcpServers`) và
  `~/.gemini/config/mcp_config.json` — hai file trùng nội dung `{codebase-memory-mcp}`
  và trùng mtime (có process giữ đồng bộ).
- 4 server kia chỉ tồn tại trong `~/.gemini/antigravity-cli/mcp_config.json` và
  `~/.gemini/antigravity/mcp_config.json` — đây là schema/đường dẫn của
  **Antigravity IDE**, không phải của CLI.
- Bằng chứng quyết định: `antigravity/mcp_config.json` chứa **đủ 5** server, nhưng
  agy vẫn chỉ thấy 1 → agy **không đọc** file đó. File duy nhất có tập server khớp
  với cái agy thấy (`{codebase-memory-mcp}`) là `settings.json` /
  `config/mcp_config.json`.

**Kết luận:** Không phải "CLI không map được", cũng không cần shell-bridge. Đây là
lỗi **đặt config sai file** — 4 server được khai báo trong config của IDE thay vì
config mà CLI đọc.

## 3. Success criteria

Chạy `agy -p "liệt kê các MCP server/tool khả dụng"` → agent thấy đủ **5** server
ngay từ đầu phiên, không cần gọi shell-bridge.

## 4. Giải pháp (Approach A — merge tối thiểu)

Đã cân nhắc:
- **A. Merge tối thiểu** (chọn): copy 4 entry vào CLI config agy đọc.
- B. Merge + dọn các `mcp_config.json` thừa — bị loại: IDE vẫn cần file riêng,
  đụng nhiều file, phức tạp hóa.
- C. Script sync IDE→CLI config — bị loại: YAGNI, chỉ đáng nếu sửa config liên tục.

### Thay đổi

1. **`~/.gemini/settings.json`** → key `mcpServers`: thêm 4 entry
   (`atlassian`, `db-remote`, `understand-anything`, `agent-memory`) **copy
   verbatim** từ `~/.gemini/antigravity-cli/mcp_config.json`, gồm cả `env`,
   `serverUrl`/`headers`, `disabledTools`. **Backup `settings.json` trước khi sửa.**
   - Token bí mật: **giữ plaintext** (khớp cách `codebase-memory-mcp` đang làm).

### Verify (giải quyết ẩn số settings.json vs config/mcp_config.json)

2. Launch `agy -p "list available MCP servers/tools"` → đếm số server:
   - Đủ **5** → settings.json đúng là file agy đọc. Done.
   - Vẫn **1** → agy đọc `config/mcp_config.json`; áp 4 entry vào file đó (đúng
     format top-level `{ "mcpServers": { ... } }`) rồi test lại.
3. Smoke-test mỗi server 1 tool (vd: `db-remote` 1 read query, `agent-memory` 1
   recall) để xác nhận kết nối thật, không chỉ đăng ký tên.

### Cleanup

4. `.maika/tools/mcp-bridge/README.md`: thêm ghi chú **DEPRECATED** — "agy đã có 5
   native MCP; chỉ dùng bridge khi agy báo mất tool." **Không xóa code** (giữ làm
   fallback).
5. `mcp_tools.md`: thay phần chẩn đoán sai bằng root-cause đúng ở mục 2 trên.

### Không làm (YAGNI)

- Không gom/xóa các `mcp_config.json` của IDE.
- Không viết script sync.
- Không đổi token sang env var.

## 5. Rủi ro đã biết

**Drift:** sau fix, 5 server tồn tại song song ở `settings.json` (CLI) và các
`mcp_config.json` (IDE). Đổi token về sau phải sửa ≥2 nơi. Chấp nhận trong phạm vi
này; ghi nhận để xử lý nếu trở thành vấn đề thực.
