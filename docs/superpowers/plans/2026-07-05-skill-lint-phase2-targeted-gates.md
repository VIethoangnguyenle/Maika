# Skill-Lint Phase 2 Targeted Gates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate the remaining 5 allowlisted skills below 300 body lines, remove the allowlist, and add targeted deterministic gate-check validators for `knowledge-curator` and `spec-validator`.

**Architecture:** Extend the existing `.maika/tools/gate-check/` validator system instead of creating a new tool family. Migrate long skill bodies into one-level `references/` files with direct links and read/run intent in each SKILL.md. Keep Understand-Anything first for codebase exploration, with Codebase Memory supporting source-code detail after UA locates the domain/flow.

**Tech Stack:** Python stdlib + PyYAML already in repo, pytest, Markdown skill/reference files, existing `gate-check` CLI.

## Global Constraints

- No new dependency.
- Keep Vietnamese prose for new skill/docs text; technical identifiers stay English.
- Keep literal placeholders such as `{{ platform.framework_root }}` and `{{ tools.domain_flow }}` unchanged.
- Reference files must be one level deep from SKILL.md, directly linked from SKILL.md, and must not link to other `references/` files.
- Reference files over 100 lines must have `## Mục lục` within the first 30 lines.
- UA-first is mandatory for codebase exploration: Understand-Anything first, Codebase Memory second, grep last.
- Scope closes targeted A-2 only for `knowledge-curator` + `spec-validator`; do not close all A-2 skill/workflow gaps.
- Do not make `openspec-explore` a fixed workflow.
- Run commands with `python3` in this repo.
- Do not stage unrelated local cleanup files such as `bao_cao_loi.md` or `PanGPA.log`.

---

## File Structure

- `.maika/tools/gate-check/gates.py`: add deterministic validators and helpers.
- `.maika/tools/gate-check/cli.py`: add new validator names and `--against` argument for two-file coverage checks.
- `.maika/tools/gate-check/tests/test_gates.py`: add positive/negative tests and CLI exit-code tests.
- `cli/tests/test_skill_standard.py`: remove `BODY_LINE_ALLOWLIST` or set it to an empty set and keep the L3 test meaningful.
- `.maika/skills/architecture-reviewer/SKILL.md`: thin entrypoint under 300 lines.
- `.maika/skills/architecture-reviewer/references/*.md`: migrated review details.
- `.maika/skills/knowledge-curator/SKILL.md`: thin entrypoint under 300 lines with exact gate-check commands.
- `.maika/skills/knowledge-curator/references/*.md`: migrated lifecycle details.
- `.maika/skills/openspec-explore/SKILL.md`: thin high-freedom entrypoint under 300 lines.
- `.maika/skills/openspec-explore/references/*.md`: migrated explore examples/guidance.
- `.maika/skills/requirement-analyst/SKILL.md`: thin entrypoint under 300 lines with UA-first open-question rule.
- `.maika/skills/requirement-analyst/references/*.md`: migrated schema/process/gotchas.
- `.maika/skills/spec-validator/SKILL.md`: thin entrypoint under 300 lines with exact gate-check commands.
- `.maika/skills/spec-validator/references/*.md`: migrated validator algorithms/details.
- `.maika/skills/skill-index.yaml`: regenerate from frontmatter.
- `cli/tests/snapshots/*.txt`: refresh only if scaffold tree changes.

---

### Task 1: Add `reset-ready`, `ac-coverage`, and `integration-coverage` gate-check validators

**Files:**
- Modify: `.maika/tools/gate-check/gates.py`
- Modify: `.maika/tools/gate-check/cli.py`
- Modify: `.maika/tools/gate-check/tests/test_gates.py`

**Interfaces:**
- Consumes: existing `Result`, `_section_text`, `validate_teaching_moment`, `validate_archive_ready`.
- Produces:
  - `validate_reset_ready(text: str) -> Result`
  - `validate_ac_coverage(requirement_text: str, spec_text: str = "") -> Result`
  - `validate_integration_coverage(requirement_text: str, spec_text: str = "") -> Result`
  - CLI: `gate-check reset-ready FILE`
  - CLI: `gate-check ac-coverage REQUIREMENT --against TASKS_OR_SPEC`
  - CLI: `gate-check integration-coverage REQUIREMENT --against TASKS_OR_SPEC`

- [ ] **Step 1: Add failing tests for `reset-ready`**

Append this block after `test_cli_archive_ready_exit_codes` in `.maika/tools/gate-check/tests/test_gates.py`:

```python

def _reset_doc(phase_state="completed", teaching_status="none", note="nothing to capture"):
    return (
        "# AGENT_TRANSPARENCY\n\n"
        "## Phase State\n\n"
        "```\n"
        f"phase_state: {phase_state}\n"
        "```\n\n"
        "## Teaching Moment Check\n\n"
        f"status: {teaching_status}\n"
        f"note: {note}\n"
        "target_updates:\n"
        "warn:\n"
        "reason:\n"
    )


def test_reset_ready_passes_completed_cancelled_or_stashed():
    assert g.validate_reset_ready(_reset_doc("completed")).ok is True
    assert g.validate_reset_ready(_reset_doc("cancelled")).ok is True
    assert g.validate_reset_ready(_reset_doc("stashed")).ok is True


def test_reset_ready_blocks_applying_or_blocked_state():
    applying = g.validate_reset_ready(_reset_doc("applying"))
    assert applying.ok is False
    assert "completed, cancelled, or stashed" in applying.reason
    blocked = g.validate_reset_ready(_reset_doc("blocked-by-arch"))
    assert blocked.ok is False
    assert "blocked-by-arch" in blocked.reason


def test_reset_ready_requires_teaching_moment_check():
    text = "# AGENT_TRANSPARENCY\n\n## Phase State\n\nphase_state: completed\n"
    result = g.validate_reset_ready(text)
    assert result.ok is False
    assert "Teaching Moment" in result.reason


def test_cli_reset_ready_exit_codes(tmp_path):
    import importlib.util
    cli_mod = Path(__file__).resolve().parents[1] / "cli.py"
    spec = importlib.util.spec_from_file_location("cli", cli_mod)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)

    f = tmp_path / "AGENT_TRANSPARENCY.md"
    f.write_text(_reset_doc("completed"), encoding="utf-8")
    assert cli.main(["reset-ready", str(f)]) == 0
    f.write_text(_reset_doc("applying"), encoding="utf-8")
    assert cli.main(["reset-ready", str(f)]) == 1
```

- [ ] **Step 2: Run reset-ready tests and confirm they fail**

Run: `python3 -m pytest .maika/tools/gate-check/tests/test_gates.py -k reset_ready -q`

Expected: FAIL with `AttributeError: module 'gates' has no attribute 'validate_reset_ready'` or CLI parser rejecting `reset-ready`.

- [ ] **Step 3: Add failing tests for AC and integration coverage**

Append this block after the reset-ready tests:

```python

REQ_WITH_AC = """# REQUIREMENT

## Acceptance Criteria

- User can export monthly settlement report
- API returns validation error for missing account id
"""

SPEC_COVERS_AC = """# tasks

- Implement monthly settlement report export
- Add validation error when account id is missing
"""

SPEC_MISSES_AC = """# tasks

- Implement monthly settlement report export
"""

REQ_WITH_INTEGRATION = """# REQUIREMENT

## Integrations & Field Mapping

### Integration: Partner KYC API

- endpoint: /kyc/check
"""

SPEC_COVERS_INTEGRATION = """# tasks

- Add Partner KYC API adapter for /kyc/check
"""

SPEC_WITHOUT_INTEGRATION = """# tasks

- Update local validation copy
"""


def test_ac_coverage_passes_when_all_ac_terms_are_in_spec():
    assert g.validate_ac_coverage(REQ_WITH_AC, SPEC_COVERS_AC).ok is True


