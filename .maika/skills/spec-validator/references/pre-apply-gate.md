# Pre-Apply Gate

> Tài liệu tham khảo cho `spec-validator`. Đọc trước `/task apply`.

## Check

- change_id tồn tại.
- proposal.md có what/why.
- spec/tasks có ít nhất một task hoặc file change.
- Không chạm ngoài PROJECT_ROOTS nếu chưa có user verification.
- OPENSPEC_STATE là propose_done.
- Technical Design Contract interface được thể hiện trong tasks khi contract tồn tại.

FAIL thì block apply. WARN cần user quyết định.
