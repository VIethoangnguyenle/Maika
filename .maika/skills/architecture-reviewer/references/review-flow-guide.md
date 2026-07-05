# Hướng dẫn Review Flow

> Tài liệu tham khảo cho `architecture-reviewer`. Đọc khi cần chạy review flow kiến trúc chi tiết 7 bước.

## Mục lục

- Bước 1 — Kiểm tra trạng thái tool & khung tin cậy
- Bước 2 — Tóm tắt kiến trúc hiện tại
- Bước 3 — Đối chiếu As-is / To-be
- Bước 4 — Boundary, ownership, topology, coupling
- Bước 5 — Tác động dữ liệu
- Bước 6 — Non-functional review
- Bước 7 — Tổng hợp đánh giá

## Bước 1 — Kiểm tra trạng thái tool & khung tin cậy

1. Đọc `{{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md`.
2. Xác định trạng thái UA, db-explorer, codebase-explorer.
3. Đặt Độ tin cậy tối đa khả dĩ và ghi rõ limitation.

## Bước 2 — Tóm tắt kiến trúc hiện tại

1. Đọc `EXPLORE_CONTEXT.md` và `knowledge-snapshot.md`.
2. Xác định service/module chính, integration, database/schema.
3. Nếu có identifier, dùng `{{ tools.read_file }}` và `{{ tools.get_dependencies }}` để xác minh code-fact nội-service.

## Bước 3 — Đối chiếu As-is / To-be

1. Dựa trên REQUIREMENT.md, map flow hiện tại và flow to-be.
2. Nếu có identifier, dùng `{{ tools.find_blast_radius }}`, `{{ tools.read_file }}`, `{{ tools.trace_flow }}` cho logic nội-service.
3. Ghi điểm khớp và điểm lệch.

## Bước 4 — Boundary, ownership, topology, coupling

1. Boundary & ownership: dùng `{{ tools.domain_relationships }}` để xác định domain owner.
2. Execution topology: dùng `{{ tools.domain_flow }}` để xác định REST/gRPC/Kafka/job.
3. Layering: đối chiếu `conventions.yaml` và `knowledge-snapshot.md`. Skill KHÔNG hardcode bất kỳ pattern nào (CQRS/MVC/Hexagonal…) — luôn đọc constraint từ `conventions.yaml` rồi enforce, bắt lỗi khi Requirement/Spec định đi tắt.
4. Coupling: đánh dấu phụ thuộc mới giữa module/service vốn độc lập.

## Bước 5 — Tác động dữ liệu

1. Dựa trên `db-explorer`, kiểm schema, constraint, migration, lịch sử.
2. Nếu dữ liệu là trọng tâm mà thiếu db-explorer, đánh dấu risk và hạ confidence.

## Bước 6 — Non-functional review

1. Hiệu năng: call/join/IO/hot path mới.
2. Độ tin cậy: dependency mới trên critical path.
3. Observability: logging/metrics/tracing cho luồng đổi mới.

## Bước 7 — Tổng hợp đánh giá

Ghi section `Đánh giá kiến trúc` vào `EXPLORE_CONTEXT.md` với điểm phù hợp, rủi ro, severity LOW/MEDIUM/HIGH/BLOCKER, hướng xử lý high-level, câu hỏi còn cần trả lời.

Luôn tách bạch: **Fact** (đã thấy từ code/DB/tài liệu), **Nhận định** (đánh giá kiến trúc), **Giả định** (khi thiếu dữ liệu).
