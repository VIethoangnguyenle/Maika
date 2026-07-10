# Agent Memory — MCP-only setup (provider boundary)

> Framework-internal guidance. Maika does **not** bundle, vendor, auto-install, or
> auto-run `agentmemory`. This recipe is for the **end project** that opts into
> the `memory` capability at `maika init`. Source of truth: design spec
> `docs/superpowers/specs/2026-06-21-memory-tool-capability-templating-design.md` §4.

## Why MCP-only (hooks OFF)

`agentmemory connect <agent>` installs **12 auto-capture hooks** that record memory
on every tool use with no gating. That directly conflicts with Maika's memory
governance (R-Tool-6, M7: one save per task, 3 quality filters, no-PII, top-K
recall, source-of-truth priority). Maika must own memory governance, so the end
project wires **only the MCP tool surface** and leaves auto-capture off.

## [CRITICAL] Register the server under the name `agent-memory`

Maika's tool mapping is pinned to the MCP server name **`agent-memory`** (with the
hyphen) — e.g. `{{ tools.dynamic_memory_save }}` resolves to
`mcp__agent-memory__memory_save` on Claude Code (see `cli/platforms/`).

agentmemory's **default** registration name is `agentmemory` (no hyphen), so
`agentmemory connect` / the npx default produce tools like
`mcp__agentmemory__memory_save` — which will **NOT** match Maika's references, and
memory calls fail with "tool not found" (this is a wiring error, not the clean
R-Tool-6 degrade). You MUST register the server as exactly `agent-memory`.
Use the manual `mcpServers` block below (it controls the name) — do not rely on
the provider's default name.

## Setup (đã xác minh với upstream 2026-07-05)

1. Cài và chạy backend daemon (user tự vận hành — Maika không cài/chạy hộ):

   ```
   npm install -g @agentmemory/agentmemory
   agentmemory          # REST API :3111, viewer :3113
   ```

   Chẩn đoán sâu: `agentmemory doctor`. Dừng: `agentmemory stop`.

2. Register the MCP server manually — JSON key MUST be `agent-memory`:

   ```json
   {
     "mcpServers": {
       "agent-memory": {
         "command": "npx",
         "args": ["-y", "@agentmemory/mcp"],
         "env": { "AGENTMEMORY_URL": "http://localhost:3111" }
       }
     }
   }
   ```

## [WARNING] Shim fallback — tool trả lời KHÔNG có nghĩa daemon sống

`@agentmemory/mcp` fallback về 7 core tools cục bộ khi không kết nối được daemon —
tool vẫn xuất hiện trong tool list nhưng không có persistence thật. Kiểm tra thật:
`maika doctor mcp` (probe HTTP tới `AGENTMEMORY_URL`) hoặc `agentmemory doctor`.
Bootstrap probe chỉ được ghi `agent-memory: healthy` khi backend thật trả lời
(xem `procedures/bootstrap.md` PHASE 5).

## Do NOT

- Do **not** run `agentmemory connect --with-hooks` (installs the 12 auto-capture hooks).
- Do **not** install agentmemory's bundled skills (they overlap Maika's canonical
  knowledge lifecycle).
- Do **not** commit `~/.agentmemory/` state into the repo (it is user-machine-scoped).

## Result

Maika's `dynamic_memory_*` abstract ops resolve to this server's tools
(`mcp__agent-memory__memory_*` on Claude Code). When `agent-memory` is not selected
at init, all recall/save are skipped per R-Tool-6 degrade and M7 Tầng 0 — Maika
still works on repo-based knowledge alone.
