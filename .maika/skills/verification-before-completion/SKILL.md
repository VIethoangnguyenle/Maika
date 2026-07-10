---
name: verification-before-completion
version: '1.0'
description: >
  Verify Maika vNext completion claims with fresh commands, observed output,
  deleted-reference scans, scaffold checks, and recorded evidence before archive
  or final status is allowed.
---

# Verification Before Completion

## Purpose
Require evidence before any completion claim.

## Triggers
Use before marking a task, wave, or change complete; before archive; and before
reporting tests as passing.

## Inputs
- `SPEC.md`
- `IMPLEMENTATION_PLAN.md`
- Task results and reviews.
- Verification commands.
- Capability IDs: `runtime_verification`, `version_control`.

## Required outcomes
- `verification/COMMANDS.yaml`.
- `verification/VERIFICATION_REPORT.md`.
- Evidence files for important command output when needed.

## Invariants
- No completion claim without a fresh command.
- Exit code alone is not enough.
- Deleted-reference and stale-artifact scans are mandatory when files are
  removed.

## Evidence requirements
Record command, expected output, observed output, exit code, timestamp, and
interpretation for every completion claim.

## Process
1. Identify commands that prove the claim.
2. Run them fresh.
3. Read output and exit codes.
4. Record evidence.
5. Report only what evidence supports.

## Stop conditions
- Any mandatory command fails.
- Output is ambiguous.
- Required scan finds removed references.

## Output contract
Write verification artifacts and return `VERIFIED` or `FAILED_VERIFICATION`.

## Next handoff
`knowledge-curator` and archive.
