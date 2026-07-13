# Provider Convergence — Phase 0 Inventory

Status: AMENDED — see `upgrade/provider-convergence-integration-first-errata.md`
Date: 2026-07-13
Governing plan: `upgrade/maika-ua-db-access-provider-convergence-closure-plan.md`

The original identity/PR assignments below are a point-in-time inventory. The errata
is authoritative where this document proposes renaming DB Access internals, changing
provider deployment topology, or making breaking changes to existing MCP tools.

## Scope and baselines

This inventory freezes the three repositories named by the governing plan and records
the current machine contracts before U1/D1/M1 implementation begins.

| Repository | Local path | Branch | Audited baseline | Worktree at audit |
|---|---|---|---|---|
| Maika | `/home/zane/Desktop/agent-memory-arch-v3` | `master-v2` | `37424721e5171f176692f4b0e2de14dc64808870` | Existing user changes only: modified `.gitignore`, untracked `upgrade/` |
| Understand-Anything-MCP | `/home/zane/Desktop/ai-tools/Understand-Anything-MCP` | `main` | `0b4f3e2b18dc038bf28856821f568f05358fab2d` | clean |
| DB Access | `/home/zane/Desktop/ai-tools/Db-Access` | `main` | `eb7292e4645f1c81d8b7a32062130d6833b8f12b` | clean |

The Maika baseline exactly matches the governing plan. Historical/archive documents
were searched for context but are not treated as active runtime surfaces. Generated
`dist/`, `.venv`, `node_modules`, and Git internals are excluded from source-of-truth
counts.

## Executive findings

1. UA identity has already converged on `understand-anything` in active Maika
   profiles, but Maika has no canonical provider registry or vendored provider
   contract. UA-MCP exposes 17 useful tools, while only `get_graph_metadata` returns a
   structured machine snapshot. Most tools return human text and text-only errors.
2. UA graph health only detects the observed edgeless-skeleton case. Dirty worktree,
   duplicate/empty IDs, dangling edges, invalid relations/layers/domain references,
   missing source files, truncation, and capability applicability are not modeled.
3. CBM is described as conditional in doctrine and skill prose, but the typed skill
   schema supports only `capabilities.required`; `grounding-explorer` and
   `reviewing-change` therefore require `semantic_code_search` mechanically.
4. Maika's active database identity is `db-remote`, and its only platform operation is
   the virtual server-level label `db_query`. There is no `db-access` provider entry.
5. DB Access package identity is partly converged (`package.json.name = db-access`),
   but server, binary, Docker, systemd, banners, environment variables and versions
   still use incompatible identities. Package version is `1.0.0`; MCP server version
   is hard-coded as `2.0.0`.
6. DB Access capabilities are `read|write|script`; every server instance registers all
   tools. Metadata-only access, tool non-exposure, source-bound sessions, revocation,
   indexes/routines/dependencies, structured health, and common response envelopes do
   not exist. Mongo schema inspection returns a raw sample document.
7. Persistence classification exists only as broad booleans such as
   `database_changed`, `migration_required`, and `transaction_changed`. The router does
   not dispatch `database-explorer`; the DB gate is inferred later from query-plan
   capability names and validates only `read_only` plus objects/degradation.
8. Active legacy gates still recognize `node_id + blast-radius`, `KG unavailable`
   prose, UA regex markers, and CBM graph verification. They cannot validate the
   provider-neutral trace and database evidence contracts in the governing plan.

## 1. Identity matrix

