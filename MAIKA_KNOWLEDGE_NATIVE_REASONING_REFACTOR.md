# Maika Knowledge-Native Reasoning Refactor Plan

> **Goal:** Transform Maika from an artifact-driven plan/execute framework into a
> knowledge-grounded engineering runtime where decisions are driven by explicit
> questions, provider-backed evidence, current-source verification, conflict
> reconciliation, and durable knowledge evolution.
>
> **Scope:** Skills, workflow, rules, capability registry, provider doctrine,
> evidence artifacts, gates, orchestration, task briefs, review, verification,
> knowledge lifecycle, tests, and downstream dogfood.
>
> **Core providers:** Understand-Anything, Codebase Memory MCP, Agent Memory MCP,
> current source, durable project knowledge, and read-only database exploration.

---

## 1. Why this refactor is necessary

Maika already has a strong execution skeleton:

```text
spec
→ plan
→ task queue
→ isolated implementer
→ task review
→ final review
→ verification
```

But the reasoning layer is still too shallow. Most skills explain **what** a role
does without defining:

- what knowledge questions must be answered;
- which evidence types are mandatory;
- which capability/provider must be used;
- how health and freshness affect behavior;
- how conflicts are reconciled;
- how evidence is carried into spec, plan, execution, review, and verification;
- how knowledge is invalidated, promoted, or superseded.

Without this refactor, Maika risks becoming:

```text
Superpowers-style workflow
+ deterministic artifacts
+ capability names
```

instead of:

```text
persistent project intelligence
+ code/domain graph
+ historical memory
+ database evidence
+ source authority
+ evidence-driven decisions
+ knowledge evolution
```

---

## 2. Target identity

Maika must become:

> **A knowledge-grounded engineering runtime that continuously retrieves,
> validates, applies, and evolves project intelligence throughout the
> software-change lifecycle.**

Canonical lifecycle:

```text
REQUEST
   ↓
INTENT + KNOWLEDGE QUESTIONS
   ↓
RETRIEVAL PLAN
   ↓
PROVIDER HEALTH / FRESHNESS
   ↓
UA + CBM + SOURCE + MEMORY + DB + DOCUMENTS
   ↓
EVIDENCE GRAPH
   ↓
CONFLICT RECONCILIATION
   ↓
DESIGN DECISION
   ↓
SPEC WITH EVIDENCE COVERAGE
   ↓
TARGETED RE-GROUNDING
   ↓
IMPLEMENTATION GRAPH
   ↓
TASK KNOWLEDGE CAPSULES
   ↓
ISOLATED IMPLEMENTATION
   ↓
INDEPENDENT COUNTER-EVIDENCE REVIEW
   ↓
REAL VERIFICATION
   ↓
KNOWLEDGE INVALIDATION / PROMOTION / SAVE
```

---

## 3. Non-negotiable principles

### P1 — Knowledge questions before retrieval

Every non-trivial reasoning phase begins by defining what it must know.

Examples:

```text
Where is the current flow assembled?
Which business rule controls this behavior?
Who owns the contract?
Has a similar change failed before?
Which convention applies?
Which database object participates?
What is the blast radius?
```

### P2 — Evidence before design

Architecture, specification, and implementation planning cannot be finalized
from a vague request, graph summary, stale memory, file-name guess, or model
intuition.

### P3 — Current source remains authoritative

Understand-Anything, Codebase Memory, Agent Memory, and DB tools support
reasoning but do not override current source, live database state, or current
explicit business contracts.

### P4 — Healthy preferred providers cannot be silently skipped

When a preferred provider is configured, healthy, fresh, and applicable, the
agent must use it or record an explicit justification.

### P5 — Degradation is explicit

A valid degradation record contains:

- provider;
- actual probe;
- observed error;
- freshness state;
- fallback;
- missing evidence;
- confidence impact;
- affected claims.

### P6 — Knowledge exists before, during, and after implementation

Before: recall decisions, incidents, conventions, and domain knowledge.

