# Báo cáo đánh giá PoC Innovation Hub

Đối chiếu kết quả 4 sprint với 5 giả thuyết trong [kế hoạch PoC](../../PoC_Plan_Innovation_Hub.md). Số liệu đo trên bộ dữ liệu dựng bằng `scripts.reset_demo` ngày 12/11/2026.

## Tóm tắt

| # | Giả thuyết | Tiêu chí thành công | Kết quả | Đánh giá |
|---|---|---|---|---|
| H1 | Chuẩn hoá 130 chỉ số thành một Indicator Registry | 100% chỉ số được import, đủ thuộc tính | 130/130 bản ghi → 96 chỉ tiêu gốc + 34 phân công; 39 cơ quan; 27 nguồn; tự phát hiện xung đột mã GII | ✅ Đạt |
| H2 | Đơn vị upload theo mẫu, hệ thống tự validate, tự tính | Upload → dashboard < 5 phút, không cần kỹ thuật | Phần hệ thống: kiểm tra + nhập 92 ms, duyệt 6 ms, dashboard 16 ms; 9 loại lỗi báo theo ô; tự tính 8 chỉ số dẫn xuất | ⚠ Đạt về kỹ thuật, **chưa kiểm thử với người dùng thật** |
| H3 | ≥ 6 chỉ số MVP-1 tự động crawl/API định kỳ | ≥ 6 chỉ số, có nguồn và thời điểm | 7 connector chạy thật, phủ 10 chỉ tiêu (8 thuộc MVP-1); có lịch chạy hằng tuần; mỗi lần chạy lưu bản chụp nguồn | ✅ Đạt |
| H4 | Đánh giá 1 case theo Program_Criteria | Có scorecard + minh chứng từng tiêu chí | Case demo 12/50 tiêu chí: 5 từ OpenAlex, 2 kê khai, TRL, 4 nhập tay; mỗi điểm có nguồn và trạng thái duyệt | ✅ Đạt về chức năng; case là **giả lập** |
| H5 | Dữ liệu ngoài giúp đề xuất tiêu chí mới | ≥ 5 tiêu chí, chuyên gia đánh giá hữu ích | 8 đề xuất có định nghĩa, công thức, nguồn, số liệu tính thử; 7 dựa trên dữ liệu thật; có sàng lọc trùng | ⚠ Đạt số lượng, **chưa có chuyên gia đánh giá** |

**Kết luận:** về kỹ thuật, PoC chứng minh được cả 5 giả thuyết. Hai giả thuyết cần người dùng xác nhận (H2, H5) chưa kiểm chứng được – đây là việc ưu tiên trước khi quyết định làm MVP. Kịch bản kiểm thử: [UAT_checklist.md](UAT_checklist.md).

## Độ phủ dữ liệu đạt được

| Nhóm | Số chỉ tiêu QĐ 2244 | Có số liệu công bố | Ghi chú |
|---|---|---|---|
| Đầu vào | 2 | 2 | 0101, 0102 từ file đơn vị (giả lập) + World Bank đối chiếu |
| Kết quả | 10 | 3 | 0201 (OpenAlex), 0202, 0203 (Cục SHTT) |
| Hiệu quả | 5 | 0 | Cần khảo sát doanh nghiệp / mô hình phân tích |
| Tác động | 29 | 4 | 0405 (proxy WB), 0426 EGDI, 0428 GII, 0429 HDI; 0425 NEAC chờ duyệt |
| **Tổng** | **46** | **9 (+1 chờ duyệt)** | |

Nhận xét: phần dễ tự động hoá (chỉ số quốc tế, sở hữu trí tuệ, công bố) đã làm được. **Khoảng 70% chỉ tiêu còn lại phụ thuộc dữ liệu hành chính hoặc khảo sát** – giá trị chính của hệ thống ở nhóm này là chuẩn hoá luồng nộp–duyệt, không phải crawl.

## Phát hiện từ dữ liệu thật

