---
name: author-dna-builder
version: '1.0'
description: >
  Phân tích codebase để infer coding philosophy và style của tác giả,
  sau đó interview để confirm/bổ sung, encode thành author-dna.yaml.
  Skill này tạo ra "judgment layer" — lens mà agent dùng khi evaluate design và propose solution.
  Dùng khi onboard project hoặc cần cập nhật coding DNA sau kiến trúc thay đổi lớn.
  KHÔNG dùng cho: scan convention (→ convention-intelligence-builder),
  tra cứu DNA đã có (→ đọc trực tiếp author-dna.yaml), review kiến trúc (→ architecture-reviewer).
trigger: /dna-scan
approve_trigger: /approve-dna
---

# Author DNA Builder

## 1. Mục tiêu & Triết lý thiết kế

`author-dna.yaml` khác hoàn toàn với `conventions.yaml`:

| | conventions.yaml | author-dna.yaml |
|-|-----------------|-----------------|
| **Capture** | Naming, suffix, package structure | Coding philosophy, decision principles |
| **Nguồn** | Extract từ code (observable) | Infer từ code + confirm với tác giả |
| **Agent dùng như** | Naming rule khi generate code | Judgment lens khi evaluate design |
| **Có thể sai không** | Hiếm — convention rõ trong code | Có — hypothesis cần author confirm |
| **Update khi nào** | Sau refactor lớn | Khi philosophy thay đổi (hiếm) |

**Nguyên tắc quan trọng nhất**: Agent KHÔNG tự kết luận philosophy từ code.
Agent chỉ được kết luận sau khi tác giả xác nhận. Mọi inference đều là
"hypothesis" cho đến khi có `confirmed: true` trong author-dna.yaml.

---

## 2. Khi nào dùng

- Lần đầu onboard project vào hệ thống (chạy sau `/convention-scan`).
- Tác giả cảm thấy agent đang đề xuất code "đúng về output nhưng sai về style".
- `author-dna.yaml` chưa tồn tại hoặc `status: stale`.
- Sau khi codebase có thay đổi kiến trúc lớn.

---

## Khi nào KHÔNG sử dụng

- Khi đang ở giữa Pha 2 hoặc Pha 3 của một task cụ thể.
- Khi chỉ muốn tra cứu DNA — đọc `author-dna.yaml` trực tiếp.
- Khi cần scan convention (→ convention-intelligence-builder).
- Khi cần review kiến trúc (→ architecture-reviewer).

---

## 3. Quy trình — 4 giai đoạn

### GIAI ĐOẠN 1: Code Evidence Scan

Thu thập evidence từ codebase qua UA + Codebase Memory. Bao gồm 5 dimension:
- **1A** Complexity Profile (nesting depth, early return frequency)
- **1B** Design Pattern Detection (CoR, Strategy, Factory, Spec, Builder...)
- **1C** If/Else vs Pattern Substitution (switch/instanceof count)
- **1D** Layer Boundary Discipline (creative overrides)
- **1E** Duplication vs Abstraction Tendency (Helper/Util/Base class usage)

### GIAI ĐOẠN 2: Hypothesis Generation

Từ evidence, tạo danh sách hypothesis có cấu trúc (id, claim, confidence, evidence, exemplar, counter_evidence, question_for_author).

> **Chi tiết đầy đủ (scan queries + hypothesis format)**: Xem [references/code-evidence-scan.md](references/code-evidence-scan.md)

---

### GIAI ĐOẠN 3: Interview Protocol

Agent trình bày hypothesis và hỏi theo cấu trúc sau:

```
"Em đã đọc toàn bộ codebase và có {n} hypothesis về coding style của anh.
Em sẽ trình bày từng hypothesis với evidence thực tế — anh confirm, reject,
hoặc làm rõ thêm.

Với mỗi hypothesis:
  [C] Confirm — đúng, encode vào DNA
  [R] Reject — sai hoặc chỉ tình cờ
  [P] Partially — đúng nhưng có điều kiện/ngoại lệ (anh mô tả thêm)
  [E] Expand — đúng, và còn nhiều hơn thế (anh muốn thêm)

Bắt đầu với hypothesis có confidence cao nhất:"
```

**Sau mỗi response của author:**

```
IF [C]: Ghi confirmed: true, lưu lý giải ngắn nếu author cung cấp
IF [R]: Ghi confirmed: false, lưu lý do reject để không re-infer sau này
IF [P]: Ghi confirmed: partial, lưu điều kiện/ngoại lệ, tạo sub-rule
IF [E]: Ghi confirmed: true, mở interview question mới để capture phần mở rộng
```

