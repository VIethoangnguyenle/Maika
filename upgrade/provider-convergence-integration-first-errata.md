# Provider Convergence — Integration-First Errata

Date: 2026-07-13
Status: ACTIVE — overrides conflicting parts of the closure plan and Phase 0 inventory

## Corrected ownership boundary

Maika is the implementation scope. Understand-Anything-MCP, Codebase Memory MCP and
DB Access are external MCP dependencies that may already be installed, configured and
used by other people. Maika owns:

- its connector/provider key;
- the tested tool catalog and argument/result expectations;
- capability-to-tool routing;
- health/tool discovery through the user's configured MCP connection;
- request/evidence artifacts, gates and worker context;
- separation between exploration, data probe and explicit write/script intent.

Maika does not own:

- whether an MCP server runs locally or on another machine;
- endpoint, API key, source, database credentials or SSH-tunnel configuration;
- provider package/bin/container/systemd/environment naming;
- stable behavior of existing provider tools;
- provider release/deployment migration.

## DB Access correction

`db-access` is Maika's MCP client configuration key. It is not a mandate to rename the
provider's internal server, binary, Docker, service or environment surfaces.

DB Access supports two independent connection axes:

```text
Maika/host -> DB Access: local stdio OR remote HTTP/SSE
DB Access -> database: direct OR SSH tunnel
```

The user configures those axes. Maika consumes the configured `db-access` connection
and validates the tools it exposes. The currently observed tool catalog is:

```text
list_databases
sql_list_tables
sql_get_columns
sql_get_constraints
sql_read
sql_write
sql_execute_script
mongo_list_collections
mongo_get_schema
mongo_read
mongo_write
```

DB Access is not a read-only provider. Maika routes it through separate lanes:

- metadata exploration: schema/catalog tools only;
- explicit data probe: read tools only when the question requires data;
- explicit write: `sql_write`/`mongo_write` only on explicit user intent;
- explicit script: `sql_execute_script` only on explicit user intent.

Provider preview/confirmation and source/database authorization remain mandatory. The
Database Explorer skill is read-only; that boundary does not remove DB Access write
capabilities from other explicitly authorized operations.

## UA correction

Existing UA-MCP tools retain their names, return shapes and human-readable behavior.
Structured contract work must be additive. Maika may use new structured operations,
but it must not silently replace the behavior of an existing operation. Graph health
and dirty-worktree metadata may add fields, while legacy callers continue to receive
their prior shape.

## Superseded work

The following original requirements are not executable without a separate provider
owner decision:

- strict DB package/server/bin/container/systemd/environment rename;
- removal of DB transport/tunnel helpers;
- mandatory DB Access permission/schema/session rewrites;
- cross-repository D1-D5 as prerequisites for Maika integration;
- changing existing UA tool return types or FastMCP server identity;
- assuming a local MCP binary in Maika scaffold/setup/doctor.

Provider changes may be proposed separately only for an observed provider defect, with
provider-owner approval and backward-compatibility tests. They are not part of normal
Maika convergence execution.

## Corrected execution order

```text
M1 provider registry + actual tool catalogs
M2 vendor tested external tool snapshots/adapters
M3 typed required/one_of/conditional capability schema
M4 provider-neutral code trace artifacts and gates
M5 persistence triggers, DB request/context and read/write lane routing
M6 Maika-side MCP execution adapters using user-configured connections
M7 pinned worker context
M8 refresh/re-probe lifecycle
M9 system-model validator and mutation suite
M10 deterministic/cross-host qualification and legacy removal
```

Understand-Anything-MCP and DB Access both remain at their audited baselines. All
normalization, compatibility envelopes, health interpretation and evidence shaping are
implemented in Maika-side adapters. External MCP source changes require a separate,
explicit provider-owner request.
