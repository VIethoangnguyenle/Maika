> **Status: SUPERSEDED by docs/superpowers/plans/2026-07-12-ua-convergence-trimmed.md (2026-07-12).**
> Reason: builds 17 phases of enforcement for unobserved failures (violates DEVELOPMENT_RULES R3/R7);
> no UA graph has ever been generated on this machine, so freshness/health/fixture design has no data.
> Phases 5–17 remain here as the deferred backlog; unlock conditions live in the trimmed plan, Track 3.

# Maika × Understand-Anything Convergence & Closure Plan

## Codex-ready cross-repository execution plan

```text
Primary repository:
  VIethoangnguyenle/Maika
  branch: master-v2
  baseline: 853ec45ba685fe8b368aaaad3e9e5e2c3cd0f8a9

Provider repository:
  VIethoangnguyenle/Understand-Anything-MCP
  branch: main
  baseline: 9a2778777d368ab3c8e7aebef1a3e18854d96480
  current package version: 0.1.0
```

---

# 1. Mission

Giải quyết dứt điểm bài toán Understand-Anything trong Maika bằng một **convergence release** thay vì tiếp tục:

```text
thêm provider doctrine
→ review thấy metadata lệch
→ sửa metadata
→ review thấy gate cũ vẫn ưu tiên CBM
→ sửa gate
→ review thấy worker không nhận contract
→ sửa prompt
→ review thấy refresh lifecycle bị đứt
```

Kết quả cuối cùng phải đạt:

```text
Understand-Anything
→ graph producer

Understand-Anything-MCP
→ deterministic structured graph tracer

Codebase Memory MCP
→ semantic discovery, gap recovery, hidden consumer search,
  independent corroboration

Current source
→ authority cuối cùng cho exact code fact
```

Maika phải có một pipeline duy nhất:

```text
question
→ trace request
→ provider resolution
→ graph health/freshness probe
→ UA-MCP structured trace
→ conditional CBM support
→ current-source verification
→ structured evidence artifact
→ capability-based gate
→ skill/plan/review consumption
```

Mục tiêu closure:

> Không còn trường hợp policy nói UA-MCP primary nhưng metadata, gate, worker hoặc runtime vẫn bắt CBM làm primary.

---

# 2. Vì sao đây là vấn đề dai dẳng từ Maika cũ

## 2.1 Provider được mô tả ở quá nhiều nơi

Hiện các surface cùng tham gia định nghĩa provider:

```text
cli/plugin-manifest.yaml
profiles/capability-registry.yaml
profiles/provider-capabilities.yaml
rules/jit/providers.md
skills/*/SKILL.md
bootstrap/doctor
external-workflows.yaml
worker prompt
gate-check
tests
```

Một fact như provider ID hiện có thể xuất hiện dưới nhiều spelling:

```text
understand-anything
understand-anything-mcp
UA-MCP
```

## 2.2 Gate cũ kiểm provider, không kiểm capability

Các gate cũ còn suy luận:

```text
node_id + blast-radius
→ CBM evidence tốt

không có CBM node
→ reject
```

Trong khi target model là:

```text
call_chain_trace được thỏa mãn
+ trace có provenance
+ source fact được verify
→ pass
```

## 2.3 UA-MCP hiện trả phần lớn kết quả dạng text

Các tool hiện trả human-readable strings.

Điều này tốt cho chat, nhưng khó dùng làm deterministic evidence vì Maika phải:

```text
parse prose
đoán freshness
đoán node
đoán truncation
đoán edge provenance
```

## 2.4 Freshness chưa đủ cho decision-level policy

Current freshness có:

```text
status
git commit
changed file count
sample changed files
```

Nhưng Maika cần thêm:

```text
repository HEAD
full/truncated changed-file information
relevant stale files đối với trace hiện tại
graph health
graph schema compatibility
```

## 2.5 Worker vẫn có thể hành xử theo host/model interpretation

Rule và skill có thể đúng nhưng worker chỉ nhận:

```text
Skill: grounding-explorer
```

Nếu không pin contract và evidence package, behavior vẫn phụ thuộc model tự tìm đúng file.

## 2.6 Graph quality chưa được đưa vào readiness

Có graph file không đồng nghĩa graph đủ tin cậy.

Cần phát hiện:

```text
duplicate node IDs
dangling edges
missing source files
unknown relation types
unresolved domain→code cross-reference
empty graph
schema mismatch
truncated traversal
ambiguous anchor
```

---

# 3. Final architectural decision

## 3.1 Ba plane độc lập

### Navigation plane

```text
UA-MCP structured graph trace: primary
CBM semantic discovery: supporting
```

### Verification plane

```text
Current source: authoritative
```

### Maintenance plane

```text
/understand
/understand-domain
CBM index
```

Maintenance operation không được trộn với read-only trace.

---

## 3.2 Explicit distinction between interactive and deterministic usage

### Interactive

```text
/understand-chat
→ host-native conversation/report
```

### Deterministic Maika task grounding

```text
Maika provider adapter
→ structured UA-MCP contract
→ TRACE_EVIDENCE.yaml
→ worker consumes pinned evidence
```

Maika task không được phụ thuộc vào một report tự do từ `/understand-chat` để chứng minh exact trace.

---

## 3.3 One canonical provider identity

Canonical provider ID:

```text
understand-anything
```

Display name:

```text
Understand-Anything MCP
```

Aliases only for user-facing input:

```text
ua-mcp
understand-anything-mcp
```

Internal artifacts, health, routing and gates must normalize to:

```text
understand-anything
```

---

## 3.4 One owner per fact

