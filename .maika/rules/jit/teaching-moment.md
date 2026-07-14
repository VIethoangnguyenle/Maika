# jit/teaching-moment.md — Teaching Moment & External KI (JIT)

> JIT rule — load khi: phát hiện user correction (teaching moment) hoặc bootstrap
> phát hiện external KI. Write boundary core: `core/write-boundary.md`.

---

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

**Sau khi phân tách** (candidate-first — kernel §7 Learning Boundary):
1. **Ngay lập tức** đề xuất capture cho user xác nhận:
   - "Anh vừa dạy về `{topic}`. Em phân tách:
     - author-dna: `{thinking level — bỏ tên cụ thể}`
     - knowledge-snapshot: `{factual level}` (nếu có)
     Confirm?"
2. **Sau confirm**: ghi CANDIDATE vào `changes/<id>/learning/TEACHING_MOMENTS.yaml`
   (skill `knowledge-recorder`): id, statement, target (dna/convention/snapshot),
   evidence anchor, `user_confirmed: true`, `status: confirmed-pending-verification`,
   `source: author-described ({date})`. **KHÔNG ghi trực tiếp vào
   `knowledge/long-term/`** — promotion (kèm rule-projector regenerate khi entry
   mechanically checkable) do `knowledge-promoter` thực hiện tại `archive`,
   sau khi verification pass.
3. **Không được defer** sang phiên sau — candidate phải capture ngay trong phiên;
   `maika task archive` từ chối khi còn candidate confirmed chưa vào KNOWLEDGE_IMPACT.
4. **Nếu user từ chối**: ghi record `status: declined` + observation WARN vào
   `reviews/SKILL_FEEDBACK.yaml`: "[R-DNA-7] Teaching moment chưa capture: `{principle}`."
5. **Direct user directive** không bypass evidence/classification/provenance —
   nó chỉ bỏ recurrence threshold.

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
