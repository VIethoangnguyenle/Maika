# Maika Framework Ecosystem Upgrade Plan — Maika-Owned Work

Date: 2026-07-15
Branch: `master-v2`
Source assessment: `upgrade/MAIKA_FRAMEWORK_ECOSYSTEM_BRAINSTORM.md`

## 1. Objective

Close the ecosystem correctness and governance gaps that Maika can own without
modifying external MCP repositories.

The end state is:

- source writes fail closed when Maika cannot prove their target scope;
- workspace locks cannot be released by a stale owner;
- provider capabilities resolve to real runtime tools and schemas;
- provider evidence carries normalized, versioned provenance;
- authoring, review, lightweight verification, and archive flows share one
  mechanically enforced execution contract;
- graph and memory providers remain supporting evidence, never implicit authority
  for current source or canonical project knowledge.

## 2. Scope and ownership

### In scope

- Findings F, I, J, K, L, Q, R, S.
- Maika-side defenses and compatibility adapters for P, T, U, V, W, X, Z, AA.
- Contract fixtures derived from pinned upstream revisions.
- Provider registry, capability probes, evidence normalization, gates, and tests.

### Out of scope

- Patching Db-Access, Understand-Anything, Codebase Memory, or AgentMemory source.
- Dashboard work.
- Replacing Maika runtime with event sourcing.
- Treating prompt instructions or setup prose as enforcement.
- Building a mandatory container sandbox in the first wave.
- Enabling DB write/script lanes by default.
- Using AgentMemory agent scope as an authorization boundary.

External changes and cross-repository acceptance tests are specified in
`upgrade/EXTERNAL_PROVIDER_CONTRACT_HARDENING_PLAN.md`.

## 3. Non-negotiable invariants

1. `current-source` remains authoritative for exact current code and behavior.
2. Unknown mutating commands never receive an unconditional allow decision.
3. Gitignored paths are not exempt from write-scope enforcement.
4. A workspace lock may be released only by its current owner token.
5. `semantic_query` is an argument of `search_graph`, not an MCP tool.
6. Provider readiness requires a probe of the capability actually being routed.
7. Provider responses are normalized only from fields proven by contract fixtures;
   missing provenance stays missing and produces explicit degradation.
8. AgentMemory fallback must never silently change the logical memory store used by
   one Maika execution.
9. AgentMemory claims are candidates or historical context, not canonical project
   knowledge.
10. Every registry field introduced in this plan has a mechanical consumer and a
    regression test in the same wave.

## 4. Delivery order

```text
M0 Baseline and contract fixture harness
  -> M1 Write boundary and workspace lock safety
  -> M2 Provider tool contract correctness
  -> M3 Workflow execution and lightweight archive correctness
  -> M4 Evidence authority and AgentMemory governance
  -> M5 Cross-provider evidence hardening and pilot gate
```

Each wave is independently reviewable and must pass the full repository CI before
the next wave starts.

---

## M0 — Baseline and provider contract fixture harness

### Goal

Create one fixture-driven contract test layer before changing runtime behavior.

### Add

```text
cli/tests/fixtures/provider_contracts/
  understand-anything/
    graph-metadata-v1.json
    graph-metadata-missing-provenance.json
  codebase-memory/
    tools-list-current.json
    search-graph-semantic-schema.json
    index-status-current.json
  agent-memory/
    tools-list-proxy.json
    tools-list-local-fallback.json
    proxy-health-failure.json
  db-access/
    write-preview.json
    write-error.json
cli/tests/test_provider_contract_fixtures.py
```

Each fixture must include a sidecar provenance record:

```yaml
provider:
repository:
revision:
captured_at:
tool:
contract_version:
content_sha256:
```

### Update

- `cli/mcp/integration/understand_anything.py`
- `cli/mcp/integration/codebase_memory.py`
- Provider integration tests under `cli/tests/`.

M0 may add fixture loading and validation helpers but must not change routing or
gate behavior.

### Tests

- Reject a fixture without provider, revision, tool, or content hash.
- Reject duplicate fixture IDs with different content.
- Prove JSON fixture content hashes are deterministic.
- Prove all external fixture revisions are explicit; never use `main` or `latest`.

### Exit gate

```bash
python3 -m pytest cli/tests/test_provider_contract_fixtures.py -q
python3 scripts/run_ci.py
git diff --check
```

---

## M1 — Write boundary and workspace lock safety

### Findings

- I — write-gate shell bypass.
- L — workspace lock lease/release race.

### Primary files

- `.maika/hooks/write-gate/write_gate.py`
- `.maika/hooks/write-gate/tests/`
- `.maika/tools/microloop-orchestrator/runtime_hardening.py`
- `.maika/tools/microloop-orchestrator/tests/`
- `cli/commands/task.py` only where it acquires the shared workspace lock.

