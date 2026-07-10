# vNext Task Orchestrator

The orchestrator drives the canonical Maika task lifecycle under
`{{ platform.framework_root }}/changes/<change-id>/`.

## Runtime Artifacts

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
python orchestrator.py vnext-compile --workspace <ws> --repo-root <repo>
python orchestrator.py vnext-review-plan --workspace <ws> --repo-root <repo>
python orchestrator.py vnext-run --workspace <ws> --repo-root <repo>
python orchestrator.py vnext-status --workspace <ws> --repo-root <repo>
```

## Run Tests

```bash
python -m pytest tests/ -q
```