def test_ac_coverage_fails_when_an_ac_is_uncovered():
    result = g.validate_ac_coverage(REQ_WITH_AC, SPEC_MISSES_AC)
    assert result.ok is False
    assert "missing account id" in result.reason


def test_ac_coverage_skips_when_requirement_has_no_ac_section():
    assert g.validate_ac_coverage("# REQUIREMENT\n\nNo AC here\n", SPEC_MISSES_AC).ok is True


def test_integration_coverage_passes_when_integration_is_in_spec():
    assert g.validate_integration_coverage(REQ_WITH_INTEGRATION, SPEC_COVERS_INTEGRATION).ok is True


def test_integration_coverage_fails_when_integration_is_uncovered():
    result = g.validate_integration_coverage(REQ_WITH_INTEGRATION, SPEC_WITHOUT_INTEGRATION)
    assert result.ok is False
    assert "Partner KYC API" in result.reason


def test_cli_coverage_checks_require_against_file(tmp_path):
    import importlib.util
    cli_mod = Path(__file__).resolve().parents[1] / "cli.py"
    spec = importlib.util.spec_from_file_location("cli", cli_mod)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)

    req = tmp_path / "REQUIREMENT.md"
    tasks = tmp_path / "tasks.md"
    req.write_text(REQ_WITH_AC, encoding="utf-8")
    tasks.write_text(SPEC_COVERS_AC, encoding="utf-8")
    assert cli.main(["ac-coverage", str(req), "--against", str(tasks)]) == 0
    assert cli.main(["ac-coverage", str(req)]) == 2
```

- [ ] **Step 4: Run coverage tests and confirm they fail**

Run: `python3 -m pytest .maika/tools/gate-check/tests/test_gates.py -k "coverage" -q`

Expected: FAIL with missing validator attributes or missing CLI `--against` support.

- [ ] **Step 5: Implement validators in `gates.py`**

Add this code after `validate_archive_ready` and before `validate_context_request`:

```python
_RESET_ALLOWED = {"completed", "cancelled", "stashed"}
_WORD = re.compile(r"[A-Za-z0-9_\-/]+", re.IGNORECASE)
_STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "when", "then",
    "user", "system", "can", "must", "should", "error", "validation",
    "api", "id", "missing", "returns",
}


def validate_reset_ready(text: str) -> Result:
    """Refuse destructive active-context reset unless the task is closed or stashed
    and the Teaching Moment Check is structurally valid."""
    m = re.search(_SECTION.format(name=re.escape("Phase State")), text, re.DOTALL | re.IGNORECASE)
    section = m.group(1) if m else ""
    ps = re.search(r"phase_state:\s*(\S+)", section)
    phase_state = ps.group(1).strip() if ps else ""
    if phase_state in _ARCHIVE_BLOCKED:
        return Result(False, f"reset blocked: phase_state={phase_state} — resolve the blocker first")
    if phase_state not in _RESET_ALLOWED:
        return Result(False, "reset requires phase_state completed, cancelled, or stashed")
    tm = validate_teaching_moment(text)
    if not tm.ok:
        return Result(False, f"reset requires valid Teaching Moment Check: {tm.reason}")
    return Result(True)


def _heading_section(text: str, heading: str) -> str:
    pattern = re.compile(
        rf"^##+\s+.*{re.escape(heading)}.*\n(.*?)(?=\n##+\s|\Z)",
        re.DOTALL | re.IGNORECASE | re.MULTILINE,
    )
    match = pattern.search(text)
    return match.group(1).strip() if match else ""


def _bullets(section: str):
    items = []
    for line in section.splitlines():
        stripped = line.strip()
        if stripped.startswith(("- ", "* ")):
            value = stripped[2:].strip()
            if value and not value.startswith("<!--"):
                items.append(value)
    return items


def _keywords(text: str):
    words = {w.lower() for w in _WORD.findall(text)}
    return {w for w in words if len(w) >= 4 and w not in _STOPWORDS}


def _covered(item: str, spec_text: str) -> bool:
    item_words = _keywords(item)
    if not item_words:
        return True
    spec_words = _keywords(spec_text)
    needed = 1 if len(item_words) <= 2 else max(2, min(4, len(item_words)))
    return len(item_words.intersection(spec_words)) >= needed


def validate_ac_coverage(requirement_text: str, spec_text: str = "") -> Result:
    section = _heading_section(requirement_text, "Acceptance Criteria")
    items = _bullets(section)
    if not items:
        return Result(True)
    missing = [item for item in items if not _covered(item, spec_text)]
    if missing:
        return Result(False, "uncovered AC: " + "; ".join(missing))
    return Result(True)


def validate_integration_coverage(requirement_text: str, spec_text: str = "") -> Result:
    section = _heading_section(requirement_text, "Integrations")
    if not section:
        return Result(True)
    items = []
    for line in section.splitlines():
        stripped = line.strip()
        heading = re.match(r"^###+\s+Integration:\s*(.+)$", stripped, re.IGNORECASE)
        if heading:
            items.append(heading.group(1).strip())
        elif stripped.startswith("- Integration:"):
            items.append(stripped.split(":", 1)[1].strip())
    if not items:
        return Result(True)
    missing = [item for item in items if not _covered(item, spec_text)]
    if missing:
        return Result(False, "uncovered integration: " + "; ".join(missing))
    return Result(True)
```

- [ ] **Step 6: Extend CLI validator map and `--against` support**

In `.maika/tools/gate-check/cli.py`, update `VALIDATORS`:

```python
    "archive-ready": "validate_archive_ready",
    "reset-ready": "validate_reset_ready",
    "ac-coverage": "validate_ac_coverage",
    "integration-coverage": "validate_integration_coverage",
```

Add an optional argument after `parser.add_argument("--artifact-type")`:

```python
    parser.add_argument("--against")
```

Replace the validator call block:

```python
    res = getattr(g, VALIDATORS[args.gate])(text, **kwargs)
```

with:

```python
    if args.gate in {"ac-coverage", "integration-coverage"}:
        if not args.against:
            print("FAIL — --against is required for coverage checks")
            return 2
        other = Path(args.against).read_text(encoding="utf-8")
        res = getattr(g, VALIDATORS[args.gate])(text, other, **kwargs)
    else:
        res = getattr(g, VALIDATORS[args.gate])(text, **kwargs)
```

- [ ] **Step 7: Run gate-check test subset**

Run: `python3 -m pytest .maika/tools/gate-check/tests/test_gates.py -k "reset_ready or coverage" -q`

Expected: all selected tests PASS.

- [ ] **Step 8: Run all gate-check tests**

Run: `python3 -m pytest .maika/tools/gate-check/tests/test_gates.py -q`

Expected: all tests PASS.

- [ ] **Step 9: Commit**

```bash
git add .maika/tools/gate-check/gates.py .maika/tools/gate-check/cli.py .maika/tools/gate-check/tests/test_gates.py
git commit -m "feat(gate-check): add reset and spec coverage validators"
```

---

### Task 2: Migrate `architecture-reviewer` below 300 lines

**Files:**
- Modify: `.maika/skills/architecture-reviewer/SKILL.md`
- Create: `.maika/skills/architecture-reviewer/references/review-flow-guide.md`
- Create: `.maika/skills/architecture-reviewer/references/ua-boundary-doctrine.md`
- Create: `.maika/skills/architecture-reviewer/references/infra-tdd-trigger.md`
- Create: `.maika/skills/architecture-reviewer/references/contract-completeness-check.md`
- Create: `.maika/skills/architecture-reviewer/references/gotchas.md`

**Interfaces:**
- Consumes: existing `architecture-reviewer` frontmatter.
- Produces: `architecture-reviewer` SKILL.md body ≤ 300 and reference files directly linked from SKILL.md.

- [ ] **Step 1: Create reference directory**

Run: `mkdir -p .maika/skills/architecture-reviewer/references`

Expected: directory exists.

- [ ] **Step 2: Move detailed review flow into `review-flow-guide.md`**

Create `.maika/skills/architecture-reviewer/references/review-flow-guide.md` with:

```markdown
# Review Flow Guide

