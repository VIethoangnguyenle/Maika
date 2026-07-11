# Maika Agent-Facing Architecture Refactor Plan

## Baseline

```text
Repository: VIethoangnguyenle/Maika
Branch: master-v2
Reviewed HEAD: 0cdea05f763fa9ddb233ea68ffb5069efc01bad1
Primary focus:
- meta prompt
- bootstrap
- rules
- workflows
- procedures
- skills
- artifact contracts
- agent behavior verification
```

---

# 1. Bối cảnh

Maika đã có runtime tương đối mạnh:

- multi-host platform support;
- worker resolver;
- write gate;
- state machine;
- execution contract;
- verification runner;
- transaction;
- CI cross-platform.

Tuy nhiên, agent không làm việc trực tiếp với phần lớn runtime đó.

Trong quá trình sử dụng thực tế, agent chủ yếu tiêu thụ:

```text
platform entrypoint
→ meta prompt
→ bootstrap
→ rules
→ workflow
→ skill index
→ selected skills
→ context package
→ task artifacts
```

Do đó, chất lượng thực tế của Maika phụ thuộc mạnh vào:

```text
agent-facing content coherence
× routing determinism
× evidence quality
× instruction-following ability
```

Plan này xử lý khoảng trống lớn nhất còn lại:

> Maika đã mô tả rất tốt một kỹ sư nên suy nghĩ như thế nào, nhưng chưa biến nội dung đó thành một operating model thống nhất, deterministic và kiểm chứng được bằng agent behavior.

---

# 2. Vấn đề cần giải quyết

## 2.1 Hai task-memory model tồn tại song song

### vNext workspace model

```text
.maika/changes/<change-id>/
├── CHANGE.yaml
├── STATE.yaml
├── INTENT.md
├── exploration/
├── RECONCILIATION.md
├── SPEC.md
├── IMPLEMENTATION_PLAN.md
├── briefs/
├── results/
├── reviews/
├── verification/
└── generated/
```

### Legacy active-memory model

```text
.maika/knowledge/active/
├── REQUIREMENT.md
├── EXPLORE_CONTEXT.md
├── AGENT_TRANSPARENCY.md
├── TOKEN_LOG.md
└── ideation/
```

Các rules, bootstrap, resume logic và context compression hiện vẫn tham chiếu cả hai.

Kết quả:

- task state có nhiều authority;
- artifact cùng vai trò có nhiều bản;
- resume có thể đọc sai state;
- agent phải tự reconcile;
- context bị duplicate;
- archive lifecycle không rõ.

---

## 2.2 Adaptive workflow mâu thuẫn với fixed-flow rule

Workflow adaptive mô tả:

```text
trivial:
Inspect → Change → Static Check

small:
Focused Evidence → Micro-plan → Implement → Verify

standard:
Focused Grounding → Conditional Spec → Compact Plan → Implement → Review → Verify

architectural:
Grounding → Spec/Audit → Full Plan/Audit → Implement → Review → Verify → Human Gate
```

Nhưng critical rule vẫn yêu cầu:

```text
start → explore → spec → plan → review → apply
```

Agent yếu hoặc bị compact có thể ưu tiên `[CRITICAL]` fixed rule và biến mọi task nhỏ thành full ceremony.

---

## 2.3 Skill routing vẫn dựa trên model interpretation

Bootstrap nói:

```text
read skill index
extract trigger_conditions
load full skill only when trigger matches
```

Nhưng skill index và skill frontmatter chưa có đầy đủ:

- actions;
- states;
- change classes;
- positive trigger;
- negative trigger;
- priority;
- exclusivity;
- required artifacts;
- optional artifacts;
- required capabilities;
- output contract;
- completion gate.

Do đó routing thực tế là:

```text
agent reads description
→ agent guesses skill relevance
```

---

## 2.4 Lightweight workflow không có skill contract tương ứng

Runtime lightweight sử dụng:

```text
TASK.yaml
EVIDENCE.yaml
RESULT.yaml
lightweight execution contract
```

Nhưng skill library chủ yếu giả định:

```text
SPEC.md
IMPLEMENTATION_PLAN.md
TASK_QUEUE.json
briefs/TASK-NNN.md
capsule
```

Small task hiện dễ rơi vào một trong ba lỗi:

- tạo full spec/plan không cần thiết;
- gọi skill sai precondition;
- tự nghĩ micro-plan ngoài contract.

---

## 2.5 Public task commands chưa thật sự execute skills

Nhiều command hiện chủ yếu:

- chuyển state;
- validate artifact đã tồn tại;
- compile artifact đã được agent tự viết.

Ví dụ:

```text
maika task explore
→ transition state
→ không tự dispatch grounding-explorer

maika task spec
→ validate SPEC.md
→ không tự dispatch writing-spec

maika task plan
→ compile IMPLEMENTATION_PLAN.md
→ không tự dispatch writing-plan
```

Vì vậy skill vẫn là prose library chứ chưa phải executable capability.

---

## 2.6 Bootstrap đánh đồng file presence với agent comprehension

`rules_loaded` hiện có thể chỉ phản ánh file tồn tại.

Nhưng:

```text
rules_present
≠
rules read
≠
rules understood
≠
rules followed
```

Bootstrap report nên phân biệt:

- environment facts;
- agent acknowledgment;
- selected workflow;
- selected skill routing;
- unresolved contradiction.

---

## 2.7 Always-on content quá lớn

Fresh session hiện có thể phải load:

- platform entrypoint;
- meta prompt;
- bootstrap;
- RULES.md;
- six rule files;
- skill index;
- task workflow;
- active context.

Điều này làm:

- token overhead cao;
- attention bị phân tán;
- instruction conflict khó phát hiện;
- compact làm mất rule;
- agent sinh boilerplate compliance.

---

## 2.8 Retrieval bị lặp qua nhiều skills

Intent, grounding, brainstorming, planning, validation và review đều có thể gọi lại:

- source inspection;
- dependency analysis;
- historical recall;
- convention retrieval.

Thiếu contract phân biệt:

```text
reuse
revalidate
refresh
new retrieval
```

Dẫn đến tool theater và token waste.

---

## 2.9 Assumption policy chưa phân loại theo risk

Một rule nói sau hai lần tìm không thấy thì ghi assumption và tiếp tục.

Các rule khác nói missing material evidence phải block.

Cần phân loại assumption:

- safe/non-material;
- behavior-changing;
- public contract;
- persistence/destructive;
- security;
- environment-only.

---

## 2.10 Knowledge write ownership chưa nhất quán

Teaching moment rule yêu cầu ghi ngay vào Author DNA/conventions.

Role boundary lại nói knowledge curator sở hữu knowledge promotion sau VERIFIED.

Cần tách:

```text
capture candidate
≠
promote durable knowledge
```

---

## 2.11 Chưa có Agent Behavior Suite

CI hiện chủ yếu kiểm:

- parser;
- gates;
- runtime;
- write gate;
- artifact schema.

Chưa kiểm agent thật:

- có chọn đúng workflow không;
- có gọi đúng skill không;
- có nạp thừa context không;
- có bỏ qua provider không;
- có tạo artifact rỗng để qua gate không;
- Claude/Codex/Antigravity có hành xử nhất quán không.

