# Plan triển khai: Chất lượng Task-Run — Integration Inventory + Thin Orchestrator

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** REQUIREMENT.md mang inventory integration + bảng field mapping xuyên suốt 3 pha, và tier `fresh-session` được tự động hóa (worker context mới per task qua `worker_command`) kèm lưới an toàn SESSION-GATE trong write-gate.

**Architecture:** Phần A (Task 1–5) thêm section "Integrations & Field Mapping" vào template/skill/validator/workflow — thuần chỉnh sửa markdown hướng dẫn agent. Phần B (Task 6–11) thêm code Python: `dispatch_worker` + `make_worker_runner` vào micro-loop orchestrator (pattern injectable-runner như `make_gate_fn` có sẵn), session-identity + SESSION-GATE vào `write_gate.py`, và cập nhật text workflow/rules. Hai phần độc lập, land riêng được.

**Tech Stack:** Python 3.10+, pytest, PyYAML (đã có — không thêm dependency mới), Jinja2 placeholder convention của Maika (`{{ platform.framework_root }}`, `{% if %}`).

**Spec:** `docs/superpowers/specs/2026-07-03-task-run-quality-thin-orchestrator-design.md`

## Ràng buộc toàn cục

- **Tiếng Việt** cho mọi văn bản mới (docstring, message, hướng dẫn trong .md) — giữ identifier kỹ thuật tiếng Anh. Quy tắc user, override style tiếng Anh cũ ở vùng lân cận.
- **Không thêm dependency** Python mới; chỉ dùng stdlib + PyYAML.
- **Giữ nguyên placeholder** `{{ platform.framework_root }}` / `{{ tools.* }}` dạng thô trong file `.maika/` (được Jinja render lúc scaffold downstream).
- **Tests phải pass trên cả ubuntu + windows** (CI pytest matrix) — không phụ thuộc `/proc` thật trong test (dùng fake `proc_root`), không dùng lệnh POSIX-only trong test (dùng `sys.executable`).
- **Backward compatible:** chữ ký hàm hiện có chỉ được thêm keyword arg có default; test cũ không được sửa để pass.
- **DEVELOPMENT_RULES.md:** không khai báo thứ không có consumer; mỗi thay đổi trace về observed failure trong spec.
- Commit message: convention repo (`feat(...)`, `fix(...)`, `docs:`, `test(...)`) + `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.
- Chạy test từ repo root: `python3 -m pytest <path> -v`.

---

## PHẦN A — Integration Inventory (Task 1–5)

### Task 1: Section "Integrations & Field Mapping" trong REQUIREMENT template

**Files:**
- Modify: `.maika/knowledge/templates/REQUIREMENT.tpl.md` (chèn sau section "Technical Design Contract", trước `## Giả định (Assumptions)`)

**Interfaces:**
- Produces: heading chuẩn `## Integrations & Field Mapping` + heading con `### Integration: <tên>` — Task 2, 3, 4, 5 tham chiếu đúng các heading này (validator match theo `### Integration:`).

- [ ] **Bước 1: Chèn section vào template**

Dùng Edit trên `.maika/knowledge/templates/REQUIREMENT.tpl.md`:

`old_string`:

```markdown
### Response / Event Schema
- <!-- Cấu trúc dữ liệu đầu ra, HTTP Status, Mã lỗi (Error Codes) -->

---

## Giả định (Assumptions)
```

`new_string`:

```markdown
### Response / Event Schema
- <!-- Cấu trúc dữ liệu đầu ra, HTTP Status, Mã lỗi (Error Codes) -->

---

## Integrations & Field Mapping

<!-- Một block cho mỗi integration mới (third-party API hệ thống cần gọi/nhận). -->
<!-- Nếu task không có integration mới: ghi "Không phát hiện integration mới". -->

### Integration: <!-- tên -->

- Hướng: <!-- outbound (hệ thống gọi third-party) / inbound (third-party gọi hệ thống) -->
- Protocol & Auth: <!-- REST/gRPC/SOAP/… + cơ chế auth -->
- Endpoint/Operation liên quan: <!-- ... -->
- Tài liệu nguồn: <!-- link doc / API spec -->

| Field third-party | Field canonical (hệ thống) | Transform / Serialize (ý định) | Nguồn |
|---|---|---|---|
| <!-- mobileNo --> | <!-- phoneNumber --> | <!-- rename khi (de)serialize --> | <!-- doc §x + UA: DTO --> |

- Field chưa map được: <!-- field — lý do; mirror vào "Vấn đề yêu cầu" -->

---

## Giả định (Assumptions)
```

- [ ] **Bước 2: Verify**

Run: `grep -c "Integrations & Field Mapping" .maika/knowledge/templates/REQUIREMENT.tpl.md`
Expected: `1`

- [ ] **Bước 3: Commit**

```bash
git add .maika/knowledge/templates/REQUIREMENT.tpl.md
git commit -m "feat(template): thêm section Integrations & Field Mapping vào REQUIREMENT template"
```

---

### Task 2: spec-extract — Bước 5b trích xuất integration

**Files:**
- Modify: `.maika/skills/spec-extract/SKILL.md` (3 chỗ: skeleton output §3, Bước 5b mới sau Bước 5, Bước 10)

**Interfaces:**
- Consumes: heading template từ Task 1 (`## Integrations & Field Mapping`, `### Integration: <tên>`).
- Produces: quy trình Bước 5b — Task 4 (validator) đọc output theo format này.

- [ ] **Bước 1: Thêm section vào skeleton output §3**

Edit `.maika/skills/spec-extract/SKILL.md`, trong khối skeleton markdown của §3 Output:

`old_string`:

```markdown
  #### Ràng buộc phi chức năng
  - ...

  #### Độ tin cậy tài liệu
```

`new_string`:

```markdown
  #### Ràng buộc phi chức năng
  - ...

  #### Integrations & Field Mapping
  - Integration: <tên> (hướng, protocol & auth, endpoint, tài liệu nguồn)
  - Bảng field mapping: field third-party → field canonical + ý định transform + nguồn
  - Field chưa map được → mirror vào "Lỗ hổng & câu hỏi mở"

  #### Độ tin cậy tài liệu
```

- [ ] **Bước 2: Thêm Bước 5b sau Bước 5**

Edit `.maika/skills/spec-extract/SKILL.md`:

`old_string`:

```markdown
   #### Luồng lỗi / ngoại lệ

   - Trường hợp X: ...
   - Trường hợp Y: ...
   ```

---

### Bước 6 — Trích quy tắc nghiệp vụ (Business Rules)
```

`new_string`:

```markdown
   #### Luồng lỗi / ngoại lệ

   - Trường hợp X: ...
   - Trường hợp Y: ...
   ```

---

### Bước 5b — Thống kê Integration & Field Mapping

1. Quét tài liệu tìm dấu hiệu integration third-party mới:

   - Section API spec / Interface / Contract / Integration (đã nhận diện ở Bước 3).
   - Bảng endpoint, sample request/response payload, attachment OpenAPI/WSDL (đã thu ở Bước 2).
   - Câu mô tả dạng "hệ thống gọi X" / "nhận callback từ Y".

2. Với mỗi integration phát hiện được, ghi block theo format template `REQUIREMENT.tpl.md`
   (section "Integrations & Field Mapping"): tên, hướng (outbound/inbound), protocol & auth,
   endpoint/operation, tài liệu nguồn.

3. Lập bảng field mapping cho từng integration:

   - **Field third-party**: lấy nguyên văn từ tài liệu/API spec (vd `mobileNo`).
   - **Field canonical**: xác định theo **UA-first** (§Quy tắc cốt lõi):
     `{{ tools.domain_overview }}` → domain/DTO liên quan, sau đó Codebase Memory extract
     field trong DTO/domain model hiện có (vd `phoneNumber` trong `CustomerDTO`).
   - **Transform / Serialize**: chỉ ghi **ý định** (rename, format date, split/merge, dịch enum).
     KHÔNG ghi cú pháp ngôn ngữ cụ thể (`@JsonProperty`, pydantic alias…) — executor Pha 3
     resolve cú pháp từ conventions/author-dna.
   - **Nguồn**: trích dẫn section tài liệu + node UA đã probe.

4. Field không xác định được canonical (domain model chưa có field tương ứng, UA không trả lời):

   - Ghi vào "Field chưa map được" kèm lý do.
   - Mirror thành câu hỏi trong "Lỗ hổng & câu hỏi mở" (Bước 10).

5. Không có integration mới → ghi rõ "Không phát hiện integration mới" (không bỏ trống section).

---

### Bước 6 — Trích quy tắc nghiệp vụ (Business Rules)
```

