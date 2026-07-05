# Hướng dẫn viết Architecture Decision Record (ADR)

> Tài liệu tham khảo cho skill `infra-tdd`. Chỉ load khi đang viết ADR (Bước 5 trong workflow).

## Mục lục

- ADR là gì?
- 7 Quy tắc viết ADR
- Ví dụ mẫu 1 — ADR Banking
- Bối cảnh
- Quyết định
- Alternatives đã xem xét
- Ma trận đánh giá
- Hệ quả
- Bằng chứng
- Ví dụ mẫu 2 — ADR Async Export
- Bối cảnh
- Quyết định
- Alternatives
- Hệ quả
- Lỗi phổ biến khi viết ADR
- Lifecycle ADR
- Đặt tên file

---

## ADR là gì?

**Architecture Decision Record (ADR)** là một văn bản ngắn ghi lại **một quyết định kiến trúc quan trọng**, bao gồm bối cảnh, alternatives đã xem xét, quyết định cuối cùng, và hệ quả.

ADR **không phải** meeting notes, RFC, hay design doc. Nó là **bản ghi quyết định bất biến** — một khi accepted, không sửa, chỉ thay thế bằng ADR mới.

### Tại sao cần ADR?

- **Trí nhớ tổ chức**: 6 tháng sau, không ai nhớ tại sao chọn MongoDB thay vì PostgreSQL
- **Onboarding**: Dev mới đọc ADR thay vì hỏi 5 người "tại sao cái này vậy?"
- **Tránh lặp lại debate**: Nếu có ADR với evidence, không cần tranh luận lại
- **Accountability**: Ghi rõ ai quyết định, dựa trên evidence gì

---

## 7 Quy tắc viết ADR

### Quy tắc 1 — Một quyết định, một ADR

Không gộp "chọn database + chọn caching strategy + chọn deployment model" vào 1 file. Mỗi quyết định có context và forces riêng.

**❌ Sai**: "ADR-001: Chọn tech stack cho Payment Service"
**✅ Đúng**: "ADR-001: Chọn MongoDB cho transaction storage" + "ADR-002: Sử dụng Redis Cluster cho distributed lock"

### Quy tắc 2 — Tiêu đề bắt đầu bằng động từ thì hiện tại

Tiêu đề phải thể hiện **hành động** rõ ràng, đọc xong biết quyết định gì.

**❌ Sai**: "Database Selection", "Caching Approach", "Về việc chọn message broker"
**✅ Đúng**: "Sử dụng MongoDB cho transaction storage", "Triển khai Redis Cluster cho distributed locking", "Chuyển sang Kafka thay thế RabbitMQ"

### Quy tắc 3 — Luôn liệt kê ≥ 2 alternatives thực sự

"Alternative" phải là option **thực sự khả thi** mà team đã cân nhắc, không phải straw man.

**❌ Sai alternative**: "Không làm gì" (khi rõ ràng phải làm), "Viết message broker từ đầu" (không ai nghiêm túc)
**✅ Đúng alternative**: "PostgreSQL với JSONB", "MongoDB với WiredTiger", "DynamoDB Serverless"

### Quy tắc 4 — Tiêu chí đánh giá phải có trọng số

Nếu mọi tiêu chí bằng nhau, chúng vô nghĩa. Trọng số buộc bạn nói rõ **cái gì quan trọng hơn cái gì**.

**❌ Sai**:
| Tiêu chí | A | B | C |
|----------|---|---|---|
| Performance | ✅ | ⚠️ | ✅ |
| Cost | ⚠️ | ✅ | ⚠️ |

**✅ Đúng**:
| Tiêu chí (trọng số) | A | B | C |
|----------------------|---|---|---|
| Latency P99 < 50ms (40%) | ✅ 3×0.4=1.2 | ⚠️ 2×0.4=0.8 | ✅ 3×0.4=1.2 |
| Monthly cost < $200 (30%) | ⚠️ 2×0.3=0.6 | ✅ 3×0.3=0.9 | ⚠️ 2×0.3=0.6 |
| Team familiarity (20%) | ✅ 3×0.2=0.6 | ❌ 1×0.2=0.2 | ⚠️ 2×0.2=0.4 |
| Operational complexity (10%) | ⚠️ 2×0.1=0.2 | ✅ 3×0.1=0.3 | ✅ 3×0.1=0.3 |
| **Tổng** | **2.6** | **2.2** | **2.5** |

### Quy tắc 5 — Đặt tên trade-off

Mọi quyết định đều có cái mất. Nếu không tìm thấy trade-off, bạn chưa hiểu đủ sâu.

