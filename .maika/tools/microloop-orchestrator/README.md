# vNext Task Orchestrator

The orchestrator drives the canonical Maika task lifecycle under
`{{ platform.framework_root }}/changes/<change-id>/`.

## Runtime Artifacts

Artifact layout is class-aware:

- `trivial`: `TASK.yaml` (Inspect → Change → Verify)
- `small`: `TASK.yaml`, `EVIDENCE.yaml`, `RESULT.yaml` (maximum two workers)
- `standard` / `architectural`: the full artifact chain below

- `STATE.yaml`
- `CHANGE.yaml`
- `SPEC.md`
- `IMPLEMENTATION_PLAN.md`
- `generated/PLAN_VALIDATION.json`
- `generated/PLAN_MANIFEST.json`
- `generated/TASK_QUEUE.json`
- `generated/DISPATCH_LOG.jsonl`
- `briefs/TASK-*.md`
- `results/TASK-*.yaml`
- `reviews/*.md`

## Commands

```bash
python orchestrator.py vnext-init --changes-root <root> --id <id> --class <class> --title <title>
python orchestrator.py vnext-start-exploration --workspace <ws> --repo-root <repo>
python orchestrator.py vnext-validate-reasoning --workspace <ws> --repo-root <repo>
python orchestrator.py vnext-compile --workspace <ws> --repo-root <repo>
python orchestrator.py vnext-review-plan --workspace <ws> --repo-root <repo>
python orchestrator.py vnext-run --workspace <ws> --repo-root <repo>
python orchestrator.py vnext-status --workspace <ws> --repo-root <repo>
```

`adaptive_runtime.py` is the single deterministic classifier/budget policy.
`vnext_state.py` is the only production writer of `STATE.yaml` and uses atomic
replacement. `runtime_hardening.py` owns structured command execution, workspace
locks, evidence freshness, compact knowledge slices, and structured review parsing.

## Run Tests

```bash
python -m pytest tests/ -q
```
