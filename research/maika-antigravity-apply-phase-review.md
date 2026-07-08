# Báo cáo Review Maika trên Antigravity Ultra

**Chủ đề:** Vì sao Maika brainstorm tốt nhưng dễ quên knowledge/tooling khi vào coding phase  
**Ngày:** 2026-07-08  
**Ngữ cảnh sử dụng:** Maika trên Antigravity Ultra, có dùng Understand Anything (UA), Codebase Memory MCP, Agent Memory, knowledge files và workflow `/task`.

---

## 1. Executive Summary

Maika hiện đang có nền tảng tốt ở các pha trước coding:

```text
Ideation -> Requirement -> Architecture -> Spec
```

Các file như `REQUIREMENT.md`, `EXPLORE_CONTEXT.md`, ideation artifacts và OpenSpec giúp agent brainstorm, chuẩn hoá requirement và phân tích architecture khá tốt.

Tuy nhiên khi chuyển sang coding/apply phase, framework đang bị đứt telemetry:

```text
Spec -> Apply -> Code edit
```

Ở đoạn này, agent không còn bị tracking đủ chặt về:

- đã load knowledge nào;
- đã dùng UA / Codebase Memory / Agent Memory chưa;
- đang sửa file nào;
- sửa vì Acceptance Criteria nào;
- đã dùng bài học nào từ knowledge;
- đã check import thừa chưa;
- đã tốn bao nhiêu context/token hoặc đã load bao nhiêu context;
- có lệch khỏi spec không.

Kết luận chính:

```text
Maika hiện mạnh ở pre-coding intelligence,
nhưng yếu ở coding telemetry và coding-time enforcement.
```

Nói cách khác, Maika đang dạy agent cách nghĩ khá tốt, nhưng chưa kiểm soát đủ từng bước agent code.

---

## 2. Những điểm Maika đang làm tốt

### 2.1. Framework có mental model rõ

Maika không chỉ là prompt pack. Nó có cấu trúc như một agent runtime gồm:

- Runtime Protocol;
- Knowledge Layer;
- Tooling Layer;
- Skills;
- Workflows;
- Rules;
- Procedures.

Đây là hướng đúng nếu mục tiêu là biến coding agent thành một worker có workflow, memory, guardrails và audit trail.

### 2.2. Workflow trước coding khá ổn

Flow chính:

```text
Ideation -> Requirement -> Architecture -> Spec -> Apply
```

Các pha đầu có artifact rõ:

| Pha | Artifact |
|---|---|
| Ideation | `active/ideation/ideation-*.md` |
| Requirement | `active/REQUIREMENT.md` |
| Architecture | `active/EXPLORE_CONTEXT.md` |
| Spec | `openspec/changes/<id>/` |
| Apply | code diff + transparency log |

Điểm này giải thích vì sao Maika brainstorm tốt: agent không nhảy thẳng vào code mà có đường ray để chuẩn hoá yêu cầu, phân tích impact, rồi mới sinh spec.

### 2.3. UA-first doctrine trong codebase-explorer khá đúng

Skill `codebase-explorer` đã định nghĩa đúng vai trò:

```text
UA = định vị domain / flow / architecture / topology
Codebase Memory = đọc logic cụ thể tại node đã định vị
grep = fallback cuối
```

Đây là tư duy đúng, đặc biệt với hệ thống backend/banking có nhiều ranh giới async như Kafka, gRPC, worker, scheduler.

### 2.4. Golden Path 5 bước hợp lý

Golden Path hiện tại:

```text
B1. domain_overview      -> UA
B2. search_code          -> Codebase Memory
B3. domain_flow          -> UA
B4. read_file/get_symbol -> Codebase Memory
B5. verify               -> Codebase Memory + UA
```

Đây là pipeline tốt vì kết hợp top-down và bottom-up:

- UA giúp hiểu domain/flow;
- Codebase Memory giúp xác minh symbol/file/logic;
- verify bằng cả hai nguồn giúp giảm hallucination.

---

## 3. Vấn đề lớn phát hiện được

## 3.1. Coding phase gần như không có black box recorder

Hiện tại các file active knowledge được sử dụng nhiều trước coding:

```text
REQUIREMENT.md
EXPLORE_CONTEXT.md
ideation/*
spec/*
```