| Fact | Canonical owner |
|---|---|
| Provider identity, aliases, setup key | `config/provider-registry.yaml` |
| Capability semantics | `profiles/capability-registry.yaml` |
| Provider→capability→tool mapping | generated from provider registry + UA contract |
| UA tool contract | exported by UA-MCP |
| Trace request schema | `config/trace-request.schema.yaml` |
| Trace evidence schema | `config/trace-evidence.schema.yaml` |
| Freshness policy | `config/graph-freshness-policy.yaml` |
| Skill routing | skill typed metadata |
| Mechanical completion | capability/evidence gates |
| Task workflow | `config/workflow-router.yaml` |
| External maintenance workflows | `config/external-workflows.yaml` |

---

# 4. Non-goals

Không làm trong initiative này:

```text
viết lại Understand-Anything graph generator
merge UA-MCP và CBM thành một server
dùng graph thay current source
ép /understand-chat vào /task
ép mọi query phải tạo report
tự động refresh graph mà user không biết
dùng LLM prose parsing làm contract chính
thêm graph database riêng cho Maika
tạo Evidence Broker tổng quát cho mọi provider
```

Chỉ mở rộng sang provider khác khi UA pipeline đã closure.

---

# 5. Closure invariants

## Identity

1. Một canonical provider ID duy nhất.
2. Alias chỉ normalize tại boundary.
3. Plugin setup, doctor, bootstrap, capability mapping và external workflow owner cùng resolve một ID.

## Contract

4. UA-MCP công bố machine-readable contract version.
5. Maika khai minimum supported contract version.
6. Unknown/incompatible contract fail closed với remediation.

## Trace

7. Mọi structured trace có project, graph commit, repository HEAD và freshness.
8. Mọi traversal có operation, direction, relation filter, depth/limit và truncation.
9. Mọi anchor có node ID, node type và source path khi có.
10. Inherited/derived edge không được giả làm direct edge.

## Source authority

11. Exact material code fact phải có current source verification.
12. Source verification có path, symbol/range và SHA-256.
13. Graph source extraction không được đọc ngoài project root.

## CBM

14. CBM không mandatory mặc định cho structured trace.
15. CBM chỉ chạy khi conditional trigger được ghi.
16. Mỗi support call ghi reason.
17. Reviewer có thể dùng CBM làm independent counter-evidence.

## Freshness

18. Stale unrelated không vô hiệu toàn graph.
19. Stale relevant hạ graph từ evidence chính xuống navigation evidence.
20. Very stale không được dùng làm primary evidence.
21. Refresh chỉ được claim sau khi graph artifact và metadata thực sự đổi.

## Worker

22. Worker nhận pinned skill/provider/evidence contract.
23. Worker không tự chạy side-effecting refresh.
24. External workflow request có path và lifecycle canonical.
25. Resume chỉ pass sau blocker được revalidated.

## Gate

26. Gate kiểm capability/evidence contract, không kiểm tên provider.
27. Gate không chứa message “trace via CBM” như invariant chung.
28. Provider-specific compatibility gate có expiry.

## Behavior proof

29. Deterministic fixture chứng minh UA primary path.
30. Real-host dogfood chứng minh Claude, Codex và Antigravity hiểu cùng model.
31. Mutation tests chứng minh cross-surface drift bị CI bắt.

---

# 6. Target architecture

```text
┌──────────────────────────────────────────────────────────┐
│ User / Maika Task                                       │
└───────────────────────┬──────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────┐
│ Query Plan / Trace Request                              │
│ TRACE_REQUEST.yaml                                      │
│ - question                                              │
│ - required capabilities                                 │
│ - target project                                        │
│ - freshness requirement                                 │
│ - source verification requirement                       │
└───────────────────────┬──────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────┐
│ Maika Provider Resolver                                 │
│ - canonical provider identity                           │
│ - contract compatibility                               │
│ - health/readiness                                      │
└──────────────┬──────────────────────┬────────────────────┘
               │                      │
               ▼                      ▼
┌──────────────────────────┐  ┌───────────────────────────┐
│ UA-MCP structured client │  │ CBM support              │
│ PRIMARY                  │  │ CONDITIONAL              │
└──────────────┬───────────┘  └──────────────┬────────────┘
               │                              │
               └──────────────┬───────────────┘
                              ▼
┌──────────────────────────────────────────────────────────┐
│ Current Source Verification                             │
│ path + symbol/range + file SHA                          │
└───────────────────────┬──────────────────────────────────┘
                        ▼
┌──────────────────────────────────────────────────────────┐
│ TRACE_EVIDENCE.yaml                                     │
│ provider-neutral evidence contract                      │
└───────────────────────┬──────────────────────────────────┘
                        ▼
┌──────────────────────────────────────────────────────────┐
│ Capability-based Gates                                  │
│ Skills / Planning / Review                              │
└──────────────────────────────────────────────────────────┘
```

---

# 7. Cross-repository release strategy

## Release train

```text
UA-MCP v0.2.0
→ machine contract + structured API + graph health

Maika provider convergence PRs
→ canonical identity + adapter + evidence + gates

UA-MCP v0.2.1
→ fixes discovered during Maika integration

Maika closure release
→ dogfood + compatibility removal
```

## Compatibility rule

Maika must declare:

```yaml
provider_contracts:
  understand-anything:
    minimum: 1
    maximum_tested: 1
```

UA-MCP must return:

```yaml
contract_version: 1
server_version: 0.2.0
```

No dependency on arbitrary latest main.

---

# 8. Phase 0 — Freeze and complete inventory

## Goal

Không code trước khi vẽ đủ dependency graph của UA integration.

## Maika inspection

Inspect exact consumers of:

```text
understand-anything
understand-anything-mcp
UA-MCP
architecture_discovery
dependency_analysis
call_chain_trace
impact_analysis
semantic_code_search
node_id
blast-radius
UA evidence
KG unavailable
EXTERNAL_WORKFLOW_REQUEST
```

Search in:

```text
.maika/
cli/
scripts/
.github/
docs/
```

## UA-MCP inspection

Inspect:

```text
server.py
kg_loader.py
pyproject.toml
tests/
README.md
```

Inventory:

```text
tool names
parameters
return types
error semantics
freshness output
graph metadata
source extraction
path safety
traversal truncation
edge resolution provenance
schema assumptions
```

## Deliverable

```text
docs/plans/ua-convergence-inventory.md
```

Required tables:

### Provider identity table

| Surface | Current value | Canonical target | Action |
|---|---|---|---|

### Gate dependency table

| Gate | Provider-specific assumption | Capability target | Removal PR |
|---|---|---|---|

### Tool contract table

| UA tool | Current output | Structured equivalent | Breaking? |
|---|---|---|---|

### User journey table

| Journey | Current behavior | Missing proof | Target |
|---|---|---|---|

## Exit gate

- Every spelling occurrence classified.
- Every gate using CBM/UA regex identified.
- Every skill required/conditional mismatch identified.
- Every runtime path consuming external workflow request identified.
- No unknown UA-MCP public tool.

---

# 9. Phase 1 — Canonical Provider Model in Maika

## New file

```text
.maika/config/provider-registry.yaml
```

## Proposed schema

```yaml
version: 1

providers:
  understand-anything:
    display_name: Understand-Anything MCP
    kind: structured_graph
    aliases:
      - ua-mcp
      - understand-anything-mcp

    setup_ref: understand-anything

    contract:
      id: ua-mcp
      minimum_version: 1
      maximum_tested_version: 1

    external_workflows:
      build_code_graph: understand
      build_domain_graph: understand-domain
      interactive_query: understand-chat

    capabilities:
      primary:
        - architecture_discovery
        - domain_flow_trace
        - call_chain_trace
        - impact_analysis
        - graph_path_trace
        - inheritance_trace

      supporting:
        - semantic_code_search

  codebase-memory-mcp:
    display_name: Codebase Memory MCP
    kind: semantic_index

    capabilities:
      primary:
        - semantic_code_search
      supporting:
        - architecture_discovery
        - call_chain_trace
        - impact_analysis

  current-source:
    display_name: Current Source
    kind: local_authority
    synthetic: true
    setup_ref: null

    capabilities:
      primary:
        - exact_source_inspection

    authoritative_for:
      - exact_code_fact
```

## Normalization API

Create:

```text
cli/providers/identity.py
```

Functions:

```python
normalize_provider_id(value) -> canonical_id
provider_aliases(canonical_id) -> set[str]
validate_provider_reference(value) -> errors
```

## Cross-surface validation

Create:

```bash
maika content validate-provider-model
```

It must cross-check:

```text
provider-registry
↔ plugin manifest setup keys
↔ capability registry provider IDs
↔ provider capability mapping
↔ bootstrap selected providers
↔ doctor provider IDs
↔ external workflow owner
↔ worker contracts
```

## Remove hard-coded provider tool list

Current validator hard-codes UA tools.

Replace it with a contract artifact exported by UA-MCP.

## Tests

- Alias normalizes.
- Unknown alias fails.
- Duplicate alias fails.
- Manifest provider mismatch fails.
- External workflow owner mismatch fails.
- Synthetic source provider allowed.
- Mutation: rename one provider in one file → CI fail.

## Exit

No internal artifact stores `understand-anything-mcp` as canonical ID.

---

# 10. Phase 2 — UA-MCP Machine Contract v1

## Goal

UA-MCP remains human-friendly for chat but gains a stable structured interface for Maika.

## 10.1 Contract document

Add to UA-MCP:

```text
contracts/ua-mcp-contract-v1.json
contracts/ua-mcp-contract-v1.schema.json
```

Contract includes:

```json
{
  "contract_version": 1,
  "server_name": "understand-anything",
  "server_version": "0.2.0",
  "graph_schema_support": {
    "code_graph": ["current"],
    "domain_graph": ["current"]
  },
  "capabilities": {},
  "tools": {}
}
```

## 10.2 New MCP tool: `get_capabilities`

Return structured JSON-compatible mapping, not prose.

Must include:

```text
contract version
server version
tools
capabilities
argument schema summary
result schema IDs
feature flags
```

## 10.3 New MCP tool: `get_graph_metadata`

Input:

```yaml
project:
include_changed_files: false
changed_files_limit: 200
```

Output:

```yaml
contract_version: 1
project:
root_path:
graph:
  code_present:
  domain_present:
  graph_commit:
  analyzed_at:
  code_graph_mtime:
  domain_graph_mtime:
repository:
  head:
freshness:
  status: FRESH | STALE | VERY_STALE | UNKNOWN
  diff_method:
  changed_file_count:
  changed_files:
  changed_files_truncated:
health:
  status: HEALTHY | DEGRADED | INVALID
  node_count:
  edge_count:
  domain_node_count:
  domain_edge_count:
  duplicate_node_ids:
  dangling_edge_count:
  missing_source_count:
  unknown_relation_count:
warnings: []
```

## 10.4 Preserve `get_graph_stats`

Do not break existing human tool.

Implementation:

```text
get_graph_stats
→ formats get_graph_metadata + statistics as text
```

One internal source of truth.

## 10.5 Structured error envelope

All new structured APIs return:

```yaml
ok: true|false
error:
  code:
  message:
  remediation:
```