| Surface | Current identity/version | Target | Contradiction | Slice |
|---|---|---|---|---|
| Maika manifest, UA | `understand-anything` (`cli/plugin-manifest.yaml`) | `understand-anything` | none; preserve | M1 |
| Maika provider mapping, UA | `understand-anything` (`.maika/profiles/provider-capabilities.yaml`) | canonical registry entry | mapping is not an identity registry and has no contract range | M1, M2 |
| UA-MCP client key | `understand-anything` (README examples) | `understand-anything` | none | U1 |
| UA-MCP FastMCP name | `knowledge-graph` (`server.py`) | contract `provider_id: understand-anything` | runtime name and provider ID are not linked | U1 |
| UA-MCP package/bin | `kg-mcp-server` / `kg-mcp`, version `0.2.1` | plan does not require a package rename; contract ID must be canonical | provider ID absent from machine responses | U1 |
| Maika manifest, DB | `db-remote` | `db-access` | obsolete provider ID | M1 |
| Maika platform DB mapping | `db_query -> db-remote` on four hosts | real `db-access` tool contracts | virtual operation and obsolete server ID | M1, M2, M6 |
| DB npm package | `db-access`, version `1.0.0` | `db-access`, one version source | package name is correct; version diverges from server | D1 |
| DB MCP server | `mcp-db-tools`, version `2.0.0` (`src/server.ts`) | `db-access`, version from package | identity and version divergence | D1 |
| DB binary | `mcp-db-tools`; `mcp-sse-proxy` | `db-access` | obsolete executable names | D1 |
| DB Docker service/container | `mcp-db-tools` | `db-access` | obsolete service/container names | D1 |
| DB systemd | `mcp-db-tools.service`; optional legacy `mcp-db-tunnel.service` | `db-access.service` | obsolete units and old path `tools/db-remote` | D1 |
| DB config environment | `CONFIG_PATH`, `MCP_SOURCE`, API key through headers | `DB_ACCESS_CONFIG_PATH`, `DB_ACCESS_SOURCE`, `DB_ACCESS_API_KEY` | generic/old variables; no canonical prefix | D1 |
| DB logs/banner | `MCP DB Tools` | `DB Access` | display-name drift | D1 |
| Database evidence | no provider ID required by v1 gate | `provider.id: db-access` | identity can be omitted or invented | M5 |

Identity decision: no alias or compatibility fallback is permitted. D1 and M1 must
land in the same release train; deployment configuration must migrate before install.

## 2. Capability matrix

| Capability | Current provider/role | Current mechanical state | Target role | Gap and slice |
|---|---|---|---|---|
| `architecture_discovery` | UA primary; CBM support | required by grounding; UA tools mapped | UA primary | registry/tool contract pinning (M1/M2) |
| `domain_flow_trace` | UA primary | required by grounding | UA primary | structured envelope/health applicability (U1/U2, M2/M4) |
| `call_chain_trace` | UA primary; CBM/source support | required by grounding/review | UA primary | structured envelope and neutral evidence (U3, M4) |
| `impact_analysis` | UA primary; CBM/source support | required globally by grounding/review | conditional when blast radius is needed | typed conditional migration (M3) |
| `graph_path_trace` | UA primary | available in registry | UA primary | contract validation (U1/U3, M2) |
| `inheritance_trace` | UA primary | available in registry | UA primary | contract validation (U1/U3, M2) |
| `semantic_code_search` | CBM primary | mechanically required by grounding and final review despite conditional prose | primary for anchor discovery; conditional support elsewhere | M3, M10 |
| `dependency_analysis` | CBM compatibility aggregate | widely required by old skills/orchestrator | remove after consumers migrate to precise capabilities | M3, M10 |
| `exact_source_inspection` | synthetic `current-source` | authoritative marker exists; exact claims can require file/symbol/hash | authoritative for exact code/application fact | M1, M4, M6 |
| `database_catalog_discovery` | absent | absent | DB Access primary | D2/D4, M1/M2/M3 |
| `database_schema_inspection` | no provider mapping; `db_query` virtual tool | required by database-explorer | DB Access primary, conditional on persistence | D2-D4, M1-M3 |
| `database_constraint_inspection` | folded into schema inspection | no distinct policy | DB Access primary | D4, M1-M3 |
| `database_index_inspection` | claimed by evidence vocabulary only | no DB tool | DB Access primary | D4, M1-M3 |
| `database_routine_inspection` | claimed by prose only | no DB tool | DB Access primary | D4, M1-M3 |
| `database_internal_dependency_analysis` | absent | old aggregate mixes DB dependencies and code consumers | DB Access primary | D4, M1-M3 |
| `database_read_probe` | `sql_read`/`mongo_read` under broad `read` | arbitrary reads are exposed; no safe read-probe contract | DB Access primary, conditional and `data_read`-gated | D3-D5, M2/M3/M6 |
| `database_code_consumer_analysis` | folded into `database_dependency_analysis` | source/graph provider unspecified | current source + UA primary; CBM conditional | M1/M3/M5 |

