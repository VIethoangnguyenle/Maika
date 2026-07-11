---
description: Workflow task chuẩn của Maika (knowledge-native).
---

# /task

Maika chạy workflow adaptive, knowledge-native. Mọi task có execution contract và
Dev Loop; Spec Loop và Plan Loop chỉ chạy theo `workflow` được classifier ghi vào
`CHANGE.yaml` (và `TASK.yaml` cho lightweight task):

```text
trivial       Inspect → Change → Static Check
small         Focused Evidence → Micro-plan → Implement → Verify
standard      Focused Grounding → Conditional Spec → Compact Plan → Implement → Review → Verify
architectural Grounding → Spec/Audit → Full Plan/Audit → Implement → Review → Verify → Human Gate
```

## Lệnh public

Scaffold ở target phơi bày workflow chuẩn qua `maika task`:

- `maika task start --id <change-id> --class <class> --title <title>`
- `maika task explore --id <change-id>`
- `maika task reconcile --id <change-id>`
- `maika task brainstorm --id <change-id>`
- `maika task spec --id <change-id>`
- `maika task plan --id <change-id>`
- `maika task validate-plan --id <change-id>`
- `maika task review --id <change-id>`
- `maika task apply --id <change-id>`
- `maika task verify --id <change-id>`
- `maika task archive --id <change-id>`
- `maika task status [--id <change-id>]`
- `maika task resume --id <change-id>`
- `maika task cancel --id <change-id>`

`maika task verify` chạy lệnh thật khai trong `verification/COMMANDS.yaml`, ghi
`verification/VERIFICATION_REPORT.md`, rồi đánh dấu workspace `COMPLETED`.
`maika task archive` yêu cầu verified completion + `reviews/KNOWLEDGE_IMPACT.yaml`,
áp knowledge lifecycle, regenerate `knowledge/long-term/knowledge-index.yaml`, ghi
`ARCHIVE_MANIFEST.yaml`, và dời workspace sang `<framework-root>/archive/<change-id>`.
Verification cũng bắt buộc `reviews/SKILL_FEEDBACK.yaml`; archive record feedback,
cluster recurrence và chỉ tạo skill candidate khi threshold trong
`rules/rules-skill-evolution.md` pass. Candidate không được auto-promote.

Mọi reconciliation/spec/plan/review/verification material decision phải pass gate
`knowledge-trace`. Mọi fresh dispatch phải pass `context-package` và
`dispatch-kernel`, đồng thời mang Task Knowledge Capsule path/hash.

Workflow chạy thật end-to-end — người dùng **không** phải tự sửa `STATE.yaml`,
grounding artifact, result, review, queue, hay verification report.

## Thứ tự artifact đầy đủ (standard/architectural)

```text
CHANGE.yaml
INTENT.md
exploration/QUERY_PLAN.yaml
exploration/TOOL_HEALTH.yaml
exploration/GROUNDING.yaml
exploration/EVIDENCE_MANIFEST.yaml
exploration/CONFLICTS.yaml
exploration/COVERAGE.yaml
exploration/DATABASE_CONTEXT.yaml   # khi có database/persistence impact
RECONCILIATION.md
SPEC.md
IMPLEMENTATION_PLAN.md
generated/PLAN_VALIDATION.json
generated/PLAN_MANIFEST.json
generated/TASK_QUEUE.json
briefs/TASK-001.md
briefs/TASK-001.knowledge.yaml
results/TASK-001.yaml
reviews/TASK-001.md
reviews/FINAL_REVIEW.md
reviews/KNOWLEDGE_IMPACT.yaml
verification/COMMANDS.yaml
verification/VERIFICATION_REPORT.md
ARCHIVE_MANIFEST.yaml
```

## Rules

- Trivial/small không bị ép tạo `SPEC.md` hoặc `IMPLEMENTATION_PLAN.md`; micro-plan
  nằm trong `TASK.yaml`.
- `workflow.execution_contract` và `workflow.dev_loop` luôn là `required`.
- Change standard và architectural cần grounding đa nguồn (query plan → provider
  probe → evidence → reconcile) trước khi chốt thiết kế.
- Provider ưu tiên khỏe không được skip im lặng; provider absent phải ghi
  degradation record (xem `rules-tool.md`).
- Implementer nhận brief bất biến + Task Knowledge Capsule, không nhận history
  của parent session.
- Reviewer không sửa application code; task review APPROVED cần counter-evidence.
- Write application-code không khai báo bị chặn bởi write gate.
- Completion cần structured result, review, và verification chạy lệnh thật.
