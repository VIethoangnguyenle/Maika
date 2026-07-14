# Maika vNext W7 Final Cutover Dogfood Report

Date: 2026-07-10

## Scope

W7 removes the last live legacy runtime surfaces and makes the vNext task lifecycle the only public workflow.

## Scenarios Covered

| Scenario | Coverage | Result |
|---|---|---|
| Default engine | `cli/tests/test_vnext_w2_reasoning_layer.py::test_vnext_is_default_workflow_engine` asserts `.maika/profiles/execution-mode.yaml` uses the vNext engine. | Passed in focused run before final CI. |
| Code write authorization | `.maika/hooks/write-gate/tests` covers allowed app writes, denied writes without an executing workspace, denied writes outside task scope, non-vNext engine denial, and Bash write gating. | Passed: 74 tests. |
| Public task lifecycle | `cli/tests/test_task_command.py` covers start/explore/spec/plan/review/apply/status/verify/archive and queue/report/archive contracts. | Covered by umbrella CI. |
| Orchestrator surface | `.maika/tools/microloop-orchestrator/tests/test_vnext_cli_e2e.py::test_orchestrator_exposes_only_vnext_commands` asserts only vNext commands are exposed. | Passed in focused run before final CI. |
| Dashboard observability | `cli/tests/test_dashboard_reader.py` and `cli/tests/test_dashboard_server.py` read vNext state, queue, briefs, results, reviews, and dispatch log artifacts. | Passed in focused run before final CI. |
| Scaffold/export surface | `cli/tests/test_snapshots.py` regenerated platform snapshots after deleting retired workflow/procedure/template files. | To be re-run in final verification. |
| Stale artifact names | `rg` scans live paths for retired names including `TASK_HANDOFF`, `TASK_QUEUE.md`, legacy engine markers, and retired workflow names. | Clean before final verification except snapshots, then regenerated. |

## Sensitive-Path Note

The Maika repository does not contain production Java, database migration, Kafka, or gRPC application code. W7 dogfood therefore covers those classes through repository-available enforcement boundaries: task scope, write authorization, plan queue contracts, result/review gates, dashboard readers, and stale-surface scans.

## Final-Cutover Decision

Proceed with W7 once final umbrella CI, snapshot refresh, stale scans, and `git diff --check` pass. The intended post-W7 public entrypoint is `maika task`; `/tdd`, legacy markdown microloop apply, OpenSpec-style workflow fallbacks, and retired knowledge templates are not live repository surfaces.