Nhưng khi sang apply/coding, agent thường bắt đầu code theo bản năng. Các file như `AGENT_TRANSPARENCY.md` và `TOKEN_LOG.md` có tồn tại trong thiết kế, nhưng nếu không được cập nhật theo microloop khi coding thì chúng không đủ tác dụng.

Triệu chứng thực tế:

```text
- Agent quên dùng UA.
- Agent quên dùng Codebase Memory MCP.
- Agent quên Agent Memory.
- Agent quên bài học trong knowledge.
- Agent vẫn để import thừa dù đã được nhắc.
- Không biết session đã load bao nhiêu context.
- Không biết agent sửa file nào vì lý do gì.
```

Đây là dấu hiệu của một Apply phase thiếu telemetry.

---

## 3.2. Knowledge tồn tại nhưng không được kéo vào vòng lặp edit

Hiện tại knowledge có thể nằm ở:

```text
knowledge-snapshot.md
conventions.yaml
author-dna.yaml
archive/*
agent memory
```

Nhưng trong lúc edit code, agent không bị ép chứng minh rằng nó đã load đúng slice knowledge.

Ví dụ rule:

```text
Không được import thừa
```

Nếu rule này chỉ nằm trong một lesson, archive hoặc memory cũ thì agent rất dễ quên. Vì rule chưa được biến thành coding-time constraint.

Nên thay vì:

```text
Agent nên nhớ không import thừa
```

Cần chuyển thành:

```text
Agent không được kết thúc task nếu Java changed files còn import thừa
```

---

## 3.3. `conventions.yaml` chưa đủ mạnh cho code hygiene

`conventions.yaml` hiện thiên về:

- naming;
- package structure;
- design patterns;
- upstream constraints;
- exceptions;
- resolved questions.

Những rule dạng code hygiene như sau chưa có chỗ đứng rõ:

```text
- Không import thừa.
- Không wildcard import.
- Không duplicate import.
- Không để unused private method/field.
- Không để TODO/debug log tạm.
- Không formatting blast ngoài phạm vi task.
```

Các rule này không nên chỉ nằm ở `author-dna` hoặc `knowledge-snapshot`. Chúng nên nằm trong một section riêng như:

```yaml
code_hygiene:
  java:
    no_unused_imports:
      severity: mandatory
      agent_action: fix_before_continue
```

---

## 3.4. `author-dna.yaml` có hard principles nhưng còn quá chung

`author-dna.yaml` có khái niệm hard principles, ví dụ SOLID + Clean Code. Đây là đúng hướng.

Nhưng với agent coding, rule quá chung như:

```text
Tuân thủ Clean Code
```

không đủ để nó tự nhớ:

```text
Không import thừa
```

Cần biến bài học lặp lại thành hard principle cụ thể:

```yaml
HP-JAVA-IMPORT-001:
  name: "Java import hygiene"
  description: >
    Khi chỉnh sửa Java file, agent phải loại bỏ unused imports,
    không dùng wildcard imports, và không thêm import nếu không cần.
  agent_action: REJECT_AND_FIX
  confirmed: true
  source: user-teaching
  scope: java
  applies_to:
    - "**/*.java"
```

---

## 3.5. `knowledge-snapshot.md` không phải nơi phù hợp cho coding hygiene

`knowledge-snapshot.md` phù hợp để lưu sự thật kiến trúc:

```text
- module nào tồn tại;
- service nào gọi service nào;
- bảng DB nào chứa config nào;
- topic Kafka nào liên quan flow nào;
- business rule nào đã xác nhận.
```

Không nên dùng nó làm nơi chính để lưu rule kiểu:

```text
Không import thừa
```

Rule đó nên thuộc:

```text
conventions.yaml / code_hygiene
author-dna.yaml / hard_principles
apply gate / hygiene gate
```

---

## 3.6. `knowledge-curator` học sau task nhưng không bảo vệ lúc edit

`knowledge-curator` phù hợp để:

```text
- archive active context;
- update knowledge snapshot;
- push to agent memory;
- reset active context.
```

Nhưng nó chạy sau khi task hoàn thành. Với lỗi như import thừa, phát hiện cuối task là quá muộn.

Rule hygiene cần chạy ở thời điểm:

