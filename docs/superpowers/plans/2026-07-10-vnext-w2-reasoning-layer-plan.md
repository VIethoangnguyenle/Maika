# Maika vNext W2 — Full Reasoning Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete W2 from `MAIKA_FULL_MASTER_REFACTOR_PLAN.md`: canonical reasoning skills, evidence/spec/plan gates, Author DNA + convention inputs, deletion of duplicate planning/exploration/spec skills, and a skill index containing only target skills.

**Architecture:** Keep W1 plan compilation and sequential execution as the execution base, but make the W2 reasoning artifacts real runtime artifacts rather than prose-only contracts. W2 extends workspace bootstrap to create `INTENT.md`, `exploration/GROUNDING.yaml`, `exploration/EVIDENCE_MANIFEST.yaml`, and `RECONCILIATION.md`; wires `INTENT.md`, `exploration-evidence`, and `spec` gates into vNext CLI transitions; then moves scaffold consumers to the target skill set. It extends `gate-check` rather than creating a new tool, honoring `.maika/DEVELOPMENT_RULES.md` R5.

**Tech Stack:** Python 3.11, pytest, PyYAML, existing `.maika/tools/gate-check`, existing `.maika/tools/skill-index/generate_index.py`, existing scaffold manifest.

## Global Constraints

- Source authority: `MAIKA_FULL_MASTER_REFACTOR_PLAN.md` §§7-14 and §31 W2; current source wins for exact paths and symbols.
- Work on branch `refactor/maika-vnext-full`; preserve pre-existing plan-file status (`D MAIKA_VNEXT_MASTER_REFACTOR_PLAN.md`, `?? MAIKA_FULL_MASTER_REFACTOR_PLAN.md`) unless W2 explicitly needs the new master plan.
- Use `rtk` prefix for shell commands. Use `/usr/bin/python3 -m pytest` for test suites.
- No compatibility aliases, backup folders, `.old`/`.bak`, duplicate skill responsibilities, provider-specific canonical skills, or removed-workflow skill references.
- Canonical skills refer to capability IDs, not concrete provider function names. Provider names may remain only in platform adapters, setup docs, historical refactor reports, and capability matrices.
- Extend existing consumers in the same wave: `vnext_state.py`, `orchestrator.py`, `plan_compiler.py`, `cli/plugin-manifest.yaml`, skill index, skill standard tests, scaffold tests, and no-hardcoded-provider tests.
- Deletions require a deletion manifest entry in `docs/refactor/maika-vnext/deletion-manifest.yaml` and a post-delete reference scan.
- Commit boundary for the wave: one W2 commit after implementation, review, and focused suites pass.

---

### Task 1: W2 failing tests for target skill set and provider independence

**Files:**
- Create: `cli/tests/test_vnext_w2_reasoning_layer.py`
- Modify: `cli/tests/test_init.py`
- Modify: `cli/tests/test_update.py`
- Modify: `cli/tests/test_scaffold.py`
- Modify: `cli/tests/test_status.py`
- Modify: `cli/tests/test_ascii_diagram_guidance.py`
- Modify: `cli/tests/test_snapshots.py` inputs through regenerated snapshot files
- Modify: `README.md`

**Interfaces:**
- Produces mechanical expectations for the 15 target skills and scaffold consumers.

- [ ] **Step 1: Write failing tests**

Create `cli/tests/test_vnext_w2_reasoning_layer.py` with tests that:

- assert `.maika/skills` directories exactly equal:
  `intent-analysis`, `grounding-explorer`, `architecture-reconciler`, `grounded-brainstorming`, `writing-spec`, `writing-plan`, `validating-plan`, `executing-task`, `reviewing-task`, `reviewing-change`, `verification-before-completion`, `knowledge-curator`, `author-dna-builder`, `convention-intelligence-builder`, `infra-tdd`;
