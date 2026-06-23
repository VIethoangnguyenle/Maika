# UA/Codebase Skill-Habit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reshape how `codebase-explorer` and `architecture-reviewer` consume UA vs Codebase MCP — codebase-memory never shapes architecture, UA is primary for architecture questions — by editing skill content into cue-based habits, plus one minimal `R-Tool-5` evidence clause.

**Architecture:** This is documentation/prompt-engineering work on Maika's skill template files (`.maika/skills/*/SKILL.md`) and one rules file (`.maika/rules/rules-tool.md`). There is no runtime code. The "tests" are Python guard tests under `cli/tests/` that assert the skill markdown contains the required content (template tool refs, no raw MCP names, required sections, new cue blocks) plus the existing skill-lint validator. Each task extends or adds a guard test (red), edits the markdown (green), then runs skill-lint + the platform suite to confirm nothing regressed.

**Tech Stack:** Python 3.10, pytest, Maika CLI (`cli/`), skill-lint (`.maika/tools/skill-lint/validate_skills.py`), Jinja-style `{{ tools.X }}` / `{{ platform.framework_root }}` template placeholders resolved at `maika init`.

**Spec:** `docs/superpowers/specs/2026-06-23-ua-codebase-skill-habit-design.md`

## Global Constraints

These apply to EVERY task. Copied from the spec + the existing protocol guard (`cli/tests/test_codebase_explorer_protocol.py`):

- **Template tool refs only.** Reference MCP ops as `{{ tools.<op> }}` — NEVER raw provider names (`mcp__understand-anything__...`, `mcp_understand-anything_...`, `mcp__codebase-memory-mcp__...`). The guard test `test_skill_has_no_raw_ua_tool_names` fails on raw names.
- **Keep all required protocol sections** in `codebase-explorer`: `Định tuyến theo độ cao`, `Cổng độ phức tạp`, `Golden Path`, `Bản đồ năng lực`, `Degradation`, `Source attribution`. Editing within a section is fine; deleting a section heading breaks `test_skill_has_protocol_sections`.
- **Keep skill-lint headings.** Both skills currently PASS skill-lint. Do not rename/remove the required headings (`Mục tiêu`, `Khi nào dùng`, `Khi nào KHÔNG sử dụng`, `Quy trình`, `Output/Đầu ra`). Pre-existing FAILs (db-explorer, requirement-analyst, spec-extract) are unrelated — do NOT touch them.
- **Surgical edits.** Touch only the lines the spec calls for. Match existing Vietnamese prose style. No refactor of adjacent content.
- **Net-negative complexity.** No new rule/gate beyond the single R-Tool-5 clause (§5.5 of spec). The `R-Tool-5` change is additive (one clause), not a gate flip.
- **UA ops resolve on all platforms already** — `domain_overview/domain_flow/domain_relationships` map in `cli/platforms/{claude_code,antigravity,codex,generic}.py` and are covered by `cli/tests/test_platforms.py`. Do not add new tool keys.

---

## File Structure

| File | Responsibility | Action |
|---|---|---|
| `.maika/skills/codebase-explorer/SKILL.md` | Exploration habit: cue cards, remove hedge, UA-friendly output schema | Modify |
| `.maika/skills/architecture-reviewer/SKILL.md` | Arch-review habit: UA-shapes / codebase-verifies in Bước 4 & 6, UA as active probe | Modify |
| `.maika/rules/rules-tool.md` | `R-Tool-5` parallel evidence clause for architecture-facts | Modify |
| `cli/tests/test_codebase_explorer_protocol.py` | Guard for codebase-explorer content | Modify (extend) |
| `cli/tests/test_architecture_reviewer_protocol.py` | Guard for architecture-reviewer content | Create |
| `cli/tests/test_rules_tool_evidence.py` | Guard for R-Tool-5 parallel-evidence clause | Create |
| `docs/superpowers/specs/2026-06-23-...-design.md` (§6.6) | Behavioral acceptance scenario (manual) | Reference only |

