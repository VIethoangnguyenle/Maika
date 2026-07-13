> **Status: AMENDED** by `upgrade/provider-convergence-integration-first-errata.md`
> (2026-07-13). The errata overrides strict cross-repository rename/rewrite work,
> provider deployment assumptions, and any requirement to change stable MCP behavior.

# Maika Provider Convergence & Closure Plan

## Understand-Anything + Codebase Memory + DB Access

### Codex-ready, cross-repository execution plan

```text
Primary repository:
  VIethoangnguyenle/Maika
  branch: master-v2
  baseline: 37424721e5171f176692f4b0e2de14dc64808870

Structured graph provider:
  VIethoangnguyenle/Understand-Anything-MCP
  branch: main
  baseline: 0b4f3e2b18dc038bf28856821f568f05358fab2d

Database provider:
  VIethoangnguyenle/Db-Access
  branch: main
  baseline: eb7292e4645f1c81d8b7a32062130d6833b8f12b
```

---

# 1. Mission

Thực hiện một **Provider Convergence Release** để đóng dứt điểm hai nhóm vấn đề tồn tại lâu dài trong Maika:

```text
A. Understand-Anything integration
B. Database Explorer / DB Access integration
```

Không tiếp tục mô hình:

```text
sửa provider doctrine
→ skill metadata vẫn lệch
→ gate vẫn kiểm mô hình cũ
→ runtime không thực thi probe
→ worker tự đoán evidence
→ review tiếp tục phát hiện contradiction mới
```

Target cuối cùng:

```text
Understand-Anything
→ tạo code graph và domain graph

Understand-Anything-MCP
→ primary structured graph navigation/tracing

Codebase Memory MCP
→ primary semantic discovery;
  graph-gap recovery;
  hidden-consumer search;
  reviewer counter-evidence

Current source
→ authority cuối cùng cho exact code fact

DB Access
→ authority cho live database observation

database-explorer
→ Maika skill reconcile:
  source ↔ graph ↔ live DB ↔ migration intent
```

Maika phải vận hành hai pipeline deterministic:

```text
CODE TRACE PIPELINE
TRACE_REQUEST
→ provider resolution
→ UA health/freshness
→ structured UA trace
→ conditional CBM support
→ current-source verification
→ TRACE_EVIDENCE
→ provider-neutral gate
```

```text
DATABASE PIPELINE
persistence signal
→ DB_REQUEST
→ DB Access health/capability probe
→ read-only catalog/schema/dependency inspection
→ current-source/migration reconciliation
→ DATABASE_CONTEXT
→ persistence gate
```

---

# 2. Final naming decisions

## 2.1 Database provider

Chỉ dùng duy nhất:

```text
db-access
```

Canonical surfaces:

```text
Provider ID: db-access
Display name: DB Access
MCP server name: db-access
MCP client config key: db-access
npm package: db-access
CLI/bin: db-access
Docker/container: db-access
systemd unit: db-access.service
Environment prefix: DB_ACCESS_
```

Không alias, không fallback, không compatibility wrapper.

Old configuration must be migrated before the new release is installed.

## 2.2 Database skill

Giữ nguyên:

```text
database-explorer
```

Reason:

```text
db-access
→ provider transporting and protecting database access

database-explorer
→ Maika reasoning skill deciding what to inspect,
  reconciling evidence and producing DATABASE_CONTEXT
```

## 2.3 Code providers

```text
understand-anything
codebase-memory-mcp
current-source
```

Internal artifacts must use exactly those canonical IDs.

---

# 3. Non-negotiable architectural roles

## Understand-Anything-MCP

Primary for:

```text
architecture traversal
domain-flow trace
call-chain trace
graph relationship traversal
impact analysis
graph path search
inheritance trace
graph-node source extraction
```

## Codebase Memory MCP

Primary for:

```text
semantic anchor discovery
natural-language code search
ambiguous symbol discovery
```

Conditional support for:

```text
graph gap
missing relationship
hidden consumer
dynamic wiring risk
relevant stale graph
independent reviewer counter-evidence
UA unavailable or invalid
```

It must not run on every task merely to repeat a complete UA result.

## Current source

Authoritative for:

```text
exact method signature
branch condition
annotation
query text
configuration
test behavior
current file existence
exact public/runtime contract
```

## DB Access

Authoritative for:

```text
observed live DB state in the selected environment
current schema/catalog objects
column types/nullability
constraints/indexes
routines/packages/procedures
database-internal dependencies
safe read probes
```

## Migration/spec

Authoritative for:

```text
intended target database state
```

Live DB must not automatically override an approved target migration.

---

# 4. Authority model

## 4.1 Code-side facts

```text
Exact current code:
current source

Structural navigation:
UA-MCP

Semantic discovery/counter-evidence:
Codebase Memory
```

## 4.2 Persistence facts

```text
Observed current environment:
DB Access live probe

Intended target state:
approved migration/spec

Exact current application behavior:
current source

Code consumers:
UA-MCP + conditional Codebase Memory + current source
```

## 4.3 Drift classification

Every source/live mismatch must be classified as one of:

```text
unexpected_runtime_drift
expected_pre_deployment_drift
expected_post_deployment_drift
environment_specific_difference
source_bug
migration_bug
provider_visibility_gap
unresolved
```

