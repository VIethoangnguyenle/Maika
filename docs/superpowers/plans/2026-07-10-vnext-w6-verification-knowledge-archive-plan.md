# Maika vNext W6 Verification, Knowledge, Archive Plan

## Scope

W6 makes the public task lifecycle closeable:

- `maika task verify` validates final review, task result/review artifacts, and
  stale workspace references.
- Verification writes `verification/COMMANDS.yaml` and
  `verification/VERIFICATION_REPORT.md`, then marks the workspace `COMPLETED`.
- `maika task archive` requires verified completion, regenerates
  `knowledge/long-term/knowledge-index.yaml`, writes `ARCHIVE_MANIFEST.yaml`,
  marks the workspace `ARCHIVED`, and moves it to `<framework-root>/archive/`.
- `scripts/run_ci.py` is the umbrella test runner used by local development and
  GitHub Actions.

## Tests

- Add CLI tests for successful verification, failed verification, successful
  archive, and archive state refusal.
- Keep existing task wrapper behavior for start/status/cancel/reconcile.
- Run the W6-focused task command tests before broad verification.
- Run `python3 scripts/run_ci.py` before commit.

## Cleanup

- Remove W6 reservation wording from workflow docs.
- Activate archive-readiness in the enforcement ledger.
- Replace CI's narrow CLI-only test command with the umbrella runner.