```text
sau mỗi edit file
trước khi chuyển file tiếp theo
trước final answer
```

---

## 3.7. `spec-validator` chưa đủ deterministic cho coding hygiene

`spec-validator` có:

```text
- pre-apply gate;
- AC coverage;
- integration coverage;
- post-apply verify;
- DNA compliance check.
```

Nhưng các rule như unused import cần deterministic gate:

```bash
./gradlew spotlessCheck
./gradlew checkstyleMain
./gradlew compileJava
```

Nếu chỉ để LLM tự review semantic thì sẽ vẫn lọt.

---

## 4. Root Cause

Root cause không phải là thiếu knowledge.

Root cause là:

```text
Knowledge chưa được compile thành coding-time gates.
```

Cụ thể:

```text
Knowledge file     -> agent có thể đọc hoặc không
Lesson cũ          -> agent có thể nhớ hoặc không
Author DNA         -> quá chung
Convention         -> chưa có code_hygiene
Apply phase        -> thiếu trace
Hygiene check      -> chưa deterministic
```

Vì vậy khi vào coding, agent hoạt động theo xác suất/model habit nhiều hơn là theo framework.

---

## 5. Đề xuất kiến trúc mới cho Apply Phase

## 5.1. Thêm `APPLY_TRACE.yaml`

Tạo file:

```text
.agents/knowledge/active/APPLY_TRACE.yaml
```

hoặc với generic root:

```text
.maika/knowledge/active/APPLY_TRACE.yaml
```

Mục tiêu: làm black box recorder cho coding phase.

Ví dụ:

```yaml
apply_session:
  task_id: "TASK-ID"
  phase: "apply"
  execution_mode: "antigravity-inline | fresh-session | subagent"
  started_at: "2026-07-08"

loaded_context:
  requirement: true
  explore_context: true
  spec_tasks: true
  author_dna_slice:
    - hard_principles
    - complexity_thresholds
  conventions_slice:
    - code_hygiene
    - naming
  agent_memory:
    status: "queried | skipped | unavailable"
    query: ""

coding_constraints:
  java:
    no_unused_imports: mandatory
    no_wildcard_imports: mandatory
    preserve_existing_style: mandatory
    compile_after_edit: recommended

changed_files: []

tool_usage:
  ua:
    used: false
    purpose: ""
  codebase_memory:
    used: false
    purpose: ""
  agent_memory:
    used: false
    purpose: ""

context_budget:
  exact_token_available: false
  loaded_files_count: 0
  large_context_warning: false
  notes: ""

final_gate:
  spec_alignment: pending
  hygiene_gate: pending
  import_check: pending
  tests: pending
```

---

## 5.2. Mỗi edit phải ghi vào `changed_files`

Ví dụ:

```yaml
changed_files:
  - path: "src/main/java/com/example/StageResponseMapper.java"
    action: "modified"
    reason: "Implement AC-2: group approvers by stageId"
    spec_ref: "openspec/changes/rle-stage/tasks.md#AC-2"
    knowledge_used:
      - "HP-JAVA-IMPORT-001"
    post_edit_checks:
      unused_imports: pass
      wildcard_imports: pass
      compile: not_run
      note: "compile skipped because project dependencies unavailable locally"
```

Điều này giúp audit được:

```text
File này sửa vì sao?
Có nằm trong spec không?
Có dùng bài học nào không?
Đã check import chưa?
```

---

## 5.3. Thêm `code_hygiene` vào `conventions.yaml`

Đề xuất section:

```yaml
code_hygiene:
  java:
    no_unused_imports:
      severity: mandatory
      agent_action: fix_before_continue
      description: "Không được để import không sử dụng trong Java files."
      detection:
        preferred:
          - "./gradlew spotlessCheck"
          - "./gradlew checkstyleMain"
          - "./gradlew compileJava"
        fallback: "manual review changed Java files"
      applies_to:
        - "**/*.java"

    no_wildcard_imports:
      severity: mandatory
      agent_action: fix_before_continue
      description: "Không dùng wildcard imports."
      applies_to:
        - "**/*.java"

    preserve_existing_style:
      severity: mandatory
      agent_action: review_before_submit
      description: "Không format lan rộng ngoài vùng code cần sửa."
      applies_to:
        - "**/*.java"
```

---

## 5.4. Thêm `code-hygiene` skill

