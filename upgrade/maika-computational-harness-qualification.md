# Computational Harness — Qualification & Closure Report (M11)

Status: PROGRAM CLOSED — 2026-07-14
Governing plan: `upgrade/maika-computational-harness-closure-plan.md`
Execution errata: `upgrade/maika-computational-harness-execution-errata.md`
Slices: M2 (#57), M3 (#58), M4 (#59), M5 (#60), M6 (#61), M7 (#62), M8 (#63),
M9 (#64), M10 (#65), M11 (this PR). Baseline `1877a75` (M1 = PR #56).

## 1. Deterministic fixtures (plan §22) → tests

| Fixture | Test |
|---|---|
| F1 fresh complete UA path, no CBM → PASS | `test_trace_gates.py::test_trace_evidence_valid_chain` |
| F2 ambiguous anchor → CBM anchor → UA trace → PASS | `test_trace_gates.py::test_support_call_with_declared_trigger_passes` |
| F3 graph gap → CBM support → source resolve → PASS | F2 test + `source_verifications` trong valid chain |
| F4 hidden consumer review → CBM counter-evidence | reviewer conditional triggers (`test_structured_trace_skills.py::test_reviewers_hold_only_neutral_required_capabilities`) |
| F5 unnecessary CBM call → FAIL | `test_support_call_without_trigger_fails`, `test_support_call_non_conditional_capability_fails` |
| F6 fake provider health → FAIL | `test_hand_written_graph_without_probe_observation_fails` |
| F7 non-persistence task → no DB route | `test_trace_compiler.py::test_derive_persistence_signal_*` (neutral case) + e2e standard flow |
| F8 persistence task → DB context mandatory | e2e `test_persistence_change_cannot_pass_reasoning_without_database_context` |
| F9 DB unavailable → structured degradation | `test_database_context_degraded_ok_without_probe` |
| F10 DB write leak → FAIL | `test_lane_write_tool_always_fails`, `test_cli_db_write_tool_rejected` |
| F11 runtime data question → data-probe allowed | `test_lane_data_probe_allowed_when_declared`, `test_cli_db_data_probe_requires_declared_need` |
| F12 wrong environment → FAIL | `test_wrong_environment_evidence_rejected` |
| F13 UA refresh → BLOCKED → new evidence → resume | `test_refresh_resume.py::test_fulfill_with_new_evidence_resumes_original_role` |
| F14 `request_only: []` stays empty | `test_refresh_resume.py::test_explicit_empty_request_only_stays_empty` |

## 2. Mutation suite (plan §21) → tests

| # | Mutation | Pinned by |
|---|---|---|
| 1 | CBM semantic search back to required | `test_cbm_capabilities_never_return_to_required` (M2) |
| 2 | reviewer calls CBM without trigger | `test_support_call_without_trigger_fails` (M4) |
| 3 | UA trace has no provider invocation | `test_observation_without_invocation_record_fails` (M4) |
| 4 | fresh-graph claim without response hash | `test_hand_written_graph_without_probe_observation_fails` (M5) |
| 5 | persistence task lacks DATABASE_CONTEXT | e2e persistence test (M10) |
| 6 | Database Explorer calls `sql_read` | `test_lane_data_probe_use_without_declared_need_fails` (M7) |
| 7 | Database Explorer calls write/script | `test_lane_write_tool_always_fails` (M7) |
| 8 | DB context omits environment | `test_database_request_missing_environment_fails`, `test_database_context_probe_missing_environment_fails` (M6) |
| 9 | drift unclassified | `test_database_context_unclassified_drift_fails` (M6) |
| 10 | worker prompt lacks skill hash | `test_control_surfaces_pin_skill_and_registry_hashes` (M8) |
| 11 | provider registry changes after ack | `test_stale_ack_rejected_after_provider_registry_change` (M10) |
| 12 | workflow request does not enter BLOCKED | `test_workflow_request_enters_durable_blocked` (M9) |
| 13 | refresh fulfilled without new evidence | `test_fulfill_refuses_without_new_evidence` (M9) |
| 14 | explicit empty request_only gets defaults | `test_explicit_empty_request_only_stays_empty` (M9) |
| 15 | gate demands provider-specific prose | `test_legacy_provider_prose_gates_removed` (M11) |
| 16 | unknown provider tool appears | `test_tool_outside_tested_snapshot_fails` (M3) |
| 17 | truncated response claims complete | `test_truncated_observation_cannot_claim_complete` (M4) |
| 18 | source verification hash missing/stale | `test_source_verification_hash_mismatch_fails` (M4) |
| 19 | context package uses stale evidence | pre-existing `test_capsule_freshness_matches_evidence` (capsule-integrity) |
| 20 | cross-host snapshot diverges | pre-existing `test_snapshots.py` (4 platform golden trees) |

## 3. Legacy removal (M11)

Removed validators + regexes + CLI wiring + CBM probe helper:
`knowledge-checkpoint` (graph-node/blast prose), `mcp-status` (probe-number
regex), `implementation-context` (UA markers), `code-evidence` (CBM node
verification, `capability.py` probe). Ledger ENF-001/005/007/009 stamped
`removed` với successor (ENF-029/030/033). Procedures (`decision-gate.md`,
`bootstrap.md`) + doctrine (`jit/providers.md` R-Tool-4/R-Tool-5) trỏ sang
typed gates. `db-remote`/`db_query` đã gỡ từ M1 (PR #56).

## 4. Cross-host qualification (errata E4 — claim đúng phạm vi đo được)

**Mechanically proven in CI (hard gates, 100%):**
- Fixtures F1–F14 + mutations #1–#20: pass (full CI exit 0).
- Scaffold equivalence Claude Code / Codex / Antigravity / Generic: golden
  tree snapshots (`test_snapshots.py`) — cùng contracts, registry, tools,
  gates ship tới cả 4 host.
- Gates/orchestrator/CLI là Python host-độc-lập: cùng input → cùng verdict
  trên mọi host (deterministic, không phụ thuộc agent).

**Live agent-behavior evidence (small-N, không claim threshold thống kê):**
- H-run C-1 (ngac, 2026-07-12, Antigravity qua agy): flow init→grounding PASS;
  R-Tool-7 degradation chuẩn; gates bắt schema drift → remediation xanh.
  Finding từ run đó (SKILL.md thiếu schema mẫu) đã fix và nay được pin bằng
  `test_skill_schema_examples.py` (mở rộng cho DATABASE_CONTEXT v2 ở M6).

**§23 thresholds (UA-selection ≥95%, unnecessary-CBM ≤5%, …):** đây là metric
hành vi live-agent. Cơ chế đo đã sẵn: `PROVIDER_INVOCATIONS.jsonl` +
`DISPATCH_LOG.jsonl` (provider_calls, gate_results, trigger/reason per call)
cho phép tính các tỉ lệ này trên mỗi run thật. Chưa đủ số run để claim con số
— threshold được ghi nhận là **operational SLO đo qua H-run**, không phải
kết quả đã chứng minh. Protocol H-run: init project trên host đích →
`maika task start/explore` → đọc PROVIDER_INVOCATIONS + DISPATCH_LOG +
EXPLORATION_VALIDATION → tính selection/necessity rates.

## 5. Acceptance criteria (plan §26)

1–28: SATISFIED — mapped ở §1/§2 trên (schema M2; invocation evidence M3;
trace M4/M5; persistence M6; lanes M7; pinning M8; refresh M9; observability
+ system-model M10; legacy removal + prose-free gates M11; fixtures + mutations
pass trong CI).
29 (Claude/Codex/Antigravity qualification): SATISFIED ở mức cơ học (snapshot
+ deterministic suite trên cả 4 platform scaffold) + evidence H-run nhỏ; live
threshold theo §4 là SLO vận hành, không phải claim.
30 (no Critical/High integration findings): các contradiction C-01..C-27 thuộc
Maika-scope đều có slice đóng (xem inventory register); C-03..C-18/D-slice và
U-slice nằm ngoài scope Maika-only (MCP là black box — errata E3).

## 6. Definition of Done (plan §27)

| DoD | Cơ chế |
|---|---|
| UA mechanically primary for structured trace | one_of `structured_trace` + trace-evidence coverage + registry primary mapping |
| CBM mechanically conditional | conditional triggers (M2) + support-call gate (M4); mutation #1/#2 |
| current source mechanically authoritative | `verify-source` hash + gate re-hash (M4) |
| provider health backed by invocation evidence | graph↔probe hash bind (M5) + provider-invocations (M3) |
| Database Explorer mechanically required by persistence risk | recorded risk signal → mandatory DB gates (M6); mutation #5 |
| Database Explorer mechanically limited to DB lane | 3-point lane enforcement (M7); mutations #6/#7 |
| worker control surfaces content-addressed | control_surfaces_block mọi dispatch (M8); mutation #10 |
| provider-specific gates removed | M11; mutation #15 |
| refresh/re-probe resumable | durable BLOCKED + new-evidence fulfillment (M9) |
| cross-host behavior qualified | §4 trên (honest scope per E4) |
