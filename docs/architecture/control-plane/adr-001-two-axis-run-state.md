# ADR-001: Two-Axis Run State Model

Status: Accepted (2026-07-14)

## Context

Maika hiện lưu một trường `STATE.yaml.state` vừa biểu diễn workflow phase, vừa
biểu diễn tình trạng vận hành và terminal state. `vnext_state.STATES` chứa đồng
thời `EXPLORING`, `EXECUTING`, `BLOCKED`, `COMPLETED`, `ARCHIVED` và
`CANCELLED`; `vnext_state.transition()` kiểm tra tất cả bằng một transition
table duy nhất.

Mô hình này đủ cho runtime tuần tự hiện tại nhưng không trả lời độc lập hai câu
hỏi mà Control Plane cần:

1. Run đang ở công đoạn workflow nào?
2. Run có thể tiến triển ngay lúc này không?

Ví dụ, `BLOCKED` hiện làm mất phase trên trường `state`; phase chỉ có thể được
khôi phục gián tiếp từ `blocked.resume_state`. Một run bị block trong exploration
và một run bị block trong verification vì thế có cùng top-level state.

## Current-runtime evidence (`master-v2`)

Các nhận định trong ADR này dựa trên runtime hiện tại, không chỉ dựa trên tài
liệu Control Plane:

| Concern | Source path | Symbol / behavior |
|---|---|---|
| State enum và transition authority | `.maika/tools/microloop-orchestrator/vnext_state.py` | `STATES`, `ALLOWED`, `transition()` |
| Atomic `STATE.yaml` writer | `.maika/tools/microloop-orchestrator/vnext_state.py` | `_dump_yaml()` |
| Guard chống writer thứ hai | `cli/tests/test_canonical_state_mutation.py` | `test_only_canonical_state_service_writes_state_yaml()` |
| Action routing | `.maika/config/workflow-router.yaml` | `actions.*.allowed_from`, `success_state`, `failure_routes` |
| Router validation | `cli/agent_content/router.py` | `_runtime_surfaces()`, `validate_router()`, `resolve_route()` |
| Block/resume metadata | `.maika/tools/microloop-orchestrator/vnext_state.py` | `transition()` stores `previous_state` and `resume_state` |
| External-request blocker | `.maika/tools/microloop-orchestrator/vnext_dispatch.py` | `block_on_refresh_request()`, `fulfill_blocked_request()` |
| Generic resume | `.maika/tools/microloop-orchestrator/orchestrator.py` | `vnext-resume` branch in `_main_unlocked()` |
| Public cancel/verify/archive | `cli/commands/task.py` | `_cancel()`, `_verify_lightweight()`, `_verify()`, `_archive()` |
| Other state-changing call sites | `.maika/tools/microloop-orchestrator/orchestrator.py` | `_main_unlocked()` calls `vs.transition()` |
| Change-loop resume | `cli/commands/loop.py` | `run_loop()` resume branch |

`STATE.yaml` remains authoritative during the shadow-telemetry migration. This
ADR defines the target contract and its compatibility projection; it does not
authorize a runtime refactor.

## Decision

Every `ChangeRun` has exactly one canonical run-state tuple:

```yaml
lifecycle: <RunLifecycle>
current_phase: <WorkflowPhase>
aggregate_version: <integer>
```

Other run metadata may exist, but it is not part of the state tuple. Lifecycle
and phase MUST NOT be collapsed into one enum.

At most one `current_phase` exists for a run. It is the central orchestrator's
coordination phase, not a worker-owned phase. Worker role, task and execution
state are modeled separately by ADR-002.

Only the central orchestrator may mutate this tuple. Workers, providers, gates,
the UI and projections may request or observe a transition, but MUST NOT commit
one directly.

## RunLifecycle

```text
CREATED
ACTIVE
WAITING
BLOCKED
COMPLETED
FAILED
CANCELLED
```

