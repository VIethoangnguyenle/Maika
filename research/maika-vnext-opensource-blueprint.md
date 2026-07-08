# Báo cáo: Gợi ý Open-source làm tiền đề update Maika vNext

**Chủ đề:** Các open-source/framework/tool nên tham khảo để nâng cấp Maika, đặc biệt cho Apply/Coding phase trên Antigravity Ultra  
**Ngày:** 2026-07-08  
**Ngữ cảnh:** Maika hiện brainstorm/requirement/architecture khá tốt, nhưng khi qua coding phase dễ mất tracking, quên UA, Codebase Memory MCP, Agent Memory và các bài học nhỏ như “không import thừa”.

---

## 1. Executive Summary

Maika hiện đang mạnh ở các pha trước coding:

```text
Ideation -> Requirement -> Architecture -> Spec
```

Nhưng yếu ở đoạn:

```text
Spec -> Apply -> Code edit -> Verify
```

Vấn đề cốt lõi:

```text
Maika có knowledge và workflow,
nhưng thiếu coding telemetry + deterministic coding gates.
```

Để update Maika, không nên tự nghĩ toàn bộ từ đầu. Nên học pattern từ các open-source/tool đã giải quyết từng phần của bài toán:

| Nhu cầu của Maika | Open-source/tool nên học |
|---|---|
| Edit → lint/test → fix loop | Aider |
| Telemetry/event stream/checkpoint/context file | Gemini CLI |
| Agent control tower/runtime/sandbox | OpenHands |
| Issue-to-patch trajectory | SWE-agent |
| Headless CLI + JSON output | Cline |
| Mode separation | Roo Code |
| Extensible tool/capability registry | Goose |
| Java import hygiene | Spotless + Checkstyle |
| Codemod/refactor lớn | OpenRewrite |
| Custom static analysis rules | Semgrep |

Kết luận ngắn:

```text
Maika vNext không cần trở thành coding agent mới.
Maika nên trở thành governance + telemetry layer bọc quanh Antigravity/Claude/Codex/Gemini.
```

---

## 2. Root Problem cần giải quyết

Hiện tượng thực tế khi dùng Maika trên Antigravity:

```text
- Brainstorm khá.
- Requirement/ExploreContext có ích.
- Nhưng khi coding, agent dễ code theo bản năng.
- Agent quên dùng UA.
- Agent quên dùng Codebase Memory MCP.
- Agent quên Agent Memory.
- Agent quên bài học trong knowledge.
- Rule nhỏ như “không import thừa” vẫn bị vi phạm.
- Không có tracking rõ agent đã load knowledge nào.
- Không có tracking rõ changed file nào sửa vì AC nào.
- Không có tracking context/token budget thực tế.
```

Chẩn đoán:

```text
Pre-coding intelligence: OK
Coding telemetry: thiếu
Coding enforcement: thiếu
```

Do đó Maika vNext cần bổ sung:

```text
Apply trace
Edit ledger
Code hygiene gate
Context budget log
Tool evidence gate
Final verification gate
```

---

## 3. Open-source nên học trực tiếp

---

# 3.1. Aider — hình mẫu cho Apply loop

**Repo:** https://github.com/Aider-AI/aider

## Nên học gì?

Aider rất đáng học cho Maika vì nó tập trung vào coding loop thực dụng:

```text
Edit code
-> run lint/test
-> detect error
-> fix
-> rerun
```

Đây chính là phần Maika đang thiếu ở Apply phase.

## Pattern nên mượn

```text
EDIT -> RUN LINT/TEST -> FIX -> RECHECK -> CONTINUE
```

Không nên để agent làm kiểu:

```text
READ MANY -> PATCH MANY -> HOPE
```

## Maika nên implement

Tạo skill:

```text
.maika/skills/apply-runner/SKILL.md
```

Microloop:

```text
1. Pick one spec task.
2. Pick one target file.
3. Explain why this file is needed.
4. Edit minimal patch.
5. Update APPLY_TRACE.yaml.
6. Run hygiene/lint/test gate.
7. Fix violations.
8. Move to next file only after gate is clean.
```

