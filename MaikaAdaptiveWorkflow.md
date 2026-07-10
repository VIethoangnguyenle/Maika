# Maika Adaptive Workflow & Token-Efficiency Plan

## 1. Mục tiêu

Nâng cấp Maika theo ba nguyên tắc:

1. Task nhỏ phải hoàn thành nhanh, ít artifact, ít worker và ít token.
2. Task có rủi ro cao vẫn phải đi qua grounding, spec, review và verification đầy đủ.
3. Workflow được nâng cấp dựa trên evidence thực tế, không dựa trên cảm giác của agent.

Nguyên tắc thiết kế trung tâm:

> Default lightweight, escalate on evidence.

Maika phải nghiêm ở các invariant an toàn, nhưng linh hoạt ở số lượng phase và artifact.

---

## 2. Các invariant áp dụng cho mọi task

Dù task thuộc class nào, runtime vẫn phải đảm bảo:

* Không ghi file ngoài scope được khai báo.
* Có evidence tối thiểu trước khi sửa code.
* Không tự ý thay đổi public contract, database, security hoặc architecture mà không nâng risk class.
* Có verification thực tế trước khi đánh dấu hoàn thành.
* Không ghi secret, credential hoặc PII vào knowledge artifacts.
* State transition phải đi qua một canonical state machine.
* Artifact stale hoặc hash mismatch phải fail closed.

Các invariant trên là safety kernel và không được bỏ qua bởi fast path.

---

## 3. Mô hình phân loại task

Giữ bốn class:

### `trivial`

Áp dụng khi:

* Sửa typo, comment hoặc documentation.
* Đổi tên nội bộ với phạm vi rõ ràng.
* Thay đổi một file, không đổi behavior.
* Không ảnh hưởng public contract, persistence, concurrency hoặc security.

Workflow:

```text
Inspect → Change → Verify
```

Artifact:

```text
TASK.yaml
```

Giới hạn:

* 1 worker.
* Không independent review.
* Không SPEC.md.
* Không RECONCILIATION.md.
* Không skill-learning candidate mặc định.

---

### `small`

Áp dụng khi:

* Thay đổi behavior nhỏ trong một module.
* Blast radius rõ ràng.
* Không thay đổi API công khai, database schema, event contract hoặc security.
* Có test cục bộ xác nhận được.

Workflow:

```text
Focused Grounding → Mini Plan → Change → Verify
```

Artifact:

```text
TASK.yaml
EVIDENCE.yaml
RESULT.yaml
```

Giới hạn:

* Tối đa 2 worker calls.
* Không full architecture reconciliation.
* Review chỉ kích hoạt khi có retry, uncertainty hoặc test failure.
* Knowledge impact mặc định là `none`, trừ khi phát hiện lesson đáng tái sử dụng.

---

### `standard`

Áp dụng khi có một trong các tín hiệu:

* Thay đổi public API hoặc service contract.
* Thay đổi database query, persistence behavior hoặc transaction boundary.
* Thay đổi Kafka, event, retry, timeout hoặc concurrency behavior.
* Ảnh hưởng nhiều module.
* Có business rule hoặc trạng thái phức tạp.
* Có uncertainty chưa được giải quyết.

Workflow:

```text
Intent
→ Grounding
→ Reconciliation
→ Spec
→ Plan
→ Plan Review
→ Execute
→ Task Review
→ Final Review
→ Verify
→ Archive
```

Artifact đầy đủ được giữ nguyên.

---

### `architectural`

Áp dụng khi:

* Thay đổi kiến trúc hệ thống.
* Thay đổi cross-service protocol.
* Migration dữ liệu hoặc compatibility concern.
* Security, permission hoặc compliance.
* Infrastructure, deployment hoặc distributed consistency.
* Blast radius lớn hoặc rollback khó.

Ngoài full standard workflow, bắt buộc:

* TDD hoặc ADR.
* Human confirmation trước apply.
* Independent architecture review.
* Rollback plan.
* Multiple real verification commands.

---

## 4. Risk classifier

Thêm một classifier cơ học chạy ngay sau intake.

Input:

```yaml
risk_signals:
  estimated_files:
  affected_modules:
  public_contract_changed:
  database_changed:
  event_contract_changed:
  transaction_changed:
  concurrency_changed:
  security_changed:
  migration_required:
  rollback_complexity:
  unknown_count:
```

Quy tắc:

* Không có risk signal: `trivial` hoặc `small`.
* Có một contract hoặc persistence signal: tối thiểu `standard`.
* Có security, migration, infrastructure hoặc cross-service signal: `architectural`.
* Agent được phép nâng class khi tìm thấy evidence mới.
* Agent không được tự hạ class sau khi risk signal đã được xác nhận.
* Việc hạ class phải có human approval hoặc deterministic classifier chứng minh.

