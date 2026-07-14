---
name: infra-tdd
version: '3.0'
description: 'Dùng khi CHANGE.yaml class architectural và change cần operational architecture:
  thu infra evidence (K8s topology, deployment manifest, service graph, Kafka topic/group,
  DB capacity/index, log/metric, incident memory, rollout/rollback command).'
routing:
  mode: conditional
  states: []
  classes:
  - architectural
capabilities:
  required:
  - architecture_discovery
  - database_schema_inspection
  - dependency_analysis
  - historical_context_retrieval
  - runtime_verification
---
# Infra TDD

## Mục tiêu
Sinh technical design document cho change infrastructure với evidence vận hành thật,
decision record, verification strategy và rollback.

## Khi nào sử dụng
Dùng khi `CHANGE.yaml` class là `architectural` và spec cần operational architecture,
migration, rollback, hoặc tradeoff hạ tầng.

## Khi nào KHÔNG sử dụng
- Change không chạm hạ tầng vận hành.
- Để thay `SPEC.md` hoặc để implement trực tiếp.

## Đầu vào
- `INTENT.md`, `GROUNDING.yaml`, `RECONCILIATION.md`.
- Manifest hạ tầng, service graph, cấu hình runtime (nếu có).

## Câu hỏi tri thức
- Topology K8s / service graph / Kafka topic-group hiện tại ra sao?
- DB capacity/index đủ cho thay đổi không? Incident vận hành liên quan?
- Rollout/rollback command cụ thể là gì?

## Loại evidence bắt buộc
- `architecture_node`, `relationship_edge` (service graph, topology).
- `database_object`, `database_index` (capacity/index).
- `incident_reference` (incident vận hành), `runtime_probe` (log/metric).

## Chính sách capability
Capability IDs: `architecture_discovery`, `dependency_analysis`,
  `database_schema_inspection`, `runtime_verification`, `historical_context_retrieval`.
Quyết định hạ tầng dựa evidence vận hành thật, không suy đoán topology.

## Quy trình truy xuất
1. Thu topology/service graph/Kafka/DB capacity từ manifest + graph.
2. Recall incident vận hành liên quan; thu log/metric baseline.

## Thứ tự authority và precedence
live runtime/DB state > manifest hiện tại > durable knowledge > memory > inference.
Topology suy đoán không được dùng làm decision.

## Kết quả bắt buộc
TDD gồm: context, strategy, architecture (topology/service graph/Kafka/DB), decision
record (ADR), verification strategy (operational), migration, rollback + rollout/rollback
command cụ thể.

## Bất biến
- Không thay `SPEC.md`.
- Không bỏ security/migration/rollback/operations cho architectural change.
- Không implement trực tiếp từ design.

## Yêu cầu evidence
Quyết định architecture cite grounding claim + source anchor + operational constraint
(capacity/index/topic). ADR ghi alternatives + lý do.

## Freshness và confidence
Ghi thời điểm thu metric/topology. Capacity/index dựa live probe là fresh nhất.

## Quy trình degradation
Không probe được runtime (không có cluster/DB) → ghi degradation + dùng manifest
declared làm fallback; hạ confidence; đánh dấu quyết định cần verify khi có môi trường.

## Quy trình
1. Đọc grounded artifacts + thu infra evidence.
2. Xác định architecture decision + ADR.
3. Viết TDD + verification/rollback strategy.
4. Đẩy quyết định về `writing-spec`.

## Điều kiện dừng
- Operational evidence bắt buộc thiếu.
- Quyết định migration/rollback cần user duyệt.
- Security impact chưa resolve.

## Tác động lên knowledge
ADR + operational lesson được đề xuất lưu (Agent Memory + knowledge-snapshot) qua curator.

## Đầu ra
TDD dưới docs dự án + danh sách evidence reference.

## Handoff tiếp theo
`writing-spec`.