## Áp dụng cho Java/Spring Boot

```bash
./gradlew compileJava
./gradlew test
./gradlew spotlessCheck
./gradlew checkstyleMain
```

## Vì sao quan trọng?

Rule như “không import thừa” không nên giao cho trí nhớ của model. Phải có loop bắt lỗi sau edit.

---

# 3.2. Gemini CLI — hình mẫu cho telemetry, checkpoint, event stream

**Repo:** https://github.com/google-gemini/gemini-cli

## Nên học gì?

Gemini CLI đáng học ở các điểm:

```text
- context files;
- checkpointing;
- MCP support;
- non-interactive scripting;
- JSON output;
- stream-json event output.
```

Đặc biệt, ý tưởng `stream-json` rất hợp để Maika xây telemetry.

## Pattern nên mượn

```text
Agent action không chỉ là prose.
Mỗi action nên emit event.
```

Ví dụ event:

```json
{"type":"phase_start","phase":"apply","change_id":"rle-approval-limit"}
{"type":"file_edit","file":"StageMapper.java","spec_ref":"AC-2"}
{"type":"hygiene_check","file":"StageMapper.java","unused_imports":"pass"}
{"type":"gate_result","gate":"apply-final","status":"pass"}
```

## Maika nên implement

CLI/event layer:

```bash
maika trace append --type file_edit --file src/main/java/...
maika trace tail --format json
maika apply --output stream-json
maika gate apply-final --output json
```

File đích:

```text
.maika/knowledge/active/APPLY_TRACE.yaml
.maika/knowledge/active/AGENT_TRANSPARENCY.md
.maika/knowledge/active/CONTEXT_BUDGET.md
```

## Vì sao quan trọng?

Nếu không có event stream/trace, Apply phase là hộp đen. Khi agent làm sai, ta chỉ thấy final diff, không thấy đường đi.

---

# 3.3. OpenHands — hình mẫu cho Control Tower / Agent Runtime

**Repo:** https://github.com/OpenHands/OpenHands  
**Paper:** https://arxiv.org/abs/2407.16741

## Nên học gì?

OpenHands đáng học ở kiến trúc control plane:

```text
frontend/control tower
-> agent backend
-> runtime/sandbox
-> tool execution
-> logs/trajectory
```

OpenHands được mô tả là platform cho software agents có thể viết code, tương tác command line, browse web, chạy trong môi trường sandbox và hỗ trợ benchmark/evaluation.

## Pattern nên mượn

Maika nên có “Control Tower” nhỏ:

```text
- current phase;
- current task/change id;
- loaded context;
- changed files;
- active gates;
- tool usage;
- confidence ceiling;
- hygiene status;
- final verification status.
```

## Maika nên implement

Dashboard hoặc CLI status:

```bash
maika status
maika trace tail
maika gate status
maika context budget
```

Ví dụ output:

```text
Phase: APPLY
Change: rle-stage-grouping
Loaded:
  - REQUIREMENT.md
  - EXPLORE_CONTEXT.md summary
  - tasks.md
  - author-dna hard_principles
  - conventions code_hygiene
Changed files:
  - StageResponseMapper.java
Gates:
  - java_hygiene: PASS
  - spec_alignment: PASS
  - tests: SKIPPED_WITH_REASON
```

## Vì sao quan trọng?

Antigravity có thể chạy agent mạnh, nhưng Maika cần nhìn được agent đang làm gì. Control Tower giúp chuyển từ “tin agent” sang “quan sát agent”.

---

# 3.4. SWE-agent — hình mẫu cho issue-to-patch trajectory

**Repo:** https://github.com/SWE-agent/SWE-agent

## Nên học gì?

SWE-agent là hình mẫu tốt cho workflow:

```text
Issue/task
-> investigate
-> locate files
-> patch
-> verify
-> produce trajectory
```

Điểm đáng học nhất không phải UI, mà là tư duy trajectory: lưu lại quá trình agent đi từ issue đến patch.

