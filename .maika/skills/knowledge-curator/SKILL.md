---
name: knowledge-curator
version: '1.1'
description: >
  Quản lý vòng đời knowledge — archive context hoàn thành, reset active/, cập nhật knowledge-snapshot sau mỗi task.
  Dùng khi task hoàn thành cần archive, hoặc cần reset/rotate context.
  KHÔNG dùng cho: review kiến trúc (→ architecture-reviewer),
  sinh/validate spec (→ openspec-propose, spec-validator), viết tài liệu (→ document-writer).
---

# Knowledge Curator — Quản lý Vòng đời Knowledge

## Mục tiêu

- Archive context đã hoàn thành vào `{{ platform.framework_root }}/knowledge/archive/{ticket-id}/`.
- Reset `{{ platform.framework_root }}/knowledge/active/` về skeleton sạch.
- Cập nhật `knowledge-snapshot.md` với discovery tái sử dụng được.
- Rotate archive cũ khi vượt ngưỡng.

Skill này là lifecycle manager. Không sinh requirement, không review kiến trúc, không validate spec.

## Khi nào dùng

- `/task apply` hoàn thành thành công.
- User yêu cầu đóng task hoặc reset context.
- Bootstrap phát hiện conflict giữa active context và task mới, và user chọn reset.
- Archive vượt retention threshold.

## Khi nào KHÔNG sử dụng

- Task chưa hoàn thành và chưa sẵn sàng archive.
- Cần requirement/spec/architecture review.

## Commands bắt buộc

Before archive, run:

```bash
python3 {{ platform.framework_root }}/tools/gate-check/cli.py archive-ready {{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md
python3 {{ platform.framework_root }}/tools/gate-check/cli.py teaching-moment {{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md
```

Before reset, run:

```bash
python3 {{ platform.framework_root }}/tools/gate-check/cli.py reset-ready {{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md
```

Any non-zero exit aborts the operation and the reason must be shown to the user.

## Lifecycle surface

1. `archive_active_context(ticket_id, status="completed")`
2. `update_knowledge_snapshot(discoveries)` when status is `completed`
3. `push_to_agent_memory(ticket_id)` after snapshot update and before reset
4. `reset_active_context()`
5. `restore_from_archive(ticket_id)` when resuming
6. `rotate_archive(keep_n=20)` when archive grows too large

Read [references/archive-active-context.md](references/archive-active-context.md) before archiving.
Read [references/reset-active-context.md](references/reset-active-context.md) before resetting active context.
Read [references/snapshot-promotion.md](references/snapshot-promotion.md) before updating knowledge snapshot.
Read [references/m7-memory-push.md](references/m7-memory-push.md) before pushing task learnings to agent memory.
Read [references/token-calibration.md](references/token-calibration.md) when calibrating `TOKEN_LOG.md` after archive.
Read [references/violation-tracking.md](references/violation-tracking.md) when tracking repeated workflow/rule violations from archived tasks.
Read [references/archive-rotation.md](references/archive-rotation.md) before rotating archive or writing cross-repo snapshot pointers.

## Output

- Archive folder: `{{ platform.framework_root }}/knowledge/archive/{ticket-id}/`
- Snapshot update: `{{ platform.framework_root }}/knowledge/long-term/knowledge-snapshot.md`
- Reset active context: `{{ platform.framework_root }}/knowledge/active/`
- Transparency log update: `AGENT_TRANSPARENCY.md`

## Cập nhật AGENT_TRANSPARENCY

Ghi:
- `[x] knowledge-curator: archive_active_context({ticket_id})`
- `[x] knowledge-curator: update_knowledge_snapshot`
- `[x] knowledge-curator: reset_active_context`
- lỗi hoặc aborted gate nếu có.
