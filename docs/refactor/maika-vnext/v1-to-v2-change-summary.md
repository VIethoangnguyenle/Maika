# Master Plan v1 → v2 — Change Summary and Traceability

- **v1:** `MAIKA_VNEXT_MASTER_REFACTOR_PLAN.md` at commit `437ae91` (superseded)
- **v2:** `MAIKA_VNEXT_MASTER_REFACTOR_PLAN.md` (current)
- **Authoritative migration strategy:** Design Spec Rev 2 — `docs/superpowers/specs/2026-07-10-vnext-plan-restructure-design.md`

Every major Rev 2 decision maps to the v2 sections that implement it.

```yaml
decisions:
  - id: P1
    decision: Dogfood-first waves — every wave ends with a dogfood checkpoint on real changes
    source_section: Design Spec Rev 2 §3
    v2_sections:
      - "§4 Migration principles"
      - "§26 W0–W7 (Dogfood checkpoint field in every wave)"
    status: applied

  - id: P2
    decision: Enforcement ledger governs implementation eligibility of every gate/hook/validator
    source_section: Design Spec Rev 2 §3, §4
    v2_sections:
      - "§4 Migration principles"
      - "§5 Enforcement ledger"
      - "§22 Enforcement architecture (ledger-reference rule)"
      - "§26 W0 scope 7"
      - "§30 criteria 19, 23"
    status: applied

  - id: P3
    decision: R4 pre-flight — platform-mechanism claims require file:line/command evidence per platform
    source_section: Design Spec Rev 2 §3
    v2_sections:
      - "§4 Migration principles"
      - "§26 W0 scope 8 (platform capability matrix)"
      - "§26 W5 preconditions"
      - "§18.6 model-tier activation"
    status: applied

  - id: P4
    decision: Single-platform-first — Claude Code vertical slice before Codex/Antigravity adapters
    source_section: Design Spec Rev 2 §3
    v2_sections:
      - "§4 Migration principles"
      - "§26 W1"
      - "§26 W5"
    status: applied

  - id: P5
    decision: Real fixtures over built fixtures — one minimal Python CI fixture + real-repo dogfood
    source_section: Design Spec Rev 2 §3
    v2_sections:
      - "§4 Migration principles"
      - "§27 End-to-end"
      - "§26 W7 scope 1"
      - "§30 criterion 21"
    status: applied

  - id: LEDGER-SCHEMA
    decision: Machine-readable ledger schema; statuses proposed/active/deferred/superseded/removed;
      evidence classifications observed_failure/reproducible_litmus/external_requirement/safety_boundary;
      deferred entries carry activation conditions; R3-amendment PR proposed in W0
    source_section: Design Spec Rev 2 §4
    v2_sections:
      - "§5 Enforcement ledger"
      - "§26 W0 scope 7, 9"
    status: applied

  - id: CAP-VOCAB
    decision: Six abstract capability IDs exist from W1; canonical skills/roles use IDs only;
      providers confined to mappings/profiles/adapters/tool docs/matrix
    source_section: Design Spec Rev 2 §5
    v2_sections:
      - "§3 AD-4"
      - "§10 Role model (all role capability lists)"
      - "§11.1 Capability vocabulary"
      - "§13 Native skill set"
      - "§26 W1 scope 2"
    status: applied

  - id: CLASSIFICATION
    decision: Four change classes with proportional pipelines, recorded in CHANGE.yaml
    source_section: Design Spec Rev 2 §6
    v2_sections:
      - "§6 Change classification"
      - "§8 workspace (class-aware artifact subset)"
      - "§14 short-spec subset for small"
      - "§30 criterion 24"
    status: applied

  - id: AUTO-CLASSIFY
    decision: trivial/clear-small display class + reason and proceed; explicit confirmation only
      for the seven listed conditions
    source_section: Design Spec Rev 2 §6
    v2_sections:
      - "§6 Automatic classification"
      - "§23 command surface + user approval gates"
    status: applied

  - id: ESCALATION
    decision: Reclassification rides the existing re-plan triggers; no new mechanism
    source_section: Design Spec Rev 2 §6
    v2_sections:
      - "§6 Escalation and reclassification"
      - "§19 re-plan triggers"
    status: applied

  - id: WAVES-8
    decision: 13 infrastructure-first waves → 8 dogfood-first waves
    source_section: Design Spec Rev 2 §7
    v2_sections:
      - "§26 Implementation waves W0–W7"
    status: applied

  - id: W1-SLICE
    decision: Genuinely end-to-end W1 vertical slice on Claude Code; explicit must-not-depend list
    source_section: Design Spec Rev 2 §7
    v2_sections:
      - "§26 W1"
      - "§18.1 dispatch-class subset"
      - "§17 compiler subset"
    status: applied

  - id: W2-3LENS
    decision: Three mandatory grounding lenses (codebase/business/conventions) in one GROUNDING.yaml;
      brainstorming blocked without all three
    source_section: Design Spec Rev 2 §7 (mandatory correction 1)
    v2_sections:
      - "§3 AD-3"
      - "§8 workspace (exploration/GROUNDING.yaml)"
      - "§10.1 Grounding Explorer"
      - "§10.3 Grounded Brainstormer"
      - "§22 exploration-evidence gate"
      - "§26 W2"
    status: applied

  - id: W3-CONDITIONAL
    decision: Explorer specialization only on recorded dogfood signals; specialized agents still
      write the same artifact
    source_section: Design Spec Rev 2 §7
    v2_sections:
      - "§10.1 (specialization clause)"
      - "§26 W3 scope 3"
    status: applied

  - id: W4-RUNTIME-SCOPE
    decision: W4 = registry, health/freshness probes, mappings, skill lint, rules-tool cleanup;
      router limited to health + freshness; no skill-contract rewrite in W4
    source_section: Design Spec Rev 2 §5, §7, §8
    v2_sections:
      - "§11.2, §11.3"
      - "§26 W4"
    status: applied

  - id: W5-R4
    decision: Codex/Antigravity adapters bounded by the W0 matrix; R4 pre-flight opens the wave
    source_section: Design Spec Rev 2 §7
    v2_sections:
      - "§26 W5"
    status: applied

  - id: MICROLOOP-MIGRATION
    decision: Microloop work framed as contract migration (markdown → JSON) with legacy
      compatibility reader, not simple extension
    source_section: Design Spec Rev 2 §9
    v2_sections:
      - "§3 AD-9"
      - "§17"
      - "§26 W1 scope 4"
    status: applied

  - id: OPENSPEC
    decision: OpenSpec importer; W6 removes OpenSpec from the vNext path only (legacy
      path keeps OpenSpec and remains the default engine); the W7 default switch removes
      OpenSpec from the default execution path; physical deletion only after the
      compatibility window and consumer-map verification
    source_section: Design Spec Rev 2 §7 (W6) + PR #39 review correction 2
    v2_sections:
      - "§24 (incl. Timeline)"
      - "§26 W6"
      - "§26 W7 scope 4"
    status: applied

  - id: GATES-9
    decision: 17 lifecycle gates → 9 primary gates; freshness/DAG/symbol-grounding/coverage/
      verification-completeness are internal checks
    source_section: Design Spec Rev 2 §8
    v2_sections:
      - "§16 (checks inside plan gate)"
      - "§22 Enforcement architecture"
      - "§22 Gate applicability by change class"
    status: applied

  - id: STATES-14
    decision: 18 persistent states → 14; blocker detail as metadata; READY removed;
      TASK_REVIEW becomes per-task queue status
    source_section: Design Spec Rev 2 §8
    v2_sections:
      - "§9 State model"
    status: applied

  - id: SEQUENTIAL-ONLY
    decision: Sequential queue is the only execution mode through W6; file locks/overlap
      detection deferred with parallelism
    source_section: Design Spec Rev 2 §8
    v2_sections:
      - "§2 Non-goals"
      - "§17 (compiler duty 4 + deferral note)"
      - "§21 (ownership checks deferred)"
      - "§26 W1/W6/W7 deferred fields"
    status: applied

  - id: EVIDENCE-FILE-HASH
    decision: Evidence and plan hashing at file level; claim-level hashing deferred with
      activation condition
    source_section: Design Spec Rev 2 §8
    v2_sections:
      - "§3 AD-8"
      - "§12 Evidence model"
    status: applied

  - id: ROUTER-SCOPE
    decision: Cost/risk/data-sensitivity routing cut; health + freshness only
    source_section: Design Spec Rev 2 §8
    v2_sections:
      - "§11.3"
      - "§26 W4 deferred"
    status: applied

  - id: DASHBOARD-DEFER
    decision: Dashboard expansion is not a committed wave; existing dashboard and
      ACTIVITY_LOG.jsonl unchanged unless dogfood records a deficiency
    source_section: Design Spec Rev 2 §8
    v2_sections:
      - "§2 Non-goals"
      - "§26 W7 scope 3 / deferred"
    status: applied

  - id: FIXTURE-DIET
    decision: 3 fixture repos + 8 built dogfood scenarios → 1 minimal Python fixture + real changes
    source_section: Design Spec Rev 2 §8
    v2_sections:
      - "§27 End-to-end"
      - "§26 W7 scope 1"
    status: applied

  - id: AD4-ROLE-FIX
    decision: Role model uses capability IDs; concrete provider names removed from role contracts
    source_section: Design Spec Rev 2 §9
    v2_sections:
      - "§10 (all roles)"
      - "§30 criterion 5"
    status: applied

  - id: FIRST-AGENT
    decision: First-agent instructions updated to W0-then-W1-slice ordering
    source_section: Design Spec Rev 2 §9
    v2_sections:
      - "§32 First agent instructions"
    status: applied

  - id: V2-CHECKLIST
    decision: Rev 2 §10 ten-point consistency checklist adopted as acceptance criteria of the rewrite
    source_section: Design Spec Rev 2 §10
    v2_sections:
      - "§2 Non-goals (items 12–15)"
      - "§26 wave preconditions/deferred fields"
      - "§30 criteria 23–24"
    status: applied
```

