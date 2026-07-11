# Maika Upgrade Plan — Adaptive Loops & Loop Engineer

## 1. Mục tiêu của đợt nâng cấp

Chuyển Maika từ:

```text
Brainstorm → Spec → Detailed Plan → Implement
```

thành:

```text
Intake
  ↓
Risk + Uncertainty Classification
  ↓
Chọn loop nhỏ nhất đủ giải quyết
  ↓
Execute → Verify
  ↓
Loop Engineer chỉ xuất hiện khi có friction
```

Nguyên tắc kiến trúc mới:

> **Mọi code change cần execution contract, nhưng không phải mọi code change đều cần detailed plan.**

Planning Specialist vẫn giữ vai trò tạo kế hoạch chi tiết cho những thay đổi cần phased handoff, dependency management, verification và audit. Nó phải được gọi có điều kiện theo risk và uncertainty, thay vì trở thành universal gateway trước mọi code write.

Loop Engineer sẽ trở thành **meta-controller bên ngoài Spec Loop, Plan Loop và Dev Loop**. Thiết kế của nó dựa trên các nguyên tắc nội bộ của Maika:

- chỉ kích hoạt khi có friction signal;
- chẩn đoán root cause trước khi đề xuất patch;
- mở loop nhỏ nhất đủ giải quyết;
- dispatch sang specialist thay vì tự làm mọi việc;
- tách local correction khỏi shared improvement;
- yêu cầu evaluation trước khi promotion.

---

## 2. Design independence

Plan này là thiết kế nội bộ của Maika.

- Không phụ thuộc vào tên skill, folder hoặc artifact của framework khác.
- Không yêu cầu giữ đường dẫn tới tài liệu tham khảo bên ngoài.
- Không copy nguyên phase name, schema hoặc governance contract từ nguồn khác.
- Mọi khái niệm phải được chuẩn hóa theo vocabulary của Maika.
- Nguồn tham khảo, nếu cần lưu attribution, phải nằm trong ADR hoặc research note riêng và không trở thành runtime dependency.
- Acceptance criteria chỉ được dựa trên behavior cần đạt, không dựa trên việc implementation giống một framework khác.

Các capability canonical của Maika:

```text
Workflow Classifier
Spec Specialist
Planning Specialist
Implementation Specialist
Verification Specialist
Loop Engineer
Knowledge Curator
Skill Evolution Pipeline
```

---

## 4. Target operating model

### 2.1 Bốn vòng lặp

```text
┌───────────────────────────────────────────────────────────┐
│                    LOOP ENGINEER                          │
│ Observe → Classify → Route → Control → Verify → Learn    │
└──────────────┬────────────────┬─────────────────┬─────────┘
               │                │                 │
               ▼                ▼                 ▼
       SPEC LOOP          PLAN LOOP          DEV LOOP
 Brainstorm ↔ Spec    Plan ↔ Audit Plan   Impl ↔ Verify
               │                │                 │
               └────────────────┴─────────────────┘
                                │
                                ▼
                       MACRO LEARNING LOOP
                Candidate → Evaluate → Canary → Promote
```

### 2.2 Điều kiện kích hoạt

| Loop | Khi nào chạy |
|---|---|
| Dev Loop | Mọi coding task |
| Spec Loop | Desired behavior chưa rõ hoặc contract thay đổi |
| Plan Loop | Nhiều dependency, module, agent hoặc rollback phức tạp |
| Loop Engineer | Flow gặp friction vượt khỏi một correction cục bộ |
| Macro Learning Loop | Root cause có khả năng tái diễn hoặc đã xuất hiện ở nhiều task |

### 2.3 Invariant mới

Mọi coding task bắt buộc có:

```text
Intent
Evidence tối thiểu
Declared scope
Verification contract
```

Chỉ task đủ điều kiện mới bắt buộc có:

```text
Brainstorm
SPEC.md
SPEC audit
Detailed implementation plan
Plan audit/red-team
```

---

## 4. Workflow matrix theo task class

### `trivial`

Chỉ cho phép:

- documentation;
- comment;
- metadata không đổi runtime behavior;
- typo;
- formatting.

Flow:

```text
Inspect → Change → Static Check
```

Artifact:

```text
TASK.yaml
```

Không chạy:

- brainstorm;
- spec;
- `planning specialist`;
- independent review;
- Loop Engineer;
- learning capture.

---

### `small`

Áp dụng cho:

- một thay đổi behavior cục bộ;
- một module;
- scope rõ;
- không đổi public contract;
- không đổi DB, event, security hoặc concurrency semantics.

Flow:

```text
Focused Evidence
→ Micro-plan trong TASK.yaml
→ Implement
→ Verify
```

Micro-plan:

```yaml
intent:
  summary: Fix null handling in StageMapper.

evidence:
  - StageMapper currently creates an empty LocalizedField for null input.

scope:
  modify:
    - src/main/.../StageMapper.java
  test:
    - src/test/.../StageMapperTest.java

actions:
  - Preserve null instead of creating an empty value.
  - Add regression coverage.

verification:
  profile: gradle-test
  parameters:
    tests:
      - StageMapperTest
```

Không cần một `plan.md` riêng.

---

### `standard`

Áp dụng khi:

- public API hoặc business behavior thay đổi;
- Kafka/event/transaction/concurrency;
- nhiều module;
- requirement có uncertainty;
- có compatibility concern.

Flow:

```text
Focused Brainstorm
→ Spec
→ Compact Plan
→ Implement
→ Review
→ Verify
```

`planning specialist` có thể được gọi với:

```text
/planning specialist --fast --tdd
```

hoặc mode tự động.

Không bắt buộc red-team nếu classifier không phát hiện high-risk signal.

---

### `architectural`

Áp dụng khi:

- architecture;
- security/permission;
- migration;
- data integrity;
- cross-service protocol;
- infrastructure;
- rollback khó;
- blast radius cao.

Flow:

```text
Brainstorm
→ Spec
→ Audit Spec
→ Detailed Plan
→ Validate/Red-team Plan
→ Implement theo phase
→ Independent Review
→ Verify
→ Human Gate
```

Đây là nơi dùng đầy đủ sức mạnh của `planning specialist`: grounding, cross-plan dependency, file map, phased tasks, validation và whole-plan consistency.

---

## 5. Loop Engineer runtime model

### 4.1 Trách nhiệm

Loop Engineer chỉ chịu trách nhiệm:

1. Nhận friction signals.
2. Xác định có cần mở loop hay không.
3. Phân loại root cause.
4. Chọn loop nhỏ nhất phù hợp.
5. Dispatch specialist.
6. Theo dõi retry, budget và scope.
7. Verify close condition.
8. Tạo learning candidate nếu đủ threshold.

Nó không trực tiếp:

- viết spec;
- viết plan;
- implement code;
- audit plan;
- sửa global skill;
- approve chính proposal của mình.

---

### 4.2 Ba cấp độ loop

#### Cấp 1 — Micro loop

Dùng cho:

- test fail lần đầu;
- review yêu cầu một fix trong scope;
- output contract malformed;
- compile error cục bộ.

Flow:

```text
Implement
→ Verify fail
→ Fix
→ Verify
```

Không tạo loop folder.

Chỉ append vào:

```text
RESULT.yaml
REVIEW.md
VERIFICATION_REPORT.md
```

Giới hạn mặc định:

```yaml
max_micro_retries: 2
```

---

#### Cấp 2 — Change loop

Kích hoạt khi:

- cùng lỗi lặp lại quá retry budget;
- touched file ngoài scope;
- plan assumption sai;
- evidence stale;
- implementation cho thấy spec thiếu;
- blast radius lớn hơn dự kiến;
- verification failure không còn là lỗi local.

Artifact duy nhất:

```text
<workspace>/LOOP.yaml
```

Schema:

```yaml
version: 1

loop_id: LOOP-<change>-001
change_id:
level: change
state: diagnosing

trigger:
  type:
  source:
  observed_at:
  evidence: []

scope:
  direct: []
  stale_risk: []
  trace_only: []
  unaffected: []

root_cause:
  category:
  statement:
  confidence:
  evidence_ids: []

route:
  target_loop:
  specialist:
  required_artifacts: []
  human_gate_required: false

actions: []

verification:
  checks: []
  result:
  residual_risk:

close:
  state:
  reason:
```

Change loop không tạo nhiều Markdown file như the reviewed governance pattern.

---

#### Cấp 3 — Macro learning loop

Kích hoạt khi:

- cùng root cause xuất hiện ở nhiều task;
- human correction;
- critical incident;
- shared skill gây lỗi reproducible;
- measurable token inefficiency;
- convention mới được xác nhận nhiều lần;
- runtime/harness gap ảnh hưởng nhiều project.

Folder:

```text
.maika/loops/<loop-id>/
```

Artifacts:

```text
LOOP.yaml
00-trigger.md
01-scope-map.md
02-root-cause.md
03-improvement-proposal.md
04-learning-candidate.yaml
05-evaluation.yaml
06-promotion-or-rollback.md
```

Chỉ macro loop mới dùng full artifact model tương tự `Loop Engineer`.

---

## 6. Trigger engine

### 5.1 Trigger categories

```yaml
trigger_categories:
  requirement:
    - ambiguous_desired_behavior
    - contradictory_acceptance_criteria
    - human_requirement_correction

  spec:
    - spec_code_conflict
    - missing_contract
    - spec_audit_failure

  plan:
    - missing_dependency
    - stale_file_map
    - invalid_task_order
    - scope_underestimated
    - plan_review_failure

  implementation:
    - repeated_test_failure
    - repeated_review_finding
    - outside_scope_write
    - unexpected_blast_radius

  verification:
    - no_real_verification
    - flaky_verification
    - environment_blocker
    - non_reproducible_result

  knowledge:
    - stale_evidence
    - conflicting_memory
    - missing_project_knowledge
    - wrong_knowledge_reuse

  skill:
    - repeated_skill_failure
    - human_correction
    - excessive_token_cost
    - reusable_review_finding

  runtime:
    - worker_crash
    - budget_exhausted
    - lock_conflict
    - command_policy_block
```

---

### 5.2 Trigger thresholds

#### Không mở Loop Engineer

- test fail lần đầu;
- compile fail cục bộ;
- review fix trong declared scope;
- worker retry đầu tiên;
- transient tool failure.

#### Mở change loop tự động

- retry count vượt `2`;
- scope escape;
- stale plan/evidence;
- verification contradiction;
- task class cần escalate;
- implementation phát hiện missing contract.

#### Yêu cầu human confirmation trước khi mở

- reopen spec làm thay đổi desired behavior;
- thay đổi public contract;
- security/data/permission;
- sửa shared skill hoặc policy;
- migration/infra;
- intent ban đầu có thể thay đổi.

#### Mở macro loop

- cùng `recurrence_key` xuất hiện từ ba lần;
- xuất hiện trong ít nhất hai change;
- một critical incident có evidence;
- explicit user directive;
- dogfood failure reproducible;
- measurable token/retry regression.

---

## 7. Root-cause taxonomy

| Category | Ý nghĩa |
|---|---|
| `requirement_gap` | User intent hoặc AC thiếu/mâu thuẫn |
| `spec_gap` | Desired contract không đủ rõ |
| `plan_gap` | Decomposition, dependency hoặc file map sai |
| `implementation_gap` | Code không làm đúng plan/spec |
| `verification_gap` | Test/check không chứng minh đúng claim |
| `knowledge_gap` | Thiếu hoặc stale codebase knowledge |
| `memory_conflict` | Long-term memory mâu thuẫn source hiện tại |
| `skill_gap` | Specialist skill thiếu rule hoặc behavior |
| `runtime_gap` | Orchestrator, write-gate, state hoặc command policy lỗi |
| `tooling_gap` | UA/MCP/worker/tool không cung cấp evidence cần thiết |
| `coordination_gap` | Handoff hoặc dependency giữa worker sai |

Mỗi diagnosis phải có:

```yaml
root_cause:
  category: plan_gap
  statement: Plan omitted the downstream serializer.
  confidence: high
  evidence_ids:
    - CODE-123
    - REVIEW-TASK-2
  rejected_alternatives:
    - category: implementation_gap
      reason: Worker followed the declared file map exactly.
```

Không cho Loop Engineer sửa trước khi có diagnosis tối thiểu.

---

## 8. Routing policy

### Specialist routing table