**❌ Sai**: "MongoDB là lựa chọn tốt nhất cho mọi mặt"
**✅ Đúng**: "MongoDB cho write throughput tốt hơn, nhưng chấp nhận: (1) eventual consistency cho cross-document queries, (2) team cần học aggregation pipeline, (3) không có ACID multi-collection transactions"

### Quy tắc 6 — Evidence không phải opinion

Mỗi claim trong ADR nên có nguồn. Evidence bao gồm:

| Loại evidence | Ví dụ | Độ tin cậy |
|---------------|-------|------------|
| Benchmark/PoC | "PoC cho thấy P99 = 45ms với 10K TPS" | Rất cao |
| Production data | "Production outage report: Redis crash gây 30 phút downtime" | Rất cao |
| UA Knowledge Graph | "Node X có 15 incoming dependencies → blast radius cao" | Cao |
| Codebase Memory search | "Pattern Y xuất hiện trong 23 files → convention mạnh" | Cao |
| DB schema analysis | "Table Z có 12M rows, no partition → query chậm" | Cao |
| Vendor documentation | "MongoDB docs: WiredTiger supports compression" | Trung bình |
| Blog/conference talk | "Netflix dùng approach tương tự cho service X" | Thấp |
| "Mọi người đều biết" | "Kafka nhanh hơn RabbitMQ" | Không chấp nhận |

### Quy tắc 7 — ADR là bất biến (Immutable)

Sau khi status = `Accepted`:
- **KHÔNG sửa** nội dung
- Nếu quyết định sai → viết ADR mới với status `Superseded by ADR-NNNN`
- ADR cũ giữ nguyên với status `Deprecated` hoặc `Superseded by ADR-NNNN`

ADR đã accepted là record bất biến. Quyết định mới phải được ghi bằng ADR mới.

---

## Ví dụ mẫu 1 — ADR Banking

```markdown
# ADR-0003: Sử dụng Redis Distributed Lock cho Transaction Serialization

> **Trạng thái**: Accepted
> **Ngày**: 2025-03-15
> **Tác giả**: Team Architecture
> **Người quyết định**: Tech Lead

## Bối cảnh

Hệ thống ngân hàng xử lý giao dịch tài chính cần đảm bảo **tại một thời điểm chỉ có 1 action**
trên cùng một ApprovalRequest (yêu cầu phê duyệt). Race condition ở đây = chuyển tiền 2 lần.

Forces:
- Hệ thống multi-instance (3 pods) → DB lock không đủ
- Latency yêu cầu < 100ms cho lock acquire
- Lock phải tự giải phóng nếu app crash (self-healing)
- Cần non-blocking — fail fast thay vì chờ

## Quyết định

**Sử dụng Redis `SET NX PX` qua Spring Integration `ExpirableLockRegistry`**,
với lock key pattern `ACTIVE_APPROVAL_REQUEST_LOCK_{requestId}` và TTL 60 giây.

## Alternatives đã xem xét

### Alt A — Database Pessimistic Lock (SELECT FOR UPDATE)
- Ưu: Đơn giản, không cần thêm infra
- Nhược: Blocking (thread chờ), latency cao, không self-healing khi app crash
- Không chọn vì: Latency P99 > 500ms với contention cao

### Alt B — ZooKeeper Distributed Lock
- Ưu: Strong consistency, battle-tested
- Nhược: Thêm infra phức tạp (ZK ensemble), operational overhead
- Không chọn vì: Over-engineering cho use case này, team không có ZK expertise

### Alt C — Redis SET NX PX ✅
- Ưu: Non-blocking tryLock, TTL self-healing, latency < 5ms
- Nhược: Không phải strong consensus (edge case khi Redis failover)

## Ma trận đánh giá

| Tiêu chí (trọng số) | DB Lock | ZooKeeper | Redis ✅ |
|----------------------|---------|-----------|----------|
| Latency < 10ms (40%) | ❌ 1×0.4=0.4 | ⚠️ 2×0.4=0.8 | ✅ 3×0.4=1.2 |
| Self-healing (30%) | ❌ 1×0.3=0.3 | ✅ 3×0.3=0.9 | ✅ 3×0.3=0.9 |
| Ops complexity (20%) | ✅ 3×0.2=0.6 | ❌ 1×0.2=0.2 | ✅ 3×0.2=0.6 |
| Consistency (10%) | ✅ 3×0.1=0.3 | ✅ 3×0.1=0.3 | ⚠️ 2×0.1=0.2 |
| **Tổng** | **1.6** | **2.2** | **2.9** |

## Hệ quả

### Tích cực
- Lock acquire < 5ms P99
- TTL tự giải phóng khi app crash — zero manual intervention
- Cùng lock key cho single + batch approve → đảm bảo serialize mọi kênh

### Tiêu cực (Trade-off)
- Redis failover (master → replica) có thể mất lock → window rất nhỏ cho duplicate
  → Mitigation: DB unique constraint làm safety net (Tầng 3 bảo vệ)
- Depend thêm vào Redis availability
  → Mitigation: Redis Sentinel cho HA

## Bằng chứng
- Production data: 3 tầng lock (Redis + Cache + DB) chặn 99.99% race conditions
- Codebase: `BaseApprovalRequestProcessor` — 10 processors đều dùng cùng pattern
```

