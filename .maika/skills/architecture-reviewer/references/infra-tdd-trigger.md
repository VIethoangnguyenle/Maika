# Infra-TDD Auto Trigger

> Tài liệu tham khảo cho `architecture-reviewer`. Read after Bước 7 when review finds infrastructure, platform, integration, DB, or contract impact.

## Mục lục

- Trigger conditions
- Suggestion flow
- Non-trigger conditions

## Trigger conditions

Suggest `infra-tdd` when review result has HIGH/BLOCKER issue related to database schema, index, migration, platform topology, new service, Kafka topic, API contract, or external integration.

## Suggestion flow

1. Tell user: `[M5] Yêu cầu này có tác động hạ tầng. Khuyến nghị tạo TDD trước khi spec.`
2. Ask whether to run `/tdd`.
3. Write `[M5-INFRA-TDD] Đề xuất TDD vì: {reason}. User cần confirm.` to `AGENT_TRANSPARENCY.md`.
4. Do not auto-run `/tdd`.

## Non-trigger conditions

Do not trigger for pure business logic, UI, validation, bugfix without schema/topology change, or internal refactor within one module.
