---
name: knowledge-curator
version: '1.1'
description: >
  Quản lý vòng đời knowledge — archive context hoàn thành, reset active/, cập nhật knowledge-snapshot sau mỗi task.
  Dùng khi task hoàn thành cần archive, hoặc cần reset/rotate context.
  KHÔNG dùng cho: review kiến trúc (→ architecture-reviewer),
  sinh/validate spec (→ openspec-propose, spec-validator), viết tài liệu (→ document-writer).
---

# Knowledge Curator — Quản lý Vòng đời Knowledge

## 1. Mục tiêu

- **Archive** context đã hoàn thành vào `{{ platform.framework_root }}/knowledge/archive/{ticket-id}/` sau khi task xong.
- **Reset** `{{ platform.framework_root }}/knowledge/active/` về template skeleton sạch sẵn sàng cho task mới.
- **Cập nhật** `{{ platform.framework_root }}/knowledge/long-term/knowledge-snapshot.md` với phát hiện mới từ task vừa hoàn thành.
- **Rotate** archive khi quá nhiều (giữ N tickets gần nhất, nén/log các ticket cũ hơn).

Skill này là **lifecycle manager** — không sinh requirement, không review kiến trúc.

---

## 2. Khi nào dùng

Kích hoạt `knowledge-curator` khi:

- `/task apply` hoàn thành thành công → archive task đã xong.
- User yêu cầu "đóng task" hoặc "reset context" trực tiếp.
- Bootstrap phát hiện conflict giữa active context và task mới → user chọn reset.
- Định kỳ: khi `archive/` có hơn 20 tickets → rotate.

---

## Khi nào KHÔNG sử dụng

- Khi cần review kiến trúc, đánh giá rủi ro (→ architecture-reviewer).
- Khi cần sinh hoặc validate spec (→ openspec-propose, spec-validator).
- Khi cần viết tài liệu kỹ thuật (→ document-writer).
- Khi cần chuẩn hoá requirement (→ requirement-analyst).
- Khi task chưa hoàn thành và chưa sẵn sàng archive.

---

## 3. Các hàm chính

### 3.1 `archive_active_context(ticket_id, status="completed")`

```
INPUT:  ticket_id (string) — ID của ticket
        status    (enum)   — một trong: completed | stashed | cancelled

PRE-CHECK (theo R-Guard-1):
  1. Đọc `phase_state` trong AGENT_TRANSPARENCY.md (block `## Phase State`)
  2. Nếu phase_state ∉ {completed, cancelled} và status=completed:
     → WARN: "phase_state chưa là `completed` — xác nhận apply đã xong chưa?"
  3. Archive-ready gate (deterministic): chạy
     `python3 {{ platform.framework_root }}/tools/gate-check/cli.py archive-ready {{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md`
     → Exit ≠ 0 (phase_state = blocked-by-arch | blocked-by-data): ABORT archive, in lý do
       cụ thể từ validator — không thể archive cho đến khi block được resolve.
     → Exit 0: tiếp tục.
     Giới hạn: check deterministic, nhưng việc gọi gate là honor-code (archive không bị
     PreToolUse write-gate chặn).
   4. Kiểm tra `{{ platform.framework_root }}/knowledge/active/TOKEN_LOG.md` tồn tại và có nội dung (không chỉ template):
      → Nếu KHÔNG tồn tại hoặc chỉ là skeleton:
         WARN: "TOKEN_LOG.md chưa được ghi. Tạo retroactively (estimate từ AGENT_TRANSPARENCY) trước khi archive."
         Ghi cảnh báo vào AGENT_TRANSPARENCY: "[TOKEN-LOG-MISSING] TOKEN_LOG không tồn tại lúc archive."
         Tiếp tục archive (không ABORT) — nhưng ARCHIVE_META ghi `token_total_estimate: unknown`.
  5. Teaching Moment gate (R-DNA-7): chạy
     `python3 {{ platform.framework_root }}/tools/gate-check/cli.py teaching-moment {{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md`
     → Exit 0: tiếp tục archive.
     → Exit ≠ 0: ABORT archive, in lỗi cụ thể từ validator, yêu cầu agent resolve section
       `## Teaching Moment Check` (đặt status hợp lệ + bằng chứng) rồi chạy lại.
     Giới hạn: validator chỉ kiểm cấu trúc, không chứng minh được có teaching moment thật;
     việc gọi gate này là honor-code (archive không bị PreToolUse write-gate chặn).