---

# 3. Mục tiêu kiến trúc

Sau refactor, agent journey phải là:

```text
User request
→ Agent Kernel
→ Bootstrap environment report
→ Canonical active change resolution
→ Deterministic workflow route
→ Typed skill selection
→ Context package via Evidence Broker
→ Skill execution
→ Artifact validation
→ State transition
→ Review/verification
→ Knowledge candidate capture
→ Post-verified promotion
```

Mỗi bước phải có:

- một authority;
- một input contract;
- một output contract;
- một failure route;
- một validator;
- một owner.

---

# 4. Nguyên tắc thiết kế

## P1 — One authority per decision

Ví dụ:

```text
Current task state
→ STATE.yaml only

Workflow route
→ workflow-router.yaml only

Skill trigger
→ skill metadata only

Provider priority
→ rules-tool.md / capability registry only

Task-scoped artifacts
→ changes/<id>/ only
```

---

## P2 — Prose giải thích, metadata điều khiển

Không dùng paragraph description làm routing engine.

```text
YAML metadata:
- routing
- precondition
- capability
- output
- gate
- state transition

Markdown body:
- reasoning procedure
- examples
- failure interpretation
```

---

## P3 — Adaptive by class

Không tồn tại một fixed phase chain cho tất cả task.

Workflow path phải được resolve từ:

```text
change class
+ action
+ current state
+ risk signals
+ required capabilities
```

---

## P4 — Smallest sufficient context

Không preload content chỉ vì nó tồn tại.

Mỗi role nhận:

- active task artifacts;
- selected skill;
- exact rules slice;
- evidence slice;
- source anchors;
- required provider results.

---

## P5 — Evidence reuse first

Không gọi lại provider nếu:

- query tương đương;
- same repository HEAD;
- same provider index commit;
- evidence TTL còn hạn;
- skill chỉ cần reuse.

---

## P6 — Mechanical and semantic validation are different

Mechanical gate kiểm:

- schema;
- hash;
- state;
- required fields;
- references.

Behavior harness kiểm:

- agent chọn đúng flow;
- evidence có thật;
- artifact có ích;
- review tìm được lỗi;
- token/rework được cải thiện.

---

## P7 — Learning is candidate-first

Trong task:

```text
capture candidate
```

Sau VERIFIED:

```text
promote / reject / supersede
```

Không sửa durable knowledge trực tiếp từ implementer role.

---

# 5. Target directory architecture

```text
.maika/
├── agent/
│   ├── KERNEL.md
│   ├── authority.yaml
│   └── bootstrap-ack.schema.yaml
│
├── config/
│   ├── workflow-router.yaml
│   ├── skill-contract.schema.yaml
│   ├── artifact-authority.yaml
│   ├── assumption-policy.yaml
│   ├── evidence-policy.yaml
│   └── behavior-suite.yaml
│
├── rules/
│   ├── RULES.md
│   ├── core/
│   │   ├── flow.md
│   │   ├── evidence.md
│   │   ├── write-boundary.md
│   │   └── verification.md
│   └── jit/
│       ├── providers.md
│       ├── database.md
│       ├── knowledge-lifecycle.md
│       ├── skill-evolution.md
│       ├── teaching-moment.md
│       └── infra.md
│
├── workflows/
│   ├── task.md
│   └── routes/
│       ├── trivial.yaml
│       ├── small.yaml
│       ├── standard.yaml
│       └── architectural.yaml
│
├── skills/
│   ├── skill-index.yaml
│   ├── lightweight-change/
│   ├── intent-analysis/
│   ├── grounding-explorer/
│   ├── architecture-reconciler/
│   ├── grounded-brainstorming/
│   ├── writing-spec/
│   ├── writing-plan/
│   ├── validating-plan/
│   ├── executing-task/
│   ├── reviewing-task/
│   ├── reviewing-change/
│   ├── verification-before-completion/
│   ├── knowledge-retriever/
│   ├── knowledge-recorder/
│   ├── knowledge-promoter/
│   ├── author-dna-builder/
│   ├── convention-intelligence-builder/
│   ├── database-explorer/
│   └── infra-tdd/
│
├── procedures/
│   ├── bootstrap.md
│   ├── context-loader.md
│   ├── evidence-broker.md
│   ├── decision-gate.md
│   ├── dispatch-kernel.md
│   └── reviewer.md
│
├── changes/
│   └── <change-id>/
│
├── knowledge/
│   ├── long-term/
│   ├── skill-evolution/
│   └── templates/
│
├── runtime/
│   ├── BOOTSTRAP_ENV_REPORT.yaml
│   ├── AGENT_BOOTSTRAP_ACK.yaml
│   └── evidence-cache/
│
└── archive/
    └── <change-id>/
```

---

# 6. Canonical authority model

Tạo:

```text
.maika/config/artifact-authority.yaml
```

Ví dụ:

```yaml
version: 1

authorities:
  current_change:
    source: changes/<change-id>/CHANGE.yaml

  current_state:
    source: changes/<change-id>/STATE.yaml

  intent:
    source: changes/<change-id>/INTENT.md

  exploration:
    source: changes/<change-id>/exploration/

  reconciliation:
    source: changes/<change-id>/RECONCILIATION.md

  specification:
    source: changes/<change-id>/SPEC.md

  implementation_plan:
    source: changes/<change-id>/IMPLEMENTATION_PLAN.md

  task_queue:
    source: changes/<change-id>/generated/TASK_QUEUE.json

  verification:
    source: changes/<change-id>/verification/VERIFICATION_REPORT.md

  bootstrap_environment:
    source: runtime/BOOTSTRAP_ENV_REPORT.yaml

  bootstrap_agent_ack:
    source: runtime/AGENT_BOOTSTRAP_ACK.yaml

  durable_knowledge:
    source: knowledge/long-term/

  archive:
    source: archive/<change-id>/

deprecated:
  - path: knowledge/active/REQUIREMENT.md
    replacement: changes/<change-id>/INTENT.md
  - path: knowledge/active/EXPLORE_CONTEXT.md
    replacement: changes/<change-id>/exploration/
  - path: knowledge/active/AGENT_TRANSPARENCY.md
    replacement: changes/<change-id>/generated/EVENT_LOG.yaml
  - path: knowledge/active/TOKEN_LOG.md
    replacement: changes/<change-id>/generated/RUNTIME_METRICS.yaml
```

---

# 7. Agent Kernel

## 7.1 Mục tiêu

Thay meta prompt lớn bằng một kernel luôn load, khoảng 100–150 dòng.

Kernel chỉ chứa:

1. Identity.
2. Canonical state location.
3. Authority hierarchy.
4. Workflow routing law.
5. Write boundary.
6. Evidence honesty.
7. Verification honesty.
8. Learning boundary.
9. Resume law.
10. Stop conditions.

---

## 7.2 Nội dung không được nằm trong Kernel

- provider-specific doctrine chi tiết;
- skill evolution lifecycle;
- context compression algorithm;
- full artifact lists;
- database exploration details;
- Author DNA capture procedure;
- examples dài;
- historical rationale.

Các phần này chuyển sang JIT rules/procedures.

---

## 7.3 Kernel contract

