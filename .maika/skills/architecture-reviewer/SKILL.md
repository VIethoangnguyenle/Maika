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

## 1. Mục tiêu

- Đánh giá **mức độ phù hợp** giữa yêu cầu (REQUIREMENT) và kiến trúc hiện tại (service/module, DB, integration).
- Phát hiện sớm:
  - Xung đột kiến trúc (vi phạm boundary, ownership, layering…).
  - Rủi ro về dữ liệu, coupling, non-functional (hiệu năng, độ tin cậy, bảo trì…).
- Ghi lại kết quả theo mức độ **LOW / MEDIUM / HIGH / BLOCKER** kèm **Độ tin cậy** dựa trên trạng thái UA/db-explorer/codebase-explorer.

Skill này **không thiết kế kiến trúc mới từ đầu**, mà tập trung “soi” yêu cầu so với kiến trúc hiện hữu và nêu ra điểm cần chú ý.

---

## 2. Khi nào dùng

Kích hoạt `architecture-reviewer` khi:

- `REQUIREMENT.md` đã tương đối ổn định (đã qua `requirement-analyst`).
- Đã có ít nhất một vòng:
  - `db-explorer` cho phần dữ liệu liên quan (nếu có thể).
  - `codebase-explorer` cho khu vực code liên quan (nếu có thể).
- Trước khi:
  - Dùng OpenSpec `/opsx:propose` để viết spec chi tiết.
  - Giao task cho implementation (dev/agent bắt đầu chỉnh code).

---

## Khi nào KHÔNG sử dụng

- Như công cụ refactor code chi tiết — dùng codebase-explorer hoặc apply trực tiếp.
- Để thay thế quyết định kiến trúc cấp tổ chức (EA, tiêu chuẩn global).
- Khi chưa có REQUIREMENT.md — chạy requirement-analyst trước.
- Khi chỉ cần khám phá code/module chi tiết (→ codebase-explorer).
- Khi cần validate spec đã sinh (→ spec-validator).

---

## 3. Input

- `{{ platform.framework_root }}/knowledge/active/REQUIREMENT.md`:
  - Business context, As-is / To-be, Scope, AC.
- `{{ platform.framework_root }}/knowledge/active/EXPLORE_CONTEXT.md`:
  - Thông tin từ `db-explorer` (tầng database).
  - Thông tin từ `codebase-explorer` (tầng code, module, entrypoint).
  - Các ghi chú kiến trúc hiện có (nếu đã được cập nhật trước đó).
- `{{ platform.framework_root }}/knowledge/long-term/knowledge-snapshot.md` (nếu có):
  - Bức tranh tổng thể kiến trúc hệ thống, các hệ thống phụ thuộc.
- `{{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md`:
  - Trạng thái tool/skill đã chạy:
    - UA (`/understand`, `/understand-chat`).
    - `db-explorer`.
    - `codebase-explorer`.
  - Cảnh báo/hạn chế truy cập trước đó.

---

## 4. Output

Cập nhật `{{ platform.framework_root }}/knowledge/active/EXPLORE_CONTEXT.md` với section:

```md
### Đánh giá kiến trúc cho yêu cầu hiện tại (architecture-reviewer)

#### Tóm tắt bối cảnh kiến trúc liên quan
- ...

#### Điểm phù hợp (alignment)
- ...

#### Điểm xung đột / rủi ro
- ...

#### Mức độ nghiêm trọng
- LOW / MEDIUM / HIGH / BLOCKER (theo từng hạng mục chính)

#### Gợi ý hướng xử lý ở mức high-level
- ...

#### Độ tin cậy đánh giá kiến trúc
- CAO / TRUNG BÌNH / THẤP (và lý do)
```

Kết quả không phải là spec chi tiết, mà là **bản nhận định kiến trúc** giúp quyết định:

- Có thể tiến hành spec/implementation không.
- Cần chỉnh yêu cầu hay kiến trúc ở mức nào.

---

## 5. Nguyên tắc Độ tin cậy

Dựa vào `AGENT_TRANSPARENCY` + thực tế tool. **UA là nguồn probe chủ động cho câu hỏi boundary/topology** (Bước 4 & 6), không phải chỉ biến đo confidence — khi UA khả dụng mà Bước 4/6 không gọi nó cho câu hỏi cross-service, đó là **thiếu sót**, không phải lựa chọn. Logic confidence dưới đây giữ nguyên:

- **UA + db-explorer + codebase-explorer đều chạy ổn**:
  - Có thể đặt Độ tin cậy **CAO** nếu phân tích dựa trên:
    - Graph UA mới.
    - Thông tin DB thực tế.
    - Bối cảnh code đã map rõ.
