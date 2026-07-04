---
name: spec-validator
version: '1.1'
description: >
  Kiểm tra spec (OpenSpec artifacts) trước và sau khi apply — pre-apply gate, AC coverage check, post-apply verify.
  Dùng khi cần validate spec trước apply hoặc verify kết quả sau apply.
  KHÔNG dùng cho: sinh spec mới (→ openspec-propose),
  review kiến trúc (→ architecture-reviewer), chuẩn hoá yêu cầu (→ requirement-analyst).
pre_conditions:
  - file: "{{ platform.framework_root }}/knowledge/active/REQUIREMENT.md"
    condition: not_skeleton
    on_fail: "ABORT — không có REQUIREMENT để validate spec"
  - phase: pha-2
    condition: phase_done
    on_fail: "ABORT — spec chưa được sinh (phase_state chưa đạt phase-2-done)"
---

# Spec Validator — Kiểm tra Spec Trước và Sau Apply

## 1. Mục tiêu

- **Pre-apply gate**: Chặn apply khi spec có vấn đề nghiêm trọng (thiếu AC, mâu thuẫn với REQUIREMENT, không có test path).
- **AC coverage check**: Đảm bảo mỗi Acceptance Criterion trong REQUIREMENT.md được cover bởi ít nhất 1 task trong spec.
- **Post-apply verify**: Sau khi apply, kiểm tra nhanh các file đã thay đổi so với spec dự kiến.

Skill này là **quality gate** — không sinh spec, không sửa code.

---

## 2. Khi nào dùng

- Trước khi `/task apply` → chạy pre-apply gate + AC coverage check.
- Sau khi `/task apply` hoàn thành → chạy post-apply verify (tuỳ chọn nhưng khuyến nghị).
- Khi user yêu cầu "kiểm tra spec" hoặc "validate spec".

---

## Khi nào KHÔNG sử dụng

- Khi cần sinh spec mới (→ openspec-propose).
- Khi cần review kiến trúc (→ architecture-reviewer).
- Khi cần chuẩn hoá yêu cầu (→ requirement-analyst).
- Khi chưa có REQUIREMENT.md — chạy requirement-analyst trước.

---

## 3. Quy trình

### 3.1 `pre_apply_gate(spec_path, requirement_path)`

```
INPUT:
  spec_path       — đường dẫn tới spec file (openspec/changes/<change-id>/)
  requirement_path — {{ platform.framework_root }}/knowledge/active/REQUIREMENT.md

STEPS:
1. Đọc spec artifacts: proposal.md, design.md, spec.md, tasks.md (tuỳ cái nào tồn tại)
2. Đọc REQUIREMENT.md

CHECKS:
  [C1] Spec có change_id rõ ràng không?
       → FAIL: "Thiếu change_id — spec chưa được OpenSpec sinh đúng format"

  [C2] proposal.md có phần "what" và "why" không?
       → WARN: "proposal.md thiếu mô tả rõ what/why"

  [C3] spec.md / tasks.md có ít nhất 1 task/file change không?
       → FAIL: "Spec trống — không có gì để apply"

  [C4] Spec có đề cập đến file/module nằm ngoài PROJECT_ROOTS không?
       → WARN: "Spec chạm ngoài PROJECT_ROOTS — verify với user"

  [C5] OPENSPEC_STATE trong AGENT_TRANSPARENCY = "propose_done" không?
       → FAIL nếu không: "Spec chưa được confirm propose — chạy /task spec trước"

  [C6] (Optional) Contract-Spec alignment:
       1. Đọc REQUIREMENT.md section "Technical Design Contract"
       2. Nếu section trống hoặc chỉ là placeholder → bỏ qua C6
       3. Nếu section có nội dung:
          - Extract danh sách interface được định nghĩa:
            * Endpoints (REST: method + path)
            * Topics (Kafka: topic name + action)
            * Services (gRPC: service + method)
          - So sánh với tasks trong spec (tasks.md / spec.md):
            * Mỗi interface định nghĩa trong contract CÓ ít nhất 1 task tương ứng?
          - Nếu có interface chưa được cover:
            → WARN: "Contract định nghĩa {interface} nhưng spec không có task tương ứng"
       → Chỉ WARN, KHÔNG BLOCK — có thể interface được cover implicit trong task chung
       → Ghi: "[C6-CONTRACT] {n_covered}/{n_total} interfaces covered. Missing: {list if any}"

RESULT:
  → PASS: tất cả [C] pass (FAIL = 0, WARN có thể có)
  → BLOCK: ít nhất 1 [C] = FAIL
  → Ghi kết quả vào AGENT_TRANSPARENCY:
     "[SPEC-VALIDATE] pre_apply_gate: {PASS|BLOCK} — {list issues}"
```