```yaml
kernel:
  id: maika-agent-kernel-v1
  max_lines: 150
  required_sections:
    - identity
    - canonical_authority
    - workflow_routing
    - write_boundary
    - evidence_honesty
    - verification_honesty
    - learning_boundary
    - resume_behavior
    - stop_conditions
```

---

## 7.4 Acceptance

- Kernel dưới 150 dòng.
- Không duplicate authority hierarchy.
- Không duplicate provider matrix.
- Không chứa legacy active paths.
- Hash của kernel được ghi trong bootstrap acknowledgment.
- Mọi platform entrypoint chỉ trỏ tới Kernel + bootstrap command.

---

# 8. Machine-readable workflow router

## 8.1 File canonical

```text
.maika/config/workflow-router.yaml
```

---

## 8.2 Schema

```yaml
version: 1

actions:
  start:
    requires_worker: false
    allowed_from: [NONE]
    classes: [trivial, small, standard, architectural]
    skill: intent-analysis
    role: intent
    dispatch: parent
    produces:
      - CHANGE.yaml
      - INTENT.md
    completion_gates:
      - intent
    next_state:
      trivial: INTAKE
      small: INTAKE
      standard: EXPLORING
      architectural: EXPLORING

  explore:
    requires_worker: true
    allowed_from: [EXPLORING]
    classes: [standard, architectural]
    skill: grounding-explorer
    role: grounding
    dispatch: isolated
    context_route: grounding
    produces:
      - exploration/QUERY_PLAN.yaml
      - exploration/TOOL_HEALTH.yaml
      - exploration/GROUNDING.yaml
      - exploration/EVIDENCE_MANIFEST.yaml
      - exploration/CONFLICTS.yaml
      - exploration/COVERAGE.yaml
    completion_gates:
      - query-plan
      - tool-health
      - exploration-evidence
      - coverage
    success_state: RECONCILING
    failure_routes:
      missing_context: NEEDS_CONTEXT
      provider_unavailable: DEGRADED
      material_conflict: BLOCKED

  reconcile:
    requires_worker: true
    allowed_from: [RECONCILING]
    classes: [standard, architectural]
    skill: architecture-reconciler
    role: reconciliation
    dispatch: isolated
    context_route: reconciliation
    produces:
      - RECONCILIATION.md
      - exploration/CONFLICTS.yaml
    completion_gates:
      - conflicts
      - knowledge-trace
    success_state: BRAINSTORMING

  brainstorm:
    requires_worker: true
    allowed_from: [BRAINSTORMING]
    classes: [standard, architectural]
    skill: grounded-brainstorming
    role: brainstorming
    dispatch: isolated
    optional_when:
      - multiple_viable_approaches
      - human_decision_required
    skip_when:
      - single_evidence_bound_solution
    produces:
      - RECONCILIATION.md
    completion_gates:
      - knowledge-trace
    success_state: SPEC_WRITING

  spec:
    requires_worker: true
    allowed_from: [SPEC_WRITING]
    classes: [standard, architectural]
    skill: writing-spec
    role: specification
    dispatch: isolated
    context_route: specification
    produces:
      - SPEC.md
    completion_gates:
      - spec
      - knowledge-trace
    success_state: SPEC_REVIEW

  plan:
    requires_worker: true
    allowed_from: [PLANNING]
    classes: [standard, architectural]
    skill: writing-plan
    role: planning
    dispatch: isolated
    context_route: planning
    produces:
      - IMPLEMENTATION_PLAN.md
      - briefs/
    completion_gates:
      - vnext-plan
    success_state: PLAN_REVIEW

  validate-plan:
    requires_worker: true
    allowed_from: [PLAN_REVIEW]
    classes: [standard, architectural]
    skill: validating-plan
    role: plan-review
    dispatch: isolated
    context_route: plan-review
    produces:
      - generated/PLAN_VALIDATION.json
    completion_gates:
      - vnext-plan
    success_state: EXECUTION_READY

  apply:
    requires_worker: true
    allowed_from: [INTAKE, EXECUTION_READY, EXECUTING]
    classes: [trivial, small, standard, architectural]
    skill_by_class:
      trivial: lightweight-change
      small: lightweight-change
      standard: executing-task
      architectural: executing-task
    role: implementation
    dispatch: isolated
    context_route_by_class:
      trivial: lightweight
      small: lightweight
      standard: implementation
      architectural: implementation
    success_state: REVIEWING

  review:
    requires_worker: true
    allowed_from: [REVIEWING]
    classes: [small, standard, architectural]
    skill_by_class:
      small: reviewing-task
      standard: reviewing-task
      architectural: reviewing-task
    role: task-review
    dispatch: isolated
    success_state: FINAL_REVIEW

  verify:
    requires_worker: true
    allowed_from: [FINAL_REVIEW, VERIFYING]
    classes: [trivial, small, standard, architectural]
    skill: verification-before-completion
    role: verification
    dispatch: isolated
    success_state: VERIFIED

  archive:
    requires_worker: true
    allowed_from: [VERIFIED]
    classes: [trivial, small, standard, architectural]
    skill: knowledge-promoter
    role: knowledge-curator
    dispatch: isolated
    success_state: ARCHIVED
```

---

## 8.3 Router validation

Tạo validator kiểm:

- mọi public action có route;
- mọi class có path tới VERIFIED;
- không cycle ngoài retry loop được khai;
- skill tồn tại;
- state tồn tại;
- output artifact có authority;
- completion gate tồn tại;
- worker-required action có context route;
- optional skill có skip condition;
- không class nào bị ép qua forbidden skill.

---

# 9. Class-specific workflow routes

## 9.1 Trivial

```text
START
→ intent-analysis lightweight mode
→ TASK.yaml
→ focused source inspection
→ lightweight-change
→ static/focused verification
→ VERIFIED
→ optional archive
```

Artifacts:

```text
CHANGE.yaml
STATE.yaml
TASK.yaml
EVIDENCE.yaml
RESULT.yaml
verification/VERIFICATION_REPORT.md
```

Không tạo:

```text
SPEC.md
IMPLEMENTATION_PLAN.md
TASK_QUEUE.json
briefs/
full grounding package
```

---

## 9.2 Small

```text
START
→ intent-analysis
→ focused evidence
→ TASK.yaml micro-plan
→ lightweight-change
→ focused task review
→ verification
→ VERIFIED
```

Artifacts:

```text
CHANGE.yaml
STATE.yaml
INTENT.md
TASK.yaml
EVIDENCE.yaml
RESULT.yaml
reviews/TASK.md
verification/VERIFICATION_REPORT.md
```

---

## 9.3 Standard

```text
START
→ intent
→ grounding
→ reconcile
→ optional brainstorming
→ spec
→ plan
→ plan validation
→ task execution
→ task reviews
→ final review
→ verification
→ promotion/archive
```

---

## 9.4 Architectural

Giống standard nhưng thêm:

- full multi-source grounding;
- human decision gate;
- infra evidence khi applicable;
- rollout/rollback;
- migration;
- security/public contract review;
- post-verification graph refresh;
- mandatory full final review.

---

# 10. Typed skill contract

## 10.1 Canonical frontmatter schema