- **UA không chạy (UA_UNAVAILABLE / user từ chối / chưa index)**:
  - Độ tin cậy tối đa = **TRUNG BÌNH**, kể cả khi đã có db-explorer + codebase-explorer.
  - Trong phần đánh giá phải note rõ:
    - “Không có UA graph, phân tích dựa trên thông tin từ db-explorer/codebase-explorer và đọc file thủ công.”
- **db-explorer không chạy được (hoặc không có quyền đọc DB)**:
  - Không được claim hiểu đầy đủ tác động lên dữ liệu.
  - Độ tin cậy cho phần liên quan dữ liệu tối đa = **TRUNG BÌNH**.
- **Cả UA lẫn db-explorer đều không chạy**:
  - Không được đặt Độ tin cậy kiến trúc = CAO.
  - Khuyến nghị:
    - Ghi rõ: “Kiến trúc chỉ được đánh giá dựa trên tài liệu và một phần code đọc tay; đề nghị hoàn thiện khám phá code/DB trước khi quyết định.”
- Luôn phân biệt:
  - Độ nghiêm trọng của vấn đề (LOW/HIGH…).
  - Độ tin cậy của nhận định (CAO/TRUNG BÌNH/THẤP).

---

## 6. Quy trình review chi tiết

### Bước 1 — Kiểm tra trạng thái tool & thiết lập “khung tin cậy”

1. Đọc `{{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md`:
   - `db-explorer`: đã chạy chưa? trên DB nào? có hạn chế quyền không?
   - `codebase-explorer`: đã chạy chưa? đã map được entrypoint/module chính chưa?
   - UA:
     - Repo đã từng chạy `/understand` chưa?
     - Lần gần nhất có được coi là mới/đủ tin cậy không?
     - `/understand-chat` có đang khả dụng không?
2. Từ đó:
   - Đặt khung Độ tin cậy **tối đa** khả dĩ.
   - Ghi chú khung này để không “lỡ tay” đánh giá quá cao.

---

### Bước 2 — Tóm tắt kiến trúc hiện tại liên quan tới yêu cầu

1. Từ `{{ platform.framework_root }}/knowledge/active/EXPLORE_CONTEXT.md` + `{{ platform.framework_root }}/knowledge/long-term/knowledge-snapshot.md`:
   - Xác định:
     - Service/module chính xử lý use case.
     - Integration (API, message, job nền…) liên quan.
     - Database/schema chính được dùng.
2. Nếu `EXPLORE_CONTEXT` có ghi kèm `identifier` (node_id hoặc file path):
   - Dùng `{{ tools.read_file }}(identifier)` để đọc code thực tế của các component quan trọng.
   - Dùng `{{ tools.get_dependencies }}(identifier)` để verify dependency thực tế vs. tài liệu.
3. Viết tóm tắt 3–7 bullet:
   - Đây là "bức tranh kiến trúc hiện tại cho yêu cầu này".
   - Dùng từ ngữ generic, không phán xét vội.

---

### Bước 3 — Đối chiếu flow As-is / To-be với kiến trúc hiện tại

1. Dựa trên As-is / To-be trong `{{ platform.framework_root }}/knowledge/active/REQUIREMENT.md`:
   - Flow hiện tại đang đi qua những component nào.
   - Flow To-be dự kiến đi thêm hoặc thay đổi component nào.
2. Nếu có identifiers từ EXPLORE_CONTEXT:
   - `{{ tools.find_blast_radius }}(identifier)` → xem blast radius của component sẽ bị sửa.
   - `{{ tools.read_file }}(identifier)` → đọc code thực tế để xác nhận logic.
   - `{{ tools.trace_flow }}(identifier)` → trace flow để verify As-is.
   - Sử dụng `{{ tools.read_file }}` để xác nhận logic thực tế đang chạy tại các điểm chạm quan trọng.
3. Đặt các câu hỏi:
   - Yêu cầu có reuse được entrypoint/flow hiện có không, hay tạo flow mới?
   - Có bỏ qua bước kiểm tra/validation quan trọng hiện đang được hệ thống thực thi không?
   - Có thêm bước mới ở đường nóng (hot path) gây ảnh hưởng hiệu năng / độ phức tạp không?
4. Ghi nhận:
   - Điểm **alignment**:
     - Phần nào của yêu cầu bám tốt vào kiến trúc hiện hữu.
   - Điểm **không khớp**:
     - Yêu cầu muốn làm việc A ở nơi kiến trúc hiện tại không được thiết kế cho việc đó.

