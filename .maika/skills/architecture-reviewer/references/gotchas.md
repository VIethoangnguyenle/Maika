# Gotcha của Architecture Reviewer

> Tài liệu tham khảo cho `architecture-reviewer`. Đọc khi xuất hiện câu hỏi về confidence, conventions, contract, hoặc upstream library.

## Gotchas

- **G1 knowledge-snapshot stale**: kiểm `<!-- verified: YYYY-MM-DD -->`. Nếu cũ hơn 30 ngày, coi là reference và cross-verify bằng UA graph.
- **G2 conventions draft**: chỉ dùng `conventions.yaml` đã approve, không dùng `conventions.draft.yaml`.
- **G3 M6 cần REQUIREMENT**: skip M6 khi REQUIREMENT trống hoặc chỉ là skeleton.
- **G4 upstream boundary**: không đề xuất đổi upstream library contract; chỉ warn khi downstream implementation lệch.
