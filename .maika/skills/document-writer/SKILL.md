---
name: document-writer
version: '1.0'
description: >
  Khung chuẩn để tạo mới hoặc cập nhật tài liệu kỹ thuật cho nhiều loại tài liệu:
  README, overview, architecture/design doc, how-to, runbook, ADR, và tài liệu module hạ tầng.
  Dùng khi cần tạo, viết lại, hoặc cập nhật tài liệu kỹ thuật trong dự án.
  KHÔNG dùng cho: viết TDD 5 tầng (→ infra-tdd), sinh spec OpenSpec (→ openspec-propose),
  chuẩn hoá requirement (→ requirement-analyst).
---

# Document Writer — Khung Viết Tài liệu Kỹ thuật

## Khi nào sử dụng

Sử dụng skill này trước và trong khi tạo mới hoặc cập nhật tài liệu kỹ thuật như:
- `README.md`
- tài liệu trong `docs/`
- architecture/design docs
- quick start/how-to guides
- runbook/troubleshooting
- ADRs
- tài liệu tổng quan module hạ tầng hoặc common modules

> **Manual-only:** skill này được gọi trực tiếp (manual) — không `/task` workflow nào auto-route tới nó. Orphan status là có chủ đích, không phải thiếu sót.

## Mục tiêu

Tạo ra tài liệu:
- đúng với source code hoặc nguồn sự thật hiện có
- giải thích đúng mức độ “Why” theo loại tài liệu
- dễ đọc, dễ bảo trì, dễ cập nhật cùng vòng đời code
- tránh lan man, tránh lặp lại, tránh bịa đặt

## Khi nào KHÔNG sử dụng

- Khi cần viết TDD 5 tầng (→ infra-tdd).
- Khi cần sinh spec kỹ thuật OpenSpec (→ openspec-propose).
- Khi cần chuẩn hoá requirement (→ requirement-analyst).
- Khi cần review kiến trúc, đánh giá rủi ro (→ architecture-reviewer).

---

## Quy trình

### Giai đoạn 1: Xác định loại tài liệu

Trước khi viết, agent PHẢI xác định loại tài liệu cần tạo/cập nhật:

1. README / Overview
2. Architecture / Design document
3. How-to / Usage guide
4. Runbook / Troubleshooting
5. ADR / Decision record
6. Module reference / Infrastructure module document

Nếu chưa xác định được, agent PHẢI hỏi lại người dùng.

## Giai đoạn 2: Thu thập thông tin vừa đủ

Agent thu thập thông tin theo nhu cầu của loại tài liệu, không mặc định ép mọi tài liệu phải có toàn bộ mục dưới đây.

### Thông tin ưu tiên

1. Bài toán / bối cảnh: module hoặc tài liệu này phục vụ mục đích gì?
2. Phạm vi: tài liệu này bao phủ gì và không bao phủ gì?
3. Cách dùng hoặc luồng chính: người đọc cần làm gì sau khi đọc?
4. Kiến trúc / quyết định thiết kế: áp dụng khi tài liệu có tính architecture hoặc module nền tảng.
5. Ràng buộc / trade-off / caveats: các điều cần biết để tránh dùng sai.
6. Bằng chứng: source code, config, ADR, issue, commit, tài liệu gốc, hoặc xác nhận từ người dùng.

### Thông tin tùy chọn

- Tác giả kiến trúc, người triển khai, người tham vấn.
- Lịch sử version / migration.
- Quan hệ phụ thuộc với các module khác.

Chỉ yêu cầu các thông tin này khi chúng thực sự làm tài liệu tốt hơn hoặc khi người dùng muốn ghi nhận rõ ràng.

## Giai đoạn 3: Quy tắc bằng chứng

- Mọi mô tả về class, handler, service, config, API, dependency hiện hữu PHẢI được xác minh từ source code hoặc nguồn đáng tin cậy.
- Mọi giải thích về “ý định thiết kế” nên dựa trên ADR, issue, commit, hoặc xác nhận từ người phụ trách nếu có.
- Nếu chưa đủ bằng chứng, agent KHÔNG được suy diễn như thể đó là sự thật đã xác minh.
- Khi cần, ghi rõ một trong các trạng thái:
  - “Đã xác minh từ source code”
  - “Suy ra từ cấu trúc hiện tại, chưa có xác nhận trực tiếp”
  - “Đề xuất / dự kiến”
  - “Chưa được xác minh”

## Giai đoạn 4: Chọn cấu trúc phù hợp

### A. README / Overview
- Mục đích
- Phạm vi
- Thành phần chính
- Quick start
- Link tới tài liệu chi tiết hơn
- Lưu ý quan trọng

