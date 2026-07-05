# Infra-TDD Auto Trigger

> Tài liệu tham khảo cho `architecture-reviewer`. Đọc sau Bước 7 khi review phát hiện tác động tới infrastructure, platform, integration, DB, hoặc contract.

## Mục lục

- Điều kiện trigger
- Luồng đề xuất
- Điều kiện không trigger

## Điều kiện trigger

Đề xuất `infra-tdd` khi kết quả review có issue HIGH/BLOCKER liên quan tới database schema, index, migration, platform topology, service mới, Kafka topic, API contract, hoặc external integration.

## Luồng đề xuất

1. Báo user: `[M5] Yêu cầu này có tác động hạ tầng. Khuyến nghị tạo TDD trước khi spec.`
2. Hỏi có chạy `/tdd` không.
3. Ghi `[M5-INFRA-TDD] Đề xuất TDD vì: {reason}. User cần confirm.` vào `AGENT_TRANSPARENCY.md`.
4. Không tự động chạy `/tdd`.

## Điều kiện không trigger

Không trigger cho business logic thuần, UI, validation, bugfix không đổi schema/topology, hoặc refactor nội bộ trong một module.