Current skill validator behavior (`cli/agent_content/skill_contract.py`) recognizes only
`capabilities.required`. It does not parse or validate `one_of`, `conditional`, trigger
vocabulary, activated reasons, or resolution/degradation. M3 owns that schema change
and the consumer migration in the same slice.

## 3. Tool contract matrix

| Provider | Current tools/contracts | Result/error behavior | Missing target contract | Slice |
|---|---|---|---|---|
| UA | `list_projects`, `get_graph_stats`, `get_graph_metadata` | metadata is JSON-safe v1; stats/list are text; many errors are `"Error: ..."` strings | `get_capabilities`; common envelope with provider/server/project/operation/request/freshness/health/result/limits/error | U1 |
| UA | `query_nodes`, `get_node_detail`, `search_by_file_path` | text results with pagination parameters; no common truncation/completeness record | structured node search and validated result schema | U1, U3 |
| UA | `get_relationships`, `trace_call_chain`, `find_impact`, `find_path`, `get_class_hierarchy` | useful BFS/traversal exists; output is human text; inherited edges are not provenance-typed | structured edges/traversals, `origin`, `confidence`, limits/truncated | U3 |
| UA | `get_domain_overview`, `get_domain_detail`, `get_domain_flow_detail` | domain graph is optional and malformed JSON silently becomes empty | structured domain flow plus domain health/applicability | U2, U3 |
| UA | `get_node_source` | path containment exists; source may be truncated with a prose marker | source hash, explicit truncation/limits, structured error | U1, U3 |
| UA | graph loader/metadata | minimal `HEALTHY|DEGRADED` edgeless check; freshness compares graph commit to committed changes | `HEALTHY|DEGRADED|INVALID`, dirty worktree, integrity checks, per-capability applicability | U2 |
| UA graph producer | provider-owned `/understand` writes final graph/meta | no operation/checkpoint/resume/quality contract in UA-MCP repo | deterministic operation workspace and proof of quality/resume | U4 |
| DB | `list_databases` | source-filtered; returns old `read|write|script` capability names | `get_capabilities`, common envelope, canonical IDs | D2, D3 |
| DB | `sql_list_tables`, `sql_get_columns`, `sql_get_constraints` | all require broad `read`; schema/owner not in tool input; Oracle uses `USER_*`; PostgreSQL defaults to `public` | `list_schemas`, `list_objects`, `get_table`, explicit schema/owner, metadata capability | D3, D4 |
| DB | no index/routine/dependency tools | absent | `get_indexes`, `list_routines`, `get_routine`, arguments, `get_dependencies` | D4 |
| DB | `sql_read`, `mongo_read` | arbitrary reads under `read`; SQL caps rows but no unified safe-probe policy | `read_probe` with projection/limit/timeout/masking/truncation and `data_read` | D3, D5 |
| DB | `mongo_list_collections`, `mongo_get_schema` | schema tool returns `sampleDocument` from `findOne({})` | metadata-only redacted shape/types/presence; no raw business row | D3, D5 |
| DB | `sql_write`, `sql_execute_script`, `mongo_write` | registered for every source, then rejected inside handler; token confirmation exists | do not register for metadata/data-read-only source; preserve privileged boundary outside Maika | D3 |
| DB | HTTP `/health` | process liveness only; unauthenticated; no database/source capability observation | authenticated `probe_database` result | D2 |
| DB | Streamable HTTP/SSE sessions | transport map keyed only by session ID; subsequent request does not compare authenticated source; reload preserves sessions | bind session to source and API-key fingerprint; revoke/permission loss closes sessions and tokens | D5 |
| Maika MCP bridge | generic `tools/list` and `tools/call` used only by learning actions | real execution exists, but not exploration adapters or evidence validation | deterministic UA/CBM/DB/current-source adapters with hashes/timeouts/redaction | M6 |

Maika must vendor the schemas delivered by U1 and D2 in M2. It must not maintain an
independent hand-written provider tool list after contract pinning; the current
`UA_TOOLS` constant is a transitional surface to remove in M2/M10.

## 4. Gate dependency matrix

