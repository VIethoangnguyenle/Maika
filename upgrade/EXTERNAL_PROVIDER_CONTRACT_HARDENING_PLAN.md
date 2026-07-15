# Maika Ecosystem External Provider Contract Hardening Plan

Date: 2026-07-15
Maika branch: `master-v2`
Source assessment: `upgrade/MAIKA_FRAMEWORK_ECOSYSTEM_BRAINSTORM.md`

## 1. Objective

Define the upstream changes and compatibility contracts needed for Maika to use
Db-Access, Understand-Anything, Codebase Memory, and AgentMemory safely.

This is a coordination and acceptance plan. Work in Maika must not directly modify
the external repositories. Each provider patch is developed, reviewed, released,
and pinned in its owning repository before Maika raises the corresponding readiness
gate.

## 2. Audited revisions

| Provider | Repository | Audited revision |
|---|---|---|
| Understand-Anything producer | `Egonex-AI/Understand-Anything` | `092feec79f6f7c78d95c9c55087fb48fa1178c99` |
| Understand-Anything MCP | `VIethoangnguyenle/Understand-Anything-MCP` | `0b4f3e2b18dc038bf28856821f568f05358fab2d` |
| Codebase Memory MCP | `DeusData/codebase-memory-mcp` | `2469ecc3a7a2f80debe296e1f17a1efcfdb9450c` |
| AgentMemory | `rohitg00/agentmemory` | `93ae9bc04f3ab5042f982aaadf11f1e3f5137531` |
| Db-Access | `VIethoangnguyenle/Db-Access` | `eb7292e4645f1c81d8b7a32062130d6833b8f12b` |

Every issue, fixture, reproduction, and upstream PR must identify its actual base
revision. Do not cite an unpinned default branch as contract evidence.

## 3. Delivery order

```text
E0 Shared fixture and release contract
  -> E1 Db-Access authorization and write safety
  -> E2 Understand-Anything producer/consumer convergence
  -> E3 Codebase Memory snapshot identity
  -> E4 AgentMemory proxy/store identity and no-fallback mode
  -> E5 Cross-provider compatibility matrix and pilot certification
```

E1 and E2 may execute in parallel after E0. E3 and E4 do not block Maika read-only
development, but they block claims of complete snapshot-bound evidence.

---

## E0 — Shared fixture and release contract

### Goal

Make provider compatibility testable without relying on README descriptions.

### Required provider release metadata

```yaml
provider_name:
provider_version:
git_revision:
protocol: mcp
protocol_version:
tool_surface_hash:
schema_version:
build_variant:
```

### Fixture rules

- Capture `tools/list` and its input schemas from the released executable.
- Capture success, error, degraded, and missing-provenance responses.
- Remove secrets and user data while preserving response shape.
- Store a content hash and upstream revision beside every fixture.
- Add producer-consumer fixtures at the boundary, not only unit fixtures inside one
  repository.

### Compatibility policy

```text
compatible   -> all required tools and critical fields understood
degraded     -> provider usable for a documented subset
unsupported  -> critical contract/version unknown or safety invariant absent
```

Additive fields do not automatically break compatibility. Unknown critical enum
values, missing identity, or silently discarded structural relations must degrade
or reject the contract.

---

## E1 — Db-Access authorization and write safety

### Findings

- A — cross-session authorization.
- B — shadow-preview fail-open.
- C — false-success tool response.
- D — confirmation token is not human approval.
- E — dynamic DDL bypass.

### Owning repository

`VIethoangnguyenle/Db-Access`

### E1.1 Bind transport sessions to source identity

For Streamable HTTP and SSE, store:

```yaml
session_id:
source_id:
api_key_fingerprint:
created_at:
transport:
```

Every request that reuses a session must match the bound source. A valid API key
for another source must receive 403 or an MCP authorization error before tool
dispatch.

Tests:

