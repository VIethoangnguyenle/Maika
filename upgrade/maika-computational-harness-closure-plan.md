# Maika Computational Harness Closure Plan

## Scope: Maika-only integration of Understand-Anything MCP, Codebase Memory MCP and DB Access

```text
Repository: VIethoangnguyenle/Maika
Branch: master-v2
Baseline: 1877a757fe1045a5f9b64bdede157e4f5f8a1d10
```

---

# 1. Mission

Đóng dứt điểm khoảng cách giữa:

```text
provider doctrine
skill metadata
workflow routing
worker prompt
MCP usage
evidence
gate
state transition
```

Ba MCP được xem là external black boxes có thể chạy local hoặc remote. Maika chỉ sở hữu:

```text
client provider IDs
tested tool snapshots
capability routing
host-delegated MCP invocation contract
worker context
evidence artifacts
gates
state transitions
refresh/re-probe lifecycle
cross-host qualification
```

---

# 2. Core best practices

```text
Harness Engineering
Policy as Code
Ports and Adapters
Least Privilege
Evidence over Self-reporting
Context Engineering
Observability and Tracing
Eval-driven Development
Resumable Workflows
```

Five invariants:

```text
1. Deterministic shell, stochastic core
2. Capabilities over providers
3. Evidence over agent claims
4. Least privilege by construction
5. Every recurring failure becomes a computational control
```

---

# 3. Provider roles

## Understand-Anything MCP

Primary:

```text
architecture_discovery
domain_flow_trace
call_chain_trace
impact_analysis
graph_path_trace
inheritance_trace
```

## Codebase Memory MCP

Primary:

```text
semantic_code_search
```

Conditional support:

```text
unresolved_anchor
ambiguous_semantic_query
graph_gap
relevant_graph_stale
hidden_consumer_risk
dynamic_wiring_risk
reviewer_counter_evidence
ua_unavailable
database_code_consumer_gap
```

## Current source

Authority:

```text
exact_code_fact
exact_application_behavior
exact_query_text
exact_annotation
exact_configuration
exact_test_behavior
```

## DB Access

Provider for observed database evidence.

## Database Explorer

Maika skill that detects persistence questions, uses the read-only exploration lane, maps code consumers, classifies drift and produces DATABASE_CONTEXT.

---

# 4. Non-goals

Do not:

```text
change MCP source code
change MCP package/server identities
change deployment topology
manage DB credentials or tunnels
require local binaries
change existing MCP return formats
make DB Access globally read-only
force CBM on every task
```

---

# 5. Current blockers

## B1 — CBM typed as mandatory

Grounding and review skills still require semantic search and dependency analysis.

## B2 — Provider-specific gates

Current gates still depend on `node_id`, `blast-radius`, `trace via cbm` and UA prose patterns.

## B3 — Provider health is self-reported

Doctor/bootstrap detect configuration, not actual MCP invocation evidence.

## B4 — Database Explorer is not mechanically routed

Persistence-sensitive exploration can complete without DATABASE_CONTEXT.

## B5 — DB lane is policy-only

Workers are not pinned to allowed MCP tools.

## B6 — Worker context is not content-addressed

Workers receive a skill name rather than exact policy files and hashes.

## B7 — Refresh workflow is not resumable

External workflow requests do not yet complete a durable BLOCKED → re-probe → resume lifecycle.

---

# 6. Target architecture

```text
User task
  ↓
Intent classifier
  ↓
Risk signals
  ↓
Capability requirement compiler
  ↓
Provider resolver
  ↓
Host-delegated MCP calls
  ↓
Maika adapter normalization
  ↓
TRACE_EVIDENCE / DATABASE_CONTEXT
  ↓
Provider-neutral gates
  ↓
Pinned worker context
  ↓
Worker reasoning
  ↓
Review / verification
  ↓
State transition
```

---

# 7. Canonical artifacts

## CAPABILITY_REQUIREMENTS.yaml

```yaml
version: 1
change_id:
role:
required: []
one_of: {}
conditional: {}
activated_triggers: []
degradation_policy: {}
```

## PROVIDER_INVOCATIONS.jsonl

One record per MCP call:

```json
{
  "trace_id": "",
  "change_id": "",
  "role": "",
  "provider_id": "",
  "tool": "",
  "invocation_mode": "host_mcp",
  "request_hash": "sha256:",
  "response_hash": "sha256:",
  "started_at": "",
  "ended_at": "",
  "status": "success|error|timeout",
  "normalized_artifact": "",
  "trigger": "",
  "reason": ""
}
```

## TRACE_REQUEST.yaml

```yaml
version: 1
change_id:
questions: []
anchors: []
required_capabilities: []
optional_capabilities: []
freshness_requirement:
source_verification_requirement:
cbm_triggers: []
```

