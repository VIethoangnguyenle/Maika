# UA Open Question Filter

> Tài liệu tham khảo cho `requirement-analyst`. Đọc trước khi hỏi user một open question.

## Quy tắc

Trước khi viết bất kỳ Open Question nào, phân loại câu hỏi:

- Code-answerable: entry point, current race/lock behavior, approve/reject flow hiện có, API/event path hiện có. Tự resolve bằng UA-first probe.
- True business unknown: SLA, business rule, trách nhiệm approver, priority, quyết định legal/compliance. Hỏi user.

## UA-first probe

Chạy `{{ tools.domain_overview }}` và `{{ tools.domain_flow }}` trước. Dùng Codebase Memory sau khi UA định vị node/flow liên quan.

## Output

Câu trả lời code-answerable đi vào As-is, To-be delta, hoặc Technical Design Contract. Unknown nghiệp vụ thật đi vào Requirement Issues.
