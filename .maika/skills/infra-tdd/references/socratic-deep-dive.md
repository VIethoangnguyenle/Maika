# Socratic Deep-Dive — Protocol Tra Vấn Quyết Định

> Tài liệu tham khảo cho skill `infra-tdd`. Load khi tra vấn quyết định kiến trúc (Bước 4).

## Mục lục

- Mục đích
- 3 Chế độ thực thi
- 5 Buckets câu hỏi
- Workflow Deep-Dive
- Failure Modes của chính Deep-Dive
- Ví dụ áp dụng

---

## Mục đích

Socratic deep-dive là protocol **tra vấn có hệ thống** để lộ các giả định ẩn, alternatives chưa xem xét, và trade-offs chưa đặt tên trong mọi quyết định thiết kế.

**Kết quả** sau deep-dive:
1. **Alternatives thực sự đã xem xét** (≥ 2, lý tưởng 3)
2. **Tiêu chí đánh giá có trọng số**
3. **Trade-off đã chấp nhận** (đặt tên cụ thể)

---

## 3 Chế độ thực thi

### Chế độ A — Understand-Anything MCP (Ưu tiên cao nhất)

Khi UA Knowledge Graph khả dụng, dùng các tool sau để drive deep-dive:

| Tool | Mục đích trong deep-dive |
|------|--------------------------|
| `{{ tools.search_code }}` | Tìm components liên quan đến quyết định |
| `{{ tools.get_symbol }}` | Xem chi tiết implementation hiện tại |
| `{{ tools.get_dependencies }}` | Map dependency — ai gọi ai, ai phụ thuộc ai |
| `{{ tools.find_blast_radius }}` | Blast radius — nếu thay đổi, bao nhiêu files bị ảnh hưởng |
| `{{ tools.trace_flow }}` | Luồng thực thi — data đi qua đâu |
| `{{ tools.get_symbol }}` | Business rules liên quan |
| `{{ tools.read_file }}` | Xem source code thực tế |

**Workflow Mode A:**
1. `{{ tools.search_code }}` → tìm module/class liên quan đến quyết định
2. `{{ tools.get_dependencies }}` → map "ai dùng cái này?"
3. `{{ tools.find_blast_radius }}` → nếu thay đổi, blast radius là gì?
4. `{{ tools.trace_flow }}` → data flow thực tế
5. Đặt câu hỏi từ 5 buckets (xem bên dưới) dựa trên evidence thu được
6. Viết ADR với evidence từ UA

### Chế độ B — Codebase Memory MCP (Ưu tiên cao)

Khi Codebase Memory index khả dụng:

| Tool | Mục đích |
|------|----------|
| `{{ tools.search_code }}` | Tìm implementation patterns liên quan |
| `{{ tools.get_dependencies }}` | Dependency graph — file X import gì, ai import X |
| `{{ tools.find_blast_radius }}` | Blast radius khi thay đổi file/symbol |
| `{{ tools.get_symbol }}` | Chi tiết symbol (callers, callees) |
| `{{ tools.trace_flow }}` | Call tree từ entry point |

**Workflow Mode B:**
1. `{{ tools.search_code }}` → tìm patterns tương tự trong codebase
2. `{{ tools.get_dependencies }}` → ai phụ thuộc module này
3. `{{ tools.find_blast_radius }}` → nếu refactor, ảnh hưởng gì
4. Đặt câu hỏi dựa trên evidence
5. Viết ADR

### Chế độ C — Câu hỏi thuần (Fallback)

Khi không có MCP tools, chạy deep-dive bằng câu hỏi trực tiếp từ 5 buckets.

---

## 5 Buckets câu hỏi

### Bucket 1 — Assumptions (Giả định)

> Mục đích: Lộ những thứ "ai cũng biết" nhưng chưa ai verify.

| # | Câu hỏi |
|---|---------|
| A1 | Giả định nào về load/traffic pattern đang ảnh hưởng thiết kế? |
| A2 | Nếu traffic tăng 10x trong 6 tháng, thiết kế này còn đứng vững? |
| A3 | Dependency nào đang giả định "luôn available"? Xảy ra gì khi nó chết? |
| A4 | Data model đang giả định schema ổn định — nếu business thay đổi yêu cầu? |
| A5 | Team đang giả định có skill gì? Nếu key person nghỉ? |

**Với UA/Codebase Memory**: Dùng `{{ tools.find_blast_radius }}` / `{{ tools.find_blast_radius }}` để verify A2, A3 bằng blast radius thực tế.

### Bucket 2 — Alternatives (Lựa chọn)

> Mục đích: Buộc liệt kê options thực sự, không chỉ option đã chọn.

| # | Câu hỏi |
|---|---------|
| B1 | Ngoài giải pháp này, đã xem xét alternatives nào khác? |
| B2 | Tại sao không dùng {alternative phổ biến nhất trong industry}? |
| B3 | "Không làm gì" có phải option không? Chi phí duy trì status quo là gì? |
| B4 | Có thể chia nhỏ quyết định không? (VD: chọn DB và chọn caching riêng) |
| B5 | Nếu phải implement trong 1 tuần thay vì 1 tháng, chọn gì? |