Task order: **Task 1** (codebase-explorer) → **Task 2** (architecture-reviewer) → **Task 3** (R-Tool-5) → **Task 4** (full verify + manual behavioral scenario). Tasks 1–3 are independent edits; each is its own red→green→commit cycle. Task 4 is the integration gate.

---

### Task 1: codebase-explorer — Cue Cards, remove "structured-first" hedge, UA-friendly output schema

**Files:**
- Modify: `.maika/skills/codebase-explorer/SKILL.md` (section `### Định tuyến theo độ cao`, ~lines 42-49; output block, ~lines 124-148)
- Test: `cli/tests/test_codebase_explorer_protocol.py`

**Interfaces:**
- Consumes: existing `{{ tools.domain_overview }}`, `{{ tools.domain_flow }}`, `{{ tools.domain_relationships }}`, `{{ tools.search_code }}`, `{{ tools.get_symbol }}`, `{{ tools.read_file }}`, `{{ tools.trace_flow }}`, `{{ tools.get_dependencies }}`, `{{ tools.find_blast_radius }}`.
- Produces: a `#### Cue Cards` block (markdown table) inside `Định tuyến theo độ cao`; the hedge paragraph replaced; output schema note allowing UA identifiers.

- [ ] **Step 1: Write the failing test** — append to `cli/tests/test_codebase_explorer_protocol.py`:

```python
def test_skill_has_cue_cards_block():
    text = _text()
    assert "Cue Cards" in text, "missing Cue Cards habit block"
    # cue table must bind a base-class rabbit-hole symptom to a UA routine
    assert "base/abstract class" in text or "BaseHandler" in text
    assert "{{ tools.domain_flow }}" in text


def test_skill_dropped_structured_first_hedge():
    text = _text()
    assert 'Quy tắc tinh chỉnh "structured-first"' not in text, (
        "old structured-first hedge still present — it pulls agent back to codebase"
    )


def test_output_schema_allows_ua_identifier():
    text = _text()
    # entry-point / integration components may be sourced from UA, not only node_id
    assert "identifier kiểu UA" in text or "UA identifier" in text
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `cd /home/zane/Desktop/Maika && python3 -m pytest cli/tests/test_codebase_explorer_protocol.py -k "cue_cards or structured_first_hedge or ua_identifier" -v`
Expected: 3 FAIL (`Cue Cards` absent, hedge still present, UA-identifier note absent).

- [ ] **Step 3: Insert the Cue Cards block** — in `.maika/skills/codebase-explorer/SKILL.md`, find the two altitude bullets ending with `...{{ tools.find_blast_radius }}.` and insert AFTER them, BEFORE the `Quy tắc tinh chỉnh` paragraph:

```markdown

#### Cue Cards (phản xạ theo triệu chứng — CUE → ROUTINE → REWARD)

Thói quen được kích bằng triệu chứng gặp *trong lúc làm*, không bằng nguyên tắc trừu tượng:

| CUE (agent nhận ra) | ROUTINE (phản xạ) | REWARD |
|---|---|---|
| Sắp `{{ tools.trace_flow }}`/`{{ tools.get_dependencies }}` vào **base/abstract class nhiều impl** (BaseHandler…) | DỪNG codebase → `{{ tools.domain_flow }}` (UA) | Flow human-readable, bỏ qua hàng chục lớp con nhiễu |
| Call-chain vừa chạm `@KafkaListener`/gRPC stub rồi **đứt lạnh** | Leo thang `{{ tools.domain_flow }}` / `{{ tools.domain_relationships }}` (UA) | Thấy service nói chuyện với nhau ra sao |
| **Chưa biết entry point** (REST? gRPC? Kafka?) | `{{ tools.domain_overview }}` → `{{ tools.domain_flow }}` (UA) **trước** mọi grep | Định vị entry đúng, không suy luận từ Controller |
| Đã có **file/symbol cụ thể, localized, sửa 1 hàm** | Codebase thẳng (`{{ tools.search_code }}` → `{{ tools.get_symbol }}` → `{{ tools.read_file }}`) | Không tốn UA overhead |
```

- [ ] **Step 4: Replace the hedge paragraph** — in the same file, replace this exact block:

```markdown
Quy tắc tinh chỉnh "structured-first": static call-chain vẫn dùng `{{ tools.trace_flow }}` (Codebase) làm chính; **nhưng** khi luồng đứt ở ranh giới async → leo thang sang `{{ tools.domain_flow }}` (UA). Agent không bỏ qua provider có cấu trúc chỉ vì grep cho cảm giác nhanh hơn.
```

with:

```markdown
Codebase là chính cho static-trace **nội-service**. Nhưng khoảnh khắc câu hỏi trở thành *"flow này bắt đầu ở đâu / service nói chuyện ra sao"* thì đó là độ-cao UA — nhận ra bằng **Cue Cards** ở trên, đừng để phí vài call rồi mới leo thang. Codebase **không** dùng để định hình/kết luận kiến trúc; UA luôn ưu tiên cho câu hỏi kiến trúc.
```

- [ ] **Step 5: Make the output schema reward UA identifiers** — replace the `> [!IMPORTANT]` note under section `## 4. Output` (the one starting `> Luôn ghi kèm \`identifier\` (node_id hoặc file path)`):

```markdown
> [!IMPORTANT]
> Luôn ghi kèm `identifier` (node_id hoặc file path) cho mỗi component quan trọng.
> Điều này cho phép `architecture-reviewer` và OpenSpec dùng `{{ tools.read_file }}(identifier)` để đọc code thực tế mà không cần search lại.
```

with:

```markdown
> [!IMPORTANT]
> Ghi kèm `identifier` cho mỗi component quan trọng. **identifier kiểu UA** (tên domain / flow / entry-point) đứng **ngang hàng** `node_id` — mục *Entry points* và *Integration / event / job* ghi nguồn từ UA là hợp lệ và được khuyến khích.
> Với component cần đọc code chi tiết downstream, vẫn nên kèm `node_id`/file-path để `architecture-reviewer` và OpenSpec gọi `{{ tools.read_file }}(identifier)` trực tiếp.
```

- [ ] **Step 6: Run the new tests + existing guard to verify green**

Run: `cd /home/zane/Desktop/Maika && python3 -m pytest cli/tests/test_codebase_explorer_protocol.py -v`
Expected: ALL PASS (new 3 + existing `test_skill_references_ua_domain_ops_via_template`, `test_skill_has_no_raw_ua_tool_names`, `test_skill_has_protocol_sections`).

- [ ] **Step 7: Run skill-lint to confirm codebase-explorer still PASS**

Run: `cd /home/zane/Desktop/Maika && python3 .maika/tools/skill-lint/validate_skills.py .maika/skills 2>&1 | grep codebase-explorer`
Expected: line ends with `PASS`.

- [ ] **Step 8: Commit**

```bash
rtk git add .maika/skills/codebase-explorer/SKILL.md cli/tests/test_codebase_explorer_protocol.py
rtk git commit -m "$(printf 'feat(codebase-explorer): cue-card habits + drop structured-first hedge + UA-friendly output\n\nCo-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>')"
```

---

### Task 2: architecture-reviewer — UA shapes / codebase verifies (Bước 4 & 6), UA as active probe

**Files:**
- Modify: `.maika/skills/architecture-reviewer/SKILL.md` (Bước 4 ~lines 197-213; Bước 6 ~lines 237-248; `Nguyên tắc Độ tin cậy` ~lines 116-138)
- Create: `cli/tests/test_architecture_reviewer_protocol.py`

**Interfaces:**
- Consumes: `{{ tools.domain_relationships }}`, `{{ tools.domain_flow }}` (newly introduced into this skill), plus existing `{{ tools.get_dependencies }}`, `{{ tools.trace_flow }}`, `{{ tools.find_blast_radius }}`, `{{ tools.read_file }}`.
- Produces: a `cli/tests/test_architecture_reviewer_protocol.py` guard mirroring the codebase-explorer guard shape (`RAW_UA` regex, `_text()` helper).

