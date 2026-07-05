# Design: skill-lint phase 2 — allowlist về 0 + targeted deterministic gates

> Trạng thái: design đã chốt hướng với user (2026-07-05)
> Branch dự kiến: `feat/skill-standard-lint` hoặc branch nối tiếp trên nó
> Nguồn chuẩn: `2026-07-04-anthropic-bp-rubric.md` (citation-grounded từ Anthropic) và kết quả audit `2026-07-04-anthropic-bp-audit-report.md`

## 1. Vấn đề

Đợt 1 đã thêm `cli/tests/test_skill_standard.py`, migrate `infra-tdd` và `spec-extract`, và enforce L1-L8 trên toàn bộ `.maika/skills`. Còn 5 skill vượt budget 300 body lines trong `BODY_LINE_ALLOWLIST`:

- `architecture-reviewer` — 389 body lines
- `knowledge-curator` — 396 body lines
- `openspec-explore` — 343 body lines
- `requirement-analyst` — 362 body lines
- `spec-validator` — 343 body lines

Đây là backlog có chủ đích của đợt 2, không phải thiếu sót của đợt 1. Tuy nhiên nếu chỉ "cắt dòng cho qua lint" thì không giải quyết finding A-2 của audit: việc deterministic vẫn đang được giao cho prose trong một số skill. Đợt 2 phải vừa đưa allowlist về 0, vừa đóng phần A-2 có đòn bẩy cao nhất mà vẫn giữ scope đủ nhỏ để review được.

## 2. Quyết định scope

1. **Một PR có scope khóa**: migrate cả 5 skill khỏi allowlist và thêm targeted deterministic gates cho `knowledge-curator` + `spec-validator`.
2. **Không đóng trọn A-2 toàn repo**: 7 skill + 8 workflow là scope riêng. PR này chỉ đóng phần có giá trị cao nhất, nơi prose đang thay code cho archive/reset/spec validation.
3. **Không đổi nghĩa skill**: phần migration chủ yếu là progressive disclosure. Logic giữ nguyên trừ nơi explicit chuyển deterministic prose thành gate/script.
4. **UA-first là invariant**: mọi skill có hoạt động khám phá codebase phải ưu tiên Understand-Anything trước, Codebase Memory sau để đọc logic node, grep cuối. Lỗi Codebase Memory không được đồng nghĩa UA unavailable.
5. **Best-practice citation bắt buộc**: design/plan phải trỏ về BP-ID từ rubric, không tạo chuẩn mới song song.

## 3. Best-practice mapping

- **BP-03**: SKILL.md mỏng, body ≤ 300 dòng. Đợt 2 đưa allowlist về 0.
- **BP-04**: progressive disclosure một tầng. Mọi reference file phải được link trực tiếp từ SKILL.md kèm điều kiện đọc; reference >100 dòng có `## Mục lục`.
- **BP-07**: deterministic operations dùng script/gate. Áp dụng targeted cho `knowledge-curator` và `spec-validator`.
- **BP-08**: mỗi tool/script reference phải rõ "Run" hay "Read/See".
- **BP-21**: gate yêu cầu evidence, không nhận assertion. Các gate mới phải trả PASS/FAIL với reason cụ thể và có tests.

## 4. Thiết kế migration 5 skill

### 4.1 `architecture-reviewer`

Giữ trong SKILL.md:

- frontmatter, mục tiêu, khi dùng/không dùng, input/output, nguyên tắc confidence.
- quy trình review dạng thin checklist 7 bước, mỗi bước 1-3 dòng.
- câu invariant: boundary/topology/cross-service phải dùng UA (`domain_relationships`, `domain_flow`) trước khi kết luận.

Tách sang references:

- `review-flow-guide.md`: chi tiết Bước 1-7, bảng câu hỏi boundary/data/NFR.
- `ua-boundary-doctrine.md`: doctrine UA-altitude cho topology, async, Kafka/gRPC, cross-service.
- `infra-tdd-trigger.md`: M5 auto-trigger.
- `contract-completeness-check.md`: M6 contract completeness.
- `gotchas.md`: G1-G4.

### 4.2 `knowledge-curator`

Giữ trong SKILL.md:

- lifecycle surface: archive, reset, update snapshot, restore, rotate.
- exact commands cho gate-check bắt buộc trước archive/reset.
- output và transparency update.

Tách sang references:

- `archive-active-context.md`: archive algorithm + status meanings.
- `reset-active-context.md`: reset rules, active/ideation handling, token log behavior.
- `snapshot-promotion.md`: promotion criteria, stale/confidence decay.
- `archive-rotation.md`: rotate logic + cross-repo snapshot considerations.
- giữ/chuẩn hóa `m7-memory-push.md`, thêm link trực tiếp nếu chưa đủ.