| Active gate/consumer | Current dependency | Why it contradicts target | Replacement owner |
|---|---|---|---|
| `knowledge-checkpoint` | regex `node_id` + `blast-radius`, or compact `KG unavailable ... MEDIUM` prose | provider-specific prose; cannot accept complete UA trace neutrally | M4, remove in M10 |
| `mcp-status` | node/edge number regex or degrade prose | not a provider contract/probe envelope | M4/M5/M6, remove in M10 |
| `code-evidence` | CBM indexed-project probe and CBM node verification | complete UA trace can still be forced through CBM-specific graph evidence | M4, remove compatibility path in M10 |
| `implementation-context` | UA marker regex plus codebase `node_id`/blast-radius | explicitly names evidence shapes/providers | M4, M7, M10 |
| `query-plan` | flat list of required capabilities | cannot express `one_of` or activated conditional support | M3, M4, M5 |
| `tool-health` | accepts worker-authored `operation`, free-text `observed`, `freshness` | a worker can invent provider health; no contract/provider/hash validation | M4-M6 |
| `exploration-evidence` | strong source file/symbol/hash check, but trace itself lives inside `GROUNDING.yaml` | source check is reusable; trace request/evidence are not canonical/provider-neutral | M4 |
| exploration orchestrator | DB need inferred from two old capability IDs in query plan | no mechanical persistence risk signal or database-explorer dispatch | M5 |
| `database-context` | `read_only: true` and non-empty `objects` or one degradation map | no provider, source, environment, probe, hashes, schema owner, drift, sensitivity, capability-scope checks | M5 |
| workflow router `explore` | unconditional fixed gates; DB gate omitted from router | conditional completion gates cannot follow persistence classification | M5 |
| skill contract validator | `required` only | cannot reject unknown triggers, duplicates, unreasoned calls, or unresolved activation | M3 |
| provider capability validator | hard-coded `UA_TOOLS`; CBM concrete tools deliberately unverified | tool truth is split from provider contracts | M2 |
| behavior fixture E | checks only skill metadata/output/gate presence | does not prove persistence dispatch, DB evidence completeness, or tool non-exposure | M9/M10 |

Reusable enforcement: source file existence/symbol/SHA verification in
`validate_exploration_evidence`, query-plan capability membership, conflict/coverage
gates, and MCP bridge redaction should be extended rather than duplicated.

## 5. Artifact producer/consumer matrix

| Artifact | Current producer | Current validators | Current consumers/authority | Target change | Slice |
|---|---|---|---|---|---|
| `QUERY_PLAN.yaml` | intent/grounding workflow worker | `query-plan` | grounding explorer/orchestrator; exploration directory authority | keep; compile typed `TRACE_REQUEST` and `DATABASE_REQUEST` from it/risk | M4, M5 |
| `TOOL_HEALTH.yaml` | grounding worker | `tool-health` | exploration validation | provider adapter must write probe-derived health; worker must not author it | M6, M7 |
| `GROUNDING.yaml` | grounding worker | `exploration-evidence` | reconcile/spec/plan | remove embedded trace as raw authority; reference canonical evidence | M4, M7 |
| `EVIDENCE_MANIFEST.yaml` | grounding worker | exact-code claim validation | reconciliation and downstream capsules | retain claim index; link trace/DB evidence hashes | M4, M5, M7 |
| `TRACE_REQUEST.yaml` | absent | absent | absent | orchestrator compiles; exploration authority | M4 |
| `TRACE_EVIDENCE.yaml` | absent | absent | absent | provider adapters produce; worker consumes pinned hash | M4, M6, M7 |
| `DATABASE_REQUEST.yaml` | absent | absent | absent | persistence classifier/orchestrator produces | M5 |
| `DATABASE_CONTEXT.yaml` v1 | database-explorer worker | minimal `database-context` | grounding/reconciliation; directory-only authority | adapter + database-explorer reconciliation produce v2; add explicit authority/validator | M5, M6 |
| `CONFLICTS.yaml` | grounding/reconciliation | `conflicts` | reconcile/spec | retain; DB drift links to typed context classification | M5 |
| `COVERAGE.yaml` | grounding worker | `coverage` | exploration completion | include conditional capability and DB/trace completeness | M4, M5 |
| `EXPLORATION_VALIDATION.json` | orchestrator | aggregate result only | transition to reconciliation | add trace and conditional persistence checks | M4, M5 |
| worker context/capsule | dispatcher | capsule/hash validators | implementation/review workers | pin registry, policy, requests and evidence SHA256 values | M7 |
| UA external workflow request | generic canonical external workflow request exists | lifecycle validation elsewhere | `/understand` owner + blocked task | add unchanged-graph rejection and re-probe/resume | M8 |
| `DB_REPROBE_REQUEST.yaml` | absent | absent | absent | create environment-bound re-probe lifecycle | M8 |
| provider contracts | absent in Maika | hard-coded mapping validator | provider routing | vendor tested U1/D2 schemas and compatibility bounds | M2 |
| provider registry | absent | identity validator spans three legacy files | setup/router/gates/workers | single `.maika/config/provider-registry.yaml` authority | M1 |