During: record discoveries, invalidate stale claims, capture conflicts, and
request re-grounding.

After: promote verified knowledge, supersede stale entries, save episodic
memory, regenerate indexes, and refresh graphs.

### P7 — Skills use capabilities, not provider call names

Canonical capabilities:

```text
architecture_discovery
exact_source_inspection
dependency_analysis
historical_context_retrieval
business_knowledge_retrieval
convention_retrieval
database_schema_inspection
database_dependency_analysis
runtime_verification
version_control
task_dispatch
review_dispatch
```

### P8 — Every implementation task receives a knowledge capsule

A brief includes the smallest relevant slice of:

- code evidence;
- business rules;
- conventions;
- Author DNA;
- historical context;
- database evidence;
- forbidden patterns;
- assumptions;
- confidence and freshness.

### P9 — Reviewers seek counter-evidence

Reviewers independently inspect critical source and evidence instead of blindly
trusting the planner.

### P10 — Gates validate authenticity, not only shape

Where possible, gates verify that files, symbols, hashes, commits, DB objects,
provider probes, memory queries, and conflict resolutions are real.

---

## 4. Provider doctrine

### 4.1 Understand-Anything

Preferred for:

- architecture boundaries;
- domain overview;
- business flows;
- module relationships;
- top-down understanding;
- document discovery.

Required evidence types:

```text
architecture_node
domain_node
domain_flow
relationship_edge
document_node
```

Rules:

- mandatory for standard/architectural architecture discovery when healthy;
- exact node detail must be fetched before a graph summary becomes a plan fact;
- exact code facts must still be confirmed by source;
- indexed commit and freshness must be recorded.

### 4.2 Codebase Memory MCP

Preferred for:

- symbols;
- dependency paths;
- caller/callee analysis;
- blast radius;
- repository-scale code flow.

Required evidence types:

```text
symbol_node
dependency_path
call_path
blast_radius
code_graph_edge
```

Rules:

- mandatory for dependency/blast-radius work when healthy;
- exact facts must be confirmed in source;
- indexed commit must be recorded;
- stale graph evidence must degrade or block high-risk decisions.

### 4.3 Agent Memory MCP

Preferred for:

- previous incidents;
- prior design decisions;
- rejected approaches;
- recurring review findings;
- lessons from similar changes.

Required evidence types:

```text
memory_reference
incident_reference
decision_reference
rejected_approach
review_pattern
```

Rules:

- standard and architectural changes must perform historical recall;
- zero results is valid evidence;
- silent skip while healthy is invalid;
- memory must be classified as valid, superseded, conflicting, or advisory.

### 4.4 Database Explorer / DB MCP

Preferred for:

- tables, columns, constraints, indexes;
- packages, procedures, functions, triggers;
- current schema state;
- DB dependencies and query plans.

Required evidence types:

```text
database_object
database_column
database_constraint
database_index
database_package
database_procedure
database_dependency
database_query_result
```

Rules:

- exploration is read-only;
- persistence-sensitive changes require DB evidence;
- differences between source and live DB state must be reconciled.

### 4.5 Current source

Authoritative for:

```text
file_symbol
source_range
test_symbol
configuration_entry
exact_code_fact
```

### 4.6 Durable project knowledge

Used for:

- Author DNA;
- conventions;
- architecture decisions;
- approved business rules;
- known constraints.

Every entry needs provenance, freshness, status, scope, and consumers.

---

## 5. Capability registry changes

Add/refine:

```yaml
capabilities:
  architecture_discovery:
    preferred_evidence: [architecture_node, domain_flow, relationship_edge]

  exact_source_inspection:
    authoritative_for: [exact_code_fact]

  dependency_analysis:
    preferred_evidence: [dependency_path, blast_radius, call_path]

  historical_context_retrieval:
    preferred_evidence:
      [memory_reference, incident_reference, decision_reference, rejected_approach]

  business_knowledge_retrieval:
    preferred_evidence: [business_rule, business_document, domain_flow]

  convention_retrieval:
    preferred_evidence: [author_dna_rule, convention_rule]

  database_schema_inspection:
    preferred_evidence:
      [database_object, database_column, database_constraint, database_index,
       database_package, database_procedure]

  database_dependency_analysis:
    preferred_evidence: [database_dependency, sql_consumer, package_consumer]

  runtime_verification:
    preferred_evidence: [command_result, test_result, runtime_probe]
```