| Root cause | Route |
|---|---|
| Requirement gap | `brainstorm` |
| Spec gap | `writing-spec` / spec audit |
| Plan gap | `planning specialist` / plan audit |
| Implementation gap | implementation/fix worker |
| Verification gap | verification specialist |
| Knowledge gap | grounding/retrieval curator |
| Memory conflict | knowledge reconciliation |
| Skill gap | skill evolution curator |
| Runtime gap | runtime-maintainer flow |
| Tooling gap | capability degradation/fallback |
| Coordination gap | orchestrator replanning |

`planning specialist` chỉ được gọi khi route target là `plan_loop`.

### Mode selection

```yaml
plan_mode_policy:
  small:
    mode: none

  standard_low_uncertainty:
    mode: fast

  standard_high_uncertainty:
    mode: auto

  architectural:
    mode: deep
    red_team: true
    validate: true

  security_or_data_integrity:
    mode: deep
    red_team: true
    validate: true
    human_gate: true
```

---

## 9. Approval model

### Tự động

- retry local trong declared scope;
- rerun test;
- regenerate malformed result;
- reopen implementation micro-loop;
- re-ground stale evidence;
- compact plan update không đổi behavior;
- increase task class từ `small` lên `standard`.

### Cần human approval

- thay đổi intent;
- thay đổi spec behavior;
- public API/event/schema;
- security/permission;
- migration/infrastructure;
- sửa global/shared skill;
- promote learning candidate;
- bỏ qua failed verification;
- hạ task class;
- mở rộng scope ngoài user-approved boundary.

Approval phải là trusted runtime artifact:

```yaml
version: 1
approval_id:
change_id:
loop_id:
decision:
approved_scope:
decision_hash:
approved_by:
approved_at:
source: explicit-user-action
```

---

## 10. State model

### Main task state

Giữ:

```text
INTAKE
EXPLORING
SPEC_REVIEW
PLANNING
EXECUTING
VERIFYING
FINAL_REVIEW
COMPLETED
BLOCKED
...
```

### Orthogonal loop state

`LOOP.yaml` quản lý:

```text
OBSERVED
CONFIRMATION_REQUIRED
OPENED
MAPPING_SCOPE
DIAGNOSING
PROPOSING
WAITING_APPROVAL
APPLYING
VERIFYING
RESOLVED
PROPOSAL_ONLY
BLOCKED
NO_OP
SUPERSEDED
CLOSED_BY_USER
```

Main state và loop state liên kết:

```yaml
STATE.yaml:
  state: BLOCKED
  active_loop_id: LOOP-ABC-001
  blocked:
    reason: plan_gap
    resume_state: EXECUTING
```

Loop close thành công:

```text
LOOP.RESOLVED
→ main task resume_state
```

---

## 11. Loop budget và anti-recursion

```yaml
loop_policy:
  max_micro_retries: 2
  max_change_loops_per_task: 2
  max_spec_reopens: 1
  max_plan_reopens: 2
  max_loop_depth: 2

  token_budget:
    change_loop: 12000
    macro_loop: 50000

  worker_budget:
    diagnosis: 1
    proposal: 1
    verification: 1
```

Rule:

> Một task chỉ có một active Loop Engineer. Friction mới được append vào loop hiện tại hoặc escalated lên macro level.

---

## 12. Artifact strategy để tiết kiệm token

### Happy path

Không có Loop Engineer artifact.

### Micro failure

Append event:

```json
{
  "event": "verification_failed",
  "attempt": 1,
  "reason": "StageMapperTest failed",
  "action": "local_fix"
}
```

### Change loop

Một `LOOP.yaml`.

### Macro loop

Full folder.

### Không duplicate context

`LOOP.yaml` chỉ lưu IDs và references:

```yaml
evidence_ids:
  - CODE-123
  - REVIEW-456

artifact_refs:
  spec: SPEC.md
  plan: IMPLEMENTATION_PLAN.md
  result: results/TASK-1.yaml
```

---

## 13. Integration vào Maika hiện tại

### Module mới

```text
.maika/tools/microloop-orchestrator/
├── loop_policy.py
├── loop_engineer.py
├── loop_state.py
├── loop_router.py
├── loop_artifacts.py
└── loop_metrics.py
```

#### `loop_policy.py`

Sở hữu:

- trigger definitions;
- thresholds;
- approval rules;
- mode selection;
- budgets;
- root-cause taxonomy.

#### `loop_engineer.py`

Sở hữu:

- observe;
- open;
- diagnose;
- propose;
- route;
- verify;
- close.