## Pattern nên mượn

Maika nên lưu `APPLY_TRACE.yaml` như một trajectory tối giản:

```yaml
trajectory:
  - step: 1
    intent: "locate relevant module"
    tool: "ua.domain_overview"
    result: "domain=rle-approval"
  - step: 2
    intent: "read target method"
    tool: "codebase_memory.read_file"
    file: "StageResponseMapper.java"
  - step: 3
    intent: "patch"
    file: "StageResponseMapper.java"
    spec_ref: "AC-2"
  - step: 4
    intent: "verify"
    command: "./gradlew compileJava"
    status: "pass"
```

## Vì sao quan trọng?

Sau task, `knowledge-curator` không nên học từ final answer mơ hồ. Nó nên học từ trajectory có bằng chứng.

---

# 3.5. Cline — hình mẫu cho headless CLI + JSON automation

**Repo:** https://github.com/cline/cline

## Nên học gì?

Cline đáng học ở surface:

```text
- IDE extension;
- SDK;
- CLI;
- headless usage;
- JSON output;
- CI/CD integration.
```

## Pattern nên mượn

Maika nên có song song hai mặt:

```text
Markdown/prose cho agent đọc
YAML/JSON cho tool/gate/dashboard parse
```

## Maika nên implement

```bash
maika apply --change-id xxx --output json
maika gate java-hygiene --output json
maika trace tail --format json
```

Ví dụ JSON:

```json
{
  "gate": "java-hygiene",
  "status": "fail",
  "violations": [
    {
      "file": "src/main/java/.../StageMapper.java",
      "rule": "unused_import",
      "line": 12
    }
  ]
}
```

## Vì sao quan trọng?

Hiện Maika nhiều markdown. Markdown tốt cho agent đọc, nhưng yếu cho enforcement. JSON/YAML giúp gate thật sự block được.

---

# 3.6. Roo Code — hình mẫu cho mode separation

**Repo:** https://github.com/RooVetGit/Roo-Code

## Nên học gì?

Roo Code đáng học ở mode system:

```text
Code
Architect
Ask
Debug
Custom Modes
```

Maika đã có skill/workflow, nhưng nên formal hóa thành mode rõ hơn.

## Pattern nên mượn

```text
MODE_REQUIREMENT
MODE_ARCHITECTURE
MODE_SPEC
MODE_APPLY
MODE_REVIEW
```

Mỗi mode có:

```yaml
allowed_actions:
  - read
  - query_ua
  - query_codebase_memory

forbidden_actions:
  - write_code

required_artifacts:
  - REQUIREMENT.md
```

Riêng Apply mode:

```yaml
mode: APPLY
must_load:
  - REQUIREMENT.md
  - EXPLORE_CONTEXT.md
  - openspec tasks.md
  - author-dna hard_principles
  - conventions code_hygiene
must_write:
  - APPLY_TRACE.yaml
must_run_before_final:
  - code_hygiene
  - spec_alignment
  - final_gate
```

## Vì sao quan trọng?

Hiện Maika tốt ở brainstorm nhưng khi qua coding bị rơi khỏi mode. Mode separation giúp agent không lẫn “architect mode” với “apply mode”.

---

# 3.7. Goose — hình mẫu cho extensible capability registry

**Repo:** https://github.com/block/goose

## Nên học gì?

Goose đáng học ở tư duy agent có thể cài tool, execute command, edit, test với nhiều model/tool provider.

## Pattern nên mượn

Maika nên có capability registry, thay vì encode tool behavior rải rác trong prose.

Ví dụ:

```yaml
capabilities:
  java_hygiene:
    required_when:
      - changed_files contains "**/*.java"
    providers:
      - name: spotless
        check: "./gradlew spotlessCheck"
        fix: "./gradlew spotlessApply"
      - name: checkstyle
        check: "./gradlew checkstyleMain"
      - name: compile
        check: "./gradlew compileJava"
    fallback:
      - manual_import_review
```

