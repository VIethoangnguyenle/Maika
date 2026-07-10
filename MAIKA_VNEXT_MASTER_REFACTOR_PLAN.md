# Maika vNext — Master Refactor Implementation Plan

> **Purpose:** Refactor the Maika framework end-to-end into a grounded, evidence-driven, plan-first, subagent-dispatched development system.
>
> **Audience:** A capable coding agent acting as orchestrator, planner, implementer, and reviewer.
>
> **Execution rule:** This document is a **master program plan**, not permission to implement the entire repository in one unreviewable change. Execute it as ordered waves. Before coding each wave, produce a repository-verified Superpowers-style implementation plan containing exact files, symbols, tests, commands, expected failures, and code where appropriate.

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
- pass entire parent-session history into subagents.

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

### AD-4 — Strict outcomes, flexible tool use

Skills define:

- purpose
- required outcomes
- invariants
- evidence requirements
- stop conditions
- artifact contracts

Skills do not globally dictate exact MCP function names or rigid call order.

Concrete provider/function mappings belong in platform adapters and capability profiles.

### AD-5 — Detailed plan is the canonical execution source

The reviewed `IMPLEMENTATION_PLAN.md` is the human-readable source of truth.

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
- referenced file hashes
- symbol anchors
- tool/index freshness metadata

A stale plan or stale task cannot silently execute.

### AD-9 — Existing chokepoints are extended

Extend:

- `.maika/tools/microloop-orchestrator`
- `.maika/tools/gate-check`
- `.maika/hooks/write-gate`
- `.maika/profiles`
- `.maika/workflows/task.md`
- existing CLI scaffolding and platform adapters

Do not build duplicate parallel systems.

---

## 4. Target workflow

```text
Intent Intake
    |
    v
Change Classification
    |
    v
Evidence Dispatch
    |-----------------------|--------------------------|
    v                       v                          v
Business Explorer      Codebase Explorer       Convention Explorer
    |                       |                          |
    +-----------------------+--------------------------+
                            |
                            v
                 Architecture Reconciler
                            |
                            v
                  Grounding Readiness Gate
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
               Fresh Implementer Per Task
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

## 5. Canonical change workspace

Create a single canonical layout:

```text
.maika/changes/<change-id>/
├── CHANGE.yaml
├── INTENT.md
├── exploration/
│   ├── BUSINESS_CONTEXT.md
│   ├── CODEBASE_CONTEXT.md
│   ├── CONVENTION_CONTEXT.md
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

Archive by moving the complete workspace to:

```text
.maika/archive/YYYY-MM-DD-<change-id>/
```

Do not copy selected artifacts into several competing canonical locations.

---

## 6. State model

Use a machine-readable state enum:

```text
INTAKE
EXPLORING
RECONCILING
GROUNDING_BLOCKED
BRAINSTORMING
SPEC_REVIEW
PLANNING
PLAN_REVIEW
READY
EXECUTING
TASK_REVIEW
VERIFYING
FINAL_REVIEW
COMPLETED
ARCHIVED
BLOCKED
STALE
CANCELLED
```

State transitions must be owned by the orchestrator and validated by gates.

A markdown marker may remain for human readability, but it must not be the only source of workflow truth.

---

## 7. Role model

### 7.1 Business Explorer

**Purpose:** Ground the requested change in business rules and domain vocabulary.

**Access:**

- read-only business knowledge
- Agent Memory
- Confluence or document MCPs when configured
- existing specs and contracts
- database metadata in read-only mode

**Required output:**

- actors
- use cases
- business rules
- states and transitions
- temporal rules
- permissions
- exceptions
- source references
- contradictions
- unknowns

**Must not:**

- propose application architecture
- write implementation code
- invent business rules without evidence

### 7.2 Codebase Explorer

**Purpose:** Ground the change in the current implementation.

**Access:**

- Understand Anything
- Codebase Memory
- repository search
- direct source reads
- tests
- git history
- build/config files

