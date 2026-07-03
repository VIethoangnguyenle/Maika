# SESSION_OVERRIDE — Tiếp tục code trong session đã chạy Pha 1/2

<!-- CHỈ ghi file này khi USER chấp thuận tường minh việc tiếp tục cùng session. -->
<!-- write-gate sẽ cho qua nhưng log violation vào AGENT_TRANSPARENCY (audit trail). -->
<!-- File nằm trong knowledge/active/ → được knowledge-curator archive + reset cùng task. -->

ticket: <!-- ticket-id đang active -->
user-confirm: <!-- nguyên văn câu user chấp thuận, vd "đồng ý tiếp tục cùng session" -->
reason: <!-- vì sao không dispatch worker / không mở session mới (vd hotfix 1 dòng) -->