The runtime must use these capabilities operationally, not merely expose them in
prompt metadata.

---

## 6. Canonical knowledge artifacts

### `exploration/QUERY_PLAN.yaml`

```yaml
version: 1
change_id: example

questions:
  - id: Q-CODE-001
    question: Where is the validation chain assembled?
    required_capabilities:
      - architecture_discovery
      - dependency_analysis
      - exact_source_inspection
    required_evidence_types:
      - architecture_node
      - dependency_path
      - file_symbol
    status: pending

  - id: Q-MEM-001
    question: Has this flow caused incidents before?
    required_capabilities: [historical_context_retrieval]
    required_evidence_types: [incident_reference]
    zero_results_allowed: true
```

### `exploration/TOOL_HEALTH.yaml`

```yaml
version: 1

providers:
  understand_anything:
    configured: true
    status: ready
    indexed_commit: abc123
    freshness: fresh
    probe:
      operation: list_projects
      observed: 1 matching project

  codebase_memory:
    configured: true
    status: ready
    indexed_commit: abc123
    freshness: fresh

  agent_memory:
    configured: true
    status: ready
    backend_verified: true

  database:
    configured: true
    status: ready
    read_only: true
    schema: RLE
```

### Extended `exploration/EVIDENCE_MANIFEST.yaml`

```yaml
claims:
  - id: CODE-001
    question_id: Q-CODE-001
    statement: ValidationChainConfig assembles the chain.
    category: exact_code_fact
    status: verified
    confidence: high
    freshness:
      repository_commit: abc123
    sources:
      - type: architecture_node
        provider: understand_anything
        node_id: ...
      - type: dependency_path
        provider: codebase_memory
        indexed_commit: abc123
        path_id: ...
      - type: file_symbol
        file: ...
        symbol: ...
        file_hash: sha256:...
```

### `exploration/CONFLICTS.yaml`

```yaml
conflicts:
  - id: CONFLICT-001
    claim_ids: [CODE-004, MEM-003]
    type: stale_memory
    resolution: current source supersedes historical memory
    resolved_by: [CODE-004]
    status: resolved
```

### `exploration/COVERAGE.yaml`

```yaml
questions:
  total: 12
  answered: 11
  blocked: 1

required_evidence:
  covered: [exact_code_fact, dependency_path, business_rule]
  missing: [database_package]

verdict: NEEDS_CONTEXT
```

### `exploration/DATABASE_CONTEXT.yaml`

Required when persistence, SQL, DB packages, transactions, or migrations are in
scope.

### `briefs/TASK-NNN.knowledge.yaml`

```yaml
task_id: TASK-003

knowledge_slice:
  author_dna: [DNA-003]
  conventions: [CONV-011]
  code_evidence: [CODE-014, CODE-021]
  business_rules: [BIZ-007]
  historical_context: [MEM-003]
  database_evidence: [DB-004]

forbidden_patterns:
  - duplicate validation outside the configured chain

assumptions:
  - id: ASM-002
    statement: business date source remains unchanged
    confidence: medium

freshness:
  repository_commit: abc123
  evidence_manifest_hash: sha256:...
```

### `reviews/KNOWLEDGE_IMPACT.yaml`

```yaml
stale_entries: [ARCH-004]
superseded_decisions: [DEC-011]
new_candidates:
  - type: convention
    source: TASK-004
graph_refresh_required: true
memory_updates:
  - save incident-prevention lesson
```

---

## 7. New skill contract standard

Every reasoning skill must contain:

```text
Purpose
Triggers
Inputs
Knowledge questions
Required evidence types
Capability policy
Retrieval protocol
Authority and precedence
Required outcomes
Invariants
Evidence requirements
Freshness and confidence
Degradation protocol
Process
Stop conditions
Knowledge effects
Output contract
Next handoff
```

---

## 8. Skill-by-skill refactor

### 8.1 `intent-analysis`

Current gaps:

- classification relies too heavily on request text;
- no historical recall;
- no retrieval plan;
- risk may be underestimated.

New flow:

```text
raw request
→ historical recall
→ domain/convention lookup
→ initial source touchpoint search
→ risk signals
→ classification
→ knowledge-question generation
→ QUERY_PLAN.yaml
```

It must identify:

- likely modules;
- public contract risk;
- persistence risk;
- async risk;
- security risk;
- historical incident risk;
- mandatory and conditional capabilities.

### 8.2 `grounding-explorer`

This becomes Maika's central coordinator.

It must:

1. read the query plan;
2. probe providers;
3. route questions to capabilities;
4. use UA for architecture/domain;
5. use CBM for dependencies/blast radius;
6. use source for exact verification;
7. use Agent Memory for history;
8. dispatch DB exploration when applicable;
9. retrieve conventions and Author DNA;
10. persist claims with provenance;
11. build conflicts and coverage;
12. return readiness.

### 8.3 `database-explorer`

Restore as a conditional specialist.

Triggers:

```text
entity, repository, native SQL, table, column, index, constraint,
procedure, Oracle package, migration, transaction, locking,
job/outbox, audit, database performance
```

Responsibilities:

- read-only DB probe;
- inspect objects;
- map code consumers;
- compare source and live DB;
- record drift and assumptions;
- emit `DATABASE_CONTEXT.yaml`.

### 8.4 `architecture-reconciler`

It must reconcile evidence, not merely summarize it.

Build a claim matrix across:

```text
UA | CBM | source | memory | database | durable knowledge
```

Conflict types:

```text
stale graph
stale memory
source drift
database drift
business ambiguity
convention conflict
cross-service contract mismatch
```

Authority:

```text
current runtime/database state
> current source
> current explicit business contract
> fresh graphs
> approved durable knowledge
> historical memory
> inference
```

### 8.5 `grounded-brainstorming`

Every approach must include:

```text
extension seam
supporting evidence
conventions satisfied
conventions violated
historical failures
blast radius
database impact
migration impact
operational risk
security impact
unknowns
confidence
rejection reasons
```

Approaches must be derived from reconciled evidence.

### 8.6 `writing-spec`

Add:

- requirement-to-evidence mapping;
- current-to-desired behavior delta;
- business state model;
- contract ownership;
- persistence/async effects;
- historical constraints;
- applicable conventions;
- assumptions and expiry;
- testable ACs;
- evidence coverage.

### 8.7 `writing-plan`

Add:

#### Preconditions

```text
spec approved
grounding approved
material conflicts resolved
evidence fresh
base commit valid
```

#### Targeted re-grounding

Before exact instructions, verify:

- exact symbols;
- dependency path;
- blast radius;
- incident history;
- DB objects;
- task-specific conventions.

#### Implementation graph

```text
contracts
→ producers
→ consumers
→ migration
→ verification
→ cleanup
```

#### Decomposition doctrine

A task must:

- have one behavioral objective;
- be independently verifiable;
- contain code and its tests;
- not require architecture invention;
- have explicit write scope;
- map evidence and ACs;
- have explicit re-plan triggers.

Split when:

- multiple public contracts;
- multiple independent modules;
- DB and application rollout differ;
- producer and multiple consumers differ;
- migration and cleanup differ;
- transaction or deployment boundaries differ.

#### Whole-plan consistency

Check:

- every AC covered;
- producer before consumer;
- deletes after consumer migration;
- no cycles;
- names and contracts consistent;
- no orphan task;
- no duplicate ownership;
- no placeholders;
- no remaining consumer for delete targets.

### 8.8 `validating-plan`

Mechanical checks:

- schema, hashes, files, symbols, DAG, AC coverage, write scope, deletes,
  task-capsule references.