#### `loop_state.py`

Sở hữu:

- loop state transition;
- atomic write;
- lock;
- resume;
- close-state validation.

#### `loop_router.py`

Map root cause sang specialist dispatch.

#### `loop_artifacts.py`

Tạo:

- `LOOP.yaml`;
- macro loop folder;
- hashes;
- artifact references.

#### `loop_metrics.py`

Theo dõi:

- retries;
- reopens;
- token cost;
- resolution path;
- candidate creation.

---

### Module cần sửa

#### `adaptive_runtime.py`

Thêm:

```python
classify_workflow_requirements(...)
```

Output:

```yaml
workflow:
  dev_loop: required
  spec_loop: skipped | required | conditional
  plan_loop: skipped | compact | full
  plan_mode: none | fast | auto | deep
  audit_spec: false
  audit_plan: false
  human_gate: false
```

#### `orchestrator.py`

Thêm hook:

```text
before_phase
after_worker
after_review
after_verification
on_block
```

#### `vnext_dispatch.py`

Dispatch theo route:

```text
spec_writer
spec_auditor
planner
plan_auditor
implementer
reviewer
knowledge_curator
skill_curator
```

#### `vnext_state.py`

Thêm:

```yaml
active_loop_id:
```

và API block/resume theo loop.

#### `runtime_hardening.py`

Thêm:

- trusted loop approvals;
- loop lock;
- artifact hash validation;
- shared-skill write restriction.

#### `plan_compiler.py`

Cho phép:

- compact plan từ `TASK.yaml`;
- full plan từ `IMPLEMENTATION_PLAN.md`;
- không ép lightweight task phải có full plan.

#### `knowledge_control.py`

Nhận verified macro-loop outcome và tạo learning candidate.

#### CLI

Thêm:

```text
maika loop status --id <change>
maika loop inspect --id <change>
maika loop approve --id <change> --decision <id>
maika loop reject --id <change> --decision <id>
maika loop resume --id <change>
maika loop close --id <change>
```

---

## 14. Runtime policy config

Tạo:

```text
.maika/profiles/loop-policy.yaml
```

Ví dụ:

```yaml
version: 1

workflow_matrix:
  trivial:
    spec_loop: never
    plan_loop: never
    dev_loop: required

  small:
    spec_loop: on_ambiguity
    plan_loop: micro
    dev_loop: required

  standard:
    spec_loop: conditional
    plan_loop: compact
    dev_loop: required

  architectural:
    spec_loop: required
    plan_loop: full
    audit_spec: required
    audit_plan: required
    dev_loop: required

triggers:
  repeated_failure:
    threshold: 2
    opens: change_loop

  scope_escape:
    threshold: 1
    opens: change_loop

  human_correction:
    threshold: 1
    opens: change_loop
    learning_candidate: true

  repeated_root_cause:
    threshold: 3
    distinct_changes: 2
    opens: macro_loop

approval:
  reopen_spec: human
  change_public_contract: human
  patch_shared_skill: human
  local_code_fix: automatic
  replan_within_scope: automatic
```

---

## 15. Implementation phases

### Phase 0 — Architecture contract

#### Tasks

1. Viết ADR:
   ```text
   docs/architecture/adaptive-loops-and-loop-engineer.md
   ```
2. Xác định invariant:
   - execution contract luôn bắt buộc;
   - detailed plan conditional;
   - Loop Engineer không chạy happy path;
   - một task chỉ có một active loop;
   - shared skill không tự patch.
3. Document workflow matrix.
4. Document trigger/root-cause/routing taxonomy.

#### Verification

- ADR được review.
- Không có conflict với existing state machine.
- Mọi task class có một deterministic path.

---

### Phase 1 — Conditional planning

#### Tasks

1. Thêm `classify_workflow_requirements()`.
2. Tách:
   ```text
   requires_execution_contract
   requires_spec
   requires_detailed_plan
   requires_plan_audit
   ```
3. Cho small dùng micro-plan.
4. Route `planning specialist` chỉ khi plan loop yêu cầu.
5. Chọn `planning specialist` mode theo risk.

#### Tests

- small không gọi planner;
- standard low-risk gọi fast plan;
- architectural gọi deep + red-team;
- ambiguity bật spec loop;
- source-only internal fix không tạo spec.