- assert `skill-index.yaml` lists exactly the same names;
- assert `cli/plugin-manifest.yaml` skill entries (except `skill-index-data`) ship exactly the same skill names;
- assert every target `SKILL.md` body contains the required contract headings: `Purpose`, `Triggers`, `Inputs`, `Required outcomes`, `Invariants`, `Evidence requirements`, `Process`, `Stop conditions`, `Output contract`, `Next handoff`;
- scan `.maika/skills/*/SKILL.md` and `.maika/skills/*/references/*.md` for removed skill names and raw provider tool names.

Update existing scaffold/status/README tests to expect `intent-analysis` as the smoke skill instead of `requirement-analyst`, and `grounding-explorer` instead of `codebase-explorer`. Rewrite the ASCII diagram guidance tests so the required diagram guidance lives in `writing-spec` and `grounded-brainstorming`, not deleted `spec-extract` or `openspec-explore`.

- [ ] **Step 2: Verify red**

Run:

```bash
rtk /usr/bin/python3 -m pytest cli/tests/test_vnext_w2_reasoning_layer.py cli/tests/test_init.py::test_init_antigravity_uses_agents_as_only_framework_root cli/tests/test_init.py::test_init_codex_uses_agents_as_only_framework_root cli/tests/test_init.py::test_init_claude_uses_claude_as_only_framework_root cli/tests/test_init.py::test_init_generic_keeps_maika_framework_root cli/tests/test_update.py::test_update_uses_resolved_framework_root cli/tests/test_update.py::test_reconfigure_to_claude_writes_claude_root_and_warns_about_legacy_maika cli/tests/test_scaffold.py::test_resolve_source_path_maps_skills cli/tests/test_status.py cli/tests/test_ascii_diagram_guidance.py .maika/tools/microloop-orchestrator/tests/test_vnext_state.py::test_init_workspace_creates_minimal_layout .maika/tools/microloop-orchestrator/tests/test_vnext_cli_e2e.py::test_vnext_cli_e2e -q
```

Expected: FAIL because legacy skill dirs and manifest entries still exist.

### Task 2: Canonical reasoning skills and skill-index cutover

**Files:**
- Create: `.maika/skills/intent-analysis/SKILL.md`
- Create: `.maika/skills/grounding-explorer/SKILL.md`
- Create: `.maika/skills/architecture-reconciler/SKILL.md`
- Create: `.maika/skills/grounded-brainstorming/SKILL.md`
- Create: `.maika/skills/writing-spec/SKILL.md`
- Create: `.maika/skills/validating-plan/SKILL.md`
- Create: `.maika/skills/executing-task/SKILL.md`
- Create: `.maika/skills/reviewing-task/SKILL.md`
- Create: `.maika/skills/reviewing-change/SKILL.md`
- Create: `.maika/skills/verification-before-completion/SKILL.md`
- Modify: `.maika/skills/writing-plan/SKILL.md`
- Modify: `.maika/skills/knowledge-curator/SKILL.md`
- Modify: `.maika/skills/author-dna-builder/SKILL.md`
- Modify: `.maika/skills/convention-intelligence-builder/SKILL.md`
- Modify: `.maika/skills/infra-tdd/SKILL.md`
- Modify: `.maika/skills/skill-index.yaml` via generator
- Delete: `.maika/skills/architecture-reviewer/`
- Delete: `.maika/skills/codebase-explorer/`
- Delete: `.maika/skills/db-explorer/`
- Delete: `.maika/skills/document-writer/`
- Delete: `.maika/skills/openspec-archive-change/`
- Delete: `.maika/skills/openspec-explore/`
- Delete: `.maika/skills/openspec-propose/`
- Delete: `.maika/skills/requirement-analyst/`
- Delete: `.maika/skills/spec-extract/`
- Delete: `.maika/skills/spec-validator/`
- Create/Modify: `docs/refactor/maika-vnext/deletion-manifest.yaml`

**Interfaces:**
- Produces only the target skill set and regenerated index.

- [ ] **Step 1: Implement skill bodies**

