---
name: architecture-reviewer
version: '1.1'
description: >
  Đối chiếu REQUIREMENT với kiến trúc + codebase thực tế (DB + code), phát hiện xung đột và rủi ro.
  Dùng khi cần đánh giá impact kiến trúc, phát hiện breaking changes, hoặc review contract design.
  KHÔNG dùng cho: chuẩn hoá yêu cầu (→ requirement-analyst),
  khám phá code chi tiết (→ codebase-explorer), validate spec đã sinh (→ spec-validator).
pre_conditions:
  - file: "{{ platform.framework_root }}/knowledge/active/REQUIREMENT.md"
    condition: not_skeleton
    on_fail: "ABORT — chạy requirement-analyst trước"
  - file: "{{ platform.framework_root }}/knowledge/active/EXPLORE_CONTEXT.md"
    condition: not_skeleton
    on_fail: "WARN — EXPLORE_CONTEXT thiếu, độ tin cậy kiến trúc sẽ là TRUNG BÌNH — cân nhắc chạy db-explorer / codebase-explorer trước"
  - file: "{{ platform.framework_root }}/knowledge/long-term/conventions.yaml"
    condition: exists
    on_fail: "WARN — conventions.yaml chưa có, đánh giá boundary không đầy đủ"
    load_scope: full  # override selective loading — arch-reviewer cần toàn bộ design_patterns
  - file: "{{ platform.framework_root }}/knowledge/long-term/author-dna.yaml"
    condition: exists
    on_fail: "WARN — author-dna.yaml chưa có, hard principles không được áp dụng"
    load_scope: hard_principles+complexity_thresholds  # pattern_preferences không cần ở Pha 1
---

# Architecture Reviewer — Đánh giá kiến trúc dựa trên trạng thái thực tế

## Mục tiêu

- Đối chiếu REQUIREMENT với kiến trúc hiện tại: service/module, DB, integration, boundary.
- Phát hiện xung đột kiến trúc, data risk, coupling, NFR risk.
- Ghi kết quả LOW / MEDIUM / HIGH / BLOCKER kèm Độ tin cậy.

Skill này không thiết kế kiến trúc mới từ đầu. Nó soi yêu cầu so với kiến trúc hiện hữu và nêu điểm cần xử lý trước khi spec/apply.

## Khi nào dùng

- REQUIREMENT.md đã tương đối ổn định.
- Đã có db-explorer/codebase-explorer hoặc limitation được ghi rõ.
- Trước OpenSpec `/opsx:propose` hoặc trước khi giao implementation.

## Khi nào KHÔNG sử dụng

- Không dùng như công cụ refactor code chi tiết.
- Không thay thế quyết định kiến trúc cấp tổ chức.
- Không dùng khi chưa có REQUIREMENT.md.
- Không dùng để validate spec đã sinh (→ spec-validator).

## Input / Output

Input chính:
- `{{ platform.framework_root }}/knowledge/active/REQUIREMENT.md`
- `{{ platform.framework_root }}/knowledge/active/EXPLORE_CONTEXT.md`
- `{{ platform.framework_root }}/knowledge/long-term/knowledge-snapshot.md`
- `{{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md`

Output: cập nhật `EXPLORE_CONTEXT.md` với section `### Đánh giá kiến trúc cho yêu cầu hiện tại (architecture-reviewer)`.

## Nguyên tắc Độ tin cậy

- UA + db-explorer + codebase-explorer đều chạy ổn → có thể CAO nếu evidence đủ.
- UA thiếu → tối đa TRUNG BÌNH cho topology/boundary.
- db-explorer thiếu → tối đa TRUNG BÌNH cho dữ liệu.
- Cả UA và db-explorer thiếu → không được đặt confidence CAO.

## UA-first invariant

Boundary/topology/cross-service/async conclusions must use Understand-Anything first:

- Run `{{ tools.domain_relationships }}` for ownership and cross-service dependency.
- Run `{{ tools.domain_flow }}` for REST/gRPC/Kafka/job topology.
- Use Codebase Memory only after UA locates the node/flow, to inspect source details.
- Use grep only as fallback. Codebase Memory failure does not mean UA is unavailable.

Read [references/ua-boundary-doctrine.md](references/ua-boundary-doctrine.md) before making topology, async, Kafka, gRPC, or cross-service conclusions.

## Quy trình mỏng

1. Check tool state and set confidence ceiling.
2. Summarize current architecture from REQUIREMENT, EXPLORE_CONTEXT, snapshot.
3. Compare As-is / To-be with current architecture.
4. Review boundary, ownership, topology, and coupling with UA-first.
5. Review data impact from db-explorer evidence.
6. Review NFR impact: performance, reliability, observability.
7. Write architecture assessment and suggested next action.

Read [references/review-flow-guide.md](references/review-flow-guide.md) when executing the full review flow.

## Optional checks

- Read [references/infra-tdd-trigger.md](references/infra-tdd-trigger.md) when review finds HIGH/BLOCKER infrastructure, platform, integration, DB, or contract impact.
- Read [references/contract-completeness-check.md](references/contract-completeness-check.md) when REQUIREMENT.md has a Technical Design Contract.
- Read [references/gotchas.md](references/gotchas.md) when confidence, conventions, contract, or upstream-library questions appear.
