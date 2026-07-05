# Cấu trúc 5 Tầng (Hybrid)

> Tài liệu tham khảo cho skill `infra-tdd`. Load khi cần bảng mapping chi tiết của hybrid 5 tầng và template bắt đầu.

## Mục lục

- Cấu trúc 5 Tầng (Hybrid)

---

## Cấu trúc 5 Tầng (Hybrid)

| Tầng | Đối tượng đọc | Mục đích | Phải trả lời |
|------|---------------|----------|--------------|
| **T0 — Bối cảnh Nghiệp vụ** | BA, PM, Stakeholder | Giải thích ý tưởng | Nghiệp vụ này giải quyết gì? User trải qua flow nào? Quy tắc kinh doanh là gì? |
| **T1 — Chiến lược** | Tech Lead, Architect | Đặt vấn đề kỹ thuật | Ai đang bị đau? Metric nào cải thiện? Ai ký duyệt? |
| **T2 — Kiến trúc** | Dev, Architect | Mô tả hệ thống | Component, ranh giới, data flow, failure domain là gì? |
| **T3 — Quyết định** | Dev, Architect | Biện minh lựa chọn | Đã xem xét những alternative nào? Tại sao chọn cái này? Trade-off chấp nhận là gì? |
| **T4 — Vận hành** | Tech Leads, Trưởng phòng | Giám sát & cấu hình | Monitoring metrics, alert thresholds, configuration reference |

Template đầy đủ nằm ở `assets/TDD_TEMPLATE.md`. Copy nó làm điểm bắt đầu cho mọi document mới.