## TRACE_EVIDENCE.yaml

```yaml
version: 1
change_id:
provider_observations: []
graph:
  project:
  graph_commit:
  repository_head:
  freshness:
  health:
  relevant_stale_files: []
anchors: []
traversals: []
impact: []
support_calls: []
source_verifications: []
limitations: []
confidence:
complete:
```

## DATABASE_REQUEST.yaml

```yaml
version: 1
change_id:
environment:
database:
questions: []
objects: []
required_capabilities: []
allowed_lane: exploration
data_probe_required: false
source_anchors: []
migration_refs: []
```

## DATABASE_CONTEXT.yaml v2

```yaml
version: 2
change_id:
read_only: true
provider:
  id: db-access
  client_key: db-access
probe:
  invocation_mode: host_mcp
  database:
  environment:
  observed_at:
  status:
allowed_lane: exploration
allowed_tools: []
used_tools: []
observations: []
code_consumers: []
drift: []
degradation: []
limitations: []
confidence:
```

---

# 8. Typed capability contract

```yaml
capabilities:
  required:
    - exact_source_inspection

  one_of:
    structured_trace:
      - architecture_discovery
      - domain_flow_trace
      - call_chain_trace

  conditional:
    semantic_code_search:
      triggers:
        - unresolved_anchor
        - ambiguous_semantic_query
        - graph_gap
        - relevant_graph_stale
        - hidden_consumer_risk
        - reviewer_counter_evidence
        - ua_unavailable

    database_schema_inspection:
      triggers:
        - persistence_change

    database_dependency_analysis:
      triggers:
        - database_dependency_risk
```

Validator rules:

```text
unknown capability → fail
unknown trigger → fail
same capability in required and conditional → fail
conditional provider call without trigger → fail
activated trigger without evidence/degradation → fail
one_of group unsatisfied → fail
```

---

# 9. Skill migrations

## Grounding Explorer

Required:

```text
exact_source_inspection
historical_context_retrieval
business_knowledge_retrieval
convention_retrieval
```

One-of:

```text
architecture_discovery
domain_flow_trace
call_chain_trace
```

Conditional:

```text
impact_analysis
semantic_code_search
dependency_analysis
database_schema_inspection
database_dependency_analysis
```

## Reviewing Task

Required:

```text
exact_source_inspection
runtime_verification
review_dispatch
```

Conditional:

```text
call_chain_trace
impact_analysis
semantic_code_search
dependency_analysis
historical_context_retrieval
database_schema_inspection
```

## Reviewing Change

Required:

```text
exact_source_inspection
runtime_verification
```

Conditional:

```text
call_chain_trace
impact_analysis
semantic_code_search
dependency_analysis
historical_context_retrieval
database_schema_inspection
```

---

# 10. Persistence risk model

Add to CHANGE.yaml:

```yaml
risk_signals:
  persistence: false
  database_dependency: false
  migration: false
  transaction_or_locking: false
  runtime_data_question: false
```

Rules:

```text
persistence=false
→ DB artifacts optional

persistence=true
→ database-explorer required
→ DATABASE_REQUEST required
→ DATABASE_CONTEXT required
→ database-context gate required

trivial/small + persistence=true
→ escalate to standard
```

---

# 11. Database lane enforcement

## Exploration

```text
list_databases
sql_list_tables
sql_get_columns
sql_get_constraints
mongo_list_collections
mongo_get_schema
```

## Data probe

```text
sql_read
mongo_read
```

Activation: explicit runtime data question.

## Explicit write

```text
sql_write
mongo_write
```

Activation: explicit user request.

## Explicit script

```text
sql_execute_script
```

Activation: explicit user request.

For database-explorer:

```text
allowed lane = exploration
```

Prompt must include allowed and denied tools. Gate rejects out-of-lane tool use.

---

# 12. Host-delegated MCP invocation

MCPs may run on other machines. Maika does not own their connections.

Required sequence:

```text
Maika compiles invocation request
→ host calls MCP
→ raw response returned
→ Maika adapter normalizes
→ request/response hashes recorded
→ evidence gate validates
```

No invocation evidence means the provider claim is untrusted.

---

# 13. Maika-side adapters

Create:

```text
cli/mcp/integration/
├── base.py
├── understand_anything.py
├── codebase_memory.py
├── db_access.py
└── current_source.py
```

Responsibilities:

```text
validate provider ID
validate tool against snapshot
validate allowed lane
normalize response
record truncation
record warnings/errors
hash request and response
redact secrets/sensitive rows
emit stable internal evidence
```

Adapters must not manage provider processes, credentials or deployment.

---

# 14. Provider-neutral gate migration

Remove active dependencies on:

```text
node_id + blast-radius
trace via cbm
UA evidence phrase
KG unavailable phrase
generic db_query
```

Add gates:

```text
capability-requirements
provider-invocations
trace-request
trace-evidence
conditional-provider-use
source-verification
database-request
database-context-v2
provider-tool-lane
context-package-freshness
```

Trace gate checks capability satisfaction, invocation evidence, freshness, truncation, source verification and CBM trigger/reason.

Database gate checks persistence signal, environment/database, provider invocation, lane, used tools, drift classification and code-consumer evidence.

---

# 15. Worker context pinning

Every dispatch includes:

```text
SKILL_FILE
SKILL_SHA256
CAPABILITY_REQUIREMENTS_FILE
CAPABILITY_REQUIREMENTS_SHA256
PROVIDER_REGISTRY_FILE
PROVIDER_REGISTRY_SHA256
PROVIDER_TOOL_POLICY_FILE
PROVIDER_TOOL_POLICY_SHA256
TRACE_REQUEST_FILE
TRACE_REQUEST_SHA256
TRACE_EVIDENCE_FILE
TRACE_EVIDENCE_SHA256
DATABASE_REQUEST_FILE
DATABASE_REQUEST_SHA256
DATABASE_CONTEXT_FILE
DATABASE_CONTEXT_SHA256
```

Worker instruction:

```text
Do not infer provider policy from memory.
Use only pinned provider/tool contracts.
Do not claim provider health without invocation evidence.
Do not call tools outside allowed lane.
```

---

# 16. Refresh and resume

## UA refresh

```text
worker detects stale graph
→ writes external workflow request
→ orchestrator validates
→ state = BLOCKED
→ blocker persisted
→ user/parent runs /understand
→ new get_graph_metadata evidence
→ request fulfilled
→ original role redispatched
```

## DB re-probe

```text
DB context stale or environment changed
→ DB_REPROBE_REQUEST
→ host calls DB Access
→ DATABASE_CONTEXT revision
→ updated hash
→ resume
```

Never rely on parent conversation memory.

---

# 17. State-machine additions

Blocked state:

```yaml
state: BLOCKED
blocked:
  reason:
  role:
  request_file:
  remediation:
  created_at:
  resume_action:
```

Resolution:

```yaml
resolved:
  result_file:
  evidence_hash:
  resolved_at:
```

---

# 18. Observability

Extend dispatch log with:

```text
trace_id
change_id
role
worker_id
provider_calls
artifacts_read
artifacts_written
gate_results
state_before
state_after
started_at
ended_at
```

The trace must answer:

```text
Was UA called?
Which tool?
Was CBM called?
Why?
Was DB Access called?
Which lane?
Was an out-of-lane tool used?
Which response produced TOOL_HEALTH?
Which source verification supports the final claim?
```

---

# 19. Data safety

For DB evidence:

```text
redact credentials and connection strings
do not persist confirmation tokens
do not persist raw rows without a data-probe trigger
limit raw Mongo samples
store schema shape by default
```

---

# 20. System-model validator

Add:

```bash
maika content validate-system-model
```

Model:

```text
risk signal
→ skill
→ capability requirement
→ provider
→ tool
→ lane
→ request artifact
→ invocation record
→ evidence artifact
→ gate
→ state transition
```

Checks all links exist and agree.

---

# 21. Mutation tests

CI must catch:

1. CBM semantic search moved back to required.
2. Reviewer calls CBM without trigger.
3. UA trace has no provider invocation.
4. Worker claims fresh graph without response hash.
5. Persistence task lacks DATABASE_CONTEXT.
6. Database Explorer calls `sql_read`.
7. Database Explorer calls write/script.
8. DB context omits environment.
9. Drift is unclassified.
10. Worker prompt lacks skill hash.
11. Provider registry changes after acknowledgment.
12. Workflow request does not enter BLOCKED.
13. Refresh is fulfilled without new evidence.
14. Explicit empty `request_only` gets defaults.
15. Gate demands provider-specific prose.
16. Unknown provider tool appears.
17. Truncated response claims complete.
18. Source verification hash is missing.
19. Context package uses stale evidence.
20. Cross-host snapshot diverges.

---

# 22. Deterministic fixtures

## Code

```text
F1 Fresh complete UA path → no CBM → PASS
F2 Ambiguous anchor → CBM anchor → UA trace → PASS
F3 Graph gap → CBM support → source resolve → PASS
F4 Hidden consumer review → CBM counter-evidence
F5 Unnecessary CBM call → FAIL
F6 Fake provider health → FAIL
```

## Database

```text
F7 Non-persistence task → no DB route
F8 Persistence task → DB context mandatory
F9 DB unavailable → structured degradation
F10 DB write leak → FAIL
F11 Runtime data question → data-probe allowed
F12 Wrong environment → FAIL
```