- [ ] **Step 1: Write the failing test** — create `cli/tests/test_architecture_reviewer_protocol.py`:

```python
"""Guard: architecture-reviewer uses UA as an active probe for topology, never raw UA names."""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL = REPO_ROOT / ".maika" / "skills" / "architecture-reviewer" / "SKILL.md"

RAW_UA = re.compile(r"mcp__understand-anything__|mcp_understand-anything_")


def _text():
    return SKILL.read_text(encoding="utf-8")


def test_step4_uses_ua_domain_ops_as_active_probe():
    text = _text()
    # boundary/topology/coupling questions must actively call UA, not just flag it
    assert "{{ tools.domain_relationships }}" in text, "Bước 4 không gọi UA domain_relationships"
    assert "{{ tools.domain_flow }}" in text, "Bước 4/6 không gọi UA domain_flow"


def test_no_raw_ua_tool_names():
    assert RAW_UA.search(_text()) is None, "skill hardcodes raw UA MCP tool name"


def test_ua_described_as_active_probe_not_only_flag():
    text = _text()
    assert "probe chủ động" in text, "UA vẫn bị mô tả chỉ là cờ confidence"


def test_codebase_must_not_shape_architecture():
    text = _text()
    assert "KHÔNG" in text and "định hình" in text, "thiếu doctrine: codebase không định hình kiến trúc"
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd /home/zane/Desktop/Maika && python3 -m pytest cli/tests/test_architecture_reviewer_protocol.py -v`
Expected: `test_step4_uses_ua_domain_ops_as_active_probe`, `test_ua_described_as_active_probe_not_only_flag`, `test_codebase_must_not_shape_architecture` FAIL; `test_no_raw_ua_tool_names` PASS (skill has no raw names yet).

- [ ] **Step 3: Rewrite Bước 4 boundary/topology block** — in `.maika/skills/architecture-reviewer/SKILL.md`, replace the body of `### Bước 4 — Kiểm tra boundary, ownership, topology, coupling` (items 1-4) with a UA-shapes / codebase-verifies framing. Replace this exact block:

```markdown
1. Boundary & ownership:
   - Yêu cầu có đẩy thêm trách nhiệm vào một module vốn không sở hữu domain đó không?
   - Có risk “trộn domain” vào cùng 1 module/service không?
   - Nếu có identifiers: `{{ tools.get_dependencies }}(identifier, direction='in')` → xem ai gọi vào module này.
2. Execution Context & Deployment Topology:
   - Yêu cầu này xử lý theo luồng Synchronous (API, Controller) hay Asynchronous (Kafka Consumer, Background Job, Scheduler)?
   - Cảnh báo BLOCKER nếu luồng Asynchronous (như Kafka Consumer) bị đặt nhầm vào các service thuần API, mà nên hướng về các service xử lý nền (ví dụ: `worker-service` hoặc module background tương đương).
3. Layering & Convention Enforcement:
```

with:

```markdown
> **Doctrine (đọc trước):** câu hỏi xuyên-service hoặc async là **UA-altitude** — kết luận topology/boundary **luôn lấy từ UA**. `{{ tools.find_blast_radius }}`/`{{ tools.get_dependencies }}` chỉ thấy method-call nội-service, **KHÔNG** thấy Kafka/gRPC và **KHÔNG** được dùng để định hình kiến trúc. Khi codebase mâu thuẫn một code-fact UA claim (vd không thấy gRPC stub) → ghi vào `AGENT_TRANSPARENCY` ("UA có thể stale ở X"), không tự override.

| Câu hỏi | UA định hình kết luận | Codebase chỉ xác nhận code-fact nội-service (tùy chọn) |
|---|---|---|
| Module **sở hữu** domain gì? Có trộn domain? | `{{ tools.domain_relationships }}` → ai sở hữu/đụng domain | `{{ tools.get_dependencies }}(identifier, direction='in')` check caller nội-service có thật |
| Luồng **Sync hay Async**? Kafka consumer đặt nhầm service? | `{{ tools.domain_flow }}` → entry Kafka/gRPC/REST | `{{ tools.trace_flow }}` xác nhận một logic nội-service |
| Coupling mới **xuyên service**? | `{{ tools.domain_relationships }}` → cạnh cross-service | `{{ tools.find_blast_radius }}` cho blast nội-service |

1. Boundary & ownership: dùng `{{ tools.domain_relationships }}` xác định ai sở hữu domain; cảnh báo nếu requirement đẩy trách nhiệm vào module không sở hữu domain đó (risk "trộn domain").
2. Execution Context & Deployment Topology: dùng `{{ tools.domain_flow }}` xác định luồng Synchronous (API/Controller) hay Asynchronous (Kafka Consumer/Job/Scheduler). Cảnh báo BLOCKER nếu luồng Asynchronous bị đặt nhầm vào service thuần API, mà nên hướng về service xử lý nền (ví dụ: `worker-service`).
3. Layering & Convention Enforcement:
```

- [ ] **Step 4: Add UA probe to Bước 6 hot-path** — replace the `1. Hiệu năng:` block under `### Bước 6 — Đánh giá non-functional (ở mức high-level)`:

```markdown
1. Hiệu năng:
   - Yêu cầu thêm call, join, IO hay tính toán trên đường nóng?
   - Có move công việc sang luồng async/background phù hợp không?
```

with:

```markdown
1. Hiệu năng:
   - Yêu cầu thêm call, join, IO hay tính toán trên đường nóng?
   - Có move công việc sang luồng async/background phù hợp không? Dùng `{{ tools.domain_flow }}` (UA) xác nhận điểm async thật sự nằm ở đâu **trước khi** nhận định hot-path — đừng đoán từ code nội-service.
```

- [ ] **Step 5: Reframe UA in "Nguyên tắc Độ tin cậy"** — replace the first bullet block under `## 5. Nguyên tắc Độ tin cậy`:

```markdown
Dựa vào `AGENT_TRANSPARENCY` + thực tế tool:

- **UA + db-explorer + codebase-explorer đều chạy ổn**:
```

with:

```markdown
Dựa vào `AGENT_TRANSPARENCY` + thực tế tool. **UA là nguồn probe chủ động cho câu hỏi boundary/topology** (Bước 4 & 6), không phải chỉ biến đo confidence — khi UA khả dụng mà Bước 4/6 không gọi nó cho câu hỏi cross-service, đó là **thiếu sót**, không phải lựa chọn. Logic confidence dưới đây giữ nguyên:

- **UA + db-explorer + codebase-explorer đều chạy ổn**:
```

- [ ] **Step 6: Run the guard to verify green**

Run: `cd /home/zane/Desktop/Maika && python3 -m pytest cli/tests/test_architecture_reviewer_protocol.py -v`
Expected: ALL 4 PASS.

- [ ] **Step 7: Run skill-lint to confirm architecture-reviewer still PASS**

Run: `cd /home/zane/Desktop/Maika && python3 .maika/tools/skill-lint/validate_skills.py .maika/skills 2>&1 | grep architecture-reviewer`
Expected: line ends with `PASS`.

- [ ] **Step 8: Commit**

```bash
rtk git add .maika/skills/architecture-reviewer/SKILL.md cli/tests/test_architecture_reviewer_protocol.py
rtk git commit -m "$(printf 'feat(architecture-reviewer): UA shapes topology, codebase only verifies code-facts (Bước 4 & 6)\n\nCo-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>')"
```

---

### Task 3: R-Tool-5 — parallel evidence path for architecture-facts

**Files:**
- Modify: `.maika/rules/rules-tool.md` (`### [CRITICAL] R-Tool-5`, ~lines 31-42)
- Create: `cli/tests/test_rules_tool_evidence.py`

