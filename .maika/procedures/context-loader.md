# Context Loader — Knowledge Router

Context loader tạo knowledge package nhỏ nhất đủ cho một role/decision. Đây không phải
artifact list tĩnh và không được preload full-history.

## Input contract

```yaml
role:
state:
change_id:
change class:
artifact type:
knowledge questions: []
required evidence: []
provider health: {}
token budget:
```

Input thiếu `role`, `state`, `knowledge questions` hoặc `required evidence` thì block.

## Routing order

1. Load active change artifacts hợp lệ cho `role` và `state`.
2. Load immutable Task Knowledge Capsule nếu role là implementation/review/verification.
3. Query `knowledge-index.yaml` theo `applies_to`, artifact type và knowledge question;
   chỉ load durable knowledge slice có status `active`.
4. Recall Agent Memory theo decision/incident/rejected approach/repeated finding;
   zero-result được ghi như negative evidence.
5. Load UA architecture/domain/flow/dependency/blast-radius evidence theo required
   evidence; provider healthy thì phải dùng capability tương ứng.
6. Verify exact facts bằng source anchors hiện tại.
7. Load database slice khi change class hoặc question persistence-sensitive.

Không load toàn bộ archive, graph, memory, history, skill references hoặc long-term
store. Chỉ mở body sau khi index metadata match route hiện tại.

## Role routes

| role | active artifacts | knowledge slice |
|---|---|---|
| intent | `CHANGE.yaml`, `INTENT.md` | history, business, convention |
| grounding | `INTENT.md`, query plan | UA/source/memory/DB evidence |
| reconciliation | grounding + evidence manifest | conflicts, authority, freshness |
| brainstorming/spec | reconciliation + evidence | accepted options and contracts |
| planning/plan review | spec + evidence manifest | targeted blast radius, task capsule |
| implementation | one brief + one capsule | allowed source/knowledge/DB anchors |
| task/final review | result + capsule + diff | counter-evidence and knowledge impact |
| verification | final review + commands | runtime evidence and trace freshness |
| knowledge curator | VERIFIED report + impact | promote/supersede/memory/refresh |
| skill evolution | verified feedback cluster | generic skill evidence only |

## Freshness checks

Mỗi package phải kiểm:

- repository commit so với package `repository_commit`;
- file hash của source anchor và loaded artifact;
- graph indexed commit so với HEAD;
- knowledge status (`active`, `superseded`, `invalidated`);
- memory relevance theo change class/question và incident age;
- DB probe timestamp so với risk-specific TTL;
- capsule hash so với queue và evidence manifest.

Stale item không bị bỏ im lặng: ghi vào `missing_context` hoặc `degradation`. High-risk
decision với source/DB/capsule stale phải block; graph/memory stale chỉ được dùng như
historical hint với confidence giảm và refresh request.

## Output contract

```yaml
version: 1
role:
change_id:
state:
loaded_artifacts: []
knowledge_slice: []
memory_slice: []
source_anchors: []
database_slice: []
missing_context: []
degradation: []
confidence: low|medium|high
freshness:
  repository_commit:
  generated_at:
```

Mỗi slice item mang `id`, `source`, `provenance`, `freshness`, `confidence` và hash/ref
applicable. Output được ghi `generated/CONTEXT_PACKAGE.<role>.yaml` rồi chạy gate
`context-package` trước dispatch.
Material decision sau retrieval vẫn phải qua `procedures/decision-gate.md`; context
đã load không đồng nghĩa Knowledge Trace hoặc decision đã hợp lệ.

## Token budget

Ưu tiên direct anchors và decision-relevant entries. Khi vượt budget, bỏ metadata ít
liên quan trước, không cắt provenance, conflict, assumption, capsule hoặc required
evidence. Nếu vẫn vượt, tạo `CONTEXT_REQUEST.yaml` thay vì tự tóm tắt mất authority.

## Degradation

Provider unhealthy phải dùng health evidence từ bootstrap report, ghi capability bị
thiếu, fallback, confidence và refresh/retry action. Không ghi provider healthy chỉ vì
tool shim trả response. Missing required evidence không có safe fallback thì block.

## Consumer contract

Meta prompt gọi router sau bootstrap. Shared dispatch kernel nhận path và hash của
package. Reviewer kiểm package freshness; knowledge curator dùng IDs đã consumed để
đo Task B thực sự retrieve knowledge của Task A.