### 3.2 `check_ac_coverage(spec_path, requirement_path)`

```
INPUT: (như trên)

STEPS:
1. Đọc REQUIREMENT.md — extract tất cả Acceptance Criteria (AC list)
2. Đọc tasks.md (hoặc spec.md) — extract tất cả tasks/changes

ALGORITHM:
  FOR EACH ac IN requirement_ac_list:
    covered = False
    FOR EACH task IN spec_tasks:
      IF semantic_match(ac, task):  ← keyword/entity overlap
        covered = True
        break
    IF NOT covered:
      uncovered_acs.append(ac)

RESULT:
  IF uncovered_acs is empty:
    → PASS: "Tất cả {n} AC đã được cover"
  ELSE:
    → WARN: "AC chưa được cover trong spec: {list}"
    → Không BLOCK apply — chỉ WARN vì có thể AC được cover implicitly
    → User tự quyết định có cần thêm task không

  Ghi vào AGENT_TRANSPARENCY:
    "[AC-COVERAGE] {n_covered}/{n_total} AC covered. Uncovered: {list if any}"
```

### 3.2b `check_integration_coverage(spec_path, requirement_path)`

```
INPUT: (như trên)

STEPS:
1. Đọc REQUIREMENT.md — extract danh sách integration từ section "Integrations & Field Mapping"
   (mỗi heading "### Integration: <tên>" là một integration).
   - Section không tồn tại, hoặc ghi "Không phát hiện integration mới" → SKIP (PASS, không check).
2. Đọc tasks.md (hoặc spec.md) — extract tất cả tasks/changes.

ALGORITHM:
  FOR EACH integration IN requirement_integrations:
    covered = False
    FOR EACH task IN spec_tasks:
      IF semantic_match(integration, task):  ← tên integration/endpoint/field xuất hiện trong task mapper/adapter/DTO
        covered = True
        break
    IF NOT covered:
      uncovered.append(integration)

RESULT:
  IF uncovered is empty:
    → PASS: "Tất cả {n} integration đã có task mapper/adapter"
  ELSE:
    → WARN: "Integration chưa có task mapper/adapter trong spec: {list}"
    → Không BLOCK apply — user tự quyết định có cần thêm task không

  Ghi vào AGENT_TRANSPARENCY:
    "[INTEGRATION-COVERAGE] {n_covered}/{n_total} integration covered. Uncovered: {list if any}"
```

### 3.3 `post_apply_verify(spec_path, changed_files)`

```
INPUT:
  spec_path     — spec đã apply
  changed_files — danh sách file đã thay đổi (từ apply output)

STEPS:
1. Đọc tasks.md — extract danh sách file/module dự kiến bị chạm
2. So sánh với changed_files thực tế:
   a. File dự kiến bị chạm nhưng KHÔNG có trong changed_files → WARN "Missing change"
   b. File KHÔNG dự kiến bị chạm nhưng lại có trong changed_files → WARN "Unexpected change"
3. Kiểm tra nhanh: file đã thay đổi có compile/không có syntax error? (nếu có tool hỗ trợ)

RESULT:
  IF no warnings:
    → "Post-apply verify: OK — changes match spec"
  ELSE:
    → List các mismatch
    → Không auto-rollback, chỉ flag cho user

  Ghi vào AGENT_TRANSPARENCY:
    "[POST-APPLY] verify: {n_match}/{n_expected} matches. Issues: {list if any}"
```

---

### 3.4 `post_apply_contract_dag_check(contract_dag_path, changed_files)`