Each skill must be under 300 body lines, include frontmatter `name`, `version`, `description`, and include the W2 contract headings. New and rewritten skills must reference canonical artifacts (`CHANGE.yaml`, `GROUNDING.yaml`, `EVIDENCE_MANIFEST.yaml`, `RECONCILIATION.md`, `SPEC.md`, `IMPLEMENTATION_PLAN.md`, `PLAN_VALIDATION.json`) and capability IDs from `.maika/profiles/capabilities.md`.

- [ ] **Step 2: Delete superseded skill dirs**

Before deletion, scan consumers:

```bash
rtk rg -n "architecture-reviewer|codebase-explorer|db-explorer|document-writer|openspec-|requirement-analyst|spec-extract|spec-validator" .maika cli README.md -g '!cli/tests/snapshots/*'
```

Move valid consumers in Task 3 and record each deleted path with reason, moved consumers, and verification command.

- [ ] **Step 3: Regenerate skill index**

Run:

```bash
rtk python3 .maika/tools/skill-index/generate_index.py .maika
```

Expected: `Successfully generated .maika/skills/skill-index.yaml with 15 skills.`

### Task 3: Scaffold manifest and W2 reasoning/planning reference cleanup

**Files:**
- Modify: `cli/plugin-manifest.yaml`
- Modify: `.maika/workflows/task.md`
- Modify: `.maika/rules/rules-exec.md`
- Modify: `.maika/rules/rules-knowledge.md`
- Modify: `.maika/rules/rules-tool.md`
- Modify: `.maika/procedures/context-loader.md`
- Modify: `.maika/procedures/reviewer.md`
- Modify: `.maika/procedures/token-tracking.md`
- Modify: `.maika/profiles/agent-memory-mcp-only-setup.md`
- Modify: `.maika/meta-prompt.md`
- Modify: `.maika/tools/README.md`
- Modify/Delete: tests that target deleted skills (`cli/tests/test_architecture_reviewer_protocol.py`, `cli/tests/test_codebase_explorer_protocol.py`, `cli/tests/test_ascii_diagram_guidance.py`)
- Modify: `README.md`
- Modify: `cli/tests/snapshots/antigravity.txt`
- Modify: `cli/tests/snapshots/claude-code.txt`
- Modify: `cli/tests/snapshots/codex.txt`
- Modify: `cli/tests/snapshots/generic.txt`

**Interfaces:**
- Consumes target skill names from Task 2.
- Produces scaffold and W2 reasoning/planning prose with no references to deleted skills. Execution/apply/review details that are not implemented until W3/W5 must be described as `vnext-run`/future dispatch phases without naming removed skills or removed OpenSpec commands.

- [ ] **Step 1: Replace manifest skill entries**

Replace the legacy `# ─── SKILLS ───` block in `cli/plugin-manifest.yaml` with one entry per target skill plus `skill-index-data`.

- [ ] **Step 2: Update W2 reasoning/planning references**

Replace deleted skill names with target roles:

- `requirement-analyst` / `spec-extract` → `intent-analysis` or `writing-spec` depending on context;
- `codebase-explorer` / `db-explorer` → `grounding-explorer`;
- `architecture-reviewer` → `architecture-reconciler` for pre-spec reconciliation, `reviewing-change` for whole-change review;
- `spec-validator` → `validating-plan`;
- `openspec-*` → canonical W2 artifact phases (`intent-analysis`, `grounding-explorer`, `architecture-reconciler`, `writing-spec`, `writing-plan`, `validating-plan`) in reasoning/planning sections only; apply/review sections must say execution stays on the W1 `vnext-run` path until W3, without referencing removed skills;
- `document-writer` → remove from operational scaffold unless a current target consumer exists.

Do not claim the full W3 task-review loop or W5 public `/task` command surface is complete in this wave. The purpose of this cleanup is to remove deleted-skill references from live docs while keeping the runtime truth accurate.

- [ ] **Step 3: Retire obsolete tests**

Delete or rewrite tests that enforce old skills. Prefer rewriting to target-skill checks where they still protect W2 behavior.

