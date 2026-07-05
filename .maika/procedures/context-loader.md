# context-loader.md — Logic Định vị & Nạp File Theo Priority

> Sub-module của bootstrap. Có thể gọi độc lập khi agent cần re-scan context giữa chừng.

---

## Mục tiêu

Xác định và nạp đúng file context phù hợp với task hiện tại, theo thứ tự ưu tiên đã định nghĩa.
Tránh tình trạng agent dùng context cũ của task khác.

---

## Context Priority Matrix

```
┌─────────────────────────────────────────────────────────────────────────┐
│ PRIORITY  │ PATH                                      │ Điều kiện nạp   │
├───────────┼───────────────────────────────────────────┼─────────────────┤
│ P1 (cao)  │ {{ platform.framework_root }}/knowledge/active/REQUIREMENT.md          │ Có nội dung thực│
│ P1        │ {{ platform.framework_root }}/knowledge/active/EXPLORE_CONTEXT.md      │ Có nội dung thực│
│ P1        │ {{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md   │ Luôn nạp nếu có │
│ P1        │ {{ platform.framework_root }}/knowledge/active/TOKEN_LOG.md             │ Luôn nạp nếu có │
│ P2        │ {{ platform.framework_root }}/knowledge/active/ideation/ideation-*.md  │ Tất cả file .md │
│ P3 (tĩnh) │ {{ platform.framework_root }}/knowledge/long-term/knowledge-index.yaml │ Luôn nạp nếu tồn tại│
│ P4 (thấp) │ {{ platform.framework_root }}/knowledge/archive/{ticket-id}/           │ Chỉ khi P1 trống│
└─────────────────────────────────────────────────────────────────────────┘
```

> `knowledge-snapshot.md`, `conventions.yaml`, `author-dna.yaml`
> KHÔNG được nạp toàn bộ ở context-loader. Context-loader chỉ nạp `knowledge-index.yaml`
> (entry list nhẹ). Body của từng entry được kéo **just-in-time tại decision-gate**
> (xem `procedures/decision-gate.md`) khi gate cần bằng chứng cho artifact-type hiện tại.
> Nếu `knowledge-index.yaml` không tồn tại → WARN "chạy knowledge-index generator; gate sẽ kéo slice JIT" và hạ độ tin cậy kiến trúc.

**knowledge-index.yaml — quy tắc nạp:**
- Luôn nạp nếu tồn tại, cùng lượt P3 (chỉ entry list, không nạp body).
- Không tồn tại → WARN "knowledge-index.yaml chưa có. Agent dùng generic judgment/naming. Chạy index generator để tạo."
- Được dùng bởi: `codebase-explorer`, `architecture-reviewer`, `spec-engineer`, `/task apply` — các skill này tự kéo slice JIT tại decision-gate theo `applies_to` khớp artifact-type, KHÔNG còn pre-load toàn bộ conventions/DNA trước khi chạy.

**Artifact-type slice (JIT, tại decision-gate)**:

Khi R-Guard-2 detect artifact type (trước khi sinh code), decision-gate kéo entry khớp từ `knowledge-index.yaml` thuần theo tag `applies_to`:

```
slice = [ entry for entry in knowledge-index
          if artifact_type in entry.applies_to       # khớp type hiện tại
          or not entry.applies_to ]                  # + entry áp dụng mọi artifact
```

- **Vocabulary artifact-type do PROJECT định nghĩa** (tag `applies_to` mà author-dna-builder / convention-intelligence-builder gắn vào entry) — framework KHÔNG hard-code danh sách type (vd Factory/Service…). Khớp thuần theo `applies_to`, không qua bảng cố định.
- Đây là slice JIT — context-loader không pre-load; decision-gate kéo đúng lúc cần bằng chứng (xem token bằng chứng bắt buộc trong `decision-gate.md`).

> **[R-KI-1 — Bắt buộc]**: External KI (Cursor rules, Antigravity knowledge…) chỉ là pointer —
> framework knowledge là source of truth. **Không được** dùng nội dung KI mâu thuẫn với
> `{{ platform.framework_root }}/knowledge/`. Quy trình detect / WARN / đề xuất cleanup: xem `bootstrap.md` PHASE 0.5.
> Nếu user chưa cleanup sau 2 phiên: nhắc lại mỗi bootstrap cho đến khi xử lý.

---

## Thuật toán định vị theo Task Type

### Khi nhận `/task <input>`:

```
1. Xác định task_type từ input:
   - Chứa ticket key (ABC-123, PROJ-456) hoặc URL ticket → HAS_TICKET
   - Chứa URL wiki/Confluence/PRD nhưng không có ticket → HAS_DOC_ONLY
   - Còn lại → IDEA_ONLY

2. Xác định context cần nạp theo task_type:
   ┌────────────────┬─────────────────────────────────────────────────────┐
   │ Task Type      │ Context cần nạp                                     │
   ├────────────────┼─────────────────────────────────────────────────────┤
   │ IDEA_ONLY      │ knowledge-index (nếu có) + active ideations         │
   │ HAS_DOC_ONLY   │ knowledge-index + active REQUIREMENT (nếu có)       │
   │ HAS_TICKET     │ TẤT CẢ: REQUIREMENT + EXPLORE_CONTEXT + knowledge-index│
   └────────────────┴─────────────────────────────────────────────────────┘

3. Nạp context theo priority, ghi status vào AGENT_TRANSPARENCY
```

### Khi nhận `/task spec <ticket-id>`:

```
REQUIRED:
  → {{ platform.framework_root }}/knowledge/active/REQUIREMENT.md      (PHẢI có, nếu không: ABORT pha 2)
  → {{ platform.framework_root }}/knowledge/active/EXPLORE_CONTEXT.md  (PHẢI có, nếu không: WARN, hạ tin cậy)

OPTIONAL:
  → {{ platform.framework_root }}/knowledge/long-term/knowledge-index.yaml (entry list; body kéo JIT tại decision-gate)
  → {{ platform.framework_root }}/knowledge/archive/{ticket-id}/       (nếu active context khác ticket)
```

### Khi nhận `/task apply <ticket-id>`:

```
REQUIRED:
  → Spec file tương ứng ticket (trong thư mục spec/ hoặc được ghi trong AGENT_TRANSPARENCY)
  → {{ platform.framework_root }}/knowledge/active/REQUIREMENT.md

VERIFICATION:
  → architecture-reviewer không đánh dấu BLOCKER
  → User đã confirm rõ ràng
```

---

## Định vị File Theo Ticket ID

Khi có ticket-id cụ thể, context-loader tìm kiếm theo thứ tự:

```
1. {{ platform.framework_root }}/knowledge/active/REQUIREMENT.md
   → Kiểm tra metadata section có ticket_id khớp không
   → Nếu khớp: nạp và dùng
   → Nếu không khớp: cảnh báo "Active context thuộc ticket khác"

2. {{ platform.framework_root }}/knowledge/archive/{ticket-id}/REQUIREMENT.md
   → Nếu tìm thấy: hỏi user có muốn restore không
   → Nếu restore: copy archive/{ticket-id}/* → active/

3. Không tìm thấy ở đâu:
   → Thông báo: "Chưa có context cho ticket này. Chạy /task <ticket-id> để tạo mới."
```

---

## Re-scan Context (giữa chừng task)

Agent có thể gọi context-loader tại bất kỳ điểm nào trong workflow khi:
- Skill A đã ghi xong file → skill B cần đọc file đó
- User yêu cầu "đọc lại context"
- Agent phát hiện file có thể đã thay đổi

```
FUNCTION rescan_active_context():
  RE-READ: {{ platform.framework_root }}/knowledge/active/REQUIREMENT.md
  RE-READ: {{ platform.framework_root }}/knowledge/active/EXPLORE_CONTEXT.md
  RE-READ: {{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md
  UPDATE: in-memory context state
  REPORT: "Context refreshed. Changes detected: [list nếu có]"
```

---

## Graceful Degradation Rules

| File thiếu | Hành động |
|-----------|-----------|
| REQUIREMENT.md trống | Tiếp tục nhưng WARN, hạ độ tin cậy |
| EXPLORE_CONTEXT.md trống | Tiếp tục, mark "Chưa explore" trong TRANSPARENCY |
| knowledge-index.yaml thiếu | WARN "Kiến trúc tổng thể chưa có knowledge-index. Kết luận kiến trúc có độ tin cậy THẤP hơn." |
| archive/ trống | Bình thường, không cần warn |
| Toàn bộ active/ trống | Bootstrap sạch, không có context cũ |

---

## Output Format

Sau khi chạy context-loader, agent phải có thể trả lời:

```
CONTEXT_SUMMARY = {
  "active_task": "<ticket-id hoặc null>",
  "requirement_status": "loaded | empty | template-only",
  "explore_context_status": "loaded | empty",
  "knowledge_index": "loaded — {n entries} | missing",
  "active_ideations": ["ideation-sdk-bill-payment.md", ...],
  "archive_count": 3,
  "warnings": ["knowledge-index.yaml missing", ...]
}
```

---

## Policy: Các Case Đặc biệt (Concern 2)

Design giả định "1 task tại 1 thời điểm". Ba case sau cần protocol rõ để không phụ thuộc vào hội thoại:

---

### Case A: Task Nóng (Hot-swap)

Xảy ra khi: User đang làm PROJ-123 (pha 1 hoặc 2) nhưng đột nhiên cần xử lý gấp PROJ-456.