```
INPUT:
  contract_dag_path — {{ platform.framework_root }}/knowledge/active/microloop/CONTRACT_DAG.md
  changed_files     — danh sách file đã thay đổi

STEPS:
1. Đọc CONTRACT_DAG.md.
2. Fail nếu còn node status `pending`, `in_progress`, `blocked`, hoặc `stale`.
3. Với mỗi node:
   - Kiểm tra changed_files của node nằm trong `writes`.
   - Nếu node type = `leaf`, kiểm tra node không ghi file thuộc contract/base.
   - Nếu node có `contract_ref`, kiểm tra version bằng contract node hiện tại.
4. Đọc các request artifact nếu tồn tại:
   - CONTEXT_REQUEST.*.md
   - CONTRACT_CHANGE_REQUEST.*.md
   - INTEGRATION_REQUEST.*.md
5. Fail nếu request chưa được resolved hoặc chưa được ghi rõ trong AGENT_TRANSPARENCY.

RESULT:
  → PASS: DAG hoàn tất, không stale, không boundary violation.
  → BLOCK: có node chưa xong, stale, contract_version mismatch, hoặc unresolved request.

Ghi vào AGENT_TRANSPARENCY:
  "[CONTRACT-DAG-CHECK] {PASS|BLOCK} — {issues}"
```

---

## 4. Tích hợp với `/task apply` (task.md)

`spec-validator` được gọi tự động trong Pha 3:

```
/task apply <ticket-id>
  ↓
spec-validator.pre_apply_gate()     ← nếu BLOCK: dừng, hỏi user
  ↓
spec-validator.check_ac_coverage()  ← nếu WARN: hiển thị, hỏi user có muốn tiếp không
  ↓
spec-validator.check_integration_coverage()  ← nếu WARN: hiển thị integration chưa cover, hỏi user
  ↓
[user confirm] → Hybrid Contract DAG micro-loop
  ↓
spec-validator.post_apply_contract_dag_check()
  ↓
spec-validator.post_apply_verify()  ← sau apply
```

Nếu `pre_apply_gate` trả về BLOCK:
- Dừng hoàn toàn `/task apply`.
- Hiển thị issues cho user.
- Gợi ý action: chạy lại `/task spec` hoặc sửa spec thủ công.

---

## 5. Cập nhật AGENT_TRANSPARENCY

Ghi sau mỗi lần chạy:

- `[x] spec-validator: pre_apply_gate — {PASS|BLOCK}`
- `[x] spec-validator: ac_coverage — {n}/{n} covered`
- `[x] spec-validator: contract_alignment — {n}/{n} interfaces covered` (nếu C6 chạy)
- `[x] spec-validator: post_apply_verify — {OK|issues}`

---

## Gotchas

- **[G1] OpenSpec artifact path versioning**: OpenSpec artifact path (`changes/{id}/`) có thể thay đổi giữa versions. Luôn dùng relative path từ project root và verify file tồn tại trước khi đọc.
- **[G2] C6 gate cần design contract**: C6 (Contract Alignment check) chỉ chạy khi REQUIREMENT.md có section "Design Contract" hoặc "Interface Specification". Nếu không có → C6 skip silently, ghi note trong output.
- **[G3] Pre-apply vs Post-apply output format**: Pre-apply gate trả `PASS | BLOCK` (binary). Post-apply verify trả `OK | issues list`. Không nhầm 2 format khi parse kết quả.
- **[G4] AC coverage false positive**: Nếu Acceptance Criteria quá generic (e.g. "Hệ thống hoạt động đúng"), coverage check sẽ trả 100% nhưng thực tế chưa verify gì. Agent phải WARN khi phát hiện AC quá mơ hồ.

---

## Đầu ra

- **Kết quả pre-apply gate**: `PASS` hoặc `BLOCK` — quyết định có được apply hay không.
- **Báo cáo AC coverage**: `{n_covered}/{n_total}` AC được cover.
- **Kết quả post-apply verify**: `OK` hoặc danh sách mismatch.
- **Kết quả Contract DAG check**: `PASS` hoặc `BLOCK` — xác nhận không còn stale node, contract mismatch, hoặc unresolved request.
- **Cập nhật**: `{{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md` — ghi lại kết quả mỗi lần chạy.

---

## 6. Post-Apply DNA Compliance Check (`post_apply_dna_check`)

> **Mục tiêu**: Thay thế Reviewer Agent riêng bằng cách mở rộng spec-validator — cùng chức năng verification, 1/10 effort.
> **Thời điểm chạy (SP1b):** phần semantic chạy **per-task trong micro-loop** (bước 4c của Pha 3
> trong task.md), **trước** `post_apply_verify`. (Trước SP1b: chạy 1 lần sau `post_apply_verify` —
> nay đã chuyển vào loop để check trên surface nhỏ của từng task.)
>
> **SP1b split:** Rule cơ học (nesting, no-else, max-lines, naming, javadoc) đã chuyển
> sang **mechanical gate deterministic** (SP1a) chạy trong micro-loop — KHÔNG check lại ở
> đây. §6 giờ chỉ giữ phần **semantic** (HP-1/2/3/5/8/9 — pattern judgment), chạy per-task
> trên DIFF của 1 task (surface nhỏ), không phải cuối cả đợt apply.

