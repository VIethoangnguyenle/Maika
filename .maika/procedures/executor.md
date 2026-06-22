# Procedure: Executor (one Hybrid Contract DAG node)

> Consumed by the agent acting as a role-specific coding executor. Input: a `TASK_HANDOFF.<node-id>.md` path.
> Output: `TASK_RESULT.<node-id>.md`, or one request artifact when blocked.

1. Read the TASK_HANDOFF at the given path. Note: task, dna_slice, convention_slice,
   spec_slice, snapshot_slice, contract_snapshot, written_files, boundary, feedback.
2. Read actual existing files from disk for every path listed in `written_files`,
   `contract_snapshot.source_file`, and task read-only files. Do not rely on summaries alone.
3. Execute only the assigned node:
   - Contract node: write/update the contract file and produce `CONTRACT_SNAPSHOT.<node-id>.md`.
   - Leaf node: implement only the child/adapter/mapper/repository file allowed by the handoff.
   - Integration node: apply queued `INTEGRATION_REQUEST` entries to shared wiring files.
   - Test node: add or update tests described by the handoff.
4. Obey hard boundaries:
   - Do not call UA/KG, DB, agent-memory, or Codebase Memory tools directly.
   - Do not edit files outside `allowed_files`.
   - Do not edit frozen contract/base files from a leaf node.
   - Do not edit shared wiring files from a leaf node.
   - Do not introduce dependencies that are absent from the spec or handoff.
5. If context is missing, stop and write `CONTEXT_REQUEST.<node-id>.md`.
6. If a leaf node needs the contract changed, stop and write `CONTRACT_CHANGE_REQUEST.<node-id>.md`.
7. If a leaf node needs registry/config/wiring, write `INTEGRATION_REQUEST.<node-id>.md`
   and continue only if the feature code itself can be completed without editing the shared file.
8. Write changed files to disk.
9. Write `TASK_RESULT.<node-id>.md` with: task_id, changed_files, gate_status set to `PENDING`,
   gate_violations as `[]`, and self_flagged for any unresolved concern.
10. Stop. The orchestrator owns gate execution, retries, stale invalidation, and task advancement.
