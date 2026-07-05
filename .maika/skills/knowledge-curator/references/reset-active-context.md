# Reset Active Context

> Tài liệu tham khảo cho `knowledge-curator`. Read before resetting active context.

## Mục lục

- Pre-check
- Reset steps
- Ideation rule

## Pre-check

Run:

```bash
python3 {{ platform.framework_root }}/tools/gate-check/cli.py reset-ready {{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md
```

Exit non-zero aborts reset. Reset is destructive and requires phase_state `completed`, `cancelled`, or `stashed` plus a valid Teaching Moment Check.

## Reset steps

1. Copy templates into active REQUIREMENT, EXPLORE_CONTEXT, AGENT_TRANSPARENCY.
2. Reset TOKEN_LOG.md from template if present.
3. Remove SESSION_OVERRIDE.md and `.session_state.json`.
4. Report `Active context reset. Ready for new task.`

## Ideation rule

Do not delete active ideation drafts unless archive already copied them or user explicitly requested clearing ideation.
