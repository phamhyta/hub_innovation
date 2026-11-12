# Kế hoạch triển khai PoC v2 – theo bản mô tả CSIRO-2244 (v0.2)

> Ngày lập: 12/11/2026 · Trạng thái: **đã duyệt** · Tiến độ: **GĐ 1–5 hoàn thành (12/11/2026)** – đạt Mốc B và tiêu chí 3; GĐ 6 chưa bắt đầu
> Căn cứ:
> - `PoC_description.md` v0.2 và `data/seed_data_2244.xlsx` trong repo `CSIRO-2244-Documents`;
> - bảng đối chiếu `CSIRO_2244_Doi_chieu.md`.
>
> Phạm vi sửa: `poc/backend` (mô hình dữ liệu, API, giao diện), `poc/docs/demo-video`, tài liệu.
> Không thay đổi: git, CI, cấu hình Vercel. Các phần đó do phiên phụ trách deploy thực hiện.

---

## 0. Mục tiêu và nguyên tắc

**Mục tiêu.** Đưa PoC về đúng bản mô tả v0.2 và đạt 5 tiêu chí nghiệm thu (spec §10):

1. Thay file Excel 2244 mới của Cục → giao diện cập nhật, không cần sửa code.
2. Mỗi số liệu hiển thị đều truy được nguồn, trạng thái dữ liệu và kỳ.
3. Người dùng Public không thấy chỉ tiêu, giá trị nội bộ hoặc chưa công bố.
4. Chỉ tiêu 137 xem được 4/6/12 kỳ gần nhất, MoM/QoQ/YoY đúng. Chỉ tiêu 2244 xem được theo quý, QoQ/YoY đúng.
5. Pipeline mô hình xuất được file Excel kết quả.

**Nguyên tắc.**
- **Dữ liệu điều khiển giao diện.** Thẻ KPI, biểu đồ, scorecard, mức sẵn sàng đều đọc từ file seed. Không ghi cứng số liệu trong HTML.
- **Tách hai loại trạng thái.**
  - *Trạng thái dữ liệu* (`data_status`): chính thức, ước tính, đang cập nhật…, theo đúng Cục.
  - *Trạng thái duyệt* (`status`): chờ duyệt, đã công bố…, quy trình nội bộ hiện có.
- **Số giả lập luôn có nhãn.** Mọi giá trị `is_simulated = 1` hiển thị nhãn "Dữ liệu minh hoạ". Số giả lập không được dùng trong thẻ KPI chính thức.
- **Không xếp hạng tỉnh.** Số liệu tỉnh chỉ hiển thị đã nộp / chưa nộp và bảng giá trị. Không sắp xếp theo giá trị.
- **Giữ phần đã làm.** Lưu vết, duyệt, minh chứng, kiểm tra biểu mẫu, xuất báo cáo được giữ và tái sử dụng. 64 test hiện có phải tiếp tục đạt.
- **Giao diện.** Tiếp tục hệ thiết kế hiện tại: nền sáng, ít chữ, thuật ngữ khoa học, không ẩn dụ.

---

## 1. Quyết định cần duyệt trước khi triển khai

Mỗi mục có phương án đề xuất. Nếu không có ý kiến khác, triển khai theo phương án đề xuất.

| # | Câu hỏi | Phương án đề xuất | Phương án khác |
|---|---|---|---|
| D1 | Module chấm 50 tiêu chí chương trình (spec v0.2 không nhắc đến) | **Giữ**, chuyển vào khu nội bộ "Đánh giá chương trình", ẩn với Public. Đã hoàn thành nên không tốn thêm công | Ẩn hoàn toàn khỏi bản demo |
| D2 | 7 bộ thu thập tự động (WIPO, UN, UNDP, World Bank, Cục SHTT, OpenAlex, NEAC) | **Giữ, đổi vai trò.** Nguồn quốc tế chỉ cấp số cho 0426–0429. OpenAlex, Cục SHTT, tin tuyển dụng chuyển sang Layer 3 "Dữ liệu thử nghiệm". Bỏ khỏi luồng chính và trang chủ | Ẩn toàn bộ |
| D3 | Bản đồ 34 tỉnh, thành phố | **Bản đồ lưới ô** (tile grid map: mỗi tỉnh một ô đặt theo vị trí tương đối). Không cần dữ liệu ranh giới, không phụ thuộc giấy phép | Choropleth ranh giới thật. Cần nguồn GeoJSON 34 đơn vị sau sắp xếp 2025 có giấy phép rõ ràng |
| D4 | Đăng nhập cho 3 vai trò | **Tài khoản demo** (Public không đăng nhập; Analyst; Admin), phiên bằng cookie ký. Mật khẩu demo đặt trong `.env`, có `.env.example` | Chỉ có nút chuyển vai trò, không mật khẩu |
| D5 | Ưu tiên số liệu khi Excel 01/09 và báo cáo 15/09 lệch nhau | **Theo quy ước của file seed:** dùng số báo cáo 15/09; 12 chỉ tiêu lệch đưa vào màn hình Đối soát chờ Cục xác nhận | Dùng số Excel |
| D6 | Ngôn ngữ | **Tiếng Việt mặc định, nút chuyển EN** cho menu, nhãn chính và tên chỉ tiêu (đã có `name_en`). Văn bản diễn giải giữ tiếng Việt | Song ngữ toàn bộ |
| D7 | Luồng đơn vị nộp biểu mẫu theo từng chỉ tiêu | **Giữ** như công cụ của Admin ("Biểu mẫu theo chỉ tiêu"). Kênh chính là nhập file tổng hợp của Cục và đồng bộ API | Bỏ |
| D8 | Số thẻ KPI trang chủ (spec ghi 14, file seed có 15) | **Hiển thị theo file seed (15)** để giữ nguyên tắc dữ liệu điều khiển | Cắt còn 14 |

