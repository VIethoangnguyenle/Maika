# rules-guard.md — Guard Rules (Pre-invoke, DNA, KI)

> Sub-file của RULES.md. Đọc qua manifest `RULES.md`.

---

## 14. Guard Rules — Pre-invoke Guardrails

### [CRITICAL] R-Guard-1: Kiểm tra pre_conditions trước khi gọi skill

- Mỗi skill có thể khai báo block `pre_conditions:` trong frontmatter.
- Trước khi thực thi bất kỳ skill nào có `pre_conditions:`, agent **PHẢI**:
  1. Đọc từng condition trong list.
  2. Kiểm tra điều kiện (`not_empty`, `not_skeleton`, `exists`, `phase_done`).
  3. Nếu **tất cả** pass → thực thi skill bình thường.
  4. Nếu **bất kỳ** condition fail → thực hiện `on_fail` action và **ABORT** skill đó.
- `on_fail` action thường là:
  - `ABORT — <hướng dẫn>`: dừng hoàn toàn, thông báo user.
  - `WARN — <hướng dẫn>`: tiếp tục nhưng ghi cảnh báo vào artifact result/review
    của phase hiện tại.
- Không được bypass `pre_conditions` dù context có vẻ đủ — guard phải chạy deterministically.
- Precondition guards phải chạy trước skill để lỗi không lan sang downstream skills.

### [CRITICAL] R-Guard-2: vNext write gate

Trước khi tạo/sửa bất kỳ application-code artifact nào, agent PHẢI có đúng một
workspace vNext ở trạng thái `EXECUTING`:

- `{{ platform.framework_root }}/changes/<id>/STATE.yaml`
- `{{ platform.framework_root }}/changes/<id>/generated/PLAN_VALIDATION.json`
- `{{ platform.framework_root }}/changes/<id>/generated/PLAN_MANIFEST.json`
- `{{ platform.framework_root }}/changes/<id>/generated/TASK_QUEUE.json`

Write-gate chỉ cho phép file nằm trong `files.create`, `files.modify`,
`files.delete`, hoặc `files.test` của task `in_progress` hiện tại. Gate FAIL →
**ABORT**, không được viết code. Chi tiết: `procedures/decision-gate.md`.

### [CRITICAL] R-DNA-7: Capture teaching moment ngay trong phiên

**Teaching moment** = user (tác giả) sửa code của agent VÀ giải thích nguyên tắc kỹ thuật:
- "không dùng setter, dùng toBuilder()"
- "Factory không được chứa business logic"
- "đây sai rồi, phải là..."
- Hoặc bất kỳ: correction nào kèm nguyên tắc design/coding.

**Bước 0 — Phân tách abstraction level TRƯỚC khi ghi** (bắt buộc):

```
1. Bỏ hết tên cụ thể (table, class, method, column) — bài học còn đúng không?
   CÓ  → author-dna.yaml   (WHY/HOW — thinking lens)
   KHÔNG → tiếp câu 2

2. Bài học về naming / structure / organization pattern?
   CÓ  → conventions.yaml  (WHAT — structural rules)
   KHÔNG → tiếp câu 3

3. Bài học về kiến trúc / component / relationship cụ thể?
   CÓ  → knowledge-snapshot.md  (WHAT IS — architecture map)
   KHÔNG → không cần ghi
```

Một teaching moment có thể sinh entries ở **nhiều file** — không gộp vào 1 chỗ.
Dấu hiệu ghi SAI level: entry author-dna phải liệt kê tên bảng/cột/dòng code.

**Sau khi phân tách**:
1. **Ngay lập tức** đề xuất capture cho user xác nhận:
   - "Anh vừa dạy về `{topic}`. Em phân tách:
     - author-dna: `{thinking level — bỏ tên cụ thể}`
     - knowledge-snapshot: `{factual level}` (nếu có)
     Confirm?"
2. **Sau confirm**: ghi vào đúng file theo phân tách, `confirmed: true`, `source: author-described ({date})`.
   - Nếu principle vừa ghi là **mechanically checkable** (map được sang `ir_rule` — xem
     `author-dna-builder/references/check-spec-mapping.md`): emit luôn `mechanically_checkable: true`
     + `check_spec`, rồi chạy rule-projector regenerate ruleset ngay trong phiên (SP1a §3.2 — active path):
     `python3 {{ platform.framework_root }}/tools/rule-projector/projector.py --dna <dna> --conventions <conv> --out generated/`
     → `python3 {{ platform.framework_root }}/tools/rule-projector/backends/checkstyle.py --ir generated/rules.json --out generated/checkstyle.generated.xml`
3. **Không được defer** sang phiên sau — teaching moment phải capture ngay trong phiên.
4. **Nếu user từ chối**: ghi observation WARN vào `reviews/SKILL_FEEDBACK.yaml` của
   workspace hiện tại: "[R-DNA-7] Teaching moment chưa capture: `{principle}`."

Điều kiện nhận biết: user dùng "không được", "phải dùng", "sai rồi", "thay bằng",
hoặc sửa code agent trực tiếp kèm giải thích.

Teaching moment phải được ghi vào persistent project knowledge, không chỉ vào KI external hoặc context tạm thời.

### [CRITICAL] R-KI-1: KI external phải là pointer, không phải source

Khi bootstrap phát hiện external KI (vd: Cursor rules, `.cursorrules`, Antigravity knowledge, v.v.):

1. **Bắt buộc** WARN trong bootstrap report.
2. **Bắt buộc** đề xuất action cleanup cụ thể:
   "Replace nội dung `{ki_file}` bằng: `# Xem {{ platform.framework_root }}/knowledge/long-term/conventions.yaml + author-dna.yaml`"
3. **Bắt buộc** ghi degradation `[R-KI-1] KI cleanup pending: {path}` vào bootstrap report.
4. Nếu KI file duplicate conventions/DNA: **từ chối dùng KI file đó trong phiên** — chỉ dùng `{{ platform.framework_root }}/knowledge/`.
5. Nhắc lại mỗi bootstrap cho đến khi cleanup xong.

Không được dùng "khuyến nghị" hay "có thể" — đây là hard enforcement.
External KI chỉ là pointer; source of truth luôn nằm trong `{{ platform.framework_root }}/knowledge/`.
