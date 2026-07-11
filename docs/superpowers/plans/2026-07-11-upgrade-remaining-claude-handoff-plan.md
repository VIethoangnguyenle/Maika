# Maika Upgrade Remaining Work — Claude Handoff Plan

Date: 2026-07-11
Owner after handoff: Claude
Source plans:

- `upgrade/maika-adaptive-loops-upgrade-plan-v2.md`
- `upgrade/maika-multi-framework-upgrade-plan.md`

## 1. Objective

Continue the two upgrade tracks from the already implemented P0 vertical slice:

1. turn the canonical `.maika` project core into a self-contained, transactional,
   diagnosable multi-host installation; and
2. add the change-level Loop Engineer without weakening the existing write gate,
   verification, knowledge, or approval boundaries.

Do not attempt all waves in one diff. Complete, verify, and hand off each wave
independently.

## 2. Current baseline — do not redo

The working tree already contains an uncommitted vertical slice with these behaviors:

- `classify_workflow_requirements()` owns the task-class workflow matrix.
- `init_workspace()` persists `workflow` in `CHANGE.yaml` and lightweight `TASK.yaml`.
- all platform adapters use `.maika` as `framework_root`.
- `.agents` and `.claude` resolved configs remain readable as legacy inputs.
- new diagnostics/state writes target `.maika`.
- `AGENTS.md` and `CLAUDE.md` use a Maika managed block.
- Claude/Codex/Antigravity JSON hook files use structural merge.
- host hook config remains host-native while hook code lives under `.maika`.
- architecture decisions are recorded in:
  - `docs/architecture/adaptive-loops-and-loop-engineer.md`
  - `docs/architecture/project-core-and-host-adapters.md`

Baseline verification already passed:

```text
python3 scripts/run_ci.py
785 passed, 1 skipped
```

There are three pre-existing deleted root documents and untracked `upgrade/` files.
Do not restore, delete, move, or rewrite them unless the user explicitly requests it:

```text
MAIKA_KNOWLEDGE_NATIVE_REASONING_REFACTOR.md
MAIKA_VNEXT_MASTER_REFACTOR_PLAN.md
MaikaAdaptiveWorkflow.md
upgrade/
```

Before every wave:

```bash
git status --short
git diff --check
python3 scripts/run_ci.py
```

If baseline behavior differs from this section, stop and report the mismatch.

## 3. Global implementation rules

- Follow `.maika/DEVELOPMENT_RULES.md` R1–R7.
- Every field/config/capability added in a wave needs a mechanical consumer in the
  same wave.
- Extend existing gates and state services; do not create a parallel task runtime.
- Preserve user-owned knowledge and all unrelated dirty-worktree changes.
- Tests must fail for the intended reason before implementation.
- No shell-string worker execution; build argv lists and use `shell=False`.
- No dangerous permission flag may be selected by default.
- No agent may approve its own shared-skill, public-contract, security, or migration
  decision.
- Add an enforcement-ledger entry only with a reproducible litmus or another valid
  R3 evidence classification.
- Run `python3 scripts/run_ci.py` at every wave exit.

## 4. Wave order

```text
W0 Baseline freeze
 → W1 Self-contained package assets
 → W2 Transactional install/update
 → W3 Canonical config + multi-host adapters
 → W4 Detection, verified capabilities, worker strategy
 → W5 Stable hook CLI + setup doctor
 → W6 Change-level Loop Engineer
 → W7 Approval/resume governance
 → W8 Macro learning evaluation
 → W9 Migration, repair, uninstall, rollout docs
```

W1–W5 complete the multi-framework P0/P1 track. W6–W8 complete adaptive-loop
P1/P2. W9 closes lifecycle and rollout gaps.

---

## W0 — Baseline freeze and ownership audit

### Goal

Make the current vertical slice explicit and protect it against accidental rollback.

### Files