**Required output:**

- verified entry points
- current call/data flow
- relevant modules
- exact files and symbols
- extension seams
- dependencies
- blast radius
- similar implementations
- tests
- unresolved code uncertainties

Every exact code claim must be verified against current source.

### 7.3 Convention Explorer

**Purpose:** Identify project-specific implementation constraints.

**Access:**

- Author DNA
- conventions
- knowledge index
- similar source files
- build rules
- projected static-analysis rules

**Required output:**

- naming and layering rules
- contract conventions
- error handling
- transaction boundaries
- testing patterns
- observability/audit requirements
- applicable rule IDs
- conflicts between written conventions and actual code

### 7.4 Architecture Reconciler

**Purpose:** Reconcile user intent, business evidence, code evidence, and conventions.

**Required output:**

- current behavior
- desired behavior
- recommended extension seam
- alternative seams and rejection reasons
- contradictions
- questions that only the user can resolve
- readiness verdict

It must not proceed to design when a material contradiction remains unresolved.

### 7.5 Grounded Brainstormer

**Purpose:** Convert reconciled evidence and user intent into a reviewed design.

It should ask questions grounded in the current system, for example:

```text
The current validation chain executes before approval creation.
Should the new limit check remain maker-time only, or also be repeated at approval-time
because available limits may change between the two events?
```

It must not ask the user to restate facts already verified from the system.

### 7.6 Spec Writer

**Purpose:** Produce the behavioral and architectural contract.

The spec defines what the system must do, not every implementation line.

### 7.7 Implementation Planner

**Purpose:** Produce a code-level blueprint grounded in the reviewed spec and current repository.

The planner is the primary coding-reasoning role.

### 7.8 Plan Reviewer

**Purpose:** Independently compare:

```text
SPEC
↔ IMPLEMENTATION_PLAN
↔ CURRENT CODEBASE
↔ CONVENTIONS
```

It must verify both coverage and feasibility.

### 7.9 Implementer

**Purpose:** Apply one task brief exactly within its scope.

It may not silently change architecture or public contracts.

### 7.10 Task Reviewer

**Purpose:** Review one task for:

1. spec/plan compliance
2. code quality
3. boundary compliance
4. test evidence

### 7.11 Final Reviewer

**Purpose:** Review the whole branch/change with cross-task context and the full diff package.

---

## 8. Capability-based tool model

Create or normalize:

```text
.maika/profiles/tool-capabilities.yaml
```

Suggested schema:

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
      - id: understand_anything
        availability_probe: ua_health
        operations:
          - domain_overview
          - domain_flow
        strengths:
          - architecture
          - business-domain mapping
      - id: codebase_memory
        availability_probe: cbm_health
        operations:
          - graph_search
          - impact_analysis
        strengths:
          - symbol graph
          - dependencies
      - id: source
        operations:
          - search
          - read
        strengths:
          - authoritative current code

  exact_symbol_inspection:
    evidence_types:
      - file_symbol
      - source_range
    providers:
      - id: source
      - id: codebase_memory

  business_knowledge_retrieval:
    evidence_types:
      - document_reference
      - memory_reference
    providers:
      - id: agent_memory
      - id: documentation_connector
```

Provider mappings may contain concrete function names.

Canonical reasoning skills must refer only to capability IDs, evidence types, and quality requirements.

### Routing rules

Routing should consider:

- evidence granularity needed
- provider health
- index freshness
- repository commit/index commit mismatch
- reliability
- expected cost
- task risk
- data sensitivity

The router is advisory by default.

Exact provider enforcement is allowed only for:

- safety boundaries
- destructive actions
- authoritative current-source verification
- reproducible final verification
- explicit organizational policy

---

## 9. Evidence model

Create a machine-readable evidence manifest.

Example:

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
        source_hash: sha256:...
      - type: dependency_edge
        provider: codebase_memory
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
verified
inferred
conflicting
unverified
stale
```

