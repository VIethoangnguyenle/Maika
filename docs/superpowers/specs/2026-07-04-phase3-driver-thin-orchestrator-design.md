# Design: Pha 3 Driver — vòng lặp apply chạy bằng code, không phải LLM

> Trạng thái: design đã chốt với user (2026-07-04)
> Branch: `feat/phase3-driver` (stack trên `feat/task-run-quality-thin-orchestrator` — phụ thuộc `dispatch_worker`/`make_worker_runner`/`worker_command` đã merge ở đó)
> Kế thừa: `docs/superpowers/specs/2026-07-03-task-run-quality-thin-orchestrator-design.md` (phần B — spec này code-hóa đường vận hành mà phần B mô tả bằng text; xem §Đóng dấu R6)

---

## 1. Vấn đề & bằng chứng

**Pattern lỗi lặp lại:** mỗi lần gặp sự cố vận hành, framework phản xạ bằng cách **thêm gate/rule mới**. Hiện trạng: 48 rule heading trong 5 file `rules/*.md`; audit TODOS.md 2026-06-20 kết luận phần lớn rule `[CRITICAL]` chỉ "trên giấy" (không được hook chặn cơ học). Chuỗi leo thang gần nhất: session-boundary warning (text) → SESSION-GATE (hook) → R-Flow-5/6 (text) — ba tầng cho cùng một mối lo context-overflow.

**Vì sao rule text không scale** (chi phí đã quan sát):

1. **Thuế context**: rule nạp lúc bootstrap ăn vào context làm việc; càng nhiều rule càng compact sớm → càng quên rule — vòng luẩn quẩn tự phá.
2. **Quá tải tuân thủ**: instruction-following giảm khi số ràng buộc tăng; agent rụt rè, sản xuất compliance theater.
3. **False positive tích lũy** qua từng gate; override thành thói quen → gate thành dead letter.
4. **Goodhart**: agent tối ưu để *qua gate* thay vì làm đúng.

**Observed failures neo spec này (R3):**

- 2026-07-03, downstream Antigravity: context tràn/compact làm mất rules/DNA → agent code cảm tính ở Pha 3 (đã neo spec task-run-quality; spec này là bước triệt để hơn cho cùng lỗi đó).
- Khối "Dashboard runtime contract (P5)" trong `task.md` §3 bước 5 = ~20 dòng dặn LLM emit event đúng thứ tự — chính là loại trách nhiệm trình tự mà LLM quên khi context loãng, trong khi code không bao giờ quên.

## 2. Nghiên cứu nền (OSS agent frameworks)