- source A creates session; source B cannot reuse it;
- read-only source cannot reuse a write-capable session;
- hot reload does not silently rebind an existing session;
- SSE message POST enforces the identity of the SSE session owner;
- session IDs and raw keys are absent from normal logs.

### E1.2 Fail closed on untrusted UPDATE/DELETE preview

Before issuing a token, require:

```yaml
preview:
  status: trusted
  query_hash:
  affected_row_sample:
  estimate_or_count:
```

If shadow generation or execution fails, return `isError: true` and do not create a
token. Full-table UPDATE/DELETE requires a separate explicit option and policy;
absence of a WHERE clause must never be hidden behind “preview not available”.

INSERT may keep a payload preview because it has no affected-row shadow query.

### E1.3 Preserve execution failure semantics

If `driver.executeWrite()` or script execution returns `success != true`:

- tool response sets `isError: true`;
- success wording is absent;
- error details remain structured;
- `rowsAffected: 0` is distinguished from execution failure.

Add Oracle, PostgreSQL, and Mongo regression tests.

### E1.4 Separate provider confirmation from human approval

Rename or document the existing token as provider confirmation, and bind it to:

```yaml
source_id:
session_id:
database:
tool:
operation_type:
request_hash:
expires_at:
```

Do not claim this token is human approval. Human approval remains a caller/control
plane concern unless Db-Access adds a separately authenticated approval API.

Increase token entropy beyond the current short display token or use an opaque
cryptographic token plus a separate display code.

### E1.5 Make database privilege the DDL boundary

- Document and test a dedicated runtime principal without CREATE, ALTER, DROP,
  TRUNCATE, GRANT, or REVOKE privileges.
- Treat script regex detection as defense in depth only.
- Reject dynamic execution constructs where safely identifiable, but do not claim
  this makes a DDL-capable credential safe.
- Publish a least-privilege matrix for Oracle and PostgreSQL.

### Db-Access release gate

- A–C pass integration tests on both HTTP transports and supported databases.
- Default example configuration uses least-privilege accounts.
- Release notes explicitly state whether token compatibility changed.
- Maika pins the fixed version before enabling any DB write capability.

---

## E2 — Understand-Anything producer/consumer convergence

### Findings

- G — dirty worktree reported fresh.
- H — malformed domain graph silently disappears.
- M — `.ua` versus `.understand-anything` discovery.
- N — `lastAnalyzedAt` versus `analyzedAt`.
- O — `inherits` versus `extends`.
- P — unversioned producer-consumer drift.

### Owning repositories

- Producer: `Egonex-AI/Understand-Anything`.
- Consumer: `VIethoangnguyenle/Understand-Anything-MCP`.

### E2.1 Publish a producer contract fixture

The producer repository should publish a minimal generated project containing:

- `.ua/knowledge-graph.json`;
- `.ua/domain-graph.json`;
- `.ua/meta.json`;
- one class inheritance edge;
- one interface implementation edge;
- one domain, flow, and step;
- producer graph/meta versions.

The MCP repository must consume this fixture in CI. Handwritten MCP fixtures alone
are insufficient.

### E2.2 Share directory resolution semantics

Consumer resolution must match the producer:

```text
existing .understand-anything -> legacy directory wins
otherwise                     -> .ua
both exist                    -> explicit conflict status
```

Do not choose the newest file silently. Return the selected directory and conflict
state in graph metadata.

### E2.3 Normalize metadata compatibility

Consumer lookup order:

```text
meta.lastAnalyzedAt
meta.analyzedAt          # legacy
project.analyzedAt       # fallback
```

Commit lookup order:

```text
meta.gitCommitHash
project.gitCommitHash
```

Return the producer schema version and which compatibility alias was used.

### E2.4 Canonicalize structural relations

Normalize at load time:

```text
extends  -> inherits
inherits -> inherits
```

All hierarchy and impact queries then operate on `inherits` plus `implements`.
Tests must cover hierarchy up/down, relationships, impact propagation, and mixed
legacy/new fixtures.

