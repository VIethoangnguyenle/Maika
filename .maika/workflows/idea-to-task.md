---
description: Chuyển kết quả ideation thành draft ticket + gợi ý chạy /task spec.
---

# /idea-to-task — Từ ý tưởng sang task cụ thể

Dùng khi:

- Đã có file `ideation-*.md` trong `{{ platform.framework_root }}/knowledge/active/ideation/` với phần **“Đề xuất scope task”** và AC gợi ý tương đối rõ.
- User muốn biến ý tưởng đã được mổ xẻ thành **task chính thức** trong hệ thống ticket (Jira/…).

Mục tiêu:

- Trích thông tin cốt lõi từ ideation → sinh **draft ticket** (summary, description, AC) sẵn sàng để:
  - Tạo task trên hệ thống ticket.
  - Sau đó đi tiếp với `/task <ticket-id-or-link>`.

---

## 1. Input / Output

### Input

- Tên/slug của file ideation (nếu user cung cấp), hoặc
- Yêu cầu chung: “convert ý tưởng gần đây thành task”.

### Output

- Một **draft ticket** với:
  - Summary: câu ngắn gọn mô tả mục tiêu.
  - Description:
    - Bối cảnh & vấn đề.
    - Phạm vi (in-scope / out-of-scope).
    - Ghi chú kỹ thuật quan trọng (nếu đã có trong ideation).
  - Acceptance Criteria: checklist từ phần AC gợi ý trong ideation.
- (Tuỳ tích hợp) Nếu có MCP tới ticket system:
  - Ticket được tạo tự động (trả về key/URL).
- Cập nhật file ideation (tuỳ chọn) với:
  - Thông tin ticket đã tạo (id/key, thời gian).
- Cập nhật `{{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md`:
  - Đã chuyển hoá ideation nào → ticket nào.

---

## 2. Quy trình chi tiết

### Bước 1 — Chọn file ideation

1. Nếu user cung cấp tên/slug:
   - Tìm file khớp nhất trong `{{ platform.framework_root }}/knowledge/active/ideation/`.
   - Nếu có nhiều match gần giống, hỏi user chọn.
2. Nếu user không chỉ rõ:
   - Liệt kê một vài file ideation **gần đây nhất**:
     - Kèm tóm tắt ngắn từng file (1–2 câu lấy từ nội dung).
   - Hỏi user chọn 1 file để chuyển hoá.

Nếu không tìm được file phù hợp → thông báo rõ, đề nghị user chạy lại `/task <ý-tưởng>` để tạo ideation trước.

---

### Bước 2 — Trích xuất thông tin từ ideation

Từ nội dung file ideation đã chọn, lấy các phần:

- **Tóm tắt ý tưởng**:
  - Câu mô tả ngắn nhất thể hiện “tại sao nên làm”.
- **Động lực**:
  - Lợi ích, pain point, rủi ro nếu không làm.
- **Đề xuất scope task**:
  - Những gì được đề xuất làm trong task đầu tiên (MVP / slice đầu tiên).
- **AC gợi ý** (nếu có):
  - Các tiêu chí high-level để coi task là xong.
- (Tuỳ chọn) **Ghi chú kỹ thuật**:
  - Module/codebase nào liên quan, constraint kỹ thuật, dependency quan trọng.

Nếu ideation thiếu một trong các phần trên:

- Vẫn có thể sinh draft, nhưng cần:
  - Ghi rõ chỗ trống trong draft là “cần user bổ sung”.
  - Không tự bịa thêm requirement.

---

### Bước 3 — Sinh draft ticket

Dùng thông tin ở Bước 2 để dựng draft cho hệ thống ticket (Jira/…):

1. **Summary**:

   - 1 câu ngắn, rõ ràng, mô tả mục tiêu chính, ưu tiên ngôn ngữ business (không quá kỹ thuật).
   - Ví dụ pattern (generic):
     - “Enable [actor] to [do X] so that [benefit].”
     - Hoặc: “Implement [capability] for [actor] to [goal].”

2. **Description**:

   - **Bối cảnh & vấn đề**:
     - Lấy từ “Tóm tắt ý tưởng” + “Động lực”.
   - **Mục tiêu**:
     - Nói rõ trạng thái “thành công” nhìn từ góc user/business.
   - **Phạm vi (In-scope / Out-of-scope)**:
     - In-scope: nội dung từ “Đề xuất scope task”.
     - Out-of-scope: những thứ được nêu là “chưa làm ở phase này” trong ideation (nếu có).
   - **Ghi chú kỹ thuật quan trọng** (nếu ideation có):
     - Các module / hệ thống / constraint kỹ thuật nên được dev chú ý.

3. **Acceptance Criteria (AC)**:

   - Biến AC gợi ý trong ideation thành checklist, mỗi mục:
     - Điều kiện / bối cảnh.
     - Hành vi hệ thống mong đợi.
     - Kết quả quan sát được (UI/API/state…).
   - Nếu AC trong ideation chưa đủ cụ thể:
     - Cố gắng refine nhẹ nhưng **không vượt quá ý gốc**.
     - Ghi chú “cần refine thêm với BA/PO” nếu vẫn mơ hồ.

Kết quả cuối là 1 draft ở dạng text, có thể:

- Hiển thị trực tiếp cho user để copy-paste vào ticket system, hoặc
- Dùng làm payload cho MCP ticket API (nếu tích hợp).

---

### Bước 4 — Trao đổi & refine với user

