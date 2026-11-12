# Đối chiếu PoC với repo CSIRO-2244-Documents

> Ngày: 12/11/2026 · Nguồn: repo `GriffithBigDataVisualizationLab/CSIRO-2244-Documents` (private), bản mô tả PoC v0.2.
> Repo được tải vào thư mục tạm để đọc, chưa đưa vào dự án.

## 1. Repo có gì

| Tệp | Nội dung chính |
|---|---|
| `PoC_description.md` (v0.2, 12/11/2026) | Mô tả PoC: kiến trúc 3 layer, 3 vai trò (Public / Analyst / Admin), sitemap, đặc tả từng màn hình và biểu đồ, mô hình dữ liệu, tiêu chí nghiệm thu |
| `raw_description_meeting_11_11_26.md` | Ghi chú họp 11/11 (ý kiến chị Hiền và anh Hoàng) |
| `data/seed_data_2244.xlsx` | **Dữ liệu đầu vào chuẩn cho PoC**, gồm 15 sheet (xem §1.1) |
| `scripts/build_seed_data.py` | Script dựng file seed từ 3 tệp nguồn |
| `Report_2244_Formatted1509.docx` | Báo cáo phân tích 2244 (bản 15/09), nguồn số liệu và mẫu biểu đồ |
| `Tables of results_Decision 2244_EN_1.9.26.xlsx` | Bảng kết quả 46 chỉ tiêu và số liệu tỉnh (bản 01/09) |
| `indicator_survey.xlsx` | Trùng khớp hoàn toàn với tệp PoC đang dùng |

### 1.1 Các sheet trong `seed_data_2244.xlsx`

| Sheet | Số dòng | Dùng cho |
|---|---|---|
| `dim_indicator` | 46 | Metadata: tên VI/EN, đơn vị, tần suất (Q/Y), quy tắc gộp (sum/avg/last), cơ quan chủ trì |
| `dim_region` | 35 | 34 tỉnh, thành phố và cờ đã nộp năm 2025 |
| `fact_observation` | 108 | **Số năm thật** (ưu tiên số trong báo cáo 15/09), có `data_status` |
| `fact_sim_quarterly` | 228 | Số quý giả lập cho 19 chỉ tiêu, giai đoạn 2023Q1 → 2025Q4 (`is_simulated = 1`) |
| `fact_province` | 162 | Số liệu 18/34 tỉnh, trạng thái "chưa kiểm chứng", **không dùng để xếp hạng** |
| `readiness_matrix` | 368 | Mức sẵn sàng: 46 chỉ tiêu × 8 chiều chất lượng |
| `status_summary` | 10 | 33/6/4/3 (tình trạng tính toán); 23/15/3/2/2/1 (mức công bố) |
| `provincial_coverage` | 8 | Độ phủ theo tỉnh và vấn đề chính của từng chỉ tiêu |
| `reconciliation` | 12 | Các số lệch giữa file Excel và báo cáo, cần Cục xác nhận |
| `chart_data` | 122 | Dữ liệu để dựng lại các hình Fig 2.x, 3.x |
| `kpi_cards` | 15 | Thẻ KPI cho trang chủ, kèm thông điệp |
| `scorecard` | 4 | Scorecard tổng hợp (chẩn đoán, mức bằng chứng, hàm ý chính sách) |
| `mock_137_indicator`, `mock_137_monthly` | 8 / 192 | Bộ 137 mẫu, số liệu theo tháng 2024–2025 |
| `mapping_2244_137` | 5 | Ánh xạ trùng; 137-M03 lệch có chủ đích ở 2025-Q4 để demo cảnh báo |

## 2. Sai lệch cần sửa ngay

| # | Vấn đề | PoC hiện tại | Theo repo |
|---|---|---|---|
| 1 | Số liệu 2244 là số giả lập nhưng hiển thị như số thật | 0101 = 194.300; 0102 = 81.500 (nguồn "Cục Thông tin, Thống kê (giả lập)") | 0101 = 2.499.736 người; ngân sách công 27.866 tỷ đồng; R&D 0,42% GDP |
| 2 | Không có nhãn cho số giả lập | Chỉ ghi "(giả lập)" trong tên nguồn | Bắt buộc gắn nhãn "Dữ liệu minh hoạ" khi `is_simulated = 1` |
| 3 | Thiếu trạng thái dữ liệu | Chỉ có trạng thái quy trình (chờ duyệt / đã công bố) | Mỗi số liệu cần `data_status`: chính thức / ước tính / đang cập nhật / chưa có / không tính được / chưa công bố |
| 4 | Số đếm sai | "130 chỉ tiêu thuộc 3 văn bản quy phạm"; video ghi "130 chỉ số · 39 cơ quan" | CSDL có 97 chỉ tiêu: 46 (QĐ 2244), 50 tiêu chí chương trình và 1 đề xuất. QĐ 3994 có 34 dòng phân công cho 2244 |
| 5 | Tần suất | Chỉ hiển thị theo năm | 2244 hiển thị **theo quý** (đã chốt); chỉ tiêu không có số quý thì hiển thị theo năm |

## 3. Khác biệt về định hướng

