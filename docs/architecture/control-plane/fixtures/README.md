# Control Plane contract fixtures

These versioned YAML files are executable examples for ADR-001 and ADR-002.
They are intentionally independent from the current runtime implementation so
the same cases can drive:

- the event simulator;
- projection tests;
- future state-machine unit tests;
- compatibility-adapter tests.

## Files

- `state-contract.yaml`: machine-readable enums, transition graphs, terminal
  states and aggregation precedence.
- `run-transition-cases.yaml`: run lifecycle, phase and aggregate-version cases.
- `worker-transition-cases.yaml`: one-attempt worker lifecycle cases.
- `run-aggregation-cases.yaml`: sequential, parallel, retry, blocker and terminal
  aggregation snapshots.
- `legacy-state-projection-cases.yaml`: current `STATE.yaml.state` compatibility
  mappings and explicitly incomplete legacy cases.

## Fixture protocol

Every suite has:

```yaml
schema_version: 1
contract: ADR-001 | ADR-002
cases:
  - id: stable-unique-id
    description: human-readable purpose
    input: {}
    expected: {}
```

Consumers MUST fail on an unsupported `schema_version`. Case order is not
semantic. `id` is the stable test parameter ID.

For transition suites, `expected.accepted: false` means no state event and no
version increment. For aggregation, `expected.error` means the contract refuses
to invent a lifecycle for an incomplete snapshot.

Paths in `source_refs` are repository-relative and document why a compatibility
case exists; simulators do not need to dereference them.
