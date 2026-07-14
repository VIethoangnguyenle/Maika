# Execution Errata — Maika Computational Harness Closure Plan

Status: ACTIVE — amends `upgrade/maika-computational-harness-closure-plan.md`
Date: 2026-07-14
Baseline verified: `1877a757fe1045a5f9b64bdede157e4f5f8a1d10` (master-v2)

Phản biện plan trước thực thi (đối chiếu source thật). Plan gốc là authority về
**mục tiêu và acceptance criteria**; errata này là authority về **cách thực thi**
khi plan xung đột với `.maika/DEVELOPMENT_RULES.md` hoặc với hiện trạng code.

## Xác nhận

- B1–B7 đều verified có thật tại baseline:
  - B1: `cli/agent_content/skill_contract.py` chỉ parse `capabilities.required`;
    `grounding-explorer`/`reviewing-change` require `semantic_code_search` +
    `dependency_analysis` cơ học.
  - B2: `gates.py` còn `_NODE_ID`/`_BLAST`/`_DEGRADE` regex, CBM node verification
    trong `validate_code_evidence`.
  - B3: `TOOL_HEALTH.yaml` worker-authored; không có invocation record.
  - B4: router `explore` gắn gate cứng `[query-plan, tool-health,
    exploration-evidence, coverage]`, không có DB gate/dispatch database-explorer.
  - B5: lanes chỉ nằm trong `provider-registry.yaml` (policy), không pin vào worker.
  - B6: capsule (`microloop-orchestrator/vnext_dispatch.py`) chưa pin provider
    policy/evidence hashes.
  - B7: BLOCKED state + failure_routes có, nhưng chưa có request/result artifact
    lifecycle + re-probe + resume redispatch.
- Hướng Maika-only, MCP = black box: đúng; gỡ dependency U1/D2 của plan cũ.

## Amendments (đánh số E1–E8)

### E1 — Gate mới chỉ cho artifact mới (R5/R7)

Plan §14 liệt kê 10 gate mới. Thực thi:

- Gate mới **chỉ** cho artifact mới: `trace-request`, `trace-evidence`,
  `provider-invocations`, `database-request`.
- `database-context-v2` = nâng cấp validator `database-context` hiện có (một
  đường enforcement cho một mối quan tâm).
- `context-package-freshness` = mở rộng `validate_context_package` /
  `validate_capsule_integrity` hiện có.
- `capability-requirements` + `conditional-provider-use` = rule bên trong
  skill-contract validator (CI-time) và trace-evidence validator (runtime),
  không phải gate tên riêng.
- Bộ đếm đúng: mối-quan-tâm → một chốt; không nhân bản.

### E2 — Enforcement ledger bắt buộc (R3)

Mọi enforcement mới phải có entry trong
`docs/refactor/maika-vnext/enforcement-ledger.yaml` cùng PR:

- B1–B7 + C-01..C-27 (inventory PR #56) = `observed_failure`.
- Fixtures F1–F14 khi đã dựng = `reproducible_litmus`.
- DB lane enforcement (M7) = `safety_boundary` (tiền lệ write-gate).

### E3 — Đồng bộ số slice + đóng dấu doc (R6)

- Inventory `docs/plans/provider-convergence-inventory.md` dùng số cũ
  (typed schema = M3-cũ) và trỏ governing plan đã xóa. PR M2 phải re-point
  governing plan sang plan mới + ghi bảng map số cũ→mới
  (M3-cũ→M2, M4-cũ→M4*, M5-cũ→M5/M6, M6-cũ→M3/M13-adapter, M7-cũ→M8,
  M8-cũ→M9, M9/M10-cũ→M10/M11 — chi tiết trong PR).
- Plan cũ (`maika-ua-db-access-provider-convergence-closure-plan.md`, errata cũ)
  đã xóa khỏi working tree — commit deletion trong PR M2.

### E4 — M11 thresholds: đo được gì thì claim cái đó

§23 thresholds (≥95% UA-selection…) là thống kê live-agent, không chứng minh
trong CI. M11 giao:

1. F1–F14 deterministic chạy trong CI (100% pass — đây là hard gate).
2. Cross-host equivalence ở mức scaffold/content qua snapshot tests
   (claude-code/codex/antigravity/generic).
3. H-run protocol + kết quả run thật qua worker (agy/codex) được ghi nhận
   dạng report; KHÔNG claim threshold thống kê khi số mẫu nhỏ.

### E5 — Một bề mặt phân loại persistence duy nhất

§10 `risk_signals` không được chồng lên `database_changed` /
`migration_required` / `transaction_changed` hiện có. M6 hợp nhất: booleans cũ
migrate vào `risk_signals` (hoặc ngược lại — chọn một), consumer migrate cùng
PR, không có hai nguồn phân loại.

### E6 — Giới hạn trung thực của adapter (black-box constraint)

UA tools phần lớn trả human text (chỉ `get_graph_metadata` structured). Adapter
Maika bảo đảm cơ học được:

- call-đã-xảy-ra (request/response hash), tool ∈ snapshot, lane hợp lệ,
  truncation marker, secret redaction, timestamp.

Adapter KHÔNG bảo đảm nội dung semantic của text response. TRACE_EVIDENCE
worker-authored phải bind từng traversal/claim vào invocation record qua
response hash; gate kiểm **linkage + coverage**, không kiểm chân lý nội dung.
Ngôn ngữ trong doc/gate message không được over-claim.

### E7 — Worker doctrine

§28 (Codex kickoff) không thực thi nguyên văn: codex = adversarial reviewer
(quota-prone), agy = executor cho phần nặng/mechanical, orchestrator implement
chính. Pre-flight `worker-health` trước khi giao; circuit breaker theo
`worker-state`.

### E8 — Legacy gate xóa ở M11, không xóa ở M5

M5 chuyển router + thêm typed gates; legacy validators (`knowledge-checkpoint`
node_id regex, `mcp-status`, CBM path trong `code-evidence`,
`implementation-context` UA marker) giữ nguyên tới M11, xóa sau khi F1–F14 xanh
(khớp inventory "remove in M10-cũ").

## Slice gate (giữ nguyên plan §25)

Mỗi PR: source note → implement một slice → targeted tests → mutation tests →
`python3 scripts/run_ci.py` xanh → behavior fixture liên quan → `git diff
--check` → clean tree → stop & report. Không gộp phase.
