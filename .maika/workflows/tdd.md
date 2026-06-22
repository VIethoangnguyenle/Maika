# Workflow: /tdd — Viết Technical Design Document

## Trigger
- `/tdd <module-name>` — Tạo TDD cho module infrastructure/platform
- Ví dụ: `/tdd api-gateway`, `/tdd payment-qr`, `/tdd cache-refactor`

## Mô tả
Standalone workflow — không qua `/task` flow. Kích hoạt skill `infra-tdd` để viết Technical Design Document theo chuẩn 4-layer (Chiến lược, Kiến trúc, Quyết định, Vận hành).

## Yêu cầu
- Skill `infra-tdd` phải đã load
- Knowledge tools (UA, Codebase Memory, db-explorer) nên khả dụng

## Các bước

### Bước 1 — Load Skill
```
READ: {{ platform.framework_root }}/skills/infra-tdd/SKILL.md
```
Đọc skill instructions và tuân thủ Knowledge-First Protocol.

### Bước 2 — Thu thập thông tin
Hỏi user hoặc đọc từ context:
- Tên module và mục đích
- Greenfield / replacement / extension?
- Ràng buộc cứng (nếu có)

### Bước 3 — Tạo TDD
```
COPY: {{ platform.framework_root }}/skills/infra-tdd/assets/TDD_TEMPLATE.md → docs/tdd/<module>-TDD.md
```
Điền từng tầng theo thứ tự T1 → T2 → T3 → T4.

**BẮT BUỘC**: Chạy knowledge tools trước mỗi tầng (xem Knowledge-First Protocol trong SKILL.md).

### Bước 4 — Socratic Deep-Dive
```
READ: {{ platform.framework_root }}/skills/infra-tdd/references/socratic-deep-dive.md
```
Chạy deep-dive cho mỗi quyết định non-trivial trong T3.

### Bước 5 — Viết ADR
```
READ: {{ platform.framework_root }}/skills/infra-tdd/references/adr-guide.md
COPY: {{ platform.framework_root }}/skills/infra-tdd/assets/ADR_TEMPLATE.md → docs/tdd/<module>-adr/NNNN-title.md
```
Một ADR per quyết định. Link từ T3 trong TDD.

### Bước 6 — Review Checklist
Chạy checklist ở cuối TDD_TEMPLATE.md trước khi tuyên bố hoàn thành.

## Output
- `docs/tdd/<module>-TDD.md` — Document chính
- `docs/tdd/<module>-adr/*.md` — ADR files (nếu có)
