# Hướng dẫn ASCII Diagram cho Explore và Spec Extract

## Bối cảnh

Pipeline `/task` của Maika đã tách rõ các pha: trích xuất yêu cầu, explore, tạo OpenSpec proposal, và implementation. Tuy vậy guidance hiện tại còn một khoảng trống: `openspec-explore` có nhắc ASCII diagram, nhưng `spec-extract` và các knowledge template chưa bắt buộc capture diagram khi tài liệu hoặc phần explore có business flow, state transition, integration, callback, job, hoặc data path.

Hệ quả là agent có thể hiểu đúng luồng trong chat, nhưng artifact downstream vẫn mất thứ tự xử lý, boundary, và nhánh rẽ quan trọng của requirement.

Thiết kế này tận dụng phần hữu ích từ stance explore của upstream OpenSpec trong `Fission-AI/openspec`: explore là một tư thế suy nghĩ, không phải workflow cứng; agent nên đọc code khi cần, so sánh option, visualize tự do, và handoff sang propose khi bức tranh đã rõ. Maika bổ sung kỷ luật artifact mạnh hơn: các ASCII diagram quan trọng phải được capture vào active knowledge layer để các pha sau dùng lại.

Nguồn upstream liên quan:

- https://github.com/Fission-AI/openspec
- https://github.com/Fission-AI/openspec/blob/main/docs/explore.md
- https://github.com/Fission-AI/openspec/blob/main/src/core/templates/workflows/explore.ts

## Mục tiêu

- Biến ASCII diagram thành phần bắt buộc trong output của `spec-extract` khi tài liệu nguồn có flow, state, integration, callback, job, hoặc data-path structure.
- Giữ stance explore linh hoạt của upstream OpenSpec, đồng thời làm guidance `/opsx:explore` của Maika rõ hơn về visual reasoning.
- Thêm anchor vào template để `REQUIREMENT.md` và `EXPLORE_CONTEXT.md` giữ diagram trong artifact thay vì chỉ nằm trong chat.
- Giữ diagram ở dạng plain-text ASCII để đọc tốt trong Markdown, code review, terminal output, và long-context handoff mà không phụ thuộc renderer.

## Không thuộc phạm vi

- Không thêm Mermaid, DOT, image generation, hoặc diagram renderer.
- Không bắt diagram cho task đơn giản không có sequence, state, branch, hoặc integration boundary đáng kể.
- Không đổi runtime code hoặc hành vi command execution.
- Không dùng diagram để thay thế acceptance criteria, source link, field mapping, hoặc architecture note.

## Kiến trúc

Thay đổi chỉ nằm ở skill guidance và knowledge template.

```text
input từ user / tài liệu nguồn
  -> spec-extract hoặc openspec-explore
  -> phát hiện flow / state / data path / integration boundary
  -> vẽ ASCII diagram
  -> capture vào REQUIREMENT.md hoặc EXPLORE_CONTEXT.md
  -> openspec-propose đọc được context Pha 1 rõ hơn
```

Các file dự kiến sẽ sửa khi implement:

- `.maika/skills/openspec-explore/SKILL.md`
- `.maika/skills/openspec-explore/references/explore-patterns.md`
- `.maika/skills/spec-extract/SKILL.md`
- `.maika/skills/spec-extract/references/quy-trinh-chi-tiet.md`
- `.maika/skills/spec-extract/references/output-schema.md`
- `.maika/knowledge/templates/REQUIREMENT.tpl.md`
- `.maika/knowledge/templates/EXPLORE_CONTEXT.tpl.md`

## Hành vi

### Điều kiện kích hoạt diagram

Agent nên tạo ASCII diagram khi nội dung đang explore hoặc extract có ít nhất một cấu trúc sau:

- Main flow có nhiều bước theo thứ tự.
- Alternate flow, error branch, retry, fallback, hoặc cancellation path.
- State transition hoặc lifecycle.
- Integration boundary giữa hệ thống nội bộ và hệ thống bên ngoài.
- Callback, webhook, scheduled job, queue, event, hoặc async handoff.
- Data path đi qua module, service, table, DTO, hoặc third-party field.
- Option branching mà so sánh bằng hình rõ hơn prose.

Agent không nên tạo diagram chỉ để trang trí cho một bullet list đơn giản.

### `spec-extract`

