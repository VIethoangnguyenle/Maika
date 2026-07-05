# Coverage Checks

> Tài liệu tham khảo cho `spec-validator`. Đọc khi check Acceptance Criteria hoặc integration coverage.

## Command

Chạy:

```bash
CHANGE_ID="${CHANGE_ID:?set CHANGE_ID to the OpenSpec change folder name}"
python3 {{ platform.framework_root }}/tools/gate-check/cli.py ac-coverage {{ platform.framework_root }}/knowledge/active/REQUIREMENT.md --against "openspec/changes/${CHANGE_ID}/tasks.md"
python3 {{ platform.framework_root }}/tools/gate-check/cli.py integration-coverage {{ platform.framework_root }}/knowledge/active/REQUIREMENT.md --against "openspec/changes/${CHANGE_ID}/tasks.md"
```

Exit khác 0 nghĩa là có AC hoặc integration chưa được cover. Hiển thị reason cho user và hỏi nên amend spec hay tiếp tục.

## Scope

Các deterministic check này dùng keyword/entity overlap đơn giản. Chúng không thay thế semantic review. Nếu cần judgment ngữ nghĩa, agent phải ghi rationale rõ ràng.
