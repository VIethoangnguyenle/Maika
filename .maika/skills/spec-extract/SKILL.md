---
name: spec-extract
version: '1.0'
standard: SP3
description: >
  Trích xuất spec có cấu trúc từ tài liệu (wiki/Confluence/PRD) vào REQUIREMENT.md, kèm đánh giá độ tin cậy.
  Dùng khi đầu vào là tài liệu dài, wiki nhiều trang, hoặc PRD cần parse.
  KHÔNG dùng cho: ticket có sẵn đã rõ scope (→ requirement-analyst),
  ideation/brainstorm (→ openspec-explore), khám phá DB schema (→ db-explorer).
pre_conditions:
  - file: "{{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md"
    condition: exists
    on_fail: "ABORT — bootstrap chưa chạy, gọi `/task` trước"
---

# Spec Extract — Tài liệu → REQUIREMENT

## Quy tắc cốt lõi (reflex)

> **UA-first khi trace code.** Thứ tự nguồn BẮT BUỘC:
> 1. **UA + kinh nghiệm** (agent-memory, knowledge-snapshot) — LUÔN trước. UA là bản đồ node (class/func/domain/flow/quan hệ/entry-point), KHÔNG chứa logic → dùng để trace/định vị.
> 2. **Codebase Memory** — hỗ trợ, vào SAU: extract logic trong thân hàm tại node UA đã định vị.
> 3. **grep** — fallback cuối.
>
> Khi tài liệu mô tả luồng đã/đang tồn tại: UA-first probe verify trong code TRƯỚC khi ghi gap hoặc hỏi user.

## 1. Mục tiêu

- Biến 1 (hoặc nhiều) tài liệu dạng tự do (wiki, Confluence, PRD, SRS, ghi chú…) thành **khối yêu cầu có cấu trúc** trong `{{ platform.framework_root }}/knowledge/active/REQUIREMENT.md`.
- Không copy-paste nguyên văn, mà rút ra và chuẩn hoá thành:
  - Tác nhân (actor), use case, mục tiêu.
  - Luồng chính và luồng lỗi ở mức business.
  - Quy tắc nghiệp vụ (business rules).
  - Acceptance Criteria (nếu có thể).
  - Ràng buộc phi chức năng (non-functional constraints).
- Đánh giá **Độ tin cậy** của tài liệu (CAO/TRUNG BÌNH/THẤP) và chỉ rõ lỗ hổng.

#### ASCII Flow / State Diagram

Bắt buộc thêm block `#### ASCII Flow / State Diagram` vào phần yêu cầu trích từ tài liệu khi tài liệu có flow, state, integration, callback, job, hoặc data path.

Áp dụng khi gặp:
- Luồng chính có nhiều bước.
- Luồng lỗi, retry, fallback, cancellation, hoặc nhánh xử lý.
- State transition / lifecycle.
- Integration boundary nội bộ ↔ bên ngoài.
- Callback, webhook, scheduled job, queue, event, hoặc async handoff.
- Data path qua module/service/table/DTO/third-party field.

Nếu evidence chưa đủ, diagram phải đánh dấu phần chưa chắc là `unknown`, `assumption`, hoặc `needs BA/PO confirmation`. Không vẽ diagram như fact khi nguồn chỉ cho phép suy luận.

Skill này tập trung **đọc – hiểu – tóm tắt có cấu trúc**, không thay thế `requirement-analyst` mà bổ sung cho nó.

---

## 2. Khi nào dùng

Dùng `spec-extract` khi:

- `/task` Pha 1 với input kiểu `HAS_DOC_ONLY` (có tài liệu, chưa có ticket rõ ràng).
- `/task` Pha 1 với input `HAS_JIRA` nhưng ticket có kèm link tới:
  - Confluence/wiki/PRD/BRS/SRS/Tech Spec, và tài liệu này chứa phần lớn nội dung yêu cầu.
- Cần gom thông tin rải rác từ nhiều trang tài liệu về **cùng một chủ đề** vào `REQUIREMENT`.

Không dùng `spec-extract` cho:

- Tài liệu hoàn toàn kỹ thuật không mang tính yêu cầu (log, dump, raw API trace…).
- Việc sinh spec kỹ thuật chi tiết cho implementation (đó là job của OpenSpec `/opsx:propose`).

---

## Khi nào KHÔNG sử dụng

- Khi ticket có sẵn đã rõ scope (→ requirement-analyst).
- Khi cần ideation/brainstorm ý tưởng thô (→ openspec-explore).
- Khi cần khám phá DB schema, constraint (→ db-explorer).
- Khi cần sinh spec kỹ thuật chi tiết cho implementation (→ openspec-propose).

---

## 3. Input / Output

### Input

- 1 URL tài liệu chính (wiki/Confluence/PRD…).
- (Tuỳ chọn) Các URL trang con / tài liệu liên kết từ trang chính:
  - Flow chi tiết.
  - Bảng rule.
  - API spec.
