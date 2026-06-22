# Báo cáo Đánh giá Framework Maika v3

> Tổng hợp từ phiên brainstorming ngày 2026-06-16.
> Phạm vi: đánh giá công tâm điểm mạnh / điểm yếu, chẩn đoán vấn đề thực chiến,
> và đề xuất hướng cải thiện — đặc biệt cho mục tiêu **portable across mọi agent framework**.

---

## 0. Tóm tắt điều hành

Maika v3 là một protocol bộ nhớ + workflow đa pha cho AI coding agent, đã trưởng thành từ
thực chiến (sinh rule sau incident, không phải lý thuyết suông). **Pha 1 (hiểu source) và
Pha 2 (viết spec) hoạt động tốt.** Vấn đề tập trung ở **Pha 3 (coding)**: agent drift khỏi
`author-dna`, miss update task trong OpenSpec, buộc người dùng sửa tay nhiều.

Chẩn đoán cốt lõi của báo cáo này: **không phải "vượt context" đơn thuần** — mà là một giới
hạn cấu trúc (rule trở thành ràng buộc phụ dưới tải generation) cộng với việc **mọi enforcement
đều là prose chứ không deterministic**. Hướng sửa: tách *sinh code* khỏi *kiểm tra code*, đẩy
phần kiểm-tra-được-bằng-máy xuống gate deterministic (git hook), và chẻ Pha 3 thành vòng lặp
subagent tuần tự để khử context dilution tận gốc.

---

## 1. Điểm mạnh (thật sự)

| # | Điểm mạnh | Vì sao đáng giá |
|---|-----------|-----------------|
| S1 | **Flow 5 pha bắt buộc** | Giải đúng một failure mode kinh điển: agent nhảy thẳng vào code khi chưa hiểu yêu cầu. Vấn đề có thật, không phải vấn đề giả. |
| S2 | **Tách 3 tầng tri thức** | `author-dna` (WHY/HOW — lens tư duy) vs `conventions` (WHAT — luật cấu trúc) vs `knowledge-snapshot` (WHAT-IS — bản đồ kiến trúc). Bước 0 của R-DNA-7 (bỏ tên cụ thể để test abstraction level) là insight hiếm. **Đây là phần giá trị nhất.** |
| S3 | **"Sandwich defense" cho context dilution** | Load rule ở đầu (bootstrap) + cuối (DNA-RELOAD trước khi code). Cho thấy hiểu cơ chế recency window thật sự. |
| S4 | **Externalize state ra disk** | `AGENT_TRANSPARENCY` + `phase_state` cho phép resume sau khi session bị truncate — đúng hướng cho agent dài hơi. |
| S5 | **Trưởng thành từ incident** | 13 rules sinh ra sau sự cố 2026-06-08. Empirically grown, không phải lý thuyết. |
| S6 | **R-DNA-7 capture teaching moment** | Biến correction của tác giả thành tri thức bền vững. Đây là *moat* thật sự — knowledge accumulation per session. |
| S7 | **Tiered loading (SMALL/MEDIUM/LARGE)** | Quản token theo độ phức tạp task — pragmatic. |

---

## 2. Điểm yếu (phần khó nghe)

