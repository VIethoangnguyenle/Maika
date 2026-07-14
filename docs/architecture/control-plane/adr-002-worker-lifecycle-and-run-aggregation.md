# ADR-002: Worker Lifecycle and Run Aggregation

Status: Accepted (2026-07-14)

## Context

ADR-001 makes run lifecycle independent from workflow phase. This ADR defines
how worker executions contribute to run lifecycle without allowing a worker to
mutate the run directly.

The current `master-v2` runtime has three related but non-equivalent concepts:

- a worker process launched by the orchestrator;
- a task record in `generated/TASK_QUEUE.json`;
- a run state in `STATE.yaml`.

They must not be collapsed into one status enum. A task can survive multiple
worker attempts; a worker attempt can fail while the task remains retryable; a
blocked worker does not necessarily block the whole run.

## Current-runtime evidence (`master-v2`)

| Concern | Source path | Symbol / behavior |
|---|---|---|
| Worker process lifecycle and timeout | `.maika/tools/microloop-orchestrator/orchestrator.py` | `make_worker_runner()`; timeout returns exit code `124` |
| Worker resolution | `.maika/tools/microloop-orchestrator/orchestrator.py` | `_worker_runner()` |
| Runtime timeout/retry policy | `cli/runtime/policy.py` | `RuntimePolicy`, `load_runtime_policy()` |
| Default retry/timeout values | `.maika/profiles/execution-mode.yaml` | `runtime_policy.max_retries`, `worker_timeout_seconds` |
| Queue creation and task dependencies | `.maika/tools/microloop-orchestrator/plan_compiler.py` | `compile_plan()` |
| Queue CAS generation | `.maika/tools/microloop-orchestrator/vnext_dispatch.py` | `_write_queue()` |
| Current task statuses and leases | `.maika/tools/microloop-orchestrator/vnext_dispatch.py` | `_update_task()` |
| Runnable task selection | `.maika/tools/microloop-orchestrator/vnext_dispatch.py` | `_next_pending_task()` |
| Implementation retry loop | `.maika/tools/microloop-orchestrator/vnext_dispatch.py` | `_run_implementation_or_fix()`, `_run_one_task()` |
| Task review lifecycle | `.maika/tools/microloop-orchestrator/vnext_dispatch.py` | `_run_task_review()` |
| Current run aggregation | `.maika/tools/microloop-orchestrator/vnext_dispatch.py` | `run_queue()` |
| Dispatch observation log | `.maika/tools/microloop-orchestrator/vnext_dispatch.py` | `_append_dispatch_log()` |
| Authoring worker dispatch/gates | `.maika/tools/microloop-orchestrator/vnext_dispatch.py` | `run_authoring_dispatch()` |
| Workflow-level block after queue result | `.maika/tools/microloop-orchestrator/orchestrator.py` | `vnext-run` branch in `_main_unlocked()` |
| DAG validation/order | `.maika/tools/microloop-orchestrator/orchestrator.py` | `topo_sort()` |

Current limitations are material to this decision:

- `run_queue()` selects one task at a time and returns immediately when it sees
  the first blocked task.
- `_next_pending_task()` returns the first dependency-ready task; it is not a
  parallel scheduler.
- `_append_dispatch_log()` is an observational JSONL append, not a canonical
  worker lifecycle journal.
- Task status `blocked` does not distinguish human remediation, terminal worker
  failure, timeout or exhausted retry policy.
- Gate validators return synchronous `Result` objects. There is not yet a
  persistent gate started/passed/failed lifecycle.

ADR-002 specifies the Control Plane contract. It does not claim these target
semantics are already implemented.

## Decision: separate Task and WorkerExecution

`Task` is durable work in the DAG. `WorkerExecution` is one attempt to perform a
role/task. Retrying a failed, timed-out or blocked attempt creates a new
`WorkerExecution` with a greater attempt number; it does not reopen the terminal
attempt.

Minimum worker identity:

```yaml
worker_execution_id: wx_<unique>
run_id: C-142
task_id: TASK-001       # nullable for phase/authoring roles
role: grounding
attempt: 1
required: true
state: DISPATCHED
```

`required` is resolved by orchestrator policy. Existing `TASK_QUEUE.json` tasks
default to required because the current compiler has no optional-task field.

## WorkerExecution lifecycle

```text
DISPATCHED
STARTING
RUNNING
WAITING
BLOCKED
SUCCEEDED
FAILED
TIMED_OUT
CANCELLED
```