Do not return a string starting with `Error:` as the only machine signal.

## Tests

- Contract schema validates.
- Contract tool list matches registered tools.
- `get_graph_metadata` returns HEAD.
- Missing meta returns UNKNOWN, not crash.
- Missing domain graph is represented.
- Changed files truncation works.
- Invalid project returns structured error.
- Existing text tools unchanged.

## Exit

Maika can discover UA capabilities without a manually hard-coded tool list.

---

# 11. Phase 3 — UA-MCP Graph Health & Trustworthiness

## 11.1 Load validation

Detect:

```text
duplicate node IDs
duplicate domain node IDs
dangling code edges
dangling domain edges
empty node IDs
empty relation types
source paths outside project root
missing source files
invalid layer references
invalid domain flow references
```

## 11.2 Health severity

```yaml
health:
  status: HEALTHY | DEGRADED | INVALID

rules:
  duplicate node ID: INVALID
  path escape: INVALID
  malformed graph: INVALID
  high dangling-edge ratio: DEGRADED or INVALID
  missing domain graph: DEGRADED for domain capability only
  missing source file: DEGRADED
```

## 11.3 Capability applicability

```yaml
applicability:
  architecture_discovery: available
  domain_flow_trace: unavailable | degraded | available
  call_chain_trace: available
  impact_analysis: available
```

## 11.4 Path safety

Before source read:

```text
normalize node file path
resolve against project root
reject absolute path outside root
reject ..
reject NUL
reject symlink escape
```

## 11.5 Edge provenance

Structured traversal edge:

```yaml
source:
target:
relation:
origin: direct | inherited_from_file | domain_cross_ref
confidence: high | medium | low
source_edge:
```

## Tests

- Malicious graph path escape rejected.
- Symlink escape rejected.
- Duplicate ID invalid.
- Dangling edge appears in health.
- Missing domain graph only degrades domain capability.
- Inherited edges carry origin.
- Direct edge remains high confidence.

---

# 12. Phase 4 — UA-MCP Structured Query API

## 12.1 New internal query layer

Refactor:

```text
kg_loader.py query functions
→ dataclasses/dicts

server.py text tools
→ formatting adapters

structured tools/CLI
→ JSON adapters
```

Avoid duplicate traversal implementations.

## 12.2 Structured operations

Required:

```text
search_nodes_structured
trace_call_chain_structured
find_impact_structured
find_path_structured
get_class_hierarchy_structured
get_domain_flow_structured
get_node_source_structured
```

## 12.3 Common envelope

```yaml
contract_version: 1
ok: true
provider_id: understand-anything
project:
operation:
request:
graph:
  commit:
  repository_head:
  freshness:
  health:
result:
warnings:
limits:
  requested_depth:
  effective_depth:
  visited_nodes:
  truncated:
```

## 12.4 Anchor result

```yaml
anchors:
  - node_id:
    node_type:
    name:
    file_path:
    layer:
    score:
```

## 12.5 Traversal result

```yaml
nodes:
  - node_id:
    type:
    file_path:

edges:
  - source:
    target:
    relation:
    origin:
    confidence:

paths:
  - node_ids:
    relation_types:

limits:
  truncated:
  reason:
```

## 12.6 Source result

```yaml
node_id:
file_path:
resolved_path:
symbol:
line_start:
line_end:
file_sha256:
source_sha256:
content:
repository_head:
```

## 12.7 CLI adapter

Add:

```bash
ua-mcp contract --json
ua-mcp metadata --project X --json
ua-mcp search --project X --query Y --json
ua-mcp trace-call --project X --node ID --depth 4 --json
ua-mcp impact --project X --node ID --json
ua-mcp domain-flow --project X --flow ID --json
ua-mcp source --project X --node ID --json
```

Update:

```toml
[project.scripts]
kg-mcp = "server:main"
ua-mcp = "cli:main"
```

The CLI and MCP must use the same core engine.

## Tests

- CLI/MCP structured output parity.
- JSON schemas validate.
- Depth/truncation recorded.
- Source hash deterministic.
- Project selection deterministic.
- Stable error codes.

---

# 13. Phase 5 — Pin UA Contract in Maika

## New files

```text
.maika/contracts/ua-mcp/v1/contract.json
.maika/contracts/ua-mcp/v1/result-envelope.schema.json
.maika/contracts/ua-mcp/v1/graph-metadata.schema.json
.maika/contracts/ua-mcp/v1/trace-result.schema.json
```

## Contract update command

Developer-only:

```bash
python scripts/update_provider_contract.py \
  --provider understand-anything \
  --from /path/to/Understand-Anything-MCP
```

Must:

```text
read exported contract
validate version
show diff
require --apply
```

Normal CI never downloads latest from network.

## Compatibility validator

```bash
maika content validate-provider-contracts
```

Checks:

```text
provider registry contract version
↔ vendored contract
↔ provider-capability mapping
↔ adapter operations
```

## Mutation tests

- Missing tool fails.
- Unknown tool fails.
- Unsupported contract fails.
- Wrong provider ID fails.

---

# 14. Phase 6 — Maika UA Provider Adapter

## New package

```text
cli/providers/
├── __init__.py
├── identity.py
├── contracts.py
├── ua_mcp.py
└── models.py
```

## Responsibilities

```text
resolve provider
locate UA-MCP
probe contract
validate compatibility
probe metadata
execute structured query
validate JSON
normalize paths
apply timeout
return typed result
```

## Invocation

```python
[
  "uv",
  "--directory", ua_mcp_dir,
  "run", "ua-mcp",
  "trace-call",
  ...
]
```

