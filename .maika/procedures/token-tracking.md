# token-tracking.md — Protocol Ghi Token Usage Theo Pha

> Agent đọc file này để biết cách ghi token consumption vào TOKEN_LOG.md.
> TOKEN_LOG.md nằm trong `{{ platform.framework_root }}/knowledge/active/` — được archive cùng context khi task xong.

---

## Mục tiêu

Tracking token usage **theo pha** (Pha 1 / Pha 2 / Pha 3) để:
- Biết pha nào tốn nhiều nhất → tối ưu prompt hoặc số tool call.
- Có audit trail theo ticket sau khi archive.
- Phát hiện sớm nếu một task "phình" bất thường về token.

---

## Công thức tính token

- **Tỷ lệ:** 1 token ≈ 4 characters (English) / ≈ 3 characters (tiếng Việt — BPE tốn ~2.5× token do ký tự có dấu là multi-byte)
- **Làm tròn:** `ceil(chars / tỷ_lệ / 10) × 10` (làm tròn lên hàng chục)
- Ví dụ (EN): 347 chars → ceil(347/4/10)×10 = ceil(8.675)×10 = 90 tokens; (VI): ceil(347/3/10)×10 = 120 tokens

---

## Phân loại Token (Token Breakdown)

Để đo lường chính xác overhead, token được chia thành 4 loại:
1. **Bootstrap/Init:** Token nạp rules, persona, config hệ thống.
2. **Skill-load:** Token nạp metadata và hướng dẫn của các skill.
3. **Bookkeeping:** Token đọc/ghi các file quản lý trạng thái (REQUIREMENT, AGENT_TRANSPARENCY...).
4. **Actual-work:** Token thực tế dùng xử lý code, logic, và thao tác sinh spec.

---

## Cấu trúc TOKEN_LOG.md

```markdown
# TOKEN_LOG — {ticket-id hoặc task-name}
> Task bắt đầu: {ISO timestamp}
> Model: {model name nếu biết}

---

## Tóm tắt

| Pha | Bootstrap | Skill-load | Bookkeeping | Actual-work | Tổng |
|-----|-----------|------------|-------------|-------------|------|
| Bootstrap | {n} | {n} | {n} | {n} | {n} |
| Pha 1 — Hiểu vấn đề | {n} | {n} | {n} | {n} | {n} |
| Pha 2 — Sinh spec | {n} | {n} | {n} | {n} | {n} |
| Pha 3 — Apply | {n} | {n} | {n} | {n} | {n} |
| **TỔNG TASK** | **{n}** | **{n}** | **{n}** | **{n}** | **{n}** |

---

## Chi tiết theo pha

### Bootstrap
- Bắt đầu: {timestamp}
- Kết thúc: {timestamp}
- Breakdown:
  - Bootstrap/Init: {n}
  - Skill-load: {n}
  - Bookkeeping: {n}
  - Actual-work: {n}
- Tổng: {n}
- Files đọc: {{ platform.config_entry_point }} ({n} tokens), RULES.md ({n} tokens), {n} SKILL.md files

### Pha 1 — Hiểu vấn đề
- Bắt đầu: {timestamp}
- Kết thúc: {timestamp}
- Breakdown:
  - Bootstrap/Init: {n}
  - Skill-load: {n}
  - Bookkeeping: {n}
  - Actual-work: {n}
- Tổng: {n}
- Skills gọi: requirement-analyst, db-explorer, codebase-explorer, architecture-reviewer
- Tool calls tốn nhiều nhất: {tool} ({n} tokens), {tool} ({n} tokens)

### Pha 2 — Sinh spec
- Bắt đầu: {timestamp}
- Kết thúc: {timestamp}
- Breakdown:
  - Bootstrap/Init: {n}
  - Skill-load: {n}
  - Bookkeeping: {n}
  - Actual-work: {n}
- Tổng: {n}

### Pha 3 — Apply
- Bắt đầu: {timestamp}
- Kết thúc: {timestamp}
- Breakdown:
  - Bootstrap/Init: {n}
  - Skill-load: {n}
  - Bookkeeping: {n}
  - Actual-work: {n}
- Tổng: {n}

---

## Cảnh báo

> Ghi các bất thường nếu có:
> - Pha X tốn nhiều hơn baseline 50%+
> - Tool Y gọi nhiều lần do kết quả không đủ
```