```
INPUT:
  changed_files — danh sách file đã thay đổi (từ apply output)

PRE-CONDITION:
  DNA đã trong context của executor qua `dna_slice` trong TASK_HANDOFF (SP1b micro-loop).
  → author-dna.yaml slice liên quan task đã sẵn (thay cho DNA-RELOAD nghi thức cũ).

STEPS:

1. Load rule sources (GENERIC — đọc từ file, KHÔNG hardcode):

   a. Đọc author-dna.yaml → extract:
      - hard_principles[]     → mỗi item có id, severity mặc định = BLOCK
      - soft_preferences[]    → severity mặc định = WARN
      - complexity_thresholds → mỗi threshold là 1 check, severity = WARN
      - style_preferences[]   → severity = WARN

   b. Đọc conventions.yaml (nếu tồn tại, status=approved) → extract:
      - naming_patterns[]     → severity = WARN
      - package_structure[]   → severity = WARN
      Nếu chỉ có conventions.draft.yaml → SKIP (chưa approved)

2. Build checklist động từ sources ở bước 1:

   checklist = []
   FOR EACH hp IN hard_principles:
     checklist.add({
       id:       hp.id,           # e.g. "HP-6"
       describe: hp.description,  # e.g. "Zero nesting"
       source:   "author-dna.yaml/hard_principles",
       severity: BLOCK
     })
   FOR EACH sp IN soft_preferences:
     checklist.add({ id: sp.id, ..., severity: WARN })
   FOR EACH threshold IN complexity_thresholds:
     checklist.add({ id: threshold.key, ..., severity: WARN })
   FOR EACH convention IN naming_patterns + package_structure:
     checklist.add({ id: convention.pattern, ..., severity: WARN })

3. Verify — với MỖI file trong changed_files:

   FOR EACH check IN checklist:
     Đánh giá file có vi phạm check.describe không
     → Nếu vi phạm: ghi { file, check.id, check.severity, line_hint, suggestion }

RESULT:
  counts = { BLOCK: n, WARN: m }

  IF counts.BLOCK > 0:
    → "DNA COMPLIANCE: BLOCK — {n} hard principle violations"
    → List tất cả violations kèm fix suggestion
    → Agent PHẢI fix trước khi hoàn thành POST-PHASE SELF-CHECK

  IF counts.BLOCK == 0 AND counts.WARN > 0:
    → "DNA COMPLIANCE: PASS with {m} warnings"
    → List warnings — user tự quyết định có fix không

  IF counts.BLOCK == 0 AND counts.WARN == 0:
    → "DNA COMPLIANCE: CLEAN — no violations detected"

  Ghi vào AGENT_TRANSPARENCY:
    "[DNA-CHECK] post_apply_dna_check: {BLOCK|PASS|CLEAN} — {summary}"

  Ghi vào Violation Log (trong AGENT_TRANSPARENCY):
    Mỗi violation 1 dòng: | Pha | Loại | Rule ID | Severity | Đã fix? | Ghi chú |
```

### Gotchas cho DNA Check

- **[G5] DNA phải có trong context qua handoff**: `post_apply_dna_check` (phần semantic) giả định DNA slice đã trong context executor qua `dna_slice` của TASK_HANDOFF (SP1b). Nếu handoff thiếu `dna_slice` → kết quả check không đáng tin.
- **[G6] Checklist là dynamic**: Skill KHÔNG hardcode rule cụ thể (HP-6, HP-7…). Rule nào có trong `author-dna.yaml` thì check, không có thì skip. Nếu project đổi DNA → checklist tự đổi theo.
- **[G7] Conventions draft bị skip**: Chỉ load `conventions.yaml` khi `status: approved`. Draft conventions KHÔNG được enforce — đây là by-design.
- **[G8] False negative**: Check dựa trên agent judgment + pattern matching, không phải AST analysis. Violations phức tạp (e.g. nesting qua method extraction) có thể miss.
