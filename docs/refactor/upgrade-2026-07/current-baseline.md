# Upgrade 2026-07 — W0 Baseline Freeze

Wave: **W0 — Baseline freeze and ownership audit**
Date: 2026-07-11
Branch: `master-v2` — baseline commit `1b15599 feat: complete Maika adaptive workflow remediation`
Governing plan: `docs/superpowers/plans/2026-07-11-upgrade-remaining-claude-handoff-plan.md`
Source plans: `upgrade/maika-adaptive-loops-upgrade-plan-v2.md`, `upgrade/maika-multi-framework-upgrade-plan.md`

## Purpose

Make the already-implemented P0 vertical slice (currently an uncommitted working-tree
change set on top of `1b15599`) explicit and protected against accidental rollback, and
confirm its five baseline behaviors are pinned by tests before any later wave begins.
**No architecture changes are made in W0.**

## Baseline verification

Umbrella CI reproduces the handoff-plan §2 baseline exactly:

```text
/usr/bin/python3 scripts/run_ci.py
368 + 161 + 104 + 81 + 5 + 13 + 53 = 785 passed, 1 skipped
```

> Environment note: `python3` on this host is the project `.venv` and has no `pytest`;
> `/usr/bin/python3` (pytest 9.1.0) is the interpreter that carries the test deps.
> `scripts/run_ci.py` uses `sys.executable`, so it is invoked as
> `/usr/bin/python3 scripts/run_ci.py`. This is an interpreter-selection detail only —
> the test surfaces and counts are unchanged.

Focused W0 exit-gate suite:

```text
/usr/bin/python3 -m pytest cli/tests/test_init.py cli/tests/test_scaffold.py \
  cli/tests/test_platforms.py \
  .maika/tools/microloop-orchestrator/tests/test_adaptive_runtime.py -q
136 passed, 1 skipped   # 134 + the 2 W0 coverage tests added below
```

`git diff --check` is clean (no whitespace/conflict errors).

## Changed-file inventory and ownership classification

Ownership vocabulary follows the multi-framework plan §3.2. `.maika/rules|workflows|
skills|procedures|tools|hooks` are **framework-owned** (replaceable by manifest/version);
`.maika/knowledge|changes|archive|loops|config/project.local.yaml` are **project-owned**
(never overwritten); `AGENTS.md`, `CLAUDE.md`, `.claude/settings.json`, `.codex/hooks.json`,
`.agents/hooks.json` are **shared host-owned** (Maika manages only its namespaced block/entry).
The `cli/` package is the **framework CLI source** that renders and installs those assets.

### Modified — framework CLI source (`cli/`, product)

| Path | Δ | Role in the slice |
|---|---|---|
| `cli/scaffold.py` | +76/− | Managed-Markdown block merge, structural JSON merge, canonical `.maika` config write + legacy-root read candidates |
| `cli/commands/init.py` | +5 | Init drives staged managed-Markdown/JSON merge |
| `cli/commands/update.py` | +27/− | Update re-runs merge; canonical `.maika` writes |
| `cli/platforms/antigravity.py` | +3/− | `framework_root = .maika` |
| `cli/platforms/claude_code.py` | +3/− | `framework_root = .maika` |
| `cli/platforms/codex.py` | +5/− | `framework_root = .maika` |
| `cli/mcp/adapters.py` | +6/− | `.maika`-relative MCP wiring |
| `cli/mcp/doctor.py` | +4/− | Report writes → `.maika`, reads legacy roots |
| `cli/plugin-manifest.yaml` | +4/− | Manifest paths |

### Modified — framework runtime tool code (`.maika/tools/…`)

| Path | Δ | Role |
|---|---|---|
| `.maika/tools/microloop-orchestrator/adaptive_runtime.py` | +36 | `classify_workflow_requirements()` — task-class workflow matrix |
| `.maika/tools/microloop-orchestrator/vnext_state.py` | +7/− | `init_workspace()` persists `workflow` in `CHANGE.yaml` + lightweight `TASK.yaml` |

### Modified — framework workflow asset

| Path | Δ | Role |
|---|---|---|
| `.maika/workflows/task.md` | +26/− | Task workflow copy aligned to adaptive matrix |

### Modified — tests and snapshots (framework-dev)

`cli/tests/test_init.py` (+86), `cli/tests/test_scaffold.py` (+77, **incl. W0 additions**),
`cli/tests/test_platforms.py` (+7), `cli/tests/test_update.py` (+15),
`cli/tests/test_mcp_doctor.py` (+14), `cli/tests/test_hook_os_rendering.py` (+18),
`cli/tests/test_hook_python_persistence.py` (+2), `cli/tests/test_mcp_adapters.py` (+6),
`cli/tests/test_dashboard_brain.py` (+6), `cli/tests/test_snapshots.py` (+6),
`.maika/tools/microloop-orchestrator/tests/test_adaptive_runtime.py` (+29, **incl. W0 addition**);
snapshot fixtures `cli/tests/snapshots/{antigravity,claude-code,codex}.txt` (rewritten to
`.maika` layout).

