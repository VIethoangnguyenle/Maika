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

## Cấu trúc 5 Tầng (Hybrid)

| Tầng | Đối tượng đọc | Mục đích | Phải trả lời |
|------|---------------|----------|--------------|
| **T0 — Bối cảnh Nghiệp vụ** | BA, PM, Stakeholder | Giải thích ý tưởng | Nghiệp vụ này giải quyết gì? User trải qua flow nào? Quy tắc kinh doanh là gì? |
| **T1 — Chiến lược** | Tech Lead, Architect | Đặt vấn đề kỹ thuật | Ai đang bị đau? Metric nào cải thiện? Ai ký duyệt? |
| **T2 — Kiến trúc** | Dev, Architect | Mô tả hệ thống | Component, ranh giới, data flow, failure domain là gì? |
| **T3 — Quyết định** | Dev, Architect | Biện minh lựa chọn | Đã xem xét những alternative nào? Tại sao chọn cái này? Trade-off chấp nhận là gì? |
| **T4 — Vận hành** | Tech Leads, Trưởng phòng | Giám sát & cấu hình | Monitoring metrics, alert thresholds, configuration reference |

Template đầy đủ nằm ở `assets/TDD_TEMPLATE.md`. Copy nó làm điểm bắt đầu cho mọi document mới.

---

## Knowledge-First Protocol — BẮT BUỘC

> ⚠️ **KHÔNG ĐƯỢC viết bất kỳ section TDD nào khi chưa chạy knowledge tools tương ứng.**
> Mọi claim trong TDD phải dựa trên evidence thực tế từ codebase, database, hoặc knowledge graph — không phải suy đoán.

### Trước khi viết mỗi tầng, agent PHẢI thực hiện:

#### T0 — Bối cảnh Nghiệp vụ
```
PHẢI ĐỌC: Tài liệu nghiệp vụ gốc (SRS, BRD, Confluence) nếu có
PHẢI GỌI: {{ tools.get_symbol }} → hiểu business domain và layer boundaries
PHẢI GỌI: {{ tools.trace_flow }} → guided walkthrough để hiểu flow end-to-end
NẾU CÓ: User story, use case diagram → trích xuất business rules
QUY TẮC: KHÔNG dùng thuật ngữ kỹ thuật — viết cho người không biết code đọc
```

#### T1 — Chiến lược
```
PHẢI ĐỌC: {{ platform.framework_root }}/knowledge/long-term/knowledge-snapshot.md
PHẢI GỌI: codebase-explorer → map module liên quan trong hệ thống
PHẢI GỌI: {{ tools.search_code }} → tìm component hiện tại và pain points
NẾU CÓ: Tài liệu/ticket/operational evidence → spec-extract hoặc đọc trực tiếp
```

#### T2 — Kiến trúc
```
PHẢI GỌI: {{ tools.get_dependencies }} → dependency map giữa components
PHẢI GỌI: {{ tools.trace_flow }} → call flow thực tế
PHẢI GỌI: {{ tools.search_code }} → tìm implementation patterns
PHẢI GỌI: {{ tools.get_dependencies }} → dependency graph
PHẢI GỌI: db_access (db-explorer) → schema, constraints, indexes liên quan
KẾT QUẢ: Mọi sơ đồ phải phản ánh code/DB thực tế, không phải giả định
```

#### T3 — Quyết định
```
PHẢI GỌI: {{ tools.find_blast_radius }} → blast radius của mỗi alternative
PHẢI GỌI: {{ tools.find_blast_radius }} → files/modules bị ảnh hưởng
PHẢI GỌI: db_access (db-explorer) → data model constraints ảnh hưởng lựa chọn
PHẢI CHẠY: Socratic deep-dive protocol (references/socratic-deep-dive.md)
KẾT QUẢ: Mỗi ADR phải có evidence từ codebase, không chỉ opinion
```

#### T4 — Vận hành
```
PHẢI GỌI: codebase-explorer → tìm monitoring metrics, alert patterns hiện có
PHẢI GỌI: {{ tools.search_code }} → tìm existing metric/alert/config patterns
KẾT QUẢ: T4 chỉ chứa Monitoring Metrics table + Configuration Reference
KHÔNG VIẾT: Troubleshooting Runbook — tài liệu này dành cho management, không phải SRE ops
```

