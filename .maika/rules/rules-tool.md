# rules-tool.md — Provider Doctrine (Tool & MCP)

> Sub-file của `RULES.md`. Đọc qua manifest `RULES.md`.
> Định nghĩa **provider doctrine**: capability nào ưu tiên provider nào, khi nào
> BẮT BUỘC dùng, cách probe/freshness/degradation, và thẩm quyền của current source.
> Nguyên tắc nền: **provider hỗ trợ suy luận, không ghi đè current source / live DB /
> business contract hiện hành** (xem `rules-knowledge.md` §Thứ tự thẩm quyền).

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
| `architecture_discovery` | Understand-Anything (UA) | boundary, domain overview, flow, quan hệ module, tài liệu nội bộ |
| `dependency_analysis` | Codebase Memory (CBM) | dependency path, call path, phạm vi ảnh hưởng (blast radius), symbol relationship |
| `exact_source_inspection` | **current source** | file, symbol, signature, test, behavior, configuration hiện tại |
| `historical_context_retrieval` | Agent Memory | incident cũ, quyết định trước, rejected approach, review pattern lặp lại |
| `business_knowledge_retrieval` | Agent Memory + tài liệu | tri thức nghiệp vụ, domain, tài liệu |
| `convention_retrieval` | durable knowledge | Author DNA, conventions, rule IDs |
| `database_schema_inspection` | Database Explorer (read-only) | table, column, constraint, index, package, procedure |
| `database_dependency_analysis` | Database Explorer (read-only) | phụ thuộc DB, consumer SQL/package |

- **UA là nguồn số 1** cho kiến trúc/domain — không được tụt xuống grep khi UA
  available. **CBM là nguồn số 1** cho dependency/blast radius ở quy mô repo.

### [CRITICAL] R-Tool-3: Use-when-healthy — không skip im lặng provider khỏe

- Khi một preferred provider **configured + healthy + fresh + applicable** cho câu
  hỏi hiện tại → agent **PHẢI** dùng nó, hoặc ghi **justification tường minh** vì sao
  không dùng.
- Skip im lặng một provider đang khỏe = **invalid** (gate từ chối).
- Zero-result từ một provider khỏe (vd Agent Memory recall trả rỗng) là **evidence
  hợp lệ**, không phải lý do bỏ qua provider.

### [CRITICAL] R-Tool-4: Real probe — registration không phải là data

- Provider health phải đến từ **probe thật**: `mcp-status` ghi provider health trước
  khi dựa vào dynamic capability; `maika doctor mcp` chẩn đoán config + runtime.
- **Registration ≠ có data.** Một provider đăng ký nhưng graph/index rỗng thì probe
  rỗng = **invalid** (không được coi là sẵn sàng). Phải verify provider có DATA, không
  chỉ có REGISTRATION.

### [CRITICAL] R-Tool-5: Current source authority + code-evidence

- **Current source là authority tối cao cho exact code fact** (file, symbol, signature,
  test, behavior, configuration). UA/CBM/memory chỉ định hướng; material fact lấy từ
  graph phải được **current source xác minh** khi đó là exact code fact.
- Evidence `code-facts` ghi `node_id` và blast-radius khi có graph evidence; evidence
  `architecture-facts` ghi source anchor, relationship và convention ID liên quan — một
  `UA identifier` là hợp lệ khi graph node ID không phải nguồn của architecture fact.
- **Grep-honesty:** nếu artifact khai "grep fallback / provider unavailable" cho một
  code-fact mà file đó thuộc project đã index trong CBM/UA → **REJECT** (không được lấy
  cớ lười để tụt xuống grep khi provider có data).

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

### [CRITICAL] R-Tool-9: Database read-only

- Exploration DB **chỉ read-only** — không tự động chạy DDL hoặc DML trong exploration.
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
