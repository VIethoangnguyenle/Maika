# ADR: Project core and host adapters

Status: Accepted (2026-07-11)

## Decision

Canonical Maika runtime của project luôn nằm tại `.maika/`. Antigravity, Claude
Code, Codex và Generic chỉ quyết định entrypoint, native hook config và tool
mapping; chúng không sở hữu knowledge, task state hoặc framework assets.

Host-owned/shared files được tích hợp an toàn:

- `AGENTS.md` và `CLAUDE.md`: Maika chỉ thay block giữa
  `<!-- maika:begin -->` và `<!-- maika:end -->`.
- `.claude/settings.json`, `.codex/hooks.json`, `.agents/hooks.json`: structural
  merge giữ entry không thuộc Maika và thay hook write-gate cũ của Maika.
- `.agents/resolved-config.yaml` và `.claude/resolved-config.yaml` vẫn được đọc
  trong compatibility window; mọi write mới đi vào `.maika`.

## Ownership

- Project-owned: `.maika/knowledge`, `.maika/changes`, `.maika/archive`.
- Framework-owned: rules, workflows, skills, procedures, tools và hooks dưới
  `.maika`.
- Shared host-owned: entrypoint và native JSON configs nêu trên.

## Consequences

Platform switch không còn tạo một knowledge root mới và update không overwrite
instruction/config ngoài vùng Maika quản lý. Self-contained wheel, transactional
rollback, multi-host enable/disable và migration command vẫn là các phase riêng;
ADR này không tuyên bố các capability đó đã hoàn tất.