> Tài liệu tham khảo cho `architecture-reviewer`. Read when executing the detailed 7-step architecture review flow.

## Mục lục

- Bước 1 — Kiểm tra trạng thái tool & khung tin cậy
- Bước 2 — Tóm tắt kiến trúc hiện tại
- Bước 3 — Đối chiếu As-is / To-be
- Bước 4 — Boundary, ownership, topology, coupling
- Bước 5 — Tác động dữ liệu
- Bước 6 — Non-functional review
- Bước 7 — Tổng hợp đánh giá

## Bước 1 — Kiểm tra trạng thái tool & khung tin cậy

1. Đọc `{{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md`.
2. Xác định trạng thái UA, db-explorer, codebase-explorer.
3. Đặt Độ tin cậy tối đa khả dĩ và ghi rõ limitation.

## Bước 2 — Tóm tắt kiến trúc hiện tại

1. Đọc `EXPLORE_CONTEXT.md` và `knowledge-snapshot.md`.
2. Xác định service/module chính, integration, database/schema.
3. Nếu có identifier, dùng `{{ tools.read_file }}` và `{{ tools.get_dependencies }}` để verify code-fact nội-service.

## Bước 3 — Đối chiếu As-is / To-be

1. Dựa trên REQUIREMENT.md, map flow hiện tại và flow to-be.
2. Nếu có identifier, dùng `{{ tools.find_blast_radius }}`, `{{ tools.read_file }}`, `{{ tools.trace_flow }}` cho logic nội-service.
3. Ghi alignment và mismatch.

## Bước 4 — Boundary, ownership, topology, coupling

1. Boundary & ownership: dùng `{{ tools.domain_relationships }}` để xác định domain owner.
2. Execution topology: dùng `{{ tools.domain_flow }}` để xác định REST/gRPC/Kafka/job.
3. Layering: đối chiếu `conventions.yaml` và `knowledge-snapshot.md`.
4. Coupling: flag phụ thuộc mới giữa module/service vốn độc lập.

## Bước 5 — Tác động dữ liệu

1. Dựa trên `db-explorer`, kiểm schema, constraint, migration, lịch sử.
2. Nếu dữ liệu là trọng tâm mà thiếu db-explorer, flag risk và hạ confidence.

## Bước 6 — Non-functional review

1. Hiệu năng: call/join/IO/hot path mới.
2. Độ tin cậy: dependency mới trên critical path.
3. Observability: logging/metrics/tracing cho luồng đổi mới.

## Bước 7 — Tổng hợp đánh giá

Ghi section `Đánh giá kiến trúc` vào `EXPLORE_CONTEXT.md` với điểm phù hợp, rủi ro, severity LOW/MEDIUM/HIGH/BLOCKER, hướng xử lý high-level, câu hỏi còn cần trả lời.
```

- [ ] **Step 3: Move UA doctrine into `ua-boundary-doctrine.md`**

Create `.maika/skills/architecture-reviewer/references/ua-boundary-doctrine.md` with:

```markdown
# UA Boundary Doctrine

> Tài liệu tham khảo cho `architecture-reviewer`. Read before making boundary, topology, async, Kafka, gRPC, or cross-service conclusions.

## Mục lục

- Doctrine
- Mapping câu hỏi sang tool
- Stale UA handling

## Doctrine

Câu hỏi xuyên-service hoặc async là UA-altitude. Kết luận topology/boundary luôn lấy từ Understand-Anything trước.

`{{ tools.find_blast_radius }}` và `{{ tools.get_dependencies }}` chỉ thấy method-call nội-service, không đủ để định hình Kafka/gRPC/cross-service topology.

## Mapping câu hỏi sang tool

| Câu hỏi | UA định hình kết luận | Codebase Memory hỗ trợ |
|---|---|---|
| Module sở hữu domain gì? | `{{ tools.domain_relationships }}` | `{{ tools.get_dependencies }}` check caller nội-service |
| Luồng sync/async? | `{{ tools.domain_flow }}` | `{{ tools.trace_flow }}` xác nhận logic nội-service |
| Coupling xuyên service? | `{{ tools.domain_relationships }}` | `{{ tools.find_blast_radius }}` cho blast nội-service |

## Stale UA handling

Khi codebase mâu thuẫn một code-fact UA claim, ghi vào `AGENT_TRANSPARENCY.md` rằng UA có thể stale ở điểm đó. Không tự override topology bằng grep.
```

- [ ] **Step 4: Move M5, M6, gotchas into reference files**

Create `.maika/skills/architecture-reviewer/references/infra-tdd-trigger.md`:

```markdown
# Infra-TDD Auto Trigger

> Tài liệu tham khảo cho `architecture-reviewer`. Read after Bước 7 when review finds infrastructure, platform, integration, DB, or contract impact.

## Mục lục

- Trigger conditions
- Suggestion flow
- Non-trigger conditions

## Trigger conditions

Suggest `infra-tdd` when review result has HIGH/BLOCKER issue related to database schema, index, migration, platform topology, new service, Kafka topic, API contract, or external integration.

## Suggestion flow

1. Tell user: `[M5] Yêu cầu này có tác động hạ tầng. Khuyến nghị tạo TDD trước khi spec.`
2. Ask whether to run `/tdd`.
3. Write `[M5-INFRA-TDD] Đề xuất TDD vì: {reason}. User cần confirm.` to `AGENT_TRANSPARENCY.md`.
4. Do not auto-run `/tdd`.

## Non-trigger conditions

Do not trigger for pure business logic, UI, validation, bugfix without schema/topology change, or internal refactor within one module.
```

Create `.maika/skills/architecture-reviewer/references/contract-completeness-check.md`:

```markdown
# Contract Completeness Check

> Tài liệu tham khảo cho `architecture-reviewer`. Read after Bước 7 and before final conclusion when REQUIREMENT.md has a Technical Design Contract.

## Mục lục

- Checks
- Output
- Skip conditions

## Checks

1. Section exists and has real content.
2. If `conventions.yaml` exists and is approved, compare selected protocol/pattern with conventions.
3. Contract has protocol/interface, request/message schema, and response/event schema.

## Output

All M6 checks are WARN only. Write `[M6] Contract Completeness: {PASS|WARN(n)} — {details}` to `AGENT_TRANSPARENCY.md`.

## Skip conditions

Skip when REQUIREMENT.md uses an old template without contract section, or task type is `refactor`.
```

Create `.maika/skills/architecture-reviewer/references/gotchas.md`:

```markdown
# Architecture Reviewer Gotchas

> Tài liệu tham khảo cho `architecture-reviewer`. Read when confidence, conventions, contract, or upstream-library questions appear.

## Gotchas

- **G1 knowledge-snapshot stale**: check `<!-- verified: YYYY-MM-DD -->`. If older than 30 days, treat as reference and cross-verify with UA graph.
- **G2 conventions draft**: use only approved `conventions.yaml`, not `conventions.draft.yaml`.
- **G3 M6 needs REQUIREMENT**: skip M6 when REQUIREMENT is empty or skeleton.
- **G4 upstream boundary**: do not propose changing upstream library contracts; warn only when downstream implementation diverges.
```

- [ ] **Step 5: Rewrite `architecture-reviewer/SKILL.md` as thin entrypoint**

Replace body after frontmatter with this text:

```markdown
# Architecture Reviewer — Đánh giá kiến trúc dựa trên trạng thái thực tế

## Mục tiêu

- Đối chiếu REQUIREMENT với kiến trúc hiện tại: service/module, DB, integration, boundary.
- Phát hiện xung đột kiến trúc, data risk, coupling, NFR risk.
- Ghi kết quả LOW / MEDIUM / HIGH / BLOCKER kèm Độ tin cậy.

Skill này không thiết kế kiến trúc mới từ đầu. Nó soi yêu cầu so với kiến trúc hiện hữu và nêu điểm cần xử lý trước khi spec/apply.

## Khi nào dùng

