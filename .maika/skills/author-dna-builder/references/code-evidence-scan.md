# Code Evidence Scan & Hypothesis Generation

> Reference file — extracted from SKILL.md for progressive disclosure.

## Mục lục

- GIAI ĐOẠN 1: Code Evidence Scan
- GIAI ĐOẠN 2: Hypothesis Generation

## GIAI ĐOẠN 1: Code Evidence Scan

Mục tiêu: Thu thập evidence thực tế từ codebase, không infer intent.

### 1A. Complexity Profile

```
CALL: {{ tools.graph_stats }}()
  → Lấy tổng số class, method, package

QUERY UA: {{ tools.search_code }}(type="method", limit=500)
  → Lấy tất cả method
  FOR EACH method:
    GET: {{ tools.read_file }}(node_id)  [chỉ lấy method body, không full class]
    ANALYZE:
      - Đếm số if/else/switch/ternary trong body
      - Đếm độ sâu lồng nhau (nesting depth)
      - Đếm số early return
      - Đếm số dòng
    CLASSIFY:
      complexity_score = if_count + (nesting_depth * 2) + switch_count
      complexity_label = HIGH (>10) | MEDIUM (4-10) | LOW (0-3)

AGGREGATE:
  - Distribution: % method LOW / MEDIUM / HIGH complexity
  - Top 5 method complexity cao nhất (có thể là legacy)
  - Top 5 method clean nhất (exemplar của style)
  - Average nesting depth toàn codebase
  - Early return frequency: tổng early return / tổng method
```

### 1B. Design Pattern Detection

```
QUERY UA: {{ tools.search_code }}(type="class", filter="name matches pattern")
  Patterns cần tìm:
  - Chain of Responsibility: *Processor, *Handler với field "next" hoặc list<>
  - Strategy: I*Strategy, *Strategy implements I*
  - Factory: I*Factory, *Factory với method create/build/make
  - Specification: *Specification, *Spec với method isSatisfiedBy
  - Builder: *Builder với method chain (return this)
  - Decorator: *Decorator wraps *
  - Template Method: abstract class với protected method
  - Observer: *Listener, *Observer, *EventHandler
  - Command: *Command với execute() method

  FOR EACH pattern found:
    GET: {{ tools.get_dependencies }}(node_id) để verify structure đúng pattern
    RECORD:
      - pattern_name
      - occurrence_count
      - exemplar_node_id (class đơn giản nhất, dễ đọc nhất)
      - exemplar_file_path
```

### 1C. If/Else vs Pattern Substitution Detection

```
Mục tiêu: Tìm bằng chứng TÁC GIẢ ĐÃ CHỦ Ý thay thế if/else bằng pattern.

STRATEGY: So sánh "nơi nên có if/else nhưng không có" với "pattern được dùng thay thế"

QUERY UA: {{ tools.search_code }}(type="class", filter="implements *Factory OR *Strategy")
  FOR EACH factory/strategy:
    GET: {{ tools.read_file }}()
    ANALYZE: Method create/execute có if/else không?
      → Nếu KHÔNG có if/else nhưng xử lý nhiều case: đây là substitution evidence

QUERY Codebase Memory: {{ tools.search_code }}("switch", limit=50)
  → Tìm tất cả switch statement
  → Nếu count rất thấp so với số case xử lý: strong evidence dùng pattern thay switch

QUERY Codebase Memory: {{ tools.search_code }}("instanceof", limit=50)
  → instanceof nhiều = ad-hoc type checking = KHÔNG phải style này
  → instanceof ít = polymorphism được dùng đúng

RECORD:
  - switch_count_total
  - instanceof_count_total
  - factory_without_switch: số Factory không dùng switch
  - strategy_without_if: số Strategy không dùng if để dispatch
```

### 1D. Layer Boundary Discipline