**Interfaces:**
- Consumes: existing R-Tool-5 prose.
- Produces: `cli/tests/test_rules_tool_evidence.py` guard.

- [ ] **Step 1: Write the failing test** — create `cli/tests/test_rules_tool_evidence.py`:

```python
"""Guard: R-Tool-5 grants architecture-facts a parallel UA evidence path."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RULES = REPO_ROOT / ".maika" / "rules" / "rules-tool.md"


def _text():
    return RULES.read_text(encoding="utf-8")


def test_rtool5_has_architecture_facts_evidence_path():
    text = _text()
    assert "architecture-facts" in text, "R-Tool-5 thiếu đường evidence cho architecture-facts"
    # UA identifier counts as valid evidence without forcing node_id
    assert "UA identifier" in text or "identifier kiểu UA" in text


def test_rtool5_keeps_codefacts_kg_path():
    text = _text()
    # code-facts still require node_id + blast-radius via KG tools (unchanged)
    assert "code-facts" in text and "node_id" in text
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd /home/zane/Desktop/Maika && python3 -m pytest cli/tests/test_rules_tool_evidence.py -v`
Expected: `test_rtool5_has_architecture_facts_evidence_path` FAIL (term absent); `test_rtool5_keeps_codefacts_kg_path` may FAIL on `code-facts` literal.

- [ ] **Step 3: Add the parallel-evidence clause** — in `.maika/rules/rules-tool.md`, find the R-Tool-5 bullet that begins `- Khi cần codebase-facts: bằng chứng trong KNOWLEDGE_CHECKPOINT` and insert this block immediately AFTER that bullet (before the `get_node_source` bullet):

```markdown
- **Đường evidence song song theo loại fact** (để gate không kéo ngược habit UA-first, xem `codebase-explorer` / `architecture-reviewer`):
  - **architecture-facts** (domain ownership, entry point, ranh giới async/cross-service): bằng chứng hợp lệ = **UA identifier** (tên domain / flow / entry-point) + 1 dòng flow summary — *không* bắt buộc `node_id`.
  - **code-facts** (symbol, static call-chain nội-service): giữ nguyên — `node_id` + blast-radius qua KG tools.
  - Khi hai nguồn mâu thuẫn ở một code-fact: surface conflict vào `AGENT_TRANSPARENCY`, knowledge chính thắng (R-KL-3), **không** suppress.
```

- [ ] **Step 4: Run to verify green**

Run: `cd /home/zane/Desktop/Maika && python3 -m pytest cli/tests/test_rules_tool_evidence.py -v`
Expected: BOTH PASS.

- [ ] **Step 5: Commit**

```bash
rtk git add .maika/rules/rules-tool.md cli/tests/test_rules_tool_evidence.py
rtk git commit -m "$(printf 'feat(rules-tool): R-Tool-5 parallel evidence path for architecture-facts (UA identifier)\n\nCo-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>')"
```

---

### Task 4: Full verification gate + manual behavioral acceptance scenario

**Files:**
- Test: entire `cli/tests/` suite + skill-lint
- Reference: spec §6.6 (behavioral scenario), §6.7 (platform resolve)

**Interfaces:**
- Consumes: all edits from Tasks 1-3.
- Produces: a recorded verification result (paste outputs into the PR/commit body or `AGENT_TRANSPARENCY` of a test run).

- [ ] **Step 1: Run the full CLI test suite** (catches any regression in snapshots/platform resolution)

Run: `cd /home/zane/Desktop/Maika && python3 -m pytest cli/tests/ -q`
Expected: PASS, including `test_platforms.py` (UA ops resolve on claude-code/antigravity/codex/generic) and `test_snapshots.py` (structural tree unchanged — we added no files to `.maika/skills/`).

- [ ] **Step 2: Run skill-lint on the whole skills dir**