Tạo:

```text
.maika/skills/code-hygiene/SKILL.md
```

Nhiệm vụ:

```text
- Review changed files.
- Remove unused imports.
- Block wildcard imports.
- Prevent formatting blast.
- Run deterministic hygiene command when available.
- Update APPLY_TRACE.yaml.
```

Quy trình:

```text
1. Read APPLY_TRACE.yaml.
2. List changed Java files.
3. Check imports.
4. Run compile/spotless/checkstyle if available.
5. Fix issues.
6. Mark hygiene gate PASS/BLOCK.
```

---

## 5.5. Thêm `apply-runner` skill

Tạo:

```text
.maika/skills/apply-runner/SKILL.md
```

Vai trò:

```text
Apply spec vào code bằng microloop có tracking.
```

Microloop bắt buộc:

```text
READ -> PLAN SMALL PATCH -> EDIT -> TRACE -> HYGIENE -> VERIFY
```

Không cho agent làm kiểu:

```text
READ MANY -> PATCH MANY -> HOPE
```

Quy tắc:

```text
- Không edit file nếu chưa ghi reason/spec_ref.
- Không chuyển sang file tiếp theo nếu chưa update APPLY_TRACE.
- Không final nếu final_gate chưa PASS hoặc chưa có lý do skip rõ.
```

---

## 5.6. Thêm gate deterministic

Đề xuất command:

```bash
python3 .agents/tools/gate-check/cli.py apply-trace-ready .agents/knowledge/active/APPLY_TRACE.yaml
python3 .agents/tools/gate-check/cli.py java-hygiene --changed-files
python3 .agents/tools/gate-check/cli.py apply-final .agents/knowledge/active/APPLY_TRACE.yaml
```

Nếu chưa implement tool đầy đủ, ban đầu có thể check tối thiểu:

```text
- APPLY_TRACE.yaml tồn tại.
- loaded_context có requirement/spec/convention slice.
- changed_files không rỗng nếu có code edit.
- Java changed files có unused_imports_checked=true.
- final_gate.hygiene_gate != pending.
```

---

## 6. Fresh session có cần thiết không?

Không cần mở session mới cho mọi thứ.

Nhưng với Maika + Antigravity, nên dùng pattern:

```text
Brainstorm / Requirement / Architecture / Spec: cùng session được.
Apply / Coding thật: nên mở fresh session hoặc fresh worker.
```

Lý do:

- session dài dễ thành context soup;
- brainstorm chứa nhiều hướng bị loại;
- tool logs và assumption cũ làm nhiễu;
- coding cần context gọn, chính xác, ít lịch sử;
- fresh session buộc agent consume artifact thay vì dựa vào trí nhớ chat.

Flow đề xuất:

```text
Session 1:
  Ideation -> Requirement -> Explore -> Spec

Session 2:
  Apply from coding capsule
```

Coding session chỉ load:

```text
- REQUIREMENT.md
- EXPLORE_CONTEXT.md summary
- OpenSpec tasks.md
- allowed files
- author-dna hard_principles + complexity_thresholds
- conventions code_hygiene
- APPLY_TRACE.yaml
```

---

## 7. Token tracking nên đổi thành Context Budget Tracking

Nếu Antigravity không expose token chính xác, không nên giả vờ tracking token tuyệt đối.

Nên đổi `TOKEN_LOG.md` thành:

```text
CONTEXT_BUDGET.md
```

hoặc giữ tên cũ nhưng đổi nội dung thành context budget.

Ví dụ:

```md
# Context Budget Log

## Apply Session

### Loaded
- REQUIREMENT.md: full
- EXPLORE_CONTEXT.md: summary
- tasks.md: full
- author-dna.yaml: hard_principles + complexity_thresholds
- conventions.yaml: code_hygiene
- target files: 3

### Avoided
- archive/: not loaded
- full knowledge-snapshot.md: not loaded
- full UA graph: not loaded
- full conversation history: not loaded

### Risk
- Context risk: LOW
- Reason: fresh apply session + limited files
```

Cái này thực dụng hơn token exact.

---

## 8. Roadmap ưu tiên

## P0 — Sửa ngay

### P0.1. Thêm `APPLY_TRACE.yaml`

Mục tiêu: có tracking cho coding phase.