- Review only: current modified files from `git status --short`.
- Add: `docs/refactor/upgrade-2026-07/current-baseline.md`.
- Update only if missing coverage: `cli/tests/test_init.py`,
  `cli/tests/test_scaffold.py`, `cli/tests/test_platforms.py`,
  `.maika/tools/microloop-orchestrator/tests/test_adaptive_runtime.py`.

### Tasks

1. Record the current changed-file inventory and ownership classification.
2. Confirm managed Markdown replacement is idempotent and malformed blocks fail
   before target mutation.
3. Confirm JSON merge preserves unrelated keys/hooks and replaces prior Maika hook.
4. Confirm legacy resolved config is readable while new state/report writes go to
   `.maika`.
5. Confirm small workspace persists the workflow contract and no full spec/plan.

### Exit gate

```bash
python3 -m pytest \
  cli/tests/test_init.py \
  cli/tests/test_scaffold.py \
  cli/tests/test_platforms.py \
  .maika/tools/microloop-orchestrator/tests/test_adaptive_runtime.py -q
python3 scripts/run_ci.py
git diff --check
```

Do not change architecture in W0.

---

## W1 — Self-contained package assets

### Goal

`pipx`, `uvx`, and wheel installs must initialize a clean project without a Maika
source checkout.

### Primary files

- Add `cli/assets.py`.
- Add the minimum setuptools build support needed to place canonical assets in the
  wheel without maintaining a second handwritten asset tree.
- Update `pyproject.toml`.
- Update `cli/commands/init.py`, `cli/commands/update.py`.
- Add `cli/tests/test_assets.py`, `cli/tests/test_wheel_install.py`.

### Required API

```python
def asset_root(explicit_source: str | None = None) -> Path: ...
def load_asset_manifest(root: Path | None = None) -> dict: ...
def validate_asset_bundle(root: Path) -> list[str]: ...
```

Resolution order:

1. explicit `--source` for framework development;
2. installed package asset location;
3. source-tree fallback only when running from a checkout.

Never silently select an incomplete bundle. Validation must require the manifest,
rules, skills, workflows, procedures, profiles, tools, hooks, and knowledge templates
actually consumed by scaffold.

### Test-first tasks

1. Build a wheel into a temporary directory.
2. Install it into a clean temporary venv.
3. Rename or hide the source checkout from the subprocess.
4. Run:

   ```bash
   maika init --target <empty-project> --platform codex --language python --yes
   ```

5. Assert `.maika`, `AGENTS.md`, host hook config, and resolved config exist.
6. Assert a deliberately incomplete bundle fails with a list of missing assets.
7. Keep `--source` tests for local framework development.

### Exit gate

- Wheel contents contain every consumed runtime asset and no framework-only tests,
  caches, or local knowledge state.
- Init succeeds with the checkout unavailable.
- Source and wheel scaffold snapshots are equivalent.

---

## W2 — Transactional init and update

### Goal

Any init/update failure restores the exact pre-operation target state.

### Add

```text
cli/install/__init__.py
cli/install/planner.py
cli/install/transaction.py
cli/install/backup.py
cli/install/ownership.py
cli/tests/test_install_planner.py
cli/tests/test_install_transaction.py
```

### Contract

Planner output must be data, not side effects:

```yaml
version: 1
operation: init | update
actions:
  - kind: create | replace | managed_markdown | merge_json | delete_framework_file
    path: <repo-relative path>
    ownership: framework | project | shared-host
```

Transaction requirements:

- preflight validates every source and destination before first target write;
- backup only paths that will change;
- writes use same-directory temporary files plus `os.replace`;
- journal records applied actions;
- rollback runs in reverse order;
- project-owned paths are never replacement targets;
- dry-run returns the same action plan without mutation.

### Refactor

- `run_init()` and `run_update()` must call one planner and one transaction engine.
- Existing `sync_tree()` may remain as a low-level helper only if the transaction
  engine is its sole mutating caller.
- Managed Markdown/JSON merge remains precomputed before apply.

### Failure litmus tests

- injected failure after action 1, middle action, and final action;
- existing AGENTS/CLAUDE content byte-identical after rollback;
- existing JSON config byte-identical after rollback;
- new directories removed when rollback leaves them empty;
- user knowledge unchanged;
- dry-run creates no files.