| Hạng mục | PoC hiện tại | Spec v0.2 | Cần làm |
|---|---|---|---|
| Nguồn dữ liệu | 7 bộ thu thập tự động (WIPO, UN, UNDP, Cục SHTT, OpenAlex, World Bank, NEAC) | **Không crawl** cho 2244/137. Dữ liệu lấy từ API anh Định (PoC dùng mock adapter) và file Excel của Cục | Thêm mock adapter API anh Định làm kênh chính. Xếp các bộ thu thập hiện có thành nguồn quốc tế / Layer 3 |
| Nhập dữ liệu | Đơn vị nộp biểu mẫu theo từng chỉ tiêu | Admin nhập file tổng hợp của Cục → xem trước → kiểm tra → **so sánh khác biệt với bản hiện tại** → công bố | Thêm luồng nhập seed/Excel Cục và màn hình so sánh khác biệt |
| Phân quyền | Không đăng nhập; 4 nhóm người dùng minh hoạ | Public / Analyst / Admin; cờ `visibility` public hoặc internal; public chỉ thấy số đã công bố | Thêm vai trò, cờ hiển thị và lọc theo vai trò |
| Bộ 137 | Chưa có | Tab riêng; chọn tháng / quý / năm; cửa sổ 4/6/12 kỳ; MoM / QoQ / YoY / YTD | Làm mới |
| Trùng 2244 ↔ 137 | Chưa có | Lưu một lần, tính lại 2244 từ 137 và cảnh báo đối soát | Làm mới (có thể dùng lại hàng chờ duyệt và cảnh báo hiện có) |
| Trang chủ | 4 KPI, vòng trụ cột, chỉ tiêu nổi bật | 14 thẻ KPI có thông điệp; thanh trạng thái 33/6/4/3; khối "Phát hiện chính" | Làm lại theo `kpi_cards` và `status_summary` |
| Chi tiết chỉ tiêu | Chuỗi số liệu, bảng, lịch sử | Bổ sung định nghĩa, chủ trì / phối hợp, phương pháp, link nguồn, chi tiết kết quả và khuyến nghị (Annex A) | Bổ sung |
| Phân tích theo báo cáo | Chưa có | Khung I-O-O-I; ≥10 biểu đồ dựng lại từ Fig 2.x, 3.x; scorecard | Làm mới từ `chart_data` và `scorecard` |
| Địa phương | Chưa có | Bản đồ 34 tỉnh (đã nộp / chưa nộp), bảng giá trị, **không xếp hạng** | Làm mới |
| Sẵn sàng dữ liệu | Chưa có | Heatmap 46 × 8 chiều | Làm mới từ `readiness_matrix` |
| Đối soát Excel ↔ báo cáo | Chưa có | 12 chỉ tiêu lệch, cần Cục xác nhận | Hiển thị cho Admin |
| Layer 2 (QĐ 39) | Chưa có | Chỉ dựng khung: registry và drill-down 2244 → 39 | Làm khung |
| Layer 3 | Có một phần (dữ liệu ngoài, tổ chức OpenAlex, đề xuất tiêu chí) | Chuyên gia theo đơn vị, tin tuyển dụng, sáng chế theo lĩnh vực × năm; nhãn "Dữ liệu thử nghiệm" | Sắp xếp lại phần đã có và bổ sung |
| Đánh giá | Chấm 50 tiêu chí cho chương trình | Pipeline mô hình tác động: nhập → làm sạch → chạy → Excel | Cần xác nhận còn giữ 50 tiêu chí hay chuyển sang mô hình tác động |
| Ngôn ngữ | Chỉ tiếng Việt | Song ngữ VI/EN (`dim_indicator` có `name_en`) | Bổ sung |

**Phần PoC đã đáp ứng:** lưu vết và lịch sử sửa đổi, duyệt trước khi công bố, truy xuất nguồn và minh chứng, kiểm tra biểu mẫu khi nhập, xuất báo cáo Excel/PDF, mã kỳ dạng `2025-Q4`.

## 4. Thứ tự đề xuất

1. **Dữ liệu:** nhập `seed_data_2244.xlsx` làm nguồn chính thay số giả lập. Thêm `data_status`, `is_simulated` (nhãn "Dữ liệu minh hoạ") và `visibility`. Sửa số đếm "130" trên giao diện và trong video.
2. **Trang chủ và chi tiết chỉ tiêu:** 14 thẻ KPI, thanh trạng thái, phát hiện chính, nội dung Annex A.
3. **2244 theo quý, Tab 137, ánh xạ trùng và cảnh báo đối soát** (tiêu chí nghiệm thu số 4).
4. **Địa phương, sẵn sàng dữ liệu, scorecard, ≥10 biểu đồ** từ báo cáo.
5. **Phân quyền** Public / Analyst / Admin (tiêu chí nghiệm thu số 3).
6. **Sắp xếp lại nguồn tự động**, khung Layer 2, Layer 3 mock, pipeline mô hình. Cập nhật video theo định hướng mới.

## 5. Cần nhóm xác nhận

- Giữ hay bỏ module chấm 50 tiêu chí chương trình (spec v0.2 không nhắc đến).
- Giữ các bộ thu thập quốc tế dưới dạng nguồn tham chiếu, hay ẩn khỏi bản demo.
- Các câu hỏi mở trong spec §11: đặc tả API anh Định, danh sách khoảng 20 chỉ tiêu trùng, QĐ 39, ngôn ngữ hiển thị.