```
PROMPT:
  "🔥 Task nóng: PROJ-456 trong khi PROJ-123 đang ở [pha hiện tại].
   [H] Hoàn tất nhanh PROJ-123 đến điểm dừng an toàn rồi stash
   [S] Stash PROJ-123 → xử lý PROJ-456 → resume sau
   [A] Bỏ PROJ-123 luôn, archive và bắt đầu PROJ-456"

IF [S] (Stash):
  1. knowledge-curator.archive_active_context("PROJ-123", status="stashed")
     → ARCHIVE_META.md phải ghi status=stashed (khác với completed)
  2. reset_active_context() → bắt đầu PROJ-456 trên context sạch
  3. Ghi vào AGENT_TRANSPARENCY của PROJ-456:
     "Hot-swap từ PROJ-123 (stashed tại archive/PROJ-123/)"

Resume stash sau: context-loader.restore_from_archive("PROJ-123") + ghi note "Resumed from stash".
```

**Stash status trong ARCHIVE_META.md:** `stashed` (chưa xong, resume được) | `completed` (đã apply) | `cancelled` (bỏ, không resume).

---

### Case B: So sánh với Ticket Cũ

Xảy ra khi: User muốn xem lại context của PROJ-100 (archived) trong khi PROJ-200 đang active.

```
PROMPT:
  "[R] Read-only (khuyến nghị): đọc archive/PROJ-100/ và hiển thị inline, KHÔNG copy vào active/ —
       PROJ-200 không bị ảnh hưởng. Ghi vào AGENT_TRANSPARENCY (PROJ-200):
       "Read-only access archive/PROJ-100/ cho mục đích so sánh"
   [F] Full restore: Stash PROJ-200 trước (Case A), rồi restore_from_archive(PROJ-100)"
```

**Rule cứng**: Không bao giờ đồng thời có 2 task `active` trong `active/`. Read-only từ archive là cách duy nhất để xem ticket cũ mà không phá vỡ task đang chạy.

---

### Case C: Đổi task giữa Pha 2 và Pha 3

Xảy ra khi: Đã chạy `/task spec PROJ-123` xong (Pha 2), nhưng trước khi apply, user muốn quay lại chỉnh REQUIREMENT.

```
PROMPT:
  "⚠️ Spec của PROJ-123 đã được sinh (Pha 2). Sửa REQUIREMENT sẽ invalidate spec hiện tại.
   [P] Patch: đánh dấu spec DRAFT-INVALIDATED, cập nhật REQUIREMENT.md, chạy lại /task spec PROJ-123;
       ghi AGENT_TRANSPARENCY: "Spec invalidated do thay đổi REQUIREMENT tại [timestamp]"
   [K] Giữ spec: ghi "[PENDING CHANGE] mô tả thay đổi" vào REQUIREMENT.md, tiếp tục apply, xử lý delta sau;
       ghi AGENT_TRANSPARENCY: "Spec và REQUIREMENT có delta chưa được sync"
   [A] Abort spec hiện tại, quay về Pha 1 toàn bộ"
```

**Rule cứng**: Khi Pha 2 đã xong mà REQUIREMENT thay đổi, **phải ghi rõ** vào AGENT_TRANSPARENCY rằng spec và requirement có thể lệch. Không được để tình trạng này âm thầm.

---

## [M2] Knowledge-Index Domain Filtering

> Status: SUPERSEDED by `procedures/decision-gate.md` — JIT slice theo `applies_to` (đóng dấu 2026-07-05).
> Fallback khi `knowledge-index.yaml` không tồn tại: xem Graceful Degradation Rules.

---

## [C1] Tích hợp Context Compressor

context-loader tích hợp với `{{ platform.framework_root }}/procedures/context-compressor.md` tại 2 điểm:

### Điểm 1 — Sau khi tính tổng token

Ngay sau khi nạp tất cả file context (cuối thuật toán định vị), tính tổng token estimate:

```
AFTER loading all context files:
  # estimate_tokens: công thức ước tính trong `token-tracking.md` (1 token ≈ 4 chars EN / 3 chars VI)
  file_estimates = {file: estimate_tokens(content) for file, content in loaded}
  total_estimate = sum(file_estimates.values())

  FOR file, tokens IN file_estimates.items():
    IF tokens > 8000:
      → context-compressor.compress_file_mode_a(file)  ← Mode A

  IF total_estimate > 50000:
    → context-compressor.compress_context_mode_b()     ← Mode B

  Ghi tổng vào TOKEN_LOG.md section "Bootstrap":
    "Context loaded: ~{total_estimate}K tokens từ {n} files"
```

### Điểm 2 — Bootstrap PHASE 2.5 (Resume detection)

Trong `bootstrap.md` PHASE 2.5, sau khi xác định phiên bị truncate:

```
IF phase_state != "bootstrapped" AND session_is_new:
  → context-compressor.compress_context_mode_c()      ← Mode C
  → Không chạy full context-loader (chỉ minimal context từ Mode C)
  → Dừng bootstrap tại đây, chờ user ra lệnh tiếp theo
```