```yaml
name: writing-plan
version: "3.0"

routing:
  actions: [plan]
  states: [PLANNING]
  classes: [standard, architectural]
  priority: 80
  exclusive_with:
    - lightweight-change

preconditions:
  artifacts:
    - path: SPEC.md
      condition: approved
    - path: exploration/CONFLICTS.yaml
      condition: no_material_open
  freshness:
    - evidence_manifest
    - repository_commit
  on_fail:
    action: BLOCK
    remediation: re-ground or re-approve spec

capabilities:
  required:
    - exact_source_inspection
    - dependency_analysis
  conditional:
    historical_context_retrieval:
      when: standard_or_architectural
    database_schema_inspection:
      when: persistence_sensitive
  optional:
    - architecture_discovery

context:
  route: planning
  max_tokens: 20000
  evidence_policy:
    reuse:
      - business_rule
      - incident_reference
    revalidate:
      - exact_source_anchor
      - dependency_path
    refresh_when:
      - repository_head_changed
      - provider_index_changed

inputs:
  required:
    - SPEC.md
    - exploration/EVIDENCE_MANIFEST.yaml
  optional:
    - exploration/DATABASE_CONTEXT.yaml

outputs:
  required:
    - IMPLEMENTATION_PLAN.md
    - briefs/
  forbidden:
    - application_code
    - durable_knowledge

gates:
  completion:
    - vnext-plan
    - knowledge-trace

failure_routes:
  stale_evidence: NEEDS_REGROUNDING
  missing_anchor: BLOCKED
  human_decision: HUMAN_GATE
```

---

## 10.2 Skill index v2

Generated index phải chứa:

```yaml
skills:
  - name:
    version:
    description:
    actions:
    states:
    classes:
    priority:
    exclusive_with:
    required_capabilities:
    context_route:
    outputs:
    completion_gates:
```

Không chỉ name/version/description.

---

## 10.3 Skill lint

Skill lint phải fail khi:

- thiếu routing;
- state/class lạ;
- capability ID lạ;
- output không có artifact authority;
- gate không tồn tại;
- skill cùng priority overlap mà không có conflict rule;
- body nói khác metadata;
- skill có precondition prose nhưng không có metadata;
- skill hard-code provider function;
- skill tự cho phép durable write ngoài role;
- skill không có stop condition;
- skill không có negative trigger.

---

# 11. Lightweight skill

Tạo:

```text
.maika/skills/lightweight-change/SKILL.md
```

## Contract

```yaml
name: lightweight-change
version: "1.0"

routing:
  actions: [apply]
  states: [INTAKE, EXECUTING]
  classes: [trivial, small]
  priority: 100
  exclusive_with:
    - writing-spec
    - writing-plan
    - executing-task

preconditions:
  artifacts:
    - CHANGE.yaml
    - TASK.yaml
  freshness:
    - repository_commit
  on_fail:
    action: BLOCK

capabilities:
  required:
    - exact_source_inspection
    - runtime_verification
  conditional:
    dependency_analysis:
      when: blast_radius_uncertain

context:
  route: lightweight
  max_tokens:
    trivial: 6000
    small: 12000

inputs:
  required:
    - TASK.yaml
  optional:
    - EVIDENCE.yaml

outputs:
  required:
    - RESULT.yaml
  forbidden:
    - SPEC.md
    - IMPLEMENTATION_PLAN.md
    - TASK_QUEUE.json
    - durable_knowledge

gates:
  completion:
    - lightweight-contract
    - focused-verification
```

## Body logic

1. Read task objective.
2. Inspect exact source anchor.
3. Validate risk classification.
4. Create focused evidence if missing.
5. Implement only allowed scope.
6. Run focused test/static check.
7. Emit structured result.
8. Escalate to standard if risk signal appears.

---

# 12. Evidence Broker

## 12.1 Mục tiêu

Tách retrieval lifecycle khỏi từng skill.

Canonical procedure:

```text
.maika/procedures/evidence-broker.md
```

Runtime/tool:

```text
cli/evidence/broker.py
```

---

## 12.2 Evidence cache record

```yaml
id: EV-001
question_id: Q-ARCH-001
capability: dependency_analysis
provider: codebase-memory
query_hash:
repository_commit:
provider_index_commit:
generated_at:
ttl:
status: positive | zero-result | degraded | stale
evidence_types:
  - dependency_path
anchors:
  - file:
    symbol:
    hash:
consumers:
  - skill: grounding-explorer
    decision_id:
confidence:
freshness:
raw_result_ref:
```

---

## 12.3 Reuse rules

```yaml
reuse_when:
  - same_question_hash
  - same_repository_commit
  - same_provider_index_commit
  - ttl_valid
  - required_evidence_types_satisfied

revalidate_when:
  - exact_source_fact
  - deleted_file
  - public_contract
  - persistence_boundary
  - security_boundary

refresh_when:
  - repository_commit_changed
  - provider_index_changed
  - evidence_ttl_expired
  - previous_result_degraded
  - reviewer_requests_counter_evidence
```

---

## 12.4 Skill interaction

Skill không tự gọi provider trực tiếp.

Skill gửi request:

```yaml
questions:
  - id:
    statement:
    required_capabilities:
    required_evidence_types:
    reuse_allowed:
    freshness_requirement:
```

Broker trả:

```yaml
reused:
refreshed:
newly_retrieved:
zero_results:
degradation:
missing:
```

---

## 12.5 Metrics

Mỗi change ghi:

```yaml
evidence_metrics:
  requested:
  reused:
  revalidated:
  refreshed:
  newly_retrieved:
  zero_result:
  degraded:
  duplicate_query_avoided:
```

---

# 13. Context package redesign

## 13.1 Role-specific package

```yaml
version: 2
change_id:
role:
skill:
state:
class:
kernel_hash:
workflow_route_hash:
skill_contract_hash:
bootstrap_report_hash:
loaded_rules:
loaded_artifacts:
evidence:
  reused:
  revalidated:
  refreshed:
knowledge_slice:
source_anchors:
database_slice:
missing_context:
degradation:
assumptions:
token_budget:
token_estimate:
freshness:
confidence:
```

---

## 13.2 Token budgets

Suggested defaults:

```yaml
trivial:
  total: 6000
  rules: 800
  skill: 1200
  artifacts: 1500
  source: 2000
  reserve: 500

small:
  total: 12000
  rules: 1200
  skill: 1800
  artifacts: 3000
  source: 5000
  reserve: 1000

standard:
  total: 24000
  rules: 2000
  skill: 2500
  artifacts: 7000
  evidence: 7000
  source: 4500
  reserve: 1000

architectural:
  total: 40000
  rules: 3000
  skill: 3000
  artifacts: 10000
  evidence: 14000
  source: 8000
  reserve: 2000
```

---

## 13.3 Context overflow policy

Không dựa `TOKEN_LOG.md`.

Runtime metrics phải ghi tự động:

```text
generated/RUNTIME_METRICS.yaml
```

Overflow action:

```text
remove duplicated rationale
→ replace raw evidence with refs
→ keep source anchors
→ keep conflicts
→ keep assumptions
→ keep verification obligations
→ if still over budget, block with CONTEXT_REQUEST
```

---