### Exit gate

Init/update mutation paths are transactional and tests compare a recursive hash of
the target before and after injected failure.

---

## W3 — Canonical config and real multi-host adapters

### Goal

Enable several host adapters over one `.maika` core without re-rendering or
duplicating project knowledge.

### Add

```text
cli/config/__init__.py
cli/config/project.py
cli/config/platforms.py
cli/commands/platform.py
cli/tests/test_project_config.py
cli/tests/test_platform_command.py
```

### Canonical config

Create and consume:

```text
.maika/config/project.y aml
.maika/config/platforms.yaml
.maika/config/install-manifest.yaml
```

Minimum consumed schema:

```yaml
version: 1
framework:
  core_root: .maika
platforms:
  enabled: [codex, claude-code]
  primary: codex
```

Do not add provider/capability fields in W3 unless a W3 command reads them.

### Commands

```text
maika platform list
maika platform enable <platform>
maika platform disable <platform>
maika platform primary <platform>
```

### Behavior

- Core assets render once into `.maika`.
- Each enabled adapter installs only its entrypoint/native config.
- Shared `AGENTS.md` contains one Maika block even when Codex and Antigravity are
  both enabled.
- Disabling a host removes only Maika-managed adapter entries; it keeps core and
  user host config.
- The legacy `resolved-config.yaml` reader becomes compatibility-only; new runtime
  reads canonical config first.

### Tests

- enable Codex + Claude in either order;
- switch primary without knowledge changes;
- disable one host while the other remains healthy;
- two enables are idempotent;
- project knowledge recursive hash remains unchanged through all operations.

---

## W4 — Platform detection, verified capabilities, worker strategy

### Goal

Separate advertised, detected, and verified host capabilities and choose a safe
worker execution strategy.

### Extend

- `cli/platforms/base.py`
- `cli/platforms/antigravity.py`
- `cli/platforms/claude_code.py`
- `cli/platforms/codex.py`
- `cli/capability_runtime.py`
- `.maika/profiles/capability-registry.yaml`

### Add

```text
cli/platforms/detection.py
cli/workers.py
cli/tests/test_platform_detection.py
cli/tests/test_worker_strategy.py
```

### Required data model

```yaml
capability:
  state: advertised | detected | verified | unavailable
  evidence: [<probe record>]
  checked_at: <timestamp>
```

Only declare fields that status/doctor/dispatch consumes in this wave.

### Detection rules

- use `shutil.which` for binaries;
- version probe uses argv + `shell=False` + timeout;
- auth probe only when non-destructive and documented;
- detection must not claim hook or worker verification;
- verification requires a successful smoke path.

### Worker strategies

```text
native_subagent
fresh_process
inline
disabled
```

Selection order is capability-driven and explainable. Fresh process commands are
structured argv. Dangerous bypass/permission flags require explicit user config and
must never appear in defaults or snapshots.

### Tests

- binary missing/version unsupported/auth unknown;
- advertised does not imply detected;
- detected does not imply verified;
- safe fallback to inline;
- argv preserves spaces and metacharacters without shell interpretation;
- no dangerous default scan.

---

## W5 — Stable hook CLI and full setup doctor

### Goal

Host hooks invoke stable `maika hook ...` commands, and setup health reports the
whole adapter installation.

### Add/extend

```text
cli/commands/hook.py
cli/commands/doctor.py
cli/maika.py
cli/tests/test_hook_command.py
cli/tests/test_setup_doctor.py
```

### Commands

```text
maika hook write-gate --runtime <runtime>
maika doctor setup --target <project> [--json]
```

`maika hook write-gate` must locate the project root, load canonical config, and call
the existing `.maika/hooks/write-gate/write_gate.py` evaluator. Do not duplicate
write-gate policy.

Doctor checks:

- canonical core and version;
- managed entrypoint integrity;
- native JSON hook integration;
- enabled host binaries and versions;
- worker strategy smoke status;
- package asset completeness;
- legacy root conflicts;
- MCP/provider health already exposed by existing doctor code.