Output:

```yaml
classification:
  proposed_class: small
  evidence:
    - ...
  escalation_triggers:
    - public_contract_detected
    - affected_modules_above_1
```

---

## 5. Escalation model

Workflow luôn bắt đầu bằng path nhẹ nhất phù hợp với classifier.

Trong quá trình thực thi, tự động escalate khi phát hiện:

* File ngoài expected scope.
* Dependency hoặc downstream consumer chưa được tính.
* Public API hoặc event contract thay đổi.
* Database/schema/transaction impact.
* Concurrency, retry hoặc timeout behavior.
* Security hoặc permission impact.
* Không đủ evidence.
* Test failure cho thấy blast radius lớn hơn dự kiến.
* Cần sửa hơn số file/module cho phép.
* Agent phải đưa ra assumption có confidence thấp.

Ví dụ:

```text
small
→ phát hiện Kafka acknowledgment thay đổi
→ block write
→ escalate thành standard
→ sinh grounding/spec/plan đầy đủ
```

Không được tiếp tục fast path sau khi escalation trigger xuất hiện.

---

## 6. Artifact tối giản cho task nhỏ

Tạo schema `TASK.yaml`:

```yaml
version: 1
change_id: rename-stage-field
class: small

intent:
  summary: Rename stageName to localizedStageName.

scope:
  files:
    modify:
      - src/.../StageResponse.java
      - src/.../StageMapper.java
    test:
      - src/test/.../StageMapperTest.java

evidence:
  - id: CODE-001
    source: src/.../StageResponse.java
    statement: stageName is only mapped by StageMapper.

plan:
  - Rename the field.
  - Update mapper references.
  - Run affected tests.

verification:
  commands:
    - ./gradlew test --tests StageMapperTest

escalation_triggers:
  - additional_consumer_found
  - public_json_contract_changed
```

Với `trivial` và `small`, artifact này thay thế:

* `INTENT.md`
* `RECONCILIATION.md`
* `SPEC.md`
* `IMPLEMENTATION_PLAN.md`

Full artifacts chỉ được tạo khi task escalate.

---

## 7. Token budget

Thêm budget theo class:

```yaml
token_budget:
  trivial:
    max_context_tokens: 8000
    max_worker_calls: 1
    max_evidence_items: 5

  small:
    max_context_tokens: 20000
    max_worker_calls: 2
    max_evidence_items: 12

  standard:
    max_context_tokens: 60000
    max_worker_calls: 6
    max_evidence_items: 30

  architectural:
    max_context_tokens: 120000
    max_worker_calls: 12
```

Khi gần vượt budget:

1. Reuse evidence đã có.
2. Compress current context.
3. Chỉ retrieve knowledge slice cần thiết.
4. Nếu vẫn thiếu, escalate hoặc block với lý do rõ ràng.

Không được tự động tiếp tục vô hạn.

---

## 8. Knowledge slice loading

Không load toàn bộ:

* knowledge graph;
* conventions;
* author DNA;
* archives;
* previous task contexts.

Quy trình:

```text
Task type
→ expected artifact types
→ required knowledge categories
→ retrieve relevant IDs
→ load compact slices
```

Ví dụ Java mapper:

```text
Load:
- mapper conventions
- null-handling rules
- nearby examples

Do not load:
- Kafka rules
- database migration rules
- unrelated architecture history
```

Mỗi knowledge entry cần có:

```yaml
id:
type:
statement:
applies_to:
source:
source_commit:
affected_paths:
confidence:
freshness:
status:
```

---

## 9. Evidence reuse

Evidence được phép reuse khi:

* Source commit hoặc relevant path digest chưa đổi.
* Task mới nằm trong cùng scope.
* Claim chưa bị superseded.
* Confidence phù hợp với risk class.

Chỉ revalidate khi:

* Relevant paths thay đổi.
* Claim quá cũ.
* Task yêu cầu authority cao hơn.
* Có conflict mới.
* Task thuộc `architectural`.

Thêm metric:

```yaml
evidence_metrics:
  retrieved:
  reused:
  revalidated:
  newly_created:
```

Mục tiêu là tỷ lệ evidence reuse tăng dần qua các task tương tự.

---

## 10. Verification policy

Khắc phục việc task có thể hoàn thành mà không chạy command thực.

```yaml
verification_policy:
  trivial:
    minimum_real_commands: 0

  small:
    minimum_real_commands: 1

  standard:
    minimum_real_commands: 1
    required_categories:
      - test_or_build

  architectural:
    minimum_real_commands: 2
    required_categories:
      - build
      - test
```