Knowledge checks:

- evidence freshness;
- mandatory provider use;
- DNA/convention compliance;
- historical incident coverage;
- DB evidence;
- architecture compatibility;
- delete consumer analysis;
- unresolved conflicts.

It must include an independent knowledge-grounded reviewer.

### 8.9 `executing-task`

The executor must:

1. read brief and knowledge capsule;
2. validate freshness;
3. re-read exact source anchors;
4. implement only declared scope;
5. run focused verification;
6. report new discoveries;
7. request re-grounding when evidence conflicts.

New statuses:

```text
NEEDS_REGROUNDING
EVIDENCE_CONFLICT
STALE_KNOWLEDGE
```

New artifact:

```text
results/TASK-NNN.EVIDENCE_UPDATE_REQUEST.yaml
```

### 8.10 `reviewing-task`

Reviewers must independently inspect:

- at least one source anchor per material behavior;
- every public contract;
- every deleted production file;
- every persistence boundary;
- every async/event boundary;
- every security-sensitive change.

They must check capsule compliance, conventions, incidents, blast radius, DB
contract, tests, and evidence drift.

### 8.11 `reviewing-change`

Add whole-change knowledge impact:

- stale knowledge;
- superseded decisions;
- new convention candidates;
- graph refresh;
- memory save/invalidation;
- DB and domain-model changes.

Write `KNOWLEDGE_IMPACT.yaml`.

### 8.12 `verification-before-completion`

Run real:

- build;
- unit/integration tests;
- static analysis;
- contract and migration tests;
- runtime smoke tests;
- deleted-reference scan;
- evidence-hash validation;
- graph/index freshness checks;
- DB assumption checks.

Record command, expected, observed, exit code, timestamp, interpretation, and
evidence path.

### 8.13 `knowledge-curator`

Redesign as four lifecycle modes:

```text
retrieve
record
reconcile
curate
```

It must operate before, during, and after implementation.

### 8.14 `author-dna-builder`

Add:

- candidate lifecycle;
- confidence;
- provenance;
- positive examples;
- counterexamples;
- scope;
- enforcement mapping;
- supersession;
- consumer list.

### 8.15 `convention-intelligence-builder`

Add:

- evidence threshold;
- examples and counterexamples;
- applies-to tags;
- scope matcher;
- conflict handling;
- enforcement type;
- supersession;
- consumers.

### 8.16 `infra-tdd`

Require infrastructure-specific evidence:

- K8s topology;
- deployment manifests;
- service graph;
- Kafka topics/groups;
- DB capacity/indexes;
- runtime logs/metrics;
- incident memory;
- rollout/rollback commands;
- operational verification.

---

## 9. Rules refactor

### `rules-knowledge.md`

Rewrite as a knowledge constitution with:

```text
knowledge sources
authority hierarchy
provenance
freshness
confidence
retrieval obligations
provider usage
conflict reconciliation
negative evidence
assumptions
invalidation
promotion
supersession
knowledge slices
memory save
database evidence
graph refresh
```

### `rules-tool.md`

Add:

- preferred provider policy;
- use-when-healthy;
- real probes;
- freshness;
- degradation;
- source authority;
- DB read-only;
- memory recall;
- graph freshness.

### `rules-flow.md`

Remove stale artifacts and old phase/command references. Replace them with the
canonical vNext workspace and lifecycle.

### `rules-guard.md`

Add preconditions for:

- query plan;
- provider health;
- evidence coverage;
- conflict resolution;
- task capsule;
- plan/evidence freshness;
- reviewer counter-evidence;
- real verification.

---

## 10. Workflow refactor

Canonical workflow:

```text
task start
→ intent analysis
→ knowledge questions
→ provider probes
→ grounding retrieval
→ evidence validation
→ conflict reconciliation
→ design
→ spec
→ targeted plan re-grounding
→ implementation plan
→ plan knowledge review
→ task-capsule compilation
→ isolated implementation
→ counter-evidence task review
→ final knowledge-impact review
→ real verification
→ knowledge promotion
→ archive
```