---

## 2. Tổng quan giai đoạn

| GĐ | Nội dung | Công (ngày) | Kết quả kiểm chứng |
|---|---|---|---|
| 1 | Dữ liệu chuẩn: mô hình mới, nhập file seed, trạng thái dữ liệu, nhãn minh hoạ | 2,5 | Tiêu chí 1, 2 |
| 2 | Trang chủ và trang chi tiết chỉ tiêu | 2 | Số trên giao diện khớp file seed |
| 3 | 2244 theo quý, Tab 137, adapter API, ánh xạ trùng, đối soát | 3 | Tiêu chí 4 |
| 4 | Phân tích theo báo cáo: biểu đồ, scorecard, sẵn sàng dữ liệu, địa phương | 3 | ≥10 biểu đồ, trang Địa phương |
| 5 | Phân quyền và quản trị dữ liệu | 2 | Tiêu chí 3 |
| 6 | Layer 2, Layer 3, mô hình tác động, song ngữ | 3 | Tiêu chí 5 |
| 7 | Video, tài liệu, kiểm thử nghiệm thu, rà soát giao diện | 1,5 | 5/5 tiêu chí có test tự động |
| | **Tổng** | **≈ 17** | |

Thứ tự bắt buộc: GĐ 1 trước, vì các giai đoạn sau phụ thuộc mô hình dữ liệu mới. GĐ 2–4 có thể làm xen kẽ. GĐ 5 nên làm trước GĐ 6, vì các trang nội bộ cần phân quyền.

---

## 3. Giai đoạn 1 – Dữ liệu chuẩn (2,5 ngày)

### 3.1 Đưa dữ liệu nguồn vào dự án
- Chép `seed_data_2244.xlsx` vào `poc/data/seed/`, kèm `README.md` ghi nguồn (repo, ngày, phiên bản) và quy ước `is_simulated`.
- Không chép báo cáo .docx và Excel gốc. Chúng chỉ cần khi dựng lại file seed bằng script của repo.

### 3.2 Mô hình dữ liệu (`app/models.py`)

**Bảng `indicators`, thêm cột:**

| Cột | Kiểu | Lấy từ `dim_indicator` |
|---|---|---|
| `indicator_set` | `2244` / `137` / `39` / `L3` / `PROGRAM` | Suy ra từ framework hiện có |
| `name_en` | text | `name_en` |
| `stage` | text | `stage` (Đầu vào, Đầu ra/Kết quả…) |
| `aggregation_rule` | `sum` / `avg` / `last` | `aggregation_rule` |
| `visibility` | `public` / `internal` | `visibility` |
| `lead_agency_text` | text | `lead_agency` |
| `latest_result_text`, `limitation`, `recommendation`, `recommended_chart` | text | Cột cùng tên (Annex A) |
| `readiness_report` | text | `readiness_report` |
| `parent_id` | FK → indicators | Liên kết 39 → 2244 (GĐ 6) |

`frequency` đã có, ghi `Q` hoặc `Y` theo file seed.

**Bảng `data_points`, thêm cột:**
- `data_status`: enum `DataQuality` (mục 3.3).
- `is_simulated`: bool.
- `period_type`: `M` / `Q` / `Y`.
- `region_code`: mã tỉnh; `VN` = toàn quốc.

Cột `geography` giữ để tương thích, lấy tên từ bảng `regions`.

**Bảng mới:**

| Bảng | Nội dung | Sheet nguồn |
|---|---|---|
| `regions` | 34 tỉnh, thành phố + toàn quốc, cờ đã nộp 2025 | `dim_region` |
| `data_releases` | Mỗi lần nhập file: tên, sha256, thời điểm, người nhập, số dòng mới/đổi/bỏ | (sinh khi nhập) |
| `indicator_mappings` | Ánh xạ 2244 ↔ 137: quan hệ, quy tắc gộp, ghi chú | `mapping_2244_137` |
| `readiness_scores` | Chỉ tiêu × 8 chiều × mức (0–2) | `readiness_matrix` |
| `chart_series` | Dữ liệu biểu đồ: chart_id, hình tham chiếu, tiêu đề, chuỗi, hạng mục, giá trị, đơn vị | `chart_data` |
| `kpi_cards` | Thẻ KPI trang chủ | `kpi_cards` |
| `scorecard_rows` | Scorecard 4 chiều | `scorecard` |
| `status_summary` | Hai phân loại trạng thái (33/6/4/3; 23/15/3/2/2/1) | `status_summary` |
| `provincial_coverage` | Độ phủ tỉnh theo chỉ tiêu và vấn đề chính | `provincial_coverage` |
| `reconciliations` | 12 chỉ tiêu lệch Excel ↔ báo cáo, trạng thái xác nhận | `reconciliation` |
| `narratives` | Đoạn "Phát hiện chính", theo mục và ngôn ngữ, cờ công bố | (Admin biên tập; khởi tạo từ `scorecard.diagnosis`) |