Do not use the blanket rule:

```text
live DB always wins
```

---

# 5. Non-goals

Do not:

```text
replace current source with graph results
merge UA-MCP and Codebase Memory into one provider
turn DB Access into a general DBA automation platform
let database-explorer execute writes
force native read-only queries into /task
auto-run /understand without user-visible lifecycle
parse human prose and call it structured evidence
retain old DB provider names
add a generic provider framework before the two target providers pass closure
```

---

# 6. Closure invariants

## Provider identity

1. Every provider has one canonical ID.
2. Every provider reference resolves through one provider registry.
3. No active file contains obsolete DB provider/server names.
4. Provider setup, health, capabilities, artifacts and doctor reports use the same ID.

## Capability model

5. Skills use capability IDs, never provider names.
6. Capabilities support `required`, `one_of` and `conditional`.
7. Conditional capability calls require an activated trigger and reason.
8. Codebase Memory is not globally required for structured tracing.
9. Database capabilities are required only when persistence risk is active.

## Provider execution

10. Provider registration is not health.
11. Health comes from a real probe.
12. Structured provider output is schema-validated.
13. Provider timeout/error/degradation is explicit.
14. No worker may invent provider health.

## Evidence

15. Trace evidence is provider-neutral.
16. Database evidence includes provider, environment, object identity, timestamp and hashes.
17. Exact material code facts have current-source verification.
18. Live DB observations are separated from intended migration state.
19. Truncated output cannot support a completeness claim.
20. Negative/zero results are retained.

## UA

21. A complete UA trace can pass without Codebase Memory.
22. Relevant stale graph lowers authority.
23. Dirty worktree is included in freshness.
24. Invalid/degenerate graph cannot be treated as healthy.
25. Graph generation has checkpoint, resume and quality validation.

## DB

26. Database Explorer is mechanically triggered by persistence signals.
27. Database Explorer is read-only at both Maika and provider boundaries.
28. DB metadata permission is separate from data-read permission.
29. A Maika DB source cannot see write/script tools.
30. DB session is bound to the authenticated source.
31. Schema/owner is explicit.
32. Sensitive data is minimized and masked.

## Gates

33. Gates check capability/evidence contracts, not provider-specific prose.
34. A gate cannot demand CBM evidence by name.
35. Persistence-sensitive exploration cannot pass without DB evidence or valid degradation.
36. Provider-specific compatibility paths have an expiry and are removed before closure.

## Qualification

37. Deterministic fixtures pass.
38. Mutation tests catch identity, capability and gate drift.
39. Claude, Codex and Antigravity execute equivalent journeys.
40. No Critical/High findings remain.

---

# 7. Target provider model

Create one canonical Maika model:

```text
.maika/config/provider-registry.yaml
```

Example:

```yaml
version: 1

providers:
  understand-anything:
    display_name: Understand-Anything MCP
    kind: structured_code_graph
    setup_ref: understand-anything

    contract:
      id: understand-anything
      minimum_version: 1
      maximum_tested_version: 1

    capabilities:
      primary:
        - architecture_discovery
        - domain_flow_trace
        - call_chain_trace
        - impact_analysis
        - graph_path_trace
        - inheritance_trace

  codebase-memory-mcp:
    display_name: Codebase Memory MCP
    kind: semantic_code_index
    setup_ref: codebase-memory-mcp

    capabilities:
      primary:
        - semantic_code_search
      supporting:
        - architecture_discovery
        - call_chain_trace
        - impact_analysis
        - database_code_consumer_analysis

  current-source:
    display_name: Current Source
    kind: local_authority
    synthetic: true

    capabilities:
      primary:
        - exact_source_inspection
        - database_code_consumer_analysis

    authoritative_for:
      - exact_code_fact
      - exact_application_behavior

  db-access:
    display_name: DB Access
    kind: database
    setup_ref: db-access

    contract:
      id: db-access
      minimum_version: 1
      maximum_tested_version: 1

    capabilities:
      primary:
        - database_catalog_discovery
        - database_schema_inspection
        - database_constraint_inspection
        - database_index_inspection
        - database_routine_inspection
        - database_internal_dependency_analysis
        - database_read_probe
```

No aliases.

---

# 8. Target capability vocabulary

## Code

```text
architecture_discovery
domain_flow_trace
call_chain_trace
impact_analysis
graph_path_trace
inheritance_trace
semantic_code_search
exact_source_inspection
```

## Database

```text
database_catalog_discovery
database_schema_inspection
database_constraint_inspection
database_index_inspection
database_routine_inspection
database_internal_dependency_analysis
database_read_probe
database_code_consumer_analysis
```

Important distinction:

```text
database_internal_dependency_analysis
→ DB objects depending on DB objects
→ DB Access primary

database_code_consumer_analysis
→ source code consuming table/query/package/procedure
→ UA/current source primary
→ Codebase Memory conditional
```

Remove generic virtual tool labels such as:

```text
db_query
```

Provider mapping must reference actual tool contracts.

---

# 9. Typed conditional capabilities

Extend the skill contract schema:

```yaml
capabilities:
  required:
    - exact_source_inspection

  one_of:
    structured_navigation:
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
        - dynamic_wiring_risk
        - reviewer_counter_evidence
        - ua_unavailable

    impact_analysis:
      triggers:
        - blast_radius_required

    database_schema_inspection:
      triggers:
        - persistence_change

    database_internal_dependency_analysis:
      triggers:
        - database_dependency_risk

    database_read_probe:
      triggers:
        - runtime_data_verification_required
```

Validator requirements:

```text
unknown trigger → fail
conditional capability duplicated in required → fail
conditional provider call without trigger → fail
activated trigger without resolution/degradation → fail
required capability missing → fail
one_of group unsatisfied → fail
```

---

# 10. Interaction boundary

## Non-task lanes

These remain outside `/task`:

```text
/understand
/understand-domain
/understand-chat
Codebase Memory read-only query
DB Access read-only query
generated analysis report
```

## Task lanes

Use `/task` when the user intends to change:

```text
source
database migration
stored procedure/package
query behavior
transaction behavior
persistence contract
```

## Privileged database operations

DML/script/migration execution is not Database Explorer.

It requires a separate explicit operation:

```text
human approval
environment selection
write-capable DB source
preview
audit
rollback
```

That operation is outside this closure initiative.

---

# 11. Phase 0 — Freeze and inventory

## Freeze

Until closure:

```text
no new provider feature
no new DB engine
no new graph provider
no new memory provider integration
```

Allowed work:

```text
identity convergence
contract work
evidence/gate migration
provider execution
graph reliability
DB read-only safety
behavior qualification
```

## Required searches in Maika

Search all active occurrences of:

```text
understand-anything
codebase-memory-mcp
semantic_code_search
dependency_analysis
node_id
blast-radius
trace via cbm
KG unavailable
database-explorer
database_schema_inspection
database_dependency_analysis
db-access
DATABASE_CONTEXT
db_query
```

## Required searches in UA-MCP

Inventory:

```text
tool names
argument schemas
result shapes
freshness
health
path safety
traversal truncation
edge provenance
source hashes
dirty worktree behavior
```

## Required searches in DB Access

Inventory:

```text
package/server/client names
environment variables
service/container names
tool names
capability enforcement
tool registration
schema/owner behavior
data exposure
session/auth binding
health probe
result envelopes
tests
CI
```

## Deliverable

```text
docs/plans/provider-convergence-inventory.md
```

Required tables:

```text
identity matrix
capability matrix
tool contract matrix
gate dependency matrix
artifact producer/consumer matrix
risk-trigger matrix
user-journey matrix
legacy removal matrix
```

## Exit gate

No implementation until every current contradiction is assigned to a PR slice.

---

# 12. Phase 1 — Strict DB Access rename

Repository:

```text
VIethoangnguyenle/Db-Access
```

Perform one atomic rename.

## Required changes

```text
package name → db-access
MCP server name → db-access
binary → db-access
client config key → db-access
Docker/container → db-access
systemd service → db-access.service
environment variables → DB_ACCESS_*
logs/banner → DB Access
docs/examples/tests → db-access
```

Canonical environment variables:

```text
DB_ACCESS_CONFIG_PATH
DB_ACCESS_SOURCE
DB_ACCESS_API_KEY
```

No fallback to generic/old variables.

## Maika changes in the same release train

```text
plugin manifest provider ID → db-access
provider registry → db-access
provider mapping → db-access
resolved config examples → db-access
doctor/bootstrap output → db-access
DATABASE_CONTEXT provider ID → db-access
```

## Fail-fast migration

Add repository scans that fail on obsolete names in active content.

Historical release notes may be excluded by explicit path rules.

## Version convergence

The npm package version and MCP server version must come from one source.

## Exit

```text
one provider name
one server name
one package version
zero runtime aliases
```

---

# 13. Phase 2 — Machine contracts for both providers

## 13.1 Understand-Anything contract

UA-MCP exposes:

```text
get_capabilities
get_graph_metadata
structured node search
structured call trace
structured impact
structured path
structured hierarchy
structured domain flow
structured source extraction
```

Common result envelope:

```yaml
ok:
contract_version:
provider_id: understand-anything
server_version:
project:
operation:
request:
freshness:
health:
result:
warnings:
limits:
error:
```

## 13.2 DB Access contract

DB Access exposes:

```text
get_capabilities
list_databases
probe_database
list_schemas
list_objects
get_table
get_columns
get_constraints
get_indexes
list_routines
get_routine
get_dependencies
read_probe
```

Common result envelope:

```yaml
ok:
contract_version:
provider_id: db-access
server_version:
source:
database:
environment:
operation:
request:
result:
warnings:
limits:
error:
observed_at:
```

## Structured error

Never rely only on text such as:

```text
Error:
Failed:
```

Required:

```yaml
ok: false
error:
  code:
  message:
  remediation:
  retryable:
```

## Contract files

Each provider repository ships JSON schemas and a contract document.

Maika vendors the tested contract version.

## Exit

Maika does not hard-code provider tool lists independently of provider contracts.

---

# 14. Phase 3 — Understand-Anything graph health

Extend graph health beyond the current edgeless check.

Detect:

```text
duplicate node IDs
empty node IDs
dangling edges
unknown relation types
missing source files
source path escape
invalid layer references
broken domain references
missing domain graph
malformed domain graph
placeholder-summary ratio
zero-edge skeleton
truncated generation
graph schema mismatch
```

Health:

```text
HEALTHY
DEGRADED
INVALID
```

Capability applicability:

```yaml
architecture_discovery: available|degraded|unavailable
domain_flow_trace: available|degraded|unavailable
call_chain_trace: available|degraded|unavailable
impact_analysis: available|degraded|unavailable
```

Edge provenance:

```yaml
origin: direct|inherited|domain_cross_ref|inferred
confidence: high|medium|low
```

## Dirty worktree freshness

Freshness identity must include:

```yaml
graph_commit:
repository_head:
worktree:
  dirty:
  staged_files:
  unstaged_files:
  untracked_source_files:
```

Relevant dirty files lower graph authority.

---

# 15. Phase 4 — Reliable graph-generation lifecycle

This phase closes the historical `/understand` pain.

## Canonical operation workspace

```text
.maika/operations/understand/<operation-id>/
├── OPERATION.yaml
├── BATCH_PLAN.yaml
├── batches/
├── CHECKPOINT.yaml
├── QUALITY_REPORT.yaml
└── RESULT.yaml
```

## Required lifecycle

```text
plan graph build
→ divide into deterministic waves/batches
→ persist every batch before continuing
→ validate each batch
→ resume from checkpoint after interruption
→ deterministic merge
→ import recovery
→ graph health validation
→ freshness metadata
→ completion
```

## Quality gates

Reject:

```text
large graph with zero edges
placeholder-only summaries
missing required layers
high dangling-edge ratio
missing graph metadata
source paths outside repository
unvalidated partial output
```

## Host behavior

The native `/understand` implementation remains provider-owned.

Maika adds:

```text
operation contract
checkpoint requirements
post-run validation
resume instructions
```

Maika must not claim success because a worker wrote a graph-shaped JSON file.

## Cross-host

Run on:

```text
Claude Code
Codex
Antigravity
```

Record exact commands, batches, outputs and recovery behavior.

---

# 16. Phase 5 — DB Access capability separation

Replace current permissions:

```text
read
write
script
```

with:

```text
metadata
data_read
write
script
```

## Database Explorer source

Create a dedicated source:

```yaml
sources:
  maika_database_explorer:
    access:
      <database>:
        capabilities:
          - metadata
```

Optional data probe requires:

```text
data_read
```

Database Explorer must never receive:

```text
write
script
```

## Tool registration

Register tools according to source capability.

For a metadata-only source, do not expose:

```text
sql_write
sql_execute_script
mongo_write
arbitrary data_read
```

Do not merely expose and reject later.

## Data minimization

`metadata` tools must not return sample business rows.

Mongo schema inspection must not return raw sample documents by default.

Return:

```text
field names
inferred types
nullable/presence ratio
redacted shape
```

Raw sample requires explicit `data_read`.

---

# 17. Phase 6 — DB Access schema completeness

## Relational catalog

Add:

```text
list_schemas
list_objects
get_table
get_columns
get_constraints
get_indexes
```

## Routine catalog

Add:

```text
list_routines
get_routine
get_routine_arguments
```

Oracle must support:

```text
packages
procedures
functions
synonyms
views
triggers
sequences
```

PostgreSQL must support:

```text
schemas
functions
procedures
views
triggers
sequences
```

## Dependency catalog

Add:

```text
get_dependencies
```

Return:

```yaml
object:
depends_on:
depended_on_by:
dependency_type:
source_catalog:
```

## Explicit schema/owner

All relational catalog operations include:

```text
database
schema/owner
object
```

Do not lock Oracle to current user or PostgreSQL to `public`.

## Safe read probe

`read_probe` requires:

```text
explicit projection
row limit
timeout
no wildcard unless approved policy
masked sensitive fields
truncated flag
```

---

# 18. Phase 7 — DB Access health and session security

## `probe_database`

Return:

```yaml
ok:
provider_id: db-access
contract_version:
database:
type:
environment:
reachable:
current_user:
database_version:
capabilities:
catalog_visibility:
observed_at:
```

## Session binding

Bind:

```text
MCP session ID
→ authenticated source ID
→ API-key fingerprint
```

Reject reuse under another source.

## Permission reload

When a source is revoked or loses access:

```text
close its existing sessions
invalidate related confirmation state
```

## Confirmation tokens

Tokens remain provider safety for privileged operations, but they are not human approval.

Database Explorer never receives privileged tools.

---

# 19. Phase 8 — Canonical request/evidence artifacts

## 19.1 Code trace request

```text
changes/<id>/exploration/TRACE_REQUEST.yaml
```

Contains:

```yaml
questions:
required_capabilities:
optional_capabilities:
anchor_strategy:
trace_parameters:
freshness_requirement:
source_verification_requirement:
cbm_triggers:
```

## 19.2 Code trace evidence

```text
changes/<id>/exploration/TRACE_EVIDENCE.yaml
```

Contains:

```yaml
provider:
contract_version:
graph_commit:
repository_head:
worktree_state:
health:
freshness:
anchors:
traversals:
edges:
truncated:
support_calls:
source_verifications:
limitations:
confidence:
```