| # | Điểm yếu | Bản chất vấn đề |
|---|----------|-----------------|
| W1 | **Mâu thuẫn cốt lõi: "deterministic guardrail" nhưng chạy bằng prose** | R-Guard-1 trích Arthur AI ("guardrails phải deterministic") rồi implement guard đó bằng *câu chữ cho LLM tự chấp hành*. Guardrail thật là *code chạy bên ngoài* model. Mọi "PHẢI / BẮT BUỘC / HARDBLOCK" đều là text mà model phi-deterministic có thể reason vượt qua. **Vấn đề sâu nhất.** |
| W2 | **Compliance theater** | Nhiều gate yêu cầu agent *ghi checkpoint chứng minh đã làm*. Nhưng viết "tôi đã check DNA" ≠ thật sự check DNA. Audit trail chứng minh *nghi thức đã chạy*, không chứng minh *chất lượng*. |
| W3 | **Overhead lớn, workflow không phân tầng** | DNA có tiered loading nhưng *workflow* thì không: một bugfix nhỏ vẫn đi full pipeline. Cảnh báo "Pha 1 > 50,000 token" tự tố cáo điều này. |
| W4 | **Mỉa mai về token** | Hệ thống lo lắng về token (có TOKEN_LOG) lại tiêu phần lớn budget cho chính bookkeeping của nó. |
| W5 | **Coupling cứng ở tầng TOOL (không phải tầng tri thức)** | RULES/workflows hardcode tool cụ thể: OpenSpec (`/opsx:propose`), UA/KG MCP (`get_graph_stats`…), codebase-memory-mcp, Antigravity. *Đây* là chỗ đâm vào mục tiêu "mọi framework". **Lưu ý phân biệt:** `author-dna`/`conventions`/`knowledge-snapshot` là **per-project by design** — nội dung Java/Spring chỉ là *instance* của dự án này (mang vào làm ví dụ file thật), KHÔNG phải coupling của framework. Framework core đã content-agnostic ở tầng tri thức; chỉ tầng tool cần adapter (→ SP2). |
| W6 | **Không có outcome loop** | Có TOKEN_LOG nhưng không có *quality log*. Không biết rule nào "đáng tiền". Rule chỉ tích lũy, không bao giờ bị prune → rule bloat → context phình → đúng thứ nó đang chống. |
| W7 | **Friction đẩy sang con người** | "Vui lòng mở session mới" sau mỗi pha là bắt user tự quản context hygiene; khi user phớt lờ thì chỉ log WARN, không enforce. |
| W8 | **DNA đơn-tác-giả** | `author-dna.yaml` là triết lý của một người, build thủ công qua interview. "Mọi team" → DNA của ai? Project mới = DNA rỗng = quay về generic. |
| W9 | **Gate trùng lặp** | R-Guard-2 + DNA-RELOAD + post_apply_dna_check + spec-validator cùng check DNA ở 4 điểm → 4 chỗ phải maintain cùng intent, dễ drift. |

---

## 3. Chẩn đoán vấn đề thực chiến (Pha 3 drift)

### 3.1 Vì sao Pha 1–2 tốt mà Pha 3 hỏng — không phải ngẫu nhiên

- **Pha 1–2: rule CHÍNH LÀ nhiệm vụ.** Việc của agent là phân tích, viết spec — DNA/convention
  là *nội dung công việc*. Model dồn toàn bộ attention vào chúng.
- **Pha 3: rule trở thành ràng buộc PHỤ.** Nhiệm vụ chính là *sinh code giải bài toán*. DNA
  (zero-nesting, no-else, max 30 dòng, update OpenSpec task) trở thành checklist phải *giữ song
  song* trong lúc vật lộn với logic. **Dưới tải generation, model thả các ràng buộc phụ một cách
  có hệ thống** — giới hạn cấu trúc, không phải lỗi nhắc chưa đủ.

**Bằng chứng:** DNA-RELOAD đã được thiết kế riêng để chống "context overflow" này, đặt ngay
trước khi code. Nó vẫn fail — vì kể cả khi DNA vừa nạp lại, lúc sinh 200 dòng qua 5 file thì
recency lại loãng ngay và attention vẫn bị generation chiếm.

### 3.2 Hệ quả

Vấn đề **không sửa được bằng "nhắc mạnh hơn / reload thêm"**. Phải **ngừng dựa vào model tự-enforce
trong lúc generate** — tách *sinh code* khỏi *kiểm tra code*.

---

## 4. Hướng cải thiện

### 4.1 Nguyên lý xuyên suốt

> **Mọi tri thức sống = file người-đọc-được (source of truth, versioned, review được)
> → sinh ra artifact máy-tối-ưu (derived, regenerate khi nguồn đổi, sync-check chống lệch pha).**

Áp dụng đồng nhất ở 2 chỗ: `DNA → linter ruleset`, và `knowledge-snapshot → vector index`.

### 4.2 Kiến trúc Phase 3 Reliability (4 thành phần)

