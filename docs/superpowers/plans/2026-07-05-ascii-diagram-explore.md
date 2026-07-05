# ASCII Diagram Explore Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bổ sung guidance bắt buộc để `spec-extract` và `openspec-explore` vẽ/capture ASCII diagram khi có flow, state, integration, callback, job, hoặc data path.

**Architecture:** Thay đổi nằm ở Markdown skill guidance, reference docs, knowledge templates, và regression tests đọc trực tiếp các file đó. Không đổi runtime code; tests bảo vệ các anchor/guidance mà downstream phase cần đọc.

**Tech Stack:** Python `pytest` cho regression tests; Markdown skill/reference/template trong `.maika`; shell command chạy qua `rtk`.

## Global Constraints

- Không thêm Mermaid, DOT, image generation, hoặc diagram renderer.
- Không bắt diagram cho task đơn giản không có sequence, state, branch, hoặc integration boundary đáng kể.
- Không đổi runtime code hoặc hành vi command execution.
- Không dùng diagram để thay thế acceptance criteria, source link, field mapping, hoặc architecture note.
- Diagram phải là plain-text ASCII, đọc tốt trong Markdown, code review, terminal output, và long-context handoff.
- Explore mode vẫn non-implementation; cập nhật artifact chỉ là capture suy nghĩ.

---

## File Structure

- Create: `cli/tests/test_ascii_diagram_guidance.py`  
  Regression tests đọc Markdown guidance/template và assert các anchor bắt buộc tồn tại.
- Modify: `.maika/skills/spec-extract/SKILL.md`  
  Thêm rule diagram capture bắt buộc ở core skill guidance.
- Modify: `.maika/skills/spec-extract/references/quy-trinh-chi-tiet.md`  
  Thêm bước chi tiết vẽ/capture ASCII diagram sau bước thống kê integration/field mapping.
- Modify: `.maika/skills/spec-extract/references/output-schema.md`  
  Thêm section output `#### ASCII Flow / State Diagram`.
- Modify: `.maika/knowledge/templates/REQUIREMENT.tpl.md`  
  Thêm anchor `## Flow / State Diagram` gần As-is/To-be để `REQUIREMENT.md` giữ diagram.
- Modify: `.maika/skills/openspec-explore/SKILL.md`  
  Làm rõ stance upstream OpenSpec và capture rule riêng cho Maika.
- Modify: `.maika/skills/openspec-explore/references/explore-patterns.md`  
  Bổ sung pattern diagram/capture cho explore.
- Modify: `.maika/knowledge/templates/EXPLORE_CONTEXT.tpl.md`  
  Thay placeholder mềm bằng guidance bắt buộc vẽ ASCII diagram khi có flow/state/data path.

---

### Task 1: Cập nhật `spec-extract` và `REQUIREMENT` template bằng regression test

**Files:**
- Create: `cli/tests/test_ascii_diagram_guidance.py`
- Modify: `.maika/skills/spec-extract/SKILL.md`
- Modify: `.maika/skills/spec-extract/references/quy-trinh-chi-tiet.md`
- Modify: `.maika/skills/spec-extract/references/output-schema.md`
- Modify: `.maika/knowledge/templates/REQUIREMENT.tpl.md`

**Interfaces:**
- Consumes: Không phụ thuộc task trước.
- Produces: Test function `test_spec_extract_requires_ascii_diagram_capture()`; `spec-extract` output guidance có section `#### ASCII Flow / State Diagram`; `REQUIREMENT.tpl.md` có anchor `## Flow / State Diagram`.

- [ ] **Step 1: Viết failing test cho `spec-extract`**

Create `cli/tests/test_ascii_diagram_guidance.py` với nội dung:

```python
"""Regression tests for ASCII diagram guidance in Maika skills/templates."""

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent.parent


def read_text(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def test_spec_extract_requires_ascii_diagram_capture():
    skill = read_text(".maika/skills/spec-extract/SKILL.md")
    detail = read_text(".maika/skills/spec-extract/references/quy-trinh-chi-tiet.md")
    schema = read_text(".maika/skills/spec-extract/references/output-schema.md")
    requirement_template = read_text(".maika/knowledge/templates/REQUIREMENT.tpl.md")

    assert "#### ASCII Flow / State Diagram" in skill
    assert "flow, state, integration, callback, job, hoặc data path" in skill
    assert "Bước 5c — Vẽ ASCII Flow / State Diagram" in detail
    assert "Diagram phải đánh dấu `unknown`, `assumption`, hoặc `needs BA/PO confirmation`" in detail
    assert "#### ASCII Flow / State Diagram" in schema
    assert "## Flow / State Diagram" in requirement_template
    assert "Bắt buộc khi task có flow, state, integration, callback, job, hoặc data path" in requirement_template
```

