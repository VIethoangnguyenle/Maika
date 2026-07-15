# Maika Framework Ecosystem — Pilot Readiness Baseline

Date: 2026-07-15<br>
Branch: `master-v2`<br>
Decision: **CONDITIONAL PILOT**<br>
Production ready: **NO**

## Maika-owned controls implemented

- Provider fixtures pin audited revision and content hash.
- Unresolved scoped writes fail closed; workspace lock has owner fencing and heartbeat.
- Worker writes use a canonical execution lease; lightweight verification emits required
  zero-impact knowledge artifacts without overwriting worker output.
- UA metadata and CBM semantic routing are normalized against tested tool surfaces.
- Provider mutability lanes keep CBM mutation/deletion, AgentMemory writes/destruction,
  and DB write/script out of exploration.
- External observations use evidence envelope v1. Graph conflicts require current-source
  verification. AgentMemory recall is historical/candidate-only.
- CBM evidence completeness requires stable pre/post `index_status` boundaries.
- Doctor reports AgentMemory auto-capture as a governance conflict without mutating host files.

## Degraded or unverified properties

- Understand-Anything fixture does not expose a provider runtime version or working-tree state.
- Codebase Memory does not expose an immutable `index_generation`; Maika records it as
  `unverified` and uses boundary comparison only as change detection, not snapshot isolation.
- AgentMemory proxy fixture does not prove server/store identity; cross-session canonical use
  remains disabled.
- Db-Access upstream authorization/write-safety findings remain owned by its external plan;
  pilot use requires a dedicated read-only principal and schema/read tools only.
- Windows hook/filesystem acceptance remains a CI responsibility; this local baseline is Linux.

## Allowed pilot scope

- Current-source inspection.
- UA and CBM read-only discovery.
- AgentMemory recall as candidate context only.
- Db-Access schema/read tools using a dedicated read-only principal.

## Disabled pilot scope

- Source writes outside an active scoped execution lease.
- CBM index mutation, ADR ingestion, trace ingestion, or project deletion during exploration.
- AgentMemory auto-capture, implicit save, canonical persistence, maintenance, or deletion.
- Db-Access write and script tools.

The baseline must not be relabeled production-ready until mandatory upstream identities,
snapshot properties, external safety contracts, Linux CI, and Windows acceptance all pass.
