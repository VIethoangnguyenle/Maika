# Context Loader

Load only the artifact needed for the current role:

- intent roles: `CHANGE.yaml`, `INTENT.md`
- grounding roles: `INTENT.md`, repository source, durable knowledge
- reconciliation and brainstorming roles: grounding and evidence artifacts
- spec and plan roles: `SPEC.md`, `IMPLEMENTATION_PLAN.md`, evidence manifest
- execution and review roles: one brief, one result, one review package

Use `knowledge-index.yaml` to select durable knowledge slices just in time at
the decision-gate. Do not preload entire session history. Use file paths and
capability IDs.
