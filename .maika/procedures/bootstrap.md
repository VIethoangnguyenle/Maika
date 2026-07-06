# bootstrap.md — Script Tự động Nhận diện & Nạp Context

> Agent thực thi script này ngay khi bắt đầu phiên. Pseudo-code có tính ràng buộc.
> Chi tiết thuật toán định vị file: xem `context-loader.md`.

---

## PHASE 0 — Pre-flight

```
CHECK {{ platform.config_entry_point }}        → không có: ABORT "Repo chưa cấu hình Agent Memory Architecture."
CHECK {{ platform.framework_root }}/rules/RULES.md → không có: WARN, tiếp tục với guardrails mặc định
READ: {{ platform.config_entry_point }}
READ: {{ platform.framework_root }}/rules/RULES.md              ← manifest + index
READ: {{ platform.framework_root }}/rules/rules-flow.md         ← flow constraints
READ: {{ platform.framework_root }}/rules/rules-tool.md         ← tool permissions
READ: {{ platform.framework_root }}/rules/rules-exec.md         ← data/arch/cost/obs
READ: {{ platform.framework_root }}/rules/rules-knowledge.md    ← knowledge lifecycle + path
READ: {{ platform.framework_root }}/rules/rules-guard.md        ← pre-invoke guards (đọc SAU cùng)
```

### PHASE 0.5 — External KI Conflict Check

> External KI (vd: Cursor rules, GitHub Copilot instructions, Antigravity knowledge, v.v.) chỉ được dùng làm pointer.

```
DETECT external KI:
  Kiểm tra sự tồn tại của bất kỳ path nào sau:
  - ~/.cursor/rules/
  - .cursorrules
  - .github/copilot-instructions.md
  - ~/.gemini/antigravity/knowledge/
  - Bất kỳ file nào có tên *-rules.md hoặc *-ki.md ngoài {{ platform.framework_root }}/

IF external KI detected:
  1. WARN bắt buộc trong bootstrap report:
     "⚠️ [R-KI-1] External KI detected: {path}
      SOURCE OF TRUTH = {{ platform.framework_root }}/knowledge/ — KI chỉ được dùng làm pointer.
      Nếu KI mâu thuẫn với {{ platform.framework_root }}/knowledge/: LUÔN ưu tiên {{ platform.framework_root }}/knowledge/."
  2. Ghi vào AGENT_TRANSPARENCY:
     "[R-KI-1] KI conflict pending cleanup: {path}"
  3. Đề xuất action trong bootstrap report:
     "→ Action: Replace nội dung {ki_file} bằng pointer:
        `# Xem {{ platform.framework_root }}/knowledge/long-term/conventions.yaml + author-dna.yaml`"
  4. Nếu phát hiện KI file duplicate conventions/DNA:
     **Từ chối dùng KI file đó trong phiên này** — chỉ dùng {{ platform.framework_root }}/knowledge/.

IF external KI NOT detected:
  → tiếp tục bình thường
```

**Constraint**: Nếu KI external mâu thuẫn với `{{ platform.framework_root }}/knowledge/`, luôn ưu tiên framework knowledge.

**Periodic re-scan**: Ngoài bootstrap, cũng chạy scan này khi:
- `knowledge-curator` chạy `archive_active_context` (kiểm tra xem có KI mới xuất hiện).
- Phát hiện KI file có `last_modified` mới hơn lần scan cuối → WARN ngay.

---

## PHASE 1 — Skill Discovery

```
READ {{ platform.framework_root }}/skills/skill-index.yaml
  EXTRACT: YAML frontmatter (name, description, trigger_conditions) của các skill
  KHÔNG ĐỌC: full instruction body — defer đến khi trigger condition match
  REGISTER vào skill-registry (in-memory): {name, description, triggers}
  ON ERROR (file corrupt): SKIP + WARN