### M1.1 Write-gate contract

Classify commands into explicit outcomes:

```yaml
classification: read_only | known_write | unresolved_possible_write
targets: []
reason:
```

Required behavior:

- known writes are checked against the active execution scope;
- unresolved possible writes fail closed while a Maika execution is active;
- commands proven read-only may pass without a target list;
- gitignored paths remain subject to scope checks;
- dangerous repository-wide commands such as `git reset --hard` are never inferred
  safe from an empty parsed target list.

Add target extraction or unresolved classification for at least:

```text
python -c / python script.py
node -e / node script.js
touch
truncate
tar extraction
unzip
git reset/clean/restore
mvn/gradle formatter tasks
```

Do not attempt perfect shell interpretation. Ambiguity must produce
`unresolved_possible_write`, not `read_only`.

### M1.2 Post-command scope validation

Introduce a reusable changed-path validator for Maika-managed execution paths:

```python
def validate_changed_paths(
    before: WorkspaceSnapshot,
    after: WorkspaceSnapshot,
    allowed_paths: set[str],
) -> ScopeValidation: ...
```

The first implementation may report and fail the execution without automatic
rollback. Container isolation and rollback remain a later hardening option.

### M1.3 Lock ownership

Extend the lock record with:

```yaml
owner_token:
pid:
host:
generation:
acquired_at:
heartbeat_at:
lease_expires_at:
```

Required semantics:

- acquire creates a cryptographically random owner token;
- release reads the current file and deletes it only when owner token and
  generation match;
- a same-host live PID is not taken over solely because wall-clock lease elapsed;
- long-running operations refresh the heartbeat before lease expiry;
- takeover increments generation;
- malformed lock records fail with a diagnosable error rather than being silently
  treated as free.

### Test-first cases

- Every payload listed in Finding I is rejected or resolved to an allowed target.
- Writing `.env` outside scope is rejected even when `.env` is gitignored.
- Owner A expires, owner B takes over, A release cannot delete B's lock.
- A live same-host PID prevents takeover.
- Dead PID plus expired lease permits takeover.
- Heartbeat keeps a long task from appearing orphaned.
- Malformed lock and interrupted atomic replacement have deterministic outcomes.

### Exit gate

```bash
python3 -m pytest .maika/hooks/write-gate/tests -q
python3 -m pytest .maika/tools/microloop-orchestrator/tests -q
python3 scripts/run_ci.py
git diff --check
```

---

## M2 — Provider tool contract correctness

### Findings

- F — Understand-Anything metadata normalization mismatch.
- Q — Codebase Memory lacks Maika tool/mutability lanes.
- R — `semantic_query` is routed as a non-existent tool.
- Defensive subset of P, T, U, V, AA.

### Primary files

- `.maika/config/provider-registry.yaml`
- `.maika/profiles/capability-registry.yaml`
- `.maika/profiles/provider-capabilities.yaml`
- `cli/mcp/integration/understand_anything.py`
- `cli/mcp/integration/codebase_memory.py`
- `cli/agent_content/provider_capabilities.py`
- `cli/platforms/claude_code.py`
- `cli/platforms/codex.py`
- `cli/platforms/antigravity.py`
- `cli/platforms/generic.py`
- `cli/tools/templatize.py`
- `cli/mcp/doctor.py`
- corresponding tests in `cli/tests/`.

### M2.1 Normalize Understand-Anything metadata

Accept the proven v1 producer shape:

```json
{
  "contract_version": 1,
  "project": "...",
  "graph": {"graph_commit": "..."},
  "repository": {"head": "..."},
  "freshness": {"status": "..."},
  "health": {"status": "..."}
}
```

Normalize to a Maika-owned observation without inventing values:

```yaml
provider_id: understand-anything
tool: get_graph_metadata
provider_contract_version: 1
project:
graph_commit:
repository_head:
freshness:
health:
response_hash:
```

Unknown contract versions and missing critical provenance must yield explicit
degradation.

### M2.2 Correct Codebase Memory semantic routing

Replace every abstract semantic-search mapping that currently resolves to
`semantic_query` with:

```yaml
tool: search_graph
argument_contract:
  semantic_query:
    type: array
    min_items: 1
```

Do not add `semantic_query` to a tool list or lane.

### M2.3 Add Codebase Memory lanes

```yaml
lanes:
  discovery:
    tools:
      - list_projects
      - index_status
      - get_graph_schema
      - search_graph
      - trace_path
      - detect_changes
      - query_graph
      - get_code_snippet
      - get_architecture
      - search_code
    mutability: read_only

  explicit_index:
    tools: [index_repository]
    activation: explicit_index_request
    mutability: local_index_write

  explicit_graph_mutation:
    tools: [manage_adr, ingest_traces]
    activation: explicit_user_request
    mutability: graph_write

  destructive_admin:
    tools: [delete_project]
    activation: explicit_user_request
    confirmation_required: true
    mutability: destructive
```