**Sau tất cả hypothesis từ code, agent hỏi thêm:**

```
"Ngoài những pattern em phát hiện được từ code, anh có nguyên tắc nào
trong đầu mà chưa thể hiện rõ trong codebase hiện tại không?
(Ví dụ: nguyên tắc anh muốn áp dụng nhưng codebase cũ chưa được refactor)"
```

→ Đây là nơi capture **philosophy chưa được code hóa** — quan trọng nhất.

---

### GIAI ĐOẠN 4: Encode → author-dna.yaml

**[PRE-PLACEMENT CHECKS — bắt buộc trước khi ghi entry bất kỳ]**

### Check 1 — Cross-check conventions.yaml (Gap 1)

Trước khi tạo SP/PP entry mới, scan **toàn bộ** conventions.yaml (không dựa vào số section — cấu trúc có thể đổi):
- Nếu tìm thấy entry tương tự với ≥70% overlap về nội dung, phân loại theo R-DNA-7 Bước 0:
  - Entry đó là **WHAT** (naming/structure/organization) → đúng chỗ ở conventions.
    Không tạo SP/PP trùng; chỉ tạo nếu author-dna cần capture thêm WHY/HOW mà conventions chưa có.
  - Entry đó là **WHY/HOW** (philosophy, decision principle — bỏ tên cụ thể vẫn đúng) →
    entry đang nằm **SAI file**. MIGRATE sang author-dna: tạo SP/PP entry mới ở author-dna,
    xoá entry khỏi conventions.yaml, ghi note vào phiên:
    "Migrated {entry-id} conventions → author-dna (philosophy không thuộc conventions)."
- conventions.yaml KHÔNG BAO GIỜ là nơi hợp lệ cho coding philosophy — chiều migrate chỉ có một: conventions → author-dna.

### Check 2 — R-DNA-7 Step 0: Phân tách abstraction level (Gap 2)

Trước khi place entry, test:
```
1. Bỏ tên cụ thể (table, class, method, column) → bài học còn đúng?
   CÓ  → author-dna (WHY/HOW)
   KHÔNG → tiếp

2. Về naming/structure/organization?
   CÓ  → conventions.yaml (WHAT)
   KHÔNG → tiếp

3. Về kiến trúc/component/relationship cụ thể?
   CÓ  → knowledge-snapshot.md (WHAT IS)
```
Dấu hiệu ghi SAI level: entry author-dna phải liệt kê tên bảng/cột → đang ghi nhầm chỗ.

### Check 3 — Deep confirmation (Gap 3)

Confirmation với tác giả phải validate 3 chiều, không chỉ "pattern có đúng không?":

```
Q1 (scope):    "Pattern này áp dụng ở đâu — toàn bộ codebase hay chỉ transaction module?"
Q2 (intent):   "Đây là rule bắt buộc hay lựa chọn thiết kế tuỳ context?"
Q3 (enforcement): "Nếu agent thấy vi phạm, phản ứng thế nào?
                   REJECT_AND_PROPOSE / FLAG_AND_WARN / SUGGEST?"
```

Không được ghi `REJECT_AND_PROPOSE` trừ khi author xác nhận rõ ràng "bắt buộc, không có ngoại lệ".
Default enforcement nếu không hỏi: `FLAG_AND_WARN`.

---

Sau interview, agent tổng hợp thành file:

```
GENERATE: {{ platform.framework_root }}/knowledge/long-term/author-dna.draft.yaml

FOR EACH confirmed hypothesis:
  → Encode vào section phù hợp (hard_principles / style_preferences / creative_overrides)
  → Gắn exemplar node_id thực tế từ evidence scan
  → Ghi confirmed: true + source: "codebase-inferred + author-confirmed"
  → Gắn applies_to: [<artifact-type tags>] — vocabulary do PROJECT định nghĩa
    (hỏi author trong interview nếu chưa rõ; principle áp dụng mọi nơi → applies_to: []).
    BẮT BUỘC có key này: entry thiếu applies_to sẽ KHÔNG được knowledge-index index
    → không vào gate slice (R-Guard-2).

FOR EACH author-added principle (từ open-ended question):
  → Encode với source: "author-described"
  → exemplar: null (chưa có trong code hiện tại)
  → agent_note: "Chưa có evidence trong code — cần tìm khi gặp task liên quan"

FOR EACH rejected hypothesis:
  → Ghi vào section rejected_hypotheses (để không re-infer)

META:
  - interview_date
  - hypotheses_proposed / confirmed / rejected / partial
  - principles_author_added (số principle author bổ sung ngoài code)
```