### E2.5 Detect dirty source state

Freshness must account for:

```text
graph commit .. HEAD
unstaged tracked changes
staged changes
untracked relevant source files
```

Return separate fields rather than one ambiguous boolean:

```yaml
commit_freshness:
working_tree:
dirty_file_count:
dirty_files_sample:
working_tree_state_hash:
```

Generated, ignored, and non-source paths should follow the same documented ignore
contract as analysis.

### E2.6 Report domain graph validity

```yaml
domain_graph:
  status: healthy | missing | empty | invalid
  node_count:
  edge_count:
  parse_error_code:
```

Malformed JSON must log a sanitized error and set provider health to degraded when
domain capability is requested. Missing optional domain data may remain a
capability-specific degradation rather than a global failure.

### Understand-Anything release gate

- MCP CI consumes an artifact produced by the pinned producer fixture job.
- New and legacy directories both pass.
- Both metadata field variants pass.
- `inherits` hierarchy and impact tests pass.
- staged, unstaged, and untracked relevant source changes are not reported fresh.
- Invalid domain JSON is observable through structured metadata.

---

## E3 — Codebase Memory snapshot identity

### Finding

- T — query evidence is not bound to an immutable index revision.

### Owning repository

`DeusData/codebase-memory-mcp`

### Existing contract to preserve

`semantic_query` is an array argument of `search_graph`. It is not a standalone
tool. No upstream tool rename is required for Finding R; Maika owns that mapping
fix.

### Required snapshot identity

Assign a monotonic or content-derived generation after every committed full,
incremental, watcher, or imported-artifact index update:

```yaml
index_generation:
index_updated_at:
index_mode: full | moderate | fast | incremental | imported_artifact
source_head:
working_tree_state_hash:
schema_version:
binary_version:
```

Expose this identity in `index_status` and every graph query response, preferably
from the same SQLite read transaction used by the query.

### Consistency semantics

- A single tool call observes one SQLite snapshot.
- The response identifies that snapshot generation.
- Watcher updates create a new generation only after commit.
- Imported artifacts record their embedded source revision and artifact hash.
- A query may optionally request `expected_generation`; mismatch returns a
  structured stale-generation error rather than silently querying the new graph.

### Tests

- Watcher update between two calls produces distinct generations.
- A query response generation matches the transaction it read.
- Failed indexing does not advance generation.
- Imported artifact identity differs from a later incremental refresh.
- `expected_generation` succeeds for the pinned snapshot and rejects after refresh.

### Codebase Memory release gate

- Runtime `tools/list` and schemas are captured from the release binary.
- `index_status` exposes immutable generation and indexed source identity.
- Query responses bind to generation.
- Maika removes its interim before/after heuristic only after pinning this release.

---

## E4 — AgentMemory proxy/store identity and no-fallback mode

### Findings

- U — proxy/local fallback split-brain.
- V — mutable tool surface requires runtime classification.
- W — auto-capture can bypass Maika governance.
- Y — agent scope is not authorization.
- AA — remote auth/store identity ambiguity.

### Owning repository

`rohitg00/agentmemory`

### E4.1 Add a hard no-fallback mode

Provide a documented runtime setting such as:

```text
AGENTMEMORY_FALLBACK=disabled
```

When disabled:

- failed startup probe returns provider unavailable;
- failed proxied core-tool call returns an MCP error;
- failed remote `tools/list` does not return the local seven-tool list;
- no write is redirected to local KV.

`AGENTMEMORY_FORCE_PROXY` alone is not sufficient if a later core-tool proxy failure
can still execute against local KV.

### E4.2 Expose instance and store identity

An authenticated readiness/capabilities endpoint should return:

```yaml
runtime_version:
server_instance_id:
store_id:
deployment_mode:
authenticated_principal:
tool_surface_hash:
memory_generation:
```

Public liveness may remain minimal, but it must not be usable as proof of store or
authorization identity.