Runtime `tools/list` remains authoritative for availability. The registry is the
allowlist and mutability policy, not evidence that the installed binary implements
the tool.

### M2.4 Pin AgentMemory integration contract

Add only the minimum required surface:

```yaml
integration_mode: mcp_proxy_only
fallback_policy: reject_store_change
required_tools:
  - memory_smart_search
  - memory_recall
  - memory_sessions
optional_tools: []
hooks:
  auto_capture: false
  session_injection: false
```

Readiness must bind at least:

```yaml
resolved_url:
runtime_version:
tool_surface_hash:
mode: proxy | local
```

If upstream cannot expose server/store identity yet, report identity as
`unverified` and keep the provider degraded for cross-session canonical use.

### Tests

- Real UA v1 fixture normalizes nested graph/repository fields.
- Missing UA provenance does not get filled from worker prose.
- Semantic search renders a `search_graph` call with array `semantic_query`.
- No platform contains a callable MCP tool named `semantic_query`.
- Exploration cannot route `index_repository`, `manage_adr`, `ingest_traces`, or
  `delete_project`.
- AgentMemory local seven-tool fallback does not satisfy proxy-only readiness.
- A tool-list hash change invalidates the prior capability probe.

### Exit gate

```bash
python3 -m pytest \
  cli/tests/test_provider_capabilities.py \
  cli/tests/test_provider_invocations.py \
  cli/tests/test_platforms.py -q
python3 scripts/run_ci.py
git diff --check
```

---

## M3 — Unified execution and lightweight archive correctness

### Findings

- J — dispatch role/write-gate mismatch.
- K — lightweight archive cannot satisfy required artifacts.

### Primary files

- `.maika/tools/microloop-orchestrator/vnext_dispatch.py`
- `.maika/tools/microloop-orchestrator/orchestrator.py`
- `.maika/hooks/write-gate/write_gate.py`
- `cli/commands/task.py`
- workflow schemas and tests already consumed by those modules.

### M3.1 Canonical execution lease

Persist one execution record for every worker that may write:

```yaml
version: 1
execution_id:
change_id:
task_id:
role:
workflow_state:
status: active | completed | failed | expired
allowed_outputs: []
allowed_source_scope: []
owner_token:
lease_expires_at:
prompt_hash:
```

Roles must cover at least grounding, specification, planning, implementation,
task-review, final-review, and reconciliation. Write-gate authorization resolves
the active execution record rather than assuming exactly one task is
`in_progress`.

### M3.2 Lightweight archive artifacts

Do not weaken archive validation. During lightweight verification, materialize
class-aware zero-impact artifacts when there are no observations requiring a
knowledge update:

```yaml
stale_entries: []
superseded_decisions: []
new_candidates: []
graph_refresh_required: false
memory_updates: []
```

The artifact must record that it was generated by lightweight verification and
must not overwrite a non-empty worker-produced artifact.

### E2E cases

- Grounding worker writes only `GROUNDING.yaml` in EXPLORING.
- Spec worker writes only specification outputs in the specification state.
- Task reviewer writes its review while task status is `reviewing`.
- Final reviewer writes after all implementation tasks are done.
- Expired or completed execution cannot authorize a later write.
- `trivial` and `small` flows complete start -> apply -> verify -> archive.
- A lightweight flow with real knowledge impact cannot silently emit zero-impact.

### Exit gate

```bash
python3 -m pytest cli/tests -q
python3 -m pytest .maika/tools/microloop-orchestrator/tests -q
python3 scripts/run_ci.py
git diff --check
```

---

## M4 — Evidence authority and AgentMemory governance

### Findings

- S — conflicting graph evidence has no authority rule.
- X — memory claims must not become current-code/business authority.
- Z — dual canonical knowledge lifecycle.
- Defensive subset of W and Y.

### Primary files

- `.maika/config/provider-registry.yaml`
- `.maika/profiles/capability-registry.yaml`
- `cli/knowledge_control.py`
- `cli/agent_content/provider_capabilities.py`
- trace-evidence schema, gates, and tests that consume provider observations.

### Authority policy

```yaml
authority:
  exact_current_source:
    authoritative: current-source

  structured_graph_trace:
    preferred: understand-anything
    corroborating: [codebase-memory-mcp, current-source]
    conflict_action: verify_current_source

  semantic_index_structure:
    preferred: codebase-memory-mcp
    corroborating: understand-anything
    conflict_action: verify_current_source

  domain_semantics:
    preferred: understand-anything
    corroborating: current-source
    conflict_action: mark_inferred_or_conflicting

  historical_context:
    preferred: agent-memory
    conflict_action: treat_as_candidate

  canonical_project_knowledge:
    authoritative: maika-knowledge-kernel
```

