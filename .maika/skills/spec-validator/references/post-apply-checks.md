# Post-Apply Checks

> Tài liệu tham khảo cho `spec-validator`. Đọc sau apply khi so sánh expected files với actual changed files.

## Check

- Expected file bị thiếu trong changed_files → WARN.
- Unexpected file xuất hiện trong changed_files → WARN.
- Syntax/compile check nếu project có tooling.
- Không auto-rollback.

Output: `[POST-APPLY] verify: {n_match}/{n_expected} matches. Issues: {issue_list_or_empty}`.
