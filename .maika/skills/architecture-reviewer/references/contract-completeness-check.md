# Contract Completeness Check

> Tài liệu tham khảo cho `architecture-reviewer`. Read after Bước 7 and before final conclusion when REQUIREMENT.md has a Technical Design Contract.

## Mục lục

- Checks
- Output
- Skip conditions

## Checks

1. Section exists and has real content.
2. If `conventions.yaml` exists and is approved, compare selected protocol/pattern with conventions.
3. Contract has protocol/interface, request/message schema, and response/event schema.

## Output

All M6 checks are WARN only. Write `[M6] Contract Completeness: {PASS|WARN(n)} — {details}` to `AGENT_TRANSPARENCY.md`.

## Skip conditions

Skip when REQUIREMENT.md uses an old template without contract section, or task type is `refactor`.
