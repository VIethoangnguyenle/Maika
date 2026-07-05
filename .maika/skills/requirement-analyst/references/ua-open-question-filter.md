# UA Open Question Filter

> Tài liệu tham khảo cho `requirement-analyst`. Đọc trước khi hỏi user một open question.

## Quy tắc

Trước khi viết bất kỳ Open Question nào, phân loại câu hỏi:

- Code-answerable: entry point, current race/lock behavior, approve/reject flow hiện có, API/event path hiện có. Tự resolve bằng UA-first probe.
- True business unknown: SLA, business rule, trách nhiệm approver, priority, quyết định legal/compliance. Hỏi user.

## UA-first probe

Thứ tự nguồn BẮT BUỘC khi trace code:

1. **UA + kinh nghiệm** (agent-memory, knowledge-snapshot) — LUÔN trước; UA là bản đồ node (class/func/domain/flow), dùng để trace/định vị.
2. **Codebase Memory** — vào SAU khi UA định vị node/flow, để đọc logic trong thân hàm.
3. **grep** — fallback cuối.

Chạy `{{ tools.domain_overview }}` và `{{ tools.domain_flow }}` trước.

## Output

Câu trả lời code-answerable đi vào As-is, To-be delta, hoặc Technical Design Contract. Unknown nghiệp vụ thật đi vào Requirement Issues.