Rules:

- `exact_code_fact` requires current-source evidence.
- Graph evidence may support relationships but cannot override current source.
- Inferences must be labeled.
- Conflicting claims block grounded design unless explicitly resolved.
- The final spec and plan must reference evidence IDs for non-obvious decisions.

---

## 10. Grounding readiness gate

Before design approval, validate:

```yaml
business:
  actors_identified: true
  primary_rules_identified: true
  source_coverage: sufficient

codebase:
  entry_points_verified: true
  current_flow_traced: true
  extension_seam_identified: true
  blast_radius_assessed: true
  tests_located: true

conventions:
  applicable_rules_loaded: true
  existing_patterns_identified: true

reconciliation:
  material_conflicts: 0
  unresolved_blockers: 0

tooling:
  health_snapshot_present: true
  degraded_capabilities_declared: true
```

The gate may return:

```text
PASS
PASS_WITH_DEGRADATION
BLOCK
```

A degraded pass must be visible in the spec and plan.

---

## 11. Native skill set

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
├── codebase-explorer/
├── business-explorer/
├── convention-explorer/
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

Concrete MCP function tutorials belong in provider references or adapter documentation, not in the canonical skill process.

### Skill strictness

Strict:

- artifact output
- evidence quality
- stop conditions
- spec coverage
- plan completeness
- write boundary
- required verification
- destructive-action protection

Flexible:

- provider selection
- search sequence
- number of retrieval calls
- exploration path
- local private-helper structure
- non-contractual formatting

---

## 12. Specification contract

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

Retain OpenSpec's valuable delta semantics:

```text
ADDED
MODIFIED
REMOVED
```

Use them inside `SPEC.md`; do not retain OpenSpec solely for this syntax.

---

## 13. Implementation-plan contract

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

Line numbers are hints only.

Identity priority:

```text
symbol anchor
> structural/context anchor
> content hash
> approximate line
```

---

## 14. Plan validation

Add a deterministic and semantic validation stage.

### Mechanical validation

Validate:

- metadata exists
- base commit is resolvable
- spec/evidence hashes match
- referenced files exist or are marked `create`
- referenced symbols exist
- source hashes match or are consciously refreshed
- task IDs are unique
- dependencies are acyclic
- every task has verification
- every acceptance criterion maps to at least one task
- every public contract change has compatibility treatment
- every exact code block has a target anchor
- no placeholder/TODO/TBD remains
- no task writes outside declared files
- implementation modes are valid

### Independent semantic review

Review:

- design matches current architecture
- plan covers the complete spec
- proposed code compiles conceptually against actual signatures
- tests validate behavior rather than implementation trivia
- tasks are sufficiently small
- cross-task interfaces are coherent
- rollback/migration is adequate
- no unrelated refactor is introduced
- plan instructions do not contradict review standards

Output:

```text
generated/PLAN_VALIDATION.json
```

Verdicts:

```text
APPROVED
APPROVED_WITH_WARNINGS
REVISE
STALE
BLOCKED
```

Only `APPROVED` may compile into an executable queue by default.

---

## 15. Deterministic plan compiler

Extend the existing microloop orchestration tool rather than adding a new parallel orchestrator.

Suggested modules under:

```text
.maika/tools/microloop-orchestrator/
├── plan_parser.py
├── plan_validator.py
├── plan_compiler.py
├── dag.py
├── task_brief.py
├── dispatcher.py
├── ledger.py
├── staleness.py
├── review_package.py
├── result_contract.py
└── state_machine.py
```

The compiler must:

1. Parse task metadata and task bodies.
2. Verify the plan validation verdict.
3. Build a dependency DAG.
4. Detect file overlap and unsafe parallelism.
5. Produce an ordered task queue.
6. Extract each task verbatim into a brief.
7. Add only runtime context that cannot be known by the original plan.
8. Hash each brief.
9. Record plan-section hash and spec hash.
10. Never summarize implementation requirements through an LLM.

