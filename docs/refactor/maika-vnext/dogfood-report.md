# Dogfood — Maika knowledge-native runtime trên Java + Postgres (Docker)

> Mục tiêu: chứng minh runtime knowledge-native hoạt động trên **code + DB thật**
> (không synthetic stub), theo yêu cầu dogfood của master plan (DoD #24).
> Chạy 2026-07-10. App thật chạy trong Docker; DB thật là Postgres trong Docker.

## Target dogfood

`inventory-service` (Java 17, Gradle) — app nhỏ nhưng chạy thật:

- **Validation chain**: `OrderValidator` gồm danh sách `Rule` (SKU_REQUIRED,
  QTY_POSITIVE, CUSTOMER_REQUIRED) — extension seam là `rules` list.
- **Persistence (JDBC → Postgres)**: `OrderRepository.insert/findById` trên bảng `orders`.
- **Async/integration boundary**: `OrderEventPublisher` publish `orders.events`
  (transport seam injected — biên Kafka/gRPC).
- **Domain**: `Order` value object dựng qua builder (không public setter).

## Bằng chứng thật (đã chạy)

### 1. App chạy thật + persist DB thật
```
$ docker run --rm --network host -v <dogfood>:/app gradle:8.7-jdk17 gradle -q run
EVENT orders.events {"orderId":1,"sku":"WIDGET-1","status":"NEW"}
SAVED order id=1

$ docker exec maika-dogfood-pg psql -U postgres -d inventory -c "SELECT * FROM orders;"
 id | customer_id |   sku    | quantity | status
----+-------------+----------+----------+--------
  1 |          42 | WIDGET-1 |        3 | NEW
```

### 2. Codebase Memory index code Java thật (dependency_analysis / architecture_discovery)
```
$ codebase-memory-mcp cli index_repository '{"repo_path":"<dogfood>"}'
{"status":"indexed","nodes":74,"edges":188}

$ codebase-memory-mcp cli search_graph '{"project":"<proj>","query":"validate"}'
name=validate  Method  file=src/main/java/com/maika/inventory/validation/OrderValidator.java:30-38
```

### 3. Database Explorer read-only trên schema thật (database_schema_inspection)
`psql \d orders` → bảng `orders` (6 cột) + index `idx_orders_status`,
`idx_orders_customer` + `uq_orders_customer_sku` UNIQUE + `orders_quantity_check` CHECK.
→ gate `database-context`: **PASS**.

### 4. Authenticity gates trên evidence thật (exact_source_inspection, P10)
Change thử: "thêm rule MAX_QUANTITY vào OrderValidator".

| Gate | Evidence | Kết quả |
|---|---|---|
| `exploration-evidence` | real file + sha256 thật + symbol `validate` có thật | **PASS** |
| `database-context` | live schema đã inspect read-only | **PASS** |
| `exploration-evidence` | **fake hash** (sha256:aaa…) | **FAIL** — "file_hash mismatch (stale/fabricated)" |
| `exploration-evidence` | **fake symbol** `ghostMethod` | **FAIL** — "symbol not found" |

→ chứng minh DoD #9 (evidence authenticity mechanically checked) và #27
(shape-only/fake evidence không pass) trên **code thật**.

## Provider coverage của dogfood

| Provider / capability | Dogfood | Trạng thái |
|---|---|---|
| Codebase Memory (dependency_analysis) | index + search_graph trên Java thật | ✅ live |
| Current source (exact_source_inspection) | sha256 + symbol verify | ✅ live |
| Database Explorer (database_schema_inspection) | psql read-only trên Postgres | ✅ live |
| Integration boundary (Kafka/event) | `orders.events` publish khi app chạy | ✅ live |
| Understand-Anything (architecture_discovery) | UA graph chưa dựng cho repo này | ⚠️ degradation (đúng doctrine) |
| Agent Memory (historical_context_retrieval) | recall rỗng ở môi trường này | ⚠️ zero-result hợp lệ |

UA/Agent Memory nằm trên degradation path đúng như doctrine degradation-first —
được ghi nhận tường minh, không skip im lặng.

## Tái lập
Nguồn dogfood + script sinh grounding nằm trong scratchpad phiên; các lệnh trên
tái lập được: `docker run postgres:16-alpine`, apply `db/schema.sql`,
`gradle:8.7-jdk17 gradle run`, `codebase-memory-mcp cli index_repository`,
`gate-check exploration-evidence --repo-root <dogfood>`.