### Graceful Degradation

Nếu một MCP tool không khả dụng:
- **Ghi rõ** trong TDD section: "⚠️ [tool] không khả dụng — section này dựa trên [source thay thế]"
- **Hạ độ tin cậy** của section đó
- **KHÔNG block** — tiếp tục với evidence có sẵn, nhưng phải thành thật về gaps

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

## Format Standards

> Các quy tắc format dưới đây đảm bảo tính nhất quán, dễ đọc, và dễ bảo trì cho toàn bộ bộ TDD.
> Kết hợp cùng hybrid 5-layer (T0-T4) để tạo trải nghiệm đọc liền mạch.

### FS-1: Attribution Header

Mỗi TDD file **PHẢI** có attribution block ở đầu file, ngay sau tiêu đề. Dùng format **single-line blockquote** để đảm bảo PDF render đúng:

```markdown
> **Attribution** - **Author**: {tên} - **Domain**: {module} - **Date**: {YYYY-MM} - **Security Level**: Internal
```

⚠️ **KHÔNG** dùng bullet list (`> -`) trong blockquote — mkdocs-with-pdf sẽ gộp thành 1 dòng mất format.

### FS-2: Navigation Footer

Mỗi TDD file **PHẢI** có navigation footer ở cuối file:

```markdown
---
**[← TDD trước](./prev-TDD.md)** | **[Mục lục](./00-index.md)** | **[TDD tiếp theo →](./next-TDD.md)**
```

Thứ tự navigation theo dependency graph trong `00-index.md` (Foundation → Transaction → Approval → ...).

### FS-3: Hub + Sub-doc Pattern

Khi TDD **vượt quá 500 dòng**, PHẢI tách thành hub + sub-docs:

```
docs/tdd/
├── <module>-TDD.md              ← Hub file (mục lục + tổng quan)
└── <module>/
    ├── <module>-01-overview.md   ← Sub-doc chi tiết
    ├── <module>-02-architecture.md
    └── <module>-03-operations.md
```

Hub file chỉ chứa: mục lục, Design Patterns Summary Table, dependency map. Chi tiết T0-T4 nằm trong sub-docs.



### FS-4: Design Patterns Summary Table

Mỗi TDD **PHẢI** có bảng tổng hợp Design Patterns ở đầu T2 Architecture:

```markdown
| Pattern | Áp dụng tại | Vai trò |
|---------|-------------|---------|
| Template Method | BaseHandler (pre → around → post) | Khung xử lý cố định, subclass override từng bước |
| Strategy | ConfirmType routing | Chọn luồng xử lý tại runtime |
```



### FS-5: Code Examples (NÊN / KHÔNG NÊN)

T2 Architecture **NÊN** có ít nhất 1 code example theo format:

```markdown
#### ✅ NÊN
```java
// Code đúng pattern
```

#### ❌ KHÔNG NÊN
```java
// Anti-pattern
```
```



### FS-6: Configuration Reference trong T4

T4 Vận hành **PHẢI** có bảng Configuration Reference:

```markdown
### Configuration Reference

| Config | Mô tả | Default |
|--------|-------|---------|
| {config key} | {mô tả chức năng} | {giá trị mặc định hoặc file tham chiếu} |
```

> **Lưu ý**: Troubleshooting Runbook **KHÔNG** nằm trong TDD. Đối tượng đọc chính của TDD là Trưởng phòng và Tech Leads — nội dung vận hành chi tiết (symptom/cause/fix) thuộc tài liệu ops riêng.



### FS-7: Developer Checklist (tùy chọn)

Nếu TDD mô tả pattern mà developer cần follow (tạo Handler mới, tạo Factory mới...), bổ sung:

```markdown
### Checklist: Thêm {feature} mới

| Bước | Tạo | Kế thừa | Ví dụ |
|------|-----|---------|-------|
| 1 | ... | ... | ... |
```