---

## 16. Dispatcher architecture

### 16.1 Dispatch classes

Support:

```text
exploration_dispatch
planning_dispatch
implementation_dispatch
fix_dispatch
task_review_dispatch
final_review_dispatch
```

### 16.2 Context isolation

Every dispatched agent must be fresh and receive:

- role contract
- one artifact/brief path
- relevant interfaces from prior tasks
- global constraints
- allowed read/write scope
- result-file path
- required result schema

Do not provide accumulated conversation history.

### 16.3 File handoff

Large artifacts and diffs must be exchanged as files:

- task brief file
- task result file
- review package file
- findings ledger file

The parent context should retain only paths, hashes, statuses, and short summaries.

### 16.4 Status contract

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

### 16.5 Retry policy

- `NEEDS_CONTEXT`: provide missing context and redispatch.
- `BLOCKED`: classify as context, capability, scope, plan, or environment failure.
- `STALE_PLAN`: stop and return to planning.
- `FAILED_VERIFICATION`: fix within task scope or return to plan review.
- repeated identical failure: escalate model/capability or split task.
- never repeat the same dispatch unchanged after an explicit blocker.

### 16.6 Model selection

Express model selection as abstract tiers:

```text
mechanical
standard
reasoning
highest-review
```

Platform adapters map tiers to concrete models.

Use:

- mechanical: exact-code transcription, isolated one-file tasks
- standard: multi-file integration with a detailed plan
- reasoning: debugging or plan deviation
- highest-review: architecture, planning, final branch review

---

## 17. Execution safety

The implementer must:

1. Verify brief hash and plan freshness.
2. Verify referenced files and symbols.
3. Write only within allowed files.
4. Follow authoritative contracts and exact-mode code.
5. Run required failing and passing commands.
6. Record all deviations.
7. Stop on re-plan triggers.
8. Self-review before returning a result.

Allowed automatic adaptations:

- formatting
- import ordering
- private local variable naming
- equivalent private helper extraction
- framework-required syntax adjustments that do not change behavior

Require re-plan for:

- public signature changes
- new dependency
- extra production file/module
- changed database/event/API contract
- architecture change
- missing referenced symbol
- invalid test strategy
- insufficient allowed files
- conflict with current source

---

## 18. Review loop

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

Task review has two explicit lenses:

1. **Spec/plan compliance**
2. **Code quality and risk**

The final reviewer receives:

- merge-base to HEAD review package
- spec
- plan
- findings ledger
- unresolved minor findings
- verification report

The final reviewer must inspect cross-task behavior, integration, compatibility, and migration.

---

## 19. Write-gate evolution

Extend `.maika/hooks/write-gate` to validate:

- current workflow state permits writing
- current role is allowed to write
- task brief exists
- brief hash matches queue
- plan/spec are current
- file is inside allowed scope
- file ownership is not held by another parallel task
- task is not already completed/cancelled
- plan validation verdict is approved

Do not use prompt prose as the only enforcement source.

Retain cooperative-governance semantics; document that this is not a hostile security sandbox.

---

## 20. Gate-check evolution

Add or refactor gates:

```text
change-workspace
exploration-artifacts
grounding-readiness
evidence-manifest
spec-completeness
spec-evidence-coverage
plan-structure
plan-code-grounding
plan-spec-coverage
plan-freshness
dag-validity
task-brief-integrity
task-result-contract
task-verification
task-review
final-review
archive-readiness
```

Existing useful gates such as code evidence, memory recall, implementation context, handoff slice, and code hygiene should be integrated into this lifecycle rather than invoked as unrelated checks.

---

## 21. Workflow and command surface

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

The default `/task <request>` may run the complete state machine, pausing only at required user-review gates or genuine blockers.

### User approval gates

Require user approval for:

- reviewed design/spec
- plan contradictions involving user intent
- public contract changes not already approved
- destructive migration
- reviewer finding that conflicts with explicit plan text

