# Procedure: Reviewer (Hybrid Contract DAG verification lane)

> Consumed by the agent acting as final verification reviewer. Input: `CONTRACT_DAG.md`,
> `EXTRACTION_INPUT.md`, all `TASK_RESULT.<node-id>.md`, and all `CONTRACT_SNAPSHOT.<node-id>.md`.
> Output: `EXTRACTION_REPORT.md`.

1. Read `CONTRACT_DAG.md` and verify there are no nodes with status `pending`, `in_progress`,
   `blocked`, or `stale`.
2. Read every `TASK_RESULT.<node-id>.md`. Verify changed files match each node's allowed write boundary.
3. Read every `CONTRACT_SNAPSHOT.<node-id>.md`. Verify leaf nodes reference the current contract version.
4. Read `EXTRACTION_INPUT.md` — the complete set of new/changed files, not a top-k slice.
5. Enumerate sibling classes:
   - If a code-graph capability is available, query it for siblings.
   - Otherwise, group changed files by business essence using disk-fallback.
6. For each group with high logic overlap, flag a Template Method opportunity:
   - shared steps in base;
   - child-specific abstract/protected hooks;
   - files affected;
   - risk if ignored.
7. Write `EXTRACTION_REPORT.md` with verdict `CLEAN` or `FLAG`, clusters, contract-version findings,
   boundary findings, and suggested follow-up. Any boundary or contract-version finding forces
   verdict `FLAG`.
8. HP-10/HP-11 style findings are recommendations. Do not auto-refactor and do not block archive
   unless the orchestrator or spec-validator has a hard failure.