#### Exit criteria

Một task small có thể:

```text
start → apply → verify → complete
```

mà không tạo `SPEC.md` và `IMPLEMENTATION_PLAN.md`.

---

### Phase 2 — Loop state và artifacts

#### Tasks

1. Implement `LOOP.yaml`.
2. Implement loop transition matrix.
3. Implement open/append/resolve/block.
4. Gắn `active_loop_id` vào task state.
5. Atomic write và workspace lock.
6. Implement close states.

#### Tests

- chỉ một active loop;
- illegal transition bị deny;
- resolved loop resume đúng task state;
- blocked loop không tự resume;
- malformed artifact fail closed.

---

### Phase 3 — Trigger engine

#### Tasks

1. Emit runtime events:
   - worker failure;
   - review finding;
   - scope escape;
   - stale evidence;
   - verification failure;
   - budget exhausted;
   - human correction.
2. Implement thresholds.
3. Micro events không mở loop.
4. Change trigger mở hoặc append loop.
5. Confirmation trigger chờ trusted approval.

#### Tests

- first test fail → micro retry;
- third repeated failure → change loop;
- scope escape → loop ngay;
- security intent → confirmation required;
- duplicate trigger append vào loop hiện tại.

---

### Phase 4 — Diagnosis và routing

#### Tasks

1. Implement deterministic diagnosis hints.
2. Dispatch diagnosis worker khi signal chưa đủ.
3. Root cause phải có evidence.
4. Map root cause sang specialist.
5. Ngăn Loop Engineer re-implement specialist logic.
6. Cho route quay lại:
   - spec;
   - plan;
   - dev;
   - knowledge;
   - skill pipeline.

#### Tests

- spec/code conflict route spec loop;
- missing dependency route plan loop;
- wrong code route dev loop;
- stale knowledge route curator;
- skill gap tạo update candidate, không patch trực tiếp.

---

### Phase 5 — Approval governance

#### Tasks

1. Trusted approval artifact.
2. CLI approve/reject.
3. Policy theo risk.
4. Shared skill write-gate.
5. Human approval timeout/block semantics.
6. Audit approval decisions.

#### Tests

- agent-authored approval bị ignore;
- local fix không hỏi human;
- spec behavior change cần approval;
- shared skill patch thiếu approval → proposal-only;
- approval hash mismatch bị deny.

---

### Phase 6 — Macro learning loop

#### Tasks

1. Aggregate root causes theo `recurrence_key`.
2. Threshold cross-task.
3. Tạo learning candidate.
4. Evaluation before/after.
5. Canary.
6. Promotion approval.
7. Rollback.
8. Ghi skill effectiveness metrics.

#### Evaluation metrics

```yaml
before:
  success_rate:
  first_pass_approval:
  retry_count:
  token_cost:
  human_corrections:

after:
  success_rate:
  first_pass_approval:
  retry_count:
  token_cost:
  human_corrections:
```

#### Tests

- một observation không tạo candidate;
- repeated cross-task tạo candidate;
- evaluation trống không promote;
- canary fail rollback;
- contractual skill change cần human approval.

---

### Phase 7 — Observability

#### Metrics

```yaml
loop_metrics:
  tasks_total:
  tasks_without_loop:
  micro_loops:
  change_loops:
  macro_loops:
  spec_reopens:
  plan_reopens:
  average_retries:
  loop_token_cost:
  resolution_rate:
  human_gate_rate:
  learning_candidates:
  promoted_candidates:
  rollback_count:
```

#### Chỉ số quan trọng

```text
Ceremony avoidance rate
= tasks hoàn thành mà không cần full spec/plan loop
```

```text
Loop precision
= loop mở đúng và tạo resolution / tổng loop mở
```

```text
False escalation rate
= task bị nâng flow nhưng không tìm thấy risk thực
```

---

### Phase 8 — Dogfood và rollout

#### Stage 1 — Shadow mode

Loop Engineer chỉ ghi:

```text
would_open_loop
would_route_to
would_require_approval
```

Không thay đổi flow thật.

Chạy trên 20–30 task.

#### Stage 2 — Advisory mode

- tự chạy micro-loop;
- đề xuất change loop;
- human xác nhận.

#### Stage 3 — Controlled auto mode

