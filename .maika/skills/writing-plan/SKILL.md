---
name: writing-plan
version: '1.0'
description: >
  Sinh IMPLEMENTATION_PLAN.md code-level cho một change vNext: frontmatter máy-đọc
  (base_commit, spec_hash, evidence_hash), mỗi task một section TASK-NNN với
  implementation_mode exact|guided|intent, files/symbols/anchors, TDD steps, commands
  + expected. Dùng khi: SPEC.md đã được duyệt và change ở state PLANNING (mọi class).
  KHÔNG dùng cho: brainstorm (W2), review plan (planning_dispatch đảm nhiệm),
  task legacy OpenSpec.
---

## Mục tiêu
Blueprint thực thi được: mọi task tự chứa, verbatim-compilable, đủ evidence.

## Khi nào sử dụng
SPEC.md đã được duyệt và change ở state PLANNING (mọi class).

## Khi nào KHÔNG sử dụng
brainstorm (W2), review plan (planning_dispatch đảm nhiệm), task legacy OpenSpec.

## Quy trình
Duyệt SPEC.md, tạo plan.


## Inputs
SPEC.md đã duyệt; codebase hiện tại (capability: exact_source_inspection,
dependency_analysis, architecture_discovery); conventions (convention_retrieval).

## Required outcomes
IMPLEMENTATION_PLAN.md đúng contract §15: frontmatter đầy đủ; task section
`### TASK-NNN: <title>` chứa ```yaml task:``` header (id, implementation_mode,
depends_on, files.create/modify/test, verification.command + expected) + thân
task TDD từng bước; không dùng placeholder chưa hoàn thiện; line numbers chỉ là hint (anchor > hash > line).

## Invariants
- Mọi file được task đụng phải khai trong files.*; symbol nêu trong plan phải tồn tại
  ở base_commit (runtime_verification trước khi ghi).
- Không paraphrase yêu cầu từ SPEC — trích nguyên văn AC vào từng task liên quan.

## Stop conditions
Thiếu SPEC duyệt / base_commit bẩn / mâu thuẫn SPEC↔code → dừng, báo NEEDS_CONTEXT.

## Output contract
Ghi IMPLEMENTATION_PLAN.md vào workspace change; chuyển state PLANNING→PLAN_REVIEW.

## Next handoff
planning_dispatch (independent plan review) → gate `plan` → compiler.