### P0.2. Thêm `code_hygiene` vào `conventions.yaml`

Mục tiêu: biến bài học “không import thừa” thành rule chính thức.

### P0.3. Thêm Java import hard principle vào `author-dna.yaml`

Mục tiêu: agent_action = `REJECT_AND_FIX`.

### P0.4. Trước final, bắt agent update `APPLY_TRACE.yaml`

Mục tiêu: không final theo bản năng.

---

## P1 — Nên làm sớm

### P1.1. Tạo `code-hygiene` skill

Mục tiêu: isolate rule hygiene khỏi architecture/spec.

### P1.2. Tạo `apply-runner` skill

Mục tiêu: coding theo microloop.

### P1.3. Thêm gate-check cho apply final

Mục tiêu: block final nếu thiếu evidence.

### P1.4. Dùng Spotless hoặc Checkstyle cho Java

Ưu tiên:

```gradle
spotless {
    java {
        removeUnusedImports()
        importOrder()
        trimTrailingWhitespace()
        endWithNewline()
    }
}
```

Command:

```bash
./gradlew spotlessApply
./gradlew spotlessCheck
```

---

## P2 — Cải thiện dài hạn

### P2.1. Structured `AGENT_TRANSPARENCY.yaml`

Đổi log prose sang machine-readable block.

### P2.2. Agent Memory Retrieval Contract

Tạo skill riêng:

```text
memory-recaller
```

Trigger:

```text
- task liên quan convention cũ;
- task liên quan incident cũ;
- task liên quan module đã từng sửa;
- user nói "như lần trước", "đã dặn", "theo knowledge".
```

### P2.3. Dashboard Control Tower

Hiển thị:

```text
- phase hiện tại;
- loaded context;
- changed files;
- gate status;
- hygiene status;
- tool usage;
- confidence ceiling.
```

---

## 9. Mẫu prompt cho Apply session trên Antigravity

Có thể dùng khi mở fresh session coding:

```text
Bạn đang ở Maika Apply phase.

Không brainstorm lại từ đầu.

Load bắt buộc:
1. .agents/knowledge/active/REQUIREMENT.md
2. .agents/knowledge/active/EXPLORE_CONTEXT.md
3. openspec/changes/<CHANGE_ID>/tasks.md
4. .agents/knowledge/long-term/author-dna.yaml
   - chỉ hard_principles + complexity_thresholds
5. .agents/knowledge/long-term/conventions.yaml
   - chỉ code_hygiene + naming liên quan
6. .agents/knowledge/active/APPLY_TRACE.yaml

Quy tắc bắt buộc:
- Mỗi file sửa phải ghi reason + spec_ref vào APPLY_TRACE.yaml.
- Nếu sửa Java file, phải check unused imports và wildcard imports.
- Không được final nếu final_gate chưa PASS hoặc chưa có lý do skip rõ.
- Nếu cần hiểu flow/domain/topology, dùng UA trước.
- Nếu cần đọc logic method/file, dùng Codebase Memory sau UA.
- Nếu có bài học cũ liên quan, query Agent Memory hoặc ghi rõ unavailable.
```

---

## 10. Kết luận

Phát hiện chính:

```text
Maika không thiếu knowledge.
Maika thiếu enforcement trong lúc coding.
```

Framework hiện đã có nền tảng tốt:

```text
Requirement
Explore Context
Spec
Knowledge Snapshot
Author DNA
Conventions
Transparency
```

Nhưng Apply phase cần được nâng thành:

```text
Spec-driven coding
+ Apply trace
+ Edit ledger
+ Hygiene gate
+ Context budget log
+ Final verification
```

Câu chốt:

```text
Đừng bắt agent nhớ bài học nhỏ bằng niềm tin.
Hãy biến bài học đó thành gate mà agent không thể bỏ qua.
```

Với lỗi “không import thừa”, cách sửa đúng không phải nhắc agent thêm 10 lần. Cách sửa đúng là:

```text
No unused imports -> code_hygiene mandatory rule
                  -> post-edit hygiene check
                  -> final gate
                  -> fail nếu chưa check/fix
```

Khi đó Maika mới thực sự chuyển từ:

```text
agent được hướng dẫn
```

sang:

```text
agent bị kiểm soát có bằng chứng
```