Do not require user confirmation between routine implementation tasks.

---

## 22. OpenSpec migration

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

## 23. Skills migration strategy

Inventory every current skill and classify:

```text
retain
merge
rewrite
deprecate
delete
```

Expected direction:

### Retain and adapt

- codebase-explorer
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

## 24. Implementation waves

# Wave 0 — Baseline, freeze, and inventory

## Objective

Create a trustworthy baseline and prevent concurrent work from invalidating the refactor.

## Tasks

1. Resolve or explicitly stack active PRs touching:
   - gate-check
   - workflow/task.md
   - rules-tool.md
   - knowledge/conventions
   - microloop
2. Create branch:
   ```bash
   git checkout main
   git pull
   git checkout -b refactor/maika-vnext
   ```
3. Run and record all test suites.
4. Capture repository tree and artifact consumers.
5. Inventory:
   - workflows
   - skills
   - rules
   - procedures
   - tools
   - hooks
   - templates
   - CLI manifest entries
   - platform adapters
6. Map producer → consumer for every workflow artifact.
7. Identify exact OpenSpec dependencies.
8. Identify concrete MCP names embedded outside adapters/tool docs.
9. Produce:
   ```text
   docs/refactor/maika-vnext/current-state-audit.md
   docs/refactor/maika-vnext/artifact-consumer-map.yaml
   docs/refactor/maika-vnext/skill-migration-map.yaml
   docs/refactor/maika-vnext/tool-coupling-report.md
   ```

## Tests

- all current test suites pass
- scaffold snapshots recorded
- no code behavior changed

## Exit criteria

- baseline commit recorded
- active conflicting branches resolved
- every planned deletion has known consumers
- current-state audit approved

---

# Wave 1 — Change workspace and schemas

## Objective

Introduce the vNext artifact model without changing the default workflow.

## Create

```text
.maika/knowledge/templates/vnext/
├── CHANGE.tpl.yaml
├── INTENT.tpl.md
├── BUSINESS_CONTEXT.tpl.md
├── CODEBASE_CONTEXT.tpl.md
├── CONVENTION_CONTEXT.tpl.md
├── EVIDENCE_MANIFEST.tpl.yaml
├── RECONCILIATION.tpl.md
├── SPEC.tpl.md
├── IMPLEMENTATION_PLAN.tpl.md
├── TASK_RESULT.tpl.yaml
├── PLAN_VALIDATION.tpl.json
└── VERIFICATION_REPORT.tpl.md
```

Add schema modules to the existing orchestrator/tooling location.

## Modify

- scaffold manifest
- template registry
- snapshot tests
- archive gate
- task state representation

## Tests

- valid/invalid fixture tests for every schema
- create/resume/archive workspace tests
- cross-platform scaffold snapshots
- backward compatibility with existing projects

## Exit criteria

- `maika change init <id>` can create a complete empty workspace
- legacy workflow remains default
- no OpenSpec removal yet

---

# Wave 2 — Capability registry and routing policy

## Objective

Move concrete MCP choreography out of canonical skills/rules.

## Tasks

1. Define capability schema.
2. Map current providers and platform functions.
3. Add health/freshness snapshot.
4. Implement advisory capability selection.
5. Update tool documentation.
6. Add lint that flags concrete provider/function names in canonical skills unless allowlisted.
7. Refactor `rules-tool.md` from exact global sequence to:
   - evidence requirements
   - preferred capabilities
   - degradation rules
   - safety exceptions

## Tests

- provider selection fixtures
- unhealthy provider fallback
- stale-index behavior
- platform adapter contract tests
- skill lint positive/negative fixtures

## Exit criteria

- canonical workflow can express needs without concrete MCP names
- provider mappings remain platform-specific
- exact-source verification remains enforced

---

# Wave 3 — Specialized exploration dispatch

## Objective

Implement parallel, artifact-producing exploration.

## Tasks

1. Create native skills:
   - business-explorer
   - codebase-explorer vNext
   - convention-explorer