Never shell strings.

## Safety

- canonicalize UA-MCP directory;
- reject missing executable/project;
- timeout;
- process group cleanup;
- output size limit;
- stdout JSON only;
- stderr diagnostics only.

## Health states

```yaml
configured:
contract_compatible:
server_version:
graph_loaded:
graph_health:
freshness:
capability_applicability:
ready:
```

## Doctor integration

Distinguish:

```text
configured
server reachable
contract compatible
project loaded
graph healthy
graph fresh
```

## Bootstrap integration

```yaml
provider_id: understand-anything
status: healthy | degraded | unavailable | incompatible
contract_version:
server_version:
project:
graph_commit:
repository_head:
freshness:
health:
applicable_capabilities:
```

---

# 15. Phase 7 — Trace Request Contract

## New schema

```text
.maika/config/trace-request.schema.yaml
```

## Artifact

```text
changes/<id>/exploration/TRACE_REQUEST.yaml
```

## Example

```yaml
version: 1
change_id: C-123
repository_head: abc123

questions:
  - id: Q-FLOW-001
    statement: Trace payment approval from controller to final event publication.

    required_capabilities:
      - call_chain_trace
      - impact_analysis

    optional_capabilities:
      - domain_flow_trace

    provider_policy:
      primary: understand-anything
      semantic_support: codebase-memory-mcp

    project:
      name: vietbank-sme-omni

    anchor_strategy:
      query: PaymentApproval
      allowed_node_types: [class, function, file]

    trace:
      direction: downstream
      depth: 6
      relation_types: [calls, triggers, contains, implements]

    freshness:
      minimum: scoped_fresh

    source_verification:
      required: true
      material_only: true

    cbm_triggers:
      - unresolved_anchor
      - graph_gap
      - relevant_stale_files
      - hidden_consumer_risk
```

## Gate

Validate:

- unique questions;
- known capabilities;
- explicit project;
- bounded depth;
- known relations;
- known freshness;
- known CBM triggers.

---

# 16. Phase 8 — Trace Evidence Contract

## New schema

```text
.maika/config/trace-evidence.schema.yaml
```

## Artifact

```text
changes/<id>/exploration/TRACE_EVIDENCE.yaml
```

## Example

```yaml
version: 1
change_id: C-123
repository_head: abc123

traces:
  - trace_id: TR-001
    question_id: Q-FLOW-001

    primary:
      provider_id: understand-anything
      contract_version: 1
      capability: call_chain_trace
      project: vietbank-sme-omni

      graph:
        commit: old123
        repository_head: abc123
        freshness: STALE
        relevant_stale_files: []
        health: HEALTHY

      anchors:
        - node_id: class:PaymentApprovalService
          node_type: class
          file_path: src/.../PaymentApprovalService.java

      traversals:
        - operation: trace_call_chain
          direction: downstream
          depth: 6
          truncated: false
          nodes: []
          edges: []

    support:
      invoked: false
      calls: []

    source_verifications:
      - claim_id: CLAIM-001
        file_path: src/.../PaymentApprovalService.java
        symbol: approve
        file_sha256:
        line_start:
        line_end:
        observed:
        verdict: verified

    limitations: []
    confidence: high
```

## CBM support record

```yaml
support:
  invoked: true
  calls:
    - provider_id: codebase-memory-mcp
      capability: semantic_code_search
      reason: hidden_consumer_risk
      query:
      evidence_refs:
      result_count:
```

## Provider-neutral gate

Checks:

```text
required capability satisfied
primary provider correct or justified
freshness sufficient
trace complete enough
source verification present
CBM reason valid when invoked
CBM not required without trigger
```

## Authority

Add:

```yaml
trace_request:
  source: changes/<change-id>/exploration/TRACE_REQUEST.yaml

trace_evidence:
  source: changes/<change-id>/exploration/TRACE_EVIDENCE.yaml
```

---

# 17. Phase 9 — Migrate Gates Away from CBM-specific Logic

## Remove/deprecate

```text
node_id + blast-radius mandatory
trace via cbm
UA evidence regex as primary contract
KG unavailable prose regex as primary contract
```

## New validators

```python
validate_trace_request(...)
validate_trace_evidence(...)
validate_capability_satisfaction(...)
validate_source_verification(...)
validate_support_trigger(...)
validate_scoped_freshness(...)
```

## Compatibility window

```text
TRACE_EVIDENCE exists
→ new gate

missing
→ legacy gate + warning
```

Every compatibility entry gets owner and expiry.

## Negative tests

- UA complete, no CBM → pass.
- CBM absent, UA fresh + source verified → pass.
- CBM without reason → fail.
- Relevant stale without fallback → fail.
- Fabricated node → fail.
- Truncated trace claimed complete → fail.
- Exact claim without source hash → fail.

## Exit

No active critical gate privileges CBM by provider name.

---

# 18. Phase 10 — Typed Conditional Capabilities

## Extend skill schema

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
        - graph_gap
        - relevant_stale_files
        - hidden_consumer_risk
        - reviewer_counter_evidence

    impact_analysis:
      triggers:
        - blast_radius_required