## PR #39 review corrections (2026-07-10)

Focused correction pass sau review; không mở lại kiến trúc.

```yaml
corrections:
  - id: REV-1-W0-SNAPSHOT
    decision: W0 maps là baseline snapshot (baseline_commit + coverage block); CI vĩnh viễn
      chỉ validate schema + nhất quán nội bộ; so khớp disk là bước audit một lần của W0.
      Ledger + capability matrix là living registries có chủ đích.
    applied_to: ["Master Plan §26 W0 (Snapshot vs registry)", "W0 plan Task 4/5/6"]
    status: applied

  - id: REV-2-W6W7-OPENSPEC
    decision: W6 gỡ OpenSpec khỏi vNext path, legacy path giữ OpenSpec và vẫn là default;
      W7 default switch mới gỡ OpenSpec khỏi default execution path; xóa vật lý sau
      compatibility window + consumer-map verification.
    applied_to: ["Master Plan §24 Timeline", "§26 W6 objective/scope 5/exit", "§26 W7 scope 4"]
    status: applied

  - id: REV-3-W1-MODEL-OPTIONAL
    decision: model_selection là optimization, không phải hard dependency của W1;
      supported=false chỉ giới hạn tier (single-tier degradation), không chặn wave.
      W1 preconditions đổi thành dispatch/handoff/result/write-gate evidence.
    applied_to: ["Master Plan §26 W1 preconditions", "§18.6", "W0 plan Task 8"]
    status: applied

  - id: REV-4-W0-DOCS-PLUS-TESTS
    decision: W0 = documentation + schema-validation tests, không đổi runtime behavior;
      rollback boundary revert cả docs lẫn tests; PR #39 tự nó vẫn docs-only.
    applied_to: ["Master Plan §26 W0 Deferred/Deliverables/Rollback", "PR #39 body"]
    status: applied

  - id: REV-5-TASK6-HEADING
    decision: sửa heading `---### Task 6:` hỏng; scan toàn plan xác nhận Task 1–11
      mỗi task đúng một heading `### Task <n>:`.
    applied_to: ["W0 plan Task 6"]
    status: applied

  - id: REV-6-GATE-APPLICABILITY
    decision: thêm ma trận class-to-gate (9 gates × 4 class); skipped = verdict
      NOT_APPLICABLE tường minh do gate-check đọc CHANGE.yaml.class, không silent bypass;
      state transitions của phase bị bỏ được collapse để không deadlock.
    applied_to: ["Master Plan §22 Gate applicability", "§9 rule mới", "§6 pointer", "§30 criterion 24"]
    status: applied

  - id: REV-7-R3-MERGE-ORDER
    decision: PR sửa R3 chỉ tạo SAU khi PR W0 merge (ledger path phải tồn tại trên main);
      hai PR không merge-order independent.
    applied_to: ["Master Plan §5 note", "§26 W0 scope 9", "W0 plan Task 11 Step 1"]
    status: applied

  - id: REV-8-TRACEABILITY-ACCURACY
    decision: bỏ hard-coded count trong PR body ("26 decisions" → "toàn bộ decisions Rev 2");
      traceability cập nhật theo mọi correction ở trên.
    applied_to: ["PR #39 body", "file này"]
    status: applied