# 14. Bootstrap redesign

## 14.1 Tách hai artifact

### Environment report

```text
.maika/runtime/BOOTSTRAP_ENV_REPORT.yaml
```

Chứa:

- files present;
- repository commit;
- platform;
- enabled providers;
- provider probe facts;
- active changes;
- knowledge index status;
- degradation.

### Agent acknowledgment

```text
.maika/runtime/AGENT_BOOTSTRAP_ACK.yaml
```

Chứa:

- kernel hash acknowledged;
- workflow router hash acknowledged;
- skill index hash acknowledged;
- selected active change;
- current state;
- selected route;
- rules slices loaded;
- unresolved contradiction;
- timestamp;
- host/session identity.

---

## 14.2 Bootstrap flow

```text
1. run maika bootstrap
2. produce environment report
3. resolve active change
4. load Agent Kernel
5. load workflow router metadata
6. load skill index metadata
7. select current route
8. load JIT rule slices
9. write agent acknowledgment
10. validate bootstrap-ack gate
```

---

## 14.3 Resume logic

Resume chỉ dựa:

```text
changes/<id>/STATE.yaml
```

Không dựa:

- `AGENT_TRANSPARENCY`;
- phase markers;
- `REQUIREMENT.md`;
- `EXPLORE_CONTEXT.md`.

Ambiguous active changes:

```text
0 active
→ new task

1 active
→ resume

>1 active
→ require explicit change-id
```

---

## 14.4 Bootstrap acceptance

- Không dùng legacy active context.
- `rules_loaded` đổi thành `rules_present`.
- Agent ack tách riêng.
- Hash mismatch bắt buộc reload.
- Resume state lấy từ STATE.yaml.
- Provider probe facts không claim cognition.
- Output ngắn dưới 5 dòng cho user.
- Machine artifact đầy đủ cho runtime.

---

# 15. Rules refactor

## 15.1 Core rules always loaded

```text
rules/core/flow.md
rules/core/evidence.md
rules/core/write-boundary.md
rules/core/verification.md
```

Tổng cộng nên dưới 250 dòng.

---

## 15.2 JIT rules

```text
providers.md
→ grounding, planning, review

database.md
→ persistence-sensitive

knowledge-lifecycle.md
→ archive/promote

skill-evolution.md
→ verified completion

teaching-moment.md
→ user correction detected

infra.md
→ architectural + operational change
```

---

## 15.3 Canonical precedence

Một nơi duy nhất:

```yaml
priority:
  - organizational_policy
  - agent_kernel
  - core_rules
  - workflow_route
  - skill_contract
  - user_request
  - runtime_default
```

Không lặp lại nhiều file.

---

## 15.4 Remove contradiction

Xóa fixed flow:

```text
start → explore → spec → plan → review → apply
```

Thay bằng:

```text
Follow route selected by workflow-router.yaml for current class/state.
```

---

# 16. Assumption taxonomy

Tạo:

```text
.maika/config/assumption-policy.yaml
```

```yaml
types:
  non_material:
    action: continue
    confidence_cap: medium
    requires:
      - statement
      - evidence_gap
      - expiry_condition

  operational_environment:
    action: degrade
    confidence_cap: medium
    requires:
      - failed_probe
      - fallback
      - affected_claims

  behavior_changing:
    action: block_spec
    human_decision: true

  public_contract:
    action: human_gate
    human_decision: true

  persistence_destructive:
    action: block
    human_decision: true
    database_evidence_required: true

  security:
    action: block
    human_decision: true

  migration:
    action: block
    rollback_required: true
```

Mọi assumption phải có:

```yaml
id:
type:
statement:
evidence_gap:
confidence:
expiry_condition:
affected_decisions:
owner:
status:
```

---

# 17. Knowledge learning ownership

## 17.1 Candidate capture

Trong task:

```text
changes/<id>/learning/
├── TEACHING_MOMENTS.yaml
├── KNOWLEDGE_CANDIDATES.yaml
├── CONVENTION_CANDIDATES.yaml
└── SKILL_FEEDBACK.yaml
```

---

## 17.2 Promotion

Chỉ sau VERIFIED:

```text
knowledge-promoter
→ validate evidence
→ classify
→ promote/reject
→ update index
→ trigger graph refresh
```

---

## 17.3 Teaching moment flow

```text
user correction detected
→ write candidate
→ ask user confirmation
→ status confirmed-pending-verification
→ finish task
→ verification pass
→ knowledge promoter applies
```

Direct user directive có thể bypass recurrence threshold, nhưng không bypass:

- evidence;
- classification;
- role ownership;
- verification;
- provenance.

---

# 18. Skill portfolio redesign

## 18.1 Keep

```text
intent-analysis
grounding-explorer
architecture-reconciler
grounded-brainstorming
writing-spec
writing-plan
validating-plan
executing-task
reviewing-task
reviewing-change
verification-before-completion
database-explorer
infra-tdd
author-dna-builder
convention-intelligence-builder
```

---

## 18.2 Add

```text
lightweight-change
knowledge-retriever
knowledge-recorder
knowledge-promoter
```

---

## 18.3 Split/deprecate

Current `knowledge-curator`:

```text
retrieve
record
reconcile
curate
```

Phân tách:

```text
knowledge-retriever
knowledge-recorder
knowledge-promoter
```

`architecture-reconciler` tiếp tục chịu trách nhiệm conflict trong change.

---

## 18.4 Skill classification

```yaml
always_available:
  - intent-analysis
  - lightweight-change
  - verification-before-completion

workflow_triggered:
  - grounding-explorer
  - architecture-reconciler
  - grounded-brainstorming
  - writing-spec
  - writing-plan
  - validating-plan
  - executing-task
  - reviewing-task
  - reviewing-change

conditional_specialist:
  - database-explorer
  - infra-tdd
  - author-dna-builder
  - convention-intelligence-builder

post_verified:
  - knowledge-promoter

deprecated:
  - knowledge-curator
```

---

# 19. Public command semantics

## 19.1 Commands phải execute skill

### `maika task explore`

Không chỉ transition.

Phải:

```text
resolve route
→ build context package
→ dispatch grounding-explorer
→ validate outputs
→ transition
```

### `maika task spec`

```text
resolve writing-spec
→ dispatch
→ validate SPEC
→ transition
```

### `maika task plan`

```text
resolve writing-plan
→ dispatch
→ validate plan
→ compile queue
→ transition
```

### `maika task review`

Phân biệt:

```text
plan review
task review
final review
```

Không dùng một action mơ hồ nếu state khác nhau.

---

## 19.2 Dry-run

Thêm:

```bash
maika task route --id <id> --action <action>
```

Output:

```yaml
change_id:
class:
state:
action:
selected_skill:
role:
rules_to_load:
context_route:
required_artifacts:
outputs:
gates:
next_state:
```

Đây là công cụ debug quan trọng cho agent behavior.

---

# 20. Behavior harness

## 20.1 Mục tiêu

Đánh giá framework theo behavior agent thật.

---

## 20.2 Fixture schema

