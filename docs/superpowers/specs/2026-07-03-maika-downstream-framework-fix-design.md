# Maika Downstream Framework Fix Design

> Date: 2026-07-03  
> Status: draft-for-review  
> Scope: Fix Maika upstream, then update downstream projects such as `vietbank-sme-omni`.

## Problem

Two downstream reports from `vietbank-sme-omni/.agents/report` exposed framework-level failures that should be fixed in Maika upstream rather than patched directly downstream.

1. `author-dna-builder` allowed confirmed hypotheses to be encoded at the wrong abstraction level. Concrete implementation rules such as annotations, naming patterns, and handler placement leaked into `author-dna.yaml` instead of being split into `conventions.yaml` or `knowledge-snapshot.md`.
2. Existing knowledge YAML files were rewritten with `yaml.dump`, destroying comments, block scalar formatting, ordering, author notes, and exemplar detail.
3. `write-gate` misclassified absolute paths under the framework root. Relative `.agents/...` targets were allowed as framework artifacts, while absolute `/home/.../.agents/...` targets were treated as app-code and blocked by checkpoint/apply gates.
4. Maika advertises `/convention-scan`, `/dna-scan`, and `/approve-dna`, but `cli/plugin-manifest.yaml` currently scaffolds only `/approve-conventions` among those workflows. Downstream `maika update` therefore cannot reliably install the complete workflow surface.

The desired outcome is an upstream fix that can be installed or updated into downstream repositories without overwriting project-owned knowledge.

## Goals

- Normalize write-gate paths so absolute targets inside the project are evaluated the same as relative targets.
- Harden `author-dna-builder` instructions so every confirmed hypothesis produces an explicit placement decision before any file write.
- Preserve existing YAML formatting and comments when updating project knowledge files.
- Ship all documented scan/approval workflows through the plugin manifest.
- Add tests that reproduce the downstream failures and protect the reinstall/update path.
- Provide a downstream verification path for `vietbank-sme-omni`.

## Non-Goals

- Do not directly fix `vietbank-sme-omni` knowledge files as part of the upstream implementation.
- Do not add a new runtime gate for R-DNA-7 in this change. This design hardens the workflow/skill instructions and scaffold distribution; mechanical teaching-moment enforcement remains covered by the existing teaching-moment checkpoint work.
- Do not introduce a new YAML dependency unless implementation proves text-preserving edits are insufficient.
- Do not relax the app-code apply gate. Code writes should still require a valid checkpoint and `Pha 2 DONE`.

## Architecture

The fix spans four existing Maika layers.

### Runtime Hook Layer

`write_gate.evaluate_write()` should normalize the target path before classification:

- If the target is absolute and is under `project_root`, convert it to `target.relative_to(project_root)`.
- If the target is relative, keep it relative.
- If the target is absolute but outside `project_root`, keep it absolute and treat it as non-framework, non-doc target.

All framework artifact checks, documentation checks, git-ignore checks, and error messages should operate on the normalized path where possible. This keeps existing app-code protections intact while fixing false denials for absolute framework paths.

### Author DNA Encoding Layer

`author-dna-builder/SKILL.md` should require a per-hypothesis placement record before encoding:

```yaml
placement_decision:
  raw_pattern: "<concrete observed pattern>"
  thinking_principle: "<WHY/HOW, if still meaningful after removing concrete names>"
  code_rule: "<WHAT naming/structure/organization rule, if present>"
  architecture_fact: "<WHAT-IS component/relationship fact, if present>"
  targets:
    author_dna: true|false
    conventions: true|false
    knowledge_snapshot: true|false
  overlap_check: "<existing HP/SP/CP/IC id or none>"
```

Rules:

- `author-dna.yaml` receives only `thinking_principle`.
- `conventions.yaml` receives `code_rule`.
- `knowledge-snapshot.md` receives `architecture_fact`.
- If the thinking principle overlaps an existing HP/SP entry, do not create a duplicate DNA entry.
- If removing concrete names leaves no principle, do not write to author DNA.

The interview protocol should ask the author to confirm the split when a hypothesis contains both a principle and a concrete rule.