```

> Full skill instructions chỉ được đọc khi trigger condition match.

---

## PHASE 2 — Workflow Discovery

```
READ {{ platform.framework_root }}/workflows/task.md          → /task
READ {{ platform.framework_root }}/workflows/idea-to-task.md  → /idea-to-task
READ {{ platform.framework_root }}/workflows/index-source.md  → /index-source (optional)
READ {{ platform.framework_root }}/workflows/tdd.md           → /tdd
READ {{ platform.framework_root }}/workflows/convention-scan.md     → /convention-scan
READ {{ platform.framework_root }}/workflows/approve-conventions.md → /approve-conventions
READ {{ platform.framework_root }}/workflows/dna-scan.md            → /dna-scan
READ {{ platform.framework_root }}/workflows/approve-dna.md         → /approve-dna
```

---

## PHASE 2.5 — Session Resume Check (bắt buộc)

> Phát hiện khi nào phiên bị truncate và agent đang resume giữa chừng task.
> **Không được bỏ qua phase này** — đây là nguyên nhân gốc của class lỗi "agent dùng thói quen mặc định khi resume".

```
DETECT resume context:
  IF active/REQUIREMENT.md có nội dung thực (không phải skeleton)
  AND active/AGENT_TRANSPARENCY.md có entry pha nào đó đã chạy (Pha 1/2/3)
  THEN → đây là phiên RESUME (không phải task mới)

IF RESUME:
  1. BẮT BUỘC re-read {{ platform.framework_root }}/workflows/task.md để nạp lại toàn bộ CRITICAL blocks
     (đặc biệt: CRITICAL block ở đầu Section 2 — OpenSpec requirement)
  2. Xác định pha hiện tại từ AGENT_TRANSPARENCY (tìm dòng "Pha X DONE" trong section "Lịch sử pha"):
     - Có `Pha 1 DONE`, chưa có `Pha 2 DONE` → đang chờ `/task spec`
       → CRITICAL: phải dùng OpenSpec. **Không re-trigger Pha 1** dù ticket ID có vẻ thiếu.
     - Có `Pha 2 DONE`, chưa có `Pha 3 DONE` → đang chờ `/task apply`
       → CRITICAL: phải xác nhận spec path là `openspec/changes/<id>/`.
     - Không có marker nào → Pha 1 chưa chạy → task mới bình thường
  3. Ghi vào bootstrap report:
     ⚠️ Resume phiên: task {ticket_id} đang ở {pha hiện tại} — đã re-read workflow constraints
  4. KHÔNG suy luận "user đã đồng ý" từ context cũ:
     - Mọi bước confirm bắt buộc trong workflow vẫn phải thực hiện lại
     - Checkpoint summary ≠ full context

IF NOT RESUME (task mới hoặc active trống):
  → tiếp tục bình thường