```

## Validator

- known triggers;
- no required/conditional duplication;
- one-of resolves;
- activated trigger recorded;
- conditional call has reason;
- required capability not skipped.

## Grounding target

Required:

```text
exact source
one appropriate structured trace
historical/business/convention as applicable
```

Conditional:

```text
semantic search
impact analysis
domain trace
call trace
```

depending on question.

## Reviewer target

Required:

```text
exact source
review dispatch
runtime verification
```

Conditional:

```text
semantic counter-evidence
call/impact retrace
historical recall
```

---

# 19. Phase 11 — Deterministic Trace Execution

## Preferred flow

```text
compile trace request
→ Maika UA adapter executes
→ TRACE_EVIDENCE.yaml
→ worker receives pinned evidence
→ worker writes grounding
```

Worker should not be solely responsible for discovering provider/tool/freshness.

## Prompt binding

```text
SKILL_FILE
SKILL_SHA256
PROVIDER_POLICY_FILE
PROVIDER_POLICY_SHA256
TRACE_REQUEST_FILE
TRACE_REQUEST_SHA256
TRACE_EVIDENCE_FILE
TRACE_EVIDENCE_SHA256
```

## Context package

```yaml
provider_context:
  primary_provider:
  contract_version:
  graph_commit:
  repository_head:
  freshness:
trace_evidence_ids:
```

## Delegated fallback

If direct adapter unavailable:

```text
host agent calls MCP
→ writes same trace evidence schema
→ assurance=delegated
→ degradation recorded
```

---

# 20. Phase 12 — Refresh Workflow Lifecycle

## Canonical request path

```text
changes/<id>/generated/requests/EXTERNAL_WORKFLOW_REQUEST.<role>.yaml
```

## Schema

```yaml
version: 1
request_type: external_workflow
workflow: understand
provider_id: understand-anything
reason:
required_for:
observed:
  graph_commit:
  repository_head:
  freshness:
  relevant_stale_files:
affected_claims:
resume:
  role:
  state:
status: requested
```

## Orchestrator

```text
validate
→ persist in STATE
→ transition BLOCKED
→ show remediation
```

## User executes

```text
/understand
```

## Verify

```bash
maika provider refresh-status \
  --provider understand-anything \
  --change-id C-123
```

Probe:

```text
graph mtime
graph commit
HEAD
health
contract
```

## Acknowledge

```bash
maika provider acknowledge-refresh \
  --provider understand-anything \
  --change-id C-123