### YAML Preservation Layer

The skill and approval workflows should explicitly forbid full-file reserialization for existing project knowledge YAML:

- Disallowed for updates: `yaml.safe_load(...)` followed by `yaml.dump(...)` over the same existing file.
- Allowed: targeted text insertion/replacement that preserves unrelated content.
- Allowed: `yaml.dump` only when creating a new file from scratch.
- Allowed later if adopted intentionally: a comment-preserving YAML library with tests proving comments and block scalars survive.

This is an instruction-level contract because Maika workflows are executed by agents, not a centralized Python writer.

### Distribution Layer

`cli/plugin-manifest.yaml` should scaffold every workflow documented in README and present in `.maika/workflows/`:

- `workflow-convention-scan` -> `{{ platform.framework_root }}/workflows/convention-scan.md`
- `workflow-approve-conventions` -> existing target
- `workflow-dna-scan` -> `{{ platform.framework_root }}/workflows/dna-scan.md`
- `workflow-approve-dna` -> `{{ platform.framework_root }}/workflows/approve-dna.md`

`knowledge-active-skeleton` and `knowledge-long-term` stay user-owned, so `maika update` must preserve downstream knowledge files while refreshing framework-managed workflows, skills, hooks, rules, procedures, and tools.

## Data Flow

1. Developer fixes Maika upstream.
2. Unit tests verify hook behavior and scaffold manifest behavior.
3. `maika update --target /home/zane/Desktop/vietbank-sme-omni` re-renders framework files into a staging directory and syncs framework-managed files.
4. Downstream receives updated `write_gate.py`, workflows, and `author-dna-builder` instructions.
5. Downstream knowledge files remain project-owned and unchanged unless the user later runs `/dna-scan`, `/approve-dna`, `/convention-scan`, or `/approve-conventions`.

## Error Handling

- Absolute paths outside the project should not be silently treated as framework artifacts.
- If a downstream project has unresolved template markers after render, `maika update` already aborts before modifying the target; this behavior should remain.
- If tests reveal an undocumented workflow should not be shipped, README and manifest must be made consistent instead of leaving the mismatch.
- Existing dirty worktree changes must not be reverted or included unless directly related to this fix.

## Testing

Add or update tests in the existing suites:

- `.maika/hooks/write-gate/tests/test_write_gate.py`
  - absolute path under framework root is allowed.
  - absolute path under docs is allowed as documentation.
  - absolute app-code path still requires checkpoint and apply evidence.
  - shell target absolute framework path is normalized before classification if parsed as a concrete target.

- `cli/tests/test_scaffold.py`
  - manifest declares `workflow-convention-scan`, `workflow-dna-scan`, and `workflow-approve-dna`.
  - scaffold output for an Antigravity/Codex platform includes all scan/approval workflow files.
  - update/scaffold preserves user-owned knowledge directories.

- Skill/workflow text checks
  - `author-dna-builder/SKILL.md` contains the placement decision contract.
  - `author-dna-builder/SKILL.md` and approval workflows contain the no-`yaml.dump`-on-existing-knowledge rule.

Verification commands:

```bash
rtk pytest .maika/hooks/write-gate/tests cli/tests -q
rtk python -m pytest cli/tests/test_scaffold.py -q
```

Downstream smoke check after implementation:

```bash
rtk maika update --target /home/zane/Desktop/vietbank-sme-omni
rtk test -f /home/zane/Desktop/vietbank-sme-omni/.agents/workflows/dna-scan.md
rtk test -f /home/zane/Desktop/vietbank-sme-omni/.agents/workflows/approve-dna.md
rtk test -f /home/zane/Desktop/vietbank-sme-omni/.agents/workflows/convention-scan.md
```

## Rollout

1. Implement upstream changes in Maika.
2. Run Maika test suites.
3. Run `maika update` against `vietbank-sme-omni`.
4. Verify downstream workflow files exist and updated hook behavior reproduces the absolute-path allow case.
5. Do not mutate downstream long-term knowledge during rollout.

## Open Decisions

None. The selected approach is upstream fix plus downstream update.
