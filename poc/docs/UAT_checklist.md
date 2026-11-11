# Kịch bản kiểm thử với người dùng thật (UAT)

**Mục tiêu:** kiểm chứng giả thuyết H2 ("đơn vị upload và hệ thống tự validate, tự tính… không cần can thiệp kỹ thuật") và độ dễ dùng của luồng duyệt, đánh giá, đề xuất – với **2–3 người dùng thật** như kế hoạch PoC.

> Trạng thái: **chưa thực hiện**. Nhóm phát triển chưa tiếp cận được người dùng thật. Tài liệu này là kịch bản để tổ chức buổi kiểm thử.

## Chuẩn bị

- Dựng dữ liệu: `uv run python -m scripts.reset_demo --yes`.
- Mỗi người dùng một máy, mở http://localhost:8000 (hoặc máy chủ thử nghiệm).
- Người quan sát **không hướng dẫn**, chỉ ghi lại: thời gian, chỗ vấp, câu hỏi, lỗi.
- Thời lượng: 45 phút/người (30 phút làm nhiệm vụ + 15 phút phỏng vấn).

## Vai trò & nhiệm vụ

### A. Cán bộ đơn vị báo cáo (vd. Sở KH&CN, Cục Thông tin – Thống kê)

| # | Nhiệm vụ | Thành công khi | Thời gian mục tiêu |
|---|---|---|---|
| A1 | Tải template 0101/0102 | Có file trên máy | < 1 phút |
| A2 | Điền 6 dòng số liệu năm 2025 cho đơn vị mình (số tự chọn) | File hợp lệ | < 10 phút |
| A3 | Nộp file `TPL-…_CO_LOI.xlsx` và sửa đúng các lỗi hệ thống báo | Nộp lại thành công, không hỏi người quan sát | < 10 phút |
| A4 | Nộp file của mình, tìm xem số liệu đang ở trạng thái nào | Trả lời được "chờ duyệt" | < 2 phút |

### B. Người duyệt dữ liệu (Cục TT-TK / Bộ KH&CN)

| # | Nhiệm vụ | Thành công khi |
|---|---|---|
| B1 | Tìm các số liệu NEAC đang chờ duyệt, mở file minh chứng | Mở được bản lưu nguồn |
| B2 | Phát hiện số liệu lệch nguồn khác > 25% (nếu có) và quyết định | Dùng được cột "Đối chiếu nguồn khác" |
| B3 | Duyệt toàn bộ số liệu của 1 lượt nộp, từ chối 1 dòng kèm lý do | Trạng thái đúng, dashboard cập nhật |
| B4 | Xuất báo cáo Excel năm 2025 | File mở được, số khớp dashboard |

### C. Chuyên gia / lãnh đạo

| # | Nhiệm vụ | Thành công khi |
|---|---|---|
| C1 | Trả lời: "Năm 2026 Việt Nam xếp hạng GII bao nhiêu, tăng hay giảm?" | Trả lời đúng từ trang Tổng quan |
| C2 | Trả lời: "Nhóm chỉ tiêu nào còn thiếu dữ liệu nhiều nhất?" | Dùng ma trận/độ phủ trụ cột |
| C3 | Mở case demo, giải thích vì sao kết luận là "tham khảo" | Nêu được độ phủ thấp / tạm tính |
| C4 | Duyệt 2 đề xuất tiêu chí: chấp nhận 1, từ chối 1 có lý do | DX-xx xuất hiện trong Registry |

## Câu hỏi phỏng vấn sau buổi thử (thang 1–5)

1. Báo lỗi khi nộp file có đủ rõ để tự sửa không?
2. So với cách nộp file hiện nay, mất ít thời gian hơn hay nhiều hơn?
3. Phân tổ trong template có khớp số liệu đơn vị đang có không? Thiếu/thừa phân tổ nào?
4. Khi duyệt, thông tin nào còn thiếu để ra quyết định?
5. Các đề xuất tiêu chí mới có hữu ích không? Đề xuất nào nên đưa vào bộ chỉ tiêu?
6. Điều gì khiến anh/chị **không** muốn dùng hệ thống này?

## Phiếu ghi nhận (mỗi người dùng)

| Người dùng | Vai trò | Nhiệm vụ | Hoàn thành (Có/Không/Có trợ giúp) | Thời gian | Vấn đề gặp phải |
|---|---|---|---|---|---|
| | | | | | |

## Tiêu chí đạt của H2

- ≥ 2/3 cán bộ đơn vị hoàn thành A1–A4 **không cần trợ giúp**.
- Thời gian từ khi có file hợp lệ đến khi số liệu lên dashboard (sau khi duyệt) < 5 phút.
- Điểm trung bình câu 1 ≥ 4/5.