Targeted gate/script work:

- Mở rộng `.maika/tools/gate-check/gates.py` và `cli.py` thay vì tạo tool mới.
- Thêm validator cho reset/archive preflight nếu cần tách khỏi `archive-ready` hiện tại:
  - fail khi phase_state thuộc blocked states.
  - fail khi `Teaching Moment Check` chưa hợp lệ.
  - warn/report khi TOKEN_LOG missing nhưng không block.
  - refuse destructive reset nếu active context chưa được archived/stashed/cancelled theo marker rõ.
- Add tests trong `.maika/tools/gate-check/tests/test_gates.py`.

### 4.3 `openspec-explore`

Giữ trong SKILL.md:

- stance: thinking partner, no implementation.
- guardrails: read/search allowed, code writes forbidden.
- UA-first probe khi brainstorm chạm code.
- khi dùng/không dùng.

Tách sang references:

- `openspec-awareness.md`: active change detection, artifact reading, capture decisions.
- `explore-patterns.md`: problem-space exploration, codebase investigation, compare options, visualize, risks.
- `examples.md`: long examples currently inflating body.

Không thêm workflow cứng. Skill này high-freedom theo BP-06; migration không được biến nó thành checklist bắt buộc.

### 4.4 `requirement-analyst`

Giữ trong SKILL.md:

- mục tiêu, trigger, input/output tối thiểu.
- 10-step flow dạng checklist mỏng.
- hard rule: trước khi ghi Open Question, câu hỏi code-trả-lời-được phải đi qua UA-first probe.

Tách sang references:

- `output-schema.md`: REQUIREMENT.md full schema.
- `process-guide.md`: chi tiết Bước 1-10.
- `ua-open-question-filter.md`: phân loại code-answerable vs true business unknown.
- `gotchas.md`: CRLF, skeleton detection, Confluence conversion, multi-ticket.

### 4.5 `spec-validator`

Giữ trong SKILL.md:

- mục tiêu, trigger, khi không dùng.
- danh sách gates: pre-apply, AC coverage, integration coverage, post-apply, contract DAG, DNA compliance.
- exact command references cho deterministic checks.

Tách sang references:

- `pre-apply-gate.md`
- `coverage-checks.md`
- `post-apply-checks.md`
- `contract-dag-check.md`
- `dna-compliance-check.md`
- `gotchas.md`

Targeted gate/script work:

- Mở rộng `gate-check` bằng validators cho coverage artifacts, ở mức deterministic vừa đủ:
  - parse REQUIREMENT sections for AC and Integration headings.
  - parse tasks/spec text.
  - report uncovered items by simple keyword/entity overlap, with explicit WARN output.
  - no semantic LLM judgment hidden inside "script". Nếu cần semantic judgment, script chỉ kiểm evidence format và yêu cầu agent ghi rationale.
- Add CLI entries and tests.
- Update `spec-validator/SKILL.md` to say Run gate-check command, not "agent tự so khớp" bằng prose.

## 5. Testing

Required verification:

1. `python3 -m pytest cli/tests/test_skill_standard.py -q`
2. `python3 -m pytest .maika/tools/gate-check/tests/test_gates.py -q`
3. `python3 -m pytest cli/tests/test_snapshots.py -q` if new reference files affect scaffold snapshots.
4. `python3 -m pytest .maika/ cli/ -q`
5. Body-line check proves all 14 skill bodies ≤ 300 or `BODY_LINE_ALLOWLIST` removed/empty.

Success criteria:

- `BODY_LINE_ALLOWLIST` is removed or empty.
- all 5 target skills pass L1-L8 without grandfathering.
- new deterministic gates have positive and negative tests.
- no new dependency.
- no nested references.
- every new reference file is linked from SKILL.md with "Read/See when..." or "Run..." wording.

## 6. Non-goals

- Do not close A-2 for all 7 skill + 8 workflow.
- Do not lint BP-05..BP-09 mechanically.
- Do not redesign the whole Maika task pipeline.
- Do not change skill names.
- Do not make `openspec-explore` a fixed workflow.
- Do not replace Understand-Anything with Codebase Memory; Codebase Memory remains support for source-code detail after UA locates the domain/flow.

## 7. Open implementation notes

- Prefer extending `.maika/tools/gate-check/gates.py`/`cli.py`; only create a new tool module if the gate-check abstraction clearly cannot represent the validator.
- Any deterministic validator that returns WARN rather than BLOCK must encode that in output shape and tests. Existing CLI is binary PASS/FAIL; if WARN is needed, either model it as PASS with structured message in a new command, or add a compatible result type carefully.
- Migration should be done skill-by-skill with lint after each skill, not as one large blind rewrite.
