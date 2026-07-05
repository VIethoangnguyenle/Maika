# DNA Compliance Check

> Tài liệu tham khảo cho `spec-validator`. Đọc khi chạy semantic post-apply DNA compliance.

## Input

- changed_files.
- author-dna.yaml hard_principles, soft_preferences, complexity_thresholds, style_preferences.
- approved conventions.yaml naming/package constraint.

## Result

- BLOCK cho hard principle violation.
- PASS kèm warning cho soft/convention concern.
- CLEAN khi không phát hiện violation.

Checklist lấy động từ DNA/conventions; không hardcode HP/SP ID.
