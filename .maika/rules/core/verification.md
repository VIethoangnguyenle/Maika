# core/verification.md — Execution & Verification (CORE, always-on)

## Execution Rules
- Không implementer nào suy ra strategy từ một request mơ hồ.
- Implementation bắt đầu từ `IMPLEMENTATION_PLAN.md` đã duyệt, queue đã compile,
  và brief bất biến (standard/architectural) hoặc `TASK.yaml` micro-plan (trivial/small).
- Mỗi task ghi một structured result và nhận review độc lập.
- Write không khai báo bị chặn bởi write gate.

## Verification Rules

- Exit code đơn lẻ không bao giờ hoàn thành một task; hoàn thành cần
  command + expected + observed + exit code + interpretation (kernel §6).
- Không complete bằng marker/checkbox; verification fail hoặc chưa chạy = chưa xong.
- Số lệnh verify thật tối thiểu theo class: trivial 0 (static check vẫn phải chạy khi
  khai báo), small ≥1, standard ≥1 thuộc test/build, architectural ≥2 gồm build + test
  (enforce bởi `maika task verify`).
- Lệnh verify khai báo trong `verification/COMMANDS.yaml` / `TASK.yaml`; lệnh ngoài
  allowlist cần approval tường minh (`maika task approve-command`).