| State | Meaning |
|---|---|
| `DISPATCHED` | Orchestrator accepted the assignment and created an execution identity. |
| `STARTING` | Local process/remote session is being established. |
| `RUNNING` | Worker acknowledged execution or produced a valid heartbeat/action. |
| `WAITING` | Same execution is paused on an automatically resolvable condition. |
| `BLOCKED` | Attempt stopped and requires intervention/evidence; terminal for this attempt. |
| `SUCCEEDED` | Attempt produced its required output and passed its execution completion contract. |
| `FAILED` | Attempt ended unsuccessfully for a non-timeout reason. |
| `TIMED_OUT` | Runtime timeout expired and the attempt was terminated or fenced. |
| `CANCELLED` | Authorized cancellation stopped or invalidated the attempt. |

### Worker transitions

```text
DISPATCHED -> STARTING | FAILED | CANCELLED
STARTING   -> RUNNING | WAITING | FAILED | TIMED_OUT | CANCELLED
RUNNING    -> WAITING | BLOCKED | SUCCEEDED | FAILED | TIMED_OUT | CANCELLED
WAITING    -> STARTING | RUNNING | BLOCKED | FAILED | TIMED_OUT | CANCELLED
BLOCKED    -> (none)
SUCCEEDED  -> (none)
FAILED     -> (none)
TIMED_OUT  -> (none)
CANCELLED  -> (none)
```

`BLOCKED`, `SUCCEEDED`, `FAILED`, `TIMED_OUT` and `CANCELLED` are terminal for a
single attempt. Retry creates a new execution. This keeps audit history stable
and makes attempt budgets deterministic.

An idempotent observation of the current state is a no-op and emits no
canonical state transition event.

## Worker events

Canonical worker lifecycle facts are:

```text
worker.dispatched
worker.starting
worker.started
worker.waiting
worker.blocked
worker.succeeded
worker.failed
worker.timed_out
worker.cancelled
worker.heartbeat
```

`worker.heartbeat` is at-least-once telemetry and does not itself change the
worker state after `RUNNING`. Lifecycle events are durable and deduplicated by
`event_id`, `operation_id` and worker execution identity.

Exit code `124` from current `make_worker_runner()` maps to `TIMED_OUT`. Other
non-zero exits map to `FAILED` unless a more specific operation contract maps
them to `BLOCKED`. A process exit alone does not decide run lifecycle.

## Task relationship

The target task states are not defined as aliases of worker states. For the
initial migration, current queue statuses are interpreted as follows:

| Current task status | Contract interpretation |
|---|---|
| `pending` | Durable task exists; no active attempt is required yet. |
| `in_progress` | A current worker attempt should be `STARTING` or `RUNNING`; lease is evidence, not proof. |
| `reviewing` | Implementation attempt succeeded; a review attempt/path remains. |
| `changes_required` | Review completed; task is runnable through a new fix attempt. |
| `done` | Task completion policy passed. |
| `blocked` | Ambiguous legacy state; blocker/retry/exit evidence is required to classify it. |

The shadow adapter MUST NOT infer `worker.blocked` solely from a queue value when
the attempt's cause is missing. It reports incomplete telemetry instead.

## Runnable required path

A required task/path is immediately runnable when all of these hold:

1. Its dependency tasks satisfy their completion contracts.
2. It is pending or explicitly eligible for remediation/retry.
3. No unresolved blocker prevents this path.
4. Retry budget remains when a retry is required.
5. Required gates/artifacts for dispatch are valid.
6. No live execution already owns the task lease.
7. Capacity policy permits immediate dispatch.

Capacity unavailable but expected to recover automatically produces a waiting
condition, not a blocker.

## Central aggregation ownership

Only the central orchestrator computes and commits run lifecycle. Worker,
task, provider, gate and blocker events are inputs to that decision. A projection
may recompute the same result for verification but is not authoritative during
the shadow phase.

Aggregation considers only required paths. Optional work is visible but does
not keep a run active or prevent completion unless phase policy promotes it to
required.

## Aggregation precedence

For a nonterminal run, evaluate in this order:

1. **COMPLETED** — completion policy is satisfied: every required task/path is
   complete, required final gates pass and no required blocker remains.
2. **FAILED** — a mandatory path has terminally failed, retry budget is exhausted,
   no fallback exists and policy classifies the outcome as terminal.
