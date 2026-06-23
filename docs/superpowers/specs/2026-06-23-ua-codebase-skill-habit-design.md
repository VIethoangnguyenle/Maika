# Định hình lại cách dùng UA MCP & Codebase MCP — qua thói quen trong skill

**Ngày:** 2026-06-23
**Phạm vi:** `.maika/skills/codebase-explorer/SKILL.md`, `.maika/skills/architecture-reviewer/SKILL.md`
**Không đụng tới:** rules (`rules-tool.md`, `rules-knowledge.md`), gates, schema artifact của arch-reviewer, db-explorer, các skill/phase khác.

---

## 1. Vấn đề

Trong thực tế explore, agent **quá phụ thuộc `codebase-memory-mcp`** → sa lầy ("rabbit hole") khi trace các base/abstract class nhiều impl, và **mù với ranh giới async (Kafka/gRPC)** vì codebase-memory chỉ thấy method-call nội-service. Kết quả: explore sai, không thấy được service nói chuyện với nhau ra sao, phải tự suy luận entry point từ Controller.

`understand-anything` (UA) MCP mạnh đúng ở chỗ codebase-memory yếu: top-down domain/business-flow, entry point (REST/gRPC/Kafka), ranh giới xuyên-service. So sánh chi tiết: xem `compare.md`.

## 2. Root cause — không nằm ở thiếu prose, mà ở "thói quen" không được củng cố

Hai skill tiêu thụ tri thức UA + Codebase **lệch theo hai kiểu khác nhau**:

- **`codebase-explorer`** — *đã có* altitude-routing + Golden Path UA↔Codebase, nhưng agent bỏ qua **đúng lúc dễ sa lầy nhất**:
  - Câu hedge "structured-first… static call-chain vẫn dùng `trace_flow` (Codebase) làm chính" kéo agent về codebase ngay tại điểm rabbit-hole.
  - Output schema `EXPLORE_CONTEXT` đòi `node_id` (khái niệm codebase-mcp) cho mọi component → để "điền cho đủ", agent quay về codebase.
- **`architecture-reviewer`** — UA gần như **không được dùng chủ động**: toàn bộ Bước 2–4 probe bằng codebase tools (`read_file`, `get_dependencies`, `find_blast_radius`, `trace_flow` theo `node_id`); UA chỉ là **cờ đo confidence**. Nhưng Bước 4 (boundary/ownership/**topology**/coupling) và Bước 6 (**async hot-path**) chính là câu hỏi độ-cao-domain UA giỏi nhất — skill có nhiệm vụ bắt lỗi async-topology lại dùng đúng lens mù-với-async.

## 3. Hướng giải quyết

**Tối ưu nội dung skill, không thêm rule.** Tạo cho agent **thói quen** dùng đúng tool, theo vòng lặp **CUE → ROUTINE → REWARD** — neo việc chọn tool vào triệu chứng agent thực sự gặp giữa task, vì agent fail ở những khoảnh khắc nhận diện được.

Nguyên tắc xuyên suốt cả hai skill:
> **Codebase = lens nội-service** (symbol / static-trace / đọc code). **KHÔNG dùng để định hình hay kết luận kiến trúc.**
> **UA = lens xuyên-service & async** (domain / flow / entry-point / boundary). **UA luôn ưu tiên cho mọi câu hỏi kiến trúc.**
> **Habit neo vào cue, không vào rule.**

Hệ quả: ở câu hỏi kiến trúc (boundary/topology/ownership/coupling), kết luận **luôn lấy từ UA**. Codebase chỉ được dùng để xác nhận một **code-fact nội-service cụ thể** (ví dụ: call X→Y có thật sự tồn tại không) — không bao giờ để định hình topology, và không được override nhận định kiến trúc của UA.

---

## 4. Thiết kế — `codebase-explorer`

### 4.1 Thêm khối "Cue Cards" (đặt đầu mục *Định tuyến theo độ cao*)

| CUE (agent nhận ra) | ROUTINE (phản xạ) | REWARD |
|---|---|---|
| Sắp `trace_flow`/`get_dependencies` vào **base/abstract class nhiều impl** (BaseHandler…) | DỪNG codebase → `domain_flow` (UA) | Flow human-readable, bỏ qua hàng chục lớp con nhiễu |
| Call-chain vừa chạm `@KafkaListener`/gRPC stub rồi **đứt lạnh** | Leo thang `domain_flow`/`domain_relationships` (UA) | Thấy service nói chuyện với nhau ra sao |
| **Chưa biết entry point** (REST? gRPC? Kafka?) | `domain_overview` → `domain_flow` (UA) **trước** mọi grep | Định vị entry đúng, không suy luận từ Controller |
| Đã có **file/symbol cụ thể, localized, sửa 1 hàm** | Codebase thẳng (`search_code` → `get_symbol` → `read_file`) | Không tốn UA overhead |

### 4.2 Gỡ câu hedge mâu thuẫn (net-negative)

Thay dòng "structured-first… static call-chain vẫn dùng `trace_flow` (Codebase) làm chính" bằng:

> Codebase là chính cho static-trace **nội-service**. Nhưng khoảnh khắc câu hỏi trở thành *"flow này bắt đầu ở đâu / service nói chuyện ra sao"* thì đó là độ-cao UA — nhận ra bằng **Cue Cards** ở trên, đừng để phí vài call rồi mới leo thang.

### 4.3 Sửa "phần thưởng" của output schema

Trong section output `Kiến trúc code hiện tại`:
- Cho phép **identifier kiểu UA** (tên domain, flow, entry-point) đứng **ngang hàng** `node_id`.
- Mục *Entry points* và *Integration / event / job* ghi nguồn từ UA là **hợp lệ và được khuyến khích**.
- Giữ ghi chú: với component cần đọc code chi tiết downstream, vẫn nên kèm `node_id`/file-path để `read_file(identifier)` trực tiếp.

→ Habit chỉ bền khi việc-dùng-UA *được thưởng* trong artifact, không bị phạt vì "thiếu node_id".

---

## 5. Thiết kế — `architecture-reviewer`

Sửa **đúng Bước 4 & 6** + đổi vai UA ở Bước 1 / Nguyên tắc Độ tin cậy. Không đụng phần còn lại.

### 5.1 Bước 4 (boundary / ownership / topology / coupling): UA định hình, Codebase chỉ xác nhận code-fact

Kết luận kiến trúc **luôn lấy từ UA**. Codebase **không** "verify ngang hàng" — nó là cấp dưới, chỉ kiểm chứng một code-fact nội-service cụ thể khi cần, và **không được dùng để định hình hay override** topology/boundary.

| Câu hỏi Bước 4 | UA (định hình kết luận — đúng altitude) | Codebase (chỉ xác nhận code-fact nội-service, KHÔNG định hình) |
|---|---|---|
| Module **sở hữu** domain gì? Có trộn domain? | `domain_relationships` → ai sở hữu/đụng domain | (tùy chọn) `get_dependencies(dir=in)` chỉ để check caller nội-service có thật |
| Luồng **Sync hay Async**? Kafka consumer đặt nhầm service? | `domain_flow` → thấy entry Kafka/gRPC/REST | (tùy chọn) `trace_flow` chỉ xác nhận một logic nội-service cụ thể |
| Coupling mới **xuyên service**? | `domain_relationships` → cạnh cross-service | (tùy chọn) `find_blast_radius` chỉ cho blast nội-service |

Cue nhúng vào Bước 4:
> Câu hỏi xuyên-service hoặc async ⇒ đó là UA-altitude, kết luận lấy từ UA. `find_blast_radius`/`get_dependencies` chỉ thấy method-call nội-service — chúng **KHÔNG** thấy Kafka/gRPC và **KHÔNG** được dùng để định hình/kết luận topology. Đừng kết luận kiến trúc từ codebase.

### 5.2 Bước 6 (non-functional / hot-path async)

Câu *"có move việc sang luồng async/background phù hợp không"* hiện không có tool → agent đoán. Thêm: dùng `domain_flow` (UA) để xác nhận điểm async thật sự nằm ở đâu **trước khi** nhận định hot-path.

### 5.3 Bước 1 & "Nguyên tắc Độ tin cậy": đổi vai UA

Giữ nguyên logic confidence (UA tắt → max TRUNG BÌNH). Bỏ ngụ ý "UA chỉ là cờ". Viết rõ:
- UA là **nguồn probe chủ động cho câu hỏi boundary/topology**, không phải chỉ biến đo confidence.
- Khi UA khả dụng mà Bước 4/6 *không gọi* nó cho câu hỏi cross-service → đó là **thiếu sót**, không phải lựa chọn.

### 5.4 Không đụng

Bước 5 (DB → db-explorer), M5/M6, Gotchas, output schema arch-reviewer.

---

## 6. Tiêu chí thành công (verify)

1. **`codebase-explorer`**: có khối Cue Cards; câu hedge "structured-first" cũ đã được thay; output schema chấp nhận identifier kiểu UA. Skill-lint `PASS`.
2. **`architecture-reviewer`**: Bước 4 có bảng ghép cặp UA-trước/Codebase-verify + cue async; Bước 6 gọi `domain_flow`; mục Độ tin cậy mô tả UA là probe chủ động. Skill-lint `PASS`.
3. **Net-negative complexity**: không thêm rule/gate mới; thay đổi ròng nghiêng về *thay thế* prose mâu thuẫn bằng cue cụ thể.
4. **Degradation giữ nguyên**: khi UA vắng, cả hai skill vẫn chạy được codebase-only + hạ confidence (không bịa).

## 7. Ngoài phạm vi (có thể làm sau)

- Đụng tới `R-Tool-5` evidence gate / schema `EXPLORE_CONTEXT` ở mức rule.
- Propagate doctrine sang các skill/phase khác (openspec-propose, task workflow, subagent dispatch).
- Cập nhật `compare.md` thành tài liệu chính thức trong `.maika/`.