**Cách áp dụng thay đổi bảng.** Dự án dùng `create_all`, không có migration. CSDL dev phải dựng lại bằng `scripts.reset_demo`. Thêm kiểm tra khi khởi động: thiếu cột thì báo rõ "cần chạy reset_demo".

### 3.3 Danh mục trạng thái dữ liệu

Danh mục lấy theo file seed. Màu theo mức độ tin cậy, không dùng màu đỏ cho "chưa có".

| Mã | Nhãn | Nhóm màu |
|---|---|---|
| `official` | Chính thức | Xanh lá |
| `official_caveat` | Chính thức (có lưu ý) | Xanh lá nhạt |
| `estimate` | Ước tính | Xanh dương |
| `method_adjustment` | Điều chỉnh phương pháp | Xanh dương |
| `updating` | Đang cập nhật | Vàng |
| `incomplete` | Chưa đầy đủ | Vàng |
| `under_review` | Đang rà soát | Vàng |
| `not_calculable` | Chưa tính được | Xám |
| `not_available` | Chưa có số liệu | Xám |
| `no_info` | Chưa có thông tin | Xám |
| `reported_unvalidated` | Tỉnh báo cáo, chưa kiểm chứng | Cam nhạt |
| `simulated` | Dữ liệu minh hoạ | Tím, viền nét đứt |

### 3.4 Bộ nhập dữ liệu (`app/seed_import.py`, `scripts/import_seed.py`)
- Đọc 15 sheet. Kiểm tra cấu trúc: thiếu sheet hoặc cột thì dừng và báo cụ thể sheet/cột.
- Nhập lặp lại an toàn (idempotent) theo khoá tự nhiên.
- **Nguồn (`origin`) theo `source_id` của file:**
  - `seed:S_RPT` – báo cáo 15/09;
  - `seed:S_XLS` – Excel của Cục;
  - `seed:S_SIM` – số giả lập.
- **Lưu vết khi giá trị thay đổi:** bản cũ đánh dấu `is_current = False`, giữ lịch sử như cơ chế hiện có. Mỗi lần nhập tạo một `data_releases`.
- **Trạng thái duyệt sau khi nhập:**

  | Loại số liệu | Trạng thái duyệt | Trạng thái dữ liệu |
  |---|---|---|
  | Số năm thật (Cục đã công bố) | `published` | Giữ `data_status` của Cục |
  | Số quý giả lập | `published` | `is_simulated = True` |
  | Số tỉnh | `published` | `reported_unvalidated` |
  | Bộ 137 mẫu | Vào qua adapter API (GĐ 3), không qua bộ nhập này | |

- Lệnh dùng:
  ```
  uv run python -m scripts.import_seed --file poc/data/seed/seed_data_2244.xlsx [--dry-run]
  ```
  `--dry-run` in ra số dòng mới / đổi / bỏ, không ghi vào CSDL. Cơ chế này dùng lại cho màn hình so sánh khác biệt ở GĐ 5.

### 3.5 Thay số giả lập hiện có
- `reset_demo`: bỏ bước nộp file toàn quốc giả lập ("Cục Thông tin, Thống kê (giả lập)") cho 46 chỉ tiêu 2244. Thay bằng `import_seed`.
- Giữ 2 file mẫu (Hà Nội, file lỗi) để demo luồng kiểm tra biểu mẫu. Gắn `is_simulated = True`, không tính vào số toàn quốc.
- Số crawler cho 0201–0203 (OpenAlex, Cục SHTT) chuyển thành **số đối chiếu**, không phải số chính thức của chỉ tiêu (theo D2).
- Giữ số crawler cho 0426–0429 (GII, EGDI, HDI…) làm chuỗi lịch sử. Giá trị chính thức kỳ 2025 lấy từ file seed.

### 3.6 Giao diện tối thiểu trong giai đoạn này
- `common.js`:
  - thêm `dataStatus(code)` hiển thị nhãn trạng thái dữ liệu, có tooltip định nghĩa;
  - thêm `simBadge()` hiển thị "Dữ liệu minh hoạ";
  - đổi nhãn cột hiện có thành "Trạng thái duyệt".
- Phụ đề trang Bộ chỉ tiêu tính từ API, thay cho "130 chỉ tiêu thuộc 3 văn bản quy phạm". Ví dụ: "46 chỉ tiêu QĐ 2244 · 8 chỉ tiêu thống kê mẫu · 50 tiêu chí đánh giá".
- Trang chi tiết chỉ tiêu: bảng số liệu thêm cột trạng thái dữ liệu và nhãn minh hoạ.

### 3.7 Kiểm thử
- `test_seed_import.py`:
  - nhập file seed: 46 chỉ tiêu, 108 quan sát năm, 228 quan sát quý giả lập, 162 quan sát tỉnh;
  - nhập lần hai không tạo bản ghi trùng;
  - sửa một giá trị trong file → giá trị mới có hiệu lực, bản cũ còn trong lịch sử (**tiêu chí 1**);
  - file thiếu sheet → báo lỗi rõ ràng.
