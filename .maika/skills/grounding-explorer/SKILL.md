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
  - architecture_discovery
  - dependency_analysis
  - exact_source_inspection
  - historical_context_retrieval
  - business_knowledge_retrieval
  - convention_retrieval
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
- Ai own contract? Blast radius tới đâu? (dependency_analysis)
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
Capability IDs: `architecture_discovery`, `exact_source_inspection`,
  `dependency_analysis`, `historical_context_retrieval`,
  `business_knowledge_retrieval`, `convention_retrieval`,
  `database_schema_inspection`, `runtime_verification`.
Provider ưu tiên theo `jit/providers.md`; skill chỉ gọi capability, không gọi provider.

## Quy trình truy xuất
1. Đọc `QUERY_PLAN.yaml`; mỗi câu hỏi → resolve capability từ required_evidence_types.
2. Probe provider → ghi `TOOL_HEALTH.yaml` (probe thật, observed, freshness).
3. UA cho kiến trúc/domain; CBM cho dependency/blast radius; source verify exact fact;
   Agent Memory cho lịch sử; dispatch `database-explorer` khi cần DB.
4. Ghi claim + provenance vào `EVIDENCE_MANIFEST.yaml`.
5. Ghi conflict vào `CONFLICTS.yaml`; ghi coverage vào `COVERAGE.yaml`.

## Thứ tự authority và precedence
live DB state > current source > business contract hiện hành > fresh graph >
durable knowledge > historical memory > inference (xem `core/evidence.md` R-Know-2).

## Kết quả bắt buộc
- 3 lens `codebase/business/conventions` không rỗng.
- Mọi câu hỏi query-plan: answered hoặc blocked-có-lý-do.
- Preferred provider khỏe không bị skip im lặng (hoặc có degradation record).

## Bất biến
- Source authoritative cho exact code fact; graph/memory hỗ trợ, không thay thế.
- Mọi inference được gắn nhãn. Không thiết kế giải pháp cuối.

## Yêu cầu evidence
Verified code claim cần file + symbol + file_hash (sha256). Business claim cần source
hoặc status `inferred`. Convention claim cite rule ID/example/approved entry.

## Freshness và confidence
Graph ghi `indexed_commit`; lệch HEAD → stale → degrade. Confidence high chỉ khi ≥2
nguồn độc lập + verify bằng source (R-Know-5).

## Quy trình degradation
Provider stale/absent → ghi degradation record có cấu trúc (provider, probe, observed,
freshness, fallback, missing evidence, confidence impact) vào `TOOL_HEALTH.yaml`.
Không degrade lặng lẽ.

## Quy trình
1. Chạy Quy trình truy xuất ở trên.
2. Reconcile sơ bộ; đánh dấu conflict material.
3. Chạy gate `query-plan`, `tool-health`, `exploration-evidence`, `conflicts`, `coverage`.
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