1. Hiển thị draft ticket (summary, description, AC) cho user:
   - Rõ ràng phân tách từng phần.
2. Hỏi user:

   - Có muốn chỉnh sửa gì không? (title, wording, scope, AC…)
   - Có cần tách thành nhiều ticket không (nếu scope lớn)?

3. Nếu user đề xuất chỉnh sửa:
   - Cập nhật lại draft theo yêu cầu.
   - Lặp lại bước này đến khi user “ok” với nội dung.

---

### Bước 5 — Tạo ticket & kết nối với `/task`

1. Nếu có tích hợp MCP với hệ thống ticket:

   - Hỏi user:
     - “Bạn muốn em tạo ticket luôn (qua MCP) hay chỉ sinh nội dung để copy?”
   - Nếu user chọn tạo luôn:
     - Gọi MCP tương ứng (ví dụ: tạo issue trên Jira/…).
     - Nhận lại ticket key/URL.
2. Nếu **không có tích hợp**, hoặc user muốn tự tạo:

   - Nhắc user:
     - Copy summary/description/AC vào hệ thống ticket của họ.
   - Hỏi lại:
     - Ticket ID hoặc URL sau khi user tạo xong.

3. Sau khi có ticket key/URL (dù do MCP tạo hay user cung cấp):

   - Hiển thị lại thông tin:
     - “Ý tưởng X đã được chuyển thành ticket Y.”
   - Gợi ý bước tiếp theo:
     - `/task <ticket-id-or-link>` để chạy full pipeline:
       - REQUIREMENT → explore (db, code) → architecture-review → spec → apply.
     - Sau đó `/task spec <ticket-id>` rồi `/task apply <ticket-id>` khi đã sẵn sàng.

---

### 6. Lịch sử chuyển hoá (tuỳ chọn)

1. Cập nhật file ideation gốc:

   - Thêm section “Lịch sử chuyển hoá”:
     - Ngày giờ tạo ticket.
     - Ticket ID/URL.
     - Ghi chú ngắn (nếu có).

2. Điều này giúp:

   - Trace từ ý tưởng → ticket → thực thi.
   - Tránh việc chuyển cùng một ideation thành nhiều ticket trùng lặp mà không chủ ý.

---

### 7. Cập nhật AGENT_TRANSPARENCY

Trong `{{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md`:

- Ghi rằng đã chạy `/idea-to-task`.
- Nêu:
  - Tên file ideation đã dùng.
  - Ticket ID/URL tương ứng (nếu đã tạo hoặc user cung cấp).
- Nếu không thể tạo ticket (do thiếu MCP / user huỷ giữa chừng):
  - Ghi rõ trạng thái (draft-only / user-cancelled).

---

## [M4] Ideation Expiry & Auto-Archive

### ideation_expiry field

Mỗi file ideation có field `ideation_expiry` trong frontmatter (xem template `ideation.tpl.md`).
Mặc định: `created_at + 30 ngày`.

### Kiểm tra Expiry khi mở workflow

Khi `/idea-to-task` được gọi hoặc khi bootstrap liệt kê ideation files:

```
FUNCTION check_ideation_expiry():
  FOR EACH file IN {{ platform.framework_root }}/knowledge/active/ideation/ideation-*.md:
    1. Đọc frontmatter: created_at, ideation_expiry, status
    2. Nếu status = "converted" hoặc "archived": bỏ qua
    3. Nếu today > ideation_expiry VÀ status = "active":
       → Đánh dấu status = "expired" trong file
       → Ghi vào AGENT_TRANSPARENCY:
          "[M4-EXPIRE] {filename} đã hết hạn ({ideation_expiry}). Chờ user quyết định."
       → Hiển thị cho user:
          "Gợi ý '{tóm tắt ý tưởng}' đã hơn 30 ngày chưa được chuyển thành task.
           [K] Giữ lại thêm 30 ngày | [C] Convert thành task ngay | [A] Archive (bỏ qua)"
    4. Nếu today <= ideation_expiry VÀ status = "active":
       → Hiển thị: "Còn {n} ngày trước khi hết hạn"
```

### Auto-Archive khi Expired

```
FUNCTION auto_archive_expired_ideation(filename):
  IF user chọn [A] hoặc không phản hồi sau 30 ngày thêm:
    1. Đọc file ideation
    2. Append vào {{ platform.framework_root }}/knowledge/archive/ARCHIVE_LOG.md:
       | {filename} | {created_at} | {ideation_expiry} | expired | {tóm tắt 1 câu} |
    3. Xoá file khỏi {{ platform.framework_root }}/knowledge/active/ideation/
    4. Ghi vào AGENT_TRANSPARENCY:
       "[M4-ARCHIVE] {filename} đã được auto-archive do hết hạn."
```

### Khi chuyển thành ticket (Bước 5 hiện tại)

Sau khi ticket được tạo:
- Cập nhật frontmatter file ideation:
  - `status: converted`
  - `converted_at: {today}`
  - `ticket_id: {id}`
  - `ticket_url: {url}`
- File ideation **giữ nguyên** trong `active/ideation/` với status=converted (không xoá).
  - Mục đích: trace từ ý tưởng → ticket → thực thi.
  - Chỉ archive khi knowledge-curator chạy `archive_active_context`.

### Tóm tắt Status Flow

```
active → (expired) → [user: K] → active (extended 30 days)
active → (expired) → [user: C] → converted
active → (expired) → [user: A] → archived (log + delete)
active → (converted via /idea-to-task) → converted
```