- `test_traceability.py`: mọi giá trị trả về từ API công khai đều có `origin`, `data_status`, `period` (**tiêu chí 2**).

---

## 4. Giai đoạn 2 – Trang chủ và chi tiết chỉ tiêu (2 ngày)

### 4.1 Trang chủ (spec §6.1)

Bố cục từ trên xuống:

1. **Phần đầu:** tiêu đề, kỳ cập nhật, hình minh hoạ hiện có (thu nhỏ).
2. **Lưới thẻ KPI**, đọc từ `kpi_cards`, 4 cột ở màn hình rộng. Mỗi thẻ gồm:
   - giá trị và đơn vị;
   - ngữ cảnh (năm, tỷ lệ);
   - sparkline nếu chỉ tiêu có ≥ 2 kỳ;
   - nhãn trạng thái dữ liệu;
   - một dòng thông điệp.

   Bấm vào thẻ mở trang chi tiết chỉ tiêu.
3. **Thanh trạng thái 46 chỉ tiêu:** hai thanh xếp chồng 100% đọc từ `status_summary` (tình trạng tính toán; mức sẵn sàng phân tích). Có chú giải và số lượng.
4. **Khung I-O-O-I:** 4 khối Đầu vào → Đầu ra → Hiệu quả → Tác động, mỗi khối là lưới ô mã chỉ tiêu tô màu theo trạng thái dữ liệu. Thay cho vòng trụ cột hiện có.
5. **Phát hiện chính:** 3–4 đoạn ngắn từ `narratives`. Admin sửa được ở GĐ 5.
6. **Vị thế quốc tế:** giữ phần xếp hạng hiện có (GII, EGDI, HDI), đồng bộ số kỳ 2025 với file seed (GII 44/139).
7. Ma trận cơ quan đặt trong khối thu gọn (đã có). Các ô tác vụ (Nộp số liệu / Phê duyệt…) chỉ hiển thị khi đăng nhập Analyst hoặc Admin (GĐ 5).

**API:** `GET /api/home` trả về `kpi_cards`, `status_summary`, khung I-O-O-I, `narratives`, xếp hạng quốc tế.

### 4.2 Trang chi tiết chỉ tiêu (Annex A)
- **Đầu trang:** mã, tên (VI/EN), nhóm, nhãn trạng thái dữ liệu, cơ quan chủ trì / phối hợp, tần suất.
- **Thẻ:** giá trị kỳ mới nhất, thay đổi so với kỳ trước, kỳ.
- **Kết quả và khuyến nghị:** `latest_result_text`, `limitation`, `recommendation` (dạng gấp mở).
- **Mức sẵn sàng:** dải 8 ô theo 8 chiều chất lượng, có chú giải.
- **Chuỗi thời gian:** bộ chọn Quý / Năm (chỉ tiêu chỉ có số năm thì khoá ở Năm, ghi "Số liệu năm"). Kỳ thiếu số liệu để trống, không nối liền. Điểm giả lập vẽ nét đứt.
- **Bảng số liệu:** thêm cột trạng thái dữ liệu; nút tải CSV.
- **Số đối chiếu:** số từ nguồn khác (crawler, 137, tỉnh) hiển thị trong khối "Số liệu đối chiếu", tách khỏi số chính thức.

### 4.3 Kiểm thử
- API `/api/home` trả về 15 thẻ khớp file seed.
- Trang chi tiết của chỉ tiêu có số giả lập thì hiển thị nhãn minh hoạ.

---

## 5. Giai đoạn 3 – 2244 theo quý, Tab 137, ánh xạ và đối soát (3 ngày)

### 5.1 Xử lý chuỗi thời gian (`app/timeseries.py`)
- **Chuẩn hoá mã kỳ:** `2025` (năm), `2025-Q4` (quý), `2025-11` (tháng).
- **Gộp kỳ** tháng → quý → năm theo `aggregation_rule`:
  - `sum`: cộng các kỳ con;
  - `avg`: trung bình các kỳ con;
  - `last`: lấy giá trị kỳ con cuối.

  Kỳ cha thiếu kỳ con thì đánh dấu "chưa đủ kỳ" và không tính.
- **Cửa sổ:** N kỳ gần nhất (4/6/8/12).
- **Mức thay đổi:**
  - MoM, QoQ: so với kỳ liền trước;
  - YoY: so với cùng kỳ năm trước;
  - YTD: luỹ kế từ đầu năm, chỉ khi quy tắc là `sum`.

  Thiếu kỳ so sánh thì trả `null`, không nội suy.

### 5.2 Adapter API anh Định (giả lập)
- `app/connectors/api_dinh.py` theo giao diện `Connector` hiện có (`base.py`). Đọc `mock_137_indicator` và `mock_137_monthly` từ file seed.
- Cấu trúc trả về theo dạng API dự kiến (mã chỉ tiêu, kỳ, giá trị, đơn vị, nguồn báo cáo). Khi có đặc tả thật chỉ thay lớp này.
- Hiển thị trên trang Nguồn dữ liệu như một nguồn, có lịch chạy và nhật ký. Nút "Đồng bộ".
- Nhập 8 chỉ tiêu 137 vào `indicators` (`indicator_set = '137'`) và 192 quan sát tháng.