## Vì sao quan trọng?

Nếu tool name/provider thay đổi theo platform, Maika cần registry để resolve capability thay vì để agent tự nhớ.

---

## 4. Tool nên dùng thật trong Maika

---

# 4.1. Spotless — P0 cho Java import hygiene

**Repo:** https://github.com/diffplug/spotless

## Vì sao nên dùng?

Spotless hỗ trợ Gradle/Maven/SBT và nhiều ngôn ngữ. Với Java, Spotless có các step liên quan trực tiếp tới vấn đề của ông:

```text
ImportOrderStep
RemoveUnusedImportsStep
ExpandWildcardImportsStep
ForbidWildcardImportsStep
```

## Maika nên dùng thế nào?

Trong Gradle:

```gradle
plugins {
    id "com.diffplug.spotless" version "7.0.4"
}

spotless {
    java {
        removeUnusedImports()
        importOrder()
        trimTrailingWhitespace()
        endWithNewline()
    }
}
```

Gate:

```bash
./gradlew spotlessApply
./gradlew spotlessCheck
```

## Vai trò trong Maika

```text
Spotless = auto-fix hygiene
```

Đặc biệt cho:

```text
- unused import;
- import order;
- wildcard import;
- whitespace;
- newline.
```

---

# 4.2. Checkstyle — P0/P1 để fail build khi import thừa

**Docs:** https://checkstyle.org/checks/imports/unusedimports.html

## Vì sao nên dùng?

Checkstyle có check `UnusedImports`.

Config mẫu:

```xml
<module name="Checker">
  <module name="TreeWalker">
    <module name="UnusedImports"/>
  </module>
</module>
```

Gate:

```bash
./gradlew checkstyleMain
```

## Vai trò trong Maika

```text
Checkstyle = block nếu vi phạm
```

Kết hợp tốt nhất:

```text
Spotless = fix
Checkstyle = verify/block
```

---

# 4.3. OpenRewrite — P1/P2 cho codemod/refactor lớn

**Docs:** https://docs.openrewrite.org/recipes/java/removeunusedimports

## Vì sao nên dùng?

OpenRewrite có recipe:

```text
org.openrewrite.java.RemoveUnusedImports
```

Nó phù hợp với task lớn hơn:

```text
- migration framework;
- bulk refactor;
- package rename;
- remove deprecated API;
- multi-module cleanup.
```

Không cần dùng cho mọi task nhỏ.

## Vai trò trong Maika

```text
OpenRewrite = codemod provider
```

Capability:

```yaml
java_codemod:
  provider: openrewrite
  recipes:
    - org.openrewrite.java.RemoveUnusedImports
```

---

# 4.4. Semgrep — P1/P2 cho custom static rules

**Docs:** https://docs.semgrep.dev/writing-rules/overview

## Vì sao nên dùng?

Semgrep cho phép viết custom rules bằng YAML. Nó hợp với rule riêng của dự án/banking hơn là import hygiene.

Ví dụ rule nên check:

```text
- Không log PII.
- Không hardcode token.
- Không catch Exception rồi bỏ qua.
- Không gọi repository trực tiếp từ controller.
- Không dùng deprecated API nội bộ.
- Không tạo transaction state sai tầng.
```

## Vai trò trong Maika

```text
Semgrep = project-specific static rule engine
```

Ví dụ capability:

```yaml
custom_static_rules:
  provider: semgrep
  command: "semgrep --config .maika/rules/semgrep"
  required_when:
    - changed_files contains "**/*.java"
```

---

## 5. Blueprint đề xuất cho Maika vNext

---

# 5.1. P0 — Coding telemetry tối thiểu

## Thêm file

```text
.maika/knowledge/active/APPLY_TRACE.yaml
```

Template:

```yaml
apply_session:
  task_id: ""
  phase: "apply"
  execution_mode: "antigravity-inline | fresh-session | subagent"
  started_at: ""

loaded_context:
  requirement: false
  explore_context: false
  spec_tasks: false
  author_dna_slice: []
  conventions_slice: []
  agent_memory:
    status: "not_checked"
    query: ""

coding_constraints:
  java:
    no_unused_imports: mandatory
    no_wildcard_imports: mandatory
    preserve_existing_style: mandatory

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

# 5.2. P0 — Code hygiene trong `conventions.yaml`

Thêm section:

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

# 5.3. P0 — Hard principle trong `author-dna.yaml`

Thêm:

```yaml
hard_principles:
  HP-JAVA-IMPORT-001:
    name: "Java import hygiene"
    description: >
      Khi chỉnh sửa Java file, agent phải loại bỏ unused imports,
      không dùng wildcard imports, và không thêm import nếu không cần.
    agent_action: REJECT_AND_FIX
    confirmed: true
    source: user-teaching
    author_note: "Không được import thừa."
    scope: java
    applies_to:
      - "**/*.java"
    exceptions: []
```

---

# 5.4. P1 — Skill `apply-runner`

Tạo:

```text
.maika/skills/apply-runner/SKILL.md
```

Nhiệm vụ:

```text
Apply spec vào code bằng microloop có tracking.
```

Microloop:

```text
READ -> PATCH -> TRACE -> HYGIENE -> VERIFY
```

Rule:

```text
- Không edit nếu chưa có spec_ref.
- Không chuyển file nếu chưa update APPLY_TRACE.yaml.
- Không final nếu final_gate chưa PASS hoặc chưa có reason skip.
```

---

# 5.5. P1 — Skill `code-hygiene`

Tạo:

```text
.maika/skills/code-hygiene/SKILL.md
```

Nhiệm vụ:

```text
- List changed Java files.
- Check unused imports.
- Check wildcard imports.
- Run Spotless/Checkstyle/compile if available.
- Fix violations.
- Update APPLY_TRACE.yaml.
```

Gate command:

```bash
python3 .maika/tools/gate-check/cli.py java-hygiene --changed-files
```

---

# 5.6. P1 — Context Budget thay vì Token Log giả

Nếu Antigravity không expose token chính xác, đừng giả vờ biết exact token.

Đổi `TOKEN_LOG.md` thành context budget log:

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

---

# 5.7. P2 — Event stream / JSON output

Theo pattern Gemini CLI + Cline:

```bash
maika apply --output stream-json
maika trace tail --format json
maika gate apply-final --output json
```

Event mẫu:

```json
{"type":"context_loaded","file":"REQUIREMENT.md","mode":"full"}
{"type":"context_loaded","file":"EXPLORE_CONTEXT.md","mode":"summary"}
{"type":"file_edit","file":"StageMapper.java","spec_ref":"AC-2"}
{"type":"hygiene_check","rule":"no_unused_imports","status":"pass"}
{"type":"gate_result","gate":"apply-final","status":"pass"}
```

---

# 5.8. P2 — Control Tower

Theo pattern OpenHands:

```text
maika status
```

Hiển thị:

```text
Phase: APPLY
Change: rle-stage-grouping
Execution mode: fresh-session
Loaded context:
  - REQUIREMENT.md
  - EXPLORE_CONTEXT.md summary
  - tasks.md
  - author-dna hard_principles
  - conventions code_hygiene
Changed files:
  - StageResponseMapper.java
Gates:
  - java_hygiene: PASS
  - spec_alignment: PASS
  - compile: SKIPPED_WITH_REASON
Tool usage:
  - UA: used
  - Codebase Memory: used
  - Agent Memory: skipped_with_reason
