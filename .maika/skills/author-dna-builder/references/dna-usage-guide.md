# DNA Usage Guide, Re-scan & Re-validation

> Reference file — extracted from SKILL.md for progressive disclosure.

## Mục lục

- Cách Agent Dùng author-dna.yaml
- Re-scan & Update Protocol
- [L5] Periodic Re-Validation Trigger

## Cách Agent Dùng author-dna.yaml

### Pha 2 — Sinh spec

```
TRƯỚC khi propose bất kỳ solution nào:
  READ: author-dna.yaml → hard_principles
  FOR EACH hard_principle:
    IF solution_draft vi phạm principle:
      → KHÔNG đưa ra solution đó
      → Tự refactor sang approach align với DNA
      → Ghi note trong spec: "Approach X được chọn thay Y vì HP-{id}"

  READ: creative_overrides
  IF task input (Confluence/wiki) mô tả if/else flow:
    → FLAG: "Tài liệu mô tả if/else, em propose structure-based alternative"
    → Show cả 2: original if/else approach + DNA-aligned approach
    → Để author quyết định
```

### Pha 3 — Apply/Review

```
Khi review code change (từ /opsx:apply hoặc PR review):
  SCAN change diff cho:
    - Nested if depth > max_nesting_depth: FLAG HP-{id}
    - Switch statement mới: FLAG HP-{id} nếu có pattern alternative
    - instanceof check mới: FLAG — suggest polymorphism
    - Method complexity > threshold: FLAG HP-{id}

  FORMAT flag:
    "⚠️ DNA-ALERT [HP-{id}]: Đoạn này dùng if/else dispatch cho {n} case.
     Theo style của anh, đây là ứng viên tốt cho Strategy/Factory pattern.
     Muốn em propose refactor không?"
```

### Architecture Review

```
Khi architecture-reviewer đánh giá design:
  READ: author-dna.yaml → hard_principles + creative_overrides
  FOR EACH proposed component/layer:
    CHECK: Design này có align với DNA không?
    IF không align:
      → WARN trong EXPLORE_CONTEXT: "Design X có thể không align với HP-{id}"
      → Suggest DNA-aligned alternative
      → Không BLOCK (chỉ WARN) vì architecture decision phức tạp hơn code-level
```

### Khi không có author-dna.yaml

```
IF author-dna.yaml không tồn tại HOẶC status != approved:
  → Agent dùng conventions.yaml (naming only)
  → Không có judgment layer cho code style
  → WARN trong bootstrap report: "author-dna.yaml chưa có. Agent dùng generic
    code style. Chạy /dna-scan để tạo coding DNA."
```

---

## Re-scan & Update Protocol

### Khi cần update DNA

```
Trigger: User cảm thấy agent đang flag sai, hoặc có principle mới

Mode:
  [A] Add principle: Thêm principle mới, không re-scan toàn bộ
      → Agent hỏi: principle gì, có exemplar trong code không?
      → Append vào author-dna.yaml trực tiếp
      → Không cần /approve-dna lại (chỉ cần user confirm trong chat)

  [U] Update existing: Sửa principle đã có (thêm ngoại lệ, làm rõ scope)
      → Edit trực tiếp trong file
      → Chạy /approve-dna để validate lại

  [R] Full rescan: Sau kiến trúc thay đổi lớn
      → Chạy lại toàn bộ /dna-scan
      → Previous DNA được archive, không xoá
```

### Rejected hypothesis log

```
Trong author-dna.yaml, section rejected_hypotheses giúp agent
KHÔNG re-infer lại cùng sai lầm trong tương lai:

rejected_hypotheses:
  - id: HP-{n}-rejected
    original_claim: "<claim bị tác giả bác bỏ>"
    rejection_reason: "<lý do từ tác giả>"
    logged_at: "<timestamp>"
```

---

## [L5] Periodic Re-Validation Trigger

### Mục đích

`author-dna.yaml` có thể bị stale khi codebase thay đổi lớn (refactor, kiến trúc mới).
L5 định nghĩa điều kiện để **tự động gợi ý** re-validation với tác giả.

### Điều kiện trigger re-validation

```
FUNCTION should_revalidate_dna():
  Đọc author-dna.yaml metadata: last_validated_at, last_scan_commit

  TRIGGER nếu BẤT KỲ điều kiện sau đúng:
  1. Thời gian: today - last_validated_at > 90 ngày
  2. Scope thay đổi: có ít nhất 2 task loại refactor hoàn thành kể từ last_validated_at
     (kiểm tra archive/ ARCHIVE_META: status=completed, task_type=refactor)
  3. Manual: user chạy `/dna-scan` trực tiếp

  KHÔNG trigger nếu:
  - author-dna.yaml có status: draft (chưa approved lần đầu)
  - Đang ở giữa Pha 2 hoặc Pha 3 của task
```

### Re-validation Workflow

```
FUNCTION trigger_dna_revalidation():
  1. Ghi vào AGENT_TRANSPARENCY:
     "[L5-DNA-REVALIDATE] author-dna.yaml có thể stale.
      Lý do: {time/refactor/manual}. Last validated: {last_validated_at}."
  2. Thông báo user (non-blocking):
     "author-dna.yaml chưa được validate {n} ngày/sau {n} refactor.
      Muốn chạy lại /dna-scan để cập nhật? (Không bắt buộc)"
  3. Nếu user đồng ý: chạy author-dna-builder với mode "re-validate"
  4. Nếu user từ chối: đánh dấu author-dna.yaml với note:
     re_validation_declined_at: {today}
     → Không hỏi lại trong 30 ngày

RE-VALIDATE mode:
  - Scan codebase để tìm pattern thay đổi (tương tự hybrid mode hiện tại).
  - Không xoá entries đã confirmed: true — chỉ hỏi về entries có thể đã thay đổi.
  - So sánh code patterns mới vs confirmed entries → highlight gaps.
  - Interview lại tác giả chỉ về những gap này (không phỏng vấn lại từ đầu).
```

### Ghi vào knowledge-curator

Khi bootstrap phát hiện trigger condition:
- knowledge-curator PHẢI gợi ý re-validation trong lúc `archive_active_context` (sau task refactor hoàn thành).
- Ghi vào ARCHIVE_META.md: `dna_revalidation_suggested: true`
