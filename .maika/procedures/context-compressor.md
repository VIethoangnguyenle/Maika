# context-compressor.md — Context Compression Strategy

> Sub-module của context-loader. Chạy khi context gần đạt ngưỡng token để tránh loop thinking do overflow.

---

## Mục tiêu

Ngăn agent bị loop thinking khi context quá lớn bằng cách áp dụng đúng strategy compression theo tình huống.
Root cause từ audit: không có strategy khi context overflow → agent re-read file, re-call tools, loop vô tận.

---

## Ba Mode Compression

### Mode A — Summarize (Tóm tắt file lớn)

**Khi dùng**: File đơn lẻ vượt quá **8,000 tokens estimate**.

**Trigger**: context-loader phát hiện file > 8K tokens khi đọc.

**Cách thực hiện**:

```
FUNCTION compress_file_mode_a(file_path):
  1. Đọc toàn bộ file
  2. Sinh summary có cấu trúc:
     - Giữ nguyên: section headers, key values, warnings, BLOCKER markers
     - Tóm gọn: bullet lists dài, ví dụ lặp lại, log rows
     - Loại bỏ: comment trùng lặp, blank lines thừa, metadata không cần thiết
  3. Ghi summary vào in-memory context (KHÔNG ghi đè file gốc)
  4. Ghi note nén vào context package của dispatch hiện tại:
     "[COMPRESS-A] {file_path} tóm tắt từ ~{original_k}K → ~{compressed_k}K tokens"
  5. Trả về: compressed_content (string)

RULE:
  - File gốc KHÔNG bị sửa — chỉ in-memory representation được nén.
  - Nếu file là `INTENT.md`, `SPEC.md` hoặc `exploration/GROUNDING.yaml`: giữ nguyên
    tất cả AC, constraint, DB schema, conflict và assumption.
```

**Ví dụ**:
- `exploration/GROUNDING.yaml` 12K tokens → tóm tắt còn 4K, giữ nguyên schema tables và BLOCKER nodes.
- `knowledge-snapshot.md` → KHÔNG nạp full body; chỉ nạp `knowledge-index.yaml` (entry list), slice kéo JIT tại decision-gate theo `applies_to` (xem `decision-gate.md`).

---

### Mode B — Memory Pointer (Lưu ngoài, truyền tham chiếu)

**Khi dùng**: Tổng context estimate vượt **50,000 tokens**.

**Trigger**: context-loader tính tổng token estimate khi nạp ≥ 50K.

**Cách thực hiện**:

```
FUNCTION compress_context_mode_b():
  1. Xác định file nào chiếm nhiều token nhất (thường: exploration/GROUNDING.yaml, knowledge-snapshot.md)
  2. Với mỗi file lớn (> 5K tokens):
     a. Tạo pointer reference:
        POINTER = {
          "file": "{{ platform.framework_root }}/changes/<id>/exploration/GROUNDING.yaml",
          "summary": "<2-3 câu tóm tắt nội dung>",
          "key_sections": ["Tầng Database", "Module X", "BLOCKER: Y"],
          "read_on_demand": true
        }
     b. Thay thế file full content trong context bằng pointer này
     c. Khi skill downstream cần chi tiết → đọc section cụ thể thay vì toàn bộ file
  3. Ghi note nén vào context package của dispatch hiện tại:
     "[COMPRESS-B] Total context vượt 50K tokens. Đã chuyển sang memory pointer mode.
      Các file lớn: {list file}. Đọc on-demand khi cần."
  4. Gợi ý user: "Context đang lớn. Cân nhắc archive task hiện tại và tiếp tục phiên mới."

PATTERN (AWS Strands): Store large data externally, pass references in context.
```

**Quy tắc đọc on-demand**:
```
FUNCTION read_section_on_demand(file_path, section_name):
  → Đọc chỉ section cần thiết từ file gốc (dùng grep/sed hoặc đọc từ offset)
  → Cache section đó trong context (không đọc lại nếu đã có)
  → Ghi note: "[ON-DEMAND] Đọc section '{section_name}' từ {file_path}"
```

---

### Mode C — Phase Reset (Reset sau resume)

**Khi dùng**: Agent detect đang resume (bootstrap PHASE 2.5) và context có vẻ stale hoặc hỗn loạn.

**Trigger**: bootstrap.md PHASE 2.5 phát hiện:
- Có đúng 1 active change với `STATE.yaml.state` giữa chừng workflow, VÀ
- Phiên bị truncate (không có context in-memory từ phiên trước).

**Cách thực hiện**:

```
FUNCTION compress_context_mode_c():
  1. CLEAR in-memory context (không xoá file)
  2. Chỉ nạp:
     a. `changes/<id>/STATE.yaml` + `CHANGE.yaml` — state và class hiện tại
     b. `INTENT.md` (hoặc `TASK.yaml` với trivial/small) — chỉ section "Mục tiêu"/AC
     c. `exploration/GROUNDING.yaml` — chỉ section headers (không body)
  3. Dựa vào STATE.yaml.state, resolve action kế tiếp qua workflow-router
     (`maika task route --id <id> --action <action>`) và hướng dẫn user.
  4. Ghi note nén vào context package của dispatch hiện tại:
     "[COMPRESS-C] Phase reset sau resume. Loaded minimal context. state={value}."
  5. Cung cấp summary ngắn cho user:
     "Đã resume change {change_id}. State hiện tại: {state}.
      Context đã được tải lại tối giản. [gợi ý bước tiếp theo]"

RULE:
  - Mode C KHÔNG đọc knowledge-snapshot.md trong lượt đầu — chỉ khi skill cụ thể yêu cầu.
  - Mode C KHÔNG chạy lại action đã DONE theo STATE.yaml.
```

---

## Khi Nào Chọn Mode Nào

```
┌─────────────────────────────────────────────────┬──────────┐
│ Tình huống                                       │ Mode     │
├─────────────────────────────────────────────────┼──────────┤
│ File đơn > 8K tokens                            │ A        │
│ Tổng context > 50K tokens (mid-session)         │ B        │
│ Resume sau phiên bị truncate                    │ C        │
│ Resume + tổng context > 50K                     │ C → B    │
│ File > 8K tokens + tổng < 50K                   │ A only   │
└─────────────────────────────────────────────────┴──────────┘
```

---

## Tích hợp với context-loader.md

context-loader gọi context-compressor tại 2 điểm:

1. **Sau khi tính tổng token ước tính** (trong thuật toán định vị context):
   ```
   IF any_file_tokens > 8000:  → compress_file_mode_a(file)
   IF total_tokens > 50000:    → compress_context_mode_b()
   ```

2. **Trong bootstrap PHASE 2.5 (resume detection)**:
   ```
   IF session_truncated AND active_change_state đang giữa workflow:
     → compress_context_mode_c()
   ```

---

## Output / Reporting

Sau mỗi lần compression, ghi note vào context package của dispatch hiện tại:

```
[COMPRESS-{MODE}] {timestamp}
  Trigger: {lý do}
  Files affected: {list}
  Token estimate trước: ~{before}K
  Token estimate sau: ~{after}K
  Action: {summarized | pointer-mode | phase-reset}
```
