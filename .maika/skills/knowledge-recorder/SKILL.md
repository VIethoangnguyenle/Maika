---
name: knowledge-recorder
version: '1.0'
description: 'Dùng trong change khi có discovery, teaching moment hoặc convention gap:
  capture CANDIDATE vào changes/<id>/learning/ (TEACHING_MOMENTS.yaml,
  KNOWLEDGE_CANDIDATES.yaml, CONVENTION_CANDIDATES.yaml) với user-confirm và provenance —
  không bao giờ ghi trực tiếp vào durable knowledge trước VERIFIED.'
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
outputs:
  required:
  - learning/
gates:
- teaching-moment
---
# Knowledge Recorder

## Mục tiêu
Capture candidate tri thức NGAY khi nó xuất hiện trong change — teaching moment,
discovery, convention gap — vào `changes/<id>/learning/`, giữ provenance, chờ
promotion sau VERIFIED.

## Khi nào sử dụng
- User correction kèm nguyên tắc kỹ thuật (teaching moment — R-DNA-7).
- Discovery material trong implementation/review (candidate cho durable knowledge).
- Convention gap lộ ra khi review.

## Khi nào KHÔNG sử dụng
- Để GHI durable knowledge (promote là việc của `knowledge-promoter`, sau VERIFIED).
- Quan sát one-off không có evidence.

## Đầu vào
- User correction / review finding / discovery + source anchor.

## Câu hỏi tri thức
- Bài học còn đúng khi bỏ tên cụ thể? (abstraction split R-DNA-7 Bước 0)
- Candidate trùng entry durable nào đang có? (ghi supersede-candidate thay vì bản sao)

## Loại evidence bắt buộc
- `exact_code_fact` (anchor), user confirmation (teaching moment).

## Chính sách capability
Capability IDs: `convention_retrieval` (đối chiếu entry hiện có),
`exact_source_inspection` (anchor).

## Quy trình truy xuất
1. Phân tách abstraction level (author-dna / conventions / knowledge-snapshot).
2. Đối chiếu candidate với durable entry hiện có.

## Thứ tự authority và precedence
Candidate KHÔNG phải knowledge — nó chờ verification; không được cite làm authority.

## Kết quả bắt buộc
- Record trong `learning/TEACHING_MOMENTS.yaml` / `KNOWLEDGE_CANDIDATES.yaml` /
  `CONVENTION_CANDIDATES.yaml` gồm: id, statement, target (dna/convention/snapshot),
  evidence anchor, `user_confirmed: true|false`, status
  `confirmed-pending-verification` | `declined`, provenance (change_id, date).
- Teaching moment: hỏi user confirm NGAY trong phiên (không defer).

## Bất biến
- KHÔNG ghi vào `knowledge/long-term/` — write gate + role boundary chặn.
- User từ chối → status `declined` + WARN vào `reviews/SKILL_FEEDBACK.yaml`.
- Direct user directive vẫn phải có record + provenance (không bypass).

## Yêu cầu evidence
Mỗi candidate cite source anchor hoặc user statement nguyên văn.

## Freshness và confidence
Candidate ghi repository_commit tại thời điểm capture.

## Quy trình degradation
Không áp dụng — capture là thao tác file local trong workspace.

## Quy trình
1. Nhận signal (correction/discovery/gap).
2. Abstraction split (Bước 0 R-DNA-7); hỏi user confirm khi là teaching moment.
3. Ghi record vào `learning/`; gate `teaching-moment` validate cấu trúc.

## Điều kiện dừng
- User từ chối confirm (ghi declined rồi dừng).
- Candidate không có evidence anchor.

## Tác động lên knowledge
Chỉ tạo CANDIDATE trong workspace; durable knowledge không đổi cho tới khi
`knowledge-promoter` chạy sau VERIFIED.

## Đầu ra
`changes/<id>/learning/*.yaml` records.

## Handoff tiếp theo
`knowledge-promoter` (tại action `archive`, sau VERIFIED).