- [ ] **Step 2: Chạy test để xác nhận fail**

Run:

```bash
rtk pytest cli/tests/test_ascii_diagram_guidance.py::test_spec_extract_requires_ascii_diagram_capture -q
```

Expected: FAIL với assertion thiếu `#### ASCII Flow / State Diagram` trong `spec-extract/SKILL.md`.

- [ ] **Step 3: Sửa `.maika/skills/spec-extract/SKILL.md`**

Insert block này sau danh sách skeleton tối thiểu trong section `### Output`:

```md
#### ASCII Flow / State Diagram

Bắt buộc thêm block `#### ASCII Flow / State Diagram` vào phần yêu cầu trích từ tài liệu khi tài liệu có flow, state, integration, callback, job, hoặc data path.

Áp dụng khi gặp:
- Luồng chính có nhiều bước.
- Luồng lỗi, retry, fallback, cancellation, hoặc nhánh xử lý.
- State transition / lifecycle.
- Integration boundary nội bộ ↔ bên ngoài.
- Callback, webhook, scheduled job, queue, event, hoặc async handoff.
- Data path qua module/service/table/DTO/third-party field.

Nếu evidence chưa đủ, diagram phải đánh dấu phần chưa chắc là `unknown`, `assumption`, hoặc `needs BA/PO confirmation`. Không vẽ diagram như fact khi nguồn chỉ cho phép suy luận.
```

- [ ] **Step 4: Sửa mục lục `.maika/skills/spec-extract/references/quy-trinh-chi-tiet.md`**

Add dòng sau `- Bước 5b — Thống kê Integration & Field Mapping`:

```md
- Bước 5c — Vẽ ASCII Flow / State Diagram
```

- [ ] **Step 5: Thêm bước 5c trong `quy-trinh-chi-tiet.md`**

Insert block này ngay sau phần `### Bước 5b — Thống kê Integration & Field Mapping` và trước `### Bước 6 — Trích quy tắc nghiệp vụ (Business Rules)`:

~~~md
---

### Bước 5c — Vẽ ASCII Flow / State Diagram

1. Nếu tài liệu có flow, state, integration, callback, job, hoặc data path, thêm section:

   ```md
   #### ASCII Flow / State Diagram

   ```text
   actor / system A
     -> bước xử lý hoặc state
     -> boundary nội bộ / bên ngoài
     -> kết quả hoặc nhánh tiếp theo
   ```
   ```

2. Diagram phải ưu tiên overview trước:
   - Actor / system chính.
   - Boundary nội bộ ↔ bên ngoài.
   - Happy path.
   - Nhánh lỗi hoặc async handoff quan trọng.

3. Nếu có nhiều flow:
   - Vẽ một overview diagram.
   - Chỉ vẽ diagram nhỏ cho nhánh phức tạp nếu prose dễ gây mơ hồ.

4. Diagram phải đánh dấu `unknown`, `assumption`, hoặc `needs BA/PO confirmation` khi evidence chưa đủ.

5. Không dùng diagram để thay thế Luồng chính, Luồng lỗi, Acceptance Criteria, hoặc Field Mapping. Diagram chỉ làm rõ trình tự và boundary.
~~~

- [ ] **Step 6: Sửa `.maika/skills/spec-extract/references/output-schema.md`**

Trong schema section `### Yêu cầu nghiệp vụ trích từ tài liệu`, add block này sau `#### Actor & Use Case`:

```md
  #### ASCII Flow / State Diagram
  - Bắt buộc khi tài liệu có flow, state, integration, callback, job, hoặc data path.
  - Dùng fenced block `text`.
  - Label boundary nội bộ / bên ngoài khi có integration.
  - Mark `unknown`, `assumption`, hoặc `needs BA/PO confirmation` khi evidence chưa đủ.
```

- [ ] **Step 7: Sửa `.maika/knowledge/templates/REQUIREMENT.tpl.md`**

Insert block này ngay sau section `### To-be (Mong muốn)`:

~~~md
---

## Flow / State Diagram

<!-- Bắt buộc khi task có flow, state, integration, callback, job, hoặc data path. -->
<!-- Nếu task đơn giản không có sequence/boundary đáng kể: ghi "Không cần diagram — task không có flow/state/data path đáng kể". -->

```text
<!-- ASCII diagram: actor/system -> step/state -> boundary -> result -->
```
~~~

- [ ] **Step 8: Chạy regression test**

Run:

```bash
rtk pytest cli/tests/test_ascii_diagram_guidance.py::test_spec_extract_requires_ascii_diagram_capture -q
```

Expected: PASS.

- [ ] **Step 9: Chạy skill standard subset**

Run:

```bash
rtk pytest cli/tests/test_skill_standard.py -q
```