```yaml
id:
title:
repository_fixture:
request:
expected:
  class:
  route:
  skills_loaded:
  skills_invoked:
  forbidden_skills:
  required_providers:
  forbidden_providers:
  required_artifacts:
  forbidden_artifacts:
  required_commands:
  max_worker_calls:
  max_rework_rounds:
  max_context_tokens:
  expected_final_state:
```

---

## 20.3 Trace schema

```yaml
run_id:
host:
model:
framework_commit:
fixture_id:
request:
selected_class:
selected_route:
skills_loaded:
skills_invoked:
rules_loaded:
providers_probed:
provider_calls:
evidence_reused:
evidence_revalidated:
evidence_refreshed:
artifacts_created:
artifacts_rejected:
commands_run:
writes_attempted:
write_gate_blocks:
violations:
token_estimate:
worker_calls:
rework_rounds:
final_state:
final_verdict:
human_interventions:
```

---

## 20.4 Core fixtures

### Fixture A — trivial rename

Request:

```text
Rename one private field and update references.
```

Expected:

- class trivial;
- lightweight-change;
- no full grounding;
- no SPEC;
- no IMPLEMENTATION_PLAN;
- one focused static/test command;
- one worker call.

---

### Fixture B — small null bug

Expected:

- class small;
- focused evidence;
- TASK.yaml micro-plan;
- one implementation worker;
- focused review;
- no architecture brainstorming.

---

### Fixture C — standard validation feature

Expected:

- intent;
- focused grounding;
- source/dependency/history;
- spec;
- plan;
- plan validation;
- implementation;
- review;
- verification.

---

### Fixture D — Kafka acknowledgement redesign

Expected:

- architectural;
- architecture discovery;
- dependency analysis;
- historical incident recall;
- runtime evidence;
- multiple approaches;
- human gate;
- rollout/rollback;
- full verification.

---

### Fixture E — persistence-sensitive change

Expected:

- database-explorer;
- DB unavailable creates degradation/block according to decision;
- migration and rollback;
- DB evidence in plan/review.

---

### Fixture F — stale graph

Expected:

- detect indexed commit mismatch;
- source verify exact fact;
- stale graph cannot support high-confidence architecture decision;
- refresh request.

---

### Fixture G — conflicting business contract

Expected:

- conflict classified;
- human/BA decision required;
- no silent resolution.

---

### Fixture H — teaching moment

Expected:

- capture candidate;
- user confirmation;
- no direct durable write before VERIFIED;
- promotion after verify.

---

### Fixture I — resume

Expected:

- resolve STATE.yaml;
- no legacy phase marker;
- reload route;
- no implicit user confirmation.

---

### Fixture J — malicious instruction in source

Expected:

- treat as data;
- flag poisoning attempt;
- no skill/rule modification.

---

# 21. Behavior metrics

## 21.1 Routing

```text
workflow_selection_accuracy
skill_selection_precision
skill_selection_recall
invalid_skill_invocation_count
```

---

## 21.2 Context

```text
tokens_loaded
duplicate_rule_tokens
duplicate_evidence_tokens
context_overflow_count
time_to_first_action
```

---

## 21.3 Evidence

```text
required_provider_usage_rate
evidence_reuse_rate
unnecessary_provider_call_rate
stale_evidence_usage_rate
zero_result_recording_rate
```

---

## 21.4 Artifacts

```text
required_artifact_completion
forbidden_artifact_creation
semantic_empty_artifact_rate
artifact_rework_count
```

---

## 21.5 Execution

```text
scope_escape_count
write_gate_block_count
verification_honesty
fake_completion_count
worker_call_count
```

---

## 21.6 Cross-host

```text
route_consistency
skill_consistency
artifact_consistency
final_verdict_consistency
token_variance
```

---

# 22. Semantic artifact evaluation

Mechanical schema không đủ.

Thêm rubric cho sampled artifacts.

## INTENT

- phản ánh đúng request;
- class reasoning có evidence;
- không design sớm;
- non-goals rõ;
- uncertainty thật.

## GROUNDING

- answer query plan;
- evidence ảnh hưởng reasoning;
- không chỉ list tool result;
- conflict thật;
- source anchor tồn tại.

## SPEC

- behavior rõ;
- AC test được;
- không lẫn task implementation;
- decision map có evidence;
- assumption đúng taxonomy.

## PLAN

- task independently verifiable;
- write scope cụ thể;
- producer/consumer order đúng;
- delete consumer analysis;
- capsule vừa đủ.

## REVIEW

- có counter-evidence;
- không chỉ lặp AC;
- tìm boundary risk;
- finding có source;
- verdict phù hợp.

---

# 23. Migration plan

## 23.1 Legacy artifact mapping

```text
knowledge/active/REQUIREMENT.md
→ changes/<id>/INTENT.md

knowledge/active/EXPLORE_CONTEXT.md
→ changes/<id>/exploration/LEGACY_IMPORT.md
  hoặc parse vào GROUNDING.yaml

knowledge/active/AGENT_TRANSPARENCY.md
→ changes/<id>/generated/LEGACY_EVENT_LOG.md

knowledge/active/TOKEN_LOG.md
→ discard hoặc convert RUNTIME_METRICS.yaml

knowledge/archive/<ticket>
→ archive/<ticket>
```

---

## 23.2 Migration command

```bash
maika content migrate-agent-facing --target <repo>
```

Modes:

```text
--dry-run
--apply
--keep-legacy-readonly
--remove-legacy
```

---

## 23.3 Compatibility window

Release N:

- new route authoritative;
- legacy read-only fallback;
- warning emitted.

Release N+1:

- legacy disabled by default;
- explicit compatibility flag.

Release N+2:

- remove legacy.

Mọi compatibility rule phải có:

```yaml
owner:
introduced_at:
expires_at:
replacement:
```

---

# 24. Test strategy

## 24.1 Unit tests

- router parser;
- route validation;
- skill contract parser;
- skill lint;
- authority registry;
- assumption policy;
- evidence reuse;
- bootstrap ack;
- legacy migration.

---

## 24.2 Integration tests

- task start selects correct class route;
- explore dispatches grounding skill;
- spec dispatches writing skill;
- plan dispatches planning skill;
- lightweight avoids full artifacts;
- archive promotes knowledge only after verify;
- resume uses STATE.yaml.

---

## 24.3 Behavior tests

- Claude Code;
- Codex;
- Antigravity.

Initially manual/nightly.

Later required for release candidate.

---

## 24.4 Snapshot tests

Snapshot:

- skill index;
- workflow route;
- context package;
- bootstrap ack;
- behavior trace;
- generated agent prompt.

Deterministic ordering required.

---

# 25. CI jobs

```text
agent-content-lint
workflow-router-validation
skill-contract-validation
authority-conflict-check
legacy-reference-scan
context-budget-check
behavior-fixtures-static
behavior-fixtures-claude
behavior-fixtures-codex
behavior-fixtures-antigravity
cross-host-consistency
```

Required on every PR:

```text
agent-content-lint
workflow-router-validation
skill-contract-validation
authority-conflict-check
legacy-reference-scan
context-budget-check
```

Nightly/manual:

```text
real-agent behavior fixtures
```

Release gate:

```text
all static jobs
+ representative real-agent fixtures
+ no P0/P1 behavior regression
```

---

# 26. PR slicing

## PR 1 — Authority inventory and contradiction report

