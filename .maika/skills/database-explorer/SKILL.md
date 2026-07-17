---
name: database-explorer
version: '3.0'
description: 'Dùng khi change chạm persistence (entity, repository, native SQL, table,
  column, index, constraint, package, procedure, migration, transaction, locking,
  job/outbox, audit): probe DB read-only và phát ra DATABASE_CONTEXT.yaml có evidence
  hoặc degradation.'
routing:
  mode: conditional
  states: []
  classes:
  - trivial
  - small
  - standard
  - architectural
capabilities:
  required:
  - database_schema_inspection
  - exact_source_inspection
  conditional:
    database_dependency_analysis:
      triggers:
      - database_dependency_risk
outputs:
  required:
  - exploration/DATABASE_REQUEST.yaml
  - exploration/DATABASE_CONTEXT.yaml
gates:
- database-request
- database-context
---
# Database Explorer

## Mục tiêu
Chuyên gia điều kiện cho persistence: kiểm tra schema/object DB ở chế độ read-only,
map code consumer, so sánh source ↔ live DB, phát ra `exploration/DATABASE_CONTEXT.yaml`
với evidence hoặc degradation record.

## Khi nào sử dụng
Dùng khi `grounding-explorer` phát hiện tín hiệu persistence: entity/repository,
native SQL, table/column/constraint, collection, migration,
transaction/locking, job/outbox, audit, hoặc DB performance.

## Khi nào KHÔNG sử dụng
- Change không chạm persistence.
- Để chạy DDL/DML thay đổi dữ liệu (exploration chỉ read-only).

## Đầu vào
- `exploration/DATABASE_REQUEST.yaml` (skeleton do orchestrator compile khi
  persistence signal kích hoạt — điền `environment` + `database` tường minh,
  gate `database-request` từ chối giá trị rỗng).
- `QUERY_PLAN.yaml` (câu hỏi DB), `INTENT.md`.
- Current source (entity/repository/migration).
- Kết nối DB read-only (nếu có).

## Câu hỏi tri thức
- Table/column/constraint hoặc Mongo collection/schema nào tham gia? (database_schema_inspection)
- FK nào quan sát được và source nào consume SQL/object đó? (database_dependency_analysis)
- Source khai schema có khớp live DB không (drift)?

## Loại evidence bắt buộc
- `database_object`, `database_column`, `database_constraint`.
- `database_dependency` trong phạm vi constraint metadata; `sql_consumer` từ current source.
- Index/routine/package/dependency catalog không có trong `tools/list` phải ghi limitation,
  không được suy đoán hoặc gọi tool không tồn tại.

## Chính sách capability
Required: `database_schema_inspection`, `exact_source_inspection`.
Conditional — chỉ gọi khi trigger kích hoạt, ghi trigger + reason:
  `database_dependency_analysis` (database_dependency_risk).
Code consumer gap ngoài constraint metadata route qua `exact_source_inspection`
  (current source) hoặc UA `query_nodes` corroborating, không phải một capability
  riêng.
Chỉ read-only; không tự chạy DDL/DML trong exploration (`jit/providers.md` R-Tool-9).

## Quy trình truy xuất
1. Từ source, liệt kê entity/table/collection trong scope.
2. Probe DB Access bằng đúng tool có trong `tools/list`: database/table/column/constraint
   hoặc Mongo collection/schema.
3. Map code consumer bằng current source (repository, native query, caller).
4. So sánh source ↔ live → ghi drift.

## Thứ tự authority và precedence
Live DB là authority cho trạng thái quan sát của environment đã chọn; approved
migration/spec là authority cho target state; current source là authority cho behavior
ứng dụng. Mọi khác biệt phải phân loại drift, không mặc định live DB thắng target.

## Kết quả bắt buộc
- `DATABASE_CONTEXT.yaml` v2: provider + probe (environment-bound, `host_mcp`) +
  observations thật, hoặc structured degradation. Drift phải phân loại
  (`source_ahead` | `db_ahead` | `mismatch`). Schema gate-true:

```yaml
# DATABASE_CONTEXT.yaml
version: 2
change_id: C-123
read_only: true
provider:
  id: db-access
  client_key: db-access
probe:
  invocation_mode: host_mcp
  database: orders_db
  environment: staging
  observed_at: '2026-07-14T08:00:00Z'
  status: success
  # response_hash của invocation record probe (maika provider record in ra) —
  # gate từ chối probe success không có record backing.
  observation: 'sha256:0000000000000000000000000000000000000000000000000000000000000000'
allowed_lane: exploration
allowed_tools: [list_databases, sql_list_tables, sql_get_columns, sql_get_constraints,
                mongo_list_collections, mongo_get_schema]
used_tools: [sql_list_tables, sql_get_columns]
observations:
- object: orders
  type: table
  columns: [id, status, created_at]
code_consumers:
- object: orders
  file: src/repo/order_repo.py
  symbol: OrderRepo
drift:
- object: orders
  classification: source_ahead
  detail: migration V42 declares column refund_status; staging chưa apply
degradation: []
limitations: []
confidence: high
```

## Bất biến
- Read-only tuyệt đối trong exploration.
- Không suy đoán schema — phải probe hoặc degrade tường minh.

## Yêu cầu evidence
Mỗi DB claim cite object name + type; dependency cite consumer. Không probe được →
degradation record (provider, probe, observed, fallback, confidence impact).

## Freshness và confidence
Ghi thời điểm probe. Schema có thể đổi giữa các phiên → coi live probe là fresh nhất;
source-declared schema là medium confidence.

## Quy trình degradation
MCP `db-access` không được cấu hình, không kết nối được, hoặc thiếu tool cần thiết →
`DATABASE_CONTEXT.yaml` chứa degradation entry có cấu trúc
(`{kind: provider_unreachable, detail: "..."}`) + fallback = source-declared schema;
hạ confidence; không block nếu change vẫn an toàn theo source. Probe lỗi vẫn phải
record qua `maika provider record --status error` (health không được tự khai).

## Quy trình
1. Chạy Quy trình truy xuất.
2. Emit `DATABASE_CONTEXT.yaml`.
3. Chạy gate `database-context`.
4. Trả evidence cho grounding-explorer.

## Điều kiện dừng
- Phát hiện destructive DB decision (drop/alter phá dữ liệu) → dừng, hỏi user/DBA.
- Thiếu credential và không degrade an toàn được.

## Tác động lên knowledge
Ghi DB evidence + drift vào exploration; đề xuất cập nhật `knowledge-snapshot.md` nếu
schema khác mô tả kiến trúc hiện tại (curator xử lý sau).

## Đầu ra
`exploration/DATABASE_CONTEXT.yaml` (evidence hoặc degradation).

## Handoff tiếp theo
`grounding-explorer` (nạp DB evidence vào gói grounding).