All new artifacts need entries in `artifact-authority.yaml`, artifact lifecycle metadata,
manifest scaffolding, producer and consumer code in the same slice (development rules
R1/R7).

## 6. Risk-trigger matrix

| Trigger/signal | Current detection | Target activation | Required result | Slice |
|---|---|---|---|---|
| `persistence` / `persistence_change` | `database_changed` from migration/repository/SQL paths | user intent, paths, entity/repository/native SQL, DB terms | escalate trivial/small; dispatch DB explorer; DB request/context required | M5 |
| `database_dependency` | absent; folded into DB capability question | routine/package/object dependency terms or query question | activate internal dependency inspection | M3, M5 |
| `migration` | `migration_required` from path/text | migration paths/DDL intent | separate intended target from observed state; classify pre/post deployment drift | M5 |
| `routine_or_package` | absent | procedure/function/package/caller signals | routine inspection + code-consumer analysis | M3, M5 |
| `transaction_or_locking` | `transaction_changed`; locking not typed | annotations/transaction/locking terms | DB evidence and safe escalation | M5 |
| `data_read_required` | absent | explicit runtime-data verification question | require `data_read`, safe `read_probe`; metadata-only remains default | D3/D5, M3/M5 |
| `relational_contract_change` | absent | column/type/nullability/constraint changes | constraint inspection | M3/M5 |
| `performance_or_query_change` | broad repository/SQL path only | index/query-plan/performance terms | index inspection | M3/M5 |
| `unresolved_anchor` | prose-only CBM reason in grounding skill | UA cannot resolve anchor | activate semantic search with support record | M3/M4 |
| `ambiguous_semantic_query` | prose-only | natural-language ambiguity | CBM anchor discovery before UA trace | M3/M4 |
| `graph_gap` | prose-only | missing relationship/incomplete traversal | conditional CBM support | M3/M4 |
| `relevant_graph_stale` | provider doctrine; no dirty-worktree machine state | changed relevant file or dirty source | lower UA authority; source/CBM recovery or refresh | U2, M3/M4 |
| `hidden_consumer_risk` / `dynamic_wiring_risk` | prose-only review guidance | reflection/config/event wiring or review counter-question | CBM counter-evidence record | M3/M4 |
| `reviewer_counter_evidence` | prose-only | risk-based independent review | CBM support allowed, never globally required | M3/M4 |
| `ua_unavailable` | free-form degradation | validated unavailable/invalid UA response | conditional fallback with lower assurance | U2, M3/M4/M6 |
| `blast_radius_required` | old aggregate is broadly required | explicit scope/risk requirement | activate impact analysis | M3/M4 |

Unknown triggers must fail validation. Every activated trigger must have a provider call,
zero-result, or structured degradation. A conditional call without trigger/reason must
fail.

## 7. User-journey matrix

