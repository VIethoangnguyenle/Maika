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
READ: {{ platform.framework_root }}/rules/rules-skill-evolution.md ← verified skill learning
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
  2. Ghi degradation record `[R-KI-1] KI conflict pending cleanup: {path}` vào bootstrap report.
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
```

---

## PHASE 2.5 — Session Resume Check (bắt buộc)

> Phát hiện khi nào phiên bị truncate và agent đang resume giữa chừng task.
> **Không được bỏ qua phase này.** Resume CHỈ dựa `changes/<change-id>/STATE.yaml`
> (authority duy nhất — `config/artifact-authority.yaml`); không dùng phase marker,
> transparency log hay bất kỳ file legacy nào.

```
RESOLVE active changes:
  LIST {{ platform.framework_root }}/changes/*/STATE.yaml

CASE số active change:
  0  → task mới bình thường
  1  → RESUME change đó (state = STATE.yaml.state)
  >1 → KHÔNG tự chọn — yêu cầu user chỉ định --id tường minh

IF RESUME:
  1. BẮT BUỘC re-read {{ platform.framework_root }}/workflows/task.md để nạp lại toàn bộ CRITICAL blocks.
  2. Đọc class từ CHANGE.yaml (effective_class) + state từ STATE.yaml; xác định action
     kế tiếp bằng `maika task route --id <id> --action <action>` khi cần giải thích.
  3. Ghi vào bootstrap report:
     ⚠️ Resume phiên: change {change_id} class {class} đang ở {state}
  4. KHÔNG suy luận "user đã đồng ý" từ context cũ:
     - Mọi bước confirm bắt buộc trong workflow vẫn phải thực hiện lại
     - Checkpoint summary ≠ full context
```

**Rule liên kết**: R-Flow-2 (router) + `agent/KERNEL.md` §8 (Resume & Bootstrap).

---

## PHASE 3 — Context Loader

Nạp file theo thứ tự ưu tiên. Logic đầy đủ: `context-loader.md`.

| Priority | Path | Điều kiện nạp | Nếu thiếu |
|----------|------|--------------|-----------|
| P1 | `{{ platform.framework_root }}/changes/<id>/STATE.yaml` + `CHANGE.yaml` | Khi có active change | status = "empty" |
| P2 | Artifact theo class: `TASK.yaml` (trivial/small) hoặc `INTENT.md` + `exploration/` (standard/architectural) | Khi resume | status = "empty" |
| P3 | `{{ platform.framework_root }}/knowledge/long-term/knowledge-index.yaml` | Luôn nạp nếu tồn tại | **WARN** — chạy `python3 {{ platform.framework_root }}/tools/knowledge-index/generate_index.py {{ platform.framework_root }}/knowledge/long-term`; gate sẽ kéo slice JIT |
| P4 | `{{ platform.framework_root }}/archive/` | Chỉ khi không có active change | đọc metadata của ≤10 change gần nhất |

---

## PHASE 4 — Conflict Detection

```
IF >1 active change:
  PROMPT user:
    "Nhiều change đang active: <danh sách id + state>
     Chỉ định change cần làm việc: maika task <action> --id <change-id>
     (hoặc dọn change treo bằng maika task cancel --id <id>)"
  KHÔNG tự chọn change; KHÔNG reset gì tự động.
```

---

## PHASE 5 — Bootstrap Report + Write Transparency

Xuất ra câu đầu tiên bắt buộc chứa trigger phrase từ `persona.yaml` (field: `greeting`).
Nếu `persona.yaml` không tồn tại → dùng `"Ready"`.

Format (Giới hạn dưới 5 dòng):

```
{greeting} — Đã Bootstrap: [x] Core [x] Skills ({n}) [x] Workflows
📋 Active: {change_id state=... / empty} | Resume: {resume/new/ambiguous}
🧠 Knowledge-index: {loaded — n entries / MISSING ⛔}
🔌 MCP: {server: nodes=N edges=M freshness=… / KG unavailable — grep fallback, MEDIUM / none configured}
📦 Archive: {n} changes
⚠️ {warnings nếu có}
```

Đồng thời ghi machine-readable report tại
`{{ platform.framework_root }}/runtime/BOOTSTRAP_ENV_REPORT.yaml` (environment FACTS —
file tồn tại là `rules_present`, không được gọi là "loaded"):

```yaml
version: 2
completed: true
timestamp:
repository_commit:
entry_point:
rules_present: []
knowledge_index:
  status:
  entries:
configured_providers: []
provider_probes: []
episodic_provider_health:
active_changes: []
resume_state: new | resume | ambiguous
degradation: []
```

Chạy gate `bootstrap-complete`. Thiếu report, `completed != true`, thiếu bất kỳ core
rule, chưa probe provider configured, hoặc degradation không được ghi thì **ABORT**.

**Acknowledgment (bắt buộc, sau khi ĐÃ ĐỌC kernel + rules + skill-index):**
chạy `maika bootstrap --ack` (nhiều active change → thêm `--id <change-id>`) để ghi
`{{ platform.framework_root }}/runtime/AGENT_BOOTSTRAP_ACK.yaml` — pin hash của
kernel/router/skill-index đã đọc. Gate `bootstrap-ack` kiểm cấu trúc; runtime từ chối
task command khi hash lệch (kernel/router/index đổi sau ack → bootstrap lại).
Mọi downstream context package và dispatch log phải cite path env report + ack.

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
>   bridge phải có degradation record trong bootstrap report. Không có native probe hoặc
>   bridge evidence thì vẫn phải degrade, không được ghi "Runtime Ready".
>   Dòng này phải pass (R-Tool-5):
>   `python3 {{ platform.framework_root }}/tools/gate-check/cli.py mcp-status <file>`.
> Nếu KHÔNG ghi các dòng này = R-Guard-1 sẽ block các skill downstream.

Machine-readable report là bản ghi duy nhất của bootstrap — không ghi thêm
transparency log nào khác.

---

## Error Handling

| Tình huống | Hành động |
|-----------|-----------|
| {{ platform.config_entry_point }} không tồn tại | ABORT |
| Skill file corrupt | SKIP + WARN |
| `changes/<id>/STATE.yaml` không đọc được | WARN, treat as no active change |
| archive/ > 50 changes | Chỉ đọc metadata 10 gần nhất |
| knowledge-index.yaml thiếu | WARN, hạ độ tin cậy kiến trúc |