---

## Ví dụ mẫu 2 — ADR Async Export

```markdown
# ADR-0007: Chuyển Export File từ Blocking sang Async DeferredResult + Kafka

> **Trạng thái**: Accepted
> **Ngày**: 2025-06-01
> **Tác giả**: Team Platform

## Bối cảnh

Export file V1 (blocking I/O) gây timeout cho file lớn (> 5000 rows).
HTTP thread bị block suốt quá trình render → connection pool exhaustion
khi nhiều user export đồng thời.

## Quyết định

**Triển khai async export pipeline**: Business Service tạo DeferredResult → publish
data lên Kafka → Worker Service render file → upload MinIO → callback qua Redis Pub/Sub
→ DeferredResult complete → client nhận encrypted download URL.

## Alternatives

### Alt A — WebSocket push
- Không chọn: Firewall issues, phức tạp connection management

### Alt B — Client polling
- Không chọn: N×M requests tạo load không cần thiết

### Alt C — DeferredResult + Kafka + Redis Pub/Sub ✅
- Chọn vì: Zero extra requests, release thread ngay, error propagation qua Pub/Sub

## Hệ quả

### Tích cực
- Thread pool không bao giờ bị exhaust bởi export
- Worker scale độc lập với business service
- File lưu MinIO với TTL → tự cleanup

### Tiêu cực
- Thêm complexity: 3 systems (Kafka + MinIO + Redis Pub/Sub)
- URL encryption (AES) thêm latency nhỏ
- Client disconnect → Worker vẫn render (wasted work)
```

---

## Lỗi phổ biến khi viết ADR

| Lỗi | Vấn đề | Cách sửa |
|-----|--------|----------|
| "Chọn X vì X tốt nhất" | Không có alternatives | Liệt kê ≥ 2 alternatives thực sự |
| Alternatives là straw man | "Alt A: Không làm gì" khi rõ ràng phải làm | Chọn alternatives team thực sự đã cân nhắc |
| Không có trọng số | Mọi tiêu chí bằng nhau → vô nghĩa | Gán trọng số, buộc prioritize |
| Trade-off = "không có" | Mọi quyết định đều có cái mất | Hỏi: "Cái gì sẽ khó hơn vì quyết định này?" |
| Evidence = "ai cũng biết" | Opinion, không phải evidence | Dẫn nguồn: benchmark, production evidence, code, docs |
| Sửa ADR đã accepted | Mất lịch sử quyết định | Viết ADR mới supersedes cái cũ |
| ADR quá dài (> 2 trang) | Gộp nhiều quyết định | Tách thành nhiều ADR, mỗi cái 1 quyết định |
| Bỏ section "Hệ quả" | Không biết cái mất khi deploy | Luôn viết cả tích cực lẫn tiêu cực |

---

## Lifecycle ADR

```
Proposed → Accepted → [Deprecated | Superseded by ADR-NNNN]
```

- **Proposed**: Đang review, chưa ai commit
- **Accepted**: Team đã đồng ý, bắt đầu implement
- **Deprecated**: Quyết định không còn áp dụng (hệ thống đã thay đổi)
- **Superseded by ADR-NNNN**: Quyết định mới thay thế, link đến ADR mới

## Đặt tên file

```
docs/tdd/{module}-adr/
├── 0001-su-dung-mongodb-cho-transaction-storage.md
├── 0002-trien-khai-redis-cluster-cho-distributed-lock.md
├── 0003-chuyen-sang-kafka-thay-the-rabbitmq.md
└── 0004-chon-deferred-result-cho-async-export.md
```

Quy ước: `{NNNN}-{slug-tieng-viet}.md` — số tăng dần, slug lowercase có dấu gạch ngang.