- (Tuỳ chọn) Bối cảnh ngắn user cung cấp:
  - Trang nào là “nguồn chuẩn”.
  - Phần nào của tài liệu liên quan tới task hiện tại.

### Output

Cập nhật `{{ platform.framework_root }}/knowledge/active/REQUIREMENT.md`:

- Thêm section (hoặc cập nhật) `### Yêu cầu nghiệp vụ trích từ tài liệu`.
- Skeleton tối thiểu: Bối cảnh & mục tiêu; Actor & Use Case; Luồng chính; Luồng lỗi / ngoại lệ; Quy tắc nghiệp vụ; Acceptance Criteria; Ràng buộc phi chức năng; Integrations & Field Mapping; ASCII Flow / State Diagram; Độ tin cậy tài liệu; Lỗ hổng & câu hỏi mở.
- Xem [references/output-schema.md](references/output-schema.md) khi cần output schema đầy đủ để cập nhật `REQUIREMENT.md`.

---

## 4. Quy trình chi tiết

- Bước 1 — Xác định & thu thập nguồn: nhận URL/từ khoá, chọn trang gốc và trang con cần đọc.
- Bước 2 — Lấy nội dung tài liệu: dùng MCP/wiki để lấy markdown/plain text, child pages, attachment cần thiết.
- Bước 3 — Nhận diện cấu trúc nội dung: map section yêu cầu, bối cảnh, rule, flow, API/interface và constraint.
- Bước 4 — Trích Actor & Use Case: liệt kê actor, use case và goal ở mức business.
- Bước 5 — Trích luồng chính và luồng lỗi: giữ thứ tự logic, không thêm bước không có cơ sở.
- Bước 5b — Thống kê Integration & Field Mapping: phát hiện integration, map field third-party sang canonical bằng UA-first.
- Bước 5c — Vẽ ASCII Flow / State Diagram: biểu diễn trình tự, boundary, và nhánh quan trọng bằng ASCII khi tài liệu có flow/state/data path.
- Bước 6 — Trích quy tắc nghiệp vụ: tách rule thành bullet rõ ràng, độc lập.
- Bước 7 — Trích Acceptance Criteria & ràng buộc phi chức năng: chỉ chuyển thành AC khi có cơ sở an toàn.
- Bước 8 — Merge vào REQUIREMENT.md: merge cẩn thận, không xoá phần đã có, ghi rõ nguồn.
- Bước 9 — Đánh giá Độ tin cậy tài liệu: gán CAO/TRUNG BÌNH/THẤP và lý do.
- Bước 10 — Ghi lỗ hổng & câu hỏi cần làm rõ: probe UA-first trước khi biến gap thành câu hỏi cho user.

Xem [references/quy-trinh-chi-tiet.md](references/quy-trinh-chi-tiet.md) khi cần thực thi chi tiết từng bước, ví dụ, sub-rule hoặc quy trình Integration & Field Mapping.

## 5. Cập nhật AGENT_TRANSPARENCY

Trong `{{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md`:

- Đánh dấu:
  - `[x] spec-extract`
  - `[x] Tài liệu (wiki/Confluence/PRD)` đã đọc.
- Ghi:
  - Độ tin cậy tài liệu (CAO/TRUNG BÌNH/THẤP) và lý do ngắn.
  - Nếu THẤP:
    - Cảnh báo rõ ràng: “Spec trích từ tài liệu có độ tin cậy THẤP, cần BA/PO cập nhật trước khi tiến xa hơn.”
- Link (hoặc ID) các trang tài liệu chính đã dùng để dễ trace về sau.

---

## [L3] Staleness Warning — Tài liệu > 6 tháng

Khi `spec-extract` đọc tài liệu nguồn, kiểm tra ngày cập nhật cuối:

```
FUNCTION check_doc_staleness(doc_url_or_path):
  1. Đọc metadata tài liệu: last_modified, last_updated, hoặc page footer date
  2. Nếu last_modified > 6 tháng trước today:
     → Ghi cảnh báo STALENESS vào AGENT_TRANSPARENCY:
        "[L3-STALE] Tài liệu '{doc_url}' cập nhật lần cuối: {date} ({n} tháng trước).
         Có thể không phản ánh yêu cầu hiện tại."
     → Hạ Độ tin cậy của spec-extract output xuống mức THẤP (nếu chưa THẤP)
     → Thông báo user: "Tài liệu này đã {n} tháng chưa cập nhật. Confirm vẫn dùng?"
  3. Nếu không tìm được ngày (metadata thiếu):
     → WARN: "Không xác định được ngày tài liệu — giả định có thể stale."
  4. Nếu last_modified trong 6 tháng → bình thường, không cần cảnh báo

THRESHOLD: 180 ngày (6 tháng)

OUTPUT trong REQUIREMENT.md:
  Thêm vào section "Nguồn tài liệu":
  - URL/path của tài liệu
  - Ngày cập nhật cuối (nếu biết)
  - Staleness warning (nếu có)
```

**Áp dụng cho**: tất cả tài liệu đầu vào (Confluence, wiki, PRD, SRS, Google Doc).
