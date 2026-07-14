# Multi-host runtime failure inventory

Baseline audited: `master-v2` at `2d3a1f887349b20cd6675703f546edf74bde40d6`.

The canonical project core and multi-platform project configuration already
exist, but worker execution is still init-bound.  The scaffold renders the
selected platform's worker command into the shared
`.maika/profiles/execution-mode.yaml`; the microloop orchestrator reads that
file directly, while setup doctor independently selects a strategy through
`cli/workers.py`.  No production runtime profile loader or active-session
resolver exists at this baseline.

## Test-to-impact mapping

| Test | Baseline evidence | Production impact |
| --- | --- | --- |
| `test_canonical_core_is_always_maika` | Passes | Prevents host adapters from reintroducing platform-owned project cores. |
| `test_project_can_enable_multiple_platforms` | Passes | Preserves the shared-project, multi-adapter configuration prerequisite. |
| `test_worker_resolves_by_active_host_not_init_platform` | Strict xfail: `cli.runtime.worker_resolver` is absent | A Claude session in a project initialized by Codex can dispatch the wrong worker. |
| `test_runtime_ignores_init_rendered_worker_executable` | Strict xfail; worker command is rendered into shared `execution-mode.yaml` | Switching hosts retains the executable baked in during init. |
| `test_primary_is_only_a_fallback_not_runtime_truth` | Strict xfail; no explicit/current-session resolution API exists | Changing the primary platform can override the host actually running a task. |
| `test_inverse_worker_resolves_codex_under_codex_host` | Strict xfail: resolver is absent | The mismatch is bidirectional, not specific to Claude Code. |

The four strict xfails were remediation targets, not accepted behavior. Their
markers were removed in A2 after per-platform profiles and the canonical
resolver made the original expectations pass unchanged.

## Shadow-policy evidence

- `cli/commands/doctor.py` calls `cli.workers.select_worker_strategy`.
- `.maika/tools/microloop-orchestrator/orchestrator.py` independently validates
  worker placeholders, builds argv, and launches the worker from the rendered
  shared profile.
- `cli/commands/task.py` loads `execution-mode.yaml` and hands that config to the
  file-based orchestrator path.
- `cli/platforms/detection.py` reports detected facts to doctor, but platform
  enable and runtime profile generation do not consume those facts.

This split means a green unit test for `cli/workers.py` does not prove that the
actual task execution path follows the same policy.
