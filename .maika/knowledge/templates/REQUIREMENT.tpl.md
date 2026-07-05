# REQUIREMENT.md — Template
> Ticket: <!-- ticket-id -->
> Loại: <!-- feature | fixbug | changerequest | refactor -->
> Ngày tạo: <!-- date -->
> Tài liệu liên kết: <!-- URL hoặc tên doc -->

<!-- TODO: fill in — file này là template skeleton, không phải context thực -->

---

## Business Context & Động lực

<!-- Ai gặp vấn đề, vấn đề gì, tại sao phải giải quyết -->

---

## As-is / To-be

### As-is (Hiện tại)

<!-- Hành vi/flow hiện tại -->

### To-be (Mong muốn)

<!-- Hành vi/flow sau khi thực hiện task -->

---

## Flow / State Diagram

<!-- Bắt buộc khi task có flow, state, integration, callback, job, hoặc data path. -->
<!-- Nếu task đơn giản không có sequence/boundary đáng kể: ghi "Không cần diagram — task không có flow/state/data path đáng kể". -->

```text
<!-- ASCII diagram: actor/system -> step/state -> boundary -> result -->
```

---

## Scope

### In-scope

- <!-- item 1 -->

### Out-of-scope

- <!-- item 1 -->

---

## Acceptance Criteria

- [ ] <!-- AC 1: điều kiện + hành vi + kết quả quan sát được -->

---

## Technical Design Contract (Đầu ra cho Client)

### Giao thức & Giao diện (REST / gRPC / Kafka)
- <!-- Loại giao thức, endpoint, method, format... -->

### Request / Message Schema
- <!-- Cấu trúc dữ liệu đầu vào (Payload, Params, Headers) -->

### Response / Event Schema
- <!-- Cấu trúc dữ liệu đầu ra, HTTP Status, Mã lỗi (Error Codes) -->

---

## Integrations & Field Mapping

<!-- Một block cho mỗi integration mới (third-party API hệ thống cần gọi/nhận). -->
<!-- Nếu task không có integration mới: ghi "Không phát hiện integration mới". -->

### Integration: <!-- tên -->

- Hướng: <!-- outbound (hệ thống gọi third-party) / inbound (third-party gọi hệ thống) -->
- Protocol & Auth: <!-- REST/gRPC/SOAP/… + cơ chế auth -->
- Endpoint/Operation liên quan: <!-- ... -->
- Tài liệu nguồn: <!-- link doc / API spec -->

| Field third-party | Field canonical (hệ thống) | Transform / Serialize (ý định) | Nguồn |
|---|---|---|---|
| <!-- mobileNo --> | <!-- phoneNumber --> | <!-- rename khi (de)serialize --> | <!-- doc §x + UA: DTO --> |

- Field chưa map được: <!-- field — lý do; mirror vào "Vấn đề yêu cầu" -->

---

## Giả định (Assumptions)

- <!-- assumption 1 -->

---

## Vấn đề yêu cầu (Open Questions)

- <!-- question 1 -->

---

## Ghi chú từ ticket

<!-- Raw text quan trọng từ ticket gốc để trace -->