- [ ] **Bước 3: Bổ sung nguồn gap vào Bước 10**

Edit `.maika/skills/spec-extract/SKILL.md`:

`old_string`:

```markdown
1. Liệt kê rõ:

   - Phần nào tài liệu **không đề cập** (ví dụ: case edge, luồng lỗi, migration).
```

`new_string`:

```markdown
1. Liệt kê rõ:

   - Phần nào tài liệu **không đề cập** (ví dụ: case edge, luồng lỗi, migration).
   - Field chưa map được từ Bước 5b (integration có field không tìm thấy canonical tương ứng).
```

- [ ] **Bước 4: Verify**

Run: `grep -c "Bước 5b" .maika/skills/spec-extract/SKILL.md`
Expected: `3` (heading + 2 tham chiếu)

- [ ] **Bước 5: Commit**

```bash
git add .maika/skills/spec-extract/SKILL.md
git commit -m "feat(spec-extract): Bước 5b thống kê integration + field mapping (UA-first canonical)"
```

---

### Task 3: requirement-analyst — mở rộng Bước 8 cho đường ticket

**Files:**
- Modify: `.maika/skills/requirement-analyst/SKILL.md` (2 chỗ: §4 Output, Bước 8)

**Interfaces:**
- Consumes: heading template từ Task 1.

- [ ] **Bước 1: Thêm mục vào §4 Output**

Edit `.maika/skills/requirement-analyst/SKILL.md`:

`old_string`:

```markdown
- **Technical Design Contract (Đầu ra cho Client)**:
  - Định nghĩa rõ giao thức, endpoint, format (REST/gRPC/Kafka).
  - Schema đầu vào (Request/Message) và đầu ra (Response/Event).
  - Các thiết kế này phải tuân thủ kiến trúc hệ thống hiện tại.
```

`new_string`:

```markdown
- **Technical Design Contract (Đầu ra cho Client)**:
  - Định nghĩa rõ giao thức, endpoint, format (REST/gRPC/Kafka).
  - Schema đầu vào (Request/Message) và đầu ra (Response/Event).
  - Các thiết kế này phải tuân thủ kiến trúc hệ thống hiện tại.
- **Integrations & Field Mapping**:
  - Integration third-party mới (hướng, protocol & auth, endpoint, tài liệu nguồn).
  - Bảng field mapping: field third-party → field canonical + ý định transform + nguồn.
  - Field chưa map được → mirror vào "Vấn đề yêu cầu".
```

- [ ] **Bước 2: Thêm mục 4 vào Bước 8**

Edit `.maika/skills/requirement-analyst/SKILL.md`:

`old_string`:

```markdown
3. Đồng bộ kiến trúc:
   - Contract đề xuất phải tuân thủ kiến trúc hiện có.
   - Đọc `conventions.yaml` (section `design_patterns`, `upstream_constraints`) và `knowledge-snapshot.md` để xác định các pattern/framework bắt buộc của hệ thống.
   - Nếu `conventions.yaml` chưa có hoặc status ≠ approved → ghi giả định vào section "Giả định", không tự bịa pattern.
```

`new_string`:

```markdown
3. Đồng bộ kiến trúc:
   - Contract đề xuất phải tuân thủ kiến trúc hiện có.
   - Đọc `conventions.yaml` (section `design_patterns`, `upstream_constraints`) và `knowledge-snapshot.md` để xác định các pattern/framework bắt buộc của hệ thống.
   - Nếu `conventions.yaml` chưa có hoặc status ≠ approved → ghi giả định vào section "Giả định", không tự bịa pattern.
4. Thống kê Integration & Field Mapping (khi ticket/tài liệu chạm tới third-party API mới):
   - Ghi block theo format template `REQUIREMENT.tpl.md` section "Integrations & Field Mapping":
     tên, hướng (outbound/inbound), protocol & auth, endpoint/operation, tài liệu nguồn.
   - Bảng field mapping: field third-party (nguyên văn từ tài liệu) → field canonical
     (xác định UA-first qua domain model/DTO hiện có) + **ý định** transform (rename/format/…).
   - KHÔNG ghi cú pháp serialize cụ thể của ngôn ngữ — executor Pha 3 resolve từ
     conventions/author-dna.
   - Field chưa map được → ghi lý do + mirror vào Bước 9 "Vấn đề yêu cầu".
```

- [ ] **Bước 3: Verify**

Run: `grep -c "Integrations & Field Mapping" .maika/skills/requirement-analyst/SKILL.md`
Expected: `2`

- [ ] **Bước 4: Commit**

```bash
git add .maika/skills/requirement-analyst/SKILL.md
git commit -m "feat(requirement-analyst): thống kê integration + field mapping ở Bước 8"
```

---

### Task 4: spec-validator check_integration_coverage + wiring vào task.md

**Files:**
- Modify: `.maika/skills/spec-validator/SKILL.md` (thêm §3.2b sau §3.2, cập nhật §4 flow + §5 transparency)
- Modify: `.maika/workflows/task.md` (§2 bước 5 — yêu cầu task mapper; §3 bước 3 — gọi check mới)

**Interfaces:**
- Consumes: heading `### Integration:` từ Task 1; câu skip "Không phát hiện integration mới" từ Task 2.
- Produces: check `check_integration_coverage(spec_path, requirement_path)` — được task.md §3 gọi.

- [ ] **Bước 1: Thêm §3.2b vào spec-validator**

Edit `.maika/skills/spec-validator/SKILL.md` — chèn ngay trước `### 3.3 \`post_apply_verify(spec_path, changed_files)\``:

`old_string`:

```markdown
### 3.3 `post_apply_verify(spec_path, changed_files)`
```

`new_string`:

````markdown
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
````

- [ ] **Bước 2: Cập nhật flow §4 của spec-validator**

Edit `.maika/skills/spec-validator/SKILL.md`:

Trong khối flow của §4 có dòng bắt đầu bằng `spec-validator.check_ac_coverage()` (dòng duy nhất trong file bắt đầu như vậy — Read file để lấy nguyên văn đầy đủ). Edit: `old_string` = nguyên văn dòng đó; `new_string` = dòng đó giữ nguyên + xuống dòng + thêm:

```markdown
spec-validator.check_integration_coverage()  ← nếu WARN: hiển thị integration chưa cover, hỏi user
```

- [ ] **Bước 3: Yêu cầu task mapper trong task.md §2 bước 5**

Edit `.maika/workflows/task.md`:

`old_string`:

```markdown
   - Chờ spec được sinh ra (file spec riêng, ví dụ trong thư mục `spec/`).
```

`new_string`:

```markdown
   - Chờ spec được sinh ra (file spec riêng, ví dụ trong thư mục `spec/`).
   - **Integration coverage**: nếu REQUIREMENT có section "Integrations & Field Mapping" với
     integration mới → `tasks.md` sinh ra PHẢI có task mapper/adapter tương ứng cho từng
     integration (DTO + mapping thuộc contract node trong CONTRACT_DAG ở Pha 3).
```

- [ ] **Bước 4: Gọi check mới trong task.md §3 bước 3**

Edit `.maika/workflows/task.md`:

`old_string`:

```markdown
   - Gọi `spec-validator.check_ac_coverage(spec_path, requirement_path)`:
     - Nếu có AC chưa cover: hiển thị danh sách, hỏi user có muốn tiếp không.
```