| Journey | Current path | Current failure | Target path | Slices |
|---|---|---|---|---|
| Fresh structured code trace | standard task -> grounding worker writes graph trace inside grounding | provider health and evidence can be worker-authored; CBM required in metadata | request -> UA probe/trace -> source verify -> neutral evidence; no CBM needed | U1-U3, M2-M7 |
| Ambiguous code request | grounding prose says semantic search conditionally | schema still marks CBM required for every grounding | CBM anchor -> UA structured trace -> source verify | M3/M4/M6 |
| Graph gap/hidden consumer | prose guidance only | no trigger record gate | UA partial -> triggered CBM counter-search -> source resolution | M3/M4 |
| Dirty or invalid graph | commit-only freshness, minimal edgeless warning | dirty source can still look fresh; malformed/degenerate graph can be used | health/applicability + dirty worktree -> lower authority/fallback/refresh | U2, M4/M8 |
| `/understand` interrupted/resumed | native external workflow writes final graph | no checkpoint/resume/quality proof | persisted batches/checkpoint -> deterministic merge -> quality -> re-probe | U4, M8 |
| Direct read-only DB query outside task | configured `db-remote` abstract label | no canonical provider or safe metadata source | authenticated `db-access` metadata/read query, no task workspace | D1-D5, M1/M2/M6 |
| Persistence-sensitive task | risk may escalate; worker may add DB capability question | no router dispatch; minimal DB gate; live DB precedence is wrong | typed persistence -> DB request -> metadata probe/catalog -> source/migration reconcile -> context v2 | D2-D5, M3/M5-M7 |
| Oracle routine + code caller | no routine catalog; Oracle catalog uses current user | cannot prove cross-owner routine/dependency/caller | explicit owner + DB routine/dependency evidence + UA/source consumer trace | D4, M5/M6 |
| PostgreSQL non-public schema | driver internally defaults to `public`; tool has no schema input | wrong schema can be queried silently | explicit schema on every catalog operation | D4 |
| Metadata-only Mongo | `mongo_get_schema` calls `findOne({})` and returns document | business data exposed under broad read | shape/types/presence only; raw sample needs `data_read` | D3/D5 |
| Wrong environment / expired evidence | environment absent from DB context | evidence can be reused across environments | block or issue DB re-probe; new context hash required | M5/M8 |
| Source revocation/session reuse | reload affects new sessions only; session ID map bypasses source comparison | old session retains access; another API key can address it | session-source-key binding, close/invalidate on revoke | D5 |
| Cross-host task | four platform maps contain same virtual DB label; Codex/Generic are passthrough | equivalent provider behavior is unproved | same requests/evidence/gates on Claude, Codex, Antigravity | M9/M10 |

## 8. Legacy removal matrix

| Legacy surface | Active locations | Replacement | Removal slice / expiry |
|---|---|---|---|
| `db-remote` | manifest, four platform adapters, README, init/MCP tests/snapshots | `db-access` | M1; no runtime alias |
| `db_query` | capability registry, base required tool list, four adapters/tests | provider contract tools/capability routing | M1/M2/M6; delete before M10 |
| `mcp-db-tools` | DB server name/bin, Docker, systemd, logs/docs | `db-access` | D1; atomic, no alias |
| `mcp-db-tools.service` | DB repo unit/docs | `db-access.service` | D1 |
| `CONFIG_PATH`, `MCP_SOURCE` | DB source/scripts/docs/examples | `DB_ACCESS_CONFIG_PATH`, `DB_ACCESS_SOURCE`; API key prefix as specified | D1; fail-fast old-name scan |
| `read|write|script` permission model | DB config/schema/access/tools/docs/tests | `metadata|data_read|write|script` | D3; configuration migration required |
| register-all-then-reject | `src/server.ts` registers all 11 tools | capability-scoped registration | D3 |
| raw Mongo `sampleDocument` | Mongo schema driver/tool/docs | redacted shape/type/presence | D3/D5 |
| PostgreSQL implicit `public` | driver defaults; tools omit schema | explicit schema | D4 |
| Oracle `USER_*` only | Oracle schema driver | explicit owner with permitted catalog views | D4 |
| UA text-only result/error | most `server.py` tools | common structured envelope | U1/U3; text compatibility removed before closure |
| hard-coded Maika `UA_TOOLS` | provider capability validator/tests | vendored provider contract | M2/M10 |
| `dependency_analysis` compatibility aggregate | registry, provider mapping, many skill contracts, orchestrator/tests | precise trace/impact and DB internal/code-consumer capabilities | M3 migration; remove M10 |
| globally required `semantic_code_search` | grounding/final-review contracts | typed conditional triggers | M3 |
| `node_id + blast-radius` gate | gate regex/tests/procedures | `TRACE_EVIDENCE` capability/completeness/source checks | M4; old gate removed M10 |
| `KG unavailable` / UA prose regex | gate regex/tests/procedures | structured provider error/degradation | M4/M6; remove M10 |
| embedded `GROUNDING.graph_trace` as raw authority | grounding skill/output | canonical request/evidence artifacts referenced by hash | M4/M7 |
| `DATABASE_CONTEXT` v1 objects/degradation | DB skill/gate/tests | v2 provider/environment/probe/observations/drift schema | M5 |
| unconditional/static router gate list | workflow router | risk-conditioned trace/DB completion gates | M5 |

