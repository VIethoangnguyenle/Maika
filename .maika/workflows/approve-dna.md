---
description: Approve author-dna.draft.yaml → commit thành author-dna.yaml chính thức sau khi user đã review và edit trực tiếp trong IDE.
---

# /approve-dna — Workflow Commit Author DNA

Workflow này chỉ chạy khi user đã:
1. Có `author-dna.draft.yaml` (sinh bởi `/dna-scan`)
2. Đã review và edit trực tiếp trong IDE
3. Sẵn sàng commit thành `author-dna.yaml` chính thức

---

## Bước 1 — Validate file

```
CHECK: {{ platform.framework_root }}/knowledge/long-term/author-dna.draft.yaml tồn tại?
  → Không tồn tại: ABORT
    "author-dna.draft.yaml không tìm thấy. Chạy /dna-scan trước."

PARSE: YAML hợp lệ?
  → Parse error: ABORT, báo dòng lỗi cụ thể.

CHECK: meta.status == "draft"?
  → Nếu "approved": ABORT "File này đã được approve rồi (author-dna.yaml)."
  → Nếu field thiếu: WARN, tiếp tục.

CHECK: Có ít nhất 1 hard_principle được confirmed?
  → Không có: WARN
    "Không có hard_principle nào được confirmed.
     DNA sẽ chỉ có style_preferences — agent sẽ không REJECT code.
     Tiếp tục? [Y/N]"
  → User chọn N: ABORT
  → User chọn Y: tiếp tục

CHECK: Tất cả exemplar node_id còn tồn tại trong code exploration?
  FOR EACH principle có exemplar:
    CALL: {{ tools.get_symbol }}(exemplar.node_id)
    → Nếu node_id không tồn tại: WARN (không block)
      "⚠️ Exemplar {node_id} cho principle {id} không còn tồn tại.
       Code có thể đã refactor. Principle vẫn hợp lệ nhưng exemplar cần cập nhật."
```

---

## Bước 2 — Cross-check với conventions.yaml

```
READ: {{ platform.framework_root }}/knowledge/long-term/conventions.yaml
  → Nếu không tồn tại: SKIP bước này, ghi WARN vào AGENT_TRANSPARENCY.

FOR EACH principle trong author-dna.draft.yaml:
  IF có principle mâu thuẫn với convention:
    VÍ DỤ:
      DNA:         "Không dùng else — dùng early return"
      conventions: "else block used in 15 files, pattern: standard"
    → LIST ra tất cả conflict.
    → HỎI user: "Phát hiện {n} conflict giữa DNA và conventions.
                  Source of truth là file nào?"
      [D] DNA là đúng → cập nhật conventions tương ứng
      [C] Conventions là đúng → cập nhật DNA tương ứng
      [K] Giữ cả 2, đánh dấu cần review sau

  IF không có conflict rõ ràng: tiếp tục.
```

---

## Bước 3 — Promote draft → approved

```
1. Cập nhật metadata trong author-dna.draft.yaml:
   meta.status: approved
   meta.approved_at: {ISO timestamp}

2. Rename:
   author-dna.draft.yaml → author-dna.yaml

3. Backup draft:
   Tạo author-dna.draft.{YYYYMMDD-HHMMSS}.yaml.bak
   → Giữ trong {{ platform.framework_root }}/knowledge/long-term/ làm audit trail
   → Không vào context (context-loader chỉ nạp knowledge-index.yaml từ long-term/, không nạp *.bak)
```

---

## Bước 4 — SP1a Integration: Regenerate Ruleset

```
CHECK: author-dna.yaml có principle nào mechanically_checkable: true?
  → CÓ:
    "🔧 DNA chứa {n} principle có thể enforce cơ học.
     Regenerate ruleset để gate SP1a áp dụng rules mới?
     Chạy: python3 {{ platform.framework_root }}/tools/rule-projector/projector.py
              --dna {{ platform.framework_root }}/knowledge/long-term/author-dna.yaml
              --conventions {{ platform.framework_root }}/knowledge/long-term/conventions.yaml
              --out {{ platform.framework_root }}/tools/rule-projector/generated/"
    → Nếu user đồng ý: chạy command trên.
    → Nếu user skip: ghi WARN — rules cũ vẫn active, DNA mới chưa enforce.

  → KHÔNG CÓ:
    SKIP — tất cả principles là semantic, enforce bởi SP1b subagent.
```

---

## Bước 5 — Cập nhật AGENT_TRANSPARENCY

```
APPEND vào {{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md:

  [x] /approve-dna: author-dna.yaml committed
  - Approved at: {timestamp}
  - Hard principles: {n} ({n} mechanically checkable)
  - Style preferences: {n}
  - Creative overrides: {n}
  - Rejected hypotheses logged: {n}
  - Source: {n} codebase-inferred + {n} author-described
  - Conflicts resolved: {n} (hoặc "none")
  - SP1a ruleset: {regenerated | skipped | no mechanizable principles}
  - author-dna.yaml status: active từ phiên tiếp theo
```

---

## Bước 6 — Thông báo user

```
"✅ author-dna.yaml đã được commit chính thức.

 Tóm tắt:
 • {n} hard principles (bắt buộc — agent sẽ REJECT nếu vi phạm)
 • {n} style preferences (khuyến nghị — agent sẽ FLAG nếu vi phạm)
 • {n} creative overrides (chấp nhận phá convention có lý do)
 • {n} rejected hypotheses (ghi nhận để không re-infer)
 • SP1a: {n} rules đã enforce cơ học qua gate
 • author-dna.draft.{timestamp}.yaml.bak đã lưu

 Hiệu lực: Từ phiên làm việc tiếp theo, agent sẽ dùng
 coding DNA của anh như judgment layer khi:
   - Evaluate design decisions (Pha 2)
   - Generate/review code (Pha 3)
   - Architecture review

 Khi agent đề xuất solution vi phạm hard principle,
 agent sẽ tự flag và propose alternative trước khi anh phải nói.

 Cập nhật DNA sau này: /dna-scan → [A] Add hoặc [U] Update"
```

---

## Error Cases

| Tình huống | Hành động |
|---|---|
| author-dna.draft.yaml không tồn tại | ABORT, hướng dẫn chạy `/dna-scan` |
| YAML parse error | ABORT, báo dòng lỗi |
| Không có hard_principle confirmed | WARN, cho phép tiếp nếu user confirm |
| Conflict với conventions, user chọn [K] | Ghi marker `# REVIEW NEEDED` vào cả 2 file |
| author-dna.yaml đã tồn tại (approve lần 2) | Hỏi: overwrite hay merge? |
| Rule-projector không tồn tại (chưa cài SP1a) | SKIP bước 4, ghi WARN |