---

### Bước 4 — Kiểm tra boundary, ownership, topology, coupling

> **Doctrine (đọc trước):** câu hỏi xuyên-service hoặc async là **UA-altitude** — kết luận topology/boundary **luôn lấy từ UA**. `{{ tools.find_blast_radius }}`/`{{ tools.get_dependencies }}` chỉ thấy method-call nội-service, **KHÔNG** thấy Kafka/gRPC và **KHÔNG** được dùng để định hình kiến trúc. Khi codebase mâu thuẫn một code-fact UA claim (vd không thấy gRPC stub) → ghi vào `AGENT_TRANSPARENCY` (“UA có thể stale ở X”), không tự override.

| Câu hỏi | UA định hình kết luận | Codebase chỉ xác nhận code-fact nội-service (tùy chọn) |
|---|---|---|
| Module **sở hữu** domain gì? Có trộn domain? | `{{ tools.domain_relationships }}` → ai sở hữu/đụng domain | `{{ tools.get_dependencies }}(identifier, direction='in')` check caller nội-service có thật |
| Luồng **Sync hay Async**? Kafka consumer đặt nhầm service? | `{{ tools.domain_flow }}` → entry Kafka/gRPC/REST | `{{ tools.trace_flow }}` xác nhận một logic nội-service |
| Coupling mới **xuyên service**? | `{{ tools.domain_relationships }}` → cạnh cross-service | `{{ tools.find_blast_radius }}` cho blast nội-service |

1. Boundary & ownership: dùng `{{ tools.domain_relationships }}` xác định ai sở hữu domain; cảnh báo nếu requirement đẩy trách nhiệm vào module không sở hữu domain đó (risk “trộn domain”).
2. Execution Context & Deployment Topology: dùng `{{ tools.domain_flow }}` xác định luồng Synchronous (API/Controller) hay Asynchronous (Kafka Consumer/Job/Scheduler). Cảnh báo BLOCKER nếu luồng Asynchronous bị đặt nhầm vào service thuần API, mà nên hướng về service xử lý nền (ví dụ: `worker-service`).
3. Layering & Convention Enforcement:
   - Đối chiếu với `conventions.yaml` và `knowledge-snapshot.md`. Bất kể dự án đang dùng kiến trúc gì (CQRS, MVC, Hexagonal), phải enforce chặt chẽ các constraint của kiến trúc đó.
   - Ví dụ (giả định, không phải mặc định): nếu `conventions.yaml` quy định API phải kế thừa một base class nhất định và mọi lệnh phải đi qua một message/command bus, thì phải bắt lỗi ngay khi Requirement/Spec định đi tắt (vd gọi thẳng tầng dưới, bỏ qua bus). Skill này **không** hardcode bất kỳ pattern nào (CQRS/MVC/Hexagonal…) — luôn đọc constraint từ `conventions.yaml` rồi enforce.
4. Coupling:
   - Yêu cầu có thêm phụ thuộc mới giữa module/service vốn nên độc lập không?
   - Nếu có identifiers: `{{ tools.find_blast_radius }}(identifier)` → xem blast radius trước khi sửa.

Đánh dấu các vấn đề theo mức độ: LOW/MEDIUM/HIGH/BLOCKER.

---

### Bước 5 — Đánh giá tác động lên tầng dữ liệu

Dựa trên kết quả `db-explorer`:

1. Schema:
   - Yêu cầu có đòi hỏi:
     - Thêm field/bảng mới (mở rộng).
     - Sửa field/bảng hiện tại (có thể ảnh hưởng backward compatibility).
     - Đụng khoá chính, quan hệ core không?
2. Constraint:
   - Có constraint hiện tại (CHECK/UNIQUE/FK…) mâu thuẫn với behaviour To-be không?
   - Có trigger/procedure đang thực hiện logic mà requirement mới không đề cập?
3. Migration & lịch sử:
   - Yêu cầu có ảnh hưởng tới dữ liệu lịch sử / báo cáo đang dùng không?
   - Cần migration hoặc backfill không?

Nếu dữ liệu là trọng tâm mà không có `db-explorer` → phải flag rủi ro và hạ Độ tin cậy.

---

### Bước 6 — Đánh giá non-functional (ở mức high-level)

1. Hiệu năng:
   - Yêu cầu thêm call, join, IO hay tính toán trên đường nóng?
   - Có move công việc sang luồng async/background phù hợp không? Dùng `{{ tools.domain_flow }}` (UA) xác nhận điểm async thật sự nằm ở đâu **trước khi** nhận định hot-path — đừng đoán từ code nội-service.