- [ ] **Step 4: Regenerate scaffold snapshots**

Run the existing snapshot update flow used by `cli/tests/test_snapshots.py` or run `maika init` through the test helper if that is how snapshots are generated locally. Snapshot files must contain only target skills.

### Task 4: W2 gates for grounding, evidence, spec, and plan semantic subset

**Files:**
- Modify: `.maika/tools/gate-check/gates.py`
- Modify: `.maika/tools/gate-check/cli.py`
- Create: `.maika/tools/gate-check/tests/test_vnext_reasoning_gates.py`
- Modify: `.maika/tools/microloop-orchestrator/vnext_state.py`
- Modify: `.maika/tools/microloop-orchestrator/orchestrator.py`
- Modify: `.maika/tools/microloop-orchestrator/plan_compiler.py`
- Modify: `.maika/tools/microloop-orchestrator/tests/test_vnext_state.py`
- Modify: `.maika/tools/microloop-orchestrator/tests/test_vnext_cli_e2e.py`
- Modify: `.maika/tools/microloop-orchestrator/tests/test_vnext_dispatch.py`
- Modify: `docs/refactor/maika-vnext/enforcement-ledger.yaml`

**Interfaces:**
- Produces runtime consumers for `GROUNDING.yaml`, `EVIDENCE_MANIFEST.yaml`, `RECONCILIATION.md`, and `SPEC.md`; validators for `exploration-evidence`, `spec`, and a W2-expanded `plan`.

- [ ] **Step 1: Write failing tests**

Tests must cover:

- `vnext_state.init_workspace(...)` creates `INTENT.md`, `exploration/GROUNDING.yaml`, `exploration/EVIDENCE_MANIFEST.yaml`, and `RECONCILIATION.md` alongside W1 artifacts;
- `validate_intent(intent_text, change_text)` requires a non-empty intent summary for `standard` and `architectural` changes and allows a lighter intent for `trivial`/`small`;
- `validate_exploration_evidence(grounding_text, evidence_text)` requires three lenses (`codebase`, `business`, `conventions`), claim IDs, claim statuses, and at least one source for verified code facts;
- `validate_vnext_spec(spec_text, change_class)` requires small/full sections per master plan §12 and `Evidence References`;
- `validate_vnext_plan(...)` rejects plans with acceptance criteria missing from task sections and rejects evidence hash mismatches when `EVIDENCE_MANIFEST.yaml` exists.
- `orchestrator.py vnext-validate-reasoning --workspace <ws> --repo-root <root>` runs `intent` and `exploration-evidence`, writes `generated/EXPLORATION_VALIDATION.json`, and transitions `EXPLORING -> RECONCILING` when approved;
- `orchestrator.py vnext-validate-spec --workspace <ws> --repo-root <root>` runs `spec`, writes `generated/SPEC_VALIDATION.json`, and transitions `SPEC_REVIEW -> PLANNING` when approved.

- [ ] **Step 2: Implement validators inside existing `gate-check`**

Do not create a new tool. Add CLI validator names:

- `exploration-evidence`
- `intent`
- `spec`
- keep/extend `vnext-plan`

Update `plan_compiler.compile_plan` to pass `EVIDENCE_MANIFEST.yaml` hash when present.

- [ ] **Step 3: Wire runtime consumers**

Update `vnext_state.init_workspace` to create the W2 artifact skeletons with valid empty YAML structures and an `INTENT.md` prompt stub. Update `orchestrator.py` with the two validation subcommands above. `vnext-validate-reasoning` must read `CHANGE.yaml`, `INTENT.md`, `exploration/GROUNDING.yaml`, and `exploration/EVIDENCE_MANIFEST.yaml`; this is the mechanical consumer for `INTENT.md`. Keep W1 `vnext-compile` compatible: if a workspace starts at `INTAKE`, it may still transition to `PLANNING` only for `trivial`/`small`; standard/architectural work must pass the W2 reasoning/spec gates before planning.

- [ ] **Step 4: Activate enforcement ledger entries**