Một command chỉ được tính là real verification khi:

* Được thực thi thật.
* Có exit code.
* Có observed output.
* Không phải internal marker.
* Phù hợp với change scope.

Không cho `standard` hoặc `architectural` chuyển sang `COMPLETED` nếu không có real verification command.

---

## 11. Command execution safety

Không chạy trực tiếp agent-authored command bằng unrestricted `shell=True`.

Thêm command policy:

```yaml
allowed_executables:
  - ./gradlew
  - mvn
  - pytest
  - npm
  - pnpm
  - go
  - cargo
  - git

requires_human_confirmation:
  - docker
  - kubectl
  - terraform
  - database migration tools

denied_patterns:
  - rm -rf
  - sudo
  - curl * | sh
  - wget * | bash
```

Ưu tiên structured command:

```yaml
command:
  executable: ./gradlew
  args:
    - test
    - --tests
    - StageMapperTest
```

Thực thi bằng `shell=False`.

---

## 12. State-machine hardening

Chỉ giữ một module được phép ghi `STATE.yaml`.

Tất cả CLI, orchestrator, verification và archive phải gọi:

```python
transition(
    workspace,
    target_state,
    evidence=None,
    blocked=None,
)
```

Bổ sung:

* Atomic state write.
* Workspace lock.
* Queue version.
* Task lease.
* Recovery cho orphan `in_progress`.
* `BLOCKED` chỉ resume về `resume_state`.

Không được ghi state trực tiếp trong test E2E hoặc production module.

---

## 13. Continuous improvement có kiểm soát

Không tạo learning candidate cho mọi task.

Chỉ capture candidate khi có:

* Human correction.
* Repeated failure.
* Unexpected blast radius.
* Review finding có khả năng tái diễn.
* Convention quan sát qua nhiều ví dụ.
* Một technique làm giảm retry hoặc token đáng kể.

Candidate phải đi qua:

```text
Observation
→ Candidate
→ Evidence aggregation
→ Independent review
→ Evaluation
→ Promotion or rejection
```

Không cho agent tự sửa skill rồi dùng ngay.

---

## 14. Metrics

Dashboard và archive phải ghi:

```yaml
runtime_metrics:
  task_class:
  total_tokens:
  worker_calls:
  tool_calls:
  evidence_reuse_ratio:
  time_to_first_change:
  retry_count:
  review_findings:
  real_verification_commands:
  human_corrections:
  knowledge_entries_created:
  knowledge_entries_reused:
```

Mục tiêu:

* Task nhỏ dùng ít token hơn.
* Task tương tự sau này dùng ít token hơn task trước.
* First-pass approval rate tăng.
* Retry và human correction giảm.
* Knowledge được reuse thật, không chỉ được lưu.

---

## 15. Thứ tự triển khai

### Phase 0 — Correctness blockers

* Sửa public transition `INTAKE → EXPLORING`.
* Thêm public E2E không chỉnh trực tiếp `STATE.yaml`.
* Bắt buộc real verification cho `standard/architectural`.
* Centralize state mutation.
* Bỏ production fallback `echo stub`.

### Phase 1 — Adaptive workflow

* Risk classifier.
* Fast path cho `trivial/small`.
* `TASK.yaml` mini artifact.
* Escalation triggers.
* Verification policy theo class.

### Phase 2 — Token efficiency

* Knowledge slice loading.
* Evidence reuse và path-based freshness.
* Token/tool-call budget.
* Context compression.
* Runtime metrics.

### Phase 3 — Runtime hardening

* Command policy.
* Workspace lock.
* Atomic writes.
* Queue version và task lease.
* Structured review verdict.
* Controlled BLOCKED resume.

### Phase 4 — Continuous improvement

* Learning candidate threshold.
* Evaluation harness.
* Candidate benchmark.
* Promotion/canary/rollback.
* Skill effectiveness tracking.

---

## 16. Exit criteria

Implementation chỉ được coi là hoàn thành khi:

* `trivial` task không tạo full artifact chain.
* `small` task có thể hoàn thành bằng tối đa 2 worker calls.
* `standard` task vẫn bắt buộc full reasoning workflow.
* Runtime tự escalate khi phát hiện contract/DB/event/security impact.
* `standard/architectural` không thể verify nếu thiếu real command.
* Không production module nào ngoài state service ghi `STATE.yaml`.
* E2E test chạy toàn bộ public CLI path.
* Token metrics được ghi cho mọi task.
* Knowledge slice được load theo scope, không load toàn bộ.
* Learning candidate không được tạo cho task bình thường không có lesson mới.
