---
name: convention-intelligence-builder
version: '3.0'
description: 'Dùng khi onboarding, sau refactor lớn, hoặc khi review lộ convention
  gap: trích convention cụ thể (naming/structure/testing/boundary) từ verified source
  với evidence threshold, examples/counterexamples, applies-to tags, scope matcher,
  enforcement type.'
routing:
  mode: conditional
  states: []
  classes:
  - trivial
  - small
  - standard
  - architectural
capabilities:
  required:
  - architecture_discovery
  - dependency_analysis
  - exact_source_inspection
outputs:
  required:
  - knowledge/long-term/conventions.yaml
---
# Convention Intelligence Builder

## Mục tiêu
Nắm bắt convention cụ thể (WHAT — structural rule) mà planner/reviewer áp được, với đủ
metadata để scope-match và enforce.

## Khi nào sử dụng
Dùng khi onboarding, sau refactor lớn, hoặc khi review finding lặp lại lộ convention gap.

## Khi nào KHÔNG sử dụng
- Bài học là triết lý (đưa sang author-dna-builder).
- Chỉ một example tình cờ, chưa đủ threshold.

## Đầu vào
- Current source + tests.
- `knowledge/long-term/conventions.yaml` hiện có.

## Câu hỏi tri thức
- Pattern naming/structure/testing/boundary nào lặp lại đủ threshold?
- Có counterexample nào phá pattern không? Convention hiện có đã cover chưa?

## Loại evidence bắt buộc
- `convention_rule` (entry hiện có), `exact_code_fact` (examples + counterexamples).
- `code_graph_edge`/`dependency_path` (boundary pattern).

## Chính sách capability
Capability IDs: `exact_source_inspection`, `architecture_discovery`,
  `dependency_analysis`.
Convention dẫn từ verified source, không hard-code provider behavior.

## Quy trình truy xuất
1. Inspect source pattern; nhóm pattern lặp lại.
2. Tách convention (structural) khỏi Author DNA (philosophy).

## Thứ tự authority và precedence
current source > review pattern lặp lại > inference. Convention từ một example đơn lẻ
không được lưu.

## Kết quả bắt buộc
Entry convention với: evidence threshold (số lần lặp), examples + counterexamples,
applies-to tags, scope matcher, conflict handling, enforcement type, supersession,
consumer list.

## Bất biến
- Không lưu triết lý ở đây.
- Không thêm convention từ một example tình cờ.
- Không hard-code provider behavior.

## Yêu cầu evidence
Mỗi convention cite verified source example + counterexample khi có. Threshold ghi rõ.

## Freshness và confidence
Ghi provenance + `applies_to`. Convention cũ bị thay ghi `superseded_by`.

## Quy trình degradation
Evidence quá thưa (dưới threshold) → giữ ở `candidate`, không enforce; ghi lý do.

## Quy trình
1. Inspect + nhóm pattern; kiểm threshold.
2. Tách convention/DNA.
3. Ghi `conventions.yaml` (đủ metadata).
4. Regenerate knowledge index.

## Điều kiện dừng
- Evidence quá thưa.
- Pattern là philosophical, không cụ thể.
- Convention hiện có đã cover.

## Tác động lên knowledge
Conventions là structural layer, consumer là grounding-explorer + validating-plan; enforce
qua rule-projector khi checkable.

## Đầu ra
`knowledge/long-term/conventions.yaml` + thay đổi index.

## Handoff tiếp theo
`grounding-explorer` và `validating-plan` tiêu thụ conventions.