`new_string`:

```markdown
   - Gọi `spec-validator.check_ac_coverage(spec_path, requirement_path)`:
     - Nếu có AC chưa cover: hiển thị danh sách, hỏi user có muốn tiếp không.
   - Gọi `spec-validator.check_integration_coverage(spec_path, requirement_path)`:
     - Nếu có integration chưa có task mapper/adapter: hiển thị danh sách, hỏi user có muốn tiếp không.
```

- [ ] **Bước 5: Verify**

Run: `grep -c "check_integration_coverage" .maika/skills/spec-validator/SKILL.md .maika/workflows/task.md`
Expected: `.maika/skills/spec-validator/SKILL.md:2` (hoặc hơn) và `.maika/workflows/task.md:1`

- [ ] **Bước 6: Commit**

```bash
git add .maika/skills/spec-validator/SKILL.md .maika/workflows/task.md
git commit -m "feat(spec-validator): check_integration_coverage — cảnh báo integration thiếu task mapper"
```

---

### Task 5: Bảng mapping vào KNOWLEDGE_PACK + handoff node mapper (task.md §3.5)

**Files:**
- Modify: `.maika/workflows/task.md` (§3 bước 5.a và 5.c)

**Interfaces:**
- Consumes: section Integrations trong REQUIREMENT (Task 1–3).

- [ ] **Bước 1: Thêm nguồn Integrations vào KNOWLEDGE_PACK (5.a)**

Edit `.maika/workflows/task.md`:

`old_string`:

```markdown
   a. Build `KNOWLEDGE_PACK.md` from REQUIREMENT, EXPLORE_CONTEXT, knowledge-snapshot,
      conventions, author-dna, OpenSpec artifacts, UA/KG evidence, db-explorer evidence, and relevant archive/memory.
```

`new_string`:

```markdown
   a. Build `KNOWLEDGE_PACK.md` from REQUIREMENT, EXPLORE_CONTEXT, knowledge-snapshot,
      conventions, author-dna, OpenSpec artifacts, UA/KG evidence, db-explorer evidence, and relevant archive/memory.
      - Section "Integrations & Field Mapping" của REQUIREMENT là nguồn BẮT BUỘC của
        Knowledge Pack khi task có integration mới.
```

- [ ] **Bước 2: Nhúng bảng mapping vào handoff node mapper (5.c)**

Edit `.maika/workflows/task.md`:

`old_string`:

```markdown
      - Assemble `TASK_HANDOFF.<node-id>.md` with Knowledge Pack slice, DNA slice, convention slice,
        architecture boundary, allowed/read-only files, and feedback if retrying.
```

`new_string`:

```markdown
      - Assemble `TASK_HANDOFF.<node-id>.md` with Knowledge Pack slice, DNA slice, convention slice,
        architecture boundary, allowed/read-only files, and feedback if retrying.
      - Node mapper/adapter: nhúng NGUYÊN bảng field mapping của integration tương ứng vào
        `## Evidence` / `## Constraints` của handoff — executor không tự tra lại tài liệu;
        cú pháp serialize cụ thể resolve từ dna_slice/convention_slice.
```

- [ ] **Bước 3: Verify**

Run: `grep -n "Integrations & Field Mapping" .maika/workflows/task.md`
Expected: 2 dòng (bước 5 Pha 2 từ Task 4, và 5.a Pha 3)

- [ ] **Bước 4: Commit**

```bash
git add .maika/workflows/task.md
git commit -m "feat(workflow): bảng field mapping vào KNOWLEDGE_PACK + handoff node mapper"
```

---

## PHẦN B — Thin Orchestrator (Task 6–11)

### Task 6: worker_command trong execution-mode.yaml + prompt worker cho tier fresh-session

**Files:**
- Modify: `.maika/profiles/execution-mode.yaml`
- Modify: `.maika/tools/microloop-orchestrator/tiers/fresh_session.py`
- Test: `.maika/tools/microloop-orchestrator/tests/test_degradation.py` (thêm 1 test)

**Interfaces:**
- Produces: key `worker_command` (template có `{prompt}`), `worker_timeout_seconds` — Task 7 (`make_worker_runner`) và Task 9 (task.md) tiêu thụ. `tiers/fresh_session.dispatch(handoff_path, result_path) -> str` trả về worker prompt.

- [ ] **Bước 1: Viết test fail cho prompt mới của fresh_session**

Thêm vào cuối `.maika/tools/microloop-orchestrator/tests/test_degradation.py`:

```python
def test_fresh_session_dispatch_targets_executor_procedure():
    fn = get_dispatch("fresh-session")
    prompt = fn("X/TASK_HANDOFF.T1.md", "X/microloop/TASK_RESULT.T1.md")
    assert "procedures/executor.md" in prompt
    assert "X/TASK_HANDOFF.T1.md" in prompt
    assert "X/microloop/TASK_RESULT.T1.md" in prompt
    assert "OPEN A NEW SESSION" not in prompt
```

- [ ] **Bước 2: Chạy test, xác nhận fail**

Run: `python3 -m pytest .maika/tools/microloop-orchestrator/tests/test_degradation.py -v`
Expected: FAIL ở `test_fresh_session_dispatch_targets_executor_procedure` (assert "OPEN A NEW SESSION" not in prompt)

- [ ] **Bước 3: Viết lại tiers/fresh_session.py**

Ghi đè toàn bộ `.maika/tools/microloop-orchestrator/tiers/fresh_session.py`:

```python
"""fresh-session tier (Cursor/Antigravity): executor chạy trong worker context MỚI.

dispatch() trả về worker prompt. Parent (orchestrator) đưa prompt này vào
`worker_command` của profiles/execution-mode.yaml qua orchestrator.dispatch_worker()
— mỗi node một worker context sạch, KHÔNG cần user mở session thủ công."""


def dispatch(handoff_path, result_path):
    return (
        f"Read {{ platform.framework_root }}/procedures/executor.md and execute the handoff at "
        f"{handoff_path}. Write the outcome to {result_path} per the TASK_RESULT schema."
    )
