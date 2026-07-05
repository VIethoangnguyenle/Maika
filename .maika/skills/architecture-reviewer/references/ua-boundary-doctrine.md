# UA Boundary Doctrine

> Tài liệu tham khảo cho `architecture-reviewer`. Read before making boundary, topology, async, Kafka, gRPC, or cross-service conclusions.

## Mục lục

- Doctrine
- Mapping câu hỏi sang tool
- Stale UA handling

## Doctrine

Câu hỏi xuyên-service hoặc async là UA-altitude. Kết luận topology/boundary luôn lấy từ Understand-Anything trước.

`{{ tools.find_blast_radius }}` và `{{ tools.get_dependencies }}` chỉ thấy method-call nội-service, không đủ để định hình Kafka/gRPC/cross-service topology.

## Mapping câu hỏi sang tool

| Câu hỏi | UA định hình kết luận | Codebase Memory hỗ trợ |
|---|---|---|
| Module sở hữu domain gì? | `{{ tools.domain_relationships }}` | `{{ tools.get_dependencies }}` check caller nội-service |
| Luồng sync/async? | `{{ tools.domain_flow }}` | `{{ tools.trace_flow }}` xác nhận logic nội-service |
| Coupling xuyên service? | `{{ tools.domain_relationships }}` | `{{ tools.find_blast_radius }}` cho blast nội-service |

## Stale UA handling

Khi codebase mâu thuẫn một code-fact UA claim, ghi vào `AGENT_TRANSPARENCY.md` rằng UA có thể stale ở điểm đó. Không tự override topology bằng grep.
