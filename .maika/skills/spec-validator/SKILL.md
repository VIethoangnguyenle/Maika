---
name: spec-validator
version: '1.1'
description: >
  Kiểm tra spec (OpenSpec artifacts) trước và sau khi apply — pre-apply gate, AC coverage check, post-apply verify.
  Dùng khi cần validate spec trước apply hoặc verify kết quả sau apply.
  KHÔNG dùng cho: sinh spec mới (→ openspec-propose),
  review kiến trúc (→ architecture-reviewer), chuẩn hoá yêu cầu (→ requirement-analyst).
pre_conditions:
  - file: "{{ platform.framework_root }}/knowledge/active/REQUIREMENT.md"
    condition: not_skeleton
    on_fail: "ABORT — không có REQUIREMENT để validate spec"
  - phase: pha-2
    condition: phase_done
    on_fail: "ABORT — spec chưa được sinh (phase_state chưa đạt phase-2-done)"
---

# Spec Validator — Kiểm tra Spec Trước và Sau Apply

## Mục tiêu

- Pre-apply gate: block apply khi spec có vấn đề nghiêm trọng.
- AC coverage: mỗi acceptance criterion trong REQUIREMENT nên được thể hiện trong tasks/spec.
- Integration coverage: mỗi integration mới nên có mapper/adapter/task coverage.
- Post-apply verify: changed files khớp với spec dự kiến.
- Contract DAG và DNA compliance check sau apply.

Skill này là quality gate. Không sinh spec, không sửa code.

## Khi nào dùng

- Trước `/task apply`.
- Sau `/task apply`.
- User yêu cầu validate spec.

## Khi nào KHÔNG sử dụng

- Cần sinh spec mới (→ openspec-propose).
- Cần architecture review (→ architecture-reviewer).
- Cần chuẩn hoá requirement (→ requirement-analyst).
- Thiếu REQUIREMENT.md (→ requirement-analyst trước).

## Command deterministic

Chạy AC coverage:

```bash
CHANGE_ID="${CHANGE_ID:?set CHANGE_ID to the OpenSpec change folder name}"
python3 {{ platform.framework_root }}/tools/gate-check/cli.py ac-coverage {{ platform.framework_root }}/knowledge/active/REQUIREMENT.md --against "openspec/changes/${CHANGE_ID}/tasks.md"
```

Chạy integration coverage:

```bash
CHANGE_ID="${CHANGE_ID:?set CHANGE_ID to the OpenSpec change folder name}"
python3 {{ platform.framework_root }}/tools/gate-check/cli.py integration-coverage {{ platform.framework_root }}/knowledge/active/REQUIREMENT.md --against "openspec/changes/${CHANGE_ID}/tasks.md"
```

Exit khác 0 nghĩa là hiển thị reason và hỏi user muốn amend spec hay tiếp tục.

## Gate list

1. Pre-apply gate.
2. AC coverage.
3. Integration coverage.
4. Contract DAG check.
5. Post-apply verify.
6. DNA compliance check.

Đọc [references/pre-apply-gate.md](references/pre-apply-gate.md) trước apply.
Đọc [references/coverage-checks.md](references/coverage-checks.md) khi check AC hoặc integration coverage.
Đọc [references/contract-dag-check.md](references/contract-dag-check.md) khi validate CONTRACT_DAG.
Đọc [references/post-apply-checks.md](references/post-apply-checks.md) sau apply.
Đọc [references/dna-compliance-check.md](references/dna-compliance-check.md) cho semantic DNA compliance.
Đọc [references/gotchas.md](references/gotchas.md) cho edge case.

## Cập nhật AGENT_TRANSPARENCY

Ghi:
- `[x] spec-validator: pre_apply_gate — {PASS|BLOCK}`
- `[x] spec-validator: ac_coverage — {n}/{n} covered`
- `[x] spec-validator: integration_coverage — {n}/{n} covered`
- `[x] spec-validator: contract_dag_check — {PASS|BLOCK}`
- `[x] spec-validator: post_apply_verify — {OK|issues}`