| Lifecycle | Meaning |
|---|---|
| `CREATED` | Run identity exists, but execution has not been activated. |
| `ACTIVE` | At least one required path is running, starting or immediately runnable. |
| `WAITING` | No required path can run now; an automatic resolution is expected. |
| `BLOCKED` | No required path can run now; human or evidence remediation is required. |
| `COMPLETED` | Completion policy passed. Terminal success. |
| `FAILED` | A mandatory path failed terminally and no retry/fallback remains. |
| `CANCELLED` | An authorized cancellation terminated the run intentionally. |

`WAITING` MUST NOT be used for approval, missing user input, unsafe action or
mandatory evidence remediation. Those conditions are `BLOCKED`.

`BLOCKED` MUST NOT be used merely because one worker is blocked. ADR-002 owns
the aggregation rule.

### Lifecycle transitions

```text
CREATED   -> ACTIVE | FAILED | CANCELLED
ACTIVE    -> WAITING | BLOCKED | COMPLETED | FAILED | CANCELLED
WAITING   -> ACTIVE | BLOCKED | FAILED | CANCELLED
BLOCKED   -> ACTIVE | FAILED | CANCELLED
COMPLETED -> (none)
FAILED    -> (none)
CANCELLED -> (none)
```

Terminal recovery, if introduced later, MUST create a new run or be authorized
by a separate recovery ADR. It is not an implicit transition out of a terminal
state.

## WorkflowPhase

```text
INTAKE
EXPLORING
RECONCILING
BRAINSTORMING
SPECIFYING
PLANNING
EXECUTING
REVIEWING
VERIFYING
ARCHIVING
```

A run has one coordination phase even when multiple workers run in parallel.
Workers do not acquire independent run phases. A task may record the phase that
created it for provenance, but that value does not change `current_phase`.

### Phase transitions

The initial target graph preserves transitions that are executable on
`master-v2` while removing review checkpoints from the phase enum:

```text
INTAKE        -> EXPLORING | PLANNING | EXECUTING
EXPLORING     -> RECONCILING | BRAINSTORMING
RECONCILING   -> BRAINSTORMING
BRAINSTORMING -> SPECIFYING
SPECIFYING    -> PLANNING
PLANNING      -> EXECUTING
EXECUTING     -> REVIEWING | VERIFYING
REVIEWING     -> VERIFYING | ARCHIVING
VERIFYING     -> REVIEWING | ARCHIVING
ARCHIVING     -> (none)
```

`SPEC_REVIEW` is a gate/checkpoint inside `SPECIFYING`; `PLAN_REVIEW` is a
gate/checkpoint inside `PLANNING`; `FINAL_REVIEW` is represented by
`REVIEWING`. Entering or leaving such a checkpoint does not necessarily emit a
phase change.

Skipping a phase is allowed only when an explicit class/workflow policy permits
the corresponding edge. The graph above defines possible edges, not permission
for every change class.

## Valid lifecycle/phase combinations

- `CREATED` is valid only with `INTAKE`.
- `ACTIVE`, `WAITING` and `BLOCKED` are valid with any nonterminal coordination
  phase.
- `COMPLETED` is valid only with `ARCHIVING`; completion occurs after required
  archive policy has finished.
- `FAILED` and `CANCELLED` preserve the phase in which termination happened.
- A lifecycle-only change preserves `current_phase` unless its operation also
  carries an accepted phase transition.
- A phase change is allowed only while lifecycle is `ACTIVE`.

The `COMPLETED` rule intentionally differs from today's single-state name. In
the current runtime, `STATE.yaml.state == COMPLETED` still has a runnable public
`archive` action, while `ARCHIVED` is the actual end of that path. The shadow
adapter therefore maps current `COMPLETED` to `ACTIVE/ARCHIVING` and current
`ARCHIVED` to `COMPLETED/ARCHIVING`.

## Block and resume semantics

Blocking changes lifecycle only:

```yaml
before:
  lifecycle: ACTIVE
  current_phase: EXPLORING

after:
  lifecycle: BLOCKED
  current_phase: EXPLORING
```

Resume returns lifecycle to `ACTIVE` and preserves phase. It MUST NOT advance
the workflow phase. The original gate or phase completion contract must run
again.