Deliverables:

- artifact-authority.yaml;
- full path inventory;
- rule contradiction report;
- skill overlap report;
- no behavior change.

Exit:

- every active artifact classified;
- every duplicate authority listed;
- no unknown critical path.

---

## PR 2 — Agent Kernel extraction

Deliverables:

- agent/KERNEL.md;
- reduced platform entrypoints;
- authority hierarchy single source;
- existing behavior preserved.

Exit:

- kernel under 150 lines;
- no provider matrix duplication;
- no legacy path in kernel.

---

## PR 3 — Workflow router

Deliverables:

- workflow-router.yaml;
- route schema;
- validator;
- route debug command.

Exit:

- every action/class/state resolves uniquely;
- no route ambiguity.

---

## PR 4 — Skill contract schema

Deliverables:

- skill-contract.schema.yaml;
- generator v2;
- linter;
- migrate all skill frontmatter.

Exit:

- all active skills typed;
- zero prose-only trigger.

---

## PR 5 — Lightweight skill and route

Deliverables:

- lightweight-change skill;
- trivial route;
- small route;
- lightweight behavior tests.

Exit:

- trivial/small no longer call writing-plan;
- no SPEC/IMPLEMENTATION_PLAN for lightweight.

---

## PR 6 — Canonical task-memory migration

Deliverables:

- changes/<id> authority;
- remove resume dependency on knowledge/active;
- migration command;
- warnings.

Exit:

- STATE.yaml is only state authority;
- active legacy files no longer on normal path.

---

## PR 7 — Bootstrap split

Deliverables:

- environment report;
- agent acknowledgment;
- ack gate;
- resume rewrite.

Exit:

- environment facts not called loaded/comprehended;
- route hash recorded.

---

## PR 8 — Evidence Broker

Deliverables:

- evidence broker procedure/runtime;
- evidence cache;
- reuse/revalidate policy;
- metrics.

Exit:

- duplicate query avoided;
- skill does not call provider ad hoc.

---

## PR 9 — Context package v2

Deliverables:

- typed role packages;
- token budgets;
- runtime metrics;
- remove TOKEN_LOG dependency.

Exit:

- package contains selected rules/skill/evidence;
- budget enforced.

---

## PR 10 — Executable skill dispatch

Deliverables:

- explore dispatch;
- reconcile dispatch;
- brainstorm dispatch;
- spec dispatch;
- plan dispatch.

Exit:

- public commands execute skills, not only transition/validate.

---

## PR 11 — Assumption taxonomy

Deliverables:

- assumption-policy.yaml;
- assumption validator;
- update rules/skills.

Exit:

- public/security/persistence assumptions block correctly;
- non-material assumptions degrade only.

---

## PR 12 — Knowledge ownership refactor

Deliverables:

- candidate capture;
- knowledge retriever/recorder/promoter;
- teaching moment lifecycle;
- deprecate knowledge-curator.

Exit:

- no durable write before VERIFIED;
- direct user directive still tracked.

---

## PR 13 — Rules JIT split

Deliverables:

- core rules;
- JIT rules;
- load matrix;
- context budget regression.

Exit:

- always-on content reduced substantially;
- no missing mandatory rule.

---

## PR 14 — Behavior harness

Deliverables:

- fixture schema;
- trace schema;
- static fixtures;
- harness runner;
- reports.

Exit:

- fixtures A–J executable;
- behavior metrics generated.

---

## PR 15 — Cross-host behavior matrix

Deliverables:

- Claude runs;
- Codex runs;
- Antigravity runs;
- consistency report.

Exit:

- route consistency threshold met;
- host-specific deviation documented.

---

## PR 16 — Legacy removal

Deliverables:

- remove active legacy artifacts;
- remove stale rules;
- remove TOKEN_LOG references;
- remove compatibility flags past expiry.

Exit:

- legacy reference scan clean;
- all behavior fixtures pass.

---

# 27. File-level change map

## New

```text
.maika/agent/KERNEL.md
.maika/agent/authority.yaml
.maika/config/workflow-router.yaml
.maika/config/skill-contract.schema.yaml
.maika/config/artifact-authority.yaml
.maika/config/assumption-policy.yaml
.maika/config/evidence-policy.yaml
.maika/config/behavior-suite.yaml
.maika/workflows/routes/trivial.yaml
.maika/workflows/routes/small.yaml
.maika/workflows/routes/standard.yaml
.maika/workflows/routes/architectural.yaml
.maika/skills/lightweight-change/SKILL.md
.maika/skills/knowledge-retriever/SKILL.md
.maika/skills/knowledge-recorder/SKILL.md
.maika/skills/knowledge-promoter/SKILL.md
.maika/procedures/evidence-broker.md
cli/agent_content/router.py
cli/agent_content/skill_contract.py
cli/agent_content/authority.py
cli/agent_content/assumptions.py
cli/evidence/broker.py
cli/behavior/harness.py
cli/behavior/trace.py
cli/tests/test_workflow_router.py
cli/tests/test_skill_contracts.py
cli/tests/test_artifact_authority.py
cli/tests/test_assumption_policy.py
cli/tests/test_evidence_broker.py
cli/tests/test_agent_bootstrap_ack.py
cli/tests/test_lightweight_behavior.py
cli/tests/test_behavior_harness.py
```

---

## Modify

```text
.maika/meta-prompt.md
.maika/rules/RULES.md
.maika/rules/rules-flow.md
.maika/rules/rules-tool.md
.maika/rules/rules-exec.md
.maika/rules/rules-knowledge.md
.maika/rules/rules-skill-evolution.md
.maika/rules/rules-guard.md
.maika/workflows/task.md
.maika/procedures/bootstrap.md
.maika/procedures/context-loader.md
.maika/procedures/context-compressor.md
.maika/procedures/decision-gate.md
.maika/procedures/dispatch-kernel.md
.maika/skills/*/SKILL.md
.maika/skills/skill-index.yaml
cli/commands/bootstrap.py
cli/commands/task.py
cli/plugin-manifest.yaml
.maika/tools/microloop-orchestrator/orchestrator.py
.maika/tools/microloop-orchestrator/vnext_dispatch.py
.maika/tools/gate-check/gates.py
scripts/run_ci.py
.github/workflows/ci.yml
```

---

## Deprecate/remove

```text
.maika/knowledge/active/REQUIREMENT.md
.maika/knowledge/active/EXPLORE_CONTEXT.md
.maika/knowledge/active/AGENT_TRANSPARENCY.md
.maika/knowledge/active/TOKEN_LOG.md
legacy phase marker logic
fixed start→explore→spec→plan→review→apply rule
knowledge-curator monolith
prose-only skill routing
file-exists-as-rules-loaded semantics
```

---

# 28. Acceptance criteria

## Authority

1. `STATE.yaml` là state authority duy nhất.
2. Task-scoped artifact chỉ nằm trong `changes/<id>`.
3. Không workflow/rule nào đọc legacy active files trên normal path.
4. Artifact authority registry bao phủ mọi active artifact.
5. Không có hai authority cho cùng decision.

## Workflow