Public commands must dispatch real reasoning work, not merely validate manually
created files.

---

## 11. Gate changes

### `exploration-evidence`

Validate:

- query-plan coverage;
- provider health;
- healthy-provider usage;
- file existence;
- hash match;
- symbol existence;
- graph freshness;
- memory query execution;
- DB evidence when required;
- conflict resolution;
- evidence coverage and confidence.

### `spec`

Validate:

- requirement/evidence coverage;
- material behavior claims;
- assumptions;
- persistence/async/security sections;
- conventions;
- freshness.

### `plan`

Validate:

- targeted re-grounding;
- implementation DAG;
- evidence/AC mapping;
- task capsule references;
- deletion/migration ordering;
- incident handling;
- DB coverage;
- convention compliance;
- whole-plan consistency.

### `brief-integrity`

Validate:

- brief hash;
- knowledge-capsule hash;
- evidence hash;
- repository commit;
- plan hash;
- allowed files;
- applicable knowledge entries.

### `task-review`

Validate:

- reviewer read the brief and capsule;
- counter-evidence exists;
- contracts/deletes/DB/async/security inspected;
- verification evidence exists.

### `final-review`

Validate:

- full diff inspected;
- `KNOWLEDGE_IMPACT.yaml` exists;
- stale entries identified;
- graph refresh identified;
- no unresolved critical knowledge conflict.

### `archive-readiness`

Validate:

- real verification;
- knowledge promotion;
- supersession;
- memory saves;
- index regeneration;
- archive manifest.

---

## 12. Capability runtime refactor

The runtime must:

1. read questions and required evidence types;
2. resolve capabilities;
3. probe providers;
4. check freshness;
5. select preferred providers;
6. execute/dispatch retrieval;
7. persist evidence;
8. record degradation;
9. return confidence;
10. expose evidence to gates.

Target interfaces:

```python
route_question(
    question_id,
    required_evidence_types,
    repo_context,
    provider_state,
) -> RetrievalPlan
```

```python
execute_retrieval(
    retrieval_plan,
    output_paths,
) -> RetrievalResult
```

---

## 13. Tests

Required:

- every reasoning skill contains the knowledge-native sections;
- healthy preferred provider cannot be silently skipped;
- stale provider degrades;
- zero-result memory recall is valid;
- fake path/symbol/hash fails;
- stale graph commit fails/degrades;
- missing DB evidence blocks persistence changes;
- unresolved material conflict blocks design;
- query-plan coverage is enforced;
- task capsule integrity is enforced;
- counter-evidence review is enforced;
- verification runs real commands;
- knowledge promotion/supersession works;
- end-to-end standard workflow needs no manual state edits.

Dogfood one real Java change involving source, graph, conventions, Agent Memory,
database evidence, and a validation/Kafka/gRPC boundary.

---

## 14. Refactor waves

### W0 — Audit and consistency cleanup

- make CI green;
- inventory skills, rules, providers, consumers, stale artifacts;
- remove vNext/legacy contradictions;
- map knowledge and MCP gaps.

### W1 — Knowledge constitution and provider doctrine

- rewrite knowledge/tool rules;
- add historical and database capabilities;
- define precedence, freshness, confidence, degradation.

### W2 — Query plan and evidence package

- implement query plan, tool health, conflicts, coverage, DB context;
- strengthen exploration gate beyond shape validation.

### W3 — Core reasoning skill rewrite

Rewrite intent, grounding, DB explorer, reconciliation, brainstorming, spec,
plan, and plan validation.

### W4 — Task capsules and execution feedback

- compile task knowledge capsules;
- add freshness checks and re-grounding requests.

### W5 — Counter-evidence review and knowledge impact

- rewrite task/final review;
- implement independent evidence checks and knowledge-impact reporting.

### W6 — Real verification and knowledge lifecycle

- execute real commands;
- implement invalidation, promotion, supersession, memory save, graph refresh.