- auto-open implementation/knowledge change loop;
- spec/security/shared-skill vẫn human-gated.

#### Stage 4 — Default adaptive mode

Dùng cho project dogfood sau khi metrics đạt threshold.

---

## 16. Test matrix

### Unit

- workflow classification;
- trigger thresholds;
- root-cause mapping;
- route selection;
- loop transitions;
- approval validation;
- budget;
- learning thresholds.

### Integration

- dev failure → local retry;
- retry exhausted → Loop Engineer;
- Loop Engineer → plan specialist;
- replan → resume execution;
- scope escape → blocked;
- skill gap → candidate;
- candidate → evaluation → promotion.

### Public E2E

#### Small happy path

```text
start
→ micro-plan
→ implement
→ verify
→ complete
```

Expected:

```text
No SPEC
No full plan
No Loop Engineer
```

#### Standard plan-gap

```text
execute
→ missing dependency
→ change loop
→ root cause plan_gap
→ planning specialist fast
→ plan audit
→ resume execute
```

#### Spec-gap

```text
implementation discovers ambiguous behavior
→ confirmation required
→ spec loop
→ approved spec
→ compact plan
→ resume
```

#### Macro learning

```text
same review finding across three tasks
→ candidate
→ offline evaluation
→ canary
→ promote or rollback
```

---

## 17. Acceptance criteria

Upgrade chỉ hoàn thành khi:

1. Mọi code task có execution contract.
2. Small task không bắt buộc có full spec hoặc detailed plan.
3. `planning specialist` chỉ được gọi theo workflow policy.
4. Dev Loop luôn tồn tại.
5. Spec Loop chỉ bật do ambiguity/contract risk.
6. Plan Loop chỉ bật do complexity/blast radius.
7. Loop Engineer không chạy trong happy path.
8. First local failure không mở Loop Engineer.
9. Repeated failure hoặc scope escape mở change loop.
10. Một task chỉ có một active loop.
11. Root cause phải có evidence.
12. Loop Engineer chỉ dispatch specialist.
13. Agent không tự approve spec/shared-skill change.
14. Shared skill gap có thể close `proposal-only`.
15. Macro learning cần cross-task evidence hoặc critical signal.
16. Candidate không promote nếu chưa evaluation/canary.
17. Loop artifacts không duplicate spec/plan content.
18. Loop budget ngăn recursive token explosion.
19. Metrics phân biệt micro/change/macro loops.
20. Public small, standard và architectural E2E đều pass.
21. Existing write-gate và verification invariants không bị suy yếu.
22. Ubuntu và Windows CI xanh.

---

## 18. Thứ tự ưu tiên

### P0 — Thay đổi tư duy runtime

- Execution contract thay detailed plan bắt buộc.
- Conditional Spec/Plan loops.
- Workflow matrix theo class.

### P1 — Loop Engineer change-level

- Trigger engine.
- `LOOP.yaml`.
- Root cause.
- Routing.
- Approval.
- Resume.

### P2 — Macro learning

- Cross-task aggregation.
- Evaluation.
- Canary.
- Promotion/rollback.

### P3 — Tối ưu

- Shadow mode metrics.
- Token budget tuning.
- False-escalation reduction.
- Adaptive mode selection cho `planning specialist`.

---

## Trạng thái đích

Maika sau upgrade không còn là:

```text
Một hệ thống luôn bắt agent lập kế hoạch thật dài trước khi code
```

Mà trở thành:

```text
Một hệ thống luôn biết mình đang làm gì,
nhưng chỉ yêu cầu mức reasoning và artifact tương xứng với rủi ro.
```

Loop Engineer là bộ phận quyết định **khi nào flow hiện tại không còn đủ**, còn `planning specialist`, spec writer, implementer và reviewer tiếp tục là các specialist thực thi từng loop.


---

## Implementation note

Khi dùng plan này để triển khai:

- Không cung cấp file tham khảo bên ngoài cho coding agent như một dependency bắt buộc.
- Không yêu cầu agent sao chép nội dung, tên gọi hoặc folder structure từ nguồn khác.
- Agent chỉ được implement behavior và invariants được mô tả trong plan.
- Nếu cần đối chiếu nguồn nghiên cứu, thực hiện trong một research task riêng và ghi kết luận bằng vocabulary của Maika trước khi coding.
