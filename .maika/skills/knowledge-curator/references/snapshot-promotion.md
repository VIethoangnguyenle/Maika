# Snapshot Promotion

> Tài liệu tham khảo cho `knowledge-curator`. Read when updating `knowledge-snapshot.md` after a completed task.

## Mục lục

- Update steps
- Promotion criteria
- Store partitioning
- Stale confidence decay

## Update steps

1. Read EXPLORE_CONTEXT.md and AGENT_TRANSPARENCY.md for the completed task.
2. Classify each discovery with the Promotion Criteria table.
3. Promote reusable code/DB facts into `knowledge-snapshot.md` with metadata:
   `source:{ticket-id} seen:{YYYY-MM} verified:{YYYY-MM} status:active`.
4. If an older entry covers the same concept:
   - Same fact: update `verified`.
   - Contradiction: mark old entry `status:superseded`, add the new entry, and name the superseded source.
   - Unclear: mark old entry `status:outdated` and require manual verification.
5. Add a history row with ticket, date, and count of added/updated entries.

## Promotion criteria

| Bucket | Điều kiện | Hành động |
|---|---|---|
| PROMOTE -> snapshot | Direct DB/code evidence, reusable across tasks, not ticket-only context, not convention/DNA material | Add to the right snapshot section with metadata |
| REDIRECT -> conventions | Naming rule, coding style, design pattern boundary, folder/package structure | Propose update to `conventions.yaml` or `conventions.draft.yaml` |
| REDIRECT -> author-dna | Programming philosophy, reason for choosing a pattern, judgment principle | Propose update to `author-dna.yaml` or `author-dna.draft.yaml` |
| ARCHIVE only | Ticket-specific workaround, unresolved debate, narrow business-case context | Keep in archive EXPLORE_CONTEXT.md |
| DISCARD | Pure inference without evidence, duplicate of better snapshot entry, PII/secret | Do not store |

## Store partitioning

| Loại nội dung | Store | Example |
|---|---|---|
| Sự thật về hệ thống | `knowledge-snapshot.md` | Table has column, module calls module |
| Quy tắc viết code | `conventions.yaml` | Naming/package/style rule |
| Triết lý hoặc judgment principle | `author-dna.yaml` | Why a pattern is preferred |
| Bài học vận hành | agent memory | Incident or fix lesson |

Write conventions/DNA at pattern level. Concrete table/class names belong in evidence, not generic rule text. If a rule only applies to one table or class, treat it as a snapshot fact.

## Stale confidence decay

For each active snapshot entry:

- If `verified` is older than 90 days and the current task touches that area, update `verified` and keep `confidence:high`.
- If `verified` is older than 90 days and the current task does not touch that area, mark `confidence:low` without changing status.
- If `verified` is older than 180 days and confidence is already low, add `<!-- needs-reverify -->`.
- When using a stale entry, mention the stale status in output and cross-check with Understand-Anything before relying on it.
