# Contract DAG Check

> Tài liệu tham khảo cho `spec-validator`. Đọc khi validate microloop CONTRACT_DAG sau apply.

## Check

- Không còn node pending, in_progress, blocked, hoặc stale.
- File changed của node nằm trong writes list của node đó.
- Leaf node không ghi contract/base file.
- contract_ref version khớp current contract node.
- CONTEXT_REQUEST, CONTRACT_CHANGE_REQUEST, và INTEGRATION_REQUEST artifact đã resolved hoặc được log trong AGENT_TRANSPARENCY.