Obsolete-name scans may exclude explicitly historical release notes and archived plans,
but not runtime code, active docs/examples, tests, manifests, service files, Docker files,
or generated client examples.

## Contradiction register and PR assignment

Every implementation contradiction found in the active surfaces is assigned below.

| ID | Contradiction | Severity | Assigned slice |
|---|---|---|---|
| C-01 | No single Maika provider registry | High | M1 |
| C-02 | Maika DB identity is `db-remote`; `db_query` is virtual | Critical | M1, M2, M6 |
| C-03 | DB package/server/bin/container/service/env/display/version identities diverge | Critical | D1 |
| C-04 | Provider schemas are not shipped/pinned in Maika | High | U1, D2, M2 |
| C-05 | UA results/errors are mostly unstructured | High | U1, U3 |
| C-06 | UA health misses graph integrity and dirty worktree | High | U2 |
| C-07 | UA graph production has no checkpoint/resume/quality proof | High | U4, M8 |
| C-08 | Skill contract has no `one_of`/`conditional`/typed triggers | Critical | M3 |
| C-09 | CBM semantic search is globally required despite conditional doctrine | High | M3 |
| C-10 | Old aggregate `dependency_analysis` conflates roles | High | M3, M10 |
| C-11 | Gates require provider-specific prose/CBM node evidence | Critical | M4, M10 |
| C-12 | No canonical trace request/evidence artifacts | High | M4 |
| C-13 | DB permission model has no metadata/data-read separation | Critical | D3 |
| C-14 | Metadata-only source still sees privileged tools | Critical | D3 |
| C-15 | DB catalog lacks indexes/routines/dependencies and explicit owner/schema | High | D4 |
| C-16 | Mongo metadata exposes a raw sample document | Critical | D3, D5 |
| C-17 | DB health is process-only; no `probe_database` contract | High | D2 |
| C-18 | DB HTTP/SSE session is not bound to authenticated source; reload preserves access | Critical | D5 |
| C-19 | Persistence signal does not mechanically dispatch/require DB context | Critical | M5 |
| C-20 | DB context v1 lacks identity/environment/probe/hashes/drift/sensitivity | Critical | M5 |
| C-21 | Active doctrine says live DB wins over source/migration intent | High | M5, M10 |
| C-22 | Runtime does not execute exploration provider adapters before workers | Critical | M6 |
| C-23 | Workers do not receive hash-pinned provider policy/evidence | High | M7 |
| C-24 | Refresh/re-probe cannot prove changed evidence or environment binding | High | M8 |
| C-25 | No cross-surface system-model/mutation validator | High | M9 |
| C-26 | Existing behavior fixture checks presence, not deterministic journeys | High | M9, M10 |
| C-27 | Prior trimmed UA plan is marked as superseding the older broad closure plan; the new governing plan reopens work | Medium | M10 documentation closure; each enforcement still needs ledger evidence per R3 |

## Slice entry and exit order

The repository baselines are clean enough to begin implementation, but the work must
remain split in the order required by the governing plan:

```text
U1 -> U2 -> U3 -> U4
D1 -> D2 -> D3 -> D4 -> D5
M1 -> M2 -> M3 -> M4 -> M5 -> M6 -> M7 -> M8 -> M9 -> M10
```

Provider slices can be developed independently across repositories, but Maika M2 cannot
pin a contract before U1/D2 publish it, M6 cannot execute contracts before M2, and M10
cannot remove compatibility paths before all behavior fixtures pass.

For each slice, the mandatory gate is: exact-source note, narrow implementation,
targeted tests, provider-contract validation where applicable, artifact audit, full
repository CI, relevant deterministic behavior fixtures, `git diff --check`, then stop
and report. No later slice proceeds while the current repository CI is red.

## Phase 0 exit decision

**PASS for inventory; implementation is unlocked at U1/D1/M1 only.**

The eight required matrices are complete, all observed contradictions have an owning
slice, all three requested baselines were verified, and no provider/runtime behavior was
changed during Phase 0. Cross-host qualification and live database probes remain later
release gates, not Phase 0 evidence.