| Nguồn | Bài học | Quyết định chịu ảnh hưởng |
|---|---|---|
| [Anthropic — Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents) (fetch 2026-07-04) | **Workflows** = "LLMs and tools are orchestrated through *predefined code paths*"; **Agents** = "LLMs dynamically direct their own processes". *"Workflows offer predictability and consistency for well-defined tasks."* | Pha 3 có DAG chốt sẵn → thuộc định nghĩa workflow → code cầm vòng lặp |
| Anthropic, cùng bài — pattern orchestrator-workers | Orchestrator là LLM **chỉ khi** "subtasks cannot be pre-defined". Maika decompose ở Pha 2 (LLM) → Pha 3 subtask đã định trước → orchestrator không cần là LLM | Chặn trước phản biện "Anthropic bảo orchestrator là LLM" |
| [LangGraph](https://www.metacto.com/blogs/a-developer-s-guide-to-langgraph-building-stateful-controllable-llm-applications) | Control flow tường minh trong code; `interrupt()` + checkpointer là primitive human-in-the-loop; *"adopt it when control flow is the actual problem"* | Blocked → exit → parent hỏi user → chạy lại = resume. `RUNTIME_QUEUE` + `next_task` (resume-first) đã là checkpointer — không xây mới |
| [SWE-agent ACI](https://arxiv.org/abs/2405.15793) | Hiệu năng tăng nhờ **thiết kế interface** (lệnh tối giản, guardrail nằm trong tool), không phải thêm prompt rule | Preconditions cơ học trong driver thay ~10 dòng rule text; một lệnh duy nhất thay N lời dặn |
| OpenHands (training knowledge) | Event-stream append-only ngoài context; sandbox là capability boundary | Xác nhận `knowledge/active/` + `ACTIVITY_LOG.jsonl` đã đúng — driver ghi vào đúng chỗ cũ, không sinh cơ chế mới |
| CrewAI / AutoGen (training knowledge) | Budget là tham số code (`max_turns`…), không phải lời dặn | Driver tiêu thụ `max_retries`/`worker_timeout_seconds` có sẵn, không thêm knob |

**Bài học âm** (điều cố ý KHÔNG làm): không import framework (lấy pattern, bỏ package — giữ ràng buộc stdlib+PyYAML); không state-machine-hóa Pha 1/2 (cần flexibility thật — đúng ranh giới workflow/agent của Anthropic); không giải quyết reliability bằng thêm prompt rule (không framework nghiêm túc nào làm vậy).

## 3. Quyết định scope (đã chốt với user)

1. **Pha 3 driver trước** — không state-machine toàn lifecycle (Pha 1/2 chưa có observed failure về vận hành; PR nhỏ ship được).
2. **Phủ cả 3 platform** — Claude Code đổi default sang `fresh-session` + `worker_command: 'claude -p {prompt}'`. Trade-off chấp nhận: bỏ Agent-tool integration ở đường default; mode `subagent` **vẫn là giá trị hợp lệ** user chọn được qua yaml, `tiers/subagent.py` không xóa.
3. **Rule pruning cùng spec** — text bị driver thay thế phải xóa/thu gọn trong cùng PR (R7 net-negative); "pruning sau" bị từ chối vì thường không bao giờ xảy ra.

## 4. Thiết kế

### 4.1 Kiến trúc & luồng chạy

Nguyên tắc phân công: **LLM làm việc ngữ nghĩa, code làm việc trình tự.**

```text
Parent agent (LLM)                          Driver (Python, không LLM)
──────────────────                          ──────────────────────────
Pha 1: hiểu đề (hỏi-đáp user)
Pha 2: spec + CONTRACT_DAG (confirm user)
Pha 3 chuẩn bị: KNOWLEDGE_PACK,
  TASK_HANDOFF.<node>.md per node,
  initialize_runtime_queue
Confirm cuối với user
        │
        └──▶ python3 {{ platform.framework_root }}/tools/microloop-orchestrator/orchestrator.py apply \
                 --active-dir <knowledge/active>
                    │
                    ├─ kiểm preconditions (§4.2) — fail thì từ chối chạy
                    ├─ đọc execution-mode.yaml (đã render) → worker_command, timeout, max_retries
                    ├─ load_runtime_queue → run_loop(queue, dispatch_fn, gate_fn, max_retries)
                    │    dispatch_fn = tiers/fresh_session.dispatch(handoff, result)
                    │                  → dispatch_worker(prompt, make_worker_runner(...),
                    │                                    active_dir=…, task_id=…)
                    │    gate v1    = worker exit 0 + TASK_RESULT tồn tại (executor tự chạy
                    │                 gate dự án; checkstyle driver-side chờ evidence — R3)
                    ├─ save_runtime_queue sau mỗi node (crash-safe)
                    └─ exit 0: tất cả done │ exit ≠0: node blocked / precondition fail
                       + in báo cáo tóm tắt (node done/blocked, lý do) ra stdout
        │
Parent đọc báo cáo + TASK_RESULT
  ├─ done hết → semantic review 1 lần (post_apply_verify) → tiếp bước 6-9 Pha 3
  └─ blocked → hỏi user / sửa handoff → chạy lại driver (resume tự nhiên:
       next_task resume-first, skip node done — checkpointer có sẵn)
```

**Không xây cơ chế mới** (R5): `run_loop`, `next_task` (resume-first), `apply_result` (retry→blocked), `dispatch_worker`, `make_worker_runner`, `make_gate_fn`, queue I/O, event log — tất cả đã tồn tại và đã có test. Driver = 1 hàm `apply_command(active_dir)` lắp ráp chúng + argparse `main()`. Ước lượng ≤ ~80 dòng gồm docstring.

**Semantic surface-check per node**: v1 không đưa vào driver (tránh nhân đôi chi phí worker). Mechanical gate per node trong driver; parent review ngữ nghĩa một lần sau khi driver xong. Nếu sau này có observed failure kiểu "gate cơ học pass nhưng node sai ngữ nghĩa hàng loạt" → cân nhắc reviewer-worker per node ở spec sau (R3).

**Event emission**: driver emit `subagent_started`/`subagent_blocked` (qua `dispatch_worker` có sẵn), `update_task_status` emit event chuyển trạng thái; `task_queue_created` do parent emit khi `initialize_runtime_queue` (đã có) — driver không emit lại. Worker vẫn tự emit `result_written`/`subagent_done` qua `write_task_result` — giữ phân công tránh double-emission như spec 2026-07-03.

### 4.2 Preconditions cơ học (thay rule text)

Driver **từ chối chạy** với exit code ≠ 0 + message một dòng nêu lý do, khi:

| Precondition | Thay cho rule text nào |
|---|---|
| `microloop/TASK_QUEUE.md` tồn tại, parse được, có ≥1 task | Lời dặn "tạo TASK_QUEUE trước khi dispatch" |
| Mỗi task pending có `TASK_HANDOFF.<id>.md` tồn tại | "Chỉ được code khi có handoff" (~10 dòng §2 bước 10) |
| `KNOWLEDGE_CHECKPOINT.md` tồn tại (v1 chỉ check tồn tại — validation sâu đã có write-gate lo tại thời điểm worker ghi file, không nhân đôi validator per R5) | Nhánh checkpoint của preflight |
| `worker_command` không rỗng sau render | Nhánh "platform không hỗ trợ fresh-session" |

Nguyên lý ACI: agent không cần *nhớ* điều kiện — lệnh không chạy nếu điều kiện sai, message chỉ thẳng cách sửa.

### 4.3 execution-mode.yaml (thay đổi duy nhất ngoài orchestrator + docs)

```yaml
{% if platform.name == "claude-code" %}
execution_mode: fresh-session
worker_command: 'claude -p {prompt}'
{% endif %}
```

(antigravity/codex giữ nguyên như đã merge; nhánh else giữ `inline-reload`.) Mode `subagent` vẫn hợp lệ — khi user tự đổi yaml, parent agent vận hành như task.md mô tả cho tier đó.

### 4.4 Danh sách xóa/thu gọn (điểm chứng minh "structure thay rule")

| Chỗ | Hiện tại | Sau |
|---|---|---|
| `task.md` §3 bước 5, khối "Dashboard runtime contract (P5)" + 5.c/5.d vận hành loop | ~40 dòng dặn LLM tự emit event, mark status, dispatch, retry, escalate | ~10 dòng: preconditions + lệnh driver + xử lý exit blocked. Nhánh `subagent`/`inline-reload` giữ bản rút gọn |
| `task.md` §2 bước 10, §3 bước 9 (session-boundary nhánh fresh-session) | Warning text nhiều nhánh | Thu gọn: đường chính là driver; giữ nhánh inline-reload |
| `rules-flow.md` R-Flow-5 | Mô tả cơ chế dispatch dài | Giữ nguyên tắc + trỏ "Pha 3: xem driver"; không mô tả lại cơ chế |
| Spec 2026-07-03 phần B | Mô tả LLM gọi dispatch_worker thủ công | Đóng dấu: `Cập nhật 2026-07-04: đường vận hành Pha 3 được code-hóa bởi <spec này> — mô tả LLM-driven trong §B là lịch sử` (R6, partial supersede) |

**Tiêu chí cứng: diff tổng của text hướng dẫn/rule (task.md + rules-flow.md) phải ÂM.** Driver không thêm gate mới nào; SESSION-GATE giữ nguyên không đổi một dòng (worker = process mới → identity khác → pass; parent code inline → block — lưới an toàn khớp hoàn hảo kiến trúc mới).

## 5. Điểm cần xác minh khi implement (R4 — verify trước, code sau)

Mỗi claim phải có một dòng dẫn chứng (lệnh + output) trong plan/PR trước khi code phần phụ thuộc:

1. `claude -p {prompt}`: chạy non-interactive, có quyền ghi file trong project, exit code ≠ 0 khi fail. (Nghi vấn: cần `--permission-mode`/`--dangerously-skip-permissions` hay settings để worker ghi file không bị prompt? Phải verify flag thật.)
2. `agy -p {prompt}`: như trên (đã claim ở spec 2026-07-03, PR body rollout checklist — vẫn chưa verify thật).
3. `codex exec {prompt}`: như trên.
4. `execution-mode.yaml` sau render trên scaffold claude-code thật sự ra `fresh-session` + worker_command đúng (test render đã có pattern từ review 2026-07-04).
5. Driver chạy được bằng `python3` hệ thống trên scaffold (không giả định venv; orchestrator.py hiện chỉ dùng stdlib+PyYAML — giữ nguyên).

Nếu (1)–(3) có CLI không đáp ứng (vd không cho ghi file ở print mode): platform đó **degrade về đường cũ** (parent agent vận hành theo task.md bản rút gọn cho tier tương ứng) — driver không ship blind cho platform chưa verify.

## 6. Testing & tiêu chí thành công

**Unit (orchestrator tests, pattern injectable có sẵn):**

- `apply_command` happy path: queue 2 node → done hết, exit 0, event đúng chuỗi.
- Blocked path: worker fail quá budget → dừng đúng node, exit ≠ 0, queue lưu trạng thái.
- Resume: chạy lại sau blocked → skip node done, tiếp node dở.
- Preconditions: thiếu queue / thiếu handoff / worker_command rỗng → refuse, message đúng.
- Cross-OS: fake worker bằng `sys.executable`, không lệnh POSIX-only (CI matrix ubuntu+windows).

**Litmus tích hợp** (fixture R3 cho mọi tranh luận enforcement sau này): queue giả 2 node + fake worker script (python) ghi TASK_RESULT → driver end-to-end; case fail-then-resume.

**Thành công khi:**

1. Litmus + unit pass cả CI matrix.
2. Diff text hướng dẫn/rule âm (đếm dòng task.md + rules-flow.md trước/sau).
3. Zero gate mới trong PR.
4. Rollout Antigravity 2 tuần: lỗi 2026-07-03 không tái hiện (parent context Pha 3 chỉ còn báo cáo driver).

## 7. Đối chiếu DEVELOPMENT_RULES

- **R1**: entry `apply` có consumer ngay trong PR (task.md §3 gọi nó; litmus chạy nó).
- **R2**: không thêm platform/variant; mode subagent vẫn trong registry giá trị hợp lệ.
- **R3**: neo observed failure 2026-07-03 + litmus tái hiện được ship cùng PR.
- **R4**: §5 là checklist verify bắt buộc trước code.
- **R5**: không gate mới — lắp ráp cơ chế đang chạy (run_loop, dispatch_worker, gate_fn, queue).
- **R6**: đóng dấu partial-supersede spec 2026-07-03 §B trong cùng PR.
- **R7**: diff text hướng dẫn âm là tiêu chí cứng; driver ≤ ~80 dòng.

## 8. Non-goals

- Không state-machine Pha 1/2 (chưa có observed failure vận hành).
- Không semantic reviewer per node (chờ evidence).
- Không capability scoping per phase / tool policy (tầng 4 — spec riêng khi có evidence).
- Không đổi SESSION-GATE, không đổi hook nào.
- Không thêm subcommand `maika task` vào CLI pip (scaffold tự chứa là đủ; alias CLI là speculative — R7).
