# Mẫu Explore

> Tài liệu tham khảo cho `openspec-explore`. Đọc khi cuộc trò chuyện cần khám phá sâu, so sánh option, hoặc map rủi ro.

## Mục lục

- Không gian vấn đề
- Điều tra codebase
- So sánh option
- Visualize
- Rủi ro và unknown
- Kết thúc discovery

## Không gian vấn đề

Hỏi câu làm rõ nảy sinh từ lời user. Challenge assumption và reframe khi hữu ích.

## Điều tra codebase

Nếu brainstorm chạm tới code, chạy UA-first probe với `{{ tools.domain_overview }}` hoặc `{{ tools.domain_flow }}` trước khi hỏi câu mà code có thể trả lời.

## So sánh option

Lập bảng so sánh nhỏ và chỉ recommend hướng đi khi đã có đủ evidence.

## Visualize

Dùng ASCII diagram rộng rãi cho state machine, data flow, architecture sketch, so sánh dependency, integration boundary, option branching, và đặc biệt là flow xử lý khi nhận task mới.

ASCII diagram bắt buộc khi có flow/state/data path đủ phức tạp để prose dễ gây mơ hồ.

Khi user đưa task mới còn nhiều nhánh xử lý, vẽ nhanh:

```text
vấn đề user nêu
  -> hành vi hiện tại / unknown
  -> UA-first probe nếu chạm code
  -> map As-is / To-be
  -> option A | option B | option C
  -> recommended next step
```

Khi diagram làm rõ một insight quan trọng, hỏi nhẹ xem có capture không:

```text
Insight này đã rõ hơn sau diagram. Capture vào EXPLORE_CONTEXT.md hoặc artifact OpenSpec liên quan không?
```

## Rủi ro và unknown

Nêu rõ điều có thể sai, điều còn unknown, và có cần spike hay không.

## Kết thúc discovery

Không bắt buộc một kiểu kết thúc. Discovery có thể: flow vào proposal ("Ready to start? I can create a change proposal."), cập nhật artifact (design.md), chỉ mang lại clarity, hoặc tiếp tục sau. Khi mọi thứ đang kết tinh, tóm tắt ngắn dạng "What We Figured Out" trước khi chuyển bước.
