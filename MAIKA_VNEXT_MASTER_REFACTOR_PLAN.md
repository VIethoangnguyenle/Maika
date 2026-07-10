# Maika vNext — Master Refactor Implementation Plan (v2)

> **Purpose:** Refactor the Maika framework end-to-end into a grounded, evidence-driven, plan-first, subagent-dispatched development system.
>
> **Audience:** A capable coding agent acting as orchestrator, planner, implementer, and reviewer.
>
> **Execution rule:** This document is a **master program plan**, not permission to implement the entire repository in one unreviewable change. Execute it as ordered waves. Before coding each wave, produce a repository-verified Superpowers-style implementation plan containing exact files, symbols, tests, commands, expected failures, and code where appropriate.
>
> **Authority:** This v2 supersedes v1 (commit `437ae91`). The migration strategy follows **Design Spec Rev 2** (`docs/superpowers/specs/2026-07-10-vnext-plan-restructure-design.md`), which is authoritative where v1 and v2 differ. The target architecture of v1 is preserved except where Rev 2 explicitly changes it.

---

## 1. Goal

Transform Maika from:

```text
Strict workflow prose
+ OpenSpec change lifecycle
+ hard-coded MCP choreography
+ Apply-time task interpretation
+ partially isolated microloop
```

into:

```text
MCP-rich evidence dispatch
+ grounded brainstorming
+ native specification and code-level planning
+ deterministic plan compilation
+ fresh subagent dispatch per role/task
+ evidence-based gates
+ constrained execution
+ independent task and branch review
+ deterministic verification and archival
```

The resulting system must:

1. Understand the current codebase and business domain before proposing a design.
2. Use MCPs and other tools as capabilities, not as a globally hard-coded call sequence.
3. Produce detailed implementation plans that identify exact files, symbols, tests, commands, expected results, and implementation code where beneficial.
4. Treat the reviewed implementation plan as the canonical execution source.
5. Dispatch fresh, scoped subagents for exploration, implementation, fixes, and review.
6. Prevent context pollution by exchanging artifacts through files.
7. Keep strictness around evidence, write boundaries, plan freshness, contracts, and verification.
8. Remove OpenSpec from the core workflow without losing delta-spec, archive, and change-history capabilities.
9. Reuse and evolve Maika's existing gates, knowledge system, write gate, and microloop rather than creating parallel frameworks.
10. Support Claude Code, Codex, Antigravity, and future platforms through adapters and abstract capabilities.

---

## 2. Non-goals

Do not:

- Replace Maika knowledge, Author DNA, conventions, memory, or gate systems with Superpowers.
- Install Superpowers as a second runtime orchestrator inside Maika.
- Copy upstream Superpowers skills unchanged.
- Force every task to use every available MCP.
- Allow implementers to redesign reviewed plans silently.
- Create a second microloop implementation beside the existing `.maika/tools/microloop-orchestrator`.
- Implement the complete migration in one PR.
- Delete legacy OpenSpec support until the vNext path passes dogfood and migration tests.
- Treat line numbers as stable code identities.
- Mark a task complete only because a subprocess exited with code `0`.
- Pass entire parent-session history into subagents.
- **Add speculative gates, states, dispatch mechanisms, routing dimensions, or fixtures that lack an eligible enforcement-ledger entry (§5).**
- **Run parallel implementers before a ledger-recorded need exists. Sequential execution is the only implementation mode through W6.**
- **Expand the dashboard as a committed wave. The existing dashboard and `ACTIVITY_LOG.jsonl` remain unchanged unless dogfood records a concrete deficiency.**
- **Claim cross-platform behavior before the W0 R4 capability matrix verifies the underlying mechanism.**

---

## 3. Architectural decisions

### AD-1 — Superpowers methodology becomes native Maika capability

Port and adapt these methodologies into native Maika skills:

- grounded brainstorming
- specification writing
- detailed implementation planning
- plan validation
- subagent-driven task execution
- task-scoped review
- final whole-change review
- verification before completion

Do not depend on upstream Superpowers at runtime. Upstream remains an inspiration and optional development aid.

### AD-2 — OpenSpec leaves the core workflow

Replace the OpenSpec lifecycle with a Maika-native change workspace.

OpenSpec compatibility remains temporarily available for importing or reading legacy changes. New changes must use the vNext artifact model.

### AD-3 — Exploration precedes brainstorming

Brainstorming may ask user questions early, but it must not propose final architecture until Maika has produced and reconciled:

- business evidence
- codebase evidence
- convention/knowledge evidence
- unresolved contradictions

All three grounding lenses (§10) are mandatory inputs to design approval.

### AD-4 — Strict outcomes, flexible tool use

Skills define:

- purpose
- required outcomes
- invariants
- evidence requirements
- stop conditions
- artifact contracts

Skills do not globally dictate exact MCP function names or rigid call order.

Canonical skills and role contracts refer only to the capability vocabulary (§11). Concrete provider/function mappings belong exclusively in provider mappings, capability profiles, platform adapters, tool documentation, and platform capability evidence.

### AD-5 — Detailed plan is the canonical execution source

A deterministic compiler produces:

- `PLAN_MANIFEST.json`
- `CONTRACT_DAG.json`
- `TASK_QUEUE.json`
- task briefs

No LLM may paraphrase task requirements between the reviewed plan and the executor brief.

### AD-6 — Planning carries broad autonomy; execution carries narrow autonomy

- Explorers and planners: broad read access, high autonomy, no application-code writes.
- Implementers: narrow scoped reads/writes, plan-bound, required verification.
- Reviewers: broad read-only access, independent judgment.
- Orchestrator: state transitions, artifact handoff, retries, gating, and ledger ownership.

### AD-7 — Plan code supports three authority levels

Every implementation task declares:

- `exact`: code and contracts are authoritative.
- `guided`: architecture and critical logic are authoritative; local implementation may adapt.
- `intent`: behavior, files, interfaces, and acceptance criteria are authoritative; implementation details are delegated.

### AD-8 — Freshness is mechanical

Plans record:

- base commit
- spec hash
- evidence hash
- referenced **file-level** hashes
- symbol anchors
- tool/index freshness metadata

A stale plan or stale task cannot silently execute. Claim-level hashing is deferred (§5) unless file-level staleness produces an observed false negative.

### AD-9 — Existing chokepoints are extended

Extend:

- `.maika/tools/microloop-orchestrator` (as a **contract migration** — see §17; not a naive extension)
- `.maika/tools/gate-check`
- `.maika/hooks/write-gate`
- `.maika/profiles`
- `.maika/workflows/task.md`
- existing CLI scaffolding and platform adapters

Do not build duplicate parallel systems.

---

## 4. Migration principles (P1–P5)

These principles govern how the waves execute. They rank equal to the Execution rule.

- **P1 — Dogfood-first.** Every wave ends with a dogfood checkpoint that runs real changes (on the Maika repository itself or a real downstream project). Observed failures from each checkpoint are recorded in the enforcement ledger and shape the scope of the next wave.
- **P2 — Enforcement ledger.** Every gate, hook, and validator must have an entry in `docs/refactor/maika-vnext/enforcement-ledger.yaml` conforming to the schema in §5. A mechanism may be implemented only when its entry satisfies at least one eligibility condition; otherwise its status stays `deferred`. **Exception by design:** write boundaries and destructive-action protections do not wait for a production incident.
- **P3 — R4 pre-flight.** Any wave that designs on top of a platform mechanism (subagent spawn, hook event, model selection) must open with a table proving "mechanism exists at `<file:line>` / `<command>`" for every claimed platform. A missing row blocks that wave at the planning stage.
- **P4 — Single-platform-first.** The vertical slice runs on Claude Code first. Codex and Antigravity follow through adapters only after the contracts have stabilized through dogfood, and only within what the W0 capability matrix proves.
- **P5 — Real fixtures over built fixtures.** Dogfood uses the Maika repository and a real downstream Java project. No banking fixture is built. CI end-to-end uses one minimal Python fixture repository.