### E4.3 Separate retrieval scope from authorization

- Keep `agentId` as a retrieval/tagging feature.
- Document wildcard and per-request override behavior explicitly.
- For shared untrusted deployments, bind principal to allowed namespaces at the
  authenticated server layer.
- Do not present `AGENTMEMORY_AGENT_SCOPE=isolated` as tenant isolation.

### E4.4 Make hooks observable

Expose hook/injection posture through a diagnostic endpoint or CLI output:

```yaml
auto_capture:
context_injection:
auto_compress:
registered_hook_types: []
```

Maika will use this only for diagnostics and governance compatibility; it will not
rewrite global hook configuration automatically.

### AgentMemory release gate

- No-fallback mode is covered for startup, tools/list, core calls, and writes.
- Authenticated identity distinguishes two stores behind different URLs.
- Tool-surface hash changes when proxy/local or configured tool surface changes.
- Namespace authorization tests do not rely solely on request `agentId`.
- Maika pins the release before calling proxy-only mode `ready`.

---

## E5 — Cross-provider compatibility matrix and pilot certification

### Matrix

For every supported version combination, record:

| Provider | Version/revision | Required tools | Contract fixture | Identity level | Allowed Maika lanes |
|---|---|---|---|---|---|
| Db-Access | pinned | read/schema by default | pass/fail | source + session | exploration, data_probe |
| UA MCP + producer | pinned pair | metadata + trace tools | pass/fail | source revision + dirty state | discovery |
| Codebase Memory | pinned | search/trace/status | pass/fail | index generation | discovery; explicit index optional |
| AgentMemory | pinned | recall core | pass/fail | proxy + store + tool hash | recall only |

### Banking pilot minimum

- Db-Access uses a dedicated read-only principal and source.
- Db-Access A–C fixes are released even if write lanes remain disabled, because
  session isolation is a server-wide concern.
- UA producer/MCP pair passes the real artifact fixture.
- CBM search and trace bind to a known generation, or Maika reports the interim
  snapshot identity as unverified.
- AgentMemory runs proxy-only with fallback disabled, recall-only lanes, hooks off,
  and candidate-only authority.
- Current source is checked for every exact code or business-rule claim that affects
  implementation.

### Features that remain blocked

- DB write until human approval, preview, failure propagation, and least privilege
  are proven end to end.
- DB script until the database principal is proven unable to perform DDL.
- Shared AgentMemory tenant isolation until authenticated namespace enforcement is
  available.
- Complete multi-call CBM evidence claims until immutable generation is available.
- Automatic canonical knowledge persistence from AgentMemory.

## 4. Upstream issue/PR slicing

Recommended independent changes:

1. Db-Access: bind HTTP/SSE sessions to source identity.
2. Db-Access: fail closed on preview failure and preserve execution errors.
3. Db-Access: bind confirmation token and publish least-privilege profiles.
4. UA MCP: shared directory and metadata compatibility resolver.
5. UA MCP: inheritance canonicalization and producer fixture CI.
6. UA MCP: dirty-tree freshness and structured domain health.
7. CBM: persistent index generation and query response binding.
8. AgentMemory: hard no-fallback proxy mode.
9. AgentMemory: authenticated server/store/tool-surface identity.
10. AgentMemory: authenticated namespace policy and hook diagnostics.

Avoid one cross-provider mega-PR. Each upstream change needs its own reproduction,
compatibility note, and release version.

## 5. Definition of done

- Every confirmed external finding has an owning repository and regression test.
- Maika fixtures are refreshed from released, pinned provider revisions.
- Provider documentation matches runtime `tools/list` and response schemas.
- No provider claims a soft parser, token, scope flag, or health endpoint is a hard
  security boundary.
- Version-pair compatibility is machine-testable.
- Pilot certification explicitly lists unavailable and degraded capabilities.
- External patches are never vendored or silently copied into the Maika repository.