2. Độ tin cậy / sẵn sàng:
   - Yêu cầu thêm dependency mới (service, DB, external system) trên đường critical?
   - Có single point of failure mới không?
3. Observability:
   - Luồng mới/đổi có được cover bởi logging/metrics/tracing hiện tại không?

Không cần thiết kế NFR chi tiết, chỉ nêu concern để spec/implementation xử lý tiếp.

---

### Bước 7 — Tổng hợp đánh giá & gợi ý hướng xử lý

1. Trong `{{ platform.framework_root }}/knowledge/active/EXPLORE_CONTEXT.md` (section `Đánh giá kiến trúc`), ghi:

   - **Điểm phù hợp**:
     - Các phần của yêu cầu tận dụng tốt kiến trúc hiện tại.
   - **Điểm xung đột / rủi ro**:
     - Liệt kê theo topic (boundary, dữ liệu, NFR…).
     - Gán mức LOW/MEDIUM/HIGH/BLOCKER.

2. Đưa ra **gợi ý hướng xử lý ở mức high-level** (không phải design chi tiết), ví dụ:
   - Cần tách thêm module/boundary.
   - Nên bổ sung event / API thay vì gọi trực tiếp.
   - Cần thiết kế chiến lược migration dữ liệu.

3. Không áp đặt giải pháp cụ thể nếu thiếu thông tin; thay vì đó:
   - Nêu ra **câu hỏi cần trả lời** khi vào bước thiết kế chi tiết.

---

## 7. Cập nhật AGENT_TRANSPARENCY

Trong `{{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md`:

- Đánh dấu:
  - `[x] architecture-reviewer`
- Ghi rõ:
  - Provider `code_exploration` đã dùng:
    - Operations đã gọi: `check_availability`, `find_blast_radius`, `get_source`, `get_dependencies`.
  - Trạng thái `db-explorer` và `codebase-explorer`.
- Ghi **Độ tin cậy kiến trúc tổng thể**:
  - CAO / TRUNG BÌNH / THẤP.
  - 1–3 câu giải thích (ví dụ: "Provider CAO + db-explorer đều OK nên độ tin cậy CAO.").
- Nếu có BLOCKER:
  - Ghi rõ cần action gì (workshop kiến trúc, làm rõ yêu cầu, bổ sung khám phá DB/code) trước khi tiếp tục pipeline.

---

## 8. Lưu ý

- Skill này **không vẽ lại toàn bộ kiến trúc**, mà đối chiếu yêu cầu với kiến trúc hiện tại và làm rõ rủi ro.
- Không encode domain business cụ thể; chỉ làm việc với **cấu trúc hệ thống** (service/module/DB/integration).
- Luôn tách bạch:
  - Fact (những gì đã thấy từ code/DB/tài liệu).
  - Nhận định (đánh giá kiến trúc).
  - Giả định (nếu thiếu dữ liệu).

---

## [M5] Infra-TDD Auto-Trigger

### Khi nào đề xuất infra-tdd

Sau khi `architecture-reviewer` hoàn thành đánh giá (Bước 7), kiểm tra:

```
FUNCTION should_trigger_infra_tdd(review_result):
  IF ANY of the following is true:
    - review_result có ít nhất 1 issue mức HIGH hoặc BLOCKER liên quan đến:
      * Infrastructure (database schema mới, index mới, migration)
      * Platform change (thêm service mới, thay đổi topology deployment)
      * Integration change (Kafka topic mới, API contract mới, external system)
    - REQUIREMENT.task_type = "changerequest" VÀ scope chạm infrastructure
    - spec sẽ tạo ra artifact cần TDD riêng (vd: DB migration, k8s config, pipeline mới)
  THEN:
    → SUGGEST infra-tdd

SUGGEST infra-tdd:
  1. Thông báo cho user:
     "[M5] Yêu cầu này có tác động hạ tầng. Khuyến nghị tạo TDD trước khi spec."
  2. Đề nghị: "Chạy `/tdd` để tạo Technical Design Document?"
  3. Ghi vào AGENT_TRANSPARENCY:
     "[M5-INFRA-TDD] Đề xuất TDD vì: {lý do}. User cần confirm."
  4. Không tự động chạy `/tdd` — chỉ đề xuất.
  5. Nếu user đồng ý → điều hướng sang workflow `{{ platform.framework_root }}/workflows/tdd.md`
  6. Nếu user từ chối → tiếp tục flow bình thường, ghi "TDD declined by user"
```