3. **ACTIVE** — at least one required execution is `DISPATCHED`, `STARTING` or
   `RUNNING`, or at least one required path is immediately runnable.
4. **BLOCKED** — no required path is active/runnable and at least one required
   condition needs human, approval, safety or evidence remediation.
5. **WAITING** — no required path is active/runnable/blocked and at least one
   required condition is expected to resolve automatically.
6. **ERROR** — no rule matches. The orchestrator reports
   `NO_PROGRESS_CLASSIFICATION`; it MUST NOT silently label the run waiting.

An explicit authorized cancellation is handled before aggregation and commits
`CANCELLED`. An already terminal lifecycle is preserved and is not re-aggregated.

This precedence means a non-critical blocked worker does not block the run while
another required path is runnable. Conversely, a mandatory terminal failure
with no retry/fallback fails the run even if cleanup workers are still running;
the orchestrator must cancel or fence those executions.

## Required aggregation inputs

The aggregation snapshot must provide enough structured information to prove
the selected result:

```yaml
run:
  lifecycle: ACTIVE
  current_phase: EXECUTING
  aggregate_version: 12

workers: []
tasks: []
blockers: []
wait_conditions: []
gates: []

policy:
  completion_satisfied: false
  terminal_failure: false
  phase_can_progress: false
```

Rules MUST NOT infer provider health, gate success or task completion from the
absence of a failure record.

## Retry and timeout

- `max_retries` counts retries after the first attempt, matching current
  `RuntimePolicy` behavior (`0` means one total attempt).
- `FAILED` and `TIMED_OUT` attempts may create a new `DISPATCHED` execution when
  retry policy permits.
- While a retry/backoff is scheduled and no path is runnable, run lifecycle is
  `WAITING`.
- When the budget is exhausted, policy must classify the path as either terminal
  `FAILED` or remediable `BLOCKED`; exhaustion alone is not an implicit choice.
- External workflow/evidence requests do not consume blind retry budget.
- A timed-out remote attempt must be fenced before a replacement attempt can
  write authoritative artifacts.

These rules preserve current behavior in `_run_implementation_or_fix()` where
evidence-update requests stop immediate retry, while making the reason explicit.

## Parallelism

The contract supports parallel worker observations, but it does not require the
current scheduler to dispatch in parallel. Current `run_queue()` remains
sequential until a separate implementation change is approved.

For parallel snapshots:

- one blocked worker plus one runnable required path => `ACTIVE`;
- one failed retryable worker plus scheduled backoff => `WAITING` when nothing
  else can run;
- all required paths intervention-blocked => `BLOCKED`;
- one mandatory non-retryable failure => `FAILED` unless a declared fallback is
  runnable;
- optional workers are ignored for completion and liveness aggregation.

## Aggregate version interaction

Worker state changes do not automatically increment run `aggregate_version`.
If aggregation commits a new run lifecycle or opens/resolves a run-scoped
blocker, that logical operation increments the run version exactly once as
specified by ADR-001. Multiple events in that operation share the same before
and after versions.

## Gate lifecycle boundary

Current gate functions in `.maika/tools/gate-check/gates.py` return synchronous
`Result` values and call sites such as `run_authoring_dispatch()`,
`_run_task_review()` and `_verify()` decide what happens next. ADR-002 consumes
structured gate results but does not define the future gate event contract.

Until that contract exists, a gate is an aggregation input only when its result
is persisted with gate identity, status, subject and artifact references.

## Consequences

- Attempt history is immutable and retry accounting becomes explicit.
- A worker failure no longer implies a run failure.
- Parallel aggregation is deterministic even before parallel dispatch exists.
- Legacy `blocked` task status is recognized as ambiguous instead of overread.
- Runtime implementation, task queue schema and provider code remain unchanged
  by this ADR task.

## Acceptance criteria

1. Task and worker execution are separate identities.
2. Worker lifecycle uses the enum and transition table above.
3. Retry creates a new worker execution.
4. Only the central orchestrator owns run aggregation.
5. Aggregation follows the ordered rules above.
6. Active/runnable required work outranks a remediable blocker on another path.
7. Optional work cannot prevent completion.
8. Timeout and exhausted retry are classified explicitly.
9. An unmatched snapshot returns an error instead of an invented lifecycle.
10. Worker-transition and aggregation fixtures cover sequential and parallel cases.
