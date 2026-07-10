# Maika vNext Meta Prompt

Use the canonical vNext runtime under `{{ platform.framework_root }}`.

## Load Order

1. Read `rules/RULES.md`.
2. Read `skills/skill-index.yaml`.
3. Read `workflows/task.md`.
4. Use capability IDs from `profiles/capabilities.md`.

## Canonical Skills

`intent-analysis`, `grounding-explorer`, `architecture-reconciler`,
`grounded-brainstorming`, `writing-spec`, `writing-plan`, `validating-plan`,
`executing-task`, `reviewing-task`, `reviewing-change`,
`verification-before-completion`, `knowledge-curator`, `author-dna-builder`,
`convention-intelligence-builder`, and `infra-tdd`.

## Runtime Discipline

Execution starts from a reviewed plan, compiled queue, and immutable task brief.
Agents exchange artifact paths and structured results. Concrete provider
behavior belongs in platform adapters, not canonical skills.
