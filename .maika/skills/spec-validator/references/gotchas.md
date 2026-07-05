# Gotcha của Spec Validator

> Tài liệu tham khảo cho `spec-validator`. Đọc khi gặp edge case về path, contract, coverage, hoặc DNA.

## Gotchas

- OpenSpec artifact path có thể đổi; verify file tồn tại trước khi đọc.
- C6 contract gate chỉ chạy khi REQUIREMENT có design contract/interface section.
- Pre-apply trả PASS/BLOCK; post-apply trả OK/issues list.
- AC generic có thể gây false positive; warn khi AC quá mơ hồ.
- DNA check giả định DNA slice có trong task handoff.
- Conventions draft được skip cho tới khi approved.