### 5.3 Ánh xạ trùng 2244 ↔ 137 và đối soát
- Từ `indicator_mappings`: với mỗi cặp, gộp số tháng 137 lên quý/năm và ghi vào chỉ tiêu 2244 với `origin = calc:137`.
- **So sánh với số của Cục** cùng kỳ. Lệch vượt ngưỡng (> 0,5% hoặc ≥ 1 đơn vị với số đếm) thì:
  - tạo cảnh báo "Lệch đối soát 2244 ↔ 137";
  - đưa điểm `calc:137` vào hàng chờ duyệt (dùng lại cơ chế cảnh báo và bộ lọc `kind=calc`).
- Trường hợp demo: 137-M03 → 0209 lệch có chủ đích ở 2025-Q4.
- **Trang Đối soát (Admin):**
  - phần 1: các cặp 2244 ↔ 137 lệch;
  - phần 2: 12 chỉ tiêu lệch Excel ↔ báo cáo (`reconciliations`), nút "Đánh dấu đã xác nhận" kèm ghi chú (lưu vết).

### 5.4 Giao diện
- **Tab 2244** (`/s2244`):
  - bộ chọn Quý (mặc định) / Năm, cửa sổ 4/6/8 quý, chọn mức thay đổi QoQ / YoY / YTD;
  - danh sách 46 chỉ tiêu theo 4 nhóm, mỗi dòng có sparkline, giá trị kỳ mới nhất, mức thay đổi, trạng thái dữ liệu;
  - chỉ tiêu chỉ có số năm ghi "Số liệu năm".
- **Tab 137** (`/s137`):
  - danh mục có tìm kiếm, lọc theo nhóm, tần suất, loại nguồn (chế độ báo cáo / điều tra / hành chính), cờ "Trùng 2244";
  - mỗi dòng có sparkline và mức thay đổi so với kỳ trước.
- **Chi tiết chỉ tiêu 137:** dùng chung trang chi tiết, thêm bộ chọn độ phân giải Tháng / Quý / Năm, cửa sổ 4/6/12 kỳ, thẻ MoM / QoQ / YoY / YTD, cột so sánh cùng kỳ năm trước.
- **So sánh** (`/compare`): chọn 2–4 chỉ tiêu, hiển thị nhiều biểu đồ nhỏ, mỗi chỉ tiêu một trục riêng.
- **Menu bên mới:**
  - Tổng quan;
  - Chỉ tiêu 2244;
  - Chỉ tiêu thống kê 137;
  - Phân tích (nhóm);
  - Địa phương;
  - Nội bộ (nhóm, theo vai trò);
  - Quản trị (nhóm, theo vai trò).

### 5.5 API
- `GET /api/sets/{set}/indicators?group=&freq=&overlap=`
- `GET /api/indicators/{code}/timeseries?res=M|Q|Y&window=N&region=VN` trả về các điểm (có `null` cho kỳ thiếu), `changes {mom, qoq, yoy, ytd}`, `aggregation_rule`, `simulated_periods`.
- `POST /api/connectors/api_dinh/run`
- `GET /api/reconciliation`, `POST /api/reconciliation/{id}/confirm`

### 5.6 Kiểm thử (tiêu chí 4)
- `test_timeseries.py`:
  - gộp sum / avg / last đúng;
  - quý thiếu tháng không được tính;
  - MoM / QoQ / YoY / YTD đúng trên dữ liệu kiểm tra viết tay;
  - cửa sổ 4/6/12 trả đúng số kỳ.
- Chỉ tiêu 2244 theo quý có QoQ / YoY đúng.
- Đối soát: 0209 ở 2025-Q4 phải sinh cảnh báo; các cặp khác không sinh.

---

## 6. Giai đoạn 4 – Phân tích theo báo cáo (3 ngày)

### 6.1 Thư viện biểu đồ (`charts.js`)
Bổ sung vào thư viện SVG hiện có, dùng chung bảng màu:

| Loại | Dùng cho |
|---|---|
| Thanh ngang sắp xếp, có nhãn giá trị | Cơ cấu, top lĩnh vực |
| Thanh xếp chồng 100% | Cơ cấu thay cho biểu đồ tròn |
| Cột nhóm | So sánh theo kỳ, theo hạng mục |
| Cột phân rã đóng góp | Phân rã tăng NSLĐ |
| Slope chart | Cơ cấu ngành 2021 → 2025 |
| Dot plot / bullet | So sánh ASEAN, so với mục tiêu |
| Scatter / bubble | Quy mô × độ sâu giá trị; GDP × điện năng |
| Sơ đồ chuỗi (flow) | Tri thức → giá trị; chính phủ số; I-O-O-I |
| Heatmap | Mức sẵn sàng 46 × 8 |

Mỗi biểu đồ có:
- tiêu đề dạng thông điệp;
- dòng nguồn (ví dụ "Nguồn: Báo cáo 2244, Fig 2.4");
- nút "Bảng số liệu" (bảng thay thế, hỗ trợ trợ năng);
- nút tải CSV.