---

## Protocol Ghi — Khi nào ghi gì

### Tạo file TOKEN_LOG.md

```
TRIGGER: Bắt đầu Pha 1 (/task <input>)
ACTION:
  IF TOKEN_LOG.md chưa tồn tại:
    → Tạo từ template với header: ticket-id, timestamp, model
    → Ghi dòng Bootstrap estimate (nếu có dữ liệu)
  IF TOKEN_LOG.md đã có (task tiếp tục):
    → Append vào section tương ứng, không overwrite
```

### Ghi checkpoint cuối mỗi pha

```
TRIGGER: Trước khi kết thúc mỗi pha (cùng lúc cập nhật AGENT_TRANSPARENCY)
ACTION:
  UPDATE TOKEN_LOG.md:
    - Điền timestamp kết thúc pha
    - Điền token estimate cho pha đó
    - Cập nhật dòng TỔNG TASK trong bảng Tóm tắt

FORMAT token estimate:
  Agent tự estimate dựa trên:
    - Số file đọc × avg token/file
    - Số tool call × avg token/call
    - Độ dài output của pha
  GHI RÕ: đây là estimate, không phải số chính xác từ API
  Nếu IDE/tool cung cấp số thực → dùng số thực, đánh dấu "(exact)"
```

### Ghi cảnh báo tự động

```
TRIGGER: Cuối Pha 1 khi tổng token Pha 1 > 50,000
ACTION:
  APPEND vào section "Cảnh báo":
  "⚠️ Pha 1 ước tính {n} tokens — cao hơn baseline.
   Nguyên nhân có thể: nhiều {{ tools.read_file }} calls, tài liệu dài, nhiều vòng lặp clarification."
```

---

## Baseline tham khảo (cập nhật dần theo thực tế)

> Điền dần sau khi có dữ liệu thực tế từ các task hoàn thành.

| Pha | Token thấp | Token trung bình | Token cao |
|-----|-----------|-----------------|-----------|
| Bootstrap | ~2,000 | ~5,000 | ~10,000 |
| Pha 1 (HAS_TICKET) | ~10,000 | ~30,000 | ~60,000+ |
| Pha 1 (IDEA_ONLY) | ~3,000 | ~8,000 | ~15,000 |
| Pha 2 (spec) | ~5,000 | ~15,000 | ~30,000 |
| Pha 3 (apply) | ~5,000 | ~20,000 | ~40,000 |

*Baseline sẽ được cập nhật bởi knowledge-curator sau mỗi task hoàn thành.*

---

## Giới hạn & Trung thực

Agent PHẢI ghi rõ trong TOKEN_LOG.md:

```
> ⚠️ LƯU Ý: Các số token trong file này là ước tính (estimate) từ agent,
> không phải số chính xác từ API trừ khi có đánh dấu "(exact)".
> Dùng để so sánh tương đối giữa các pha và task, không dùng cho billing.
```

---

## Archive Protocol

Khi `knowledge-curator.archive_active_context(ticket_id)` chạy:

```
COPY: {{ platform.framework_root }}/knowledge/active/TOKEN_LOG.md
   → {{ platform.framework_root }}/knowledge/archive/{ticket_id}/TOKEN_LOG.md

UPDATE: {{ platform.framework_root }}/knowledge/archive/ARCHIVE_LOG.md
  Thêm cột token_total vào entry của ticket này:
  | {ticket_id} | {date} | {status} | {summary} | {token_total_estimate} |
```

Sau nhiều task, `ARCHIVE_LOG.md` có cột `token_total_estimate` → dễ so sánh task nào tốn nhiều.

---

## Update Baseline

Sau mỗi task hoàn thành, `knowledge-curator` nên:

```
1. Đọc TOKEN_LOG.md của task vừa archive
2. So sánh với baseline trong token-tracking.md
3. Nếu số liệu thực tế lệch xa baseline (>2x hoặc <0.5x):
   → Cập nhật baseline tương ứng
   → Ghi note: "Updated from ticket {ticket_id}"
```
