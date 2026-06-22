# Structural Audit — 5 Scan Dimensions

> Reference file — extracted from SKILL.md for progressive disclosure.

## 2A. File & Class Naming Patterns

```
QUERY UA: {{ tools.search_code }}(type="class", limit=200)
  → Lấy tên tất cả class
  → GROUP BY suffix:
      *Service, *ServiceImpl, *Repository, *RepositoryImpl
      *Handler, *Processor, *Command, *Query, *Event
      *Factory, *Builder, *Mapper, *Converter, *Validator
      *Controller, *Facade, *UseCase, *Manager
      *Config, *Properties, *Constants, *Enum
      *Request, *Response, *DTO, *Model, *Entity, *VO
      *Exception, *Error, *ExceptionHandler
  → COUNT occurrence per suffix
  → FILTER: chỉ giữ suffix có count >= 3 (đủ để thành convention)

QUERY Codebase Memory: {{ tools.semantic_search }}("naming convention class suffix")
  → Bổ sung các pattern UA có thể bỏ sót
```

## 2B. Package / Layer Structure

```
CALL: get_domain_overview()
  → Liệt kê tất cả domain/layer hiện có
  → Map layer name → package path pattern

CALL: {{ tools.get_symbol }}(mỗi layer)
  → Hiểu responsibility của từng layer
  → Detect pattern: Clean Architecture / Hexagonal / Layered / CQRS

QUERY UA: {{ tools.search_code }}(type="package")
  → Extract package naming: {project_package_root}.{module}.{layer}
  → Identify depth convention (mấy cấp package)
```

## 2C. Architecture Core Patterns & Dispatch Mechanisms

```
QUERY UA: {{ tools.search_code }}(type="class", filter="suffix IN [Controller, Command, Query, Handler, Processor]")
  FOR EACH node:
    CALL: {{ tools.get_dependencies }}(node_id)
      → Khám phá cách Controller tương tác với Logic Layer: Controller gọi trực tiếp
        Handler/Service hay đi qua một message bus / dispatcher?
      → Controller có bắt buộc kế thừa base class nào không (vd một base class chung do dự án quy định)?
    CALL: {{ tools.read_file }}(node_id)
      → Đọc actual implementation (chỉ signature, không toàn bộ body)
      → Nếu phát hiện một dispatch pattern bắt buộc (vd CQRS: Controller → bus → Command → Handler),
        đánh dấu đây là kiến trúc cốt lõi với mức độ MANDATORY (upstream_constraints).
```

## 2D. Upstream Conventions từ shared library

```
QUERY UA: {{ tools.search_code }}(filter="source_path STARTS_WITH {upstream_root}")
  → Lấy tất cả class/interface từ upstream library
  → GROUP BY type: Base*, I*, Abstract*, common annotations...
  → Đây là convention MANDATORY — project downstream PHẢI follow

CALL: {{ tools.get_symbol }}(mỗi base class/interface quan trọng)
  → Extract: abstract method naming, field naming, annotation usage
  → Tag tất cả với origin: upstream, weight: mandatory
```

## 2E. Test & Config Conventions

```
QUERY Codebase Memory: {{ tools.search_code }}("@Test class", limit=50)
  → Detect: test class suffix (*Test, *Spec, *IT)
  → Detect: test method naming (should_*, when_*_then_*, given_*)

QUERY UA: {{ tools.search_code }}(type="class", filter="name CONTAINS 'Config' OR name CONTAINS 'Properties'")
  → Extract config class naming pattern
  → Detect: @ConfigurationProperties prefix convention
```
