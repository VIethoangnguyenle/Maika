# ADR-{NNNN}: {Tiêu đề bắt đầu bằng động từ thì hiện tại}

> **Trạng thái**: Proposed | Accepted | Deprecated | Superseded bởi [ADR-NNNN](./NNNN-title.md)
> **Ngày**: {YYYY-MM-DD}
> **Tác giả**: {tên}
> **Người quyết định**: {tên — người có quyền chốt}
> **TDD liên quan**: [{tên module}-TDD](../{module}-TDD.md)

---

## Bối cảnh

> Mô tả tình huống buộc phải ra quyết định. Bao gồm:
> - **Lực tác động** (forces) đang kéo về nhiều hướng khác nhau
> - **Ràng buộc** từ hệ thống, compliance, team, timeline
> - **Trigger** — chuyện gì xảy ra khiến phải quyết định ngay bây giờ?
>
> Viết bối cảnh như thể người đọc chưa biết gì về hệ thống.
> Tham chiếu evidence từ: UA Knowledge Graph, Codebase Memory search, DB schema, production evidence.

## Quyết định

> **Chúng ta chọn {Alternative X}.**
>
> Viết 1-3 đoạn giải thích rõ quyết định, bao gồm:
> - Cụ thể chọn cái gì (không mơ hồ)
> - Phạm vi áp dụng (module nào, team nào, từ khi nào)
> - Điều kiện để xem xét lại quyết định này

## Alternatives đã xem xét

### Alternative A — {tên}

- **Mô tả**: {1-2 câu}
- **Ưu điểm**: {liệt kê}
- **Nhược điểm**: {liệt kê}
- **Lý do không chọn**: {1 câu quyết định}

### Alternative B — {tên}

- **Mô tả**: {1-2 câu}
- **Ưu điểm**: {liệt kê}
- **Nhược điểm**: {liệt kê}
- **Lý do không chọn**: {1 câu quyết định}

### Alternative C — {tên} ✅ Đã chọn

- **Mô tả**: {1-2 câu}
- **Ưu điểm**: {liệt kê}
- **Nhược điểm**: {liệt kê — phải thành thật}

## Ma trận đánh giá

| Tiêu chí (trọng số) | Alt A | Alt B | Alt C ✅ |
|----------------------|-------|-------|----------|
| {tiêu chí 1} ({X}%) | {điểm + giải thích ngắn} | | |
| {tiêu chí 2} ({X}%) | | | |
| {tiêu chí 3} ({X}%) | | | |
| **Tổng điểm** | **X.X** | **X.X** | **X.X** |

> **Quy ước**: ✅ = tốt (3đ), ⚠️ = chấp nhận được (2đ), ❌ = kém (1đ). Tổng = Σ(điểm × trọng số).

## Hệ quả (Consequences)

### Tích cực
- {hệ quả tốt 1}
- {hệ quả tốt 2}

### Tiêu cực (Trade-off chấp nhận)
- {cái mất 1 — cụ thể, không mơ hồ}
- {cái mất 2}

### Rủi ro đã nhận diện
- {rủi ro 1} → mitigation: {cách giảm thiểu}
- {rủi ro 2} → mitigation: {cách giảm thiểu}

## Bằng chứng

> Liệt kê evidence hỗ trợ quyết định:
> - Benchmark/PoC kết quả
> - Production data / operational history
> - UA Knowledge Graph references (node IDs, relationships)
> - Codebase Memory search results
> - DB schema constraints
> - Tài liệu/paper/blog kỹ thuật

## Ghi chú

> Thông tin bổ sung, discussion notes, hoặc context không khớp vào sections trên.
