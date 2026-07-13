---
name: grounding-explorer
version: '3.0'
description: 'Dùng khi một change hạng standard/architectural cần thu thập bằng chứng
  trước thiết kế: điều phối truy xuất đa nguồn (kiến trúc, dependency, source, lịch
  sử, DB, convention), ghi evidence có provenance, phát hiện conflict và trả readiness.'
routing:
  mode: workflow
  actions:
  - explore
  states:
  - INTAKE
  classes:
  - standard
  - architectural
capabilities:
  required:
  - exact_source_inspection
  - historical_context_retrieval
  - business_knowledge_retrieval
  - convention_retrieval
  one_of:
    structured_trace:
    - architecture_discovery
    - domain_flow_trace
    - call_chain_trace
  conditional:
    impact_analysis:
      triggers:
      - blast_radius_required
    semantic_code_search:
      triggers:
      - unresolved_anchor
      - ambiguous_semantic_query
      - graph_gap
      - relevant_graph_stale
      - hidden_consumer_risk
      - ua_unavailable
    dependency_analysis:
      triggers:
      - graph_gap
      - ua_unavailable
    database_schema_inspection:
      triggers:
      - persistence_change
    database_dependency_analysis:
      triggers:
      - database_dependency_risk
outputs:
  required:
  - exploration/GROUNDING.yaml
  - exploration/EVIDENCE_MANIFEST.yaml
  - exploration/TOOL_HEALTH.yaml
  - exploration/CONFLICTS.yaml
  - exploration/COVERAGE.yaml
  optional:
  - exploration/QUERY_PLAN.yaml
  - exploration/DATABASE_CONTEXT.yaml
gates:
- query-plan
- tool-health
- exploration-evidence
- coverage
---
# Grounding Explorer

## Mục tiêu
Là trung tâm điều phối truy xuất của Maika: biến `QUERY_PLAN.yaml` thành gói
grounding thật (`GROUNDING.yaml` + `EVIDENCE_MANIFEST.yaml` + `TOOL_HEALTH.yaml`
+ `CONFLICTS.yaml` + `COVERAGE.yaml`), evidence có provenance và readiness verdict.

## Khi nào sử dụng
Dùng khi `intent-analysis` phân loại change là standard hoặc architectural, hoặc
khi planner báo thiếu evidence (targeted re-grounding).

## Khi nào KHÔNG sử dụng
- Change trivial/small không cần gói grounding đầy đủ.
- Khi chưa có `QUERY_PLAN.yaml` (chạy intent-analysis trước).
- Để thiết kế giải pháp cuối — đó là brainstorming/spec.

## Đầu vào
- `CHANGE.yaml`, `INTENT.md`, `exploration/QUERY_PLAN.yaml`.
- Current repository source (authority cho exact code fact).
- Durable knowledge trong `knowledge/long-term/`.

## Câu hỏi tri thức
- Flow hiện tại lắp ráp ở đâu? (architecture_discovery, exact_source_inspection)
- Ai own contract? Call chain và blast radius tới đâu? (call_chain_trace, impact_analysis)
- Change này từng gây incident chưa? (historical_context_retrieval)
- Business rule/convention nào áp? (business_knowledge_retrieval, convention_retrieval)
- DB object nào tham gia? (database_schema_inspection)

## Loại evidence bắt buộc
- `architecture_node`, `relationship_edge` (kiến trúc).
- `dependency_path`, `blast_radius` (phụ thuộc).
- `file_symbol`, `exact_code_fact` (source — bắt buộc verify).
- `incident_reference` (lịch sử; zero-result hợp lệ).
- `convention_rule`, `author_dna_rule`; `database_object` (khi persistence-sensitive).

## Chính sách capability
Required: `exact_source_inspection`, `historical_context_retrieval`,
  `business_knowledge_retrieval`, `convention_retrieval`.
One-of `structured_trace` (thoả ≥1 khi graph áp dụng được): `architecture_discovery`,
  `domain_flow_trace`, `call_chain_trace`.
Conditional — chỉ gọi khi trigger kích hoạt, ghi trigger + reason vào `support_calls`:
  `impact_analysis` (blast_radius_required); `semantic_code_search` (unresolved_anchor,
  ambiguous_semantic_query, graph_gap, relevant_graph_stale, hidden_consumer_risk,
  ua_unavailable); `dependency_analysis` (graph_gap, ua_unavailable);
  `database_schema_inspection` (persistence_change); `database_dependency_analysis`
  (database_dependency_risk).
Trigger kích hoạt mà không có provider call/zero-result/degradation record = invalid;
conditional call không có trigger = invalid (plan §8).
Provider ưu tiên theo `jit/providers.md`; skill chỉ gọi capability, không gọi provider.

## Quy trình truy xuất
1. Đọc `QUERY_PLAN.yaml`; mỗi câu hỏi → resolve capability từ required_evidence_types.
2. Compile trace request (orchestrator, không tự viết):
   `orchestrator.py vnext-compile-trace-request --workspace <ws> --repo-root <root>`
   → `exploration/TRACE_REQUEST.yaml`.