OUTPUT: archive/{ticket_id}/ được tạo với đầy đủ file

Status meanings:
  completed  ← Đã apply xong, task kết thúc. knowledge-curator sẽ chạy update_knowledge_snapshot.
  stashed    ← Tạm dừng (hot-swap hoặc chen task), có thể resume. KHÔNG update snapshot.
  cancelled  ← Bỏ giữa chừng, không tiếp tục. KHÔNG update snapshot.

STEPS:
1. Tạo thư mục: {{ platform.framework_root }}/knowledge/archive/{ticket_id}/
2. Copy:
   - {{ platform.framework_root }}/knowledge/active/REQUIREMENT.md      → archive/{ticket_id}/REQUIREMENT.md
   - {{ platform.framework_root }}/knowledge/active/EXPLORE_CONTEXT.md  → archive/{ticket_id}/EXPLORE_CONTEXT.md
   - {{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md → archive/{ticket_id}/AGENT_TRANSPARENCY.md
   - {{ platform.framework_root }}/knowledge/active/TOKEN_LOG.md        → archive/{ticket_id}/TOKEN_LOG.md (nếu có)
   - {{ platform.framework_root }}/knowledge/active/SESSION_OVERRIDE.md → archive/{ticket_id}/SESSION_OVERRIDE.md (nếu có)
   - {{ platform.framework_root }}/knowledge/active/.session_state.json → archive/{ticket_id}/.session_state.json (nếu có)
   - {{ platform.framework_root }}/knowledge/active/ideation/           → archive/{ticket_id}/ideation/ (nếu có)
3. Tạo archive/{ticket_id}/ARCHIVE_META.md:
   - ticket_id: {ticket_id}
   - archived_at: <timestamp>
   - status: {status}
   - summary: <1-2 câu tóm tắt task đã làm gì>
   - phase_at_archive: <đọc từ `phase_state` trong AGENT_TRANSPARENCY.md>
   - stash_note: <chỉ khi status=stashed: lý do stash và ticket hot-swap là gì>
   - token_total_estimate: <tổng token từ TOKEN_LOG.md nếu có, "unknown" nếu không có>
4. Verify: đọc lại các file đã copy, đảm bảo không corrupt
5. IF status == "completed":
   → tiếp tục chạy update_knowledge_snapshot(discoveries)
   ELSE:
   → bỏ qua update_knowledge_snapshot (context chưa hoàn chỉnh)
6. REPORT: "Archived ticket {ticket_id} [{status}] to {{ platform.framework_root }}/knowledge/archive/{ticket_id}/"
```

### 3.2 `reset_active_context()`

```
INPUT:  none
OUTPUT: {{ platform.framework_root }}/knowledge/active/ được reset về template skeleton

STEPS:
1. Đọc template từ:
   - {{ platform.framework_root }}/knowledge/templates/REQUIREMENT.tpl.md (nếu có) → copy → active/REQUIREMENT.md
   - {{ platform.framework_root }}/knowledge/templates/EXPLORE_CONTEXT.tpl.md → copy → active/EXPLORE_CONTEXT.md
   - {{ platform.framework_root }}/knowledge/templates/AGENT_TRANSPARENCY.tpl.md → copy → active/AGENT_TRANSPARENCY.md
2. Nếu template .tpl.md không tồn tại:
   → Tạo file trống với skeleton tối thiểu (chỉ có header section)
3. Xoá toàn bộ file trong active/ideation/ (trừ .gitkeep nếu có)
4. Reset TOKEN_LOG.md:
   → Xoá (hoặc rename sang TOKEN_LOG.{timestamp}.bak nếu muốn giữ)
   → Tạo file mới từ template TOKEN_LOG.tpl.md (trống, chờ task mới điền)
5. Xoá session-safety sidecars nếu có:
   - {{ platform.framework_root }}/knowledge/active/SESSION_OVERRIDE.md
   - {{ platform.framework_root }}/knowledge/active/.session_state.json
6. REPORT: "Active context reset. Ready for new task."
```

### 3.3 `update_knowledge_snapshot(discoveries)`

```
INPUT:  discoveries — list các phát hiện từ task vừa hoàn thành
        (trích từ EXPLORE_CONTEXT.md và AGENT_TRANSPARENCY.md)
OUTPUT: {{ platform.framework_root }}/knowledge/long-term/knowledge-snapshot.md được cập nhật

STEPS:
1. Đọc EXPLORE_CONTEXT.md + AGENT_TRANSPARENCY.md của task vừa xong
2. Với mỗi discovery: chạy qua Promotion Criteria (xem Bảng Phân loại bên dưới)
3. Nếu được promote → thêm vào đúng section trong snapshot với đủ 4 field metadata:
   source:{ticket-id} seen:{YYYY-MM} verified:{YYYY-MM} status:active
4. Nếu có entry cũ cùng tên/khái niệm trong snapshot:
   - Nếu discovery mới đồng thuận → chỉ cập nhật verified:{date}
   - Nếu discovery mới mâu thuẫn → đánh dấu entry cũ là status:superseded,
     thêm entry mới và ghi rõ “Supersedes entry cũ (ticket {cũ})”
   - Nếu không chắc → đánh dấu cũ là status:outdated, cần verify thủ công
5. Thêm entry vào “Lịch sử cập nhật”: ticket, ngày, số entry thêm/updated

WARN: Nếu knowledge-snapshot.md trống (mới tạo repo):
  → Tạo cấu trúc ban đầu từ template knowledge-snapshot.md
```

#### Bảng Phân loại Promotion Criteria

Mỗi discovery rơi vào đúng một trong các bucket:

| Bucket | Điều kiện | Hành động |
|--------|-----------|----------|
| **PROMOTE → snapshot** | Đủ tất cả: (1) có evidence trực tiếp từ DB/code (không suy luận), (2) khả năng tái sử dụng ở task khác cao, (3) không mang context riêng của một ticket duy nhất, (4) không thuộc phạm vi conventions.yaml hoặc author-dna.yaml (xem bảng phân vùng bên dưới) | Thêm vào đúng section, gắn đủ metadata |
| **REDIRECT → conventions** | Nội dung là **quy tắc** đặt tên, coding style, design pattern boundary, cấu trúc thư mục | Không ghi vào snapshot. Đề xuất cập nhật vào `conventions.yaml` (hoặc `conventions.draft.yaml` nếu chưa approve) |
| **REDIRECT → author-dna** | Nội dung là **triết lý** lập trình, lý do chọn pattern, coding philosophy, judgment principle | Không ghi vào snapshot. Đề xuất cập nhật vào `author-dna.yaml` (hoặc `author-dna.draft.yaml`) |
| **ARCHIVE only** | Một trong: (1) đặc thù cho ticket này (ví dụ: workaround tạm thời), (2) còn đang tranh luận / chưa xác nhận, (3) chỉ liên quan một business case hẹp | Lưu trong archive/{ticket-id}/EXPLORE_CONTEXT.md, không lên snapshot |
| **DISCARD** | Một trong: (1) suy luận thuần túy không có evidence, (2) đã có entry tốt hơn trong snapshot rồi, (3) PII hoặc secret | Không ghi vào đâu cả |

**Bảng phân vùng kiến thức (điều kiện 4):**

| Loại nội dung | Thuộc store nào | Ví dụ |
|--------------|----------------|-------|
| **Sự thật** — hệ thống có gì, cái gì gọi cái gì | `knowledge-snapshot` ✅ | "Bảng X có column Y", "Module A gọi Module B" |
| **Quy tắc** — viết code thế nào, đặt tên ra sao | `conventions.yaml` | "Table prefix phải là APP_", "Factory không chứa business logic" |
| **Triết lý** — tại sao chọn cách này | `author-dna.yaml` | "HP-1: Chain of Responsibility vì need-driven" |
| **Bài học** — team đã gặp gì, giải quyết ra sao | `agent-memory` | "Bug race condition → fix bằng DB-first read" |

**Quy tắc mức trừu tượng khi REDIRECT:**

- `conventions.yaml` và `author-dna.yaml` phải viết **generic** — mô tả quy tắc/triết lý ở mức pattern, không gắn vào tên bảng/class/ticket cụ thể.
- Tên cụ thể (vd: `ORDERS_DAILY_LIMIT`) chỉ xuất hiện trong `evidence` (minh chứng), không phải trong `description` (mô tả quy tắc).
- Nếu quy tắc chỉ đúng cho 1 bảng/1 class cụ thể → đó là **sự thật**, thuộc snapshot, không phải convention.

**Regenerate ruleset sau khi DNA thay đổi (SP1a producer contract):**

- Sau bất kỳ thay đổi DNA nào được approve (REDIRECT → author-dna đã commit), gọi rule-projector
  để regenerate ruleset:
  `python3 {{ platform.framework_root }}/tools/rule-projector/projector.py --dna <dna> --conventions <conv> --out generated/`
- Git pre-commit sync-check là backstop — nếu quên regenerate, hook sẽ chặn commit khi ruleset out-of-sync.

**Ví dụ áp dụng:**

| Phát hiện | Bucket | Lý do |
|-----------|--------|-------|
| Bảng `ORDERS_DAILY_LIMIT` có column `AMOUNT`, `COMPANY_ID` | PROMOTE | DB schema thực tế, tái sử dụng cao |
| `ValidateOrderLimitProcessor` chưa check bảng `ORDERS_DAILY_LIMIT` | PROMOTE | Code gap có evidence, relevant cho nhiều task |
| "Table prefix phải dùng `APP_` cho bảng project-native" | REDIRECT → conventions | Đây là **quy tắc**, không phải sự thật. Thuộc conventions.yaml |
| "Dùng Chain of Responsibility vì need-driven, không ép buộc" | REDIRECT → author-dna | Đây là **triết lý**, không phải sự thật. Thuộc author-dna.yaml |
| "Chiến lược cần thêm cột X" (chưa confirm) | ARCHIVE | Còn đang propose, chưa xác nhận |
| Kafka topic tên `app.order.created` (suy luận từ naming convention) | ARCHIVE | Chưa có evidence trực tiếp |
| Sample data 5 dòng từ bảng user | DISCARD | PII potential, không có giá trị kiến trúc |
| Logic validate giống hệt entry cũ đã có trong snapshot | DISCARD | Dư thừa |

#### Quy trình xử lý Entry Cũ Stale + Confidence Decay

Mỗi lần chạy `update_knowledge_snapshot`, ngoài việc thêm mới, còn kiểm tra:

```
FOR EACH entry trong snapshot có status:active:
  IF verified < (today - 90 days):
    IF task hiện tại "đụng" vào entry này (mention trong EXPLORE_CONTEXT):
      → cập nhật verified:{today}, confidence:high (confirm còn đúng)
    ELSE:
      → Hạ confidence:low (KHÔNG thay đổi status)
         Ghi metadata: <!-- confidence:low reason:stale-90d -->

  IF verified < (today - 180 days) VÀ confidence đã là low:
    → Thêm marker: <!-- needs-reverify -->
    → Agent VẪN sử dụng entry nhưng phải ghi rõ trong output:
       "[STALE] Entry '{name}' chưa verify > 180 ngày — cần xác nhận lại"
```

**Metadata format cho snapshot entries** (backward-compatible với Markdown):

```markdown
### Module: Transaction Framework
<!-- verified: 2026-06 | confidence: high | source: ticket-123 -->

- Mọi transaction đi qua BaseOrderHandler...
```

> Agent đọc HTML comment để biết confidence, nhưng content vẫn là Markdown readable.
> `confidence:low` là signal nhẹ; chỉ evidence mâu thuẫn mới thay đổi `status`.

### 3.4 `restore_from_archive(ticket_id)`

```
INPUT:  ticket_id — ticket muốn restore
OUTPUT: {{ platform.framework_root }}/knowledge/active/ được điền lại từ archive

STEPS:
1. Kiểm tra archive/{ticket_id}/ tồn tại
   → Nếu không: ERROR "Không tìm thấy archive cho ticket {ticket_id}"
2. Kiểm tra active/ có context đang active không:
   → Nếu có: WARN và hỏi user có muốn archive trước không
3. Copy từ archive/{ticket_id}/:
   - REQUIREMENT.md → active/REQUIREMENT.md
   - EXPLORE_CONTEXT.md → active/EXPLORE_CONTEXT.md
   - AGENT_TRANSPARENCY.md → active/AGENT_TRANSPARENCY.md
   - ideation/ → active/ideation/ (nếu có)
4. Thêm note vào AGENT_TRANSPARENCY.md:
   "Restored from archive at <timestamp> — Tiếp tục task {ticket_id}"
5. REPORT: "Context restored for ticket {ticket_id}. Ready to continue."
```

### 3.5 `rotate_archive(keep_n=20)`

```
INPUT:  keep_n — số lượng tickets archive muốn giữ lại (default: 20)
OUTPUT: archive cũ được nén/log, giữ lại N tickets gần nhất

STEPS:
1. LIST tất cả thư mục trong {{ platform.framework_root }}/knowledge/archive/ → sort by date DESC
2. Nếu count > keep_n:
   tickets_to_rotate = list[keep_n:]
   FOR EACH ticket in tickets_to_rotate:
     a. Đọc ARCHIVE_META.md → lấy summary
     b. Append vào {{ platform.framework_root }}/knowledge/archive/ARCHIVE_LOG.md:
        - ticket_id, archived_at, status, summary
     c. XOÁ thư mục archive/{ticket_id}/
3. REPORT: "Rotated {n} old tickets to ARCHIVE_LOG.md. Keeping {keep_n} most recent."
```

---

## Đầu ra

- **Thư mục archive**: `{{ platform.framework_root }}/knowledge/archive/{ticket-id}/` — context task đã hoàn thành.
- **Cập nhật**: `{{ platform.framework_root }}/knowledge/long-term/knowledge-snapshot.md` — phát hiện mới từ task.
- **Reset**: `{{ platform.framework_root }}/knowledge/active/` — về template skeleton sẵn sàng task mới.
- **Log**: `{{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md` — ghi lại hành động archive.

---

## 4. Workflow tích hợp

```
/task apply <ticket> hoàn thành
    ↓
knowledge-curator.archive_active_context(ticket_id)
    ↓
knowledge-curator.update_knowledge_snapshot(discoveries)
    ↓
knowledge-curator.push_to_agent_memory(ticket_id)    ← NEW: Agent Memory hook
    ↓
knowledge-curator.reset_active_context()
    ↓
Agent sẵn sàng nhận task mới
```

---

## 8. [M7] Hook đẩy Agent Memory sau task

Gọi SAU `update_knowledge_snapshot`, TRƯỚC `reset_active_context`. Chỉ khi `status == "completed"`.

Bao gồm 3 tầng lọc chất lượng (Gate → Dedup → Quota), `{{ tools.dynamic_memory_save }}` call, kind selection guide,
triển khai theo giai đoạn (R-Tool-6), và graduation trigger.

> **Chi tiết đầy đủ**: Xem [references/m7-memory-push.md](references/m7-memory-push.md)

---

## 5. Cập nhật AGENT_TRANSPARENCY

Trong `{{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md`:

- Ghi lại mỗi action đã thực hiện:
  - `[x] knowledge-curator: archive_active_context({ticket_id})`
  - `[x] knowledge-curator: update_knowledge_snapshot`
  - `[x] knowledge-curator: reset_active_context`
- Ghi lại nếu có lỗi trong quá trình archive (và đã xử lý thế nào).

---

## 6. [M6] TOKEN_LOG Calibration

So sánh token estimate vs actual usage để cải thiện độ chính xác TOKEN_LOG theo thời gian.
Bao gồm calibration workflow, estimate guidelines, và archive update logic.

> **Chi tiết đầy đủ**: Xem [references/token-calibration.md](references/token-calibration.md)

---

## 7. [M3] Violation Pattern Tracking

Tích lũy pattern vi phạm rule/workflow qua các task để nhận diện vấn đề hệ thống.
Bao gồm `track_violation_patterns()`, tích hợp vào archive flow, và privacy rules.

> **Chi tiết đầy đủ**: Xem [references/violation-tracking.md](references/violation-tracking.md)

---

## 9. Transparency Log Rotation

### Mục tiêu

Ngăn `AGENT_TRANSPARENCY.md` phình to sau nhiều phiên resume liên tiếp (mỗi phiên thêm bootstrap entries).

### Logic rotation

```
FUNCTION rotate_transparency_log():
  Chạy khi: archive_active_context(ticket_id) được gọi

  1. Đọc AGENT_TRANSPARENCY.md trong active/
  2. Đếm số bootstrap entries (tìm pattern "✅ Core:" hoặc "[Bootstrap]")
  3. IF bootstrap_entries > 5:
     → Giữ lại entry đầu tiên (original bootstrap) + 2 entry cuối cùng (recent)
     → Thay các entry giữa bằng:
        "<!-- [ROTATED] {n} bootstrap entries archived — see archive/{ticket-id} -->"
  4. Full log luôn được preserve trong archive/{ticket-id}/AGENT_TRANSPARENCY.md

  IF task chưa hoàn thành (stashed/resumed nhiều lần):
    → Chỉ giữ 3 bootstrap entries gần nhất trong active
    → Compact các entry cũ bằng summary line
```

> Task kéo dài nhiều phiên chỉ giữ bootstrap report gần nhất trong active context; full log nằm trong archive.

---

## 10. Cross-Repo Snapshot Consideration

### Mục tiêu

Cho phép agent reference knowledge-snapshot từ repo phụ thuộc (nếu có) mà không duplicate dữ liệu.

### Cách hoạt động

```
Trong knowledge-snapshot.md, thêm section (nếu cần):

### Cross-Repo References
<!-- Chỉ thêm khi hệ thống có nhiều repo liên kết -->

| Repo | Snapshot path | Verified | Quan hệ |
|------|--------------|----------|---------|
| (ví dụ: shared-lib) | (ví dụ: ../shared-lib/{{ platform.framework_root }}/knowledge/long-term/knowledge-snapshot.md) | (YYYY-MM) | (upstream dependency) |
```

**Quy tắc:**

- KHÔNG copy nội dung snapshot của repo khác vào repo hiện tại.
- Chỉ ghi **pointer** (relative path) + verified date.
- Agent khi cần context từ cross-repo → đọc trực tiếp file snapshot đó.
- Nếu cross-repo snapshot không tồn tại → WARN và ghi vào AGENT_TRANSPARENCY.

> **Khi nào dùng**: Khi project có monorepo hoặc multi-repo setup. Không bắt buộc cho single-repo.

---

## Gotchas

- **[G1] Archive folder name sanitization**: Ticket ID dùng làm tên folder phải được sanitize — loại bỏ `/`, spaces, special chars. Dùng pattern `{TICKET-ID}` trực tiếp (e.g. `SME-123`), không dùng full ticket title.
- **[G2] Bootstrap entries regex**: Regex parse bootstrap report phải match cả format mới và cũ (v2 vs v3). Nếu format thay đổi mà regex không update → context loader sẽ miss active entries.
- **[G3] Cross-repo pointers dùng relative path**: Khi ghi pointer tới cross-repo snapshot, luôn dùng relative path từ project root. Absolute path sẽ break trên máy khác.
- **[G4] Reset active/ không xóa ideation/**: Khi `archive_active_context` reset `active/`, thư mục `active/ideation/` phải được giữ nguyên nếu có ideation đang draft chưa thành ticket.
