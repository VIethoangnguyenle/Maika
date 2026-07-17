# Serena provider guide

This is the authoritative install and operations guide for Maika's optional
Serena provider on Codex, Claude Code, and Antigravity. Phase 1 supplies
read-only, LSP-backed symbols, references, declarations, implementations, and
diagnostics over the current project. It does not give Serena workflow,
knowledge, verification, or write authority.

Maika generates `.maika/MCP_SETUP.md` and the fixed context at
`.maika/config/serena-context.yml`. Maika does not automatically mutate native workspace or global MCP configs.
Copy the generated workspace entry into the host-owned file named below; never
run `serena setup <host>` for a Maika-managed project.

## Provider authority and non-goals

| Need | Primary authority | Supporting use and limit |
|---|---|---|
| Project identity, graph freshness, architecture, domain, relationships, call trace, impact, paths, inheritance, entry points, node source | UA-MCP | Current source verifies exact facts; Serena does not replace structured graph/domain traversal. |
| Exact symbol identity, declaration, implementation, LSP references, diagnostics | Serena | Scoped semantic evidence only; verify material claims against current source and current tests. |
| Fuzzy semantic anchor search | CBM | Conditional support for vocabulary mismatch, graph gaps/staleness, reviewer counter-evidence, or hidden-consumer risk; record the activation reason. |
| Historical/session recall | AgentMemory | Historical candidate evidence only, never current-code authority. |
| Exact current behavior | current source and current tests | Provider output is navigation/evidence; observed source/runtime/test evidence wins conflicts. |

UA-MCP retains its full role and all 18 tools:

- Project/freshness: `list_projects`, `get_graph_stats`, `get_graph_metadata`.
- Node/architecture discovery: `get_tour`, `query_nodes`, `get_node_detail`,
  `get_layer_info`, `find_entry_points`, `search_by_file_path`.
- Relationships/traversal: `get_relationships`, `trace_call_chain`,
  `find_impact`, `find_path`, `get_class_hierarchy`.
- Domain graph: `get_domain_overview`, `get_domain_detail`,
  `get_domain_flow_detail`.
- Known-node source resolution: `get_node_source`.

`get_node_source` is one of 18 tools, not UA-MCP's entire role. No static
provider guarantees hidden consumers: static graphs and LSP references cannot
prove the absence of reflective, configured, generated, or event-driven
consumers.

Maika's Serena context exposes exactly these eight tools:

- `get_symbols_overview`
- `find_symbol`
- `find_referencing_symbols`
- `find_implementations`
- `find_declaration`
- `get_diagnostics_for_file`
- `get_diagnostics_for_symbol`
- `restart_language_server`

The context excludes Serena memory, onboarding, shell, basic file browsing, and
write tools. `restart_language_server` is operational recovery, not evidence
that a code claim is correct.

## Prerequisites

- `uv` on `PATH`.
- Serena's stable Python range `>=3.11,<3.15`. Maika's reproducible install
  command selects Python 3.13 and pins `serena-agent==1.5.3` exactly.
- One Maika language selection: `java`, `typescript`, `python`, `go`, `csharp`,
  or `other`.
- The project's normal language toolchain and dependencies must work before the
  LSP can give useful results: a compatible JDK/build for Java, Node.js and
  installed project packages for TypeScript, the intended virtual environment
  and packages for Python, the Go toolchain/modules for Go, or the .NET SDK and
  restored project for C#. Serena chooses and starts the language backend; some
  backends may download components. Review that package/network trust boundary
  and use a sandbox for an untrusted repository.

Install the pinned engine on Linux, macOS, or PowerShell:

```sh
uv tool install --python 3.13 'serena-agent==1.5.3'
serena --version
```

## Select Serena in Maika

For a new project, select `serena` in the interactive MCP prompt, or run a
non-interactive command such as:

```sh
maika init --target /absolute/project/path --platform codex --mcp serena --language python --yes
```

Use `--platform claude-code` or `--platform antigravity` for the other supported
hosts. Repeat `--mcp` to keep other providers. For an existing Maika project:

```sh
maika update --target /absolute/project/path --reconfigure
```

Choose Serena while reconfiguring. Maika records the selection, renders the
Maika-owned context `.maika/config/serena-context.yml`, and regenerates
`.maika/MCP_SETUP.md`; you still apply the workspace MCP entry yourself.

## Create the Serena project

