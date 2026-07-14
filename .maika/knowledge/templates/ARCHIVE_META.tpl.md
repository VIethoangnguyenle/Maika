---
ticket_id: "<!-- ABC-123 -->"
archived_at: "<!-- 2026-MM-DD HH:mm +07 -->"
status: "<!-- completed | stashed | cancelled -->"
state_at_archive: "<!-- state từ changes/<id>/STATE.yaml -->"
task_type: "<!-- feature | fixbug | refactor | changerequest -->"
---

# ARCHIVE_META — {ticket_id}

## Summary

<!-- 1-2 câu: task làm gì, output chính là gì -->

## Flags

```yaml
conv_rescan_required: false   # true nếu task_type=refactor — R-Conv-5
dna_revalidation_suggested: false  # true nếu ≥2 refactor tasks kể từ last DNA scan — L5
violations_tracked: 0         # số violation patterns ghi nhận trong phiên — M3
spec_validator_result: "n/a"  # pass | block | n/a — M1
```

## Stash Note

<!-- Chỉ điền khi status=stashed -->
<!-- stash_reason: -->
<!-- hot_swap_ticket: -->
