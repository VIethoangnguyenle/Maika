# jit/providers.md — Provider Doctrine (JIT)

> JIT rule — load khi: grounding/exploration, planning, review, hoặc change
> chạm persistence (DB doctrine nằm ở đây).
> Định nghĩa **provider doctrine**: capability nào ưu tiên provider nào, khi nào
> BẮT BUỘC dùng, cách probe/freshness/degradation, và thẩm quyền của current source.
> Nguyên tắc nền: **provider hỗ trợ suy luận, không ghi đè current source / live DB /
> business contract hiện hành** (xem `core/evidence.md` §Thứ tự thẩm quyền).

---

## 3. Tool Rules — Provider Doctrine

### [CRITICAL] R-Tool-1: Skill dùng capability, không dùng tên provider

- Canonical skill/role contract CHỈ tham chiếu **capability IDs**
  (`profiles/capability-registry.yaml`).
- Concrete provider call cụ thể chỉ nằm ở **platform adapters** (`cli/platforms/*.py`),
  tool docs và capability matrix — không hard-code trong skill.
- Skill-lint từ chối capability ID lạ và tên provider trong canonical skill.

### [CRITICAL] R-Tool-2: Preferred provider — mỗi capability có nguồn ưu tiên

| Capability | Provider ưu tiên | Dùng cho |
|---|---|---|
| `architecture_discovery` | Understand-Anything MCP (UA-MCP) | boundary, domain overview, quan hệ module, tài liệu nội bộ |
| `domain_flow_trace` | UA-MCP | domain overview/detail/flow traversal |
| `call_chain_trace` | UA-MCP | structured call-chain và relationship traversal |
| `impact_analysis` | UA-MCP | structured impact và blast-radius traversal |
| `graph_path_trace` | UA-MCP | path giữa graph nodes |
| `inheritance_trace` | UA-MCP | class hierarchy traversal |
| `symbolic_code_navigation` | Serena | exact symbol identity, declaration, implementation và LSP references |
| `code_diagnostics` | Serena | LSP diagnostics cho file/symbol khi trigger yêu cầu |
| `operational_maintenance` | Serena | bounded language-server recovery; không tạo semantic/diagnostic evidence |
| `semantic_code_search` | Codebase Memory (CBM, conditional) | fuzzy semantic anchor discovery, graph-gap recovery và reviewer counter-evidence |
| `dependency_analysis` | CBM (compatibility aggregate, conditional) | counter-evidence trong lúc consumer migrate; không phải structured trace authority |
| `exact_source_inspection` | **current source** | file, symbol, signature, test, behavior, configuration hiện tại |
| `historical_context_retrieval` | Agent Memory | incident cũ, quyết định trước, rejected approach, review pattern lặp lại |
| `business_knowledge_retrieval` | Agent Memory + tài liệu | tri thức nghiệp vụ, domain, tài liệu |
| `convention_retrieval` | durable knowledge | Author DNA, conventions, rule IDs |
| `database_schema_inspection` | DB Access qua Database Explorer | database, table, column, constraint, collection/schema |
| `database_dependency_analysis` | DB Access constraints + current source | FK metadata và consumer SQL; capability DB không có phải degrade tường minh |

- **UA-MCP là nguồn số 1** cho structured architecture/domain/call/impact/path/
  inheritance trace khi graph áp dụng được. Serena là nguồn số 1 cho quan sát symbol/
  diagnostics theo LSP. CBM sở hữu fuzzy semantic anchor discovery nhưng chỉ được gọi
  có điều kiện cho graph-gap/counter-evidence, không thay structured trace.
  `restart_language_server` thuộc operational maintenance, không thuộc diagnostics,
  không normalize thành semantic evidence và không thỏa evidence coverage.

### [CRITICAL] R-Tool-2A: UA-MCP Primary Structured Trace

Khi Understand-Anything graph healthy, đủ fresh và áp dụng được:

- UA-MCP sở hữu toàn bộ surface **18 tools**: `list_projects`, `get_graph_stats`,
  `get_graph_metadata`, `get_tour`, `query_nodes`, `get_node_detail`,
  `get_node_source`, `get_relationships`, `trace_call_chain`, `get_layer_info`,
  `find_entry_points`, `find_impact`, `find_path`, `get_class_hierarchy`,
  `search_by_file_path`, `get_domain_overview`, `get_domain_detail` và
  `get_domain_flow_detail`. Surface này sở hữu graph/project freshness,
  architecture/domain discovery, relationships, trace, impact, path, hierarchy,
  entry points và node source access.