Run: `cd /home/zane/Desktop/Maika && python3 .maika/tools/skill-lint/validate_skills.py .maika/skills`
Expected: `codebase-explorer` PASS and `architecture-reviewer` PASS. The pre-existing 3 FAILs (db-explorer, requirement-analyst, spec-extract) are unchanged and out of scope — confirm the count is still `11/14 PASS`, not lower.

- [ ] **Step 3: Confirm UA ops resolve on all 3 target platforms** (spec §6.7 — already covered, just verify)

Run: `cd /home/zane/Desktop/Maika && python3 -m pytest cli/tests/test_platforms.py -k "ua or domain or tool" -v`
Expected: PASS. This proves the cue cards' `{{ tools.domain_* }}` refs resolve to non-null tool names on claude-code, antigravity, codex (not the raw placeholder, not empty). If any platform returns empty for a UA op, STOP — the cue card would point at a null tool; route that platform's cue to the Degradation branch instead.

- [ ] **Step 4: Manual behavioral acceptance scenario (spec §6.6)** — this CANNOT be a unit test; it needs a live repo with both UA + codebase-memory MCP and a real agent run. Record the result manually.

  Scenario: take the "Hủy/Duyệt lệnh" flow from `compare.md`. Run `codebase-explorer` against a requirement that traces it. Verify:
  - [ ] (a) Agent calls UA (`{{ tools.domain_overview }}` / `{{ tools.domain_flow }}`) **before** any static `{{ tools.trace_flow }}` — UA-first.
  - [ ] (b) Agent **avoids** the base-class rabbit hole (e.g. `BaseInitTransReqActionHandler`) — does not dump dozens of subclasses into context.
  - [ ] (c) `EXPLORE_CONTEXT.md` records entry point sourced from UA (Kafka/gRPC), not inferred from Controller.

  If the live run still bolts to codebase-first, the habit did not hold → the cue cards need to move closer to the exact decision step, or R-Tool-5 still contradicts. Log the outcome in the PR.

- [ ] **Step 5: Final commit / PR** (only if Steps 1-3 green; Step 4 result recorded)

```bash
rtk git status
# Steps 1-3 must be green; Step 4 outcome pasted into PR body.
```

---

## Self-Review

**1. Spec coverage:**
- §4.1 Cue Cards → Task 1 Step 3 ✓
- §4.2 remove hedge → Task 1 Step 4 ✓
- §4.3 output schema reward → Task 1 Step 5 ✓
- §5.1 Bước 4 UA-shapes → Task 2 Step 3 ✓
- §5.2 Bước 6 domain_flow → Task 2 Step 4 ✓
- §5.3 UA active probe in confidence → Task 2 Step 5 ✓
- §3/§5.1 codebase may falsify code-fact, surface conflict → Task 2 Step 3 doctrine note + Task 3 Step 3 conflict bullet ✓
- §5.5 R-Tool-5 parallel evidence → Task 3 ✓
- §6.1/§6.2 skill-lint PASS → Task 1 Step 7, Task 2 Step 7, Task 4 Step 2 ✓
- §6.3 R-Tool-5 clause → Task 3 ✓
- §6.5 degradation unchanged → Global Constraints + Task 4 Step 3 (null-tool guard) ✓
- §6.6 behavioral scenario → Task 4 Step 4 ✓
- §6.7 platform resolve → Task 4 Step 3 ✓

**2. Placeholder scan:** No "TBD"/"handle edge cases"/"similar to". Every edit shows exact old→new markdown. Behavioral scenario (Task 4 Step 4) is explicitly manual, not a hidden placeholder.

**3. Type consistency:** All tool refs use `{{ tools.<op> }}` with op names verified against `cli/platforms/base.py` ALLOWED ops. Guard test helper `_text()` and `RAW_UA` regex names are consistent across the three test files. Skill section headings referenced (`Bước 4`, `Bước 6`, `Nguyên tắc Độ tin cậy`, `Định tuyến theo độ cao`, output `[!IMPORTANT]`) match the current files read during planning.