```
   author-dna.yaml ─┐                        knowledge-snapshot.md
   conventions.yaml ─┤ (approved, SoT)            (SoT, git, review)
        │            │                                  │
        ▼            ▼                                  ▼ index
  [phần semantic]  [1] RULE PROJECTOR              Qdrant read-index
        │            │ (chiếu phần checkable)      (slice cho subagent)
        │            ▼
        │          ruleset (Checkstyle/PMD — derived, KHÔNG sửa tay)
        │            │
        │            ▼
        │     ┌──── ORCHESTRATOR /task apply ──── topo-sort task (base trước)
        │     │              │ tuần tự
        ▼     ▼              ▼
   [3] CODING MICRO-LOOP (mỗi task = 1 subagent context sạch)
        │  prompt = [DNA slice + spec slice + snapshot slice(Qdrant)
        │            + 1 task + tóm tắt file đã ghi]
        │  subagent đọc file cũ từ DISK → sinh code CHỈ task này
        │            │
        ▼            ▼
   [2] MECHANICAL GATE (git hook, DETERMINISTIC) ← chạy ruleset đã sinh
        │  FAIL → feedback subagent fix; PASS → mark [x] OpenSpec task → next
        ▼ (hết task)
   [4] EXTRACTION REVIEW (1 subagent thấy TẤT CẢ file mới) → HP-10/11
        enumerate siêu class qua UA graph (KHÔNG vector top-k)

   agentmemory/Qdrant ── SỞ HỮU RIÊNG: tầng kinh nghiệm episodic (gotcha per-ticket)
```

### 4.3 Ba ý tưởng cốt lõi giải đúng triệu chứng

1. **"Không tuân author-dna"** → fix bằng *hai* cơ chế:
   - **(A) Mechanical gate** — rule cơ học bị git hook chặn deterministic. Model không thể "quên".
   - **(B/C) Surface nhỏ** — rule ngữ nghĩa check trên 1 task, nơi attention còn dồi dào.
2. **"Miss update OpenSpec task"** → fix bằng cấu trúc: mark task done là *bước đóng vòng lặp*,
   không phải việc nền. Không advance được nếu chưa mark.
3. **State chia sẻ qua FILESYSTEM, không qua context** → subagent Task 2 đọc `BaseXHandler.java`
   mà Task 1 vừa ghi ra đĩa. "Context sạch" và "nhất quán kế thừa" không còn mâu thuẫn.

### 4.4 Rule Projector — tránh bẫy linter cũ

Vì `author-dna`/`conventions`/`knowledge-snapshot` là **file sống** (đổi theo R-DNA-7 / knowledge-curator),
linter **không được viết tay** (sẽ thành đồ cổ khi DNA đổi). Nó là **artifact sinh ra TỪ DNA**:

- DNA vẫn là single source of truth; linter chỉ là *hình chiếu cơ học*.
- Đổi DNA → regenerate → ruleset mới. Sync-check trong git hook: DNA đổi mà ruleset chưa
  regenerate → FAIL.
- Chỉ chiếu entry `mechanically_checkable: true` **và** `status: approved` (draft bị skip).
- **Vòng khép kín đẹp:** teaching moment giữa Pha 3 → update DNA → regenerate → áp dụng luôn cho
  task tiếp theo trong cùng vòng lặp.

**Chiếu cụ thể lên DNA hiện tại:**

| DNA entry | Chiếu được? | Thành gì |
|---|---|---|
| `complexity_thresholds` (nesting≤1, branches≤3, lines≤30, early_return) | ✅ | Checkstyle metrics |
| HP-6 zero nesting, HP-7 no else | ✅ | AST rule |
| SP-5 javadoc `@author/@since`, SP-6 field ordering | ✅ | presence/format check |
| `conventions` naming_patterns | ✅ | regex |
| HP-1/2/3/5/9/10/11 (CoR, Template Method, Strategy, Factory boundary, config-driven, extraction) | ❌ semantic | → context subagent + extraction review |
| HP-8 SOLID | ❌ phần lớn semantic | → subagent + extraction review |

### 4.5 Memory layout — hybrid (quyết định đã chốt)

- **knowledge-snapshot.md = source of truth** (versioned, review được, git diff, gate draft→approved).
- **Qdrant = derived read-index** sinh từ file, để subagent truy hồi *slice liên quan* nhét vào
  context nhỏ. Regenerate khi file đổi.
- **agentmemory/Qdrant sở hữu RIÊNG tầng kinh nghiệm episodic** (gotcha per-ticket) — nơi vector
  search thật sự toả sáng.