### FS-8: Blank Line trước Bullet List (PDF compatibility)

mkdocs-with-pdf gộp text thành 1 dòng inline nếu thiếu dòng trống trước bullet list. **BẮT BUỘC** có blank line trong 3 trường hợp:

**Trường hợp 1 — Bold header + bullet list** (ADR Consequences, Contract...):

```markdown
<!-- ✅ ĐÚNG -->
**Consequences**:

- Item 1
- Item 2

<!-- ❌ SAI — PDF render thành 1 dòng -->
**Consequences**:
- Item 1
```

**Trường hợp 2 — Mô tả text + bullet link** (Hub files):

```markdown
<!-- ✅ ĐÚNG -->
### 1. Tầng Nghiệp vụ (T0)
Bối cảnh nghiệp vụ, quy tắc kinh doanh chung.

- 📖 **[T0 Bối cảnh Nghiệp vụ](./pf-01-business.md)**

<!-- ❌ SAI — mô tả và link dính 1 dòng -->
### 1. Tầng Nghiệp vụ (T0)
Bối cảnh nghiệp vụ, quy tắc kinh doanh chung.
- 📖 **[T0 Bối cảnh Nghiệp vụ](./pf-01-business.md)**
```

**Trường hợp 3 — Plain text + bullet list** (Architecture bài toán, yêu cầu...):

```markdown
<!-- ✅ ĐÚNG -->
Các yêu cầu chính:

- **Multi-stage flexible** — 1-3 cấp duyệt
- **Race-free** — concurrent actions

<!-- ❌ SAI — bullets dính vào text -->
Các yêu cầu chính:
- **Multi-stage flexible** — 1-3 cấp duyệt
```

**Quy tắc chung**: Bất kỳ dòng text nào ngay trước `- ` (bullet) đều **phải** có 1 blank line xen giữa.

### FS-9: Không dùng Numbered List trong ADR (PDF indentation bug)

mkdocs-with-pdf (WeasyPrint) coi mọi text sau numbered list (`1. 2. 3.`) vẫn là continuation của list item cuối cùng → các phần **Decision**, **Consequences** bị thụt lề sai.

**Quy tắc**: Trong ADR, phần **Alternatives** phải dùng **bullet list** (`- `), KHÔNG dùng numbered list (`1. 2. 3.`). Ghi số option vào tên:

```markdown
<!-- ✅ ĐÚNG — bullet list, Decision/Consequences không bị thụt -->
**Alternatives**:

- **Option 1: Template Method** — Base class skeleton → Type-safe, dễ debug
- **Option 2: AOP** — Annotations → Khó debug, ẩn side-effects
- **Option 3: Middleware** — Filter chain → Thiếu type safety

**Decision**: Option 1 — Template Method.

**Consequences**:

- ✅ Consistent codebase
- ⚠️ Inheritance depth cần kiểm soát

<!-- ❌ SAI — numbered list khiến Decision/Consequences thụt lề -->
**Alternatives**:

1. **Template Method** — ...
2. **AOP** — ...
3. **Middleware** — ...

**Decision**: Option 1   ← BỊ THỤT VÀO DƯỚI ITEM 3!
```

### FS-10: Mermaid Line Break — dùng `<br/>`, KHÔNG dùng `\n`

Kroki (mermaid renderer trong mkdocs) render `\n` thành **literal text** `\n` thay vì xuống dòng. **BẮT BUỘC** dùng `<br/>`:

```markdown
<!-- ✅ ĐÚNG -->
A["Người dùng chọn<br/>phương thức xác thực"]

<!-- ❌ SAI — hiển thị literal \n -->
A["Người dùng chọn\nphương thức xác thực"]
```

Ngoài ra, nếu diagram có nhiều node ngang (>4), ưu tiên layout `LR` (left-right) thay vì `TB` (top-bottom) để tránh diagram quá rộng bị tràn/che nội dung trong PDF.

## Tài nguyên đi kèm

- `assets/TDD_TEMPLATE.md` — template điền sẵn (5 tầng hybrid + checklist)
- `assets/ADR_TEMPLATE.md` — template ADR format MADR
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