### AgentMemory lanes

Pin only tools actually returned by the selected runtime fixture. Classify them as:

```text
recall
explicit_memory_write
maintenance
destructive
coordination
team_or_mesh
```

Default activation permits recall only. Writes happen only after Maika validation
and an explicit persistence decision. Destructive, coordination, and team/mesh
lanes remain disabled unless independently enabled.

### Required enforcement

- A graph conflict cannot be merged into one `verified` claim.
- Exact-code claims require current-source revision evidence.
- AgentMemory recall enters context as `historical` or `candidate`.
- Canonical knowledge updates go through `cli/knowledge_control.py`.
- Auto-capture presence is reported by doctor as a governance conflict; Maika does
  not silently install, remove, or rewrite user-global hooks.
- `agentId` is treated as a retrieval filter, not an authorization proof.

### Tests

- UA and CBM disagree on a call edge -> current-source verification required.
- Observations from different source revisions cannot form a complete evidence
  package without an explicit refresh boundary.
- A memory claiming an obsolete business rule cannot pass the canonical knowledge
  gate by itself.
- Memory save is not called before validation/archive completion.
- AgentMemory auto-capture hooks produce a doctor warning and degraded governance
  status.

### Exit gate

```bash
python3 -m pytest cli/tests .maika/tools/gate-check/tests -q
python3 scripts/run_ci.py
git diff --check
```

---

## M5 — Cross-provider evidence hardening and pilot gate

### Findings

- P — producer/consumer schema drift.
- T — Codebase Memory observations are not bound to immutable index generation.
- AA — AgentMemory remote identity remains ambiguous.

### Evidence envelope

All external provider observations must use one envelope:

```yaml
contract_version: 1
provider_id:
provider_runtime_version:
tool:
tool_contract_hash:
request_hash:
response_hash:
project:
source_revision:
working_tree_state:
provider_snapshot:
observed_at:
status: success | error | degraded
degradation_reasons: []
```

Provider-specific fields remain nested under `provider_snapshot`; do not invent a
fake universal generation value.

### Codebase Memory interim consistency rule

Until upstream exposes an immutable index generation:

1. capture `index_status` before an evidence session;
2. serialize CBM evidence calls for that session;
3. capture `index_status` after the session;
4. reject completeness if HEAD, working-tree state, node/edge counts, tool-surface
   hash, or available index timestamp changed;
5. record `index_generation: unverified`.

This is a detection mechanism, not a claim of snapshot isolation.

### Pilot gate

A Java/Spring Boot banking pilot may use:

- current-source inspection;
- UA and CBM read-only discovery;
- AgentMemory recall in candidate-only mode;
- Db-Access schema/read tools through a dedicated read-only DB principal.

It must not enable:

- source writes outside a scoped Maika execution;
- CBM mutation or deletion during exploration;
- AgentMemory automatic capture or canonical persistence;
- DB write or script capabilities.

### Exit gate

- Full CI passes on Linux.
- Platform-specific hook and filesystem tests pass on Windows CI.
- All provider fixture revisions and hashes are pinned.
- Pilot readiness report lists every degraded or unverified provider property.
- No production-readiness label is emitted while a mandatory property is
  `unverified`.

---

## 5. Change slicing

Keep reviews small and ordered:

1. `test: add provider contract fixture harness`
2. `fix: fail closed on unresolved scoped writes`
3. `fix: fence workspace lock ownership and heartbeat`
4. `fix: normalize UA metadata and CBM semantic routing`
5. `feat: enforce provider mutability lanes and runtime tool probes`
6. `feat: authorize writes from canonical execution leases`
7. `fix: make lightweight verification archive-complete`
8. `feat: enforce provider evidence authority and memory governance`
9. `feat: bind evidence sessions to provider snapshot checks`

Do not combine external provider patches with these commits.

## 6. Definition of done

- Findings F, I, J, K, L, Q, R, and S have regression tests that fail on the
  current baseline and pass after their owning wave.
- P, T, U, V, W, X, Z, and AA have explicit Maika-side degradation behavior.
- Provider tool names and schemas come from pinned fixtures plus runtime probes.
- No provider health result is inferred from a different capability.
- Every evidence package can identify its provider, tool surface, source revision,
  request, response, and degradation state.
- DB write/script remain disabled by default regardless of external provider
  availability.
- `python3 scripts/run_ci.py` and `git diff --check` pass at every wave exit.