### Check 4 — Emit check_spec cho principle mechanizable (SP1a producer contract)

Khi encode mỗi principle (hard_principles / style_preferences), tham chiếu
[references/check-spec-mapping.md](references/check-spec-mapping.md) để xác định
principle có map được sang `ir_rule` không:
- Nếu CÓ → emit `mechanically_checkable: true` + `check_spec` (theo bảng mapping).
- Nếu KHÔNG (CoR, Template Method, Strategy, Factory boundary, SOLID, config-driven,
  extraction) → set `mechanically_checkable: false`. Principle này ở dạng semantic,
  do SP1b (subagent) enforce, không phải linter.

Sau khi DNA được approve (/approve-dna), regenerate ruleset qua rule-projector
(SP1a §3.2) — xem cuối check-spec-mapping.md để biết câu lệnh đầy đủ.

**Sau khi sinh draft:**

```
"author-dna.draft.yaml đã được tạo tại {{ platform.framework_root }}/knowledge/long-term/.
Anh mở file, đọc lại toàn bộ — chỉnh trực tiếp nếu cần.
Khi sẵn sàng: /approve-dna để commit chính thức."
```

---

## 4. /approve-dna Workflow

```
1. VALIDATE author-dna.draft.yaml:
   - YAML hợp lệ?
   - Có ít nhất 1 hard_principle được confirmed?
   - Tất cả exemplar node_id còn tồn tại trong UA graph?
     IF node_id không tồn tại: WARN, không block

2. CHECK conflict với conventions.yaml:
   - Nếu author-dna có principle mâu thuẫn với convention
     (ví dụ: DNA nói "không dùng X" nhưng conventions.yaml liệt kê X là pattern)
   → LIST conflicts, hỏi author resolve

3. PROMOTE:
   - Rename: author-dna.draft.yaml → author-dna.yaml
   - Update: meta.status = approved, meta.approved_at = timestamp
   - Backup: author-dna.draft.{timestamp}.yaml.bak

4. UPDATE AGENT_TRANSPARENCY:
   "[x] /approve-dna: author-dna.yaml committed
    - Hard principles: {n}
    - Style preferences: {n}
    - Creative overrides: {n}
    - Rejected hypotheses logged: {n}
    - Source: {n} codebase-inferred + {n} author-described"

5. NOTIFY:
   "✅ author-dna.yaml committed. Agent sẽ dùng coding DNA của anh
    như judgment layer từ phiên tiếp theo.

    Quan trọng: Khi agent đề xuất solution vi phạm hard principle,
    agent sẽ tự flag và propose alternative trước khi anh phải nói."
```

---

## 5. Cách Agent Dùng author-dna.yaml

Agent áp dụng DNA trong 4 context: Pha 2 (sinh spec), Pha 3 (apply/review),
Architecture Review, và fallback khi không có DNA.

## 6. Re-scan & Update Protocol

3 mode: [A] Add principle, [U] Update existing, [R] Full rescan.
Rejected hypothesis log ngăn agent re-infer cùng sai lầm.

## [L5] Periodic Re-Validation Trigger

Tự động gợi ý re-validation khi DNA stale (>90 ngày hoặc 2+ refactor tasks).

> **Chi tiết đầy đủ (usage, rescan, L5)**: Xem [references/dna-usage-guide.md](references/dna-usage-guide.md)

---

## Đầu ra

- **File chính**: `{{ platform.framework_root }}/knowledge/long-term/author-dna.draft.yaml` — bản nháp DNA chờ user review.
- **Sau `/approve-dna`**: `{{ platform.framework_root }}/knowledge/long-term/author-dna.yaml` — bản chính thức (approved).
- **Cập nhật**: `{{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md` — ghi lại kết quả scan + interview.

---

## 7. AGENT_TRANSPARENCY

```
[x] author-dna-builder: /dna-scan
  - Giai đoạn 1 (scan): {n} method analyzed, {n} pattern found
  - Giai đoạn 2 (hypothesis): {n} hypotheses generated
    ({n} HIGH, {n} MEDIUM, {n} LOW confidence)
  - Giai đoạn 3 (interview): {n} confirmed, {n} rejected, {n} partial
  - Giai đoạn 4 (encode): author-dna.draft.yaml generated
  - Status: awaiting /approve-dna
```