### Điều kiện KHÔNG trigger

- Thay đổi thuần code (business logic, UI, validation).
- Bugfix không thay đổi schema/topology.
- Refactor trong phạm vi 1 module, không có DB/infra impact.

### Ví dụ trigger scenarios

| Scenario | Trigger? | Lý do |
|----------|----------|-------|
| Thêm bảng mới vào Oracle | Có | DB schema change |
| Thêm Kafka consumer mới | Có | New integration topology |
| Sửa validation logic | Không | Code-only change |
| Thêm API endpoint mới | Có (nếu thay đổi contract) | Platform/API impact |
| Refactor service nội bộ | Không | Internal code only |

---

## [M6] Contract Completeness Check

### Mục đích

Kiểm tra section "Technical Design Contract" trong REQUIREMENT.md có được điền đủ không — lớp bảo vệ thứ hai sau `requirement-analyst` Bước 7.

Chạy **sau** Bước 7 (Tổng hợp), **trước** khi kết luận đánh giá kiến trúc.

### Logic kiểm tra

```
FUNCTION check_contract_completeness(requirement_path):
  1. Đọc REQUIREMENT.md — tìm section "Technical Design Contract"
     (hoặc tên section tương đương theo template)

  2. [M6-C1] Section tồn tại và có nội dung thực (không chỉ placeholder/comment)?
     IF chỉ là skeleton (chỉ chứa <!-- --> hoặc "- <!-- item -->"):
       → WARN: "[M6-WARN] Technical Design Contract chưa được điền.
               Spec Pha 2 có thể thiếu API/interface definition."

  3. [M6-C2] Nếu section có nội dung:
     - Đọc conventions.yaml (nếu tồn tại, status=approved):
       - Lấy design_patterns, upstream_constraints, naming conventions
     - So sánh giao thức/pattern được chọn trong contract với conventions:
       IF contract chọn giao thức/pattern mâu thuẫn với conventions:
         → WARN: "[M6-WARN] Contract chọn {protocol/pattern} nhưng
                 conventions.yaml quy định {expected}. Cần xác nhận."
     - Nếu conventions.yaml không tồn tại hoặc status ≠ approved:
       → Bỏ qua M6-C2 (không có cơ sở để cross-check)

  4. [M6-C3] Contract có đủ 3 phần tối thiểu không?
     - Giao thức & Giao diện (protocol/endpoint/topic)
     - Request/Message schema
     - Response/Event schema
     IF thiếu bất kỳ phần nào:
       → WARN: "[M6-WARN] Contract thiếu {phần thiếu}. Cân nhắc bổ sung trước Pha 2."

SEVERITY: Tất cả M6 checks chỉ WARN, KHÔNG BLOCK pipeline.
  → Contract có thể được bổ sung/refine ở Pha 2 (spec).
  → Mục đích: nhắc sớm, không gây cản trở.

GHI VÀO AGENT_TRANSPARENCY:
  "[M6] Contract Completeness: {PASS|WARN(n)} — {chi tiết nếu có WARN}"
```

### Điều kiện KHÔNG chạy M6

- REQUIREMENT.md không có section "Technical Design Contract" trong template → bỏ qua (template cũ).
- Task type = `refactor` → thường không có interface mới, bỏ qua.

### Quan hệ với M5

M5 và M6 chạy **độc lập**, không phụ thuộc nhau:
- M5: đánh giá tác động hạ tầng → đề xuất TDD.
- M6: đánh giá contract completeness → nhắc bổ sung trước spec.

---

## Gotchas

- **[G1] knowledge-snapshot stale**: Luôn check tag `<!-- verified: YYYY-MM-DD -->` trong `knowledge-snapshot.md`. Nếu >30 ngày → coi snapshot là reference chứ không phải source of truth. Cross-verify với UA graph.
- **[G2] conventions.yaml vs conventions.draft.yaml**: Chỉ dùng `conventions.yaml` (approved). File `.draft.yaml` chưa được user xác nhận — KHÔNG dùng làm căn cứ đánh giá.
- **[G3] M6 contract check cần REQUIREMENT**: M6 (Check contract completeness) chỉ trigger khi `REQUIREMENT.md` có nội dung thực. Nếu REQUIREMENT trống/skeleton → M6 skip, không báo lỗi.
- **[G4] Upstream library boundary**: Khi đánh giá design, KHÔNG đề xuất thay đổi interface/base class từ upstream library. Chỉ WARN nếu downstream implementation lệch so với upstream contract.
