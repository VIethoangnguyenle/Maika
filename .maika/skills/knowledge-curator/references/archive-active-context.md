# Archive Active Context

> Tài liệu tham khảo cho `knowledge-curator`. Read before archiving active context.

## Mục lục

- Pre-checks
- Status meanings
- Archive steps

## Pre-checks

Run:

```bash
python3 {{ platform.framework_root }}/tools/gate-check/cli.py archive-ready {{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md
python3 {{ platform.framework_root }}/tools/gate-check/cli.py teaching-moment {{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md
```

Exit non-zero aborts archive.

## Status meanings

- `completed`: apply done; update knowledge snapshot.
- `stashed`: paused; do not update snapshot.
- `cancelled`: abandoned; do not update snapshot.

## Archive steps

1. Create `{{ platform.framework_root }}/knowledge/archive/{ticket_id}/`.
2. Copy REQUIREMENT, EXPLORE_CONTEXT, AGENT_TRANSPARENCY, TOKEN_LOG if present, SESSION_OVERRIDE if present, `.session_state.json` if present, and `active/ideation/` if present.
3. Create ARCHIVE_META.md with ticket_id, archived_at, status, summary, phase_at_archive, stash_note if stashed, token_total_estimate.
4. Verify copied files can be read.
5. If status is `completed`, run snapshot update.
6. Report archive path.