### 6.2 Trang Phân tích (`/analysis`)
21 biểu đồ từ `chart_series`, nhóm theo khung I-O-O-I:

| Nhóm | chart_id | Loại biểu đồ |
|---|---|---|
| Đầu vào | C_WORKFORCE_MIX, C_DIGITAL_ENT | Thanh ngang |
| | C_INVEST_HEADLINE | Thẻ |
| | C_GERD | Cột + ghi chú phạm vi |
| Đầu ra | C_PUB_SPLIT | Thanh xếp chồng |
| | C_ASEAN_BENCH | Dot plot |
| | C_TT_DIRECTION | Thanh chiều vào / chiều ra |
| | C_KNOWLEDGE_VALUE | Chuỗi tri thức → giá trị |
| Hiệu quả | C_STID_GDP | Đường đa chuỗi |
| | C_LP_DECOMP | Cột phân rã |
| | C_NEW_PRODUCT | Dot plot |
| | C_EFFICIENCY | Thanh |
| Tác động | C_DIGITAL_VA | Đường |
| | C_DIGITAL_VA_REGION | Dot plot |
| | C_SECTOR_SLOPE | Slope |
| | C_SCALE_DEPTH | Scatter |
| | C_GROWTH_ENERGY | Bubble |
| | C_RENEWABLE | Thanh xếp chồng |
| | C_DIGITAL_GOV_CHAIN | Chuỗi 5 bước |
| | C_INCLUSION | Thẻ |
| | C_INTL_INDEX | Thẻ xếp hạng + đường |

Loại biểu đồ chọn theo `recommended_chart` và mô tả spec §6.2. Biểu đồ không đủ dữ liệu thì hiển thị thẻ "Chưa tính được" kèm phương án đo, không vẽ.

### 6.3 Scorecard (`/scorecard`)
- Bảng 4 chiều: chẩn đoán, mức bằng chứng, hàm ý chính sách.
- Ô tín hiệu tô màu theo mức bằng chứng: Established / Indicative-strong / Mixed / Emerging.

### 6.4 Mức sẵn sàng dữ liệu (`/readiness`)
- Heatmap 46 chỉ tiêu × 8 chiều: đầy đủ, nhất quán, độ phủ, mẫu số, độ dài chuỗi, phân tổ, kiểm chứng độc lập, so sánh quốc tế.
- 3 mức màu (Không đủ / Một phần / Đạt).
- Sắp xếp theo nhóm hoặc theo tổng điểm. Lọc theo nhóm.
- Bấm vào ô hiện ghi chú.
- Phía trên: hai thanh trạng thái (dùng chung component với trang chủ).

### 6.5 Địa phương (`/provinces`)
- Bản đồ lưới ô 34 tỉnh, thành phố (D3). Chế độ mặc định: đã nộp / chưa nộp (18/34).
- Chọn chỉ tiêu (0101, 0209, 0210, 0407–0412) → ô hiển thị giá trị dạng số. **Không tô màu theo độ lớn** để tránh hàm ý xếp hạng.
- Bảng giá trị sắp xếp theo tên tỉnh, có đơn vị và trạng thái "chưa kiểm chứng".
- Khối độ phủ từ `provincial_coverage`: tỉnh báo cáo, độ phủ dùng được, vấn đề chính.
- Dòng cảnh báo cố định: "Số liệu do tỉnh tự báo cáo, chưa chuẩn hoá; không dùng để xếp hạng."

### 6.6 Kiểm thử
- API `/api/charts` trả về đủ 21 chart_id. Mỗi chart có `figure_ref` và đơn vị.
- API tỉnh không có tham số sắp xếp theo giá trị.
- Kiểm tra bằng ảnh chụp: không biểu đồ nào tràn khung ở 375px.

---

## 7. Giai đoạn 5 – Phân quyền và quản trị dữ liệu (2 ngày)

### 7.1 Vai trò
| Vai trò | Đăng nhập | Thấy | Làm |
|---|---|---|---|
| Public | Không | Chỉ tiêu `visibility = public`, giá trị `published`; Tổng quan, 2244, 137, Phân tích, Địa phương, Sẵn sàng dữ liệu | Xem, tải CSV |
| Analyst | Có | Thêm khu Nội bộ: Layer 2, Layer 3, Đánh giá chương trình, Mô hình tác động, So sánh | Phân tích, chạy mô hình |
| Admin | Có | Toàn bộ | Nhập dữ liệu, duyệt và công bố, sửa giá trị, đặt cờ hiển thị, đối soát, xem lưu vết |

### 7.2 Triển khai
- `SessionMiddleware` (cookie ký, khoá trong `.env`). Trang `/login` với tài khoản demo (D4); mật khẩu demo nằm trong `.env.example`.
- Dependency `require_role("analyst" | "admin")` cho các API ghi và API nội bộ.
- API đọc dữ liệu lọc theo vai trò ở một chỗ duy nhất (hàm truy vấn chung), tránh rò dữ liệu nội bộ qua endpoint phụ.
- Thanh trên: avatar hiện vai trò; menu và nút tác vụ ẩn theo vai trò.
- Chế độ demo trên Vercel: có nút "Xem với vai trò…" để người xem chuyển nhanh.