3. Probe structured graph project + freshness; ghi observed graph commit và HEAD vào
   `TOOL_HEALTH.yaml`. Mỗi MCP call (probe lẫn traversal) phải record qua
   `maika provider record --provider <id> --tool <t> --request-file <req> --response-file <res>`
   — record tạo hash + provider observation trong `TRACE_EVIDENCE.yaml`.
4. Chọn domain-graph hoặc code-graph entry strategy và resolve anchor nodes.
5. Traverse domain flow, relationships, call chain hoặc impact bằng precise trace
   capability; lấy node source cho material nodes. Viết traversal vào
   `TRACE_EVIDENCE.yaml` tham chiếu response hash của observation tương ứng.
6. Chỉ gọi `semantic_code_search` khi một trigger conditional kích hoạt; record call
   với `--trigger <trigger> --reason "<why>"` (support call thiếu trigger/reason bị
   gate từ chối).
7. Verify exact material facts bằng
   `maika provider verify-source --file <path> --symbol <symbol>` — Maika tự hash,
   gate re-verify (không tự viết sha256).
8. Ghi claim + provenance vào `EVIDENCE_MANIFEST.yaml`; ghi conflict và coverage.

## Thứ tự authority và precedence
live DB state > current source > business contract hiện hành > fresh graph >
durable knowledge > historical memory > inference (xem `core/evidence.md` R-Know-2).

## Kết quả bắt buộc
- 3 lens `codebase/business/conventions` không rỗng.
- Mọi câu hỏi query-plan: answered hoặc blocked-có-lý-do.
- Preferred provider khỏe không bị skip im lặng (hoặc có degradation record).
- `GROUNDING.yaml` có structured trace contract:

```yaml
graph_trace:
  provider:
  project:
  graph_commit:
  repository_head:
  freshness:
  relevant_stale_files: []
  anchor_nodes: []
  traversals: []
  support_calls: []
  source_verifications: []
```

Mỗi traversal ghi node IDs + relationship types; mỗi support call ghi capability + reason.

## Bất biến
- Source authoritative cho exact code fact; graph/memory hỗ trợ, không thay thế.
- Mọi inference được gắn nhãn. Không thiết kế giải pháp cuối.

## Yêu cầu evidence
Verified code claim cần file + symbol + file_hash (sha256). Business claim cần source
hoặc status `inferred`. Convention claim cite rule ID/example/approved entry.

## Freshness và confidence
Graph ghi `indexed_commit`; phân biệt stale file liên quan và không liên quan theo
provider doctrine. Relevant stale làm giảm confidence; very-stale graph chỉ làm anchor.
Confidence high chỉ khi ≥2 nguồn độc lập + verify bằng source (R-Know-5).

## Quy trình degradation
Provider stale/absent → ghi degradation record có cấu trúc (provider, probe, observed,
freshness, fallback, missing evidence, confidence impact) vào `TOOL_HEALTH.yaml`.
Không degrade lặng lẽ.

Schema gate-checked (`providers` là **map** theo tên provider; status chỉ nhận
`ready | degraded | unavailable | unsupported`):

```yaml
# TOOL_HEALTH.yaml (schema example — gate `tool-health`)
version: 1
change_id: C-123
providers:
  understand-anything:
    status: ready
    probe:
      operation: get_graph_metadata
      observed: "1799 nodes / 2854 edges, graph_commit a14930e"
    freshness: FRESH
  codebase-memory-mcp:
    status: unavailable
    degradation:
      probe_ran: true
      error: "no index for this project"
      fallback_used: current_source
      missing_evidence: "semantic corroboration"
      confidence_impact: "medium"
```

```yaml
# QUERY_PLAN.yaml (schema example — gate `query-plan`)
version: 1
change_id: C-123
questions:
  - id: Q-CODE-001
    question: "Where is the approve flow assembled?"
    required_capabilities: [exact_source_inspection]
    required_evidence_types: [exact_code_fact]
```

## Quy trình
1. Chạy Quy trình truy xuất ở trên.
2. Reconcile sơ bộ; đánh dấu conflict material.
3. Chạy gate `query-plan`, `tool-health`, `exploration-evidence`, `conflicts`, `coverage`.
   Gate `exploration-evidence` nhận `GROUNDING.yaml` làm file chính và
   `--against exploration/EVIDENCE_MANIFEST.yaml`.
4. Trả readiness verdict (READY / NEEDS_CONTEXT / BLOCKED).

## Điều kiện dừng
- Một lens bắt buộc rỗng.
- Conflict material chưa resolve.
- Tool health chặn exact source inspection.
- Phát hiện quyết định chỉ user/BA chốt (public contract/business).

## Tác động lên knowledge
Ghi evidence + conflict mới; đánh dấu stale claim. Không promote (promotion ở
`knowledge-promoter` sau verified completion).

## Đầu ra
`exploration/GROUNDING.yaml`, `EVIDENCE_MANIFEST.yaml`, `TOOL_HEALTH.yaml`,
`CONFLICTS.yaml`, `COVERAGE.yaml` + readiness verdict.

## Handoff tiếp theo
`architecture-reconciler`.