### W7 — Full orchestration and dogfood

- public lifecycle runs end to end;
- no manual state/artifact editing;
- downstream Java/DB/async dogfood;
- final cleanup.

---

## 15. Definition of done

1. Every reasoning skill is knowledge-question-driven.
2. Every standard/architectural change has a query plan.
3. Provider health is probed and persisted.
4. UA is used for architecture/domain discovery when healthy.
5. CBM is used for dependencies/blast radius when healthy.
6. Agent Memory recall runs for standard/architectural changes.
7. DB exploration runs for persistence-sensitive changes.
8. Current source verifies exact code facts.
9. Evidence authenticity is mechanically checked.
10. Material conflicts block design.
11. Spec requirements map to evidence.
12. Plans perform targeted re-grounding.
13. Plans create an implementation graph.
14. Plans create task knowledge capsules.
15. Executors consume capsules.
16. Executors can request re-grounding.
17. Reviewers seek counter-evidence.
18. Final review reports knowledge impact.
19. Verification runs real commands.
20. Knowledge is invalidated, promoted, superseded, and saved.
21. Graph/index refresh happens when required.
22. Public workflow needs no manual state edits.
23. CI is green.
24. Real downstream Java dogfood passes.
25. No stale knowledge/workflow artifacts remain.
26. No provider capability exists only as metadata.
27. Shape-only fake evidence cannot pass.
28. Maika behavior is materially different from generic Superpowers.

---

# Codex Implementation Prompt

Copy the following prompt into Codex.

---

## PROMPT START

You are the lead implementation agent for the Maika knowledge-native reasoning
refactor.

Read and follow:

- `MAIKA_KNOWLEDGE_NATIVE_REASONING_REFACTOR.md`
- the current repository source and tests
- all current skills, rules, workflows, gates, capabilities, provider mappings,
  platform adapters, and scaffold manifests

## Mission

Refactor Maika so that the lifecycle is driven by:

```text
knowledge questions
→ provider-backed retrieval
→ evidence validation
→ conflict reconciliation
→ evidence-grounded decisions
→ task knowledge capsules
→ counter-evidence review
→ real verification
→ knowledge evolution
```

Do not merely make skill files longer.

Do not stop at documentation, schemas, capability names, or prompts.

The runtime, gates, orchestration, provider routing, tests, and public workflow
must enforce the new model.

## Core identity requirement

The completed system must be clearly different from a generic
Superpowers-style framework.

It must actively use, through abstract capabilities:

- Understand-Anything;
- Codebase Memory MCP;
- Agent Memory MCP;
- current source;
- durable project knowledge;
- read-only Database Explorer / DB MCP where applicable.

## Implementation rules

- Remove stale workflow and artifact concepts.
- Do not create duplicate knowledge systems.
- Do not put concrete provider calls in canonical skills.
- Do not preserve shape-only validators where authenticity is verifiable.
- Do not create backup files or compatibility copies.
- Keep sequential task execution unless explicitly required otherwise.
- Keep commits scoped and reviewable.
- Keep CI green after every wave.
- Continue through W0–W7 without asking for routine confirmation.

## Mandatory work

### Knowledge constitution

Rewrite `rules-knowledge.md` to define:

- sources;
- authority;
- provenance;
- freshness;
- confidence;
- retrieval obligations;
- provider use;
- conflict reconciliation;
- assumptions;
- invalidation;
- promotion;
- supersession;
- knowledge slices;
- memory save;
- DB evidence;
- graph refresh.

### Provider doctrine

Rewrite `rules-tool.md` to enforce:

- preferred provider use when healthy;
- real probes;
- freshness records;
- explicit degradation;
- source authority;
- Agent Memory recall for standard/architectural changes;
- DB evidence for persistence changes;
- UA for architecture/domain discovery;
- CBM for dependency/blast radius.

### Capabilities

Add:

```text
historical_context_retrieval
database_schema_inspection
database_dependency_analysis
```

Make capability runtime operational, not metadata-only.

### Grounding package

Implement:

```text
QUERY_PLAN.yaml
TOOL_HEALTH.yaml
GROUNDING.yaml
EVIDENCE_MANIFEST.yaml
CONFLICTS.yaml
COVERAGE.yaml
DATABASE_CONTEXT.yaml when applicable
```

### Skills

Deeply rewrite:

```text
intent-analysis
grounding-explorer
database-explorer
architecture-reconciler
grounded-brainstorming
writing-spec
writing-plan
validating-plan
executing-task
reviewing-task
reviewing-change
verification-before-completion
knowledge-curator
author-dna-builder
convention-intelligence-builder
infra-tdd
```

Every reasoning skill must include:

```text
Knowledge questions
Required evidence types
Capability policy
Retrieval protocol
Authority and precedence
Freshness and confidence
Degradation protocol
Knowledge effects
```

### Planning

`writing-plan` must implement:

- targeted re-grounding;
- cross-plan dependency detection;
- implementation graph;
- decomposition doctrine;
- evidence and AC mapping;
- task knowledge capsules;
- deletion/migration ordering;
- whole-plan consistency;
- re-plan triggers.

### Task knowledge capsules

Compile:

```text
briefs/TASK-NNN.md
briefs/TASK-NNN.knowledge.yaml
```

Capsules contain:

- Author DNA;
- conventions;
- code evidence;
- business rules;
- historical memory;
- DB evidence;
- forbidden patterns;
- assumptions;
- freshness.

### Review

Reviewers must seek independent counter-evidence.

Task review independently inspects high-risk source, contracts, deletes,
persistence, async, and security boundaries.

Final review writes:

```text
reviews/KNOWLEDGE_IMPACT.yaml
```

### Verification

Run actual commands and record:

```text
command
expected
observed
exit code
timestamp
interpretation
evidence path
```

Do not complete from file existence, textual markers, or exit code alone.

### Knowledge lifecycle

Implement:

```text
retrieve
record
reconcile
curate
```

Promote verified knowledge, supersede stale entries, save episodic memory,
regenerate indexes, and trigger graph refresh.

## Gate requirements

Critical gates must reject:

- fake paths;
- fake symbols;
- fake hashes;
- stale graph evidence;
- skipped healthy providers;
- missing memory recall;
- missing DB evidence;
- unresolved material conflicts;
- incomplete evidence coverage;
- stale task capsules;
- review without counter-evidence;
- completion without real verification.

## Workflow requirement

The public workflow must run end to end without manually editing:

- `STATE.yaml`;
- grounding artifacts;
- result files;
- review files.

It must dispatch the actual reasoning and retrieval work.

## Execution protocol

For each wave:

1. inspect repository reality;
2. write an exact implementation plan;
3. verify files and symbols;
4. identify tests first;
5. run independent plan review;
6. fix Critical/Important findings;
7. execute tasks sequentially;
8. run focused tests;
9. run independent task review;
10. delete stale references and dead files;
11. run full relevant CI;
12. commit;
13. continue to the next wave.

## Dogfood

Run at least one real downstream Java change exercising:

- architecture/domain graph;
- code dependency graph;
- exact source;
- project conventions;
- historical memory;
- DB exploration;
- a validation chain, Kafka, gRPC, or other integration boundary.

## Stop conditions

Stop only for:

- an uncovered public-contract decision;
- a destructive DB decision;
- a security decision;
- provider credentials/access that cannot degrade safely;
- a repository contradiction that changes target architecture;
- an unrecoverable environment failure.

Do not stop for routine implementation choices.

## Final report

Return:

- files created/rewritten/deleted;
- skills rewritten;
- capabilities added;
- gates strengthened;
- workflow/runtime changes;
- tests and CI results;
- dogfood results;
- remaining Minor findings;
- final commit SHA;
- readiness verdict.

Do not declare completion until every Definition of Done item in
`MAIKA_KNOWLEDGE_NATIVE_REASONING_REFACTOR.md` is satisfied.

Begin with W0 and continue through W7.

## PROMPT END