### 7.3 Quản trị dữ liệu
- **Nhập file tổng hợp của Cục:** tải file → kiểm tra cấu trúc → xem trước khác biệt so với bản đang dùng (mới / thay đổi / bỏ, có giá trị cũ → mới) → "Công bố". Dùng `import_seed --dry-run` (GĐ 1).
- **Trang Nhập dữ liệu có 2 tab:** "File tổng hợp của Cục" (mới) và "Biểu mẫu theo chỉ tiêu" (đã có).
- **Sửa một giá trị:** bắt buộc nhập lý do. Ghi lưu vết: người sửa, thời điểm, cũ → mới, lý do.
- **Quản lý chỉ tiêu:** cờ public / internal, trạng thái dữ liệu, sửa đoạn "Phát hiện chính".
- **Quản lý ánh xạ 2244 ↔ 137:** thêm, sửa, xoá cặp và quy tắc gộp.
- **Nhật ký:** trang xem lưu vết, lọc theo người, chỉ tiêu, thời gian.

### 7.4 Kiểm thử (tiêu chí 3)
- Public gọi mọi API đọc không nhận được chỉ tiêu `internal` hoặc giá trị chưa công bố. Kiểm tra trên toàn bộ danh sách route.
- Public gọi API ghi → 401. Analyst gọi API của Admin → 403.
- Sửa giá trị không có lý do → 422. Có lý do → lưu vết đủ trường.

---

## 8. Giai đoạn 6 – Layer 2, Layer 3, mô hình tác động, song ngữ (3 ngày)

### 8.1 Layer 2 – QĐ 39 (khung)
- `indicator_set = '39'`, liên kết `parent_id` tới chỉ tiêu 2244.
- Chưa có danh mục thật, nên tạo 6–8 chỉ tiêu con mẫu cho 2–3 chỉ tiêu 2244, gắn nhãn "Ví dụ minh hoạ cấu trúc".
- Trang drill-down 2244 → 39 theo cấp / ngành, nhãn nguồn (bộ ngành / quốc tế / TCTK).

### 8.2 Layer 3 – Dữ liệu thử nghiệm (sắp xếp lại phần đã có)
| Màn hình | Dữ liệu | Hiện trạng |
|---|---|---|
| Chuyên gia theo loại đơn vị (trường / viện / doanh nghiệp), top đơn vị | OpenAlex institutions | Đã có bảng; thêm thanh ngang |
| Tin tuyển dụng theo kỹ năng công nghệ theo tháng | Tin tuyển dụng mẫu (`generate_job_sample`) | Đã có dữ liệu; thêm biểu đồ đường |
| Sáng chế theo lĩnh vực × năm | Bộ thu thập Cục SHTT | Thêm heatmap |
| Đề xuất tiêu chí mới | Module đề xuất hiện có | Giữ, chuyển vào Layer 3 |

Toàn bộ trang Layer 3 gắn nhãn "Dữ liệu thử nghiệm".

### 8.3 Mô hình đánh giá tác động (internal)
- **Luồng 5 bước** (spec §9):
  1. chọn dữ liệu hoặc tải file;
  2. làm sạch: chuẩn hoá đơn vị, xử lý thiếu, phát hiện ngoại lai, ghi nhật ký từng bước;
  3. chọn mô hình và tham số;
  4. chạy như tác vụ nền, lưu lịch sử;
  5. kết quả.
- **Mô hình mẫu:** phân rã tăng trưởng năng suất lao động (growth accounting) trên dữ liệu `C_LP_DECOMP`, cộng một hồi quy tuyến tính đơn giản để minh hoạ. Ghi rõ "Mô hình minh hoạ; mô hình chính thức do nhóm phân tích cung cấp".
- **Kết quả:** file Excel (sheet đầu vào đã làm sạch, nhật ký làm sạch, hệ số, đóng góp, ghi chú phương pháp) + biểu đồ + lịch sử các lần chạy.
- Bảng `model_runs`: tham số, thời điểm, người chạy, trạng thái, đường dẫn file kết quả.
- **Kiểm thử (tiêu chí 5):** chạy pipeline với dữ liệu mẫu → file .xlsx tồn tại và có đủ sheet; tổng đóng góp bằng tốc độ tăng NSLĐ (sai số cho phép).

### 8.4 Đánh giá chương trình 50 tiêu chí
Theo D1: chuyển vào khu Nội bộ, không đổi chức năng.

### 8.5 Song ngữ (D6)
- Từ điển `I18N` trong `common.js` cho menu, tiêu đề trang, nhãn trạng thái, nút.
- Nút VI/EN trên thanh trên, lưu lựa chọn trong `localStorage`.
- Tên chỉ tiêu dùng `name_en` khi chọn EN. Văn bản diễn giải chưa có bản EN thì hiển thị tiếng Việt kèm ghi chú.

---

## 9. Giai đoạn 7 – Video, tài liệu, nghiệm thu (1,5 ngày)

### 9.1 Video giới thiệu
Dựng lại kịch bản theo định hướng mới, giữ cấu trúc và hiệu ứng hiện có:

| Cảnh | Hiện tại | Sửa thành |
|---|---|---|
| Hiện trạng | "130 chỉ số · 39 cơ quan" | "46 chỉ tiêu QĐ 2244 · 18/34 tỉnh đã nộp · 33/46 đáp ứng yêu cầu tính toán" |
| Giải pháp | 3 kênh: đơn vị báo cáo, nguồn công khai, tài liệu | 2 kênh chính: File tổng hợp của Cục, API hệ thống thống kê; nguồn quốc tế là kênh tham chiếu |
| Nguồn tự động | 7 nguồn thu thập | Đồng bộ API (bộ 137, theo tháng) và đối soát 2244 ↔ 137 |
| Tổng quan | 4 KPI | 15 thẻ KPI, thanh trạng thái 46 chỉ tiêu |
| (mới) | | Theo quý: cửa sổ 4/6/12 kỳ, QoQ / YoY |
| (mới) | | Địa phương và mức sẵn sàng dữ liệu |
| Đánh giá / Đề xuất | 50 tiêu chí; đề xuất tiêu chí | Gộp thành "Phân tích nội bộ": mô hình tác động, Layer 3 |
| Người dùng | 4 nhóm | 3 vai trò: Công chúng, Cán bộ phân tích, Quản trị dữ liệu |

Chụp lại 8 ảnh màn hình trong `img/` sau khi giao diện ổn định. Rà lại toàn bộ khung hình như lần trước.

### 9.2 Tài liệu
- `poc/README.md`: cách nhập file seed, cách thay file của Cục, tài khoản demo, cấu trúc trang mới.
- Cập nhật `UI_Redesign_Plan.md` (sitemap mới) và `CSIRO_2244_Doi_chieu.md` (đánh dấu mục đã xử lý).
- `poc/data/seed/README.md`: nguồn và quy ước dữ liệu.

### 9.3 Nghiệm thu
- Chạy toàn bộ pytest: test cũ + test mới cho 5 tiêu chí.
- Chụp mọi trang ở 1440px và 375px. Kiểm tra: không tràn ngang, không lỗi console, mọi số có nhãn trạng thái.
- Danh sách kiểm tra theo spec §10, ghi kết quả vào README.

---

## 10. Ảnh hưởng tới phần khác

| Hạng mục | Ảnh hưởng | Xử lý |
|---|---|---|
| CSDL dev | Thêm cột và bảng; `create_all` không tự thêm cột | Chạy `reset_demo --yes` sau GĐ 1. Bước nhập seed không cần Internet |
| Bản demo Vercel | Dùng ảnh chụp CSDL `poc/deploy/demo.db` | Sau GĐ 1 và cuối GĐ 7 dựng lại `demo.db`. Phiên deploy thực hiện commit và triển khai |
| `reset_demo` | Đổi thứ tự: nhập seed → adapter 137 → đối soát → bộ thu thập quốc tế (tuỳ chọn) | Thêm cờ `--offline` để bỏ qua các bước cần Internet |
| Test hiện có | Một số test dựa trên số giả lập toàn quốc | Sửa fixture theo số seed. Giữ nguyên ý nghĩa kiểm thử |
| Trang hiện có | `/connectors` đổi thành "Nguồn dữ liệu"; `/upload` thêm tab; `/cases`, `/insights` vào khu nội bộ | Giữ URL cũ, chuyển hướng nếu đổi |

---

## 11. Rủi ro

| Rủi ro | Mức | Giảm thiểu |
|---|---|---|
| Cục gửi file mới có cấu trúc khác file seed | Trung bình | Bộ nhập kiểm tra cấu trúc và báo lỗi theo sheet/cột. Ánh xạ tên cột đặt trong một chỗ cấu hình |
| Danh sách 20 chỉ tiêu trùng và quy tắc gộp chưa có | Cao | Ánh xạ là dữ liệu (bảng), sửa qua giao diện Admin, không ghi cứng |
| Đặc tả API anh Định khác giả định | Trung bình | Adapter tách riêng, cùng giao diện `Connector`. Chỉ thay một tệp |
| Người xem hiểu nhầm số giả lập là số thật | Cao | Nhãn minh hoạ bắt buộc, nét đứt trên biểu đồ, không dùng trong thẻ KPI chính thức |
| Số tỉnh bị hiểu là xếp hạng | Trung bình | Không tô màu theo độ lớn, không sắp xếp theo giá trị, cảnh báo cố định |
| Khối lượng ≈ 17 ngày | Trung bình | Giai đoạn độc lập, có thể dừng sau GĐ 4 để demo hội thảo (đủ tiêu chí 1, 2, 4) |

---

## 12. Mốc demo đề xuất
- **Mốc A (sau GĐ 1–2, ≈ 4,5 ngày):** số thật, trạng thái dữ liệu, trang chủ và chi tiết chỉ tiêu theo spec.
- **Mốc B (sau GĐ 3–4, ≈ 10,5 ngày):** đủ nội dung cho hội thảo: theo quý, bộ 137, đối soát, phân tích, địa phương, sẵn sàng dữ liệu.
- **Mốc C (sau GĐ 5–7, ≈ 17 ngày):** đủ 5 tiêu chí nghiệm thu, phân quyền, Layer 2/3, mô hình, video mới.
