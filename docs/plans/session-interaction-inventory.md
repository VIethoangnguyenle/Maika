# Session Interaction Inventory

Date: 2026-07-12
Baseline: `master-v2` at `96497fbfbdb066181f594b63d77a3b87a20da12d`

This note records Phase 0 discovery for the Maika session-interaction boundary.

## Existing routing and command surfaces

- `cli/maika.py` owns Maika CLI parsing and dispatch. `cli/commands/content.py`
  exposes the existing agent-content validators.
- `.maika/config/workflow-router.yaml` and
  `cli/agent_content/router.py` govern only the task state machine. The runtime
  consumer is `.maika/tools/microloop-orchestrator/`; the human projection is
  `.maika/workflows/task.md`.
- Native slash workflows are provider-owned. The Maika manifest documents
  `/understand` and `/understand-domain` as graph-generation commands but there
  is no universal slash-command interceptor or session interaction router.
- `.maika/agent/KERNEL.md` currently says freeform specification/code requests
  route to `maika task`, but names `workflows/task.md` rather than the YAML
  router as route authority. It does not explicitly distinguish read/query,
  maintenance, report, learning, admin, and application-change lanes.

## Ownership and update behavior

- `cli/plugin-manifest.yaml` is the scaffold source list.
- `cli/install/ownership.py` classifies framework files as replaceable,
  `changes`, `archive`, `loops`, selected knowledge subtrees, and
  `config/project.local.yaml` as project-owned, and host entrypoints as shared.
- The planned `reports/` and `knowledge/preferences/` stores are not yet
  project-owned. They must be added to ownership classification so update and
  uninstall preserve user data. Registry/schema files remain framework-owned.
- Fresh install/update and platform projections are covered by
  `cli/tests/test_scaffold.py`, `test_fresh_scaffold_vnext.py`,
  `test_install_*`, `test_update.py`, `test_snapshots.py`, and GitHub Actions.

## Artifact and learning surfaces

- `.maika/config/artifact-authority.yaml` has task/runtime/durable-knowledge
  authorities but no non-canonical generated-analysis authority.
- There is no generated-report schema/path validator and no standalone report
  store.
- Task learning already uses change-local candidates plus the existing
  knowledge recorder/promoter skills. There is no direct `remember`/`memory`
  CLI lane. Project preferences therefore require a separate store and must
  not mutate rules, skills, or long-term snapshots.

## Provider capabilities and verified integration names

- Existing capability IDs include `architecture_discovery`,
  `exact_source_inspection`, and aggregate `dependency_analysis`.
- Maika's manifest configures Understand-Anything as a graph producer and its
  MCP server, and Codebase Memory as a separate `code_exploration` provider.
- The integration currently names only the Codebase Memory operation
  `index_repository` in its install hint. No other concrete CBM tool name is
  verified locally, so provider metadata must stay capability-only for CBM.
- The plan-provided UA-MCP tool list is treated as the available public
  contract; no UA-MCP repository change is justified by this discovery.
- Current provider doctrine makes UA primary for architecture and CBM primary
  for the aggregate dependency capability. It needs precise structured-trace
  capabilities while retaining `dependency_analysis` for compatibility.

## Validation and CI consumers

- Validator style is `load_*` plus `validate_*` under `cli/agent_content`,
  exposed through `maika content ...` and tested under `cli/tests`.
- `scripts/run_ci.py` runs the CLI, gate, orchestrator, write-gate,
  knowledge-index, and rule-projector test columns. `.github/workflows/ci.yml`
  provides Linux/Windows and install coverage.
- New registries will have mechanical consumers through CLI validation, CI,
  scaffold installation, and runtime/skill lookup where behavior requires it.

## Implementation decisions and plan corrections

1. Keep `workflow-router.yaml` task-only; add a separate deterministic
   interaction registry with no default-to-task route.
2. Preserve provider ownership: declare native commands and effects, but do not
   build a slash executor or generic workflow runner.
3. Make reports/preferences project-owned; keep their contracts and validators
   framework-owned.
4. Implement report schema validation as validation of report documents/paths,
   not merely a dead schema file.
5. Implement `memory promote` as an explicit status/target record only. It must
   not write core rules or canonical knowledge automatically.
6. Add worker request validation and prompt contract, but block/remediate rather
   than pretend Maika can execute host-native slash commands.
7. Operation records remain deferred: direct provider workflows are not
   observable by the current runtime, and optional unconsumed audit metadata
   would violate the no-dead-declaration rule.