Promote the `exploration-evidence` and `spec` gate entries in `docs/refactor/maika-vnext/enforcement-ledger.yaml` from proposed to active in the same commit as their validators. Each entry must cite the W2 litmus pytest command and `external_requirement` or `safety_boundary` evidence classification as appropriate.

### Task 5: Focused verification and W2 review package

**Files:**
- Modify: `docs/refactor/maika-vnext/deletion-manifest.yaml`

**Interfaces:**
- Produces W2 verification evidence and deletion manifest completion.

- [ ] **Step 1: Run focused suites**

```bash
rtk /usr/bin/python3 -m pytest cli/tests/test_vnext_w2_reasoning_layer.py cli/tests/test_skill_standard.py cli/tests/test_no_hardcoded_memory_tools.py cli/tests/test_init.py cli/tests/test_update.py cli/tests/test_scaffold.py cli/tests/test_status.py cli/tests/test_ascii_diagram_guidance.py cli/tests/test_snapshots.py .maika/tools/gate-check/tests/test_vnext_reasoning_gates.py .maika/tools/gate-check/tests/test_vnext_plan_gate.py .maika/tools/gate-check/tests/test_vnext_brief_gate.py .maika/tools/gate-check/tests/test_vnext_result_gate.py .maika/tools/microloop-orchestrator/tests/test_vnext_state.py .maika/tools/microloop-orchestrator/tests/test_vnext_cli_e2e.py .maika/tools/microloop-orchestrator/tests/test_vnext_dispatch.py .maika/tools/microloop-orchestrator/tests/test_plan_compiler.py -q
```

Expected: all selected tests pass.

- [ ] **Step 2: Reference scan**

```bash
rtk rg -n "architecture-reviewer|codebase-explorer|db-explorer|document-writer|openspec-|requirement-analyst|spec-extract|spec-validator" .maika cli README.md -g '!docs/refactor/maika-vnext/*' -g '!cli/tests/snapshots/*'
```

Expected: no operational references. Historical references under `docs/refactor/maika-vnext/` are allowed.

- [ ] **Step 3: Independent task/wave review**

Create a diff package and run an independent review against this W2 plan. Resolve Critical and Important findings before commit.

- [ ] **Step 4: Commit**

```bash
rtk git add README.md cli/tests/test_vnext_w2_reasoning_layer.py cli/tests/test_init.py cli/tests/test_update.py cli/tests/test_scaffold.py cli/tests/test_status.py cli/tests/test_ascii_diagram_guidance.py cli/tests/snapshots/antigravity.txt cli/tests/snapshots/claude-code.txt cli/tests/snapshots/codex.txt cli/tests/snapshots/generic.txt cli/plugin-manifest.yaml .maika/skills .maika/workflows/task.md .maika/rules/rules-exec.md .maika/rules/rules-knowledge.md .maika/rules/rules-tool.md .maika/procedures/context-loader.md .maika/procedures/reviewer.md .maika/procedures/token-tracking.md .maika/profiles/agent-memory-mcp-only-setup.md .maika/meta-prompt.md .maika/tools/README.md .maika/tools/gate-check/gates.py .maika/tools/gate-check/cli.py .maika/tools/gate-check/tests/test_vnext_reasoning_gates.py .maika/tools/microloop-orchestrator/vnext_state.py .maika/tools/microloop-orchestrator/orchestrator.py .maika/tools/microloop-orchestrator/plan_compiler.py .maika/tools/microloop-orchestrator/tests/test_vnext_state.py .maika/tools/microloop-orchestrator/tests/test_vnext_cli_e2e.py .maika/tools/microloop-orchestrator/tests/test_vnext_dispatch.py docs/refactor/maika-vnext/deletion-manifest.yaml docs/refactor/maika-vnext/enforcement-ledger.yaml docs/superpowers/plans/2026-07-10-vnext-w2-reasoning-layer-plan.md
rtk git commit -m "feat(vnext-w2): canonical reasoning layer and skill cutover"
```