- ⚠️ **Không dời hẳn snapshot vào Qdrant**: mất git diff, mất gate draft→approved, retrieval lossy
  có thể miss base class → đi ngược bệnh đang chữa.
- ⚠️ **Enumeration đầy đủ (HP-10/11)** dùng UA graph / đọc nguyên section file, **KHÔNG** vector top-k.
- ⚠️ **Tránh overlap**: UA graph = cấu trúc code (auto-extract); knowledge-snapshot = lớp phủ
  *được curate* (business rule, ý nghĩa config table, cái "tại sao"). Đừng để snapshot tan vào
  vector blob trùng vai UA graph.

---

## 5. Đụng vào gì trong framework hiện tại (blast radius)

| File hiện tại | Thay đổi |
|---|---|
| `task.md` Pha 3 | **Viết lại**: "một lần apply" → vòng lặp orchestrated subagent |
| `spec-validator` §6 `post_apply_dna_check` | **Tách đôi**: rule cơ học → Lớp A (deterministic); semantic → giữ, chạy surface nhỏ |
| DNA-RELOAD (task.md bước 2a) | **Phần lớn nghỉ hưu**: reload thành *cấu trúc* (DNA slice trong context subagent), không phải *nghi thức* |
| `spec-validator` pre_apply_gate / ac_coverage / post_apply_verify | **Giữ nguyên** |
| `author-dna.yaml` / `conventions.yaml` schema | **Thêm field** `mechanically_checkable: bool` + `check_spec` |
| Mới | Rule Projector, ruleset sinh ra, Qdrant indexer cho snapshot |

---

## 6. Build order (3 increment độc lập, giảm rủi ro)

1. **Increment 1 — Lớp A (giá trị ngay, độc lập):** Schema field + Rule Projector + Mechanical Gate
   qua git hook. Biến "deterministic" thành sự thật cho ~50% DNA. Ship được mà chưa cần micro-loop.
2. **Increment 2 — Micro-loop (B/C):** Viết lại Pha 3 thành orchestrated sequential subagent +
   extraction review.
3. **Increment 3 — Qdrant index cho snapshot:** chỉ cần khi snapshot phình to; tối ưu context
   curation cho subagent.

---

## 7. Phân rã dự án lớn

| Sub-project | Nội dung | Ưu tiên |
|---|---|---|
| **SP1 — Phase 3 Reliability** | Mục 4–6 ở trên. Sửa cái đang chảy máu. | **Làm trước** |
| **SP2 — Portability layer** | Tách Core (phases, memory layer, transparency) khỏi Project Pack (DNA, conventions, tool adapter); tool-capability interface để workflow phụ thuộc *năng lực trừu tượng* (`propose_spec`, `explore_code`, `query_graph`) thay vì tool cụ thể (OpenSpec, UA MCP). | Sau SP1 |

**Lưu ý portability:** Lớp A (git hook) framework-agnostic sẵn → chạy trên mọi platform (git là
mẫu số chung). Lớp B/C cần subagent — Claude Code có; framework không có subagent degrade về
"micro-loop tuần tự cùng context" (vẫn hơn monolithic). Rule Projector nên sinh **IR trung lập
(JSON)** trước, backend dịch sang Checkstyle/PMD — sau này thêm ngôn ngữ chỉ thêm backend.

---

## 8. Khuyến nghị ưu tiên (TL;DR)

1. **Ngay:** Increment 1 — đưa rule cơ học của DNA vào git hook qua Rule Projector. Đây là thứ
   biến "deterministic" từ khẩu hiệu thành sự thật, và là bước portable đầu tiên.
2. **Kế tiếp:** Increment 2 — chẻ Pha 3 thành sequential subagent micro-loop để khử context
   dilution và ép OpenSpec task-update thành ranh giới vòng lặp.
3. **Song song, dài hạn:** Bổ sung **outcome loop** (W6) — log chất lượng để biết rule nào đáng
   giữ, prune rule chết, chống rule bloat.
4. **Khi mở rộng đa team:** Giải bài toán **DNA đơn-tác-giả** (W8) — cơ chế merge/namespace DNA
   nhiều tác giả.