## 19.3 Database request

```text
changes/<id>/exploration/DATABASE_REQUEST.yaml
```

Contains:

```yaml
persistence_questions:
environment:
database:
schemas:
objects:
required_capabilities:
data_access:
  metadata_only: true
drift_expectation:
migration_refs:
source_anchors:
```

## 19.4 Database context

Upgrade:

```text
exploration/DATABASE_CONTEXT.yaml
```

Schema:

```yaml
version: 2
change_id:
read_only: true

provider:
  id: db-access
  contract_version:
  source_id:

probe:
  database:
  type:
  environment:
  schema_or_owner:
  current_user:
  capabilities:
  observed_at:
  status:

observations:
  - id:
    kind:
    qualified_name:
    tool:
    request_hash:
    result_hash:
    truncated:
    freshness:
    facts:

dependencies: []

code_consumers:
  - source:
    symbol:
    evidence_ref:

drift:
  - classification:
    observed_state:
    intended_state:
    source_state:
    resolution:

queries: []
degradation: []
limitations: []
confidence:
```

---

# 20. Phase 9 — Mechanical persistence trigger

## Change classification

Add structured signals:

```yaml
risk_signals:
  persistence:
  database_dependency:
  migration:
  routine_or_package:
  transaction_or_locking:
  data_read_required:
```

## Trigger sources

Detect from:

```text
user request
changed paths
entity/repository/native SQL
migration files
stored-procedure calls
transaction annotations
outbox/job/audit terms
QUERY_PLAN questions
```

## Router behavior

For standard/architectural:

```text
persistence = false
→ DB artifacts not required

persistence = true
→ dispatch database-explorer
→ require DATABASE_REQUEST
→ require DATABASE_CONTEXT
→ require database-context gate
```

For trivial/small:

```text
persistence signal
→ escalate to standard
```

Exception:

```text
pure comment/format-only persistence file change
```

must be mechanically justified.

## Completion gate

Explore completion gates become conditional.

A persistence task cannot pass exploration without:

```text
valid DATABASE_CONTEXT
or
valid provider degradation with safe fallback
```

---

# 21. Phase 10 — Provider-neutral gates

## Remove active provider-specific checks

Remove requirements equivalent to:

```text
must have CBM node
must have blast-radius string
trace via CBM
UA evidence regex
generic db_query marker
read_only + arbitrary objects list
```

## New code trace gates

```text
validate_trace_request
validate_trace_evidence
validate_capability_satisfaction
validate_conditional_support
validate_source_verification
validate_graph_freshness
validate_trace_completeness
```

## New DB gates

```text
validate_database_request
validate_database_context_v2
validate_db_probe
validate_db_capability_scope
validate_metadata_only_boundary
validate_db_freshness
validate_drift_resolution
validate_sensitive_data_policy
```

## Required negative tests

```text
complete UA trace without CBM → pass
CBM call without trigger → fail
relevant stale graph claimed current → fail
truncated trace claimed complete → fail
material exact fact without source hash → fail

persistence task without DB context → fail
metadata-only source exposes write tool → fail
DB context lacks environment → fail
DB context contains raw sensitive sample without data_read → fail
live/source drift has no classification → fail
```

---

# 22. Phase 11 — Runtime provider execution

## Preferred execution

Maika orchestrator performs provider probes and deterministic retrieval before authoring workers.

```text
compile request
→ execute provider adapter
→ validate structured response
→ write evidence artifact
→ dispatch worker with pinned evidence
```

## Provider adapters

```text
cli/providers/understand_anything.py
cli/providers/codebase_memory.py
cli/providers/db_access.py
cli/providers/current_source.py
```

## Execution strategies

### UA

Prefer:

```text
structured local CLI over UA-MCP core
```

or a deterministic MCP client.

### DB Access

Use the configured MCP endpoint through a minimal read-only MCP client.

Do not bypass DB Access authentication by reading DB credentials directly from Maika.

### Codebase Memory

Use only when conditional trigger is activated.

## Adapter requirements

```text
canonical provider ID
contract compatibility
timeouts
structured error
output-size limit
redacted logs
request/result hashes
no shell-string execution
```

## Fallback

If direct provider execution is not available on a host:

```text
delegated provider call
→ same result schema
→ raw response hash
→ lower assurance
→ visible in evidence
```

No silent fallback.

---

# 23. Phase 12 — Pinned worker context

Every relevant worker receives:

```text
SKILL_FILE
SKILL_SHA256
PROVIDER_REGISTRY_FILE
PROVIDER_REGISTRY_SHA256
CAPABILITY_POLICY_FILE
CAPABILITY_POLICY_SHA256
TRACE_REQUEST_FILE
TRACE_REQUEST_SHA256
TRACE_EVIDENCE_FILE
TRACE_EVIDENCE_SHA256
DATABASE_REQUEST_FILE
DATABASE_REQUEST_SHA256
DATABASE_CONTEXT_FILE
DATABASE_CONTEXT_SHA256
```

Workers synthesize decisions from evidence.

They do not invent provider health or rewrite raw observations.

---

# 24. Phase 13 — Refresh and re-probe lifecycle

## UA refresh request

Canonical path:

```text
changes/<id>/generated/requests/EXTERNAL_WORKFLOW_REQUEST.<role>.yaml
```

Lifecycle:

```text
requested
→ task BLOCKED
→ user/parent runs /understand
→ Maika re-probes graph
→ quality/freshness validated
→ fulfilled
→ original role resumed
```

Unchanged graph cannot be acknowledged as refreshed.

## DB re-probe request

When DB evidence expires or environment changes:

```text
DB_REPROBE_REQUEST.yaml
```

Lifecycle:

```text
requested
→ probe_database
→ required catalog probes
→ new DATABASE_CONTEXT revision
→ context hash updated
→ resume
```

Do not reuse DB evidence across environments.

---

# 25. Phase 14 — Database Explorer redesign

## Typed capabilities

```yaml
capabilities:
  required:
    - exact_source_inspection

  conditional:
    database_catalog_discovery:
      triggers:
        - persistence_change

    database_schema_inspection:
      triggers:
        - persistence_change

    database_constraint_inspection:
      triggers:
        - relational_contract_change

    database_index_inspection:
      triggers:
        - performance_or_query_change

    database_routine_inspection:
      triggers:
        - routine_or_package_change

    database_internal_dependency_analysis:
      triggers:
        - database_dependency_risk

    database_read_probe:
      triggers:
        - runtime_data_verification_required

    database_code_consumer_analysis:
      triggers:
        - persistence_change
```

## Procedure

```text
read DATABASE_REQUEST
→ validate DB provider health
→ inspect live catalog
→ inspect source/migration anchors
→ trace code consumers through UA/current source
→ activate CBM only on semantic/gap trigger
→ classify drift
→ emit DATABASE_CONTEXT
```

## Stop conditions

```text
destructive decision
wrong environment
missing credentials with no safe fallback
provider source has write/script capabilities
unresolved schema owner
sensitive data request without authorization
```

---

# 26. Phase 15 — Codebase Memory role enforcement

## Permitted triggers

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

## Required support record

```yaml
provider_id: codebase-memory-mcp
capability: semantic_code_search
trigger:
reason:
query:
result_refs:
contribution:
```

## Forbidden behavior

```text
call CBM after every UA trace
repeat the same path without a counter-question
use CBM result as exact source authority
call CBM without recording a trigger
block a complete fresh UA path merely because CBM is unavailable
```

## Review pattern

```text
implementer/grounding:
UA primary path

reviewer:
UA revalidation
+ CBM counter-evidence only where risk warrants
```

---

# 27. Phase 16 — System-model validator

Add:

```bash
maika content validate-system-model
```

Build an internal graph:

```text
Interaction
→ Risk signal
→ Skill
→ Capability
→ Provider
→ Tool contract
→ Request artifact
→ Evidence artifact
→ Gate
→ Consumer
→ Ownership
```

## Checks

### Identity

```text
provider exists
single canonical ID
setup key matches
artifact IDs match
```

### Capabilities

```text
skill capability exists
capability has provider
conditional trigger exists
provider tool exists in contract
```

### Artifacts

```text
producer exists
validator exists
authority exists
consumer exists
ownership exists
```

### Gates

```text
gate evidence has producer
gate does not require obsolete provider-specific evidence
conditional gates align with risk signals
```

### Naming

```text
db-access is the only active DB provider/server/package name
```

---

# 28. Phase 17 — Mutation tests

CI deliberately introduces and must catch:

1. Change Maika DB provider ID.
2. Change DB Access MCP server name.
3. Reintroduce an obsolete DB name.
4. Make semantic search required.
5. Remove a CBM trigger.
6. Remove UA contract tool.
7. Claim graph fresh with relevant dirty file.
8. Accept a zero-edge skeleton.
9. Remove source verification.
10. Allow persistence task without DB context.
11. Give Database Explorer write capability.
12. Expose write tool to metadata-only source.
13. Remove DB environment from context.
14. Return raw Mongo sample in metadata operation.
15. Mark DB refresh complete without a new probe.
16. Use live DB state as target migration without classification.
17. Reuse an HTTP session under another source.
18. Use an unknown schema/owner implicitly.
19. Claim complete trace when truncated.
20. Invoke CBM without support reason.

Every mutation must fail.

---

# 29. Phase 18 — Deterministic behavior fixtures

## Code fixtures

### C1 Fresh UA complete trace

```text
UA primary
no CBM
source verified
pass
```

### C2 Ambiguous request

```text
CBM finds anchor
UA traces
source verifies
```

### C3 Graph gap

```text
UA partial
CBM trigger=graph_gap
source resolves
```

### C4 Hidden consumer

```text
UA flow
CBM counter-search finds alternate consumer
```

### C5 Relevant dirty source

```text
graph authority reduced
current source wins
```

### C6 Invalid graph

```text
UA unavailable
conditional fallback
no fabricated path
```

### C7 Truncated trace

```text
cannot claim completeness
```

### C8 Refresh resume

```text
BLOCKED
/understand
re-probe
resume
```

## DB fixtures

### D1 Entity/table match

```text
metadata-only probe
no drift
```

### D2 Column type drift

```text
drift classified
planning impact generated
```

### D3 Migration not deployed

```text
expected_pre_deployment_drift
```

### D4 Package/procedure call