`spec-extract` nên thêm block bắt buộc `#### ASCII Flow / State Diagram` khi tài liệu nguồn chứa bất kỳ trigger nào ở trên.

Vị trí đề xuất:

```text
### Yêu cầu nghiệp vụ trích từ tài liệu
  -> Bối cảnh & mục tiêu
  -> Actor & Use Case
  -> ASCII Flow / State Diagram
  -> Luồng chính
  -> Luồng lỗi / ngoại lệ
  -> Quy tắc nghiệp vụ
```

Nếu tài liệu có nhiều flow, `spec-extract` nên vẽ một overview diagram trước. Chỉ vẽ diagram nhỏ hơn cho các nhánh đủ phức tạp để dễ mơ hồ nếu không có hình.

Nếu evidence chưa đủ, diagram phải đánh dấu phần chưa chắc là `unknown`, `assumption`, hoặc `needs BA/PO confirmation`.

### `openspec-explore`

`openspec-explore` nên mượn stance upstream:

- Explore là một thinking stance, không phải fixed workflow.
- Agent có thể đọc file, search code, điều tra codebase, so sánh option, và visualize tự do.
- Agent không được implement code.
- Agent nên offer chuyển sang proposal creation khi suy nghĩ đã kết tinh.

Bổ sung riêng cho Maika:

- Khi một cuộc explore dùng diagram để làm rõ insight quan trọng, agent nên offer capture insight đó vào `EXPLORE_CONTEXT.md`, OpenSpec artifact, hoặc active knowledge file phù hợp.
- Nếu explore bắt đầu từ task mới có flow chưa rõ, agent nên sketch một map gọn:

```text
vấn đề user nêu
  -> hành vi hiện tại / unknown
  -> probe code hoặc tài liệu
  -> các option
  -> bước tiếp theo được recommend
```

### Template

`REQUIREMENT.tpl.md` nên có diagram anchor riêng gần phần As-is/To-be và phần extracted-document.

`EXPLORE_CONTEXT.tpl.md` nên thay placeholder mềm "Sơ đồ hoặc danh sách module" bằng guidance rõ hơn: khi có flow, state, hoặc data path, phải có ASCII diagram. Danh sách plain text vẫn chấp nhận được khi không có sequence hoặc boundary đáng kể.

## Xử lý lỗi và guardrail

- Diagram phải phân biệt evidence với inference.
- Diagram không được bịa actor, system, field, hoặc state không có trong source hoặc code evidence.
- Diagram phải có label boundary bên ngoài khi có integration.
- Diagram phải gọn. Nếu diagram quá dày, tách thành overview diagram và một diagram riêng cho nhánh phức tạp.
- Explore mode vẫn là non-implementation. Cập nhật OpenSpec hoặc knowledge artifact chỉ được xem là capture suy nghĩ, không phải thay đổi application code.

## Tiêu chí chấp nhận

- Khi `spec-extract` xử lý tài liệu có process flow, `REQUIREMENT.md` có `#### ASCII Flow / State Diagram`.
- Khi `spec-extract` xử lý tài liệu có state lifecycle, diagram thể hiện state và transition.
- Khi `spec-extract` xử lý integration, callback, job, event, hoặc data-path material, diagram label được boundary nội bộ và bên ngoài.
- Khi evidence chưa đủ, diagram đánh dấu node hoặc edge chưa chắc chắn một cách rõ ràng thay vì trình bày assumption như fact.
- Guidance `openspec-explore` giữ rõ behavior "stance, not workflow" và guardrail "do not implement" của upstream OpenSpec.
- Guidance `openspec-explore` yêu cầu agent dùng ASCII diagram khi diagram làm rõ code, architecture, data flow, state, hoặc option branching.
- Guidance `openspec-explore` yêu cầu agent offer capture vào Maika/OpenSpec artifact khi insight quan trọng dựa trên diagram đã kết tinh.
- `REQUIREMENT.tpl.md` và `EXPLORE_CONTEXT.tpl.md` có diagram anchor để downstream `openspec-propose` đọc được mà không phụ thuộc chat history.

## Kế hoạch verify

- Chạy skill/template lint test nếu có.
- Search trong repo theo section title mới để xác nhận guidance và template đã align.
- Review thủ công Markdown đã sửa để đảm bảo không còn placeholder, không phụ thuộc renderer, và không mâu thuẫn với phase gate hiện có.