## Resume

```text
F13 UA refresh → BLOCKED → new evidence → resume
F14 request_only: [] remains empty
```

---

# 23. Cross-host qualification

Run fixtures on:

```text
Claude Code
Codex
Antigravity
```

Thresholds:

```text
UA selected for structured trace ≥ 95%
unnecessary CBM calls ≤ 5%
provider calls with invocation evidence = 100%
material exact facts source-verified = 100%
persistence trigger precision ≥ 95%
Database Explorer write/script use = 0
resume success = 100%
cross-host outcome equivalence ≥ 95%
```

---

# 24. PR sequence

## M2 — Typed capability schema

Implement `required`, `one_of`, `conditional`, triggers and migrate core skills.

## M3 — Provider invocation evidence

Implement PROVIDER_INVOCATIONS, request/response hashing and delegated host records.

## M4 — Trace request/evidence

Implement TRACE_REQUEST, TRACE_EVIDENCE, UA adapter, CBM support-call records and source verification.

## M5 — Provider-neutral gate migration

Remove CBM-specific and UA-prose gates.

## M6 — Persistence routing

Implement persistence signals, Database Explorer dispatch, DATABASE_REQUEST, DATABASE_CONTEXT v2 and conditional gates.

## M7 — DB lane enforcement

Inject allowed/denied tool sets and reject out-of-lane calls.

## M8 — Worker context pinning

Pin control surfaces and hashes.

## M9 — Refresh/re-probe lifecycle

Implement durable BLOCKED, request/result artifacts, re-probe and resume.

## M10 — Observability and system-model validator

Add end-to-end trace, validator and mutation suite.

## M11 — Behavior qualification

Run deterministic and cross-host journeys; remove legacy provider-specific gates.

---

# 25. Slice execution gate

Every PR:

```text
inspect current source
→ narrow implementation note
→ implement one slice
→ targeted tests
→ mutation tests
→ full CI
→ behavior fixture
→ git diff --check
→ clean working tree
→ stop and report
```

Do not combine multiple phases into one large PR.

---

# 26. Acceptance criteria

1. Skill schema supports required/one_of/conditional.
2. CBM is not required for grounding.
3. CBM is not required for every review.
4. Every conditional call has trigger and reason.
5. Every trusted MCP call has invocation evidence.
6. Every invocation has request/response hashes.
7. Agent self-reported health cannot pass alone.
8. Complete UA trace passes without CBM.
9. Unnecessary CBM call fails.
10. Material facts have source hashes.
11. Persistence risk is typed.
12. Persistence task routes to Database Explorer.
13. DATABASE_CONTEXT is mandatory for persistence.
14. Database Explorer only uses exploration tools.
15. Data probe needs explicit trigger.
16. Write/script is impossible in Database Explorer context.
17. DB context includes environment/database/time.
18. Drift is classified.
19. Worker receives skill and provider policy hashes.
20. Stale acknowledgment blocks dispatch.
21. External refresh enters BLOCKED.
22. Refresh needs new provider evidence.
23. Resume redispatches the original role.
24. Explicit empty request_only stays empty.
25. No active gate requires CBM by name.
26. No active gate parses UA evidence prose.
27. Gates operate on typed evidence.
28. All fixtures and mutation tests pass.
29. Claude, Codex and Antigravity qualification pass.
30. No Critical/High integration findings remain.

---

# 27. Definition of Done

```text
UA is mechanically primary for structured trace
CBM is mechanically conditional
current source is mechanically authoritative
provider health is backed by invocation evidence
Database Explorer is mechanically required by persistence risk
Database Explorer is mechanically limited to its DB lane
worker control surfaces are content-addressed
provider-specific gates are removed
refresh/re-probe is resumable
cross-host behavior is qualified
```

Not sufficient:

```text
policy prose updated
provider registry exists
worker says it called a provider
DB context says read_only: true
one manual demo works
```

---

# 28. Codex kickoff prompt

```text
Implement the Maika Computational Harness Closure Plan in:

Repository: VIethoangnguyenle/Maika
Branch: master-v2
Baseline: 1877a757fe1045a5f9b64bdede157e4f5f8a1d10

External dependencies are black boxes:
- Understand-Anything MCP
- Codebase Memory MCP
- DB Access

Do not modify their repositories, deployment, credentials, identities or return formats.

Start with M2 only:
- add required/one_of/conditional capability semantics;
- migrate grounding-explorer, reviewing-task, reviewing-change and database-explorer;
- make CBM semantic search conditional;
- add trigger validation;
- add positive, negative and mutation tests;
- run full CI, git diff --check and clean-tree verification;
- stop after the M2 report.

Do not implement provider invocation adapters, persistence routing or gate migration
in the same PR.
```