```text
DB routine inspection
UA code consumer trace
```

### D5 Cross-schema Oracle

```text
explicit owner
ALL_* visibility
```

### D6 PostgreSQL non-public schema

```text
explicit schema
```

### D7 Metadata-only Mongo

```text
no raw sample document
```

### D8 Provider unavailable

```text
structured degradation
source fallback
confidence reduced
```

### D9 Wrong environment

```text
block
```

### D10 Write capability leak

```text
block before task worker
```

---

# 30. Phase 19 — Real-host qualification

Hosts:

```text
Claude Code
Codex
Antigravity/Agy
```

## Journeys

### H1

Trace a known business flow.

Expected:

```text
UA primary
CBM not called unnecessarily
source verification
```

### H2

Trace a deliberately ambiguous flow.

Expected:

```text
CBM anchor support
UA structured trace
```

### H3

Make relevant graph source dirty.

Expected:

```text
freshness degraded
no false fresh claim
```

### H4

Run `/understand`, interrupt, resume.

Expected:

```text
checkpoint recovery
quality gate
```

### H5

Start a persistence-sensitive task.

Expected:

```text
database-explorer invoked
DB context mandatory
```

### H6

Inspect Oracle routine and code caller.

Expected:

```text
DB Access routine evidence
UA/current-source consumer evidence
```

### H7

Use a metadata-only DB source.

Expected:

```text
no write/script/data-read tool exposure
```

### H8

Attempt to reuse DB session under another source.

Expected:

```text
rejected
```

## Qualification thresholds

```text
UA primary selection ≥ 95%
unnecessary CBM calls ≤ 5%
material source verification = 100%
persistence trigger accuracy ≥ 95%
DB context completeness = 100%
Database Explorer write exposure = 0
cross-host journey consistency ≥ 95%
refresh/re-probe success = 100%
```

---

# 31. Cross-repository PR sequence

## Understand-Anything-MCP

### U1 — Structured contract

```text
get_capabilities
structured result schemas
contract version
```

### U2 — Graph health and dirty freshness

```text
health validation
worktree freshness
edge provenance
```

### U3 — Structured trace API

```text
node search
call trace
impact
path
hierarchy
domain flow
source hashes
```

### U4 — Graph-build operation support

```text
batch/checkpoint metadata
quality report contract
resume proof
```

## DB Access

### D1 — Strict canonical rename

```text
db-access everywhere
single version source
zero aliases
```

### D2 — Contract and health

```text
get_capabilities
probe_database
structured envelope
```

### D3 — Capability separation

```text
metadata
data_read
write
script
tool registration by capability
```

### D4 — Catalog completeness

```text
schemas/owners
tables
constraints
indexes
routines
dependencies
```

### D5 — Security hardening

```text
session-source binding
revocation
data minimization
read-probe policy
```

## Maika

### M1 — Provider registry and names

```text
canonical provider registry
db-access naming scan
```

### M2 — Contract pinning

```text
vendor/test provider contracts
```

### M3 — Conditional capability schema

```text
required/one_of/conditional
```

### M4 — Trace artifacts and gates

```text
TRACE_REQUEST
TRACE_EVIDENCE
provider-neutral gates
```

### M5 — Persistence trigger and DB artifacts

```text
DATABASE_REQUEST
DATABASE_CONTEXT v2
conditional router gate
```

### M6 — Provider execution adapters

```text
UA
CBM
DB Access
current source
```

### M7 — Worker context pinning

```text
hash-bound evidence
```

### M8 — Refresh/re-probe lifecycle

```text
UA refresh
DB re-probe
BLOCKED/resume
```

### M9 — System-model validator and mutation suite

```text
cross-surface convergence
```

### M10 — Behavior qualification and legacy removal

```text
fixtures
real-host report
remove old gates/contracts
closure report
```

---

# 32. Mandatory slice gate

For every PR slice:

```text
inspect exact source
→ write narrow implementation note
→ implement one slice
→ targeted tests
→ provider contract validation
→ artifact audit --check
→ full repository CI
→ relevant behavior fixtures
→ git diff --check
→ clean working tree verification
→ stop and report
```

Do not continue to the next slice while CI is red.

---

# 33. CI requirements

## UA-MCP

```text
unit tests
contract schema
structured API
path safety
graph health
dirty freshness
package build
CLI/MCP parity where applicable
```

## DB Access

```text
TypeScript build
unit tests
contract schema
capability exposure tests
metadata/data separation
session binding
Oracle/PostgreSQL/Mongo fixtures
package/bin/server identity
obsolete-name scan
```

## Maika

```text
provider registry validation
provider contract validation
skill contract validation
conditional trigger validation
trace evidence gates
DB context gates
system-model validation
mutation tests
Ubuntu
Windows
Linux install E2E
PowerShell install E2E
```

## Release qualification

No network dependency in normal CI.

Release/nightly may run pinned provider packages and real-host smoke.

---

# 34. Rollback

## UA

New structured APIs are additive until closure.

Rollback:

```text
switch trace_mode to delegated
retain old text tools
pin previous contract
```

## DB Access

Strict rename is intentionally breaking.

Rollback is deployment rollback to the previous release, not runtime aliasing.

## Maika feature flags

During shadow rollout:

```yaml
providers:
  understand-anything:
    mode: structured_shadow|structured_primary

  db-access:
    mode: context_shadow|context_required
```

Shadow mode records differences but does not make production decisions.

After qualification:

```text
structured_primary
context_required
```

Remove shadow paths before closure.

---

# 35. Acceptance criteria

## Naming

1. `db-access` is the only active DB provider name.
2. Package, server, binary and client key are `db-access`.
3. Maika manifest and runtime use `db-access`.
4. DB evidence uses `provider_id: db-access`.
5. No runtime alias exists.
6. CI rejects obsolete names.

## UA

7. UA contract is machine-readable.
8. Maika pins a compatible contract.
9. Structured trace results validate.
10. Graph health covers invalid/degenerate graphs.
11. Dirty worktree affects freshness.
12. Graph build supports checkpoint/resume.
13. Quality gate rejects fabricated skeletons.
14. Complete UA trace passes without CBM.
15. Exact facts are source-verified.

## Codebase Memory

16. Semantic search is conditional.
17. Every CBM call has a trigger.
18. Every CBM call has a reason.
19. CBM is primary for semantic anchor discovery.
20. CBM supports hidden-consumer/counter-evidence.
21. CBM unavailability does not block a complete UA trace.

## DB Access

22. DB Access exports a machine contract.
23. `probe_database` exists.
24. Metadata and data-read permissions are separate.
25. Metadata-only source has no write/script tools.
26. Mongo metadata does not expose raw samples.
27. Oracle owner is explicit.
28. PostgreSQL schema is explicit.
29. Index/routine/dependency tools exist.
30. Session is bound to source.
31. Revocation invalidates sessions.
32. Package/server versions agree.

## Database Explorer

33. Persistence signal is typed.
34. Persistence task invokes Database Explorer.
35. Persistence task requires DATABASE_CONTEXT.
36. Trivial/small persistence task escalates.
37. DB context records environment and source.
38. DB observations have request/result hashes.
39. DB drift is classified.
40. Observed state and target state are separate.
41. Read-only boundary is enforced.
42. Missing provider degrades explicitly.

## Gates/runtime

43. Gates are provider-neutral.
44. No active gate requires CBM by name.
45. No active gate accepts arbitrary DB object lists.
46. Runtime performs real provider probes.
47. Worker cannot invent provider health.
48. Worker receives pinned evidence hashes.
49. Refresh/re-probe lifecycle is complete.
50. Resume revalidates evidence.

## Qualification

51. All deterministic fixtures pass.
52. All mutation tests pass.
53. Claude journeys pass.
54. Codex journeys pass.
55. Antigravity journeys pass.
56. UA primary threshold met.
57. Unnecessary CBM threshold met.
58. DB write exposure is zero.
59. Full CI is green.
60. No Critical/High findings remain.

---

# 36. Definition of Done

This program is complete only when:

```text
one provider model owns identity
UA traces are structured and health-aware
graph generation can resume and prove quality
CBM is genuinely conditional
current source mechanically verifies exact facts
db-access is one strict canonical name
DB Access enforces metadata-only exploration
persistence tasks mechanically require Database Explorer
DATABASE_CONTEXT is real observed evidence
gates validate capability/evidence rather than provider prose
cross-surface mutation tests prevent regression
real-host qualification passes
old provider-specific gates and names are removed
```

Not sufficient:

```text
rules updated
skill prose updated
a Markdown report looks correct
provider is configured
CI only checks file presence
```

---

# 37. Codex kickoff prompt

```text
Implement the Maika Provider Convergence & Closure Plan across:

1. VIethoangnguyenle/Maika, branch master-v2
2. VIethoangnguyenle/Understand-Anything-MCP, branch main
3. VIethoangnguyenle/Db-Access, branch main

Start with Phase 0 only. Produce:
docs/plans/provider-convergence-inventory.md

Do not code before completing the identity, capability, tool-contract,
gate-dependency, artifact and user-journey matrices.

Core decisions:
- Understand-Anything-MCP is primary for structured graph tracing.
- Codebase Memory MCP is primary for semantic discovery and conditional
  support/counter-evidence.
- Current source is authoritative for exact code facts.
- DB Access is authoritative for observed live DB state.
- database-explorer reconciles source, graph, live DB and migration intent.
- The only DB provider/server/package/client name is db-access.
- There are no aliases or compatibility fallbacks for old DB names.
- Skills use capabilities; gates validate provider-neutral evidence.
- Persistence-sensitive tasks mechanically require DATABASE_CONTEXT.
- Database Explorer must be metadata-only/read-only at provider level.
- Every PR slice must finish with targeted tests, full CI, behavior fixtures,
  git diff --check and a clean working tree.

Execute in the PR order U1-U4, D1-D5, M1-M10.
Do not combine the initiative into one large PR.
```

---

# 38. Closure statement

After this plan, Maika should no longer “hope” that an agent:

```text
uses UA first
calls CBM only when useful
checks the live DB
does not write to DB
records freshness honestly
```

The system must prove those behaviors through:

```text
canonical identity
typed capability triggers
machine provider contracts
structured evidence
provider execution
read-only boundaries
cross-surface validators
mutation tests
real-host qualification
```