Update hook templates only after CLI tests pass. Keep graceful diagnostics when the
`maika` executable is absent.

### Exit gate

Rendered Linux and Windows hook tests invoke the stable CLI entrypoint and all setup
findings have machine-readable IDs/severity/evidence/remediation.

---

## W6 — Change-level Loop Engineer

### Goal

Open one change loop only after observed friction exceeds the micro-retry boundary.

### Add

```text
.maika/tools/microloop-orchestrator/loop_policy.py
.maika/tools/microloop-orchestrator/loop_state.py
.maika/tools/microloop-orchestrator/loop_router.py
.maika/tools/microloop-orchestrator/loop_engineer.py
.maika/tools/microloop-orchestrator/tests/test_loop_policy.py
.maika/tools/microloop-orchestrator/tests/test_loop_state.py
.maika/tools/microloop-orchestrator/tests/test_loop_engineer.py
```

Do not add `loop_artifacts.py` or `loop_metrics.py` until duplication is demonstrated;
start with the minimum functions in the four modules above.

### First supported triggers

Only implement triggers with tests and current runtime evidence:

- repeated verification failure after `max_micro_retries`;
- scope escape from `inspect_lightweight_changes()`;
- stale/invalidated execution contract;
- explicit human correction signal from an existing review/result artifact.

First local test failure remains a micro loop and must not create `LOOP.yaml`.

### Artifact

One active change loop uses:

```text
<workspace>/LOOP.yaml
```

Minimum schema:

```yaml
version: 1
loop_id: LOOP-<change>-001
change_id: <id>
level: change
state: diagnosing
trigger:
  type: repeated_failure | scope_escape | stale_contract | human_correction
  evidence_refs: []
root_cause: null
route: null
retry_budget:
  used: 0
  maximum: 2
```

Every field needs a state/router/CLI consumer in W6.

### Integration

- `vnext_state.py`: one optional `active_loop_id`, block/resume APIs.
- `orchestrator.py`: call observe hooks after worker/review/verification failure.
- `adaptive_runtime.py`: remain workflow classifier owner; do not move its policy.
- `runtime_hardening.py`: reuse workspace lock and trusted artifact validation.

### Routing

Root cause must cite evidence and route to exactly one existing specialist role:

```text
spec_gap → spec_writer
plan_gap → planner
implementation_gap → implementer
verification_gap → verification specialist/current verifier
knowledge_gap → knowledge_curator
```

Loop Engineer diagnoses/routes; it does not write spec, plan, application code, or
shared skill.

### R3 requirement

For each enforced trigger, add a reproducible litmus and then add/update the matching
entry in `docs/refactor/maika-vnext/enforcement-ledger.yaml`.

---

## W7 — Approval, resume, and loop CLI

### Goal

Make change loops operable without manual YAML editing.

### CLI

```text
maika loop status --id <change>
maika loop inspect --id <change>
maika loop approve --id <change> --decision <decision-id>
maika loop reject --id <change> --decision <decision-id>
maika loop resume --id <change>
maika loop close --id <change>
```

### Add

- `cli/commands/loop.py`
- `cli/tests/test_loop_command.py`

### Governance

Automatic:

- local code correction inside declared scope;
- replan inside an unchanged approved contract;
- rerun a previously approved safe verification profile.

Human approval required:

- reopen/change spec;
- public contract/security/migration changes;
- scope expansion;
- shared-skill patch or promotion;
- budget extension beyond configured maximum.

Approval records must use existing trusted approval patterns from
`runtime_hardening.py`, bind change/loop/decision hashes, and reject agent-authored
boolean approval fields.

### Tests

- one active loop invariant;
- stale/tampered approval rejected;
- resume returns task to recorded state;
- close requires evidence-backed resolution or explicit `proposal-only` outcome;
- recursive loop opening denied.

---

## W8 — Macro learning evaluation and promotion boundary

### Goal