Run the command matching the Maika language selection. The path must be the
absolute project root.

```sh
# java
serena project create /absolute/project/path --language java

# typescript
serena project create /absolute/project/path --language typescript

# python
serena project create /absolute/project/path --language python

# go
serena project create /absolute/project/path --language go

# csharp
serena project create /absolute/project/path --language csharp

# other: omit the language flag and let Serena infer
serena project create /absolute/project/path
```

For `other`, inspect `/absolute/project/path/.serena/project.yml` after inference
and correct its language list before continuing if it does not match the repo.
Do not request a separate index build: the language server initializes when the
project is activated.

## Workspace MCP configuration

The following blocks are the exact output for `/absolute/project/path`. Keep
the project and context paths fixed to the same absolute workspace.

### Codex

Paste into the workspace file `.codex/config.toml`:

```toml
[mcp_servers.serena]
command = "serena"
args = ["start-mcp-server", "--project", "/absolute/project/path", "--context", "/absolute/project/path/.maika/config/serena-context.yml", "--mode", "no-memories", "--enable-web-dashboard", "false", "--open-web-dashboard", "false"]
```

### Claude Code

Paste/merge into the workspace file `.mcp.json`:

```json
{
  "mcpServers": {
    "serena": {
      "command": "serena",
      "args": [
        "start-mcp-server",
        "--project",
        "/absolute/project/path",
        "--context",
        "/absolute/project/path/.maika/config/serena-context.yml",
        "--mode",
        "no-memories",
        "--enable-web-dashboard",
        "false",
        "--open-web-dashboard",
        "false"
      ]
    }
  }
}
```

### Antigravity

Paste/merge into the workspace file `.agents/mcp_config.json`:

```json
{
  "mcpServers": {
    "serena": {
      "command": "serena",
      "args": [
        "start-mcp-server",
        "--project",
        "/absolute/project/path",
        "--context",
        "/absolute/project/path/.maika/config/serena-context.yml",
        "--mode",
        "no-memories",
        "--enable-web-dashboard",
        "false",
        "--open-web-dashboard",
        "false"
      ]
    }
  }
}
```

These are workspace examples. Maika's doctor may also discover documented
user-level host locations, but Maika does not edit those global files.

## Verify and smoke test

First inspect the pinned installation's upstream inventory, then probe the real
Maika context through doctor:

```sh
serena tools list --all --quiet
maika doctor mcp --target /absolute/project/path
```

The first command is an upstream inventory and can show tools outside Maika's
context. The doctor checks every enabled host, verifies Serena `1.5.3`, validates
that the activated `.serena/project.yml` backend matches Maika's selected language,
performs a real `tools/list`, checks the pinned schema hash, and chooses the first
deterministic project source file with the matching language extension. The symbol
smoke, optional single `restart_language_server`, and one retry share one bounded
MCP session; the process is then cleaned up. The doctor writes a redacted report to
`.maika/knowledge/active/mcp-doctor-report.md`. Healthy Serena includes:

```text
engine: ✓ installed
wired: ✓ configured
version: READY (Serena 1.5.3)
project: READY (python backend; smoke file: src/example.py)
contract: READY (8 Phase 1 tools; sha256:<pinned-contract-hash>)
symbol smoke: READY
```

Restart the host after changing its workspace config. In the host's MCP tool
UI, make these read-only smoke calls using paths/names that exist in the repo:

```text
find_symbol({"name_path_pattern":"KnownClass/known_method","relative_path":"src/example.py"})
find_referencing_symbols({"name_path":"KnownClass/known_method","relative_path":"src/example.py"})
get_diagnostics_for_file({"relative_path":"src/example.py"})
```

A useful smoke result identifies the expected symbol, returns known references
(or an explainable empty result), and returns diagnostics without startup/LSP
errors. These observations do not replace build, lint, or tests.

## Troubleshooting

### binary missing

If doctor says `engine: ✗ not installed`, confirm `uv tool dir --bin` is on the
host's `PATH`, reopen the terminal/host, and rerun the pinned install. Pointing a
host at an unpinned `uvx` command is outside Maika's release contract.

### project config missing

If `.serena/project.yml` is absent, rerun the matching `serena project create`
command. Confirm `--project` names that same absolute root and that
`.maika/config/serena-context.yml` exists.

### language server unavailable