```

## Preserved unchanged from v1 (intent intact)

Goal (§1); Non-goals core list (§2); AD-1..AD-9 (§3, AD-4/AD-8/AD-9 amended only as Rev 2 requires); canonical workspace direction (§8); spec contract (§14); implementation-plan contract and anchor priority (§15); plan validation checks and verdicts (§16); dispatcher context isolation, file handoff, status contract, retry policy, abstract model tiers (§18); execution safety (§19); review loop (§20); write-gate check list (§21); command surface and approval gates (§23); OpenSpec migration mechanics (§24); skills migration strategy (§25); CI umbrella requirement (§28); glossary direction (§29); acceptance criteria 1–22 core (§30, wording of 2/5/19/21 adjusted); rollback strategy (§31).

## Deferred items and activation conditions

| Deferred mechanism | Activation condition | Ledger status |
|---|---|---|
| Parallel execution + file overlap detection + file locks/ownership | Recorded wall-clock need across ≥2 dogfood changes | deferred |
| Claim-level evidence hashing | Observed staleness false negative that file-level hashing missed | deferred |
| Cost/risk/data-sensitivity routing | Observed misrouting failure attributable to a missing dimension | deferred |
| Dashboard expansion | Dogfood-recorded observability deficiency | deferred |
| Specialized explorer subagents | Dogfood B records the five §10.1 signals | decision at W3 |
| `fix_dispatch` as distinct class | W2 review-loop hardening | scheduled (W2) |
| Model tiers per platform | W0 matrix proves model selection on that platform | matrix-bounded |
| Legacy runtime deletion | Post-W7, consumer-map verified | scheduled (post-W7) |