```
Mục tiêu: Xem tác giả có "creative override" layer boundary không,
và nếu có thì theo pattern nào.

QUERY UA: get_domain_overview()
  → Liệt kê tất cả layer

FOR EACH layer pair (A calls B):
  CALL: {{ tools.get_dependencies }}(layer_A_nodes) filtered to layer_B
  ANALYZE:
    - Có layer nào gọi "ngược chiều" (controller → domain trực tiếp bỏ qua service)?
    - Có class nào bridge 2 layer theo cách không conventional?
    - Có abstract layer nào được inject vào layer không expected?

  Nếu phát hiện "override":
    GET: {{ tools.read_file }}(bridge_class)
    NOTE: "Đây là creative override hay anti-pattern?" → để nguyên, không kết luận
```

### 1E. Code Duplication vs Abstraction Tendency

```
QUERY Codebase Memory: {{ tools.semantic_search }}("common logic abstraction helper util")
  → Xem tác giả có xu hướng extract common logic không

QUERY UA: {{ tools.search_code }}(type="class", filter="name contains 'Helper' OR 'Util' OR 'Common'")
  → Đếm helper/util class
  → Nếu ít: tác giả prefer đặt common logic ở chỗ khác (Base class? Interface default? Composition?)

QUERY UA: {{ tools.search_code }}(type="class", filter="extends Base*")
  → Base class abstraction có nhiều không?
  → Inheritance depth trung bình
```

---

## GIAI ĐOẠN 2: Hypothesis Generation

Từ evidence Giai đoạn 1, agent tạo **danh sách hypothesis có cấu trúc**.

**Mỗi hypothesis phải có:**
- `id`: HP-{n}
- `claim`: Phát biểu cụ thể về style/philosophy
- `confidence`: HIGH | MEDIUM | LOW (dựa trên số lượng và tính nhất quán của evidence)
- `evidence_summary`: 2-3 dòng data cụ thể từ code
- `exemplar`: Node_id hoặc file path của ví dụ rõ nhất
- `counter_evidence`: Những nơi KHÔNG follow pattern này (nếu có)
- `question_for_author`: Câu hỏi cụ thể để confirm

**Ví dụ hypothesis output:**

```
HP-1 [HIGH confidence]
Claim: "Tác giả áp dụng nguyên tắc zero-nested-if nhất quán"
Evidence:
  - 87% method trong codebase có nesting depth = 0
  - Average nesting depth: 0.3 (rất thấp)
  - 23 method có early return pattern
  - Chỉ 3 method có if lồng — đều trong legacy package
Exemplar: <ClassNameProcessor>.validate() [node_id: xxx]
Counter-evidence: <LegacyService>.processRequest() — legacy, chưa refactor
Question: "Em thấy hầu hết code không có if lồng, và những nơi có thì đều trong
           legacy package. Đây có phải nguyên tắc anh áp dụng nhất quán không?
           Hay có ngoại lệ nào không phải legacy mà vẫn OK?"

HP-2 [HIGH confidence]
Claim: "Tác giả ưu tiên Chain of Responsibility thay vì if/else dispatch"
Evidence:
  - {n} Processor class implement cùng interface, không có if dispatch
  - 0 switch statement trong service layer
  - Factory classes: {n}/{n} không dùng if/switch để chọn implementation
Exemplar: <ExemplarProcessor> [node_id: yyy]
Counter-evidence: (không có)
Question: "Đây có phải pattern anh intentionally chọn cho mọi dispatch logic,
           hay chỉ áp dụng cho validation flow?"

HP-3 [MEDIUM confidence]
Claim: "Tác giả prefer composition over inheritance"
Evidence:
  - Inheritance depth average: 1.2 (chủ yếu chỉ extend BaseEntity/BaseRepository)
  - 0 class extend business class (chỉ extend infra base class)
  - Nhiều interface injection hơn abstract class
Counter-evidence: <AbstractXxxProcessor> (1 case)
Question: "Em thấy hầu hết không dùng inheritance cho business logic.
           <AbstractXxxProcessor> là exception hay có pattern riêng?"
```

> **Lưu ý**: Các placeholder `<ClassName>` sẽ được thay bằng tên thực tế
> từ kết quả scan ở Giai đoạn 1. Agent KHÔNG được bịa tên class.
