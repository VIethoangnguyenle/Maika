---
name: database-explorer
version: '1.0'
description: >
  Dùng khi change chạm persistence (entity, repository, native SQL, table, column,
  index, constraint, package, procedure, migration, transaction, locking, job/outbox,
  audit): probe DB read-only và phát ra DATABASE_CONTEXT.yaml có evidence hoặc degradation.
---

# Database Explorer

## Mục tiêu
Chuyên gia điều kiện cho persistence: kiểm tra schema/object DB ở chế độ read-only,
map code consumer, so sánh source ↔ live DB, phát ra `exploration/DATABASE_CONTEXT.yaml`
với evidence hoặc degradation record.

## Khi nào sử dụng
Dùng khi `grounding-explorer` phát hiện tín hiệu persistence: entity/repository,
native SQL, table/column/index/constraint, package/procedure, migration,
transaction/locking, job/outbox, audit, hoặc DB performance.

## Khi nào KHÔNG sử dụng
- Change không chạm persistence.
- Để chạy DDL/DML thay đổi dữ liệu (exploration chỉ read-only).

## Đầu vào
- `QUERY_PLAN.yaml` (câu hỏi DB), `INTENT.md`.
- Current source (entity/repository/migration).
- Kết nối DB read-only (nếu có).

## Câu hỏi tri thức
- Table/column/constraint/index nào tham gia? (database_schema_inspection)
- Object nào phụ thuộc / consumer SQL/package nào? (database_dependency_analysis)
- Source khai schema có khớp live DB không (drift)?

## Loại evidence bắt buộc
- `database_object`, `database_column`, `database_constraint`, `database_index`.
- `database_package`, `database_procedure` (khi có).
- `database_dependency`, `sql_consumer`, `package_consumer`.

## Chính sách capability
Capability IDs: `database_schema_inspection`, `database_dependency_analysis`,
  `exact_source_inspection`.
Chỉ read-only; không tự chạy DDL/DML trong exploration (`rules-tool.md` R-Tool-9).

## Quy trình truy xuất
1. Từ source, liệt kê entity/table/procedure trong scope.
2. Probe DB read-only: mô tả object, column, constraint, index, dependency.
3. Map code consumer (repository, native query, package caller).
4. So sánh source ↔ live → ghi drift.

## Thứ tự authority và precedence
live DB state > current source > durable knowledge. Khác biệt source ↔ live là
conflict `database drift`, resolve nghiêng về live state.

## Kết quả bắt buộc
- `DATABASE_CONTEXT.yaml`: `read_only: true` + objects thật, hoặc degradation record.
- Drift được ghi và phân loại.

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
DB không kết nối được (môi trường không có DB) → `DATABASE_CONTEXT.yaml` chứa
degradation record + fallback = source-declared schema; hạ confidence; không block nếu
change vẫn an toàn theo source.

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