Turn verified recurring loop outcomes into candidates without automatic global
mutation.

### Extend first

- `cli/knowledge_control.py`
- existing skill candidate/review/promotion paths;
- existing recurrence and poisoning-protection tests.

Add a new module only if existing consumers cannot own aggregation cleanly.

### Candidate threshold

- same root cause across at least two distinct changes and configured recurrence
  threshold; or
- explicit critical safety signal with human approval.

### Required stages

```text
candidate → evaluate → canary → human promote | reject → rollback if needed
```

No verified evaluation means no promotion. Candidate evidence must reference loop
artifacts rather than copy spec/plan bodies.

### Metrics

Add only metrics consumed by report/tests:

- loop level;
- retries before resolution;
- reopen count;
- resolution route;
- candidate created/evaluated/promoted/rejected.

### Tests

- one change cannot produce recurrence-based global candidate;
- distinct-change recurrence can;
- poisoned/untrusted evidence cannot;
- failed canary blocks promotion;
- rollback restores prior shared skill version.

---

## W9 — Migration, repair, uninstall, docs, and rollout

### Goal

Close lifecycle gaps after core/adapter/loop behavior is stable.

### Commands

```text
maika migrate --dry-run|--apply
maika repair --finding <id>
maika uninstall [--purge-project-data]
maika status [--json]
```

### Migration

- inventory `.agents`, `.claude`, `.maika` ownership;
- choose canonical knowledge with hashes/timestamps and explicit conflicts;
- never silently merge conflicting project-owned files;
- install enabled adapters;
- verify before optional legacy cleanup;
- default cleanup preserves source legacy roots until user confirmation.

### Repair

Only safe, finding-specific actions from `doctor setup`; reuse W2 transaction engine.

### Uninstall

- remove framework-owned core and Maika-managed host entries transactionally;
- preserve `.maika/knowledge`, changes, archive, loops, and local config by default;
- purge project data only with explicit confirmation.

### Rollout

1. shadow metrics for Loop Engineer;
2. advisory change-loop recommendations;
3. controlled automatic change loops;
4. default adaptive mode only after false-escalation and resolution metrics pass.

Update README, platform guides, migration guide, troubleshooting, rollback, and
support tier only to match verified behavior.

---

## 5. Per-wave handoff template

Claude must finish every wave with:

```markdown
## Wave <N> handoff

Outcome:
Files changed:
Behavior added:
Behavior intentionally deferred:
Tests added:
Focused verification:
Umbrella CI:
Dirty-worktree items preserved:
Known risks / next-wave prerequisites:
```

Do not begin the next wave when umbrella CI is red, an ownership conflict is
unresolved, or completion would require changing user-owned dirty files.

## 6. Final acceptance

The upgrade is complete only when all applicable acceptance criteria in both source
plans are backed by tests or explicit verified manual smoke evidence. At minimum:

- clean wheel install works without checkout;
- init/update/migrate/uninstall are transactional;
- canonical core and multi-host coexistence pass E2E;
- host content/config outside Maika ownership survives lifecycle operations;
- capability state distinguishes advertised/detected/verified;
- stable hook CLI works on Ubuntu and Windows tests;
- small happy path creates no full plan and no Loop Engineer artifact;
- repeated failure/scope escape opens exactly one evidence-backed change loop;
- approval and recursion boundaries hold;
- macro candidate cannot promote without evaluation/canary;
- umbrella CI, wheel E2E, multi-host E2E, and `git diff --check` pass.

## 7. Claude kickoff prompt

Use this exact initial instruction for the next session:

```text
Read CLAUDE.md and .maika/DEVELOPMENT_RULES.md completely. Then read
docs/superpowers/plans/2026-07-11-upgrade-remaining-claude-handoff-plan.md and the
two source plans under upgrade/. Preserve all existing dirty-worktree changes.
Execute W0 only. Do not start W1 until W0 tests and python3 scripts/run_ci.py pass.
Report the W0 handoff using the template in the plan. Do not restore or delete the
three pre-existing deleted root documents.
```
