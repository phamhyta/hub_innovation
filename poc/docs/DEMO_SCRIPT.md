# Kịch bản demo PoC Innovation Hub (~20 phút)

## Chuẩn bị (trước buổi demo 30 phút)

```bash
cd poc/backend
uv run python -m scripts.reset_demo --yes     # ~1 phút, cần Internet
uv run uvicorn app.main:app --port 8000
```

Kết quả mong đợi: 7/7 connector thành công, 9/46 chỉ tiêu QĐ 2244 có số liệu công bố, ~760 điểm chờ duyệt, 1 case demo, 8 đề xuất tiêu chí.

**Nếu mất mạng trong buổi demo:** mọi trang vẫn chạy trên dữ liệu đã dựng; chỉ bỏ qua bước bấm "Chạy" connector (bước 4) và "Tính lại từ OpenAlex" (bước 6).

Mở sẵn file `poc/sample_data/TPL-0101-0102_DonViX_2025_CO_LOI.xlsx` trong Finder để kéo thả.

---

## 1. Bài toán (1 phút) – trang **Registry**

- "130 chỉ số từ 3 văn bản, trước đây mỗi đơn vị nộp 1 file Excel/Word."
- Gõ `sang che` (không dấu) → ra 0202, 0203. Lọc **Mức tin cậy A** + **MVP-1** → các chỉ tiêu có thể tự động hoá.
- Gõ `0427` → hệ thống tự phát hiện **xung đột mã GII** giữa QĐ 3994 và QĐ 2244 (thẻ cảnh báo màu cam).

## 2. Đơn vị nộp số liệu (3 phút) – trang **Nộp số liệu**

- Tải template → chỉ ra dropdown địa bàn/phân tổ, sheet hướng dẫn.
- Kéo thả file `…_CO_LOI.xlsx` → bảng **9 lỗi theo từng dòng/cột** (thiếu giá trị, nhập chữ, năm 2050, phân tổ lạ, trùng dòng, số âm, % nhầm đơn vị, link sai, thiếu năm). "File lỗi không được nhập – đơn vị biết chính xác phải sửa ô nào."
- Mở lượt nộp của Sở KH&CN Hà Nội (đã nhập) → "số liệu vào trạng thái chờ duyệt".

## 3. Duyệt dữ liệu (3 phút) – trang **Duyệt dữ liệu**

- Lọc nguồn `crawler:neac` → đoạn trích "*tổng số chứng thư chữ ký số đã cấp đạt khoảng 26,45 triệu*" + link **minh chứng** (bản lưu trang gốc).
- Đổi trạng thái sang **Đã công bố**, nguồn `crawler:worldbank`, chỉ tiêu 0101 → cột **Đối chiếu nguồn khác**: World Bank lệch +5,8% so với số đơn vị báo cáo năm 2023 (số World Bank đã được duyệt sẵn khi dựng dữ liệu demo).
- Nhập tên người duyệt, chọn vài dòng NEAC → **Duyệt & công bố**. Từ chối 1 dòng → bắt buộc ghi lý do.

## 4. Thu thập tự động (2 phút) – trang **Thu thập tự động**

- 7 nguồn: GII, EGDI, HDI tự công bố (tin cậy A); Cục SHTT, OpenAlex, World Bank, NEAC cần duyệt.
- Bấm **▶ Chạy** GII → "42 không đổi" – chạy lại không sinh trùng; mỗi lần chạy lưu bản chụp nguồn.
- Kể 3 sự cố thực tế đã xử lý: SSL thiếu chứng chỉ trung gian (Cục SHTT), header HTTP sai chuẩn (UN), trang GII dựng bằng JavaScript.

## 5. Tổng quan & báo cáo (3 phút) – trang **Tổng quan**

- Thẻ số liệu: 0101 = 8,9 FTE/vạn dân (2025, ▲ +7,2%), GII hạng 43 (2026, ▲ tăng 1 bậc).
- Ma trận 46 chỉ tiêu × năm: thấy ngay chỉ tiêu nào **chưa có dữ liệu** (đa số nhóm Hiệu quả/Tác động – cần khảo sát).
- Bấm **Xuất Excel** và **Báo cáo in / PDF**.
- Mở 0428 → biểu đồ so sánh thứ hạng tổng với thứ hạng trụ cột Đầu vào.

## 6. Đánh giá một case (4 phút) – trang **Đánh giá case**

- Mở case DEMO: **84,8/100 – tạm tính, độ phủ thấp (12/50 tiêu chí)**. Nhấn mạnh: hệ thống **tự cảnh báo** khi kết luận chưa đủ căn cứ.
- Các dòng OpenAlex: 20 bài, 75% có hợp tác quốc tế, 24 trích dẫn/bài, h-index trung vị 11 – kèm link dữ liệu nguồn.
- Khung TRL: gợi ý **TRL 6**; giải thích hệ thống bỏ qua cụm "**chưa** thử nghiệm thực tế" nên không gợi ý sai TRL 7.
- Bấm **Tính lại từ OpenAlex** (cần mạng).

## 7. Đề xuất tiêu chí mới (3 phút) – trang **Đề xuất tiêu chí**

- 8 đề xuất từ dữ liệu ngoài, xếp theo ưu tiên (độ mới × khả thi). Ví dụ:
  - Tỷ lệ đơn sáng chế của người nộp trong nước: **12,4%** (2024) – cho thấy mức làm chủ công nghệ.
  - Tỷ lệ công bố có đồng tác giả doanh nghiệp: **<1%** – liên kết viện–doanh nghiệp rất yếu.
  - Số tỉnh có ≥10 đơn sáng chế/GPHI – đo mức lan toả vùng.
- Chỉ ra cảnh báo **"Có thể trùng ECO-06"** ở đề xuất "Số doanh nghiệp mới thành lập" → **Từ chối** (ghi lý do).
- **Chấp nhận** "Tỷ lệ đơn sáng chế trong nước" → xuất hiện **DX-01** trong Registry (lọc "Đề xuất mới"), số liệu tính thử vào hàng đợi duyệt.

## Kết (1 phút)

Nhắc 5 giả thuyết của PoC và kết quả (xem `PoC_Evaluation.md`), các câu hỏi cần chốt để làm MVP.