```

---

# 5.9. P3 — Trajectory archive

Theo pattern SWE-agent:

Khi task xong, archive:

```text
knowledge/archive/<task-id>/APPLY_TRACE.yaml
knowledge/archive/<task-id>/PATCH_SUMMARY.md
knowledge/archive/<task-id>/GATE_RESULTS.yaml
knowledge/archive/<task-id>/CONTEXT_BUDGET.md
```

Sau đó `knowledge-curator` học từ các file này.

---

## 6. Priority Matrix

| Priority | Hạng mục | Lấy cảm hứng từ | Tác dụng |
|---|---|---|---|
| P0 | `APPLY_TRACE.yaml` | SWE-agent/Gemini CLI | Có black box recorder cho coding |
| P0 | `code_hygiene` trong conventions | Spotless/Checkstyle | Không quên rule nhỏ |
| P0 | Java import hard principle | Maika author-dna | Biến lesson thành rule |
| P0 | Spotless/Checkstyle gate | Spotless/Checkstyle | Fix/block import thừa |
| P1 | `apply-runner` skill | Aider | Edit theo microloop |
| P1 | `code-hygiene` skill | Aider/Spotless | Hygiene sau mỗi edit |
| P1 | Context budget log | Gemini CLI | Biết đã load gì |
| P2 | JSON/event stream | Gemini CLI/Cline | Dashboard/gate parse được |
| P2 | Control Tower | OpenHands | Quan sát agent đang làm gì |
| P3 | Trajectory archive | SWE-agent | Học từ quá trình, không chỉ final |

---

## 7. File layout đề xuất

```text
.maika/
  knowledge/
    active/
      REQUIREMENT.md
      EXPLORE_CONTEXT.md
      AGENT_TRANSPARENCY.md
      CONTEXT_BUDGET.md
      APPLY_TRACE.yaml
    long-term/
      conventions.yaml
      author-dna.yaml
      knowledge-snapshot.md
    archive/
      <task-id>/
        APPLY_TRACE.yaml
        PATCH_SUMMARY.md
        GATE_RESULTS.yaml
        CONTEXT_BUDGET.md

  skills/
    apply-runner/
      SKILL.md
    code-hygiene/
      SKILL.md
    memory-recaller/
      SKILL.md

  tools/
    gate-check/
      cli.py
    trace/
      cli.py

  rules/
    semgrep/
      no-pii-log.yaml
      no-direct-repository-in-controller.yaml
```

---

## 8. Apply session prompt mẫu cho Antigravity

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

## 9. Nguồn tham khảo

### Agent/coding frameworks

- Aider: https://github.com/Aider-AI/aider
- Gemini CLI: https://github.com/google-gemini/gemini-cli
- OpenHands: https://github.com/OpenHands/OpenHands
- OpenHands paper: https://arxiv.org/abs/2407.16741
- SWE-agent: https://github.com/SWE-agent/SWE-agent
- Cline: https://github.com/cline/cline
- Roo Code: https://github.com/RooVetGit/Roo-Code
- Goose: https://github.com/block/goose

### Java/code quality tools

- Spotless: https://github.com/diffplug/spotless
- Checkstyle UnusedImports: https://checkstyle.org/checks/imports/unusedimports.html
- OpenRewrite RemoveUnusedImports: https://docs.openrewrite.org/recipes/java/removeunusedimports
- Semgrep custom rules: https://docs.semgrep.dev/writing-rules/overview

---

## 10. Kết luận

Nếu chỉ chọn 5 thứ làm tiền đề update Maika vNext, nên chọn:

```text
1. Aider
2. Spotless + Checkstyle
3. Gemini CLI
4. OpenHands
5. SWE-agent
```

Chiến lược đúng:

```text
Aider        -> Apply loop
Spotless     -> Auto-fix hygiene
Checkstyle   -> Block hygiene violation
Gemini CLI   -> Event stream/context/checkpoint
OpenHands    -> Control Tower
SWE-agent    -> Trajectory archive
```

Câu chốt:

```text
Maika không nên chỉ nhắc agent làm đúng.
Maika phải ghi lại, kiểm tra, và chặn agent khi nó chưa chứng minh đã làm đúng.
```

Đặc biệt với bài học “không import thừa”:

```text
Không import thừa
-> code_hygiene mandatory rule
-> post-edit hygiene check
-> Spotless/Checkstyle gate
-> APPLY_TRACE evidence
-> final gate
```

Khi đó, agent không cần “nhớ” nữa. Nó bị framework buộc phải kiểm tra.