Expected: PASS. Nếu fail do body length của `spec-extract/SKILL.md`, move chi tiết từ `SKILL.md` sang `references/quy-trinh-chi-tiet.md` và giữ `SKILL.md` chỉ còn rule ngắn.

- [ ] **Step 10: Commit task**

```bash
rtk proxy git add cli/tests/test_ascii_diagram_guidance.py \
  .maika/skills/spec-extract/SKILL.md \
  .maika/skills/spec-extract/references/quy-trinh-chi-tiet.md \
  .maika/skills/spec-extract/references/output-schema.md \
  .maika/knowledge/templates/REQUIREMENT.tpl.md
rtk proxy git commit -m "docs(skills): require spec-extract ascii diagrams"
```

---

### Task 2: Cập nhật `openspec-explore` và `EXPLORE_CONTEXT` template bằng regression test

**Files:**
- Modify: `cli/tests/test_ascii_diagram_guidance.py`
- Modify: `.maika/skills/openspec-explore/SKILL.md`
- Modify: `.maika/skills/openspec-explore/references/explore-patterns.md`
- Modify: `.maika/knowledge/templates/EXPLORE_CONTEXT.tpl.md`

**Interfaces:**
- Consumes: `read_text(rel_path: str) -> str` helper từ Task 1.
- Produces: Test function `test_openspec_explore_uses_visual_stance_and_capture()`; explore guidance có stance upstream, visual/capture rule, và template anchor cho architecture/code/data flow.

- [ ] **Step 1: Thêm failing test cho `openspec-explore`**

Append function này vào `cli/tests/test_ascii_diagram_guidance.py`:

```python
def test_openspec_explore_uses_visual_stance_and_capture():
    skill = read_text(".maika/skills/openspec-explore/SKILL.md")
    patterns = read_text(".maika/skills/openspec-explore/references/explore-patterns.md")
    explore_template = read_text(".maika/knowledge/templates/EXPLORE_CONTEXT.tpl.md")

    assert "Explore là stance, không phải workflow cứng" in skill
    assert "Visualize tự do" in skill
    assert "capture insight đó vào `EXPLORE_CONTEXT.md`" in skill
    assert "Do visualize" in skill
    assert "ASCII diagram bắt buộc khi có flow/state/data path" in patterns
    assert "vấn đề user nêu" in patterns
    assert "ASCII diagram bắt buộc khi có flow/state/data path" in explore_template
    assert "Danh sách module chỉ đủ khi không có sequence hoặc boundary đáng kể" in explore_template
```

- [ ] **Step 2: Chạy test để xác nhận fail**

Run:

```bash
rtk pytest cli/tests/test_ascii_diagram_guidance.py::test_openspec_explore_uses_visual_stance_and_capture -q
```

Expected: FAIL với assertion thiếu `Explore là stance, không phải workflow cứng`.

- [ ] **Step 3: Sửa `.maika/skills/openspec-explore/SKILL.md` intro**

Replace đoạn mở đầu dưới heading `# OpenSpec Explore — Đối tác suy nghĩ` bằng:

```md
Vào chế độ explore. Suy nghĩ sâu, Visualize tự do, và đi theo hướng cuộc trò chuyện đang mở ra.

Explore là stance, không phải workflow cứng: không có fixed step, không có output bắt buộc, và không ép user vào funnel. Agent là đối tác suy nghĩ giúp user khám phá vấn đề, đọc code khi liên quan, so sánh option, vẽ diagram khi hữu ích, rồi handoff sang proposal khi bức tranh đã rõ.
```

- [ ] **Step 4: Sửa section `## Stance` trong `SKILL.md`**

Replace bullet list hiện tại bằng:

```md
- Tò mò, không áp đặt.
- Mở thread suy nghĩ, không thẩm vấn.
- Linh hoạt và kiên nhẫn.
- Có grounding: câu hỏi code-trả-lời-được đi qua UA-first probe.
- Visualize tự do: dùng ASCII diagram khi diagram làm rõ flow, state, data path, architecture, dependency, hoặc option branching.
- Capture có kỷ luật: khi một insight quan trọng đã được diagram làm rõ, offer capture insight đó vào `EXPLORE_CONTEXT.md`, OpenSpec artifact, hoặc active knowledge file phù hợp.
- Do visualize: một diagram tốt đáng giá hơn nhiều đoạn prose khi user và agent cần cùng nhìn trình tự xử lý.
```

- [ ] **Step 5: Sửa `.maika/skills/openspec-explore/references/explore-patterns.md`**

Replace nội dung section `## Visualize` bằng:

~~~md
## Visualize

ASCII diagram bắt buộc khi có flow/state/data path đủ phức tạp để prose dễ gây mơ hồ.

Dùng ASCII diagram rộng rãi cho:
- State machine.
- Data flow.
- Architecture sketch.
- Dependency comparison.
- Integration boundary.
- Option branching.
- Flow xử lý khi nhận task mới.

