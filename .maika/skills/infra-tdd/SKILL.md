---
name: infra-tdd
version: '1.0'
description: >
  Xây dựng Technical Design Document (TDD) chuẩn hoá theo 5 tầng hybrid:
  Bối cảnh Nghiệp vụ, Chiến lược, Kiến trúc, Quyết định, và Vận hành.
  Dùng khi cần thiết kế, viết hoặc review TDD / Design Doc / RFC / ADR cho module infrastructure.
  KHÔNG dùng cho: README/how-to/runbook (→ document-writer),
  spec OpenSpec (→ openspec-propose), review kiến trúc (→ architecture-reviewer).
license: MIT
metadata:
  author: project-team
  version: '2.5'
  language: vi
  based-on: infra-tdd-template by perplexity-computer
---

# Skill Viết Technical Design Document (TDD) cho Infrastructure

## Mục tiêu

- Tạo Technical Design Document (TDD) chuẩn hoá, trả lời được 5 câu hỏi cốt lõi về nghiệp vụ, chiến lược, kiến trúc, quyết định thiết kế, và vận hành.
- Đảm bảo tài liệu có thể đọc được bởi cả non-tech (T0) và tech (T1–T4).
- Mọi claim trong TDD phải dựa trên evidence thực tế từ codebase, database, hoặc knowledge graph.

---

## Khi nào sử dụng

Kích hoạt skill khi:

- Thiết kế hoặc viết **TDD / Technical Design Document / Design Doc / RFC** cho module infrastructure hoặc platform
- Chuẩn hoá cách đội viết design document
- Viết hoặc review **Architecture Decision Record (ADR)**
- Tạo **sơ đồ kiến trúc** giải thích *tại sao* (không chỉ *cái gì*)
- Review design doc hiện có và bổ sung tầng decision record
- Chạy Socratic deep-dive trên quyết định kỹ thuật để lộ các giả định ẩn

Trigger: `/tdd <module-name>`, "viết TDD", "thiết kế module", "design doc cho service", "ADR cho lựa chọn DB", "sơ đồ kiến trúc", "RFC hạ tầng", "chuẩn hoá tài liệu thiết kế".

---

## Khi nào KHÔNG sử dụng

- Khi cần viết README, how-to, runbook (→ document-writer).
- Khi cần sinh spec kỹ thuật OpenSpec (→ openspec-propose).
- Khi cần review kiến trúc, đánh giá rủi ro (→ architecture-reviewer).
- Khi cần chuẩn hoá requirement (→ requirement-analyst).

## Triết lý cốt lõi

Một TDD tốt phải trả lời **5 câu hỏi** theo thứ tự. Format **hybrid** cho phép cả non-tech và tech đều đọc được cùng một tài liệu:

0. **NGHIỆP VỤ này là gì?** (Bối cảnh Nghiệp vụ — cho BA, PM, Stakeholder)
1. **TẠI SAO chúng ta xây cái này?** (Chiến lược — cho Tech Lead, Architect)
2. **HỆ THỐNG trông như thế nào?** (Kiến trúc)
3. **TẠI SAO thiết kế này chứ không phải cái khác?** (Quyết định / ADR)
4. **GIÁM SÁT và cấu hình như thế nào?** (Vận hành)

> **Nguyên tắc hybrid**: T0 viết bằng ngôn ngữ tự nhiên, KHÔNG dùng class name, pattern name, hay thuật ngữ kỹ thuật.
> BA/PM chỉ cần đọc T0 là hiểu module làm gì. Dev đọc từ T1 trở đi để hiểu cách triển khai.

Mọi section T1-T4 phải **kiểm chứng được** — reviewer phải có thể chỉ vào bất kỳ claim nào và hỏi "bạn biết điều này vì sao?" và tìm thấy bằng chứng (benchmark, citation, prototype, operational evidence).

Xem [references/cau-truc-5-tang.md](references/cau-truc-5-tang.md) khi cần bảng mapping chi tiết của hybrid 5 tầng và template bắt đầu.
Xem [references/knowledge-first-protocol.md](references/knowledge-first-protocol.md) trước khi viết từng tầng hoặc khi MCP tool không khả dụng.
Xem [references/format-standards.md](references/format-standards.md) khi cần quy tắc attribution, navigation, hub/sub-doc, PDF compatibility, ADR list, và Mermaid.

---

## Quy trình

Tuân thủ workflow theo thứ tự. **KHÔNG bỏ qua Socratic deep-dive** — đó là thứ phân biệt design doc thật với wiki page.

### Bước 1 — Thu thập thông tin (5 phút)

Hỏi user (hoặc đọc từ context):