```

**Rule liên kết**: R-Boot-1, R-Boot-3 (RULES.md) + CRITICAL block trong task.md Section 2.

---

## PHASE 3 — Context Loader

Nạp file theo thứ tự ưu tiên. Logic đầy đủ: `context-loader.md`.

| Priority | Path | Điều kiện nạp | Nếu thiếu |
|----------|------|--------------|-----------|
| P1 | `{{ platform.framework_root }}/knowledge/active/REQUIREMENT.md` | Tồn tại + không phải skeleton | status = "empty" |
| P1 | `{{ platform.framework_root }}/knowledge/active/EXPLORE_CONTEXT.md` | Tồn tại + không phải skeleton | status = "empty" |
| P1 | `{{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md` | Tồn tại | bỏ qua |
| P2 | `{{ platform.framework_root }}/knowledge/active/ideation/ideation-*.md` | Tất cả file .md | danh sách rỗng |
| P3 | `{{ platform.framework_root }}/knowledge/long-term/knowledge-index.yaml` | Luôn nạp nếu tồn tại | **WARN** — chạy `python3 {{ platform.framework_root }}/tools/knowledge-index/generate_index.py {{ platform.framework_root }}/knowledge/long-term`; gate sẽ kéo slice JIT |
| P4 | `{{ platform.framework_root }}/knowledge/archive/` | Chỉ khi P1 trống | đọc metadata của ≤10 ticket gần nhất |

**Skeleton detection**: File là template skeleton nếu chứa `<!-- TODO: fill in -->` hoặc độ dài < 200 ký tự.

---

## PHASE 4 — Conflict Detection

```
IF REQUIREMENT.status == "active":
  PROMPT user:
    "Active context từ task: <ticket-id>
     REQUIREMENT: <tóm tắt 1 dòng> | EXPLORE_CONTEXT: <có/trống>
     [A] Tiếp tục task cũ  [B] Reset + archive tự động  [C] Xem chi tiết"

  IF [B]: knowledge-curator.archive_active_context() → reset_active_context()
  IF [A/C]: giữ nguyên context
```

---

## PHASE 5 — Bootstrap Report + Write Transparency

Xuất ra câu đầu tiên bắt buộc chứa trigger phrase từ `persona.yaml` (field: `greeting`).
Nếu `persona.yaml` không tồn tại → dùng `"Ready"`.

Format (Giới hạn dưới 5 dòng):

```
{greeting} — Đã Bootstrap: [x] Core [x] Skills ({n}) [x] Workflows
📋 Context: REQ={active/empty} | EXPLORE={active/empty}
🧠 Knowledge-index: {loaded — n entries / MISSING ⛔}
🔌 MCP: {server: nodes=N edges=M freshness=… / KG unavailable — grep fallback, MEDIUM / none configured}
📦 Archive: {n} tickets | Token Log: {exists/new}
⚠️ {warnings nếu có}
```

> **Bắt buộc sau khi nạp**:
> - `knowledge-index.yaml` đã nạp → report ghi `🧠 Knowledge-index: loaded — {n entries}`.
>   Body của từng entry KHÔNG nạp ở bootstrap; kéo JIT tại decision-gate (xem `procedures/decision-gate.md`).
> - **MCP probe bắt buộc:** nếu `resolved-config.yaml` khai báo MCP server (vd `understand-anything`) →
>   PHẢI gọi probe thật (`list_projects` — không cần tham số, trả về node/edge counts thật;
>   với UA dùng tool stats của chính server) và ghi dòng `🔌 MCP:` chứa **SỐ THẬT**
>   (nodes/edges/freshness). **Cấm** ghi "Runtime Ready" rỗng. Probe fail/absent → ghi dòng degrade
>   `KG unavailable — grep fallback, MEDIUM`.
>   Nếu `resolved-config.yaml` khai báo `agent-memory` → probe `{{ tools.dynamic_memory_health }}` và CHỈ ghi
>   `🔌 MCP: agent-memory: healthy` khi response xác nhận **kết nối backend daemon thật**.
>   Shim `@agentmemory/mcp` có fallback tool cục bộ khi daemon chết — tool trả lời KHÔNG
>   đồng nghĩa healthy. Probe fail / fallback / absent → ghi dòng degrade
>   `agent-memory unavailable — skip recall/save` + gợi ý chạy `maika doctor mcp --target <repo>`.
>   Không có MCP nào trong config → `🔌 MCP: none configured`.
>   Khi native MCP không khả dụng nhưng config hợp lệ, chạy `maika doctor mcp --target <repo>`
>   để tạo `mcp-doctor-report.md`. Nếu doctor chứng minh bridge fallback healthy, bootstrap
>   có thể ghi dòng `🔌 MCP: bridge fallback — <server> tools/list ok`; mọi reasoning dùng
>   bridge phải ghi vào `AGENT_TRANSPARENCY.md`. Không có native probe hoặc bridge evidence
>   thì vẫn phải degrade, không được ghi "Runtime Ready".
>   Dòng này phải pass (R-Tool-5):
>   `python3 {{ platform.framework_root }}/tools/gate-check/cli.py mcp-status <file>`.
> Nếu KHÔNG ghi các dòng này = R-Guard-1 sẽ block các skill downstream.

Sau đó ghi vào `{{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md` — section Bootstrap:

```
- Timestamp, {{ platform.config_entry_point }} [x], RULES.md [x], Skills loaded [list], Workflows [list]
- Context state: {requirement/explore_context/knowledge-index status}
- Warnings: {list}
```

---

## Error Handling

| Tình huống | Hành động |
|-----------|-----------|
| {{ platform.config_entry_point }} không tồn tại | ABORT |
| Skill file corrupt | SKIP + WARN |
| active/ file không đọc được | WARN, treat as empty |
| archive/ > 50 tickets | Chỉ đọc metadata 10 gần nhất |
| knowledge-index.yaml thiếu | WARN, hạ độ tin cậy kiến trúc |