---

## 5. Enforcement ledger

File: `docs/refactor/maika-vnext/enforcement-ledger.yaml`. Created in W0. Minimum schema:

```yaml
version: 1

entries:
  - id: ENF-001
    mechanism: code-evidence
    type: gate            # gate | hook | validator
    status: active

    failure:
      classification: observed_failure
      reference: docs/incidents/example.md
      summary: Agent used grep despite a healthy indexed provider.

    litmus:
      command: python3 ...
      expected_without_enforcement: pass
      expected_with_enforcement: fail

    implementation:
      files:
        - .maika/tools/gate-check/gates.py
      consumers:
        - .maika/workflows/task.md

    scope:
      change_classes:
        - standard
        - architectural

    reviewed_at: 2026-07-10
```

Allowed statuses:

```text
proposed | active | deferred | superseded | removed
```

Allowed evidence classifications:

```text
observed_failure | reproducible_litmus | external_requirement | safety_boundary
```

**Implementation eligibility.** An enforcement mechanism may be implemented only when at least one of these is true:

1. An observed failure exists.
2. A reproducible litmus exists.
3. An external requirement mandates it.
4. It protects a safety or destructive-action boundary.

Otherwise its status must remain `deferred`. Every `deferred` entry must state its activation condition (see §26 Wave definitions and §30).

The ledger schema itself is validated by gate-check; that validator's own ledger entry uses classification `reproducible_litmus` (schema fixture tests).

Note relative to `DEVELOPMENT_RULES.md` R3: `external_requirement` and `safety_boundary` are a deliberate extension of R3's literal wording (observed failure / litmus only). W0 must propose the corresponding `DEVELOPMENT_RULES.md` amendment in its own PR (R6 — no silent override), created only **after** the W0 PR merges so the ledger path the amended rule references exists on `main`.

`proposed` entries are scheduling records, not implementation permission: at its scheduled wave, a proposed mechanism still needs an eligible evidence classification added before any code is written. The `litmus` block is optional — omit it rather than shipping empty fields.

---

## 6. Change classification

Every change is classified at INTAKE and the class is recorded in `CHANGE.yaml`. Gates read the class to determine which artifacts are mandatory; the class-to-gate applicability contract is in §22.

| Class | Example | Pipeline |
|---|---|---|
| `trivial` | typo, docs, one-file config, no behavior change | INTENT → mini-plan (1 task, mode `intent`) → implement → verify. No explorer, no SPEC. Write gate and result contract still apply. |
| `small` | bug/feature within one module, ≤ ~3 files | Light grounding (seam + tests) → short SPEC (Goal/Current/Desired/AC) → plan → plan review → execute → task review (doubles as final review when there is a single task) → verify. |
| `standard` | multi-file, multi-module | Full pipeline (§7). |
| `architectural` | public contract, database, cross-service | Full pipeline + all user-approval gates mandatory + Compatibility/Migration sections must be non-empty. |

### Automatic classification

For `trivial` and clearly scoped `small` changes:

1. The orchestrator classifies the change.
2. It briefly displays the classification and reason.
3. It proceeds unless the user objects.

Example display:

```text
Classified as `small`: one module, three files or fewer, no public contract,
database, security, or cross-service impact.
```

Explicit user confirmation is required only when:

- classification is ambiguous;
- the proposed class is `standard` or `architectural`;
- public contract changes are involved;
- persistence or database changes are involved;
- security-sensitive behavior is involved;
- destructive migration is involved;
- reclassification introduces significant additional artifacts or approval gates.

Every classification — including auto-proceeded ones — is recorded in `CHANGE.yaml`.

### Escalation and reclassification

When execution hits a re-plan trigger that exceeds the current class (public signature change, new dependency, new module, changed DB/event/API contract — the §19 list), the orchestrator re-classifies upward and returns to the earliest missing pipeline step. No new mechanism: the existing re-plan triggers are the escalation signal.

---

## 7. Target workflow

Full pipeline (`standard` / `architectural`; `trivial` and `small` compress per §6):

```text
Intent Intake
    |
    v
Change Classification (§6)
    |
    v
Grounding Dispatch
    |
    v
Grounding Explorer — three mandatory lenses
  (codebase + business + conventions; specialized
   agents only after W3 evidence — §10)
    |
    v
Architecture Reconciler
    |
    v
Grounding Readiness Check (inside exploration-evidence gate)
    |
    v
Grounded Brainstorming
    |
    v
Reviewed SPEC.md
    |
    v
Detailed IMPLEMENTATION_PLAN.md
    |
    v
Independent Plan Validation
    |
    v
Deterministic Plan Compiler
    |
    v
CONTRACT_DAG + TASK_QUEUE + Briefs
    |
    v
Fresh Implementer Per Task (sequential)
    |
    v
Task-Scoped Reviewer
    |
   findings? -- yes --> Fix Agent --> Re-review
    |
    v
Final Whole-Change Review
    |
    v
Mechanical Verification + Archive
```

---

## 8. Canonical change workspace

Create a single canonical layout:

```text
.maika/changes/<change-id>/
├── CHANGE.yaml                # includes `class:` (§6)
├── INTENT.md
├── exploration/
│   ├── GROUNDING.yaml         # three mandatory lenses (§10)
│   ├── EVIDENCE_MANIFEST.yaml
│   └── TOOL_HEALTH_SNAPSHOT.yaml
├── RECONCILIATION.md
├── SPEC.md
├── IMPLEMENTATION_PLAN.md
├── generated/
│   ├── PLAN_MANIFEST.json
│   ├── CONTRACT_DAG.json
│   ├── TASK_QUEUE.json
│   └── PLAN_VALIDATION.json
├── briefs/
│   ├── task-001.md
│   └── ...
├── results/
│   ├── task-001.yaml
│   └── ...
├── reviews/
│   ├── task-001.md
│   ├── final-review.md
│   └── findings-ledger.yaml
├── verification/
│   ├── commands.yaml
│   ├── VERIFICATION_REPORT.md
│   └── evidence/
├── LEDGER.yaml
└── STATE.yaml
```

Classes `trivial`/`small` create only the artifacts their pipeline requires (§6); the layout is the superset.

Archive by moving the complete workspace to:

```text
.maika/archive/YYYY-MM-DD-<change-id>/
```

Do not copy selected artifacts into several competing canonical locations.

---

## 9. State model

Fourteen persistent lifecycle states:

```text
INTAKE
EXPLORING
RECONCILING
BRAINSTORMING
SPEC_REVIEW
PLANNING
PLAN_REVIEW
EXECUTING
VERIFYING
FINAL_REVIEW
COMPLETED
ARCHIVED
BLOCKED
CANCELLED
```

Rules:

- Blocker detail is metadata, not state. `BLOCKED` carries a structured reason in `STATE.yaml`:

  ```yaml
  state: BLOCKED
  blocked:
    reason: grounding | stale_plan | capability | user_input | environment
    detail: ...
    since: 2026-07-10T...
  ```

  (v1's `GROUNDING_BLOCKED` and `STALE` collapse into this.)
- Readiness to execute is a gate-validated transition (`PLAN_REVIEW → EXECUTING`), not a state. (v1's `READY` is removed.)
- Per-task progress (including task review status) lives in `TASK_QUEUE.json` as task-level statuses, not in the change-level state machine. (v1's `TASK_REVIEW` state is removed.)
- Classes traverse a subset of states (§6): phases a class skips are collapsed transitions, and their guarding gates return an explicit `NOT_APPLICABLE` verdict (§22) rather than blocking — e.g. a `trivial` change moves INTAKE → PLANNING directly.
- State transitions are owned by the orchestrator and validated by gates.
- A markdown marker may remain for human readability, but it must not be the only source of workflow truth.

---

## 10. Role model

Role contracts refer to capabilities (§11), never to concrete providers.

### 10.1 Grounding Explorer (three mandatory lenses)

**Purpose:** Ground the requested change in the current implementation, the business domain, and project conventions.

One unified explorer produces a single `exploration/GROUNDING.yaml` containing three mandatory sections:

```yaml
codebase:
  entry_points:
  current_flow:
  extension_seams:
  related_tests:
  blast_radius:

business:
  terminology:
  known_rules:
  states_and_transitions:
  unresolved_questions:
  evidence_sources:

conventions:
  applicable_rule_ids:
  existing_patterns:
  testing_patterns:
  error_handling:
  conflicts:
```

**Capabilities:** `architecture_discovery`, `exact_source_inspection`, `dependency_analysis`, `business_knowledge_retrieval`, `convention_retrieval`.

**Must not:**

- propose application architecture
- write implementation code
- invent business rules without evidence

Every exact code claim must be verified against current source.

**Specialization is conditional (W3).** Splitting the lenses into dedicated Business/Convention/Codebase Explorer subagents happens only when dogfood evidence shows: business rules repeatedly missed; convention constraints omitted; context too large; business and code evidence not reconciled; or shallow unified output. Absent that evidence, the unified explorer remains. Specialized agents, when introduced, still write sections of the same `GROUNDING.yaml`.

### 10.2 Architecture Reconciler

**Purpose:** Reconcile user intent, business evidence, code evidence, and conventions.

**Required output:** current behavior; desired behavior; recommended extension seam; alternative seams and rejection reasons; contradictions; questions only the user can resolve; readiness verdict.

It must not proceed to design when a material contradiction remains unresolved.

### 10.3 Grounded Brainstormer

**Purpose:** Convert reconciled evidence and user intent into a reviewed design.

It must ask questions grounded in the current system, for example:

```text
The current validation chain executes before approval creation.
Should the new limit check remain maker-time only, or also be repeated at approval-time
because available limits may change between the two events?
```

It must not ask the user to restate facts already verified from the system. It cannot propose final architecture unless all three grounding lenses are present and the exploration-evidence gate passed.

### 10.4 Spec Writer

**Purpose:** Produce the behavioral and architectural contract. The spec defines what the system must do, not every implementation line.

### 10.5 Implementation Planner

**Purpose:** Produce a code-level blueprint grounded in the reviewed spec and current repository. The planner is the primary coding-reasoning role. **Capabilities:** `exact_source_inspection`, `dependency_analysis`, `architecture_discovery`.

### 10.6 Plan Reviewer

**Purpose:** Independently compare:

```text
SPEC ↔ IMPLEMENTATION_PLAN ↔ CURRENT CODEBASE ↔ CONVENTIONS
```

It must verify both coverage and feasibility.

### 10.7 Implementer

**Purpose:** Apply one task brief exactly within its scope. It may not silently change architecture or public contracts. **Capabilities:** `exact_source_inspection`, `runtime_verification`.

### 10.8 Task Reviewer

**Purpose:** Review one task for: spec/plan compliance; code quality; boundary compliance; test evidence.

### 10.9 Final Reviewer

**Purpose:** Review the whole branch/change with cross-task context and the full diff package.

---

## 11. Capability model

### 11.1 Capability vocabulary (exists from W1)

The abstract vocabulary precedes the runtime (which arrives in W4). Minimum capability IDs:

```text
architecture_discovery
exact_source_inspection
dependency_analysis
business_knowledge_retrieval
convention_retrieval
runtime_verification
```

Rules:

- Canonical skills and role contracts refer only to capability IDs.
- Concrete provider names and function mappings appear only in: provider mappings, capability profiles, platform adapters, tool documentation, and platform capability evidence (the W0 matrix).
- The vocabulary ships in the same PR as the first canonical skill that references it (R1: consumer in the same PR). The mechanical consumer (skill lint) arrives in W4; between W1 and W4, compliance is held by plan review.

### 11.2 Provider registry and profiles (W4 runtime)

Create or normalize `.maika/profiles/tool-capabilities.yaml`:

```yaml
version: 1

capabilities:
  architecture_discovery:
    description: Discover modules, domain boundaries, and execution flows.
    evidence_types:
      - domain_node
      - flow_path
      - dependency_edge
    providers:
      - id: understand_anything        # provider mapping — allowed here only
        availability_probe: ua_health
        operations:
          - domain_overview
          - domain_flow
      - id: codebase_memory
        availability_probe: cbm_health
        operations:
          - graph_search
          - impact_analysis
      - id: source
        operations:
          - search
          - read
```

Provider mappings may contain concrete function names. Canonical reasoning skills must refer only to capability IDs, evidence types, and quality requirements.

### 11.3 Routing rules (W4 runtime)

Routing considers exactly two runtime dimensions:

- provider health
- index freshness (repository commit vs index commit)

Cost, risk, and data-sensitivity routing are **not implemented**; their ledger entry stays `deferred` with activation condition "an observed misrouting failure attributable to a missing dimension".

The router is advisory by default. Exact provider enforcement is allowed only for:

- safety boundaries
- destructive actions
- authoritative current-source verification
- reproducible final verification
- explicit organizational policy

---

## 12. Evidence model

Machine-readable evidence manifest, file-level hashing:

```yaml
version: 1
change_id: approval-limit-check

claims:
  - id: CODE-001
    statement: ValidateCreateApprovalLimitProcessor participates in the create-validation chain.
    classification: exact_code_fact
    sources:
      - type: file_symbol
        file: src/main/java/.../ValidateCreateApprovalLimitProcessor.java
        symbol: ValidateCreateApprovalLimitProcessor
        source_hash: sha256:...      # hash of the file, not the claim
      - type: dependency_edge
        provider: codebase_memory    # provider reference allowed: this is evidence, not a skill
        node_id: project....ValidateCreateApprovalLimitProcessor
        indexed_commit: abc123
    status: verified

  - id: BIZ-004
    statement: Maker limit is evaluated per business date.
    classification: business_rule
    sources:
      - type: document_reference
        uri: ...
        revision: ...
    status: verified
```

Claim statuses:

```text
verified | inferred | conflicting | unverified | stale
```

Rules:

- `exact_code_fact` requires current-source evidence.
- Graph evidence may support relationships but cannot override current source.
- Inferences must be labeled.
- Conflicting claims block grounded design unless explicitly resolved.
- The final spec and plan must reference evidence IDs for non-obvious decisions.
- Hash granularity is per file. Claim-level hashing stays `deferred` in the ledger; activation condition: an observed staleness false negative that file-level hashing missed.

---

## 13. Native skill set

Create or refactor toward these canonical skills:

```text
.maika/skills/
├── grounded-brainstorming/
├── writing-spec/
├── writing-plan/
├── validating-plan/
├── executing-plan-task/
├── reviewing-task/
├── reviewing-change/
├── verification-before-completion/
├── grounding-explorer/            # three lenses; specialization conditional (W3)
└── architecture-reconciler/
```

Each skill body should contain:

```text
Purpose
When to use
Inputs
Required outcomes
Invariants
Evidence requirements
Strategy principles
Stop conditions
Output contract
Next handoff
```

Skills reference capability IDs only. Concrete MCP function tutorials belong in provider references or adapter documentation, never in the canonical skill process.

### Skill strictness

Strict: artifact output; evidence quality; stop conditions; spec coverage; plan completeness; write boundary; required verification; destructive-action protection.

Flexible: provider selection; search sequence; number of retrieval calls; exploration path; local private-helper structure; non-contractual formatting.

---

## 14. Specification contract

`SPEC.md` must contain:

```text
Goal
Context
Current Behavior
Desired Behavior
Actors
Functional Requirements
Business Rules
States and Transitions
Architecture
Components and Boundaries
Data Flow
Contract/API Changes
Persistence Changes
Asynchronous/Event Behavior
Error Handling
Security and Authorization
Observability and Audit
Compatibility
Migration
Testing Strategy
Acceptance Criteria
Non-goals
Open Risks
Evidence References
```

For `small` changes, the short-spec subset is: Goal, Current Behavior, Desired Behavior, Acceptance Criteria, Evidence References.

Retain OpenSpec's valuable delta semantics:

```text
ADDED | MODIFIED | REMOVED
```

Use them inside `SPEC.md`; do not retain OpenSpec solely for this syntax.

---

## 15. Implementation-plan contract

`IMPLEMENTATION_PLAN.md` must begin with machine-readable metadata:

```yaml
---
change_id: approval-limit-check
plan_version: 1
base_commit: abc123
spec_hash: sha256:...
evidence_hash: sha256:...
created_at: 2026-07-10T...
planner_role: implementation-planner
global_constraints:
  - preserve public gRPC contract
  - no new database table
---
```

Each task must include:

```text
Task ID and title
Purpose
Implementation mode: exact | guided | intent
Dependencies
Files to create
Files to modify
Files to read
Exact symbols and anchors
Interfaces consumed
Interfaces produced
Relevant evidence IDs
Preconditions
Step-by-step TDD/implementation instructions
Complete code or critical snippets where appropriate
Commands to run
Expected failing result
Expected passing result
Acceptance criteria covered
Allowed adaptations
Re-plan triggers
Commit boundary
```

Example machine-readable task header:

```yaml
task:
  id: TASK-004
  implementation_mode: exact
  depends_on:
    - TASK-002
  files:
    modify:
      - path: src/main/java/.../Processor.java
        symbols:
          - process
        source_hash: sha256:...
        anchor:
          type: symbol
          value: Processor#process
    test:
      - src/test/java/.../ProcessorTest.java
  interfaces:
    consumes:
      - LimitClient#check
    produces:
      - ValidationResult
  evidence:
    - CODE-001
    - BIZ-004
  requires_replan:
    - public signature change
    - new production dependency
    - additional module
```

### Line numbers

Line numbers are hints only. Identity priority:

```text
symbol anchor > structural/context anchor > content hash > approximate line
```

---

## 16. Plan validation

Plan validation is the internal check set of the **`plan` gate** (§22), plus an independent semantic review. It is not a family of separate lifecycle gates.

### Mechanical checks (inside the `plan` gate)

- metadata exists
- base commit is resolvable
- spec/evidence hashes match (freshness)
- referenced files exist or are marked `create`
- referenced symbols exist (symbol grounding)
- file-level source hashes match or are consciously refreshed
- task IDs are unique
- dependencies are acyclic (DAG validity)
- every task has verification
- every acceptance criterion maps to at least one task (coverage)
- every public contract change has compatibility treatment
- every exact code block has a target anchor
- no placeholder/TODO/TBD remains
- no task writes outside declared files
- implementation modes are valid

### Independent semantic review

- design matches current architecture
- plan covers the complete spec
- proposed code compiles conceptually against actual signatures
- tests validate behavior rather than implementation trivia
- tasks are sufficiently small
- cross-task interfaces are coherent
- rollback/migration is adequate
- no unrelated refactor is introduced
- plan instructions do not contradict review standards

Output: `generated/PLAN_VALIDATION.json`.

Verdicts:

```text
APPROVED | APPROVED_WITH_WARNINGS | REVISE | STALE | BLOCKED
```

Only `APPROVED` may compile into an executable queue by default.

---

## 17. Deterministic plan compiler and microloop contract migration

This work is a **contract migration**, not a simple extension. The existing microloop contract is markdown (`TASK_QUEUE.md`, `TASK_HANDOFF.md`, `TASK_RESULT.md` under `knowledge/active/microloop/`); vNext moves the execution contract to JSON artifacts plus hashed verbatim briefs in the change workspace. During the opt-in period the orchestrator must keep a compatibility reader for legacy artifacts, and snapshot tests must be updated deliberately.

Target modules under `.maika/tools/microloop-orchestrator/` (W1 implements the subset it needs; nothing is created without a consumer in the same PR):

```text
plan_parser.py
plan_validator.py
plan_compiler.py
dag.py
task_brief.py
dispatcher.py
ledger.py
staleness.py
review_package.py
result_contract.py
state_machine.py
```

The compiler must:

1. Parse task metadata and task bodies.
2. Verify the plan validation verdict.
3. Build a dependency DAG.
4. Produce an ordered **sequential** task queue.
5. Extract each task verbatim into a brief.
6. Add only runtime context that cannot be known by the original plan.
7. Hash each brief.
8. Record plan-section hash and spec hash.
9. Never summarize implementation requirements through an LLM.

File-overlap detection and unsafe-parallelism analysis are deferred together with parallel execution (ledger entry; activation condition: a ledger-recorded need for parallel implementers).

---

## 18. Dispatcher architecture

### 18.1 Dispatch classes

```text
exploration_dispatch
planning_dispatch
implementation_dispatch
fix_dispatch
task_review_dispatch
final_review_dispatch
```

W1 implements `planning_dispatch`, `implementation_dispatch`, `task_review_dispatch` (a fix is a re-dispatch of `implementation_dispatch` carrying the findings file until `fix_dispatch` is introduced with the W2 review loop). `exploration_dispatch` arrives in W2; `fix_dispatch` and `final_review_dispatch` with the hardened review loop in W2–W3.

### 18.2 Context isolation

Every dispatched agent is fresh and receives:

- role contract
- one artifact/brief path
- relevant interfaces from prior tasks
- global constraints
- allowed read/write scope
- result-file path
- required result schema

Do not provide accumulated conversation history.

### 18.3 File handoff

Large artifacts and diffs are exchanged as files: task brief file, task result file, review package file, findings ledger file. The parent context retains only paths, hashes, statuses, and short summaries.

### 18.4 Status contract

Agents report:

```text
DONE
DONE_WITH_CONCERNS
NEEDS_CONTEXT
BLOCKED
STALE_PLAN
FAILED_VERIFICATION
```

Required result fields:

```yaml
status:
task_id:
brief_hash:
base_commit:
changed_files:
changed_symbols:
commands:
  - command:
    exit_code:
    expected:
    observed:
tests:
concerns:
deviations:
evidence:
commit_sha:
```

An exit code alone is never sufficient to mark a task complete.

### 18.5 Retry policy

- `NEEDS_CONTEXT`: provide missing context and redispatch.
- `BLOCKED`: classify as context, capability, scope, plan, or environment failure.
- `STALE_PLAN`: stop and return to planning.
- `FAILED_VERIFICATION`: fix within task scope or return to plan review.
- Repeated identical failure: escalate model/capability or split task.
- Never repeat the same dispatch unchanged after an explicit blocker.

### 18.6 Model selection

Model selection is expressed as abstract tiers:

```text
mechanical | standard | reasoning | highest-review
```

Platform adapters map tiers to concrete models. Tier activation on a platform requires the W0 capability matrix to prove that the platform's dispatch mechanism supports model selection; where it does not, the adapter declares a single-tier degradation. Model selection is an optimization, never a hard wave dependency: a `model_selection: supported: false` matrix row limits tier behavior on that platform — it does not block any wave.

Use: mechanical for exact-code transcription and isolated one-file tasks; standard for multi-file integration with a detailed plan; reasoning for debugging or plan deviation; highest-review for architecture, planning, and final branch review.

---

## 19. Execution safety

The implementer must:

1. Verify brief hash and plan freshness.
2. Verify referenced files and symbols.
3. Write only within allowed files.
4. Follow authoritative contracts and exact-mode code.
5. Run required failing and passing commands.
6. Record all deviations.
7. Stop on re-plan triggers.
8. Self-review before returning a result.

Allowed automatic adaptations: formatting; import ordering; private local variable naming; equivalent private helper extraction; framework-required syntax adjustments that do not change behavior.

Require re-plan for: public signature changes; new dependency; extra production file/module; changed database/event/API contract; architecture change; missing referenced symbol; invalid test strategy; insufficient allowed files; conflict with current source.

---

## 20. Review loop

Per task:

```text
Implementer
    |
    v
Result Contract Gate
    |
    v
Generate Review Package
    |
    v
Task Reviewer
    |
    +-- Critical/Important --> Fix Agent --> Re-run tests --> Re-review
    |
    v
Task Complete
```

Task review has two explicit lenses: **spec/plan compliance** and **code quality and risk**.

The final reviewer receives: merge-base to HEAD review package; spec; plan; findings ledger; unresolved minor findings; verification report. The final reviewer must inspect cross-task behavior, integration, compatibility, and migration.

---

## 21. Write-gate evolution

Extend `.maika/hooks/write-gate` to validate:

- current workflow state permits writing
- current role is allowed to write
- task brief exists
- brief hash matches queue
- plan/spec are current
- file is inside allowed scope
- task is not already completed/cancelled
- plan validation verdict is approved

File-ownership checks against parallel tasks are deferred together with parallel execution.

Ledger entry: the write-scope mechanism is classified `safety_boundary` (implementable without waiting for an incident); the state/brief/freshness checks additionally reference the observed write-gate bypass on Antigravity (fixed, logged) as `observed_failure`.

Do not use prompt prose as the only enforcement source. Retain cooperative-governance semantics; document that this is not a hostile security sandbox.

---

## 22. Enforcement architecture — nine lifecycle gates

The change lifecycle has exactly nine primary gates:

| Gate | Guards transition | Internal checks (not separate gates) |
|---|---|---|
| `change-workspace` | INTAKE → EXPLORING | workspace layout, `CHANGE.yaml` schema incl. class, state file validity |
| `exploration-evidence` | EXPLORING/RECONCILING → BRAINSTORMING | three lenses present and non-empty, evidence manifest schema, claim statuses, tool health snapshot, grounding readiness verdict (PASS / PASS_WITH_DEGRADATION / BLOCK), degraded capabilities declared |
| `spec` | SPEC_REVIEW → PLANNING | spec section completeness (per class), evidence coverage of significant decisions, delta semantics validity |
| `plan` | PLAN_REVIEW → EXECUTING | full §16 mechanical set: structure, symbol grounding, spec coverage, freshness (hashes/base commit), DAG validity, verification presence, mode validity, write-scope declarations |
| `brief-integrity` | before each dispatch | brief hash matches queue, verbatim-slice traceability to approved plan section, plan not stale |
| `result-contract` | after each task | required result fields, commands with expected vs observed, verification evidence present, no undeclared file touched |
| `task-review` | task completion | review artifact exists, findings triaged, Critical/Important resolved or escalated |
| `final-review` | FINAL_REVIEW → VERIFYING/COMPLETED | full-diff package reviewed, cross-task findings resolved, unresolved minors acknowledged |
| `archive-readiness` | COMPLETED → ARCHIVED | verification report complete, ledger consistent, workspace movable |

Rules:

- Plan freshness, DAG validity, symbol grounding, coverage, and verification completeness are **checks inside** their primary gate, never separate lifecycle gates.
- Every gate, hook, and validator section must state how its enforcement-ledger entry (§5) is created or referenced; gate-check refuses to register a gate without an eligible ledger entry.
- Existing gates (code-evidence, memory-recall, implementation-context, handoff-slice, code hygiene) are integrated as internal checks of the gates above rather than invoked as unrelated checks; their ledger entries carry their existing observed-failure references.
- A degraded exploration pass (`PASS_WITH_DEGRADATION`) must be visible in the spec and the plan.

### Gate applicability by change class

The nine gates apply proportionally per §6. Gate-check evaluates applicability from `CHANGE.yaml.class`:

| Gate | `trivial` | `small` | `standard` | `architectural` |
|---|---|---|---|---|
| `change-workspace` | required (minimal workspace) | required | required | required |
| `exploration-evidence` | not applicable | light-grounding variant | required | required |
| `spec` | not applicable | short-spec variant (§14) | required | required |
| `plan` | mini-plan variant (1 task) | required | required | required |
| `brief-integrity` | required | required | required | required |
| `result-contract` | required | required | required | required |
| `task-review` | risk-based; may combine with verification | required | required | required |
| `final-review` | aliased to task review | aliased to task review when single-task; otherwise required | required | required |
| `archive-readiness` | required if workspace archived | required | required | required |

Rules:

- "Not applicable" is an **explicit verdict** the gate records (`NOT_APPLICABLE`), never a silent bypass.
- Skipped phases collapse the corresponding state transitions (§9); gates guarding a skipped phase return `NOT_APPLICABLE`, so the lifecycle cannot deadlock waiting for a phase that never occurs.
- `trivial` is never forced through explorer or SPEC; `small` uses the shortened variants.

---

## 23. Workflow and command surface

Refactor `.maika/workflows/task.md` around explicit commands:

```text
/task start
/task explore
/task reconcile
/task brainstorm
/task spec
/task plan
/task validate-plan
/task apply
/task review
/task verify
/task archive
/task status
/task resume
```

The default `/task <request>` may run the complete state machine, pausing only at required user-review gates or genuine blockers. Classification happens at `/task start` per §6: `trivial` and clear `small` changes display their class and proceed; `standard`/`architectural` (and the other §6 conditions) require explicit confirmation.

### User approval gates

Require user approval for:

- reviewed design/spec
- plan contradictions involving user intent
- public contract changes not already approved
- destructive migration
- reviewer finding that conflicts with explicit plan text
- classification confirmations per §6 (only in the listed cases)

Do not require user confirmation between routine implementation tasks.

---

## 24. OpenSpec migration

### Retain conceptually

- delta requirements
- change workspace
- reviewed specification
- archive/history

### Remove from core

- OpenSpec-specific commands
- OpenSpec artifact dependency
- duplicate phase state
- OpenSpec task checklist as execution input
- Apply-time conversion from vague tasks into a strategy

### Timeline

- **W6:** OpenSpec is removed from the **vNext path only**; the legacy path keeps OpenSpec and remains the default engine.
- **W7 default switch:** OpenSpec leaves the default execution path; legacy/OpenSpec stays available only as fallback/import compatibility for the declared compatibility period.
- **Post-W7:** physical deletion of legacy runtime files only after consumer-map verification and the rollback window (§31).

### Compatibility adapter

Temporarily support:

```text
maika migrate-openspec <legacy-change-id>
```

The adapter should:

1. Read proposal/design/spec/tasks.
2. Create a vNext change workspace.
3. Preserve original artifacts under `legacy/`.
4. Convert requirements into `SPEC.md`.
5. Mark implementation plan as missing.
6. Require grounded exploration and new planning before execution.

Do not pretend a legacy `tasks.md` is equivalent to a vNext implementation plan.

---

## 25. Skills migration strategy

Inventory every current skill and classify:

```text
retain | merge | rewrite | deprecate | delete
```

Expected direction:

### Retain and adapt

- codebase-explorer (→ grounding-explorer, three lenses)
- architecture-reviewer
- knowledge-curator
- infra-tdd
- spec-extract
- convention-intelligence-builder
- author-dna-builder

### Merge/rewrite into vNext

- OpenSpec-specific exploration
- requirement analysis
- spec validation
- executor/reviewer procedures
- implementation-context and handoff guidance

### Deprecate/delete

- skills whose only purpose is enforcing a concrete MCP call sequence
- duplicated tool documentation
- OpenSpec-only runtime skills after migration
- rules with no mechanical consumer and no observed failure rationale

The inventory itself must be evidence-backed and must identify all downstream consumers before deletion.

---

## 26. Implementation waves

Eight waves. Every wave produces its own repository-verified implementation plan before coding, preserves a green baseline, and is independently revertible.

---

### W0 — Baseline, inventory, ledger, and platform capability matrix

**Objective:** Create a trustworthy baseline; prevent concurrent work from invalidating the refactor; establish the two artifacts every later wave depends on.

**Value:** Framework-visible — a verified current-state audit, the enforcement ledger, and the R4 platform capability matrix.

**Preconditions:** Active PRs touching gate-check, `workflows/task.md`, rules, knowledge/conventions, or microloop are resolved or explicitly stacked.

**Scope:**

1. Create branch `refactor/maika-vnext` from green `main`.
2. Run and record all test suites.
3. Inventory workflows, skills, rules, procedures, tools, hooks, templates, CLI manifest entries, platform adapters.
4. Map producer → consumer for every workflow artifact.
5. Identify exact OpenSpec dependencies.
6. Identify concrete MCP names embedded outside adapters/tool docs.
7. Initialize `docs/refactor/maika-vnext/enforcement-ledger.yaml` (§5): one entry per existing gate/hook/validator with its known observed-failure reference; one `proposed`/`deferred` entry per mechanism this plan introduces, each with an activation condition.
8. Produce the **platform capability matrix** (`docs/refactor/maika-vnext/platform-capability-matrix.yaml`): for Claude Code, Codex, Antigravity — subagent/fresh-session spawn mechanism, hook events that actually fire, model selection support — each row with `file:line` or command evidence. No cross-platform behavior may be claimed anywhere in vNext before its matrix row exists.
9. Propose the `DEVELOPMENT_RULES.md` R3 amendment for `external_requirement`/`safety_boundary` (own PR, R6). **Merge order:** the amendment PR is created only after the W0 PR merges, because the amended rule references `docs/refactor/maika-vnext/enforcement-ledger.yaml`, which does not exist on `main` until then.

**Deferred:** everything implementational beyond the schema-validation tests below.

**Deliverables:** `current-state-audit.md`, `artifact-consumer-map.yaml`, `skill-migration-map.yaml`, `tool-coupling-report.md`, `enforcement-ledger.yaml`, `platform-capability-matrix.yaml`, plus `cli/tests/test_vnext_w0_artifacts.py` (schema-validation tests — the R1 mechanical consumer of the four YAML artifacts, and the only non-documentation change in W0). W0 changes documentation and schema-validation tests only; it does not change runtime behavior.

**Snapshot vs registry:** `current-state-audit.md`, `artifact-consumer-map.yaml`, and `skill-migration-map.yaml` are **baseline snapshots** pinned to the W0 baseline commit — permanent CI validates their schema and internal consistency only and never compares them against the current tree (disk-coverage comparison is a one-time W0 audit step recorded in the artifact). `enforcement-ledger.yaml` and `platform-capability-matrix.yaml` are **living registries** by design, updated across waves.

**Dogfood checkpoint:** retroactively classify the three most recently merged real changes with §6 rules and check the ledger/matrix explain them; record any misfit.

**Evidence to record:** baseline test results; scaffold snapshots; ledger entries for every known past failure (grep-dishonesty/code-evidence, Antigravity write-gate bypass, skill-migration guidance loss).

**Exit criteria:** baseline commit recorded; conflicting branches resolved; every planned deletion has known consumers; audit approved; ledger and matrix exist and validate.

**Rollback boundary:** revert W0 documentation and its schema-validation tests; no runtime behavior change to undo.

**Input to next wave:** ledger + matrix + consumer map feed W1's implementation plan.

---

### W1 — Claude Code vertical slice

**Objective:** A genuinely end-to-end, opt-in execution path on one platform:

```text
detailed plan
+ mechanical validation
+ independent plan review
+ deterministic sequential queue
+ verbatim brief
+ fresh Claude Code implementer
+ structured result
+ independent task review
+ write-scope enforcement
```

**Value:** User-visible — a real change can run through the vNext pipeline (`workflow_engine: vnext`, opt-in).

**Preconditions:** W0 complete; matrix rows proving, for Claude Code: fresh subagent / isolated task dispatch; file-based artifact handoff; structured result/report collection; the write-gate mechanism W1 extends. **Model selection is optional, never blocking:** if the matrix proves it, W1 uses abstract tiers (§18.6); if `model_selection` is `supported: false`, W1 declares a single-tier degradation and proceeds.

**Scope:**

1. Minimal workspace: `CHANGE.yaml` (with class), `INTENT.md`, `SPEC.md`, `IMPLEMENTATION_PLAN.md`, `generated/TASK_QUEUE.json`, `briefs/`, `results/`, `STATE.yaml` + schemas and fixtures.
2. Capability vocabulary (§11.1) shipped in the same PR as the first canonical skill referencing it.
3. `writing-plan` skill (capability IDs only) + `plan` gate mechanical subset (files/symbols exist, per-task verification, unique IDs, acyclic DAG, freshness metadata) + independent plan review via `planning_dispatch`.
4. Minimal compiler: parse → sequential queue → verbatim briefs + hashes (§17), with legacy-artifact compatibility reader.
5. `implementation_dispatch` + `task_review_dispatch` on Claude Code; result contract (§18.4); `brief-integrity` and `result-contract` gates.
6. Write-gate extension: brief-scope check (§21).
7. Feature flag `workflow_engine: legacy | vnext` (default `legacy`).

**W1 must not depend on:** runtime provider registry; advanced router; specialized exploration agents; parallel execution; file locks; Codex or Antigravity parity. Only the static vocabulary (§11.1) is used.

**Deferred (ledger entries with activation conditions):** parallel queue + overlap detection (activation: recorded wall-clock need across ≥2 dogfood changes); `fix_dispatch` as a distinct class (activation: W2 review loop); exploration dispatch (W2).

**Deliverables:** schemas, compiler subset, dispatcher subset, gates `plan`/`brief-integrity`/`result-contract` wired into gate-check, write-gate extension, flag.

**Dogfood checkpoint (A):** two real `small` changes on the Maika repository run end-to-end under `workflow_engine: vnext`.

**Evidence to record:** tokens by phase; plan revisions; task retries; any brief-hash mismatch; any write-scope denial; failures → ledger.

**Exit criteria:** Dogfood A completes; no task marked complete from exit code alone; briefs are verbatim traceable; legacy workflow untouched and default.

**Rollback boundary:** flag off = legacy behavior; new modules unused.

**Input to next wave:** dogfood-A failure list drives W2 grounding scope.

---

### W2 — Three-lens grounding core

**Objective:** Prevent generic use-case-only designs: mandatory grounding with three lenses, evidence manifest, grounded brainstorming, full spec contract.

**Value:** User-visible — designs and specs cite verified evidence from codebase, business, and conventions.

**Preconditions:** W1 exit; Dogfood A evidence reviewed.

**Scope:**

1. `grounding-explorer` skill (refactor of existing codebase-explorer) producing `GROUNDING.yaml` with the three mandatory lenses (§10.1) via `exploration_dispatch`.
2. Evidence manifest (§12, file-level hashes) + `exploration-evidence` gate (three lenses non-empty, claim statuses, health snapshot, readiness verdict).
3. Port grounded brainstorming; brainstormer blocked without a passing exploration-evidence gate.
4. Full `SPEC.md` contract + `spec` gate (class-aware completeness, evidence coverage).
5. Review loop hardening: `fix_dispatch`, `task-review` gate; degradation handling (indexed providers unavailable → declared degradation).

**Deferred:** specialized explorer subagents (W3 decision); reconciler (W3).

**Deliverables:** grounding-explorer skill, evidence manifest schema + validator, exploration-evidence and spec gates, grounded-brainstorming and writing-spec skills.

**Dogfood checkpoint (B):** one real `standard` change on Maika and one on the real downstream Java project, both fully grounded.

**Evidence to record:** the five specialization signals (§10.1): missed business rules, omitted conventions, context size, reconciliation failures, shallow output; degradation occurrences.

**Exit criteria:** no design reaches approval without all three lenses; exact code claims point at current source; degraded exploration is visible in spec and plan.

**Rollback boundary:** grounding artifacts additive; flag still opt-in.

**Input to next wave:** Dogfood B signals decide W3 specialization.

---

### W3 — Reconciliation and conditional explorer specialization

**Objective:** Reconcile intent, evidence, and conventions before design; decide explorer specialization on evidence.

**Value:** Framework-visible — contradictions surface before design instead of during review.

**Preconditions:** W2 exit; Dogfood B signal record.

**Scope:**

1. `architecture-reconciler` skill + `RECONCILIATION.md` contract; material contradictions block design (BLOCKED, reason `grounding`).
2. Full grounding-readiness verdict integrated into the `exploration-evidence` gate.
3. **Conditional:** split Business/Convention/Codebase explorer subagents **only** if Dogfood B recorded the §10.1 signals; otherwise retain the unified explorer. Specialized agents write sections of the same `GROUNDING.yaml`.

**Deferred:** anything not evidenced by Dogfood B.

**Deliverables:** reconciler skill + contract; specialization decision recorded in the ledger with its evidence.

**Dogfood checkpoint:** one real change with a known business/code contradiction (from the downstream project's real backlog) — the reconciler must catch it before design.

**Evidence to record:** contradiction-catch rate; reconciler cost; explorer-specialization outcome.

**Exit criteria:** contradictions block design mechanically; specialization decision is evidence-backed either way.

**Rollback boundary:** reconciler additive.

**Input to next wave:** stable skill set ready for capability runtime.

---

### W4 — Capability runtime and canonical-skill cleanup

**Objective:** Implement the runtime half of the capability model; make the vocabulary mechanically enforced.

**Value:** Framework-visible — provider outages degrade gracefully; canonical skills are provider-clean, verified by lint.

**Preconditions:** W1–W3 skills exist and already use the vocabulary (no skill-contract rewrite needed in this wave).

**Scope:**

1. Provider registry `.maika/profiles/tool-capabilities.yaml` (§11.2).
2. Health checks and freshness checks (observed failures exist: indexed-provider daemons down; stale index vs repository commit).
3. Provider mappings for the platforms the matrix covers.
4. Skill lint: canonical skills must not contain concrete provider/function names unless allowlisted (mechanical consumer of §11.1 completing the R1 loop).
5. Refactor `rules-tool.md` from exact global sequence to evidence requirements, preferred capabilities, degradation rules, safety exceptions.

**Deferred:** cost/risk/data-sensitivity routing (ledger: activation = observed misrouting failure).

**Deliverables:** registry, probes, lint wired into CI, refactored `rules-tool.md`.

**Dogfood checkpoint:** one real `small` change executed with a deliberately stopped indexed provider — pipeline must complete with declared degradation.

**Evidence to record:** provider-selection outcomes; degradation events; lint violations found in existing skills.

**Exit criteria:** canonical workflow expresses needs without concrete MCP names; lint green; exact-source verification still enforced.

**Rollback boundary:** registry advisory; removing it restores W3 behavior.

**Input to next wave:** stable capability contracts for adapters.

---

### W5 — Codex and Antigravity adapters

**Objective:** Extend dispatch and write-gate parity to the other two platforms, strictly bounded by the W0 matrix.

**Value:** User-visible — vNext runs on Codex and Antigravity.

**Preconditions:** **R4 pre-flight table** (from the W0 matrix, refreshed): dispatch mechanism, hook availability, model selection per platform, each with evidence. Missing row = wave blocked at planning.

**Scope:**

1. Dispatcher adapter per platform (fresh-session tier where subagent spawn is unavailable).
2. Write-gate parity (hook wiring per platform as the matrix proves).
3. Model tiers only where the platform supports model selection; otherwise declared single-tier degradation.

**Deferred:** any platform behavior the matrix cannot evidence.

**Deliverables:** platform adapters, adapter contract tests, updated matrix.

**Dogfood checkpoint:** one real `trivial`-or-`small` change per platform end-to-end.

**Evidence to record:** platform-specific dispatch failures; hook misfires; tier degradations.

**Exit criteria:** identical contract artifacts across platforms; write-gate parity demonstrated; no unverified platform claims.

**Rollback boundary:** per-platform adapters independent; Claude Code path unaffected.

**Input to next wave:** all platforms ready for user-facing cutover.

---

### W6 — Workflow cutover and OpenSpec migration

**Objective:** Expose vNext through the user-facing task workflow; make the vNext path OpenSpec-free and introduce the compatibility importer, while the legacy path (with OpenSpec) remains the default until W7.

**Value:** User-visible — `/task` commands drive the vNext state machine; legacy changes importable.

**Preconditions:** W1–W5 exits; sequential queue remains the only execution mode (unchanged through this wave).

**Scope:**

1. Refactor `task.md` around the state machine and commands (§23), including auto-classification behavior.
2. `/task status`, `/task resume` (crash-safe resume from `STATE.yaml` + queue).
3. Update bootstrap, meta-prompt, plugin manifest, scaffold snapshots.
4. `maika migrate-openspec` importer (§24); migration warnings on OpenSpec commands; legacy-read compatibility preserved during cutover.
5. Remove OpenSpec invocation from the **vNext workflow path** while preserving the legacy OpenSpec path until the W7 default switch. The default engine remains `legacy`; OpenSpec is not yet removed from the repository or from the legacy fallback path.

**Deferred:** default switch (W7); deletion of legacy runtime files (post-W7, consumer-map verified).

**Deliverables:** refactored workflow, commands, importer, updated docs/snapshots.

**Dogfood checkpoint:** full workflow (start → archive) on a real change driven only by public commands; one representative legacy OpenSpec change imported and re-grounded.

**Evidence to record:** resume correctness after interruption; importer fidelity; command-surface gaps.

**Exit criteria:** vNext end-to-end via commands on all platforms; the vNext path invokes no OpenSpec; legacy workflow (including its OpenSpec usage) still functional and still the default; no hidden command required; archived legacy changes readable.

**Rollback boundary:** flag still defaults `legacy`; cutover is opt-in until W7.

**Input to next wave:** complete system for hardening and the switch decision.

---

### W7 — Hardening, dogfood, metrics, and default switch

**Objective:** Prove the architecture on real work; flip the default only on evidence.

**Value:** User-visible — vNext becomes the default with a legacy fallback.

**Preconditions:** W6 exit.

**Scope:**

1. Expanded dogfood on real changes from the Maika repo and the downstream project (covering at minimum, as they genuinely arise: one-file bug, multi-file feature, contract-sensitive change, incident-driven debug).
2. Metrics: tokens by phase/role; tool calls; exploration degradation; plan revisions; stale-plan incidents; task retries; out-of-plan file changes; first-pass compile/test rate; reviewer findings; escaped defects; parent-context growth; time/cost by tier.
3. Ledger review: activate any deferred mechanism whose activation condition was met (e.g., parallelism, dashboard expansion); everything else stays deferred.
4. Default-switch gate: the default engine may switch to `vnext` only after the gate passes. At the switch, OpenSpec leaves the **default execution path**; legacy/OpenSpec remains temporarily available only as fallback and import compatibility for the declared compatibility period; physical deletion of legacy runtime files happens only after consumer-map verification and the rollback window (§31).

**Deferred:** parallel execution remains deferred unless its ledger condition was met during dogfood; dashboard expansion likewise.

**Deliverables:** metrics report, ledger review record, default-switch decision.

**Dogfood checkpoint:** this wave largely *is* dogfood; at least three representative real changes complete.

**Evidence to record:** the full metrics list; every deviation → ledger.

**Exit criteria (default switch):** all mandatory suites pass; ≥3 representative dogfood changes complete; no Critical unresolved findings; plan-to-code drift acceptably low; fresh-session execution reliable; rollback to legacy remains available for one release.

**Rollback boundary:** `workflow_engine: legacy` remains one flag away for at least one release.

**Input to next phase:** post-refactor operations; legacy removal per §31 rollout.

---

## 27. Test strategy

### Unit

- schemas (workspace, ledger, matrix, evidence, result)
- parsers
- hashes
- DAG
- state transitions (14 states, blocked metadata)
- result contracts
- evidence validation
- classification rules
- router selection (health/freshness)
- staleness detection

### Contract

- platform adapters
- provider health probes
- model-tier mapping (matrix-bounded)
- dispatcher input/output
- scaffold manifest

### Integration

- grounding → reconciliation
- spec → plan
- plan → queue
- queue → implementer
- result → reviewer
- reviewer → fix
- final review → archive

### End-to-end

One minimal Python fixture repository in CI. Real-repository dogfood (Maika + downstream Java project) covers the realistic scenarios per P5.

### Fault injection

- provider (MCP) unavailable
- stale provider index
- malformed provider response
- agent returns incomplete result
- agent edits forbidden file
- process crashes (resume)
- branch advances after planning (staleness)
- test command unavailable
- final review finds cross-task defect

---

## 28. CI requirements

CI must run all enforcement suites, not only CLI tests:

```text
cli
gate-check
microloop-orchestrator
write-gate
knowledge-index
rule-projector
skill-lint
plan compiler
dispatcher
enforcement-ledger validation
migration
end-to-end fixture
```

One umbrella command, e.g. `python3 scripts/test_all.py`, which fails if a mandatory suite is missing from the registry.

---

## 29. Documentation changes

Update: top-level README; architecture overview; workflow guide; skill authoring guide; tool capability guide; evidence guide; planning guide; subagent dispatch guide; migration guide; troubleshooting; platform-specific setup; downstream scaffold documentation.

Document clearly:

```text
Skill      = reasoning method and output contract
Capability = semantic need (the §11.1 vocabulary)
Provider   = concrete tool/MCP
Adapter    = capability-to-provider mapping
Evidence   = proof supporting a claim
Spec       = behavioral contract
Plan       = executable implementation blueprint
Brief      = immutable task slice
Gate       = deterministic transition check (nine lifecycle gates)
Ledger     = enforcement eligibility record
Dispatcher = isolated role/task execution
Reviewer   = independent judgment
```

---

## 30. Acceptance criteria for the complete refactor

The refactor is complete only when all are true:

1. New tasks do not require OpenSpec.
2. Grounded exploration with three lenses occurs before final design.
3. Business, codebase, and convention evidence are reconciled.
4. Canonical skills do not hard-code provider call sequences.
5. Concrete provider names are localized to provider mappings, capability profiles, platform adapters, tool documentation, and platform capability evidence.
6. Significant spec and plan decisions reference evidence.
7. Detailed plans contain exact code-level instructions appropriate to task risk.
8. Plan validation catches nonexistent symbols and stale source.
9. Plan compilation is deterministic.
10. Task briefs are verbatim slices of approved plans.
11. Fresh subagents execute individual tasks.
12. Implementers cannot silently redesign contracts.
13. Each task receives independent review.
14. The full change receives final review.
15. Task completion requires structured results and verification evidence.
16. Write gate validates state, role, brief, freshness, and file scope.
17. Parent context is not polluted by complete task histories or diffs.
18. Microloop can resume safely after interruption.
19. CI runs every enforcement suite, including enforcement-ledger validation.
20. Legacy OpenSpec changes can be imported but not treated as implementation-ready.
21. The system passes dogfood on representative real changes (Maika repository + real downstream Java project).
22. Documentation and scaffold snapshots match runtime behavior.
23. Every enforcement mechanism has an eligible enforcement-ledger entry; every deferred mechanism has an activation condition.
24. Change classification keeps `trivial`/`small` pipelines proportional (no full-pipeline overhead, no unnecessary user interaction); gate applicability is evaluated from `CHANGE.yaml.class` with explicit `NOT_APPLICABLE` verdicts, never silent bypasses.

---

## 31. Rollback strategy

Every wave must:

- preserve a green baseline
- be independently revertible
- avoid destructive artifact migration without backup
- keep feature flags until dogfood passes
- write new state beside legacy state during the opt-in period
- not delete OpenSpec artifacts until compatibility import is proven

Recommended rollout:

```text
legacy default
→ vNext opt-in                        (from W1)
→ vNext default with legacy fallback  (W7 gate)
→ legacy read/import only
→ remove legacy runtime
```

---

## 32. First agent instructions

The first implementing agent must not begin W1 immediately.

It must:

1. Read this master plan (v2) and Design Spec Rev 2.
2. Read `DEVELOPMENT_RULES.md`.
3. Inspect the current main branch and active PRs.
4. Run the full baseline.
5. Execute **W0 only**: audit, consumer maps, enforcement ledger, platform capability matrix, R3-amendment proposal.
6. Present contradictions between this master plan and the actual repository.
7. Write a separate Superpowers-style implementation plan for **W1** with exact files, exact symbols, failing tests, implementation code, commands, expected outputs, commit boundaries.
8. Obtain plan review approval.
9. Then execute W1 through fresh task subagents and independent reviews.

Do not extrapolate exact code from this master plan when the repository can be inspected directly.