```

Refuse if graph unchanged.

Optional explicit:

```bash
--accept-degraded-fallback
```

## Resume

```text
request fulfilled
→ resume original state/role
→ rerun trace
```

Do not delete request history. Use statuses:

```text
requested
fulfilled
superseded
cancelled
```

---

# 21. Phase 13 — Mechanical Source Verification

## Artifact

Embedded in trace evidence or:

```text
exploration/SOURCE_VERIFICATION.yaml
```

## Fields

```yaml
claim_id:
file_path:
symbol:
line_start:
line_end:
repository_head:
file_sha256:
observed:
verification_method:
verdict:
```

## Rules

- path under repo root;
- file exists at current snapshot;
- hash computed by Maika;
- exact material claim has symbol/range;
- deletion uses explicit absence verification;
- dirty worktree represented;
- graph/source mismatch becomes conflict.

---

# 22. Phase 14 — System Model Validator

## Command

```bash
maika content validate-system-model
```

## Internal graph

```text
Provider
→ Capability
→ Tool
→ Skill
→ Trace request
→ Evidence
→ Gate
→ Artifact
→ Consumer
→ Ownership
```

## Checks

### Provider

- canonical provider exists;
- setup resolves;
- external workflow owner resolves;
- aliases unique;
- contract present.

### Capability

- skill capability exists;
- primary provider exists;
- conditional trigger exists;
- no policy/gate contradiction.

### Tool

- tool exists in contract;
- structured output supported;
- freshness probe supported.

### Artifact

- producer;
- authority;
- consumer;
- validator;
- ownership;
- update behavior.

### Gate

- evidence producer exists;
- no deprecated provider-specific requirement;
- input authority exists.

## Mutation suite

1. Rename provider in one file.
2. Remove UA tool.
3. Make CBM required.
4. Remove source verification.
5. Remove trace authority.
6. Mark refresh complete without graph change.
7. Remove conditional trigger.
8. Add provider-specific gate.
9. Break workflow owner.
10. Break contract version.

Every mutation must fail.

---

# 23. Phase 15 — Deterministic Behavior Fixtures

Build a fixture project with:

```text
controller
service
repository
event publisher
alternate consumer
inheritance
domain flow
```

Ship source + graph + meta.

## Fixtures

### UA-1 Fresh complete trace

UA primary, no CBM, source verified.

### UA-2 Ambiguous anchor

No silent arbitrary selection; CBM may support.

### UA-3 Graph gap

UA partial; CBM reason=graph_gap.

### UA-4 Hidden consumer

Impact + CBM counter-search.

### UA-5 Stale unrelated

UA remains primary.

### UA-6 Stale relevant

UA navigation only; current trace required.

### UA-7 Very stale

Refresh request.

### UA-8 Missing domain graph

Domain unavailable; code trace usable.

### UA-9 Invalid graph

Provider invalid; safe fallback.

### UA-10 Inherited edge

Origin preserved; source verification required.

### UA-11 Truncated trace

Cannot claim complete flow.

### UA-12 Source changed after graph

Source wins, conflict recorded.

### UA-13 Refresh lifecycle

BLOCKED → refresh → reprobe → resume.

### UA-14 Alias normalization

Alias resolves canonical ID.

### UA-15 CBM unavailable

Complete UA path still passes without trigger.

---

# 24. Phase 16 — Real-host Qualification

Hosts:

```text
Claude Code
Codex
Antigravity/Agy
```

Journeys:

```text
H1 fresh approval trace
H2 ambiguous semantic query
H3 relevant stale graph
H4 /understand-chat report without task
H5 /understand refresh and resume
```

Record:

```yaml
host:
model:
maika_commit:
ua_mcp_version:
contract_version:
journey:
provider_calls:
files_created:
task_state:
trace_evidence:
cbm_reason:
source_verification:
verdict:
```

Thresholds:

```text
route consistency 100%
UA primary ≥95%
unnecessary CBM ≤5%
source verification 100%
refresh success 100%
```

---

# 25. Phase 17 — Remove Compatibility Debt

## `dependency_analysis`

### Release N

Supported as compatibility aggregate, warning in new skills.

### N+1

Canonical skill usage fails lint.

### N+2

Remove legacy CBM-specific gates and regex.

Every compatibility record:

```yaml
owner:
introduced_at:
expires_at:
replacement:
```

---

# 26. PR sequence

## UA-MCP

### U1 — Contract and metadata

- contract v1;
- `get_capabilities`;
- `get_graph_metadata`;
- tests.

### U2 — Health and path safety

- graph health;
- applicability;
- containment;
- edge provenance;
- tests.

### U3 — Structured query layer

- typed operations;
- source hash;
- truncation;
- tests.

### U4 — CLI and v0.2.0

- `ua-mcp` CLI;
- schemas;
- version bump;
- release.

## Maika

### M1 — Provider identity

- registry;
- normalizer;
- cross-surface checks.

### M2 — Contract pinning

- vendored v1 contract;
- compatibility validator;
- remove hard-coded tools.

### M3 — UA adapter

- structured invocation;
- real doctor/bootstrap probe.

### M4 — Trace request/evidence

- schemas;
- artifacts;
- authority;
- validators.

### M5 — Gate migration

- provider-neutral gates;
- negative tests.

### M6 — Conditional capabilities

- schema/lint;
- skill migration.

### M7 — Deterministic execution

- pre-worker trace;
- pinned evidence.

### M8 — Refresh lifecycle

- request;
- BLOCKED;
- verify;
- resume.

### M9 — System validator

- contract graph;
- mutation suite.

### Q1 — Joint qualification

- UA-1..UA-15;
- H1..H5.

### M10 — Closure

- remove legacy;
- closure report.

---

# 27. File-level map

## UA-MCP new

```text
contracts/ua-mcp-contract-v1.json
contracts/ua-mcp-contract-v1.schema.json
contracts/graph-metadata-v1.schema.json
contracts/trace-result-v1.schema.json
structured_api.py
cli.py
graph_health.py
schemas.py
tests/test_contract.py
tests/test_graph_metadata.py
tests/test_graph_health.py
tests/test_structured_api.py
tests/test_cli.py
tests/test_path_safety.py
```

## UA-MCP modify

```text
server.py
kg_loader.py
pyproject.toml
README.md
```

## Maika new

```text
.maika/config/provider-registry.yaml
.maika/config/trace-request.schema.yaml
.maika/config/trace-evidence.schema.yaml
.maika/config/graph-freshness-policy.yaml
.maika/contracts/ua-mcp/v1/*
cli/providers/__init__.py
cli/providers/identity.py
cli/providers/contracts.py
cli/providers/ua_mcp.py
cli/providers/models.py
cli/agent_content/system_model.py
cli/commands/provider.py
cli/tests/test_provider_identity.py
cli/tests/test_provider_contracts.py
cli/tests/test_ua_adapter.py
cli/tests/test_trace_request.py
cli/tests/test_trace_evidence.py
cli/tests/test_system_model.py
cli/tests/test_refresh_lifecycle.py
cli/tests/test_ua_behavior_fixtures.py
```

## Maika modify

```text
cli/plugin-manifest.yaml
.maika/profiles/capability-registry.yaml
.maika/profiles/provider-capabilities.yaml
.maika/config/artifact-authority.yaml
.maika/config/external-workflows.yaml
.maika/rules/jit/providers.md
.maika/skills/grounding-explorer/SKILL.md
.maika/skills/reviewing-task/SKILL.md
.maika/skills/reviewing-change/SKILL.md
.maika/skills/writing-plan/SKILL.md
.maika/procedures/dispatch-kernel.md
.maika/tools/gate-check/gates.py
.maika/tools/microloop-orchestrator/vnext_dispatch.py
.maika/tools/microloop-orchestrator/orchestrator.py
cli/commands/bootstrap.py
cli/commands/content.py
cli/maika.py
scripts/run_ci.py
.github/workflows/ci.yml
```

---

# 28. CI matrix

## UA-MCP

```text
unit
contract schema
structured parity
path safety
package build
CLI smoke
MCP registration smoke
```

## Maika

```text
provider model
provider contract
system model
skill contracts
trace schemas
legacy provider-specific scan
mutation suite
artifact audit
UA adapter fixtures
refresh lifecycle
worker binding
Windows
Ubuntu
Linux E2E
PowerShell E2E
```

Normal CI must not download network latest.

---

# 29. Rollback

## UA-MCP

Structured tools are additive.

Rollback to old text tools remains possible.

## Maika feature flag

```yaml
providers:
  understand-anything:
    trace_mode: structured_v1 | delegated_legacy
```

Rollout:

```text
legacy default
→ structured shadow
→ structured opt-in
→ structured default
→ legacy removal
```

## Shadow comparison

Compare:

```text
anchors
paths
source facts
freshness
CBM calls
```

No production decision from shadow trace.

---

# 30. Metrics

```text
ua_primary_selection_rate
cbm_support_activation_rate
unnecessary_cbm_rate
anchor_resolution_accuracy
trace_truncation_rate
source_verification_rate
graph_source_conflict_rate
refresh_request_rate
refresh_resume_success_rate
contract_mismatch_count
provider_id_drift_count
cross_host_consistency
```

Targets:

```text
UA primary ≥95%
unnecessary CBM ≤5%
source verification 100%
contract mismatch 0
provider-ID drift 0
refresh success 100%
```

---

# 31. Acceptance criteria

## Identity

1. Canonical ID `understand-anything`.
2. Aliases normalize.
3. Internal artifacts use canonical ID.
4. Manifest resolves provider.
5. Bootstrap/doctor resolve provider.
6. External workflow owner resolves.
7. Mutation fails CI.

## Contract

8. Contract version exported.
9. Server version exported.
10. Tool list machine-readable.
11. Result schemas versioned.
12. Maika pins support.
13. Incompatible contract fails closed.
14. Old tools remain compatible.

## Metadata/health

15. HEAD returned.
16. Graph commit returned.
17. Freshness structured.
18. Changed-file truncation known.
19. Health structured.
20. Applicability structured.
21. Missing domain represented.
22. Invalid graph represented.

## Trust

23. Duplicate ID rejected.
24. Dangling edges counted.
25. Path escape rejected.
26. Symlink escape rejected.
27. Missing source recorded.
28. Edge origin recorded.
29. Inherited edge distinguished.

## Trace

30. Typed anchors.
31. Typed nodes/edges.
32. Depth/direction recorded.
33. Truncation recorded.
34. Domain ordered steps.
35. Source SHA.
36. Stable error envelope.
37. CLI/MCP parity.

## Adapter

38. argv only.
39. timeout.
40. JSON validation.
41. contract validation.
42. stderr separated.
43. ambiguity detected.
44. invalid graph detected.
45. real provider probe.

## Evidence

46. Request valid.
47. Evidence valid.
48. Provider-neutral capability check.
49. Source verification.
50. Graph commit/HEAD.
51. Freshness.
52. anchors/relations.
53. truncation.
54. limitations/confidence.

## CBM

55. Not globally required.
56. Trigger required.
57. Reason required.
58. Complete UA path passes alone.
59. Graph gap activates support.
60. Reviewer corroboration supported.
61. CBM unavailable does not block irrelevant path.

## Gates

62. No active critical CBM-name gate.
63. No “trace via CBM” invariant.
64. Source verification enforced.
65. Stale relevant enforced.
66. Very stale blocked for material decisions.
67. Truncation blocks completeness.
68. Legacy expiry declared.

## Worker/refresh

69. Skill/provider/request/evidence hashes pinned.
70. Worker cannot silently refresh.
71. Canonical request path.
72. State BLOCKED.
73. Lifecycle persisted.
74. Resume revalidates.
75. Unchanged graph cannot be acknowledged.
76. Degraded fallback explicit.

## System/behavior

77. No dangling provider.
78. Every capability has provider.
79. Tool exists in contract.
80. Artifact producer/authority/consumer/validator/ownership.
81. Mutation suite catches drift.
82. UA-1..UA-15 pass.
83. H1..H5 pass on three hosts.
84. Thresholds met.
85. No Critical/High finding.
86. Full CI green.
87. Repository clean.
88. Closure report committed.

---

# 32. Definition of Done

Không đóng initiative cho đến khi:

```text
provider ID thống nhất
UA-MCP có machine contract
Maika dùng structured adapter
trace có typed request/evidence
source verification mechanical
CBM conditional thật sự
gate provider-neutral
refresh lifecycle complete
system validator chống drift
fixtures và real-host dogfood pass
legacy path bị loại bỏ
```

---

# 33. Codex execution protocol

Mỗi slice:

```text
inspect
→ inventory
→ implement one PR
→ targeted tests
→ full CI
→ git diff --check
→ verify clean generated state
→ report
```

Không được:

- gộp toàn bộ initiative;
- break public UA tools;
- hard-code tool list mới trong Maika;
- dùng regex parse text làm integration chính;
- giữ CBM mandatory;
- claim refresh chưa probe;
- claim real-host khi chỉ fake;
- bỏ Windows CI;
- merge đỏ.

Report:

```yaml
repository:
slice:
base_commit:
commit:
contract_changes:
behavior_changes:
files_changed:
tests:
ci:
known_gaps:
rollback:
next_slice:
```

---

# 34. Codex kickoff prompt

```text
Implement the Maika × Understand-Anything Convergence & Closure Plan.

Repositories:
- VIethoangnguyenle/Understand-Anything-MCP, branch main
- VIethoangnguyenle/Maika, branch master-v2

Start with Phase 0 only. Produce docs/plans/ua-convergence-inventory.md
before changing code.

Core decisions:
1. Canonical provider ID is understand-anything.
2. UA-MCP is primary for structured graph trace.
3. CBM is conditional semantic/gap/counter-evidence support.
4. Current source is authoritative for exact facts.
5. Maika gates validate capability/evidence, not provider prose.
6. Task grounding consumes structured UA evidence.
7. Graph refresh is parent-controlled and re-probed.
8. Existing text MCP tools remain backward compatible.
9. Every PR slice ends with targeted tests, full CI and git diff --check.
10. Do not combine the initiative into one PR.

Follow U1→U4, then M1→M10.
```

---

# 35. Closure statement

Khi hoàn thành, Maika không còn “hy vọng agent dùng Understand-Anything đúng”.

Nó có bằng chứng cơ học rằng:

```text
provider được resolve đúng
graph đủ khỏe
trace đúng capability
freshness đúng scope
CBM chỉ chạy khi có trigger
source hiện tại đã xác minh
gate kiểm đúng evidence
worker không tự refresh
task resume đúng lifecycle
```

Understand-Anything khi đó là một subsystem có:

```text
contract
health
evidence
lifecycle
qualification
```

chứ không còn chỉ là một provider recommendation trong prose.