- `get_node_source` đọc source của một UA node và chỉ là **một trong 18 tools**;
  nó không thu hẹp UA-MCP thành source-only provider.
- **Serena không thay thế UA-MCP**. Serena sở hữu quan sát exact symbol identity,
  declaration, implementation, LSP reference và diagnostics; các quan sát này là
  scoped semantic evidence, không phải architecture/trace ownership.
- CBM không thay structured traversal bằng generic semantic search khi graph đã có
  cấu trúc cần thiết. CBM chỉ hỗ trợ có điều kiện cho fuzzy semantic anchor discovery,
  graph-gap recovery, independent corroboration và reviewer counter-evidence.
- Current source vẫn authoritative cho exact code fact.
- AgentMemory chỉ cung cấp historical candidate context; current source và tests hiện
  tại mới authoritative cho claim hiện hành.
- Mọi static provider đều không bảo đảm hidden-consumer completeness ngoài semantics
  mà nó model; đặc biệt LSP/static graph không chứng minh mọi reflective, configured
  hoặc event-driven consumer.

Canonical trace: freshness probe → graph/domain anchor → structured UA-MCP
traversal → conditional CBM support → exact source verification → evidence manifest.
Mỗi CBM support call phải ghi reason: unresolved anchor, incomplete relationship,
ambiguous semantic query, relevant stale graph files, reviewer corroboration, hoặc
hidden consumer/dependency search.

Freshness handling:

- `FRESH`: UA-MCP primary; source verify material exact facts.
- `STALE` chỉ ở file không liên quan: UA-MCP vẫn primary; ghi scoped freshness và
  verify relevant source.
- `STALE` ở file liên quan: UA-MCP chỉ là navigation evidence; CBM/source tạo current
  trace, giảm confidence, có thể request refresh.
- `VERY_STALE`: chỉ dùng initial anchor; không dùng làm primary material evidence.

### [CRITICAL] R-Tool-3: Use-when-healthy — không skip im lặng provider khỏe

- Khi một preferred provider **configured + healthy + fresh + applicable** cho câu
  hỏi hiện tại → agent **PHẢI** dùng nó, hoặc ghi **justification tường minh** vì sao
  không dùng.
- Skip im lặng một provider đang khỏe = **invalid** (gate từ chối).
- Zero-result từ một provider khỏe (vd Agent Memory recall trả rỗng) là **evidence
  hợp lệ**, không phải lý do bỏ qua provider.

### [CRITICAL] R-Tool-4: Real probe — registration không phải là data

- Provider health phải đến từ **probe thật**: `TOOL_HEALTH.yaml` (gate `tool-health`)
  ghi probe operation + observed output + freshness; mọi MCP call phải có invocation
  record hash-bound (`maika provider record`, gate `provider-invocations`) — health
  tự khai không có record = **invalid**. `maika doctor mcp` chẩn đoán config + runtime.
- Maika dùng MCP config key `db-access` mà user đã cấu hình. Không suy đoán provider
  chạy local/remote, không yêu cầu local binary, và không đọc DB/tunnel credentials.
- **Registration ≠ có data.** Một provider đăng ký nhưng graph/index rỗng thì probe
  rỗng = **invalid** (không được coi là sẵn sàng). Phải verify provider có DATA, không
  chỉ có REGISTRATION.

### [CRITICAL] R-Tool-5: Current source authority + source verification

- **Current source là authority tối cao cho exact code fact** (file, symbol, signature,
  test, behavior, configuration). UA/CBM/memory chỉ định hướng; material fact lấy từ
  graph phải được **current source xác minh** khi đó là exact code fact.
- Structured trace ghi vào `TRACE_EVIDENCE.yaml`: traversal tham chiếu observation
  response hash; exact fact verify bằng `maika provider verify-source` (Maika tự hash,
  gate `trace-evidence`/`exploration-evidence` re-verify — không tự viết sha256).