2. Add exploration dispatch profile.
3. Add role permissions.
4. Dispatch explorers in parallel when independent.
5. Write outputs to the change workspace.
6. Produce tool health and evidence manifests.
7. Integrate current code-evidence and memory-recall gates.
8. Add degradation handling.

## Tests

- full-capability exploration
- UA unavailable
- CBM unavailable
- business knowledge unavailable
- conflicting business/code evidence
- fabricated evidence
- stale graph vs current source
- parallel explorer isolation

## Exit criteria

- no explorer writes application code
- all exact code claims point to current source
- exploration can complete with declared degradation
- evidence manifests are mechanically validated

---

# Wave 4 — Reconciliation and grounded brainstorming

## Objective

Prevent generic use-case-only designs.

## Tasks

1. Create architecture-reconciler skill.
2. Create `RECONCILIATION.md` contract.
3. Implement grounding-readiness gate.
4. Port/adapt Superpowers brainstorming methodology.
5. Require grounded questions.
6. Write reviewed `SPEC.md`.
7. Keep user approval gate.
8. Add spec self-review and independent spec validation.

## Tests

- current architecture supports requested change
- desired behavior conflicts with current behavior
- business docs conflict with code
- missing extension seam
- user chooses an architecture-breaking option
- simple task produces a short spec without bypassing grounding

## Exit criteria

- no design can reach approval without grounding verdict
- spec references evidence for significant decisions
- user-facing questions reflect current system facts

---

# Wave 5 — Detailed planning and plan validation

## Objective

Port the strongest part of Superpowers: code-level implementation planning.

## Tasks

1. Create writing-plan skill.
2. Support exact/guided/intent modes.
3. Require exact files, symbols, tests, commands, and expected outputs.
4. Add code blocks where useful.
5. Add plan self-review.
6. Add independent plan reviewer.
7. Implement mechanical plan gates.
8. Implement spec-to-plan coverage mapping.
9. Implement plan freshness metadata.
10. Produce approved plan verdict.

## Tests

- nonexistent symbol
- stale source hash
- missing acceptance-criterion coverage
- cyclic task dependencies
- test without assertion
- code block incompatible with current signature
- plan uses line number without stable anchor
- exact-mode change requests an undeclared file
- cross-task interface mismatch

## Exit criteria

- approved plans are grounded and executable
- vague task lists fail validation
- legacy OpenSpec tasks cannot bypass planning

---

# Wave 6 — Plan compiler and task briefs

## Objective

Convert reviewed plans into deterministic execution artifacts.

## Tasks

1. Implement parser.
2. Build DAG.
3. Detect file overlap.
4. Generate queue.
5. Extract task sections verbatim.
6. Generate brief hashes.
7. Add interface carry-forward from completed dependencies.
8. Add task ownership and file locks.
9. Add staleness checks.

## Tests

- deterministic output
- identical plan produces identical queue/brief hashes
- plan edit invalidates derived artifacts
- spec edit invalidates plan
- source change affects only relevant tasks where possible
- overlapping files prevent unsafe parallelism
- independent tasks may batch safely

## Exit criteria

- no LLM paraphrase is required to produce a task brief
- every brief is traceable to an approved plan section
- queue and DAG are reproducible

---

# Wave 7 — Fresh subagent dispatcher

## Objective

Adopt Superpowers-style context isolation and review dispatch.

## Tasks

1. Add dispatcher interfaces.
2. Add platform adapter implementation.
3. Add role-based model tiers.
4. Add file handoff.
5. Add result contract.
6. Add status handling.
7. Add retry/escalation policy.
8. Add progress ledger.
9. Add review-package generation.
10. Add final review dispatch.

## Tests

- fresh context per task
- no accumulated-history injection
- needs-context redispatch
- blocker classification
- stale-plan stop
- failed verification stop
- implementer result missing tests rejected
- reviewer independence
- fix/re-review loop
- final review receives complete merge-base diff

