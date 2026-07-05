# Architecture Reviewer Gotchas

> Tài liệu tham khảo cho `architecture-reviewer`. Read when confidence, conventions, contract, or upstream-library questions appear.

## Gotchas

- **G1 knowledge-snapshot stale**: check `<!-- verified: YYYY-MM-DD -->`. If older than 30 days, treat as reference and cross-verify with UA graph.
- **G2 conventions draft**: use only approved `conventions.yaml`, not `conventions.draft.yaml`.
- **G3 M6 needs REQUIREMENT**: skip M6 when REQUIREMENT is empty or skeleton.
- **G4 upstream boundary**: do not propose changing upstream library contracts; warn only when downstream implementation diverges.
