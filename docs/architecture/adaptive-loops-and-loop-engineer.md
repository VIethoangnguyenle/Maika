# ADR: Adaptive workflow loops

Status: Accepted (2026-07-11)

## Decision

Mọi coding task phải có execution contract và Dev Loop. Spec Loop và Plan Loop
được chọn theo task class thay vì là gateway bắt buộc:

| Class | Spec | Plan | Planner mode | Audit/Human gate |
|---|---|---|---|---|
| trivial | skipped | skipped | none | no |
| small | skipped, trừ khi ambiguous | micro trong `TASK.yaml` | none | no |
| standard | conditional | compact | fast | no |
| architectural | required | full | deep | yes |

`classify_workflow_requirements()` là policy owner. `init_workspace()` ghi output
vào artifact để CLI, orchestrator và reviewer dùng cùng một contract. Classifier
không mở Loop Engineer trên happy path; trigger/change-loop là phase tiếp theo.

## Invariants

- Execution contract và Dev Loop luôn bắt buộc.
- Ambiguity có thể bật Spec Loop nhưng không tự nâng Plan Loop lên full.
- Task class không bị downgrade trong runtime.
- Shared skill không được tự patch hoặc tự approve.

## Consequences

Small changes không còn trả token tax của full spec/plan. Architectural changes
vẫn giữ full review boundary. Trigger engine, `LOOP.yaml` và macro learning chưa
nằm trong vertical slice này và phải có evidence/consumer trước khi thêm.
