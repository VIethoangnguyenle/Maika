# Workflow: /tdd

Use `infra-tdd` for architectural infrastructure design work that needs an
explicit technical design document, operational decisions, verification
strategy, migration, and rollback.

## Steps

1. Read `{{ platform.framework_root }}/skills/infra-tdd/SKILL.md`.
2. Gather module purpose, constraints, current evidence, and target behavior.
3. Write `docs/tdd/<module>-TDD.md`.
4. Write ADR files under `docs/tdd/<module>-adr/` when a decision needs a durable
   record.
5. Feed approved design decisions back into `SPEC.md`.