## Exit criteria

- tasks are not marked complete from exit code alone
- task result and review are required
- parent context stores paths and statuses, not full artifacts

---

# Wave 8 — Microloop and write-gate integration

## Objective

Make the dispatcher the real execution runtime.

## Tasks

1. Integrate plan queue with existing microloop.
2. Update write gate for role/state/brief/file ownership.
3. Remove Apply-time strategy generation.
4. Add task-level verification gate.
5. Add task-level review gate.
6. Add whole-change verification.
7. Add crash-safe resume.

## Tests

- restart during task
- restart after implementation before review
- write outside allowed files
- two tasks claim same file
- brief hash mismatch
- task from stale queue
- executor tries to redesign contract
- verification command lies about output
- reviewer flags plan-mandated defect

## Exit criteria

- microloop consumes reviewed plan tasks
- executor cannot write without valid task ownership
- resume does not duplicate completed work

---

# Wave 9 — Workflow and CLI cutover

## Objective

Expose vNext through the user-facing task workflow.

## Tasks

1. Refactor `task.md`.
2. Add state-aware commands.
3. Add status and resume.
4. Update bootstrap and meta-prompt.
5. Update plugin manifest and snapshots.
6. Add feature flag:
   ```yaml
   workflow_engine: legacy | vnext
   ```
7. Make vNext opt-in first.
8. Add migration warnings for OpenSpec commands.

## Tests

- init on all supported platforms
- full simple-task workflow
- full standard-task workflow
- resume workflow
- user spec revision
- user rejects reviewer/plan conflict
- legacy workflow still works during transition

## Exit criteria

- vNext can execute end-to-end in a downstream fixture
- CLI and docs are consistent
- no hidden command is required

---

# Wave 10 — OpenSpec compatibility and removal

## Objective

Remove OpenSpec from the core after vNext is proven.

## Tasks

1. Implement legacy change importer.
2. Migrate relevant templates and archived examples.
3. Remove OpenSpec invocation from default workflow.
4. Remove OpenSpec-specific skill dependencies.
5. Remove duplicate task/state concepts.
6. Update docs.
7. Keep importer for at least one compatibility release.
8. Delete dead files only after consumer-map verification.

## Tests

- migrate representative legacy change
- preserve original legacy artifacts
- require new grounded plan
- no OpenSpec runtime command invoked by vNext
- scaffold does not ship dead OpenSpec runtime files

## Exit criteria

- OpenSpec is not a core dependency
- existing archived changes remain readable
- new changes cannot accidentally use legacy Apply

---

# Wave 11 — Observability and dashboard

## Objective

Make agent activity understandable and controllable.

## Display

- current change/state
- active dispatches
- role/model tier
- task ownership
- tool health
- evidence degradation
- queue/DAG
- blockers
- review findings
- verification status
- token/context estimates where available

## Rules

- dashboard reads state/ledger artifacts
- dashboard does not become a second state owner
- runtime remains functional without dashboard

## Tests

- ledger replay
- interrupted task display
- stale plan display
- concurrent explorer display
- review loop display

---

# Wave 12 — Dogfood, metrics, and default switch

## Objective

Prove the architecture on real work.

## Dogfood scenarios

1. Small one-file bug.
2. Multi-file feature inside one module.
3. Java Spring Boot feature involving validation chain.
4. Database migration.
5. Kafka or asynchronous workflow.
6. gRPC contract-sensitive change.
7. Cross-repository/upstream dependency.
8. Incident-driven debugging task.

## Metrics

Record:

- tokens by phase/role
- number of tool calls
- exploration degradation
- plan revisions
- stale-plan incidents
- task retries
- files changed outside initial plan
- first-pass compile/test rate
- reviewer findings
- escaped defects
- total parent-context growth
- time and cost by model tier

## Default-switch gate

Make vNext default only when:

- all mandatory suites pass
- at least three representative dogfood changes complete
- no Critical unresolved findings
- plan-to-code drift is acceptably low
- fresh-session execution is reliable
- rollback to legacy remains available for one release

---

## 25. Test strategy

### Unit

- schemas
- parsers
- hashes
- DAG
- state transitions
- result contracts
- evidence validation
- router selection
- staleness detection
- file ownership

### Contract

- platform adapters
- provider health probes
- model-tier mapping
- dispatcher input/output
- scaffold manifest

### Integration

- explorer → reconciliation
- spec → plan
- plan → queue
- queue → implementer
- result → reviewer
- reviewer → fix
- final review → archive

### End-to-end

Use fixture repositories representing:

- Python framework repository
- Java Spring Boot service
- multi-module banking application

### Fault injection

- MCP unavailable
- stale MCP index
- malformed provider response
- agent returns incomplete result
- agent edits forbidden file
- process crashes
- conflicting parallel writes
- branch advances after planning
- test command unavailable
- final review finds cross-task defect

---

## 26. CI requirements

CI must run all enforcement suites, not only CLI tests.

Required groups:

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
migration
end-to-end fixtures
```

Add one umbrella command such as:

```bash
python3 scripts/test_all.py
```

It must fail if a mandatory suite is missing from the registry.

---

## 27. Documentation changes

Update:

- top-level README
- architecture overview
- workflow guide
- skill authoring guide
- tool capability guide
- evidence guide
- planning guide
- subagent dispatch guide
- migration guide
- troubleshooting
- platform-specific setup
- downstream scaffold documentation

Document clearly:

```text
Skill = reasoning method and output contract
Capability = semantic need
Provider = concrete tool/MCP
Adapter = capability-to-provider mapping
Evidence = proof supporting a claim
Spec = behavioral contract
Plan = executable implementation blueprint
Brief = immutable task slice
Gate = deterministic transition check
Dispatcher = isolated role/task execution
Reviewer = independent judgment
```

---

## 28. Acceptance criteria for the complete refactor

The refactor is complete only when all are true:

1. New tasks do not require OpenSpec.
2. Grounded exploration occurs before final design.
3. Business, codebase, and convention evidence are reconciled.
4. Canonical skills do not hard-code provider call sequences.
5. Concrete provider names are localized to adapters, profiles, or tool documentation.
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
19. CI runs every enforcement suite.
20. Legacy OpenSpec changes can be imported but not treated as implementation-ready.
21. The system passes dogfood on representative Java/banking scenarios.
22. Documentation and scaffold snapshots match runtime behavior.

---

## 29. Rollback strategy

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
→ vNext opt-in
→ vNext default with legacy fallback
→ legacy read/import only
→ remove legacy runtime
```

---

## 30. First agent instructions

The first implementing agent must not begin Wave 1 immediately.

It must:

1. Read this master plan.
2. Read `DEVELOPMENT_RULES.md`.
3. Inspect the current main branch and active PRs.
4. Run the full baseline.
5. Execute Wave 0 only.
6. Produce the current-state audit and migration maps.
7. Present contradictions between this master plan and the actual repository.
8. Write a separate Superpowers-style implementation plan for Wave 1 with:
   - exact files
   - exact symbols
   - failing tests
   - implementation code
   - commands
   - expected outputs
   - commit boundaries
9. Obtain plan review approval.
10. Then execute Wave 1 through fresh task subagents and independent reviews.

Do not extrapolate exact code from this master plan when the repository can be inspected directly.

---

## 31. Final design principle

```text
Superpowers provides the discipline of deep planning and isolated task execution.

Maika provides the missing enterprise intelligence:
business knowledge, code graphs, conventions, memory, evidence gates,
write boundaries, deterministic orchestration, and long-term evolution.

The target is not “Superpowers inside Maika.”

The target is:
Maika as a grounded agentic engineering runtime whose planning and dispatch quality
matches or exceeds Superpowers while remaining native, portable, and mechanically governed.
```