Blocker state is a separate aggregate child with identity, scope and
remediation. A blocker may exist while lifecycle remains `ACTIVE` if another
required path can still progress.

## Aggregate version

`aggregate_version` is a positive, monotonically increasing version of the run
aggregate:

- Initial `run.created` state has version `1`.
- One accepted logical operation increments the version exactly once.
- If one operation changes both lifecycle and phase, both emitted events carry
  the same `aggregate_version_before` and `aggregate_version_after`.
- Opening/resolving/cancelling a run-scoped blocker increments the version even
  if aggregation leaves lifecycle `ACTIVE`.
- Worker heartbeat, logs, provider progress and artifact preview do not change
  it.
- Worker-state changes change it only when central aggregation also commits a
  run-state or run-scoped blocker mutation.
- A rejected operation or idempotent no-op does not increment it.

Commands MUST supply an expected aggregate version. A mismatch rejects the
command as stale before side effects begin.

## Canonical state events

Initialization uses `run.created` with the full initial tuple. Subsequent state
mutations use only:

```text
run.lifecycle_changed
run.phase_changed
```

`run.blocked`, `run.resumed` and `run.activated` are derived UI labels, not
additional canonical state events. `blocker.opened` and `blocker.resolved` are
canonical blocker events and may share the same operation/version change as a
`run.lifecycle_changed` event.

## Compatibility projection from current STATE.yaml

During shadow telemetry, the adapter uses this mapping:

| Current `STATE.yaml.state` | Lifecycle | Phase |
|---|---|---|
| `INTAKE` | `ACTIVE` | `INTAKE` |
| `EXPLORING` | `ACTIVE` | `EXPLORING` |
| `RECONCILING` | `ACTIVE` | `RECONCILING` |
| `BRAINSTORMING` | `ACTIVE` | `BRAINSTORMING` |
| `SPEC_REVIEW` | `ACTIVE` | `SPECIFYING` |
| `PLANNING`, `PLAN_REVIEW` | `ACTIVE` | `PLANNING` |
| `EXECUTING` | `ACTIVE` | `EXECUTING` |
| `FINAL_REVIEW` | `ACTIVE` | `REVIEWING` |
| `VERIFYING` | `ACTIVE` | `VERIFYING` |
| `COMPLETED` | `ACTIVE` | `ARCHIVING` |
| `ARCHIVED` | `COMPLETED` | `ARCHIVING` |
| `BLOCKED` | `BLOCKED` | map `blocked.resume_state` using this table |
| `CANCELLED` | `CANCELLED` | preserve phase from the preceding event |

Existing cancelled workspaces that have no preceding event cannot be projected
losslessly because current `transition()` does not retain the previous phase on
cancel. The importer MUST report `INCOMPLETE_EVENT_STREAM`; it MUST NOT invent a
phase. New shadow telemetry records the before-state before cancellation.

The current runtime has no persisted `FAILED` equivalent; most non-success
conditions become `BLOCKED`. The shadow adapter MUST preserve that behavior
until a separate runtime migration is approved.

## Consequences

- Control Plane can show progress condition and workflow location independently.
- Resume no longer needs a synthetic phase jump.
- Parallel-worker behavior can be aggregated without allowing workers to own run
  state.
- Compatibility projection exposes real information loss instead of hiding it.
- `STATE.yaml` schema and runtime code remain unchanged by this ADR task.

## Acceptance criteria

1. Every run state contains lifecycle, current phase and aggregate version.
2. Lifecycle and phase use the enums and transition graphs above.
3. `BLOCKED` is never a phase.
4. Resume preserves phase.
5. Exactly one central orchestrator owns run-state mutation.
6. Terminal lifecycles are absorbing.
7. Aggregate version changes once per accepted logical aggregate mutation.
8. Canonical state events are not duplicated by semantic aliases.
9. Current-runtime compatibility mappings are explicit and testable.
10. Transition fixtures under `fixtures/` cover accepted and rejected cases.