### B. Architecture / Design document
- Bối cảnh và bài toán
- Mục tiêu / phi mục tiêu
- Ràng buộc
- Kiến trúc đề xuất hoặc hiện tại
- Design patterns / quyết định chính
- Alternatives considered / trade-offs
- Sơ đồ
- Tác động vận hành và downstream considerations

### C. How-to / Usage guide
- Khi nào dùng
- Điều kiện tiên quyết
- Các bước thực hiện
- Ví dụ ngắn gọn
- Lỗi thường gặp / caveats

### D. Runbook / Troubleshooting
- Triệu chứng
- Cách chẩn đoán
- Các bước xử lý
- Rollback / recovery
- Escalation / owner

### E. ADR
- Context
- Decision
- Alternatives considered
- Consequences
- Status

## Giai đoạn 5: Visualize đúng chỗ

- Với architecture/design docs hoặc tài liệu module nền tảng, ưu tiên dùng Mermaid để minh họa context, container, component, flow hoặc sequence.
- Với README hoặc how-to ngắn, chỉ dùng Mermaid khi nó thực sự giúp hiểu nhanh hơn.
- Không thêm sơ đồ chỉ để “đủ form”.

## Giai đoạn 6: Cách viết

- Viết bằng tiếng Việt rõ ràng, chuẩn mực, sát nghĩa.
- Ưu tiên giải thích cho người đọc biết:
  - đây là gì
  - dùng khi nào
  - tại sao thiết kế như vậy (nếu phù hợp)
  - cần lưu ý gì để không dùng sai
- Không nhồi quá nhiều code vào phần mở đầu.
- Ví dụ code phải ngắn, đúng ngữ cảnh, và ưu tiên use case đơn giản nhất trước.
- Nếu có ghi nhận công sức, hãy viết ngắn gọn và tự nhiên; không biến tài liệu thành phần vinh danh.

## Giai đoạn 7: Đồng bộ tài liệu

Chỉ chạy sync checks khi thay đổi nằm trong phạm vi cần đồng bộ, ví dụ:
- cập nhật overview module thì rà soát mục lục hoặc tài liệu tổng hợp liên quan
- thay đổi version hoặc migration thì áp dụng documentation sync protocol
- thay đổi dependency hoặc module map thì rà soát sơ đồ phụ thuộc

Không áp dụng đồng bộ toàn cục nếu thay đổi chỉ là chỉnh câu chữ nhỏ hoặc how-to cục bộ.

## Giai đoạn 8: Validation

Trước khi hoàn tất, agent PHẢI kiểm tra:
1. Tài liệu có đúng loại tài liệu không?
2. Có phần nào đang suy diễn mà chưa gắn nhãn không?
3. Ví dụ và tên thành phần có đúng với source code không?
4. Có phần nào dài nhưng không hữu ích không?
5. Có lặp lại nội dung đã tồn tại ở nơi khác không? Nếu có, nên link thay vì chép lại.

## Nguyên tắc cốt lõi

> Code trả lời “How”. Tài liệu nên ưu tiên trả lời “What”, “When”, và “Why” ở mức phù hợp với loại tài liệu.

> Tài liệu tốt không phải là tài liệu dài nhất; đó là tài liệu đúng, ngắn gọn, cập nhật, và giúp người đọc hành động đúng.

> Ghi nhận công sức khi phù hợp, đặc biệt với các module nền tảng hoặc quyết định kiến trúc quan trọng; nhưng luôn giữ văn phong tiết chế, chuyên nghiệp.

---

## Đầu ra

- **File tài liệu**: Vị trí tuỳ loại (`README.md`, `docs/`, `docs/tdd/`, v.v.).
- **Định dạng**: Markdown, tiếng Việt, theo cấu trúc chuẩn của loại tài liệu tương ứng.
- **Chất lượng**: Đã qua validation 5 điểm (Giai đoạn 8) trước khi hoàn tất.
## Tài liệu tham khảo — Nguyên tắc viết tài liệu kỹ thuật

> Khi project có bộ tài liệu mẫu (gold standard), agent nên tham khảo format và cấu trúc từ đó.
> Nếu chưa có, áp dụng các nguyên tắc chung dưới đây.

### Nguyên tắc chung

- **Attribution Header**: Mỗi tài liệu nên có credit (tác giả, reviewer, thời gian cập nhật).
- **Hub + Sub-doc**: Khi tài liệu > 500 dòng, tách thành file hub (mục lục) + sub-docs chi tiết.
- **Navigation**: Mỗi file nên có link `← Trước` / `Tiếp theo →` / `Mục lục`.
- **Code Examples**: Ưu tiên format NÊN/KHÔNG NÊN để rõ best practices vs anti-patterns.
- **Troubleshooting**: Dùng format "Triệu chứng → Nguyên nhân → Xử lý".