- **Grep-honesty:** nếu artifact khai "grep fallback / provider unavailable" cho một
  code-fact mà file đó thuộc project đã index trong CBM/UA → **REJECT** (không được lấy
  cớ lười để tụt xuống grep khi provider có data); degradation phải là limitations
  entry có cấu trúc, backed bằng invocation record status error.

### [CRITICAL] R-Tool-6: Historical recall bắt buộc cho standard/architectural change

- Mọi standard và architectural change **PHẢI** recall Agent Memory (incident, quyết
  định cũ, rejected approach) **trước** khi chốt spec.
- Recall trả rỗng = evidence hợp lệ; **thiếu** recall (khi provider khỏe) = invalid.
- Memory phải được phân loại: valid / superseded / conflicting / advisory.

### [CRITICAL] R-Tool-7: Freshness & degradation tường minh

- Provider graph/index phải ghi `indexed_commit` + freshness state.
- Provider **stale hoặc absent** → ghi một **degradation record có cấu trúc** gồm:
  provider, probe thật đã chạy, error/observed, freshness state, fallback đã dùng,
  missing evidence, confidence impact, và affected claims.
- **Không degrade lặng lẽ.** Degradation không ghi record = như skip im lặng = invalid.

### [CRITICAL] R-Tool-8: Dispatch & handoff evidence

- `handoff-slice` và `node-checkpoint` là gate evidence cho task handoff.
- Handoff slice PHẢI gồm section `Applicable DNA/Conventions`.
- Node progress có thể ghi `NODE_CHECKPOINT.<node-id>.md`.
- Context còn thiếu có thể yêu cầu qua `CONTEXT_REQUEST.<node-id>.md`.

### [CRITICAL] R-Tool-9: Database operation boundary

- DB Access là provider có cả `read`, `write` và `script`; Maika không được mô tả
  toàn provider là read-only hoặc che các tool ghi hợp lệ.
- Lane `database-explorer` **chỉ read-only** — không tự động chạy DDL hoặc DML trong
  exploration và không được thấy write/script tools trong context của lane này.
- `sql_write`, `mongo_write` và `sql_execute_script` chỉ được route khi user yêu cầu
  thao tác ghi tường minh, chọn đúng source/database/environment, và vẫn phải qua
  preview + confirmation token của DB Access. Confirmation token là safety của
  provider, không thay thế intent tường minh của user.
- Persistence-sensitive change (entity, repository, native SQL, table/column/index,
  constraint, package/procedure, migration, transaction, locking, job/outbox, audit)
  **PHẢI** có DB evidence; chênh lệch giữa source và live DB state phải được reconcile.

### [REFERENCE] R-Tool-10: mcp-bridge fallback

- `mcp-bridge` là đường fallback khi một platform cần wiring MCP tường minh (provider
  không auto-discover). Bootstrap trỏ MCP failure về `maika doctor mcp` và bridge fallback.

### [CRITICAL] R-Tool-11: Evidence type requirement

- Mỗi capability khai `required_evidence_types` cho câu hỏi nó phục vụ. Retrieval **chưa
  thu đủ** required evidence type → coi như **chưa pass** (không đủ để dựng decision).
- Reviewer **không** sửa application code.

### [CRITICAL] R-Tool-12: Evidence authority và envelope

- Mọi external observation trong `TRACE_EVIDENCE.yaml` dùng evidence envelope
  version 1: provider/runtime/tool-contract, request/response hash, project, source
  revision, working-tree state, provider snapshot, observed time và degradation.
- Không tự điền dữ liệu upstream không cung cấp. Giá trị chưa chứng minh phải là
  `unverified`; readiness không được mang nhãn production khi còn mandatory field
  `unverified`.
- Conflict UA/CBM không được merge thành một claim `verified`. Phải ghi `conflicts`
  và resolve bằng file đã hash qua `maika provider verify-source`.
- AgentMemory chỉ có authority `historical_context`, classification `candidate`,
  `canonical: false`. `agentId` chỉ là retrieval filter, không phải authorization.
  Durable knowledge chỉ được promote qua `cli/knowledge_control.py` sau verification.
- Khi dùng CBM cho material evidence: ghi `index_status` trước/sau session; HEAD,
  working tree, node/edge count, index timestamp và tool-contract hash phải ổn định.
  `index_generation` tiếp tục là `unverified` cho tới khi upstream cung cấp immutable ID.
