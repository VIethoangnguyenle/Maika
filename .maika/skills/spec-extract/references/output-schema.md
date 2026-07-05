# Output schema đầy đủ

## Mục lục

- Output

### Output

Cập nhật `{{ platform.framework_root }}/knowledge/active/REQUIREMENT.md`:

- Thêm section (hoặc cập nhật) kiểu:

  ```md
  ### Yêu cầu nghiệp vụ trích từ tài liệu

  #### Bối cảnh & mục tiêu (từ tài liệu)
  - ...

  #### Actor & Use Case
  - ...

  #### Luồng chính
  - ...

  #### Luồng lỗi / ngoại lệ
  - ...

  #### Quy tắc nghiệp vụ
  - ...

  #### Acceptance Criteria (nếu ghi nhận được)
  - ...

  #### Ràng buộc phi chức năng
  - ...

  #### Integrations & Field Mapping
  - Integration: <tên> (hướng, protocol & auth, endpoint, tài liệu nguồn)
  - Bảng field mapping: field third-party → field canonical + ý định transform + nguồn
  - Field chưa map được → mirror vào "Lỗ hổng & câu hỏi mở"

  #### Độ tin cậy tài liệu
  - CAO / TRUNG BÌNH / THẤP (và lý do)

  #### Lỗ hổng & câu hỏi mở
  - ...
  ```

- Đảm bảo:
  - Không xoá/ghi đè phần REQUIREMENT đã có trừ khi có lý do rõ ràng (và phải merge cẩn thận).
  - Giữ link tới tài liệu gốc để trace back.