Run the project's own toolchain/build command first, install/restore its normal
dependencies, and inspect Serena startup output for the backend failure. Check
that `.serena/project.yml` selected the intended language. Treat the provider as
degraded until the smoke call works.

### empty symbols

Confirm the requested file is inside the project, is not excluded by
`.serena/project.yml`, and uses the selected language. Try
`get_symbols_overview` on one small known source file before widening the query.
An empty result is not proof that the symbol or consumer does not exist.

### stale LSP

After dependency, branch, or generated-source changes, invoke
`restart_language_server` once and repeat the smoke call. If it remains stale,
restart the host/Serena process and verify current source directly; do not loop
unbounded restarts.

This call belongs to Maika's operational-maintenance lane. It is not diagnostics,
does not normalize as semantic-symbol evidence, and cannot satisfy evidence coverage.

### unexpected/write tools

If doctor reports missing, unexpected, forbidden, or schema-drifted tools, stop
using Serena for Phase 1 evidence. Confirm the exact package pin and the exact
Maika context path. Do not approve a write tool merely because upstream lists
it; restore the pinned setup and rerun doctor.

### Windows path quoting

In PowerShell, quote paths containing spaces:

```powershell
serena project create "C:\absolute path\project" --language python
maika doctor mcp --target "C:\absolute path\project"
```

In JSON, either escape each backslash (`C:\\absolute path\\project`) or use
forward slashes (`C:/absolute path/project`). Apply the same path consistently
to both `--project` and `--context`; do not include shell quote characters in a
JSON `args` value.

### logs without secrets

Prefer the doctor's redacted report. Before sharing logs, remove environment
values, tokens, headers, private source, usernames, and private absolute paths.
Do not paste the raw native MCP config or unreviewed language-server output into
an issue. The doctor intentionally shows matched config only after redaction.

## Upgrade and fixture recapture

Do not change the pin based only on a successful install. In one change:

1. Change the manifest pin and expected provider version.
2. Run the candidate with the Maika context and recapture real `tools/list` into
   `cli/tests/fixtures/provider_contracts/serena/tools-list-readonly-v1.json`.
3. Update `tools-list-readonly-v1.provenance.yaml` with the real command,
   version/revision, capture time, and raw SHA-256.
4. Recompute `SERENA_READONLY_V1_TOOL_SURFACE_HASH` from the captured schemas.
5. Review every missing, unexpected, or write-capable tool, then run contract,
   platform, doctor, snapshot, and full CLI regression tests:

   ```sh
   python3 -m pytest cli/tests/test_provider_contract_fixtures.py cli/tests/test_platforms.py cli/tests/test_mcp_doctor.py cli/tests/test_serena_documentation.py cli/tests/test_snapshots.py -q
   python3 -m pytest cli/tests -q
   ```

6. Exercise Codex, Claude Code, and Antigravity with a real symbol/reference/
   diagnostic smoke call. Only then update this guide and merge the new pin.

To roll back, restore the previous pin, fixture, provenance, hash, and docs as
one reviewed change; reinstall that exact pin and rerun doctor.

## Phase 2 write gate

Phase 2 symbolic write tools are **not enabled**. The release gate remains
closed pending real native hook event payload evidence for Serena MCP write
calls on all three hosts: Codex, Claude Code, and Antigravity. Before any
registry, context, or platform mapping change, Maika must:

1. capture and characterize each host's real interception payload;
2. extend the existing Maika write gate rather than add a parallel gate;
3. deny out-of-phase, out-of-scope, stale-brief, and pathless symbol writes;
4. run bypass characterization for alternate names, missing paths, partial
   failure, and direct/native MCP invocation;
5. prove diff capture, focused verification, independent review, and safe
   partial-failure behavior end to end on every host.

Instructions alone are not hook evidence. A host without verified interception
must remain read-only.

## Disable or uninstall

1. Run `maika update --target /absolute/project/path --reconfigure` and remove
   `serena` from the selected MCPs while keeping the other desired providers.
2. Let Maika regenerate its owned context/setup state, then manually remove the
   `serena` workspace entry from `.codex/config.toml`, `.mcp.json`, or
   `.agents/mcp_config.json`. Do not remove another project's/global entry.
3. Optionally remove the engine with `uv tool uninstall serena-agent` only when
   no other project uses it.
4. Explicitly choose whether to preserve `.serena` for later reuse or delete `.serena`;
   Maika never assumes that user-owned project state may be deleted.