- REQUIREMENT.md đã tương đối ổn định.
- Đã có db-explorer/codebase-explorer hoặc limitation được ghi rõ.
- Trước OpenSpec `/opsx:propose` hoặc trước khi giao implementation.

## Khi nào KHÔNG sử dụng

- Không dùng như công cụ refactor code chi tiết.
- Không thay thế quyết định kiến trúc cấp tổ chức.
- Không dùng khi chưa có REQUIREMENT.md.
- Không dùng để validate spec đã sinh (→ spec-validator).

## Input / Output

Input chính:
- `{{ platform.framework_root }}/knowledge/active/REQUIREMENT.md`
- `{{ platform.framework_root }}/knowledge/active/EXPLORE_CONTEXT.md`
- `{{ platform.framework_root }}/knowledge/long-term/knowledge-snapshot.md`
- `{{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md`

Output: cập nhật `EXPLORE_CONTEXT.md` với section `### Đánh giá kiến trúc cho yêu cầu hiện tại (architecture-reviewer)`.

## Nguyên tắc Độ tin cậy

- UA + db-explorer + codebase-explorer đều chạy ổn → có thể CAO nếu evidence đủ.
- UA thiếu → tối đa TRUNG BÌNH cho topology/boundary.
- db-explorer thiếu → tối đa TRUNG BÌNH cho dữ liệu.
- Cả UA và db-explorer thiếu → không được đặt confidence CAO.

## UA-first invariant

Boundary/topology/cross-service/async conclusions must use Understand-Anything first:

- Run `{{ tools.domain_relationships }}` for ownership and cross-service dependency.
- Run `{{ tools.domain_flow }}` for REST/gRPC/Kafka/job topology.
- Use Codebase Memory only after UA locates the node/flow, to inspect source details.
- Use grep only as fallback. Codebase Memory failure does not mean UA is unavailable.

Read [references/ua-boundary-doctrine.md](references/ua-boundary-doctrine.md) before making topology, async, Kafka, gRPC, or cross-service conclusions.

## Quy trình mỏng

1. Check tool state and set confidence ceiling.
2. Summarize current architecture from REQUIREMENT, EXPLORE_CONTEXT, snapshot.
3. Compare As-is / To-be with current architecture.
4. Review boundary, ownership, topology, and coupling with UA-first.
5. Review data impact from db-explorer evidence.
6. Review NFR impact: performance, reliability, observability.
7. Write architecture assessment and suggested next action.

Read [references/review-flow-guide.md](references/review-flow-guide.md) when executing the full review flow.

## Optional checks

- Read [references/infra-tdd-trigger.md](references/infra-tdd-trigger.md) when review finds HIGH/BLOCKER infrastructure, platform, integration, DB, or contract impact.
- Read [references/contract-completeness-check.md](references/contract-completeness-check.md) when REQUIREMENT.md has a Technical Design Contract.
- Read [references/gotchas.md](references/gotchas.md) when confidence, conventions, contract, or upstream-library questions appear.

## Cập nhật AGENT_TRANSPARENCY

Ghi:
- `[x] architecture-reviewer`
- provider operations used, especially UA calls for boundary/topology.
- trạng thái db-explorer/codebase-explorer.
- Độ tin cậy kiến trúc tổng thể và lý do.
- BLOCKER action nếu có.
```

- [ ] **Step 6: Run skill lint for architecture-reviewer**

Run: `python3 -m pytest cli/tests/test_skill_standard.py -k architecture-reviewer -q`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add .maika/skills/architecture-reviewer/
git commit -m "refactor(architecture-reviewer): split review guides into references"
```

---

### Task 3: Migrate `knowledge-curator` below 300 lines and wire reset gate wording

**Files:**
- Modify: `.maika/skills/knowledge-curator/SKILL.md`
- Create: `.maika/skills/knowledge-curator/references/archive-active-context.md`
- Create: `.maika/skills/knowledge-curator/references/reset-active-context.md`
- Create: `.maika/skills/knowledge-curator/references/snapshot-promotion.md`
- Create: `.maika/skills/knowledge-curator/references/archive-rotation.md`

**Interfaces:**
- Consumes: Task 1 CLI `gate-check reset-ready`.
- Produces: `knowledge-curator` SKILL.md body ≤ 300 and deterministic reset/archive commands.

- [ ] **Step 1: Create lifecycle reference files**

Create `.maika/skills/knowledge-curator/references/archive-active-context.md`:

```markdown
# Archive Active Context

> Tài liệu tham khảo cho `knowledge-curator`. Read before archiving active context.

## Mục lục

- Pre-checks
- Status meanings
- Archive steps

## Pre-checks

Run:

```bash
python3 {{ platform.framework_root }}/tools/gate-check/cli.py archive-ready {{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md
python3 {{ platform.framework_root }}/tools/gate-check/cli.py teaching-moment {{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md
```

Exit non-zero aborts archive.

## Status meanings

- `completed`: apply done; update knowledge snapshot.
- `stashed`: paused; do not update snapshot.
- `cancelled`: abandoned; do not update snapshot.

## Archive steps

1. Create `{{ platform.framework_root }}/knowledge/archive/{ticket_id}/`.
2. Copy REQUIREMENT, EXPLORE_CONTEXT, AGENT_TRANSPARENCY, TOKEN_LOG if present, SESSION_OVERRIDE if present, `.session_state.json` if present, and `active/ideation/` if present.
3. Create ARCHIVE_META.md with ticket_id, archived_at, status, summary, phase_at_archive, stash_note if stashed, token_total_estimate.
4. Verify copied files can be read.
5. If status is `completed`, run snapshot update.
6. Report archive path.
```

Create `.maika/skills/knowledge-curator/references/reset-active-context.md`:

```markdown
# Reset Active Context

> Tài liệu tham khảo cho `knowledge-curator`. Read before resetting active context.

## Mục lục

- Pre-check
- Reset steps
- Ideation rule

## Pre-check

Run:

```bash
python3 {{ platform.framework_root }}/tools/gate-check/cli.py reset-ready {{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md
```

Exit non-zero aborts reset. Reset is destructive and requires phase_state `completed`, `cancelled`, or `stashed` plus a valid Teaching Moment Check.

## Reset steps

1. Copy templates into active REQUIREMENT, EXPLORE_CONTEXT, AGENT_TRANSPARENCY.
2. Reset TOKEN_LOG.md from template if present.
3. Remove SESSION_OVERRIDE.md and `.session_state.json`.
4. Report `Active context reset. Ready for new task.`

## Ideation rule

Do not delete active ideation drafts unless archive already copied them or user explicitly requested clearing ideation.
```

Create `.maika/skills/knowledge-curator/references/snapshot-promotion.md` with:

```markdown
# Snapshot Promotion

> Tài liệu tham khảo cho `knowledge-curator`. Read when updating `knowledge-snapshot.md` after a completed task.

## Mục lục

- Update steps
- Promotion criteria
- Store partitioning
- Stale confidence decay

## Update steps

1. Read EXPLORE_CONTEXT.md and AGENT_TRANSPARENCY.md for the completed task.
2. Classify each discovery with the Promotion Criteria table.
3. Promote reusable code/DB facts into `knowledge-snapshot.md` with metadata:
   `source:{ticket-id} seen:{YYYY-MM} verified:{YYYY-MM} status:active`.
4. If an older entry covers the same concept:
   - Same fact: update `verified`.
   - Contradiction: mark old entry `status:superseded`, add the new entry, and name the superseded source.
   - Unclear: mark old entry `status:outdated` and require manual verification.
5. Add a history row with ticket, date, and count of added/updated entries.

## Promotion criteria

| Bucket | Điều kiện | Hành động |
|---|---|---|
| PROMOTE -> snapshot | Direct DB/code evidence, reusable across tasks, not ticket-only context, not convention/DNA material | Add to the right snapshot section with metadata |
| REDIRECT -> conventions | Naming rule, coding style, design pattern boundary, folder/package structure | Propose update to `conventions.yaml` or `conventions.draft.yaml` |
| REDIRECT -> author-dna | Programming philosophy, reason for choosing a pattern, judgment principle | Propose update to `author-dna.yaml` or `author-dna.draft.yaml` |
| ARCHIVE only | Ticket-specific workaround, unresolved debate, narrow business-case context | Keep in archive EXPLORE_CONTEXT.md |
| DISCARD | Pure inference without evidence, duplicate of better snapshot entry, PII/secret | Do not store |

## Store partitioning

| Loại nội dung | Store | Example |
|---|---|---|
| Sự thật về hệ thống | `knowledge-snapshot.md` | Table has column, module calls module |
| Quy tắc viết code | `conventions.yaml` | Naming/package/style rule |
| Triết lý hoặc judgment principle | `author-dna.yaml` | Why a pattern is preferred |
| Bài học vận hành | agent memory | Incident or fix lesson |

Write conventions/DNA at pattern level. Concrete table/class names belong in evidence, not generic rule text. If a rule only applies to one table or class, treat it as a snapshot fact.

## Stale confidence decay

For each active snapshot entry:

- If `verified` is older than 90 days and the current task touches that area, update `verified` and keep `confidence:high`.
- If `verified` is older than 90 days and the current task does not touch that area, mark `confidence:low` without changing status.
- If `verified` is older than 180 days and confidence is already low, add `<!-- needs-reverify -->`.
- When using a stale entry, mention the stale status in output and cross-check with Understand-Anything before relying on it.
```

Create `.maika/skills/knowledge-curator/references/archive-rotation.md` with:

```markdown
# Archive Rotation

> Tài liệu tham khảo cho `knowledge-curator`. Read when archive count exceeds the retention threshold or cross-repo snapshot references are needed.

## Mục lục

- Rotate archive
- Transparency log rotation
- Cross-repo snapshot references
- Gotchas

## Rotate archive

Keep the most recent `keep_n=20` ticket folders. For older folders, append metadata to `ARCHIVE_LOG.md`, then remove the old folder only after the log write succeeds.

## Transparency log rotation

When archive runs, compact repeated bootstrap entries in active AGENT_TRANSPARENCY while preserving the full log in archive.

## Cross-repo snapshot references

Use relative paths from project root. Do not copy cross-repo snapshot content.

## Gotchas

- Sanitize ticket IDs before folder creation.
- Regex for bootstrap entries must support old and new formats.
- Reset must not clear ideation drafts unless explicitly archived or requested.
```

- [ ] **Step 2: Rewrite `knowledge-curator/SKILL.md` as thin entrypoint**

Keep the frontmatter. Replace the body after frontmatter with:

```markdown
# Knowledge Curator — Quản lý Vòng đời Knowledge

## Mục tiêu

- Archive context đã hoàn thành vào `{{ platform.framework_root }}/knowledge/archive/{ticket-id}/`.
- Reset `{{ platform.framework_root }}/knowledge/active/` về skeleton sạch.
- Cập nhật `knowledge-snapshot.md` với discovery tái sử dụng được.
- Rotate archive cũ khi vượt ngưỡng.

Skill này là lifecycle manager. Không sinh requirement, không review kiến trúc, không validate spec.

## Khi nào dùng

- `/task apply` hoàn thành thành công.
- User yêu cầu đóng task hoặc reset context.
- Bootstrap phát hiện conflict giữa active context và task mới, và user chọn reset.
- Archive vượt retention threshold.

## Khi nào KHÔNG sử dụng

- Task chưa hoàn thành và chưa sẵn sàng archive.
- Cần requirement/spec/architecture review.

## Commands bắt buộc

Before archive, run:

```bash
python3 {{ platform.framework_root }}/tools/gate-check/cli.py archive-ready {{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md
python3 {{ platform.framework_root }}/tools/gate-check/cli.py teaching-moment {{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md
```

Before reset, run:

```bash
python3 {{ platform.framework_root }}/tools/gate-check/cli.py reset-ready {{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md
```

Any non-zero exit aborts the operation and the reason must be shown to the user.

## Lifecycle surface

1. `archive_active_context(ticket_id, status="completed")`
2. `update_knowledge_snapshot(discoveries)` when status is `completed`
3. `push_to_agent_memory(ticket_id)` after snapshot update and before reset
4. `reset_active_context()`
5. `restore_from_archive(ticket_id)` when resuming
6. `rotate_archive(keep_n=20)` when archive grows too large

Read [references/archive-active-context.md](references/archive-active-context.md) before archiving.
Read [references/reset-active-context.md](references/reset-active-context.md) before resetting active context.
Read [references/snapshot-promotion.md](references/snapshot-promotion.md) before updating knowledge snapshot.
Read [references/m7-memory-push.md](references/m7-memory-push.md) before pushing task learnings to agent memory.
Read [references/archive-rotation.md](references/archive-rotation.md) before rotating archive or writing cross-repo snapshot pointers.

## Output

- Archive folder: `{{ platform.framework_root }}/knowledge/archive/{ticket-id}/`
- Snapshot update: `{{ platform.framework_root }}/knowledge/long-term/knowledge-snapshot.md`
- Reset active context: `{{ platform.framework_root }}/knowledge/active/`
- Transparency log update: `AGENT_TRANSPARENCY.md`

## Cập nhật AGENT_TRANSPARENCY

Ghi:
- `[x] knowledge-curator: archive_active_context({ticket_id})`
- `[x] knowledge-curator: update_knowledge_snapshot`
- `[x] knowledge-curator: reset_active_context`
- lỗi hoặc aborted gate nếu có.
```

- [ ] **Step 3: Run skill lint for knowledge-curator**

Run: `python3 -m pytest cli/tests/test_skill_standard.py -k knowledge-curator -q`

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add .maika/skills/knowledge-curator/
git commit -m "refactor(knowledge-curator): split lifecycle details into references"
```

---

### Task 4: Migrate `openspec-explore` below 300 lines

**Files:**
- Modify: `.maika/skills/openspec-explore/SKILL.md`
- Create: `.maika/skills/openspec-explore/references/openspec-awareness.md`
- Create: `.maika/skills/openspec-explore/references/explore-patterns.md`
- Create: `.maika/skills/openspec-explore/references/examples.md`

**Interfaces:**
- Consumes: existing `openspec-explore` stance.
- Produces: high-freedom SKILL.md body ≤ 300 with UA-first invariant preserved.

- [ ] **Step 1: Create reference files**

Create `.maika/skills/openspec-explore/references/openspec-awareness.md`:

```markdown
# OpenSpec Awareness

> Tài liệu tham khảo cho `openspec-explore`. Read when the discussion touches an active OpenSpec change or when insights should be captured into artifacts.

## Mục lục

- Check context
- No active change
- Active change
- Capture table

## Check context

Run `openspec list --json` when OpenSpec state matters.

Also check:
- `{{ platform.framework_root }}/knowledge/active/REQUIREMENT.md`
- `{{ platform.framework_root }}/knowledge/active/EXPLORE_CONTEXT.md`
- `{{ platform.framework_root }}/knowledge/long-term/knowledge-snapshot.md`

## No active change

Think freely. When insight crystallizes, offer to create a proposal. Do not pressure.

## Active change

Read proposal/design/tasks/spec artifacts for context and reference them naturally.

## Capture table

| Insight type | Where to capture |
|---|---|
| New requirement | Relevant capability spec file, for example `specs/billing/spec.md` |
| Design decision | `design.md` |
| Scope changed | `proposal.md` |
| New work | `tasks.md` |
| Assumption invalidated | relevant artifact |
```

Create `.maika/skills/openspec-explore/references/explore-patterns.md`:

```markdown
# Explore Patterns

> Tài liệu tham khảo cho `openspec-explore`. Read when the conversation needs deeper exploration, option comparison, or risk mapping.

## Mục lục

- Problem space
- Codebase investigation
- Compare options
- Visualize
- Risks and unknowns

## Problem space

Ask clarifying questions that emerge from the user's statement. Challenge assumptions and reframe when useful.

## Codebase investigation

If brainstorm touches code, run UA-first probe with `{{ tools.domain_overview }}` or `{{ tools.domain_flow }}` before asking code-answerable questions.

## Compare options

Build small comparison tables and recommend a path only when enough evidence exists.

## Visualize

Use ASCII diagrams for state machines, data flow, architecture sketches, and dependency comparisons.

## Risks and unknowns

Name what could go wrong, what is unknown, and whether a spike is needed.
```

Create `.maika/skills/openspec-explore/references/examples.md`:

```markdown
# Explore Examples

> Tài liệu tham khảo cho `openspec-explore`. Read only when needing examples of how to conduct explore-mode conversations.

## Mục lục

- Vague idea
- Specific problem
- Mid-implementation stuck point
- Option comparison

## Vague idea

Use spectrum framing. Example: awareness → coordination → sync for collaboration features.

## Specific problem

Read code/context first, summarize current flow, then ask which tangle is burning.

## Mid-implementation stuck point

Read existing change artifacts, identify the current task, trace involved components, then offer to update design or add a spike.

## Option comparison

Start from context constraints, then compare options. Recommend only when constraints make the answer clear.
```

- [ ] **Step 2: Rewrite `openspec-explore/SKILL.md` as thin entrypoint**

Keep frontmatter. Replace body after frontmatter with:

```markdown
# OpenSpec Explore — Thinking Partner

Enter explore mode. Think deeply. Visualize freely. Follow the conversation wherever it goes.

## Guardrails

- Explore mode is for thinking, not implementing.
- You may read files, search code, and investigate.
- You must not write code or implement features.
- If the user asks for implementation, remind them to exit explore mode and create/approve a change proposal first.
- Creating OpenSpec artifacts is allowed when the user asks; that captures thinking, not implementation.

## UA-first invariant

When brainstorm touches code, run UA-first probe (`{{ tools.domain_overview }}` / `{{ tools.domain_flow }}`) before asking user a code-answerable question. Use Codebase Memory after UA locates the node/flow. Use grep last.

## Mục tiêu

- Act as a thinking partner for ideas, investigation, and requirement clarification.
- Keep the conversation high-freedom: no fixed steps, no mandatory output, no funnel.

## Khi nào sử dụng

- User wants to brainstorm before a change.
- Idea is ambiguous and needs exploration.
- Implementation is stuck and design needs rethinking.

## Khi nào KHÔNG sử dụng

- Requirement is clear and needs formalization (→ requirement-analyst).
- Need generated technical spec/artifacts (→ openspec-propose).
- Need architecture review (→ architecture-reviewer).
- Need code implementation.

## Stance

- Curious, not prescriptive.
- Open threads, not interrogation.
- Adaptive and patient.
- Grounded: code-answerable questions go through UA-first probe.

Read [references/openspec-awareness.md](references/openspec-awareness.md) when OpenSpec state or artifact capture matters.
Read [references/explore-patterns.md](references/explore-patterns.md) when deeper exploration, codebase investigation, comparison, visualization, or risk mapping is needed.
Read [references/examples.md](references/examples.md) only when needing conversation examples.
```

- [ ] **Step 3: Run skill lint for openspec-explore**

Run: `python3 -m pytest cli/tests/test_skill_standard.py -k openspec-explore -q`

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add .maika/skills/openspec-explore/
git commit -m "refactor(openspec-explore): split explore examples into references"
```

---

### Task 5: Migrate `requirement-analyst` below 300 lines

**Files:**
- Modify: `.maika/skills/requirement-analyst/SKILL.md`
- Create: `.maika/skills/requirement-analyst/references/output-schema.md`
- Create: `.maika/skills/requirement-analyst/references/process-guide.md`
- Create: `.maika/skills/requirement-analyst/references/ua-open-question-filter.md`
- Create: `.maika/skills/requirement-analyst/references/gotchas.md`

**Interfaces:**
- Consumes: UA-first invariant from approved design.
- Produces: `requirement-analyst` body ≤ 300 with output/process details in references.

- [ ] **Step 1: Create reference files**

Create `.maika/skills/requirement-analyst/references/output-schema.md`:

```markdown
# REQUIREMENT Output Schema

> Tài liệu tham khảo cho `requirement-analyst`. Read when writing or checking the final REQUIREMENT.md shape.

## Mục lục

- Required sections
- Technical Design Contract
- Integrations & Field Mapping

## Required sections

- Metadata task
- Business context & động lực
- As-is / To-be
- Scope: in-scope and out-of-scope
- Acceptance Criteria
- Technical Design Contract
- Integrations & Field Mapping
- Assumptions
- Requirement issues / open questions
- Source notes when traceability is needed

## Technical Design Contract

Define protocol, endpoint/topic/service, request/message schema, response/event schema, and architecture constraints.

## Integrations & Field Mapping

For third-party API work, include integration name, direction, protocol/auth, endpoint/source doc, field mapping from third-party field to canonical field, transform intent, and unmapped fields mirrored into open questions.
```

Create `.maika/skills/requirement-analyst/references/process-guide.md`:

```markdown
# Requirement Analyst Process Guide

> Tài liệu tham khảo cho `requirement-analyst`. Read when executing the detailed 10-step flow.

## Mục lục

- Bước 1 — Thu thập nguồn
- Bước 2 — Xác định loại task
- Bước 3 — Business context
- Bước 4 — UA-first codebase probe
- Bước 5 — As-is / To-be
- Bước 6 — Scope
- Bước 7 — Acceptance Criteria
- Bước 8 — Technical Design Contract
- Bước 9 — Assumptions and Requirement Issues
- Bước 10 — Finalise REQUIREMENT.md

## Bước 1 — Thu thập nguồn

Read ticket description, comments, attachments, linked docs, and user clarifications. Use spec-extract for long docs.

## Bước 2 — Xác định loại task

Classify as `feature`, `fixbug`, `changerequest`, or `refactor`. If uncertain, mark as tentative.

## Bước 3 — Business context

Name who has the problem, what hurts, why now, and what done means from business view.

## Bước 4 — UA-first codebase probe

Run `{{ tools.domain_overview }}` and `{{ tools.domain_flow }}` before writing As-is or open questions that code can answer.

## Bước 5 — As-is / To-be

Separate current behavior from desired behavior. Use UA identifiers when code evidence exists.

## Bước 6 — Scope

List in-scope and out-of-scope modules, APIs, screens, jobs, events, data, and reports.

## Bước 7 — Acceptance Criteria

Normalize each AC into precondition, behavior, and observable result.

## Bước 8 — Technical Design Contract

Define protocol/interface and schemas. Read conventions/snapshot before assuming patterns.

## Bước 9 — Assumptions and Requirement Issues

Assumptions are unstated things being treated as true. Requirement issues are true business unknowns, not code-answerable questions.

## Bước 10 — Finalise REQUIREMENT.md

Ensure required sections exist, language is concise, and sources are traceable.
```

Create `.maika/skills/requirement-analyst/references/ua-open-question-filter.md`:

```markdown
# UA Open Question Filter

> Tài liệu tham khảo cho `requirement-analyst`. Read before asking the user an open question.

## Rule

Before writing any Open Question, classify it:

- Code-answerable: entry point, current race/lock behavior, existing approve/reject flow, existing API/event path. Resolve with UA-first probe.
- True business unknown: SLA, business rule, approver responsibility, priority, legal/compliance decision. Ask user.

## UA-first probe

Run `{{ tools.domain_overview }}` and `{{ tools.domain_flow }}` first. Use Codebase Memory after UA locates the relevant node/flow.

## Output

Code-answerable answers go into As-is, To-be delta, or Technical Design Contract. True business unknowns go into Requirement Issues.
```

Create `.maika/skills/requirement-analyst/references/gotchas.md`:

```markdown
# Requirement Analyst Gotchas

> Tài liệu tham khảo cho `requirement-analyst`. Read when parsing existing REQUIREMENT files or external docs.

## Gotchas

- CRLF/LF line endings: normalize before regex parsing.
- Skeleton detection: check section content, not just headings.
- Confluence conversion: macros may become noisy text; read raw first, clean after.
- Multi-ticket input: create one REQUIREMENT per ticket or ask user to choose one. Do not merge unrelated tickets.
```

- [ ] **Step 2: Rewrite `requirement-analyst/SKILL.md` as thin entrypoint**

Keep frontmatter. Replace body after frontmatter with:

```markdown
# Requirement Analyst — Chuẩn hoá REQUIREMENT từ ticket + tài liệu

## UA-first invariant

Trước khi hỏi user: câu hỏi code-trả-lời-được phải tự giải bằng UA-first probe (`{{ tools.domain_overview }}` / `{{ tools.domain_flow }}`). Chỉ unknown nghiệp vụ thật mới hỏi user. Codebase Memory hỗ trợ đọc logic node sau khi UA định vị flow.

## Mục tiêu

Biến ticket/tài liệu/chat thành `{{ platform.framework_root }}/knowledge/active/REQUIREMENT.md` rõ scope, AC, As-is/To-be, contract, assumptions, and open questions.

## Khi nào dùng

- `/task` Pha 1 với input HAS_TICKET.
- User yêu cầu chuẩn hóa requirement từ ticket/tài liệu.
- Có tài liệu rời rạc nhưng chưa có REQUIREMENT.md chuẩn.

## Khi nào KHÔNG sử dụng

- Ideation thô (→ openspec-explore).
- Wiki/Confluence dài nhiều trang cần extract trước (→ spec-extract).
- Architecture review (→ architecture-reviewer).
- Technical spec generation (→ openspec-propose).

## Input / Output

Input: ticket, linked docs, user clarifications, and codebase evidence from UA-first probe.

Output: `{{ platform.framework_root }}/knowledge/active/REQUIREMENT.md`.

Read [references/output-schema.md](references/output-schema.md) when writing the full REQUIREMENT.md structure.

## Quy trình mỏng

1. Collect sources.
2. Classify task: `feature | fixbug | changerequest | refactor`.
3. Write business context.
4. Run UA-first codebase probe.
5. Write As-is / To-be.
6. Define in-scope and out-of-scope.
7. Normalize Acceptance Criteria.
8. Write Technical Design Contract.
9. Filter assumptions and open questions.
10. Finalise REQUIREMENT.md.

Read [references/process-guide.md](references/process-guide.md) when executing the full process.
Read [references/ua-open-question-filter.md](references/ua-open-question-filter.md) before asking user an open question.
Read [references/gotchas.md](references/gotchas.md) when parsing existing files or external docs.

## Cập nhật AGENT_TRANSPARENCY

Mark `[x] REQUIREMENT.md`, `[x] requirement-analyst`, sources read, major limitations, and confidence CAO/TRUNG BÌNH/THẤP.
```

- [ ] **Step 3: Run skill lint for requirement-analyst**

Run: `python3 -m pytest cli/tests/test_skill_standard.py -k requirement-analyst -q`

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add .maika/skills/requirement-analyst/
git commit -m "refactor(requirement-analyst): split schema and process into references"
```

---

### Task 6: Migrate `spec-validator` below 300 lines and wire coverage commands

**Files:**
- Modify: `.maika/skills/spec-validator/SKILL.md`
- Create: `.maika/skills/spec-validator/references/pre-apply-gate.md`
- Create: `.maika/skills/spec-validator/references/coverage-checks.md`
- Create: `.maika/skills/spec-validator/references/post-apply-checks.md`
- Create: `.maika/skills/spec-validator/references/contract-dag-check.md`
- Create: `.maika/skills/spec-validator/references/dna-compliance-check.md`
- Create: `.maika/skills/spec-validator/references/gotchas.md`

**Interfaces:**
- Consumes: Task 1 CLI `gate-check ac-coverage` and `gate-check integration-coverage`.
- Produces: `spec-validator` body ≤ 300 with exact commands.

- [ ] **Step 1: Create reference files**

Create `.maika/skills/spec-validator/references/pre-apply-gate.md`:

```markdown
# Pre-Apply Gate

> Tài liệu tham khảo cho `spec-validator`. Read before `/task apply`.

## Checks

- change_id exists.
- proposal.md has what/why.
- spec/tasks contains at least one task or file change.
- no outside PROJECT_ROOTS without user verification.
- OPENSPEC_STATE is propose_done.
- Technical Design Contract interfaces are represented in tasks when contract exists.

FAIL blocks apply. WARN requires user decision.
```

Create `.maika/skills/spec-validator/references/coverage-checks.md`:

```markdown
# Coverage Checks

> Tài liệu tham khảo cho `spec-validator`. Read when checking Acceptance Criteria or integration coverage.

## Commands

Run:

```bash
CHANGE_ID="${CHANGE_ID:?set CHANGE_ID to the OpenSpec change folder name}"
python3 {{ platform.framework_root }}/tools/gate-check/cli.py ac-coverage {{ platform.framework_root }}/knowledge/active/REQUIREMENT.md --against "openspec/changes/${CHANGE_ID}/tasks.md"
python3 {{ platform.framework_root }}/tools/gate-check/cli.py integration-coverage {{ platform.framework_root }}/knowledge/active/REQUIREMENT.md --against "openspec/changes/${CHANGE_ID}/tasks.md"
```

Non-zero exit means uncovered AC or integration. Show reason to user and ask whether to amend spec or continue.

## Scope

These deterministic checks use simple keyword/entity overlap. They do not replace semantic review. If semantic judgment is needed, agent must write rationale explicitly.
```

Create `.maika/skills/spec-validator/references/post-apply-checks.md`:

```markdown
# Post-Apply Checks

> Tài liệu tham khảo cho `spec-validator`. Read after apply when comparing expected files with actual changed files.

## Checks

- Expected file touched but absent from changed_files → WARN.
- Unexpected file touched → WARN.
- Syntax/compile check if project tooling exists.
- Do not auto-rollback.

Output: `[POST-APPLY] verify: {n_match}/{n_expected} matches. Issues: {issue_list_or_empty}`.
```

Create `.maika/skills/spec-validator/references/contract-dag-check.md`:

```markdown
# Contract DAG Check

> Tài liệu tham khảo cho `spec-validator`. Read when validating microloop CONTRACT_DAG after apply.

## Checks

- No node remains pending, in_progress, blocked, or stale.
- Node changed files fit its writes list.
- Leaf node does not write contract/base files.
- contract_ref version matches current contract node.
- CONTEXT_REQUEST, CONTRACT_CHANGE_REQUEST, and INTEGRATION_REQUEST artifacts are resolved or logged in AGENT_TRANSPARENCY.
```

Create `.maika/skills/spec-validator/references/dna-compliance-check.md`:

```markdown
# DNA Compliance Check

> Tài liệu tham khảo cho `spec-validator`. Read when performing semantic post-apply DNA compliance.

## Inputs

- changed_files
- author-dna.yaml hard_principles, soft_preferences, complexity_thresholds, style_preferences
- approved conventions.yaml naming/package constraints

## Result

- BLOCK for hard principle violations.
- PASS with warnings for soft/convention concerns.
- CLEAN when no violations detected.

The checklist is dynamic from DNA/conventions; do not hardcode HP/SP IDs.
```

Create `.maika/skills/spec-validator/references/gotchas.md`:

```markdown
# Spec Validator Gotchas

> Tài liệu tham khảo cho `spec-validator`. Read when path, contract, coverage, or DNA edge cases appear.

## Gotchas

- OpenSpec artifact path may change; verify files exist before reading.
- C6 contract gate runs only when REQUIREMENT has a design contract/interface section.
- Pre-apply returns PASS/BLOCK; post-apply returns OK/issues list.
- Generic AC can cause false positives; warn when AC is too vague.
- DNA check assumes DNA slice is available in task handoff.
- Conventions draft is skipped until approved.
```

- [ ] **Step 2: Rewrite `spec-validator/SKILL.md` as thin entrypoint**

Keep frontmatter. Replace body after frontmatter with:

```markdown
# Spec Validator — Kiểm tra Spec Trước và Sau Apply

## Mục tiêu

- Pre-apply gate: block apply when spec has serious issues.
- AC coverage: every REQUIREMENT acceptance criterion should be represented in tasks/spec.
- Integration coverage: every new integration should have mapper/adapter/task coverage.
- Post-apply verify: changed files match intended spec.
- Contract DAG and DNA compliance checks after apply.

Skill này là quality gate. Không sinh spec, không sửa code.

## Khi nào dùng

- Before `/task apply`.
- After `/task apply`.
- User asks to validate spec.

## Khi nào KHÔNG sử dụng

- Need new spec (→ openspec-propose).
- Need architecture review (→ architecture-reviewer).
- Need requirement normalization (→ requirement-analyst).
- Missing REQUIREMENT.md (→ requirement-analyst first).

## Deterministic commands

Run AC coverage:

```bash
CHANGE_ID="${CHANGE_ID:?set CHANGE_ID to the OpenSpec change folder name}"
python3 {{ platform.framework_root }}/tools/gate-check/cli.py ac-coverage {{ platform.framework_root }}/knowledge/active/REQUIREMENT.md --against "openspec/changes/${CHANGE_ID}/tasks.md"
```

Run integration coverage:

```bash
CHANGE_ID="${CHANGE_ID:?set CHANGE_ID to the OpenSpec change folder name}"
python3 {{ platform.framework_root }}/tools/gate-check/cli.py integration-coverage {{ platform.framework_root }}/knowledge/active/REQUIREMENT.md --against "openspec/changes/${CHANGE_ID}/tasks.md"
```

Non-zero exit means show the reason and ask whether to amend spec or continue.

## Gate list

1. Pre-apply gate.
2. AC coverage.
3. Integration coverage.
4. Contract DAG check.
5. Post-apply verify.
6. DNA compliance check.

Read [references/pre-apply-gate.md](references/pre-apply-gate.md) before apply.
Read [references/coverage-checks.md](references/coverage-checks.md) when checking AC or integration coverage.
Read [references/contract-dag-check.md](references/contract-dag-check.md) when validating CONTRACT_DAG.
Read [references/post-apply-checks.md](references/post-apply-checks.md) after apply.
Read [references/dna-compliance-check.md](references/dna-compliance-check.md) for semantic DNA compliance.
Read [references/gotchas.md](references/gotchas.md) for edge cases.

## Cập nhật AGENT_TRANSPARENCY

Ghi:
- `[x] spec-validator: pre_apply_gate — {PASS|BLOCK}`
- `[x] spec-validator: ac_coverage — {n}/{n} covered`
- `[x] spec-validator: integration_coverage — {n}/{n} covered`
- `[x] spec-validator: contract_dag_check — {PASS|BLOCK}`
- `[x] spec-validator: post_apply_verify — {OK|issues}`
```

- [ ] **Step 3: Run skill lint for spec-validator**

Run: `python3 -m pytest cli/tests/test_skill_standard.py -k spec-validator -q`

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add .maika/skills/spec-validator/
git commit -m "refactor(spec-validator): split validator details into references"
```

---

### Task 7: Remove the skill body allowlist and refresh generated artifacts

**Files:**
- Modify: `cli/tests/test_skill_standard.py`
- Modify: `.maika/skills/skill-index.yaml`
- Conditionally modify when snapshot tests report missing paths: `cli/tests/snapshots/antigravity.txt`
- Conditionally modify when snapshot tests report missing paths: `cli/tests/snapshots/claude-code.txt`
- Conditionally modify when snapshot tests report missing paths: `cli/tests/snapshots/codex.txt`
- Conditionally modify when snapshot tests report missing paths: `cli/tests/snapshots/generic.txt`

**Interfaces:**
- Consumes: all 5 migrated skills.
- Produces: no active allowlist; full lint/regression green.

- [ ] **Step 1: Remove `BODY_LINE_ALLOWLIST` usage**

In `cli/tests/test_skill_standard.py`, replace:

```python
BODY_LINE_ALLOWLIST = {
    "architecture-reviewer",
    "knowledge-curator",
    "openspec-explore",
    "requirement-analyst",
    "spec-validator",
}
```

with:

```python
BODY_LINE_ALLOWLIST = set()
```

Keep `test_l3_allowlisted_body_ok`; it documents grandfather behavior for future emergency use. Do not add any real skill names to the allowlist.

- [ ] **Step 2: Run skill lint**

Run: `python3 -m pytest cli/tests/test_skill_standard.py -q`

Expected: all tests PASS.

- [ ] **Step 3: Regenerate skill index**

Run: `python3 .maika/tools/skill-index/generate_index.py`

Expected: generator prints a success line ending with `with 14 skills.`

- [ ] **Step 4: Run snapshot tests**

Run: `python3 -m pytest cli/tests/test_snapshots.py -q`

Expected: PASS if snapshots already include new references, FAIL only if scaffold tree needs new reference paths.

- [ ] **Step 5: If snapshots fail, refresh exact paths**

For each failing snapshot, add the new reference paths reported by pytest in sorted order under the correct root:

- `.agents/skills/{skill-name}/references/{file-name}.md` for antigravity/codex snapshots
- `.claude/skills/{skill-name}/references/{file-name}.md` for claude-code snapshot
- `.maika/skills/{skill-name}/references/{file-name}.md` for generic snapshot

Run again: `python3 -m pytest cli/tests/test_snapshots.py -q`

Expected: PASS.

- [ ] **Step 6: Run full regression**

Run: `python3 -m pytest .maika/ cli/ -q`

Expected: all tests pass, with the existing skipped count unchanged.

- [ ] **Step 7: Commit**

```bash
git add cli/tests/test_skill_standard.py .maika/skills/skill-index.yaml cli/tests/snapshots/
git commit -m "test(skill-lint): remove body allowlist after phase 2 migration"
```

---

### Task 8: Final audit and report

**Files:**
- Modify: `TODOS.md` if the phase-2 work closes or partially closes an existing TODO entry.
- No code changes unless verification shows an explicit miss.

**Interfaces:**
- Consumes: completed Tasks 1-7.
- Produces: reviewer-ready summary and final verification.

- [ ] **Step 1: Verify body counts**

Run:

```bash
python3 - <<'PY'
import re
from pathlib import Path
for skill in sorted(Path(".maika/skills").iterdir()):
    p = skill / "SKILL.md"
    if p.exists():
        text = p.read_text(encoding="utf-8")
        m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
        body = text[m.end():] if m else text
        n = len(body.splitlines())
        print(f"{skill.name:32} {n:4}")
        if n > 300:
            raise SystemExit(f"{skill.name} still exceeds 300 body lines")
PY
```

Expected: all 14 skills print with body count ≤ 300.

- [ ] **Step 2: Verify reference links**

Run: `python3 -m pytest cli/tests/test_skill_standard.py -q`

Expected: PASS confirms no orphan/dangling/nested references and TOC requirements.

- [ ] **Step 3: Decide TODO update**

If `TODOS.md` has an entry for BP-A2, update it to say this PR closes the targeted `knowledge-curator` + `spec-validator` slice and leaves broader 7-skill/8-workflow A-2 work for a later PR. Do not claim full A-2 closure unless every listed skill/workflow was handled.

- [ ] **Step 4: Final regression**

Run: `python3 -m pytest .maika/ cli/ -q`

Expected: PASS.

- [ ] **Step 5: Commit TODO update if any**

If `TODOS.md` changed:

```bash
git add TODOS.md
git commit -m "docs(todos): mark targeted A-2 gate work completed"
```

If no TODO update is needed, do not create an empty commit.
