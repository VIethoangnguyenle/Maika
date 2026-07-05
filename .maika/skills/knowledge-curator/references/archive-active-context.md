# Archive Active Context

> Tài liệu tham khảo cho `knowledge-curator`. Đọc trước khi archive active context.

## Mục lục

- Pre-check
- Ý nghĩa status
- Các bước archive

## Pre-check

Chạy:

```bash
python3 {{ platform.framework_root }}/tools/gate-check/cli.py archive-ready {{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md
python3 {{ platform.framework_root }}/tools/gate-check/cli.py teaching-moment {{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md
```

Exit khác 0 thì abort archive.

## Ý nghĩa status

- `completed`: apply xong; cập nhật knowledge snapshot.
- `stashed`: đang tạm dừng; không cập nhật snapshot.
- `cancelled`: đã huỷ; không cập nhật snapshot.

## Các bước archive

1. Tạo `{{ platform.framework_root }}/knowledge/archive/{ticket_id}/`.
2. Copy REQUIREMENT, EXPLORE_CONTEXT, AGENT_TRANSPARENCY, TOKEN_LOG nếu có, SESSION_OVERRIDE nếu có, `.session_state.json` nếu có, và `active/ideation/` nếu có.
3. Tạo ARCHIVE_META.md với ticket_id, archived_at, status, summary, phase_at_archive, stash_note nếu stashed, token_total_estimate.
4. Verify các file đã copy vẫn đọc được.
5. Nếu status là `completed`, chạy cập nhật snapshot.
6. Báo archive path.