Khi user đưa task mới còn nhiều nhánh xử lý, vẽ nhanh:

```text
vấn đề user nêu
  -> hành vi hiện tại / unknown
  -> UA-first probe nếu chạm code
  -> map As-is / To-be
  -> option A | option B | option C
  -> recommended next step
```

Khi diagram làm rõ một insight quan trọng, hỏi nhẹ xem có capture không:

```text
Insight này đã rõ hơn sau diagram. Capture vào EXPLORE_CONTEXT.md hoặc artifact OpenSpec liên quan không?
```
~~~

- [ ] **Step 6: Sửa `.maika/knowledge/templates/EXPLORE_CONTEXT.tpl.md`**

Replace section `### 2.1 Module/Service liên quan` bằng:

~~~md
### 2.1 Module/Service liên quan

```text
ASCII diagram bắt buộc khi có flow/state/data path.

<!-- Ví dụ:
actor/system
  -> entry point
  -> service/module
  -> database / external system
  -> result / event
-->
```

Danh sách module chỉ đủ khi không có sequence hoặc boundary đáng kể.
~~~

- [ ] **Step 7: Chạy regression tests**

Run:

```bash
rtk pytest cli/tests/test_ascii_diagram_guidance.py -q
```

Expected: PASS.

- [ ] **Step 8: Chạy skill standard subset**

Run:

```bash
rtk pytest cli/tests/test_skill_standard.py -q
```

Expected: PASS.

- [ ] **Step 9: Commit task**

```bash
rtk proxy git add cli/tests/test_ascii_diagram_guidance.py \
  .maika/skills/openspec-explore/SKILL.md \
  .maika/skills/openspec-explore/references/explore-patterns.md \
  .maika/knowledge/templates/EXPLORE_CONTEXT.tpl.md
rtk proxy git commit -m "docs(skills): align explore ascii diagram capture"
```

---

### Task 3: Verify toàn bộ

**Files:**
- Modify: none expected.
- Test: `cli/tests/test_ascii_diagram_guidance.py`, `cli/tests/test_skill_standard.py`, `.maika/tools/skill-lint/tests/test_validate_skills.py`.

**Interfaces:**
- Consumes: Tất cả thay đổi từ Task 1-2.
- Produces: Verification evidence và working tree sạch.

- [ ] **Step 1: Chạy regression tests mới**

Run:

```bash
rtk pytest cli/tests/test_ascii_diagram_guidance.py -q
```

Expected: PASS.

- [ ] **Step 2: Chạy skill standard test**

Run:

```bash
rtk pytest cli/tests/test_skill_standard.py -q
```

Expected: PASS.

- [ ] **Step 3: Chạy skill-lint unit tests**

Run:

```bash
rtk pytest .maika/tools/skill-lint/tests/test_validate_skills.py -q
```

Expected: PASS.

- [ ] **Step 4: Chạy validator trực tiếp trên skill thật**

Run:

```bash
rtk python .maika/tools/skill-lint/validate_skills.py .maika/skills
```

Expected: exit code 0. Nếu validator fail vì rule SP3 hiện hữu không liên quan đến thay đổi này, ghi rõ failure trong final answer và giữ `cli/tests/test_skill_standard.py` làm gate chính cho skill Markdown.

- [ ] **Step 5: Search anchor mới**

Run:

```bash
rtk proxy grep -R "ASCII Flow / State Diagram\\|ASCII diagram bắt buộc khi có flow/state/data path\\|Flow / State Diagram" -n .maika cli/tests docs/superpowers/specs/2026-07-05-ascii-diagram-explore-design.md
```

Expected: output có match trong `spec-extract`, `openspec-explore` reference, `REQUIREMENT.tpl.md`, `EXPLORE_CONTEXT.tpl.md`, regression test, và design spec.

- [ ] **Step 6: Kiểm tra git status**

Run:

```bash
rtk proxy git status --short
```

Expected: clean sau khi các task commit xong.

- [ ] **Step 7: Final summary**

Final answer cần nêu:
- Các file skill/template đã sửa.
- Test đã chạy và kết quả.
- Nếu `validate_skills.py` fail vì baseline SP3 không liên quan, nêu rõ command và lý do.

---

## Self-Review

- Spec coverage: Task 1 cover `spec-extract`, output schema, và `REQUIREMENT.tpl.md`; Task 2 cover `openspec-explore`, explore patterns, và `EXPLORE_CONTEXT.tpl.md`; Task 3 cover verification.
- Placeholder scan: plan không dùng các placeholder cấm hoặc step mơ hồ.
- Type consistency: test helper `read_text(rel_path: str) -> str` được định nghĩa ở Task 1 và dùng lại ở Task 2; không có API runtime mới.