### Deleted — pre-existing, PROTECTED (not part of this or any wave)

- `MAIKA_KNOWLEDGE_NATIVE_REASONING_REFACTOR.md`
- `MAIKA_VNEXT_MASTER_REFACTOR_PLAN.md`
- `MaikaAdaptiveWorkflow.md`

Do not restore, delete, move, or rewrite these unless the user explicitly requests it.

### Untracked — new, PRESERVE

- `docs/architecture/adaptive-loops-and-loop-engineer.md`, `docs/architecture/project-core-and-host-adapters.md` — ADRs from the P0 slice.
- `docs/superpowers/plans/2026-07-11-upgrade-remaining-claude-handoff-plan.md` — this handoff plan.
- `upgrade/maika-adaptive-loops-upgrade-plan-v2.md`, `upgrade/maika-multi-framework-upgrade-plan.md` — source plans (PROTECTED).
- `docs/refactor/upgrade-2026-07/current-baseline.md` — this document (the sole W0 addition outside the two test files).

## Baseline behaviors confirmed by tests

| # | Behavior | Status | Evidence |
|---|---|---|---|
| 1 | Managed Markdown replacement is idempotent; content outside the block is preserved | COVERED | `cli/tests/test_init.py:410` `test_reinit_replaces_managed_entrypoint_block_without_duplication` (exactly one begin/end pair after re-init); `cli/tests/test_init.py:393` `test_init_preserves_existing_entrypoint_outside_managed_block` |
| 1b | Malformed managed Markdown block fails **before** target mutation (fail-closed) | COVERED (W0-added) | `cli/tests/test_scaffold.py` `test_merge_managed_markdown_rejects_duplicate_blocks`, `test_managed_markdown_malformed_block_fails_before_target_mutation` — asserts `ValueError` from `cli/scaffold.py:47` and target file left byte-identical |
| 2 | JSON merge preserves unrelated keys/hooks and replaces the prior Maika hook (single entry) | COVERED | `cli/tests/test_scaffold.py:26` `test_managed_json_merge_preserves_host_config_and_replaces_maika_hook` — preserves `permissions` + `team-check`, replaces old `.maika/…/old.py` with the new write-gate entry (exactly one Maika entry). Impl `merge_managed_json` `cli/scaffold.py:78`, Maika-entry identity `_is_maika_json` `cli/scaffold.py:73` |
| 3 | Legacy resolved config remains readable | COVERED | `cli/tests/test_scaffold.py:279` `test_load_resolved_config_reads_agents_config`; `cli/tests/test_status.py:6` `test_status_reads_skills_from_agents_root`; candidate set incl. `.agents`/`.claude` at `cli/scaffold.py:148` |
| 3b | New state/report/config writes target `.maika` | COVERED | `cli/tests/test_snapshots.py:89-91` (`.maika/resolved-config.yaml` present, `.agents`/`.claude` absent); `cli/tests/test_init.py:283-286`; `cli/tests/test_mcp_doctor.py:53,96` (report → `.maika/knowledge/active/…`); all adapters `framework_root == ".maika"` (`cli/tests/test_platforms.py:16`) |
| 4 | Small workspace persists the workflow contract in both `TASK.yaml` and `CHANGE.yaml` | COVERED (CHANGE.yaml W0-added) | `.maika/tools/microloop-orchestrator/tests/test_adaptive_runtime.py:70` `test_workspace_persists_consumable_workflow_contract` — now asserts `TASK.yaml["workflow"]` **and** `CHANGE.yaml["workflow"]` equal `classify_workflow_requirements("small")`. Impl `vnext_state.py:111-117,125` |
| 5 | Small/trivial task creates no full `SPEC.md` / `IMPLEMENTATION_PLAN.md` | COVERED | `.maika/tools/microloop-orchestrator/tests/test_adaptive_runtime.py:120` `test_class_specific_workspace_artifacts` — asserts absence of `SPEC.md`/`IMPLEMENTATION_PLAN.md` for small (`:131-132`) and `SPEC.md` for trivial (`:123`) |

## W0 coverage additions (the only test changes in this wave)

Two genuine gaps were found and filled; both pin behavior that already exists in the
slice, so both passed on first run (no implementation change).

1. **Markdown fail-before-mutation** (behavior 1b) — the `ValueError` guard at
   `cli/scaffold.py:46-47` had no test. Added two tests to `cli/tests/test_scaffold.py`
   covering both malformed conditions (duplicate block, and begin-without-end), the
   second asserting the host target is byte-identical after the error.
2. **`CHANGE.yaml` workflow contract** (behavior 4) — the persisted contract was asserted
   only for `TASK.yaml`. Extended `test_workspace_persists_consumable_workflow_contract`
   to also assert the `CHANGE.yaml` `workflow` block.

Behaviors 2, 3, 3b, and 5 already had adequate coverage; per the handoff plan ("update
only if missing coverage") and DEVELOPMENT_RULES R7 (net-negative/neutral complexity),
no further tests were added.