```

(Ghi chú: `{{` trong f-string in ra `{` — giữ đúng pattern placeholder của file gốc, được Jinja render lúc scaffold.)

- [ ] **Bước 4: Cập nhật execution-mode.yaml (per-platform qua Jinja)**

Ghi đè toàn bộ `.maika/profiles/execution-mode.yaml`:

```yaml
# Declares the active micro-loop execution tier for THIS platform.
# The ONLY place platform-specifics live. Change one line to retarget.
#   subagent      → Claude Code (Agent tool, full isolation)
#   fresh-session → Cursor / Antigravity (worker context mới per task, tự động qua worker_command)
#   inline-reload → fallback single-session (LCD; always works)
{% if platform.name == "antigravity" %}
execution_mode: fresh-session
# Lệnh spawn worker dùng-một-lần; {prompt} được thay bằng prompt đã shell-quote.
worker_command: 'agy -p {prompt}'
{% elif platform.name == "codex" %}
execution_mode: fresh-session
worker_command: 'codex exec {prompt}'
{% elif platform.name == "claude-code" %}
execution_mode: subagent
worker_command: ''
{% else %}
execution_mode: inline-reload
worker_command: ''
{% endif %}
max_retries: 2
worker_timeout_seconds: 900
gate:
  # Path to the SP1a generated ruleset at the target project.
  checkstyle_xml: "{{ platform.framework_root }}/tools/rule-projector/generated/checkstyle.generated.xml"
  # Command template; {xml} and {files} are substituted. Empty in Maika repo (no Java).
  command: "checkstyle -c {xml} {files}"
```

- [ ] **Bước 5: Xác nhận profiles được Jinja render lúc scaffold**

Run: `grep -n "profiles" cli/platforms/base.py cli/maika.py | head -5`
Expected: có dòng cho thấy `profiles` nằm trong danh sách thư mục được scaffold/render (docstring base.py:140 đã liệt kê "rules, skills, workflows, procedures, tools, profiles"). Nếu KHÔNG có bằng chứng profiles đi qua Jinja render: dừng, báo lại — không đoán (khi đó chuyển sang cách đặt default trong `cli/platforms/*.py`).

- [ ] **Bước 6: Chạy test, xác nhận pass**

Run: `python3 -m pytest .maika/tools/microloop-orchestrator/tests/test_degradation.py -v`
Expected: PASS toàn bộ (test cũ + test mới)

- [ ] **Bước 7: Commit**

```bash
git add .maika/profiles/execution-mode.yaml .maika/tools/microloop-orchestrator/tiers/fresh_session.py .maika/tools/microloop-orchestrator/tests/test_degradation.py
git commit -m "feat(execution-mode): worker_command per-platform + fresh-session prompt hướng executor"
```

---

### Task 7: dispatch_worker + make_worker_runner trong orchestrator.py (TDD)

**Files:**
- Modify: `.maika/tools/microloop-orchestrator/orchestrator.py` (thêm 2 hàm + 2 import)
- Create: `.maika/tools/microloop-orchestrator/tests/test_dispatch_worker.py`

**Interfaces:**
- Consumes: `append_activity_event(active_dir, event, **fields)` (đã có trong orchestrator.py); `worker_command`/`worker_timeout_seconds`/`max_retries` từ Task 6.
- Produces:
  - `make_worker_runner(worker_command: str, timeout: int = 900) -> Callable[[str], tuple[int, str]]`
  - `dispatch_worker(prompt: str, runner, *, retries: int = 2, active_dir=None, task_id=None) -> dict` — trả `{"status": "done"|"blocked", "attempts": int, "output": str}`. Task 9 (task.md §3.5c/d) tham chiếu đúng chữ ký này.

- [ ] **Bước 1: Viết test fail**

Tạo `.maika/tools/microloop-orchestrator/tests/test_dispatch_worker.py`:

```python
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
import orchestrator  # noqa: E402


def test_dispatch_worker_done_on_first_success():
    result = orchestrator.dispatch_worker("do X", lambda p: (0, "ok"), retries=2)
    assert result["status"] == "done"
    assert result["attempts"] == 1


def test_dispatch_worker_retries_then_done():
    calls = []

    def runner(prompt):
        calls.append(prompt)
        return (1, "err") if len(calls) < 3 else (0, "ok")

    result = orchestrator.dispatch_worker("do X", runner, retries=2)
    assert result["status"] == "done"
    assert result["attempts"] == 3
    assert calls == ["do X"] * 3


def test_dispatch_worker_blocked_after_retry_budget():
    result = orchestrator.dispatch_worker("do X", lambda p: (1, "boom"), retries=1)
    assert result["status"] == "blocked"
    assert result["attempts"] == 2


def test_dispatch_worker_logs_activity_events(tmp_path):
    result = orchestrator.dispatch_worker(
        "do X", lambda p: (1, "boom"), retries=0,
        active_dir=tmp_path, task_id="T1",
    )
    assert result["status"] == "blocked"
    log = (tmp_path / "microloop" / "ACTIVITY_LOG.jsonl").read_text(encoding="utf-8")
    events = [json.loads(line) for line in log.splitlines()]
    assert [e["event"] for e in events] == ["subagent_started", "subagent_blocked"]
    assert events[0]["task_id"] == "T1"


def test_make_worker_runner_renders_prompt(tmp_path):
    marker = tmp_path / "prompt.txt"
    script = "import sys, pathlib; pathlib.Path(sys.argv[2]).write_text(sys.argv[1])"
    command = f'"{sys.executable}" -c "{script}" {{prompt}} "{marker}"'
    runner = orchestrator.make_worker_runner(command, timeout=60)
    exit_code, _ = runner("helloworker")
    assert exit_code == 0
    assert marker.read_text() == "helloworker"


def test_make_worker_runner_timeout_returns_124():
    command = f'"{sys.executable}" -c "import time; time.sleep(5)" {{prompt}}'
    runner = orchestrator.make_worker_runner(command, timeout=1)
    exit_code, output = runner("x")
    assert exit_code == 124
    assert "timeout" in output.lower()
```

- [ ] **Bước 2: Chạy test, xác nhận fail**

Run: `python3 -m pytest .maika/tools/microloop-orchestrator/tests/test_dispatch_worker.py -v`
Expected: FAIL — `AttributeError: module 'orchestrator' has no attribute 'dispatch_worker'`

- [ ] **Bước 3: Implement trong orchestrator.py**

Thêm import ở đầu file (sau `import json`):

```python
import shlex
import subprocess
```

Thêm 2 hàm ngay sau `make_gate_fn` (giữ pattern injectable-runner cùng chỗ):

```python
def make_worker_runner(worker_command, timeout=900):
    """Tạo runner spawn MỘT worker CLI dùng-một-lần (fresh-session tier).

    worker_command: template có placeholder {prompt} (vd 'agy -p {prompt}');
    prompt được shell-quote trước khi thay. Trả về (exit_code, output).
    Timeout → exit_code 124 (convention của timeout(1))."""
    def runner(prompt):
        command = worker_command.replace("{prompt}", shlex.quote(prompt))
        try:
            proc = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return 124, f"worker timeout sau {timeout}s"
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")

    return runner


def dispatch_worker(prompt, runner, *, retries=2, active_dir=None, task_id=None):
    """Chạy một worker context mới cho prompt; retry khi fail; log activity event.

    runner: (prompt) -> (exit_code, output) — inject được (make_worker_runner cho
    subprocess thật, stub cho unit test; cùng pattern với make_gate_fn).
    Khi truyền active_dir: tự emit subagent_started (mỗi attempt) và subagent_blocked
    (fail cuối). KHÔNG emit subagent_done — write_task_result của worker đã emit,
    tránh double-emission."""
    attempt = 0
    while True:
        if active_dir is not None:
            append_activity_event(
                active_dir, "subagent_started",
                actor="subagent", task_id=task_id, attempt=attempt,
            )
        exit_code, output = runner(prompt)
        if exit_code == 0:
            return {"status": "done", "attempts": attempt + 1, "output": output}
        attempt += 1
        if attempt > retries:
            if active_dir is not None:
                append_activity_event(
                    active_dir, "subagent_blocked",
                    actor="subagent", task_id=task_id, reason=str(output)[:500],
                )
            return {"status": "blocked", "attempts": attempt, "output": output}
```

- [ ] **Bước 4: Chạy test, xác nhận pass**

Run: `python3 -m pytest .maika/tools/microloop-orchestrator/tests/test_dispatch_worker.py -v`
Expected: PASS cả 6 test

- [ ] **Bước 5: Chạy toàn bộ test orchestrator (regression)**

Run: `python3 -m pytest .maika/tools/microloop-orchestrator/tests/ -v`
Expected: PASS toàn bộ

- [ ] **Bước 6: Commit**

```bash
git add .maika/tools/microloop-orchestrator/orchestrator.py .maika/tools/microloop-orchestrator/tests/test_dispatch_worker.py
git commit -m "feat(orchestrator): dispatch_worker + make_worker_runner — tự động hóa fresh-session tier"
```

---

### Task 8: SESSION-GATE trong write_gate.py (TDD)

**Files:**
- Modify: `.maika/hooks/write-gate/write_gate.py`
- Test: `.maika/hooks/write-gate/tests/test_write_gate.py` (thêm ~9 test, dùng helper `_write_valid_checkpoint` / `_write_valid_implementation_context` có sẵn trong file test)

**Interfaces:**
- Produces:
  - `_session_identity(payload: dict, proc_root=Path("/proc")) -> str | None`
  - `record_session_state(project_root, framework_root, session_identity) -> None` — ghi `knowledge/active/.session_state.json`
  - `check_session_gate(project_root, framework_root, session_identity) -> Decision`
  - `evaluate_write(..., session_identity=None)` — keyword mới, default None (test cũ không đổi)
- Consumes: `Decision`, `_warn`, `_section_text` (đã có); template `SESSION_OVERRIDE.md` (Task 9 tạo — gate chỉ cần file tồn tại đúng format, không cần template trước).

- [ ] **Bước 1: Viết test fail**

Thêm vào cuối `.maika/hooks/write-gate/tests/test_write_gate.py`:

```python
# ---------- SESSION-GATE (context-overflow safety net) ----------


def _setup_valid_app_context(tmp_path, target="src/App.java"):
    active = tmp_path / ".maika" / "knowledge" / "active"
    _write_valid_checkpoint(active)
    (active / "AGENT_TRANSPARENCY.md").write_text(
        "Pha 1 DONE\nPha 2 DONE\n", encoding="utf-8"
    )
    _write_valid_implementation_context(active, target)
    return active


def _write_session_state(active, identity, phase="phase-2-done"):
    (active / ".session_state.json").write_text(
        json.dumps({"phases": {phase: {"session_identity": identity, "ts": "t"}}}),
        encoding="utf-8",
    )


def test_session_gate_blocks_same_session_code_write(tmp_path):
    active = _setup_valid_app_context(tmp_path)
    _write_session_state(active, "sid:abc")
    result = wg.evaluate_write(
        tmp_path, Path("src/App.java"), framework_root=".maika",
        session_identity="sid:abc",
    )
    assert result.ok is False
    assert "[SESSION-GATE]" in result.reason


def test_session_gate_allows_new_session(tmp_path):
    active = _setup_valid_app_context(tmp_path)
    _write_session_state(active, "sid:abc")
    result = wg.evaluate_write(
        tmp_path, Path("src/App.java"), framework_root=".maika",
        session_identity="sid:xyz",
    )
    assert result.ok is True


def test_session_gate_degrades_without_identity(tmp_path):
    active = _setup_valid_app_context(tmp_path)
    _write_session_state(active, "sid:abc")
    result = wg.evaluate_write(
        tmp_path, Path("src/App.java"), framework_root=".maika",
        session_identity=None,
    )
    assert result.ok is True


def test_session_override_allows_and_logs_violation(tmp_path):
    active = _setup_valid_app_context(tmp_path)
    _write_session_state(active, "sid:abc")
    (active / "SESSION_OVERRIDE.md").write_text(
        "ticket: ABC-1\nuser-confirm: đồng ý tiếp tục cùng session\nreason: hotfix 1 dòng\n",
        encoding="utf-8",
    )
    result = wg.evaluate_write(
        tmp_path, Path("src/App.java"), framework_root=".maika",
        session_identity="sid:abc",
    )
    assert result.ok is True
    transparency = (active / "AGENT_TRANSPARENCY.md").read_text(encoding="utf-8")
    assert "[VIOLATION][SESSION-GATE]" in transparency


def test_session_override_incomplete_still_blocks(tmp_path):
    active = _setup_valid_app_context(tmp_path)
    _write_session_state(active, "sid:abc")
    (active / "SESSION_OVERRIDE.md").write_text("reason: quên format\n", encoding="utf-8")
    result = wg.evaluate_write(
        tmp_path, Path("src/App.java"), framework_root=".maika",
        session_identity="sid:abc",
    )
    assert result.ok is False


def test_record_session_state_first_writer_wins(tmp_path):
    active = tmp_path / ".maika" / "knowledge" / "active"
    active.mkdir(parents=True)
    (active / "AGENT_TRANSPARENCY.md").write_text(
        "## Phase State\nphase_state: phase-1-done\n", encoding="utf-8"
    )
    wg.record_session_state(tmp_path, ".maika", "sid:one")
    wg.record_session_state(tmp_path, ".maika", "sid:two")
    state = json.loads((active / ".session_state.json").read_text(encoding="utf-8"))
    assert state["phases"]["phase-1-done"]["session_identity"] == "sid:one"


def test_record_session_state_ignores_other_phase(tmp_path):
    active = tmp_path / ".maika" / "knowledge" / "active"
    active.mkdir(parents=True)
    (active / "AGENT_TRANSPARENCY.md").write_text(
        "phase_state: applying\n", encoding="utf-8"
    )
    wg.record_session_state(tmp_path, ".maika", "sid:one")
    assert not (active / ".session_state.json").exists()


def _write_proc_stat(proc_root, pid, comm, ppid, starttime):
    d = proc_root / str(pid)
    d.mkdir(parents=True)
    tokens = ["S", str(ppid)] + ["0"] * 17 + [str(starttime)]
    (d / "stat").write_text(f"{pid} ({comm}) " + " ".join(tokens), encoding="utf-8")


def test_process_identity_skips_shell_ancestors(tmp_path, monkeypatch):
    proc = tmp_path / "proc"
    _write_proc_stat(proc, 100, "sh", 50, 8888)     # wrapper shell của hook
    _write_proc_stat(proc, 50, "agy", 1, 4242)      # process agent runtime
    monkeypatch.setattr(wg.os, "getppid", lambda: 100)
    assert wg._process_identity(proc_root=proc) == "pid:50:4242"


def test_process_identity_none_without_proc(tmp_path, monkeypatch):
    monkeypatch.setattr(wg.os, "getppid", lambda: 100)
    assert wg._process_identity(proc_root=tmp_path / "no-proc") is None


def test_session_identity_prefers_payload_id(tmp_path):
    assert wg._session_identity({"session_id": "s-9"}, proc_root=tmp_path) == "sid:s-9"
```

- [ ] **Bước 2: Chạy test, xác nhận fail**

Run: `python3 -m pytest .maika/hooks/write-gate/tests/test_write_gate.py -v -k "session or process_identity"`
Expected: FAIL — `AttributeError` (chưa có `record_session_state`, `_process_identity`, `_session_identity`) và TypeError cho keyword `session_identity`

- [ ] **Bước 3: Implement trong write_gate.py**

(a) Thêm import ở đầu file (sau `import json`):

```python
import os
```

và (sau `from dataclasses import dataclass`):

```python
from datetime import datetime, timezone
```

(b) Thêm constants sau `_SHELL_TOOLS = {...}`:

```python
_SESSION_PHASES = ("phase-1-done", "phase-2-done")
_PHASE_STATE_RE = re.compile(r"phase_state:\s*([A-Za-z0-9-]+)")
_SHELL_COMMS = {"sh", "bash", "dash", "zsh", "fish", "python", "python3", "py"}
_SESSION_GATE_MESSAGE = (
    "[SESSION-GATE] Pha 1/2 đã chạy trong session này — context có nguy cơ đã tràn/compact. "
    "Dispatch node qua worker (procedures/executor.md + TASK_HANDOFF, xem "
    "profiles/execution-mode.yaml) hoặc mở session mới rồi chạy /task apply <ticket>. "
    "User có thể override tường minh: ghi knowledge/active/SESSION_OVERRIDE.md theo template "
    "(sẽ được log vào Violation Log)."
)
```

(c) Thêm các hàm sau `_warn` (trước `extract_target_paths`):

```python
def _proc_stat(proc_root: Path, pid: int):
    """Parse /proc/<pid>/stat → (comm, ppid, starttime). None nếu không đọc được."""
    try:
        stat = (proc_root / str(pid) / "stat").read_text(encoding="utf-8")
        comm = stat.split("(", 1)[1].rsplit(")", 1)[0]
        rest = stat.rsplit(")", 1)[1].split()
        return comm, int(rest[1]), rest[19]
    except (OSError, IndexError, ValueError):
        return None


def _process_identity(proc_root: Path = Path("/proc")):
    """Tổ tiên đầu tiên không phải shell/python = process của agent runtime.

    Ổn định qua compaction (cùng process), đổi khi restart session (process mới).
    Trả về "pid:<pid>:<starttime>" hoặc None (vd Windows không có /proc → degrade)."""
    pid = os.getppid()
    for _ in range(16):
        info = _proc_stat(proc_root, pid)
        if info is None:
            return None
        comm, ppid, starttime = info
        if comm.lower() not in _SHELL_COMMS:
            return f"pid:{pid}:{starttime}"
        if ppid <= 1:
            return None
        pid = ppid
    return None


def _session_identity(payload: dict, proc_root: Path = Path("/proc")):
    """Định danh session hiện tại: ưu tiên id từ hook payload; fallback POSIX
    process-identity; không có → None (SESSION-GATE degrade về cho-qua)."""
    sid = (
        payload.get("session_id")
        or payload.get("sessionId")
        or payload.get("conversation_id")
        or payload.get("conversationId")
    )
    if sid:
        return f"sid:{sid}"
    return _process_identity(proc_root=proc_root)


def _session_state_path(project_root: Path, framework_root: str) -> Path:
    return project_root / framework_root / "knowledge" / "active" / ".session_state.json"


def record_session_state(project_root: Path, framework_root: str, session_identity) -> None:
    """Ghi session identity tại LẦN ĐẦU quan sát phase_state ∈ _SESSION_PHASES.

    Sidecar nằm trong knowledge/active/ nên được knowledge-curator reset cùng task —
    state cũ không bao giờ chặn nhầm task sau."""
    if not session_identity:
        return
    transparency = project_root / framework_root / "knowledge" / "active" / "AGENT_TRANSPARENCY.md"
    if not transparency.exists():
        return
    try:
        match = _PHASE_STATE_RE.search(transparency.read_text(encoding="utf-8"))
    except OSError:
        return
    if not match:
        return
    phase = match.group(1).lower()
    if phase not in _SESSION_PHASES:
        return
    state_path = _session_state_path(project_root, framework_root)
    state = {}
    if state_path.exists():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8")) or {}
        except (OSError, json.JSONDecodeError):
            state = {}
    phases = state.setdefault("phases", {})
    if phase in phases:
        return
    phases[phase] = {
        "session_identity": session_identity,
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    try:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(
            json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError:
        pass


def _log_session_violation(project_root: Path, framework_root: str, session_identity: str) -> None:
    transparency = project_root / framework_root / "knowledge" / "active" / "AGENT_TRANSPARENCY.md"
    marker = f"[VIOLATION][SESSION-GATE] override dùng cho session {session_identity}"
    try:
        text = transparency.read_text(encoding="utf-8") if transparency.exists() else ""
        if marker in text:
            return
        stamp = datetime.now(timezone.utc).isoformat()
        with transparency.open("a", encoding="utf-8") as f:
            f.write(f"\n{marker} lúc {stamp}\n")
    except OSError:
        pass


def check_session_gate(project_root: Path, framework_root: str, session_identity) -> Decision:
    """Lưới an toàn context-overflow: chặn code write inline trong session đã
    hoàn thành Pha 1/2. Không có identity/state → cho qua (degrade, không tệ hơn hiện trạng)."""
    if not session_identity:
        return Decision(True)
    state_path = _session_state_path(project_root, framework_root)
    if not state_path.exists():
        return Decision(True)
    try:
        state = json.loads(state_path.read_text(encoding="utf-8")) or {}
    except (OSError, json.JSONDecodeError):
        return Decision(True)
    phases = state.get("phases", {})
    same_session = any(
        phases.get(phase, {}).get("session_identity") == session_identity
        for phase in _SESSION_PHASES
    )
    if not same_session:
        return Decision(True)
    override = project_root / framework_root / "knowledge" / "active" / "SESSION_OVERRIDE.md"
    if override.exists():
        try:
            body = override.read_text(encoding="utf-8")
        except OSError:
            body = ""
        if re.search(r"^ticket:\s*\S+", body, re.MULTILINE) and re.search(
            r"^user-confirm:\s*\S+", body, re.MULTILINE
        ):
            _log_session_violation(project_root, framework_root, session_identity)
            _warn("write-gate: [SESSION-GATE] override active — violation đã log vào AGENT_TRANSPARENCY.")
            return Decision(True)
        return Decision(False, "SESSION_OVERRIDE.md thiếu ticket:/user-confirm: — " + _SESSION_GATE_MESSAGE)
    return Decision(False, _SESSION_GATE_MESSAGE)
```

(d) Sửa `evaluate_write` — thêm keyword và chèn check sau documentation exemption:

`old_string`:

```python
def evaluate_write(project_root: Path, target_path: Path, framework_root: str = ".maika") -> Decision:
    if not target_path.as_posix():
        return Decision(False, "Unable to identify target path for write-gate payload")
    policy_path = _policy_path(project_root, target_path)
    if _is_framework_artifact(policy_path, framework_root):
        return Decision(True)
    if _is_documentation(policy_path):
        return Decision(True)
```

`new_string`:

```python
def evaluate_write(project_root: Path, target_path: Path, framework_root: str = ".maika",
                   session_identity=None) -> Decision:
    if not target_path.as_posix():
        return Decision(False, "Unable to identify target path for write-gate payload")
    policy_path = _policy_path(project_root, target_path)
    if _is_framework_artifact(policy_path, framework_root):
        return Decision(True)
    if _is_documentation(policy_path):
        return Decision(True)

    session_result = check_session_gate(project_root, framework_root, session_identity)
    if not session_result.ok:
        return session_result
```

(e) Sửa `main()` — tính identity, ghi state, truyền vào cả 2 call site của `evaluate_write`:

`old_string`:

```python
    payload = json.loads(raw or "{}")
    cwd = Path.cwd()
    root = _project_root_from_cwd(cwd)
```

`new_string`:

```python
    payload = json.loads(raw or "{}")
    cwd = Path.cwd()
    root = _project_root_from_cwd(cwd)
    session_identity = _session_identity(payload)
    record_session_state(root, args.framework_root, session_identity)
```

Rồi thay CẢ HAI chỗ (nhánh shell-tool và nhánh direct-tool):

`old_string` (xuất hiện 2 lần — dùng `replace_all: true`):

```python
                evaluate_write(root, target, framework_root=args.framework_root)
```

`new_string`:

```python
                evaluate_write(root, target, framework_root=args.framework_root,
                               session_identity=session_identity)
```

- [ ] **Bước 4: Chạy test session mới, xác nhận pass**

Run: `python3 -m pytest .maika/hooks/write-gate/tests/test_write_gate.py -v -k "session or process_identity"`
Expected: PASS cả 10 test mới

- [ ] **Bước 5: Chạy toàn bộ test write-gate (regression — test cũ không sửa)**

Run: `python3 -m pytest .maika/hooks/write-gate/tests/test_write_gate.py -v`
Expected: PASS toàn bộ

- [ ] **Bước 6: Commit**

```bash
git add .maika/hooks/write-gate/write_gate.py .maika/hooks/write-gate/tests/test_write_gate.py
git commit -m "feat(write-gate): SESSION-GATE — chặn code write inline trong session đã chạy Pha 1/2"
```

---

### Task 9: Template SESSION_OVERRIDE + task.md dispatch/session-boundary

**Files:**
- Create: `.maika/knowledge/templates/SESSION_OVERRIDE.tpl.md`
- Modify: `.maika/workflows/task.md` (mục 0 bootstrap — thêm 1.0 dispatch mode; §1.4 bước 10; §2 bước 10; §3 bước 5.c; §3 bước 9)
- Modify (nếu áp dụng): `.maika/skills/knowledge-curator/SKILL.md` — bổ sung 2 file mới vào enumeration archive/reset (chỉ khi SKILL enumerate từng file)

**Interfaces:**
- Consumes: `dispatch_worker` / `make_worker_runner` (Task 7), `worker_command` / `worker_timeout_seconds` / `max_retries` (Task 6), prompt tier fresh-session (Task 6), format override (Task 8: cần dòng `ticket:` và `user-confirm:`).

- [ ] **Bước 1: Tạo template SESSION_OVERRIDE**

Tạo `.maika/knowledge/templates/SESSION_OVERRIDE.tpl.md`:

```markdown
# SESSION_OVERRIDE — Tiếp tục code trong session đã chạy Pha 1/2

<!-- CHỈ ghi file này khi USER chấp thuận tường minh việc tiếp tục cùng session. -->
<!-- write-gate sẽ cho qua nhưng log violation vào AGENT_TRANSPARENCY (audit trail). -->
<!-- File nằm trong knowledge/active/ → được knowledge-curator archive + reset cùng task. -->

ticket: <!-- ticket-id đang active -->
user-confirm: <!-- nguyên văn câu user chấp thuận, vd "đồng ý tiếp tục cùng session" -->
reason: <!-- vì sao không dispatch worker / không mở session mới (vd hotfix 1 dòng) -->
```

- [ ] **Bước 2: Thêm mục "0b. Dispatch mode" vào task.md (sau mục 0 Bootstrap, trước §1)**

Edit `.maika/workflows/task.md`:

`old_string`:

```markdown
## 1. `/task <ý-tưởng-hoặc-link>` — Pha 1: Hiểu vấn đề
```

`new_string`:

```markdown
## 0b. Dispatch mode — Orchestrator mỏng (R-Flow-5)

Đọc `{{ platform.framework_root }}/profiles/execution-mode.yaml` một lần khi bootstrap:

- `execution_mode` = `subagent` hoặc `fresh-session` → các skill đọc-nặng của Pha 1
  (`spec-extract`, `codebase-explorer`, `db-explorer`) PHẢI chạy trong worker context:
  - `subagent`: dispatch qua Agent tool với prompt:
    _"Đọc `{{ platform.framework_root }}/skills/<skill>/SKILL.md`, thực thi với input `<URL/ticket>`,
    ghi output vào file knowledge mà skill chỉ định."_
  - `fresh-session`: gọi helper `dispatch_worker(prompt, make_worker_runner(worker_command,
    worker_timeout_seconds), retries=max_retries)` trong
    `{{ platform.framework_root }}/tools/microloop-orchestrator/orchestrator.py` với cùng prompt.
  - Parent KHÔNG đọc tài liệu nguồn / KHÔNG quét code trực tiếp; chỉ đọc lại
    `REQUIREMENT.md` / `EXPLORE_CONTEXT.md` sau khi worker xong (R-Flow-5).
  - Worker `blocked` sau max_retries → fallback chạy inline + ghi WARN vào AGENT_TRANSPARENCY:
    `[DISPATCH-FALLBACK] <skill> chạy inline — worker fail: <lý do>`.
- `execution_mode` = `inline-reload` → chạy inline như cũ (LCD).
- Hỏi–đáp với user LUÔN ở parent (tương tác), dựa trên file knowledge đã ghi.

---

## 1. `/task <ý-tưởng-hoặc-link>` — Pha 1: Hiểu vấn đề
```

- [ ] **Bước 3: Viết lại SESSION-BOUNDARY Pha 1 (§1.4 bước 10)**

Edit `.maika/workflows/task.md`:

`old_string`:

```markdown
10. **[SESSION-BOUNDARY — Pha 1]** Sau khi POST-PHASE SELF-CHECK pass:
    - Thông báo user:
      > "Pha 1 hoàn thành. **Vui lòng mở session mới** để chạy `/task spec`.
      > Context đã lưu đầy đủ vào `{{ platform.framework_root }}/knowledge/active/`.
      > Session mới sẽ Bootstrap fresh — rule/DNA ở top-of-mind, tránh Context Dilution."
    - Nếu user tiếp tục trong cùng session (gọi `/task spec` ngay):
      - Ghi WARN vào AGENT_TRANSPARENCY: `[SESSION-BOUNDARY] Tiếp tục cùng session sau Pha 1 — rủi ro Context Dilution.`
      - **Không block** — vẫn cho phép tiếp tục, nhưng ghi vào Violation Log.
```

`new_string`:

```markdown
10. **[SESSION-BOUNDARY — Pha 1]** Sau khi POST-PHASE SELF-CHECK pass:
    - **Đường chính** (Pha 1 đã dispatch qua worker theo mục 0b): session này vẫn mỏng —
      có thể tiếp tục `/task spec` trong CÙNG session, không cần mở mới.
    - **Nếu Pha 1 đã chạy inline** (inline-reload hoặc dispatch fallback):
      > "Pha 1 hoàn thành. **Vui lòng mở session mới** để chạy `/task spec`.
      > Context đã lưu đầy đủ vào `{{ platform.framework_root }}/knowledge/active/`.
      > Session mới sẽ Bootstrap fresh — rule/DNA ở top-of-mind, tránh Context Dilution."
    - **Escalation theo TOKEN_LOG**: nếu estimate Pha 1 > 50,000 tokens → lời nhắc trên trở thành
      **BẮT BUỘC**: "Context đã vượt ngưỡng an toàn, khả năng cao đã compact — rules/DNA
      không còn đảm bảo trong context. Mở session mới trước khi tiếp tục."
    - Nếu user vẫn tiếp tục cùng session sau cảnh báo:
      - Ghi WARN vào AGENT_TRANSPARENCY: `[SESSION-BOUNDARY] Tiếp tục cùng session sau Pha 1 — rủi ro Context Dilution.`
      - **Không block tại đây** — nhưng lưu ý: write-gate SESSION-GATE sẽ chặn code write inline
        ở Pha 3 trong session này (override: `SESSION_OVERRIDE.md` theo template, có log violation).
```

- [ ] **Bước 4: Viết lại SESSION-BOUNDARY Pha 2 (§2 bước 10)**

Edit `.maika/workflows/task.md`:

`old_string`:

```markdown
10. **[SESSION-BOUNDARY — Pha 2]** Sau khi POST-PHASE SELF-CHECK pass:
    - Thông báo user:
      > "Pha 2 hoàn thành. **Vui lòng mở session mới** để chạy `/task apply`.
      > Spec đã lưu tại `openspec/changes/<change-id>/`.
      > Session mới sẽ Bootstrap fresh — DNA/conventions ở top-of-mind khi code."
    - Nếu user tiếp tục trong cùng session:
      - Ghi WARN vào AGENT_TRANSPARENCY: `[SESSION-BOUNDARY] Tiếp tục cùng session sau Pha 2 — rủi ro Context Dilution khi code.`
      - **Chỉ được code khi implementation preflight pass** — micro-loop Pha 3 (SP1b)
        phải ghi `TASK_HANDOFF.<node>.md` chứa `## Applicable DNA/Conventions`,
        `## Evidence`, và `## Allowed Files`; `write-gate` sẽ block code write nếu
        handoff/context thiếu, stale, hoặc không match target file.
```

`new_string`:

```markdown
10. **[SESSION-BOUNDARY — Pha 2]** Sau khi POST-PHASE SELF-CHECK pass:
    - **Đường chính** (execution_mode = subagent/fresh-session): tiếp tục `/task apply` trong
      CÙNG session — mỗi node code chạy trong worker context mới (§3 bước 5.c), parent chỉ
      điều phối nên không cần mở session mới.
    - **Nếu execution_mode = inline-reload** (code sẽ chạy inline trong session này):
      > "Pha 2 hoàn thành. **Vui lòng mở session mới** để chạy `/task apply`.
      > Spec đã lưu tại `openspec/changes/<change-id>/`.
      > Session mới sẽ Bootstrap fresh — DNA/conventions ở top-of-mind khi code."
    - **Escalation theo TOKEN_LOG**: nếu tổng estimate Pha 1+2 > 50,000 tokens → lời nhắc trên
      trở thành **BẮT BUỘC** (context có nguy cơ đã compact).
    - Nếu user vẫn tiếp tục cùng session:
      - Ghi WARN vào AGENT_TRANSPARENCY: `[SESSION-BOUNDARY] Tiếp tục cùng session sau Pha 2 — rủi ro Context Dilution khi code.`
      - **Chỉ được code khi implementation preflight pass** — micro-loop Pha 3 (SP1b)
        phải ghi `TASK_HANDOFF.<node>.md` chứa `## Applicable DNA/Conventions`,
        `## Evidence`, và `## Allowed Files`; `write-gate` sẽ block code write nếu
        handoff/context thiếu, stale, hoặc không match target file.
      - Ngoài ra write-gate SESSION-GATE chặn code write inline trong session đã hoàn thành
        Pha 1/2 (kể cả khi handoff hợp lệ) — đường đúng là dispatch worker hoặc session mới;
        override tường minh qua `SESSION_OVERRIDE.md`.
```

- [ ] **Bước 5: Tự động dispatch executor trong §3 bước 5.c**

Edit `.maika/workflows/task.md`:

`old_string`:

```markdown
      - Dispatch executor by `{{ platform.framework_root }}/profiles/execution-mode.yaml`.
```

`new_string`:

```markdown
      - Dispatch executor theo `{{ platform.framework_root }}/profiles/execution-mode.yaml`:
        - `subagent`: Agent tool với prompt từ `tiers/subagent.py`.
        - `fresh-session`: gọi `dispatch_worker(prompt, make_worker_runner(worker_command, worker_timeout_seconds), retries=max_retries, active_dir=<knowledge/active>, task_id=<node-id>)`
          (orchestrator.py) với prompt từ `tiers/fresh_session.py` — worker context MỚI per node,
          KHÔNG yêu cầu user mở session; `dispatch_worker` tự emit `subagent_started`/`subagent_blocked`
          (không emit thủ công 2 event này cho node đó).
        - `inline-reload`: prompt từ `tiers/inline_reload.py`, chạy trong session hiện tại (LCD).
```

- [ ] **Bước 6: Ghi chú fresh-session ở SESSION-BOUNDARY Pha 3 (§3 bước 9)**

Edit `.maika/workflows/task.md`:

`old_string`:

```markdown
    - Đây là kết thúc tự nhiên của task — session mới là best practice, không chỉ là gợi ý.
```

`new_string`:

```markdown
    - Đây là kết thúc tự nhiên của task — session mới là best practice, không chỉ là gợi ý.
    - Ngoại lệ: nếu toàn bộ task chạy theo đường dispatch worker (mục 0b + §3 bước 5.c),
      parent vẫn mỏng — có thể nhận task mới trong cùng session sau khi archive xong.
```

- [ ] **Bước 7: Kiểm tra knowledge-curator enumeration**

Run: `grep -n "reset_active_context\|archive_active_context" .maika/skills/knowledge-curator/SKILL.md | head -10`

Đọc các section đó: nếu SKILL **enumerate từng file** của active/ khi archive/reset → thêm `SESSION_OVERRIDE.md` và `.session_state.json` vào danh sách. Nếu SKILL thao tác cả thư mục active/ (không enumerate) → không sửa gì (2 file tự được dọn theo thư mục).

- [ ] **Bước 8: Verify**

Run: `grep -c "SESSION-GATE\|dispatch_worker\|0b. Dispatch mode" .maika/workflows/task.md`
Expected: ≥ 5

- [ ] **Bước 9: Commit**

```bash
git add .maika/knowledge/templates/SESSION_OVERRIDE.tpl.md .maika/workflows/task.md .maika/skills/knowledge-curator/SKILL.md
git commit -m "feat(workflow): dispatch worker tự động Pha 1/Pha 3 + session-boundary theo execution-mode"
```

(Nếu knowledge-curator không cần sửa thì bỏ file đó khỏi `git add`.)

---

### Task 10: R-Flow-5 (orchestrator mỏng) + R-Flow-6 (reflex routing) trong rules-flow.md

**Files:**
- Modify: `.maika/rules/rules-flow.md` (thêm 2 rule sau R-Flow-4, trước section "## 6. Spec & Apply Rules")

**Interfaces:**
- Consumes: tên rule R-Flow-5 được task.md mục 0b tham chiếu (Task 9 đã ghi "R-Flow-5" — hai task phải khớp tên).

- [ ] **Bước 1: Thêm 2 rule**

Edit `.maika/rules/rules-flow.md`:

`old_string`:

```markdown
- Sau hardstop, không tiếp tục scan cùng một dữ liệu/cấu hình trong phiên hiện tại.


---

---

## 6. Spec & Apply Rules
```

`new_string`:

```markdown
- Sau hardstop, không tiếp tục scan cùng một dữ liệu/cấu hình trong phiên hiện tại.

### [CRITICAL] R-Flow-5: Orchestrator mỏng — việc nặng chạy trong worker

- Context của agent cha (orchestrator) CHỈ giữ: phase state, tóm tắt ngắn, đường dẫn file.
- Nội dung thô khối lượng lớn — trang tài liệu (Confluence/wiki/PRD), quét code diện rộng,
  log dài — phải được tiêu thụ trong worker context (subagent / worker_command theo
  `{{ platform.framework_root }}/profiles/execution-mode.yaml`) và persist kết quả ra file knowledge.
- Parent chỉ đọc lại file kết quả (REQUIREMENT, EXPLORE_CONTEXT, TASK_RESULT…), không đọc nguồn thô.
- Lý do: context tràn/compact làm mất rules/DNA đã đọc lúc bootstrap → agent code cảm tính
  (observed failure 2026-07-03, downstream Antigravity).

### [CRITICAL] R-Flow-6: Freeform "viết spec/code" phải route về /task

- Sau khi Pha 1/2 đã chạy, mọi yêu cầu freeform kiểu "viết spec đi", "code đi", "implement đi"
  PHẢI được route về `/task spec` / `/task apply` (nơi dispatch worker theo execution-mode).
- KHÔNG code inline từ trí nhớ hội thoại — write-gate SESSION-GATE chặn code write inline
  trong session đã hoàn thành Pha 1/2 (override tường minh: `SESSION_OVERRIDE.md`, có log violation).


---

---

## 6. Spec & Apply Rules
```

- [ ] **Bước 2: Verify**

Run: `grep -c "R-Flow-5\|R-Flow-6" .maika/rules/rules-flow.md`
Expected: `2` (2 heading; nếu grep đếm dòng thì ≥ 2)

- [ ] **Bước 3: Commit**

```bash
git add .maika/rules/rules-flow.md
git commit -m "feat(rules): R-Flow-5 orchestrator mỏng + R-Flow-6 reflex routing freeform"
```

---

### Task 11: Regression toàn bộ + tổng kết

**Files:**
- Không sửa file mới (chỉ chạy verification; sửa nếu regression lộ ra)

- [ ] **Bước 1: Chạy toàn bộ pytest của repo**

Run: `python3 -m pytest .maika/ cli/ -q`
Expected: PASS toàn bộ, 0 failed (số test tăng so với baseline: +1 degradation, +6 dispatch_worker, +10 write-gate)

- [ ] **Bước 2: Kiểm tra placeholder/tiếng Việt trong file đã sửa**

Run: `git diff main --stat` (hoặc `git log --oneline` đếm các commit của plan) và `grep -rn "TODO\|TBD" .maika/knowledge/templates/SESSION_OVERRIDE.tpl.md .maika/rules/rules-flow.md`
Expected: không có TODO/TBD mới ngoài comment template chủ đích (`<!-- ... -->`).

- [ ] **Bước 3: Commit cuối (nếu có sửa regression) + báo cáo**

Tóm tắt cho user: danh sách commit, số test pass, các điểm cần xác minh khi rollout downstream (spec §"Điểm cần xác minh khi implement": flags `agy -p`, session id trong payload Antigravity, `codex exec`).

---

## Ghi chú deviation so với spec

1. **Override binding với ticket active**: spec yêu cầu "ticket khớp task đang active"; plan hiện thực mức v1 — override phải có dòng `ticket:` + `user-confirm:` không rỗng; binding theo vòng đời (file nằm trong `knowledge/active/`, được knowledge-curator reset cùng task) thay vì parse ticket-id từ AGENT_TRANSPARENCY (fragile). Ghi rõ trong template.
2. **Event log của dispatch_worker**: chỉ emit `subagent_started`/`subagent_blocked`; `subagent_done`/`result_written` do worker emit qua `write_task_result` — tránh double-emission (spec B3 nói "append các event có sẵn", plan làm chính xác hóa phân công).
