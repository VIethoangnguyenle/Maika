---
name: author-dna-builder
version: '3.0'
description: 'Dùng khi review lặp lại một triết lý kỹ thuật hoặc user xác nhận nguyên
  tắc định hướng: quản lý candidate lifecycle của Author DNA với confidence, provenance,
  positive/counterexample, scope, enforcement mapping, supersession và consumer list.'
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
  - convention_retrieval
  - exact_source_inspection
  - historical_context_retrieval
outputs:
  required:
  - knowledge/long-term/author-dna.yaml
gates:
- teaching-moment
---
# Author DNA Builder

## Mục tiêu
Nắm bắt triết lý tác giả bền vững (thinking lens) ảnh hưởng phán đoán kỹ thuật, quản lý
theo candidate lifecycle với đủ metadata để planning/review áp dụng và enforce.

## Khi nào sử dụng
Dùng khi onboarding, khi review finding lặp lại, hoặc khi user xác nhận một triết lý
định hướng change tương lai.

## Khi nào KHÔNG sử dụng
- Bài học là convention cụ thể (đưa sang convention-intelligence-builder).
- Preference one-off chưa lặp lại.

## Đầu vào
- `knowledge/long-term/author-dna.yaml` hiện có.
- Verified example từ source/review; teaching moment đã confirm.

## Câu hỏi tri thức
- Nguyên tắc còn đúng khi bỏ hết tên cụ thể (table/class/method) không? (thinking lens)
- Có positive example + counterexample từ source không?
- Nguyên tắc mechanically checkable (map sang enforcement) không?

## Loại evidence bắt buộc
- `author_dna_rule` (entry hiện có), `exact_code_fact` (positive/counterexample).
- `review_pattern` (finding lặp lại).

## Chính sách capability
Capability IDs: `exact_source_inspection`, `convention_retrieval`,
  `historical_context_retrieval`.
Không suy diễn triết lý chỉ từ code; cần user confirm.

## Quy trình truy xuất
1. Thu candidate principle từ teaching moment/review lặp lại.
2. Tách philosophy khỏi convention (bỏ tên cụ thể còn đúng → DNA).

## Thứ tự authority và precedence
user confirmation > review pattern lặp lại > source example > inference. DNA chưa
confirm không được enforce.

## Kết quả bắt buộc
Entry Author DNA với: candidate lifecycle (candidate→confirmed→superseded), confidence,
provenance, positive examples, counterexamples, scope, enforcement mapping (ir_rule nếu
checkable), supersession, consumer list.

## Bất biến
- Không suy diễn triết lý chỉ từ code.
- Không trùng lặp convention cụ thể.
- Không thêm preference one-off.

## Yêu cầu evidence
Entry confirmed cite user confirmation + ≥1 source/review example khi có. Entry
checkable ghi `mechanically_checkable: true` + `check_spec`.

## Freshness và confidence
Ghi confidence + `source: author-described (<date>)`. Entry cũ bị thay ghi `superseded_by`.

## Quy trình degradation
Chưa có confirm của user → giữ ở `candidate`, không enforce; ghi WARN để nhắc capture
sau (R-DNA-7).

## Quy trình
1. Thu candidate + tách philosophy/convention.
2. Xin confirm khi cần.
3. Ghi/cập nhật `author-dna.yaml` (đủ metadata).
4. Regenerate knowledge index; emit ruleset nếu checkable.

## Điều kiện dừng
- Nguyên tắc không lặp lại.
- User chưa confirm claim philosophy.
- Entry thuộc về conventions.

## Tác động lên knowledge
Author DNA là judgment layer, consumer là planning/review; enforce qua rule-projector
khi checkable.

## Đầu ra
`knowledge/long-term/author-dna.yaml` + thay đổi index.

## Handoff tiếp theo
`convention-intelligence-builder` khi phát hiện convention cụ thể.
