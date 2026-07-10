# Capability Vocabulary (vNext §11.1 — tồn tại từ W1, runtime đến W4)

Canonical skill/role contract CHỈ tham chiếu các ID sau; provider cụ thể chỉ nằm ở
provider mappings / adapters / tool docs / capability matrix:

- `architecture_discovery` — khám phá module, boundary, flow.
- `exact_source_inspection` — đọc symbol/source hiện tại (authoritative).
- `dependency_analysis` — quan hệ phụ thuộc, blast radius.
- `business_knowledge_retrieval` — tri thức nghiệp vụ, tài liệu, memory.
- `convention_retrieval` — Author DNA, conventions, rule IDs.
- `runtime_verification` — chạy lệnh build/test và đọc output thật.
- `version_control` — đọc/ghi bằng chứng git, commit SHA, diff, và trạng thái.
- `task_dispatch` — dispatch một task implementation theo contract chung.
- `review_dispatch` — dispatch task review hoặc final review theo contract chung.

W4 runtime source of truth: `profiles/capability-registry.yaml`.
Skill-lint rejects unknown capability IDs and provider names in canonical skills.