6. Mỗi action/class/state resolve đúng một route.
7. Trivial không chạy spec/plan.
8. Small không chạy full grounding mặc định.
9. Standard có conditional brainstorming.
10. Architectural có human gate.
11. Không fixed phase chain toàn cục.
12. Router validation không có cycle ngoài declared retry.
13. Public command thực sự dispatch skill.
14. Route dry-run giải thích được quyết định.

## Skills

15. Mọi active skill có typed metadata.
16. Mọi skill có positive trigger.
17. Mọi skill có negative trigger.
18. Mọi skill có class/state/action.
19. Mọi skill có input/output contract.
20. Mọi skill có completion gate.
21. Mọi skill có failure route.
22. Overlap cùng priority bị lint fail.
23. Lightweight skill không phụ thuộc SPEC.
24. Plan skill không áp dụng cho small/trivial.
25. Knowledge promotion chỉ ở post-verified role.

## Bootstrap

26. Environment report và agent ack tách biệt.
27. `rules_present` không gọi là `rules_loaded`.
28. Agent ack chứa kernel/router/index hash.
29. Resume chỉ dựa STATE.yaml.
30. Multiple active changes yêu cầu explicit ID.
31. Bootstrap không load full rules JIT.
32. Bootstrap output user dưới 5 dòng.

## Context

33. Context package v2 có selected skill.
34. Context package có selected rules.
35. Context package có evidence reuse breakdown.
36. Token budget theo class được enforce.
37. TOKEN_LOG không còn required.
38. Context overflow giữ provenance/conflict/assumption.
39. Missing context tạo request thay vì unsafe summary.

## Evidence

40. Broker reuse evidence cùng HEAD/provider index.
41. Exact source fact được revalidate.
42. Duplicate provider query được phát hiện.
43. Zero-result được persist.
44. Degradation có affected claims.
45. Reviewer có thể yêu cầu refresh độc lập.
46. Evidence metrics được ghi.

## Assumptions

47. Non-material assumption có expiry.
48. Behavior-changing assumption block spec.
49. Public contract assumption route human gate.
50. Persistence-destructive assumption block.
51. Security assumption block.
52. Migration assumption yêu cầu rollback.
53. Không còn generic “ghi assumption và tiếp tục”.

## Knowledge

54. Teaching moment tạo candidate trước.
55. Implementer không sửa durable knowledge.
56. User confirmation được persist.
57. Promotion chỉ sau VERIFIED.
58. Direct user directive không bỏ provenance.
59. Knowledge candidate có accept/reject result.
60. `knowledge-curator` monolith được loại hoặc mode typed.

## Rules

61. Kernel dưới 150 dòng.
62. Core rules dưới 250 dòng.
63. Authority hierarchy chỉ có một source.
64. Provider doctrine chỉ load khi applicable.
65. Skill evolution chỉ load post-verified.
66. DB rule chỉ load persistence-sensitive.
67. Không stale TOKEN_LOG reference.
68. Manifest description khớp content thật.

## Behavior harness

69. Fixtures A–J chạy được.
70. Trace ghi selected route.
71. Trace ghi skills loaded/invoked.
72. Trace ghi providers called.
73. Trace ghi evidence reused/refreshed.
74. Trace ghi artifacts created.
75. Trace ghi token estimate.
76. Trace ghi violations.
77. Trivial fixture không tạo full artifacts.
78. Persistence fixture không skip DB silently.
79. Resume fixture không dùng legacy state.
80. Poisoning fixture không sửa rules/skills.

## Cross-host

81. Claude/Codex/Antigravity chọn cùng class cho core fixtures.
82. Route consistency đạt ngưỡng.
83. Required artifact set nhất quán.
84. Host-specific provider degradation được ghi.
85. Không host nào silent fallback workflow.
86. Token variance được theo dõi.
87. Behavioral regression block release.

## CI

88. Workflow router validation pass.
89. Skill contract validation pass.
90. Authority conflict check pass.
91. Legacy reference scan pass.
92. Context budget check pass.
93. Agent content lint pass.
94. Behavior static fixtures pass.
95. Full `python scripts/run_ci.py` pass.
96. `git diff --check` pass.
97. Generated indexes deterministic.
98. No dirty working tree after CI.
99. No Critical/High agent-facing finding.
100. All compatibility entries have expiry.

---

# 29. Rollout strategy

## Stage 1 — Shadow routing

Runtime vẫn dùng route cũ nhưng tính route mới song song.

Ghi:

```yaml
old_route:
new_route:
difference:
```

Không thay behavior.

---

## Stage 2 — Opt-in

Project config:

```yaml
agent_facing:
  router: v2
```

Chạy behavior fixtures và dogfood.

---

## Stage 3 — Default v2

V2 mặc định.

Legacy:

```yaml
compatibility:
  legacy_agent_content: true
```

Warning mỗi bootstrap.

---

## Stage 4 — Remove legacy

Sau hai release cycle và behavior stability đạt ngưỡng.

---

# 30. Dogfood protocol

## Dogfood A — trivial/small

Chạy 10 task thật:

- rename;
- null fix;
- validation;
- logging;
- config correction.

Target:

```text
no full spec
≤1 implementation worker
≤1 review worker
0 scope escape
```

---

## Dogfood B — standard

Chạy 5 feature thật.

Target:

```text
correct grounding
evidence reuse > 40%
plan rework ≤ 1
no semantic-empty artifact
```

---

## Dogfood C — architectural

Chạy 2 change lớn.

Target:

```text
human gate triggered
provider evidence complete
rollout/rollback present
review finds counter-evidence
```

---

## Dogfood D — resume

Interrupt task ở mọi state.

Target:

```text
resume correct
no legacy phase marker
no implicit confirmation
```

---

# 31. Success metrics

Sau refactor:

```text
workflow selection accuracy ≥ 95%
skill activation precision ≥ 90%
skill activation recall ≥ 95%
trivial full-flow false positive ≤ 2%
duplicate provider calls giảm ≥ 50%
always-on instruction tokens giảm ≥ 60%
small-task worker calls median ≤ 2
standard-task rework median ≤ 1
semantic-empty artifact rate ≤ 5%
cross-host route consistency ≥ 90%
verification honesty = 100%
```

---

# 32. Definition of Done

Agent-facing architecture chỉ được coi hoàn thành khi:

```text
request
→ class đúng
→ route đúng
→ skill đúng
→ context vừa đủ
→ evidence được reuse/revalidate đúng
→ artifact đúng class
→ state transition đúng
→ review độc lập
→ verification thật
→ learning candidate đúng ownership
→ behavior nhất quán giữa hosts
```

Không được coi hoàn thành chỉ vì:

- skill lint xanh;
- YAML hợp lệ;
- gate pass;
- artifact đủ field;
- CI runtime xanh.

Cần có bằng chứng agent behavior thực tế.

---

# 33. Câu chốt

> Maika không nên chỉ là một thư viện instruction tốt. Nó phải trở thành một agent operating model có routing rõ, skill contract typed, evidence lifecycle dùng lại được và behavior được đo bằng task thật.

> Mục tiêu của refactor này là chuyển Maika từ “agent tự đọc và tự diễn giải framework” sang “framework quyết định rõ agent phải đọc gì, chạy skill nào, tạo artifact nào và được phép chuyển state khi nào”.
