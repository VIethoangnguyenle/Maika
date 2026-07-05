# Reset Active Context

> Tài liệu tham khảo cho `knowledge-curator`. Đọc trước khi reset active context.

## Mục lục

- Pre-check
- Các bước reset
- Quy tắc ideation

## Pre-check

Chạy:

```bash
python3 {{ platform.framework_root }}/tools/gate-check/cli.py reset-ready {{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md
```

Exit khác 0 thì abort reset. Reset là thao tác destructive và yêu cầu phase_state `completed`, `cancelled`, hoặc `stashed` cùng Teaching Moment Check hợp lệ.

## Các bước reset

1. Copy template vào active REQUIREMENT, EXPLORE_CONTEXT, AGENT_TRANSPARENCY.
2. Reset TOKEN_LOG.md từ template nếu có.
3. Xoá SESSION_OVERRIDE.md và `.session_state.json`.
4. Báo `Active context reset. Ready for new task.`

## Quy tắc ideation

Không xoá active ideation draft trừ khi archive đã copy chúng hoặc user yêu cầu rõ là clear ideation.