**Với UA**: Dùng `{{ tools.search_code }}` để tìm cách hệ thống khác trong codebase giải quyết vấn đề tương tự.

### Bucket 3 — Trade-offs

> Mục đích: Đặt tên cụ thể cho cái mất.

| # | Câu hỏi |
|---|---------|
| T1 | Chọn giải pháp này, cái gì trở nên KHÓ HƠN? |
| T2 | Consistency vs Availability — đang chọn bên nào? |
| T3 | Complexity nằm ở đâu? (Infra? Code? Operations? Onboarding?) |
| T4 | Chi phí ẩn nào sẽ xuất hiện sau 6 tháng? |
| T5 | Nếu phải giải thích trade-off cho CFO trong 1 câu, nói gì? |

### Bucket 4 — Failure Modes

> Mục đích: Tìm cách hệ thống chết.

| # | Câu hỏi |
|---|---------|
| F1 | Kịch bản failure nguy hiểm nhất là gì? (Mất data? Mất tiền? Downtime?) |
| F2 | Nếu {dependency} chết 30 phút, user experience ra sao? |
| F3 | Có single point of failure nào không? |
| F4 | Recovery time (RTO) mục tiêu là bao lâu? Hiện tại đạt được không? |
| F5 | Sự cố vận hành tương tự gần nhất là gì? Root cause là gì? |

**Với UA**: Dùng `{{ tools.get_dependencies }}(direction="in")` để tìm mọi thứ phụ thuộc module này → single point of failure.

### Bucket 5 — Evolution (Tiến hoá)

> Mục đích: Test khả năng mở rộng của thiết kế.

| # | Câu hỏi |
|---|---------|
| E1 | Nếu cần hỗ trợ thêm 1 loại giao dịch mới, thay đổi bao nhiêu files? |
| E2 | Thiết kế này có "lock-in" với vendor/technology nào không? |
| E3 | Nếu team quyết định chuyển sang {tech khác} sau 1 năm, effort bao nhiêu? |
| E4 | Module này có thể tách ra thành microservice riêng không? |
| E5 | API contract có backward-compatible không khi thêm field mới? |

**Với Codebase Memory**: Dùng `{{ tools.find_blast_radius }}` để answer E1 bằng con số thực (bao nhiêu files thay đổi).

---

## Workflow Deep-Dive

```
1. Xác định quyết định cần tra vấn
   ↓
2. Chọn chế độ (A: UA, B: Codebase Memory, C: Câu hỏi)
   ↓
3. Thu thập evidence từ tools (Mode A/B)
   hoặc đặt câu hỏi (Mode C)
   ↓
4. Chạy qua 5 buckets — chọn 2-3 câu quan trọng từ mỗi bucket
   ↓
5. Tổng hợp findings:
   - Alternatives thực sự (≥ 2)
   - Ma trận đánh giá có trọng số
   - Trade-offs đặt tên
   ↓
6. Viết ADR (file riêng)
```

---

## Failure Modes của chính Deep-Dive

| Failure | Symptom | Mitigation |
|---------|---------|------------|
| **Shallow dive** | Chỉ hỏi 2-3 câu rồi dừng | Bắt buộc chạy ≥ 2 buckets |
| **Confirmation bias** | Chỉ tìm evidence ủng hộ choice đã chọn | Hỏi bucket B (alternatives) trước |
| **Analysis paralysis** | Deep-dive 2 tiếng cho 1 quyết định nhỏ | Time-box: 15 phút cho quyết định nhỏ, 30 phút cho lớn |
| **No evidence** | Kết luận dựa trên opinion | Ghi rõ "⚠️ Thiếu evidence — cần benchmark/PoC" |
| **Tool unavailable** | UA/Codebase Memory không chạy | Degrade sang Mode C (câu hỏi), ghi rõ gaps |

---

## Ví dụ áp dụng

> Quyết định: "Dùng Redis Distributed Lock hay DB Pessimistic Lock cho transaction serialization?"

**Mode A (UA):**
1. `{{ tools.search_code }}("distributed lock")` → tìm `ExpirableLockRegistry`, `BaseApprovalRequestProcessor`
2. `{{ tools.get_dependencies }}("BaseApprovalRequestProcessor")` → 10 processors kế thừa
3. `{{ tools.find_blast_radius }}("BaseApprovalRequestProcessor")` → blast radius = 10 files
4. `{{ tools.trace_flow }}("BaseApprovalRequestProcessor")` → Redis → tryLock → strategy → cache

**Evidence thu được**: Lock pattern đã dùng rộng (10 processors), blast radius lớn → thay đổi cần cẩn thận, Redis lock < 5ms P99.

**Buckets applied**:
- A3: "Redis chết → mọi action bị reject" → mitigation: DB constraint safety net
- T1: "Chọn Redis = depend thêm infra" → chấp nhận vì HA Sentinel
- F3: "Redis single point?" → Không, có Sentinel failover