- Tỷ lệ đơn sáng chế của người nộp trong nước chỉ **12,4%** (2024) – phần lớn sáng chế được bảo hộ tại Việt Nam là của nước ngoài.
- **Dưới 1%** công bố có đồng tác giả doanh nghiệp (OpenAlex; OpenAlex mới phân loại được 10 doanh nghiệp Việt Nam nên con số có thể thấp hơn thực tế).
- 1.587 nhà khoa học tại Việt Nam có h-index ≥ 20.
- Bộ chỉ tiêu hiện chủ yếu đo **số lượng** (bài báo, đơn, nhân lực); các đề xuất bổ sung chiều **chất lượng**, **liên kết** và **lan toả vùng**.

## Vấn đề kỹ thuật gặp thực tế

| Vấn đề | Cách xử lý | Bài học cho MVP |
|---|---|---|
| ipvietnam.gov.vn thiếu chứng chỉ SSL trung gian | Kèm chứng chỉ trung gian công khai, vẫn xác minh đầy đủ | Theo dõi chứng chỉ của nguồn; đề nghị đơn vị chủ quản sửa cấu hình |
| UN EGOVKB trả header HTTP sai chuẩn | Tự chuyển sang trình tải dễ dãi hơn | Mỗi nguồn cần cơ chế dự phòng riêng |
| Trang GII dựng bằng JavaScript | Dùng file CSV mà trang tải về | Ưu tiên tìm dữ liệu gốc thay vì "cào" giao diện |
| Cục SHTT đổi bố cục file Excel giữa các năm | Parser dò theo tiêu đề cột | Kiểm thử connector bằng dữ liệu nhiều năm |
| OpenAlex chặn phân trang cursor khi không có key | Dùng phân trang theo số trang | Đăng ký API key cho môi trường thật |
| Số liệu thật lệch nhau giữa nguồn (WB vs đơn vị +5,8%) | Hiển thị đối chiếu, quy tắc ưu tiên nguồn rõ ràng | Cần văn bản quy định nguồn chính thức cho từng chỉ tiêu |

## Hạn chế của PoC

1. **Chưa kiểm thử với người dùng thật** (H2, H5).
2. **Số liệu đơn vị và case đánh giá là giả lập.** Chưa có file báo cáo thật của bộ, ngành nào.
3. **Chưa có LLM** (chưa có API key):
   - Doc-ETL dùng luật + từ khoá.
   - Chống trùng đề xuất dùng so khớp từ (có báo nhầm, vd. SCI-04).
   - Chưa có tính năng nối file "tự do" vào chỉ tiêu.
4. **Chưa có đăng nhập/phân quyền**; người duyệt tự khai tên.
5. **Hạ tầng:** chưa chạy thử Docker/Postgres (mới SQLite); file minh chứng lưu thư mục local thay vì MinIO; chưa có migration (Alembic).
6. **Proxy:**
   - OpenAlex thay Scopus/WoS.
   - World Bank 0405 khác mẫu số.
   - Tin tuyển dụng dùng dữ liệu giả lập.

## Khuyến nghị cho giai đoạn MVP

1. **Tổ chức UAT** với 2–3 đơn vị theo `UAT_checklist.md`; xin 1–2 file báo cáo thật để chỉnh template.
2. **Chốt với Bộ KH&CN:**
   - định nghĩa, phân tổ, giá trị mục tiêu cho các chỉ tiêu MVP-1/2;
   - nguồn chính thức cho từng chỉ tiêu;
   - xử lý xung đột mã GII (0427/0428).
3. **Hạ tầng:**
   - Postgres + Alembic;
   - MinIO;
   - đăng nhập theo đơn vị (SSO/VNeID) và phân quyền theo phân công QĐ 3994;
   - nhắc hạn nộp.
4. **LLM (Claude API):** Doc-ETL cho PDF/báo cáo khó; nối file tự do; so khớp ngữ nghĩa khi chống trùng đề xuất. Cần quyết định trước về việc gửi dữ liệu ra dịch vụ ngoài hoặc dùng mô hình nội bộ.
5. **Mở rộng dữ liệu:**
   - license Scopus/WoS;
   - danh sách doanh nghiệp KH&CN;
   - dữ liệu tuyển dụng có cấp phép;
   - khảo sát cho nhóm Hiệu quả (0304, 0305).
