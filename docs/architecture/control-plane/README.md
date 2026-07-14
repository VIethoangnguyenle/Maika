# Maika Control Plane architecture guide

Maika Control Plane is currently an **architecture and runtime-contract
foundation**, not a shipped dashboard. Its agreed architecture is an:

> **Event-log-backed operational control plane.**

During the initial migration, `STATE.yaml` and existing Maika operations remain
authoritative. Runtime events are shadow telemetry, projections are rebuildable
verification views, and future commands must call adapters around existing
operations. Moving runtime authority to events is an optional, evidence-driven
decision gate—not an assumed destination.

## Document map

Read the documents in this order:

1. [Product and UX design](product-design.md) — product thesis, users, journeys,
   information architecture and phased scope.
2. [ADR-001: Two-Axis Run State Model](adr-001-two-axis-run-state.md) — canonical
   run lifecycle, workflow phase and aggregate-version contract.
3. [ADR-002: Worker Lifecycle and Run Aggregation](adr-002-worker-lifecycle-and-run-aggregation.md)
   — worker attempts, retries, timeouts and deterministic run aggregation.
4. [Fixture protocol](fixtures/README.md) — executable contract examples for
   simulators, projections and unit tests.
5. [Visual design constitution](DESIGN.md) — tokens, components, interaction,
   accessibility and visual QA for a future UI.

The ADRs own runtime semantics. `DESIGN.md` owns presentation. Product design
must not redefine lifecycle or transition rules in prose.

## Canonical machine-readable contract

The contract entrypoint is:

```text
docs/architecture/control-plane/fixtures/state-contract.yaml
```

It defines:

- run lifecycle states and allowed transitions;
- workflow phases and allowed transitions;
- valid lifecycle/phase combinations;
- aggregate-version behavior;
- worker execution states and transitions;
- run aggregation precedence.

Consumers must reject unknown `schema_version` values rather than applying a
best-effort interpretation.

## Validate the contract

From the repository root:

```bash
python -m pytest cli/tests/test_control_plane_contract_fixtures.py -q
```

To include the current state and dispatch regression suites:

```bash
python -m pytest \
  cli/tests/test_control_plane_contract_fixtures.py \
  .maika/tools/microloop-orchestrator/tests/test_vnext_state.py \
  .maika/tools/microloop-orchestrator/tests/test_vnext_dispatch.py \
  -q
```

The contract guards check that:

- every transition target belongs to a declared enum;
- terminal run and worker states have no outgoing transition;
- accepted/rejected transition cases agree with the machine-readable graph;
- aggregate version changes only for accepted mutations;
- aggregation fixtures use declared run and worker states;
- legacy projection covers every current `STATE.yaml.state` value.

## Use fixtures in a simulator

Fixture files are ordinary YAML. A simulator should load
`state-contract.yaml` first, then replay one or more case suites:

```python
from pathlib import Path
import yaml

fixture_root = Path("docs/architecture/control-plane/fixtures")
contract = yaml.safe_load((fixture_root / "state-contract.yaml").read_text())
suite = yaml.safe_load((fixture_root / "run-transition-cases.yaml").read_text())

if contract["schema_version"] != 1 or suite["schema_version"] != 1:
    raise ValueError("unsupported Control Plane fixture schema")

for case in suite["cases"]:
    simulator.run_case(case["id"], case["input"], case["expected"])
```

The example uses a conceptual `simulator.run_case`; no Control Plane simulator
command exists yet. The fixtures are deliberately implementation-neutral so a
future simulator and unit tests can consume the same cases.

## Use fixtures in unit tests

Parameterize directly by the stable case ID:

```python
import pytest
import yaml

CASES = yaml.safe_load(
    open(
        "docs/architecture/control-plane/fixtures/worker-transition-cases.yaml",
        encoding="utf-8",
    )
)["cases"]


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
def test_worker_transition_contract(case):
    observed = transition_worker(case["input"])
    assert observed == case["expected"]
```

A runtime implementation may produce richer output, but it must be reducible to
the fixture's expected contract fields.

## Fixture suites

### Run transitions

`fixtures/run-transition-cases.yaml` covers creation, activation, waiting,
blocking, resume, phase changes, completion, cancellation, failure, idempotent
no-op, illegal edges and stale aggregate versions.

When one logical operation changes both lifecycle and phase, it increments
`aggregate_version` once even if it emits two canonical events.

### Worker transitions

`fixtures/worker-transition-cases.yaml` models one immutable worker attempt.
`BLOCKED`, `SUCCEEDED`, `FAILED`, `TIMED_OUT` and `CANCELLED` are terminal for
that attempt. Retry creates a new `worker_execution_id` and increments `attempt`.

### Run aggregation

`fixtures/run-aggregation-cases.yaml` covers sequential and parallel snapshots.
The outcome precedence is:

```text
COMPLETED → FAILED → ACTIVE → BLOCKED → WAITING → ERROR
```

If no rule matches, consumers must return `NO_PROGRESS_CLASSIFICATION`; they
must not silently invent `WAITING`.

### Legacy projection

`fixtures/legacy-state-projection-cases.yaml` maps the current combined
`STATE.yaml.state` enum into ADR-001's two axes. Existing `CANCELLED` workspaces
without a preceding event are intentionally incomplete because the current
state file does not retain their prior phase.

## Add or change a contract rule

Use this order:

1. Update the owning ADR and explain the decision/consequence.
2. Update `fixtures/state-contract.yaml`.
3. Add accepted, rejected and boundary cases to the relevant fixture suite.
4. Update the compatibility suite if current runtime mapping changes.
5. Run the contract guards and current-runtime regression suites.
6. Only then implement or instrument runtime behavior in a separate change.

Do not change a runtime enum first and retrofit the ADR afterward. Do not add a
fixture that contradicts `state-contract.yaml` to preserve accidental behavior.

## Current runtime boundary

The ADR source-evidence tables identify every current runtime claim by repository
path and symbol. The most important boundaries are:

- `.maika/tools/microloop-orchestrator/vnext_state.py::transition` owns current
  `STATE.yaml` transitions;
- `.maika/tools/microloop-orchestrator/vnext_dispatch.py::run_queue` is currently
  sequential and stops on the first blocked task;
- `.maika/tools/microloop-orchestrator/orchestrator.py::make_worker_runner`
  owns fresh-process timeout behavior;
- `.maika/tools/gate-check/gates.py` exposes synchronous gate validators, not a
  durable gate event lifecycle.

The contract does not authorize dashboard work, runtime refactoring or changes
to Understand-Anything MCP, Codebase Memory MCP or DB Access.

## Planned migration boundary

The safe implementation order remains:

```text
runtime contract
→ fixture/event simulator
→ shadow telemetry
→ projection verification
→ safe command adapters
→ vertical-slice UI
→ optional runtime-authority decision
```

Until shadow projection proves deterministic replay with effectively zero
unexplained drift, current Maika state remains authoritative.