- Tên module và mục đích 1 dòng
- Nghiệp vụ này phục vụ ai? Flow end-to-end từ góc nhìn user?
- Team sở hữu và stakeholder
- Đây là greenfield, replacement, hay extension?
- Ràng buộc cứng (compliance, latency, budget, deadline)
- Tài liệu, operational evidence, hoặc prototype cần link

Nếu thiếu thông tin **quan trọng**, hỏi user. Nếu không, tiến hành với assumptions viết rõ vào T0/T1.

### Bước 2 — Copy template + Viết T0 trước

Copy template vào đúng vị trí:
```
docs/tdd/<module-name>-TDD.md
```

**Điền T0 (Bối cảnh Nghiệp vụ) trước**. T0 là "cánh cửa" — nếu BA/PM đọc T0 mà không hiểu module làm gì, toàn bộ TDD thất bại.

**Quy tắc viết T0**:
- Dùng ngôn ngữ tự nhiên — không class name, không pattern name
- Flowchart đơn giản — dùng tên vai trò (Kế toán, Giám đốc) thay vì tên component
- Business rules bằng bullet points — "Nếu số tiền > 500 triệu thì cần 2 cấp duyệt"
- Ví dụ thực tế — "Kế toán A tạo lệnh chuyển lương cho 50 nhân viên..."
- Kết thúc T0 bằng 1 bảng tóm tắt thuật ngữ nghiệp vụ (glossary)

Sau T0, điền T1 (Chiến lược). KHÔNG BAO GIỜ nhảy sang kiến trúc trước khi vấn đề đã rõ ràng.

### Bước 3 — Kiến trúc với C4 + Mermaid

Đọc `references/diagrams-guide.md` và vẽ **ít nhất 2 C4 levels**:

- **Level 1 — System Context**: module + actors và systems bên ngoài
- **Level 2 — Containers**: deployable units (services, DBs, queues, jobs)
- **Level 3 — Components** (tuỳ chọn, chỉ cho module phức tạp)

Mỗi sơ đồ phải đi kèm prose giải thích:

- **Ranh giới trust / failure** mà mỗi mũi tên đi qua
- **Data contract** trên mỗi mũi tên (sync/async, schema link, retry policy)
- Chuyện gì xảy ra khi mỗi mũi tên **fail**

Sơ đồ không có 3 annotation này là trang trí, không phải documentation.

### Bước 4 — Socratic deep-dive trên các quyết định

Đây là trái tim của skill. Với mỗi quyết định non-trivial trong thiết kế, chạy protocol trong `references/socratic-deep-dive.md`. Mục tiêu là buộc 3 thứ vào văn bản:

1. **Các alternative thực sự đã xem xét** (≥ 2, lý tưởng 3)
2. **Tiêu chí đánh giá có trọng số** (không phải cảm tính)
3. **Trade-off đã chấp nhận** (mọi lựa chọn đều mất thứ gì đó — đặt tên nó)

**Ưu tiên**: Dùng **Understand-Anything** và **Codebase Memory** MCPs để drive deep-dive — xem section "Knowledge-First Protocol". Nếu MCPs không khả dụng, chạy cùng protocol bằng câu hỏi trong `references/socratic-deep-dive.md`.

### Bước 5 — Viết ADR

Với mỗi quyết định vượt qua test "một team member mới có hỏi tại sao không?", viết ADR riêng theo format MADR. Hướng dẫn và ví dụ đầy đủ trong `references/adr-guide.md`. ADR nằm ở `docs/tdd/<module>-adr/` và được link từ T3.

Quy tắc ADR:

- Một ADR per quyết định. Không gộp.
- Bất biến sau khi accepted. Thay đổi bằng ADR mới *supersedes* cái cũ.
- Lifecycle: `Proposed → Accepted → Deprecated → Superseded by ADR-NNNN`.

### Bước 6 — Tầng Vận hành

Điền T4 với 2 bảng chính:

1. **Monitoring & Alerts**: Metric name, cách đo, alert threshold — cụ thể, đo được.
2. **Configuration Reference**: Config key, mô tả, giá trị mặc định.

> ⚠️ **KHÔNG viết Troubleshooting Runbook trong TDD.** Tài liệu TDD dành cho Trưởng phòng và Tech Leads, không phải SRE ops. Runbook nếu cần sẽ là tài liệu riêng.

### Bước 7 — Review checklist

Trước khi tuyên bố TDD hoàn thành, chạy checklist ở cuối `assets/TDD_TEMPLATE.md`. Lỗi phổ biến:

- T0 dùng thuật ngữ kỹ thuật (class name, pattern name) → BA đọc không hiểu
- T0 thiếu ví dụ thực tế / kịch bản cụ thể
- T1 goals không đo được
- T2 sơ đồ thiếu failure annotations
- T2 thiếu Design Patterns Summary Table
- T2 thiếu Code Examples (NÊN/KHÔNG NÊN)
- T3 chỉ liệt kê 1 alternative ("chọn Postgres vì Postgres")
- T4 không có rollback plan
- T4 thiếu Configuration Reference table
- Thiếu Navigation Footer
- Thiếu Attribution Header chuẩn

### Bước 8 — Cập nhật Index & Navigation

Sau khi TDD hoàn thành:

1. **Cập nhật `docs/tdd/00-index.md`** — thêm TDD mới vào bảng modules, cập nhật cross-reference map và thống kê ADR.
2. **Kiểm tra Navigation Footer** — đảm bảo `← Trước` / `Tiếp theo →` link chính xác giữa các TDD liên quan.
3. **Kiểm tra Hub → Sub-doc** (nếu áp dụng) — nếu TDD đã tách sub-docs, đảm bảo file hub liệt kê đầy đủ.

---

## Đầu ra

- **Vị trí TDD**: `docs/tdd/<module>-TDD.md`
- **Vị trí ADR**: `docs/tdd/<module>-adr/NNNN-title.md`
- **Ngôn ngữ**: Tiếng Việt. Thuật ngữ kỹ thuật giữ tiếng Anh (SLO, ADR, C4, Kafka, Redis, gRPC...).
- **Định dạng**: Markdown.

## Tài nguyên đi kèm

- `assets/TDD_TEMPLATE.md` — template điền sẵn (5 tầng hybrid + checklist)
- `assets/ADR_TEMPLATE.md` — template ADR format MADR
- `references/cau-truc-5-tang.md` — bảng mapping chi tiết của hybrid 5 tầng
- `references/knowledge-first-protocol.md` — protocol evidence bắt buộc trước từng tầng
- `references/format-standards.md` — quy tắc format TDD và PDF compatibility
- `references/adr-guide.md` — hướng dẫn viết ADR, kèm 2 ví dụ mẫu
- `references/diagrams-guide.md` — mô hình C4 + cú pháp Mermaid, quy tắc annotation
- `references/socratic-deep-dive.md` — ngân hàng câu hỏi để tra vấn quyết định

Chỉ load reference files khi đến bước tương ứng — chúng quá dài để giữ trong context cùng lúc.

## Anti-patterns cần cảnh báo

Phản đối lịch sự nếu user muốn bất kỳ điều nào sau — chúng phá vỡ mục đích của skill:

- "**Bỏ qua alternatives, chỉ document thiết kế đã chọn**" → Không, T3 bắt buộc
- "**Dùng 1 sơ đồ khổng lồ chứa mọi thứ**" → Không, tách theo C4 levels
- "**ADR là 1 đoạn văn trong TDD**" → Không, file riêng, bất biến
- "**Tầng Vận hành để SRE điền sau**" → Không, designer sở hữu T4 ở v1 (metrics + config reference)
- "**Thêm Troubleshooting Runbook vào TDD**" → Không, TDD dành cho management — runbook là tài liệu ops riêng
- "**Viết TDD không cần chạy knowledge tools**" → Không, Knowledge-First Protocol là bắt buộc
- "**Dùng assumption thay vì evidence từ codebase**" → Không, mọi claim phải có bằng chứng
- "**Bỏ T0 vì đây là tài liệu kỹ thuật**" → Không, T0 là hybrid layer bắt buộc — BA/PM phải hiểu được
- "**Dùng thuật ngữ kỹ thuật trong T0**" → Không, T0 viết cho non-tech — dùng ngôn ngữ tự nhiên
- "**Bỏ navigation footer / attribution header**" → Không, FS-1 và FS-2 là bắt buộc
- "**File TDD 800+ dòng mà không tách sub-doc**" → Không, FS-3 yêu cầu tách khi > 500 dòng
- "**Viết T2 mà không có Design Patterns Table**" → Không, FS-4 bắt buộc bảng patterns

## Ví dụ lệnh

- `/tdd api-gateway` — "Viết TDD cho module API Gateway mới, thay thế NGINX Ingress"
- `/tdd payment-qr` — "Thiết kế module thanh toán QR code"
- `/tdd cache-refactor` — "TDD cho refactor caching strategy, chuyển sang Redis Cluster"
- "Review design doc này và bổ sung ADR cho phần chọn message broker"
- "Deep-dive vì sao chọn Postgres thay vì DynamoDB cho module ledger"
