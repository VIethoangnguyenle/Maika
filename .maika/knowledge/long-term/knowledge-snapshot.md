# Knowledge Snapshot — Kiến trúc Hệ thống
> Cập nhật lần cuối: —
> Cập nhật bởi: —

Đây là **source of truth kiến trúc tổng thể** của hệ thống.
Được tích luỹ bởi `knowledge-promoter` sau mỗi task hoàn thành.

> ⓘ **Đây là skeleton.** Khi `maika init` vào dự án của bạn, file này được seed rỗng;
> `knowledge-promoter` điền dần sau mỗi task. Điền các bảng dưới theo đúng format metadata.

---

## Quy ước Metadata Bắt buộc

Mọi entry trong file này đều phải có metadata inline theo format:

```
| Tên entry | ... | `source:{ticket-id hoặc doc-url}` `seen:{YYYY-MM}` `verified:{YYYY-MM}` `status:{active|outdated|superseded}` |
```

**Giải thích field:**

| Field | Ý nghĩa | Ai ghi | Cập nhật khi nào |
|-------|---------|--------|-----------------|
| `source` | Ticket-id hoặc URL tài liệu đầu tiên xác nhận thông tin này | knowledge-promoter | Lần đầu thêm vào |
| `seen` | Tháng/năm phát hiện lần đầu (`YYYY-MM`) | knowledge-promoter | Chỉ ghi một lần |
| `verified` | Tháng/năm xác nhận gần nhất còn đúng (`YYYY-MM`) | knowledge-promoter | Cập nhật mỗi khi task chạm vào entry này và confirm còn đúng |
| `status` | Trạng thái hiện tại của tri thức này | knowledge-promoter | Cập nhật khi có thay đổi |

**Quy tắc status:**

- `active` — Đang đúng, đã verified trong vòng 90 ngày hoặc chưa có lý do tin là thay đổi.
- `outdated` — Có dấu hiệu không còn đúng (ticket mới mâu thuẫn, refactor lớn) nhưng chưa xác nhận thay thế. Agent đọc với độ tin cậy **THẤP**.
- `superseded` — Đã được thay thế bởi entry mới hơn. Giữ để audit trail, **không dùng cho reasoning**.

**Quy tắc agent khi đọc:**
- Chỉ dùng entry `status:active` cho reasoning và spec.
- Entry `status:outdated` → phải ghi cảnh báo vào AGENT_TRANSPARENCY trước khi dùng.
- Entry `status:superseded` → bỏ qua hoàn toàn, chỉ đọc khi cần trace lịch sử.

---

## Tổng quan Hệ thống

<!-- Điền khi khám phá hệ thống: -->
- **Tên hệ thống**: <!-- vd: Acme Orders Service -->
- **Stack chính**: <!-- vd: ngôn ngữ / framework -->
- **Database**: <!-- vd: Postgres -->
- **Message Queue**: <!-- nếu có -->
- **Auth**: <!-- vd: JWT -->
- **Cache**: <!-- nếu có -->

---

## Tầng Database

### Bảng/Collection chính

| Tên | Loại | Mô tả ngắn | Metadata |
|-----|------|-----------|----------|
<!-- ví dụ: | `ORDERS` | TABLE | đơn hàng | `source:TICKET-1` `seen:2026-06` `verified:2026-06` `status:active` | -->

### Constraint & Trigger quan trọng

| Tên | Loại | Mô tả | Metadata |
|-----|------|-------|----------|
<!-- ví dụ: | `UQ_ORDER_NO` | UNIQUE | `(ORDER_NO)` | `source:TICKET-1` `seen:2026-06` `verified:2026-06` `status:active` | -->

---

## Kiến trúc Code

> Snapshot này chỉ ghi **sự thật** — module nào tồn tại, gọi gì, ở đâu.
> Quy tắc đặt tên/pattern → xem `conventions.yaml`; triết lý → xem `author-dna.yaml`.

### Module/Service chính

| Module | Package/Path | Vai trò | Metadata |
|--------|-------------|---------|----------|
<!-- ví dụ: | `OrderService` | `com.acme.order` | xử lý vòng đời đơn | `source:TICKET-1` `seen:2026-06` `verified:2026-06` `status:active` | -->

### Entry Points quan trọng

| Endpoint/Handler | Class | Mô tả | Metadata |
|-----------------|-------|-------|----------|
<!-- ví dụ: | POST /orders | `OrderController` | tạo đơn | `source:TICKET-1` `seen:2026-06` `verified:2026-06` `status:active` | -->

---

## Business Rules Đã Xác Nhận

| Rule | Mô tả | Metadata |
|------|-------|----------|
<!-- ví dụ: | BR-ORD-001 | đơn không được vượt hạn mức ngày | `source:TICKET-1` `seen:2026-06` `verified:2026-06` `status:active` | -->

---

## Integration & External Systems

| Hệ thống | Loại | Giao thức | Ghi chú | Metadata |
|---------|------|-----------|---------|----------|
<!-- ví dụ: | Payment GW | downstream | REST | thanh toán | `source:TICKET-1` `seen:2026-06` `verified:2026-06` `status:active` | -->

---

## Non-functional Notes

| Aspect | Mô tả | Metadata |
|--------|-------|----------|
<!-- ví dụ: | Caching | Redis TTL 5m | `source:TICKET-1` `seen:2026-06` `verified:2026-06` `status:active` | -->

---

## Cross-reference Index

> Snapshot chỉ chứa sự thật. Khi cần quy tắc hoặc triết lý → xem đúng store tương ứng.

| Topic | Quy tắc → conventions.yaml | Triết lý → author-dna.yaml |
|-------|---------------------------|---------------------------|
<!-- ví dụ: | Naming | `naming` → class_suffixes | — | -->

---

## Lịch sử cập nhật

| Ticket | Ngày | Hành động | Entries thêm | Entries updated |
|--------|------|-----------|-------------|----------------|
<!-- ví dụ: | TICKET-1 | 2026-06 | Initial snapshot | 5 | 0 | -->

---

## Outdated / Superseded Log

> Các entry đã bị đánh dấu `outdated` hoặc `superseded` được liệt kê tóm tắt ở đây để dễ audit.
> Không xoá chúng khỏi các section trên — chỉ cập nhật `status` field.

| Entry | Section | Status | Lý do | Ticket |
|-------|---------|--------|-------|--------|
| <!-- chưa có --> | | | | |

---

## [M3] Violation Pattern Tracking

> Section này được tự động cập nhật bởi `knowledge-promoter` sau mỗi task hoàn thành.
> Dùng để nhận diện các vi phạm rule/workflow lặp đi lặp lại để cải thiện hệ thống.

### Bảng Vi phạm Đã Ghi nhận

| Pattern | Rule bị vi phạm | Lần xảy ra | Task đầu tiên | Task gần nhất | Severity |
|---------|----------------|-----------|--------------|--------------|----------|
| <!-- chưa có --> | | | | | |

**Severity levels**: LOW (cosmetic), MEDIUM (workflow issue), HIGH (data integrity risk), CRITICAL (security/data loss)

### Quy tắc cập nhật

- Chỉ ghi pattern **đã xảy ra ≥ 2 lần** (không ghi one-off).
- Khi cùng pattern xảy ra lần mới: tăng "Lần xảy ra" và cập nhật "Task gần nhất".
- Không ghi tên user vào đây — chỉ ghi pattern hành vi.
- Định kỳ review: khi có ≥ 5 pattern → xem xét bổ sung rule mới vào RULES.md.
