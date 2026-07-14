# Maika vNext W5 Workflow, CLI, Scaffold, and Docs Cutover Plan

## Objective
Expose the canonical vNext task runtime through public commands and remove
obsolete workflow/scaffold surfaces from fresh installs and docs.

## Scope
- Add `maika task` public command wrapper.
- Map public actions to vNext orchestrator commands without creating a second
  state machine.
- Update `workflows/task.md` to document the public command surface.
- Remove obsolete workflow manifest entries and source files.
- Refresh scaffold tree snapshots.
- Update bootstrap, README, init next steps, and stale write-gate/rule wording.
- Record deleted workflow/template paths in the deletion manifest.

## Non-goals
- W6 verification/archive implementation.
- Legacy runtime physical deletion outside the W5 scaffold surface.
- Rewriting author DNA/convention skills.

## Acceptance Criteria
- `maika task start|explore|reconcile|brainstorm|spec|plan|validate-plan|review|apply|status|resume|cancel`
  are parser-visible and route through vNext artifacts.
- `maika task verify|archive` refuse explicitly until W6.
- Fresh scaffold snapshots contain only target workflow files.
- Removed workflow names do not appear in live `.maika`, `cli`, or README paths.
- Update pruning can remove dropped workflow files from downstream installs.
- CLI/scaffold/update/snapshot tests pass.
