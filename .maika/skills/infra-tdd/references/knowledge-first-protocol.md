# Knowledge-First Protocol — BẮT BUỘC

> Tài liệu tham khảo cho skill `infra-tdd`. Load trước khi viết từng tầng hoặc khi MCP tool không khả dụng.

## Mục lục

- Knowledge-First Protocol — BẮT BUỘC

---

## Knowledge-First Protocol — BẮT BUỘC

> ⚠️ **KHÔNG ĐƯỢC viết bất kỳ section TDD nào khi chưa chạy knowledge tools tương ứng.**
> Mọi claim trong TDD phải dựa trên evidence thực tế từ codebase, database, hoặc knowledge graph — không phải suy đoán.

### Trước khi viết mỗi tầng, agent PHẢI thực hiện:

#### T0 — Bối cảnh Nghiệp vụ
```
PHẢI ĐỌC: Tài liệu nghiệp vụ gốc (SRS, BRD, Confluence) nếu có
PHẢI GỌI: {{ tools.get_symbol }} → hiểu business domain và layer boundaries
PHẢI GỌI: {{ tools.trace_flow }} → guided walkthrough để hiểu flow end-to-end
NẾU CÓ: User story, use case diagram → trích xuất business rules
QUY TẮC: KHÔNG dùng thuật ngữ kỹ thuật — viết cho người không biết code đọc
```

#### T1 — Chiến lược
```
PHẢI ĐỌC: {{ platform.framework_root }}/knowledge/long-term/knowledge-snapshot.md
PHẢI GỌI: codebase-explorer → map module liên quan trong hệ thống
PHẢI GỌI: {{ tools.search_code }} → tìm component hiện tại và pain points
NẾU CÓ: Tài liệu/ticket/operational evidence → spec-extract hoặc đọc trực tiếp
```

#### T2 — Kiến trúc
```
PHẢI GỌI: {{ tools.get_dependencies }} → dependency map giữa components
PHẢI GỌI: {{ tools.trace_flow }} → call flow thực tế
PHẢI GỌI: {{ tools.search_code }} → tìm implementation patterns
PHẢI GỌI: {{ tools.get_dependencies }} → dependency graph
PHẢI GỌI: db_access (db-explorer) → schema, constraints, indexes liên quan
KẾT QUẢ: Mọi sơ đồ phải phản ánh code/DB thực tế, không phải giả định
```

#### T3 — Quyết định
```
PHẢI GỌI: {{ tools.find_blast_radius }} → blast radius của mỗi alternative
PHẢI GỌI: {{ tools.find_blast_radius }} → files/modules bị ảnh hưởng
PHẢI GỌI: db_access (db-explorer) → data model constraints ảnh hưởng lựa chọn
PHẢI CHẠY: Socratic deep-dive protocol (references/socratic-deep-dive.md)
KẾT QUẢ: Mỗi ADR phải có evidence từ codebase, không chỉ opinion
```

#### T4 — Vận hành
```
PHẢI GỌI: codebase-explorer → tìm monitoring metrics, alert patterns hiện có
PHẢI GỌI: {{ tools.search_code }} → tìm existing metric/alert/config patterns
KẾT QUẢ: T4 chỉ chứa Monitoring Metrics table + Configuration Reference
KHÔNG VIẾT: Troubleshooting Runbook — tài liệu này dành cho management, không phải SRE ops
```

### Graceful Degradation

Nếu một MCP tool không khả dụng:
- **Ghi rõ** trong TDD section: "⚠️ [tool] không khả dụng — section này dựa trên [source thay thế]"
- **Hạ độ tin cậy** của section đó
- **KHÔNG block** — tiếp tục với evidence có sẵn, nhưng phải thành thật về gaps
