# Innovation Hub – PoC

Hiện thực hoá [PoC_Plan_Innovation_Hub.md](../PoC_Plan_Innovation_Hub.md). Đã hoàn thành cả 4 sprint: **Nền tảng → Thu thập → Hiển thị & đánh giá → Mở rộng & demo**.

📄 Tài liệu: [Kịch bản demo](docs/DEMO_SCRIPT.md) · [Kịch bản kiểm thử người dùng](docs/UAT_checklist.md) · [Báo cáo đánh giá PoC](docs/PoC_Evaluation.md)

## Cấu trúc

```
poc/
├── docker-compose.yml        # Postgres 16 + MinIO (dự phòng) + backend
├── docs/                     # kịch bản demo, kịch bản UAT, báo cáo đánh giá PoC
├── data/
│   ├── raw/indicator_survey.xlsx   # workbook nguồn (bản sao)
│   ├── storage/                    # file minh chứng: snapshot crawl, file upload (lưu theo sha256)
│   └── import_report.json          # báo cáo lần import registry gần nhất
├── templates/                # template Excel cho đơn vị (sinh tự động)
├── sample_data/              # file đã điền số liệu GIẢ LẬP (hợp lệ + có lỗi)
└── backend/
    ├── app/
    │   ├── models.py             # schema (registry → dữ liệu → duyệt → case → đề xuất)
    │   ├── registry_import.py    # import workbook → registry (idempotent)
    │   ├── template_spec.py      # định nghĩa template (dùng chung cho sinh file & validate)
    │   ├── catalog.py            # tên phân tổ dùng chung
    │   ├── validation.py         # kiểm tra file upload (lỗi/cảnh báo theo dòng)
    │   ├── submissions.py        # nhận file template + tài liệu Doc-ETL
    │   ├── datapoints.py         # ghi điểm dữ liệu có lịch sử phiên bản + quy trình duyệt
    │   ├── calculations.py       # tự tính chỉ số dẫn xuất từ dữ liệu đã công bố
    │   ├── docetl.py             # trích số liệu từ PDF/HTML/TXT
    │   ├── analytics.py          # tổng hợp dashboard, chọn giá trị tiêu biểu, ưu tiên nguồn
    │   ├── reports.py            # xuất báo cáo Excel
    │   ├── case_scoring.py       # chấm điểm case theo 50 tiêu chí chương trình
    │   ├── external.py           # 6 bộ thu thập dữ liệu ngoài (OpenAlex, World Bank, tuyển dụng)
    │   ├── suggestions.py        # đề xuất tiêu chí mới + sàng lọc trùng + duyệt vào registry
    │   ├── connectors/           # 7 connector + runner + chứng chỉ trung gian bổ sung
    │   ├── scheduler.py          # chạy connector định kỳ
    │   ├── storage.py            # kho file minh chứng
    │   ├── api/                  # REST API
    │   └── static/               # Tổng quan, Registry, Chi tiết chỉ tiêu, Nộp số liệu, Thu thập,
    │                             # Duyệt dữ liệu, Đánh giá case, Báo cáo in; charts.js (SVG, không cần CDN)
    ├── scripts/
    │   ├── import_registry.py
    │   ├── generate_templates.py
    │   ├── run_connectors.py
    │   ├── create_demo_case.py
    │   ├── generate_job_sample.py
    │   └── reset_demo.py         # dựng lại toàn bộ dữ liệu demo (XOÁ dữ liệu cũ, cần --yes)
    └── tests/                    # 63 test, chạy offline trên fixture lấy từ nguồn thật
```

## Chạy nhanh trên máy (SQLite, không cần Docker)

Yêu cầu: [uv](https://docs.astral.sh/uv/). Cách nhanh nhất – dựng toàn bộ dữ liệu demo bằng một lệnh (⚠ xoá dữ liệu cũ):

```bash
cd poc/backend
uv run python -m scripts.reset_demo --yes             # thêm --offline nếu không có Internet
uv run uvicorn app.main:app --port 8000
```

> Khi cấu trúc CSDL thay đổi (ví dụ sau GĐ 1 của kế hoạch v2), server dừng với thông báo "CSDL được tạo từ phiên bản cũ…". Chạy lại lệnh `reset_demo` ở trên.

Hoặc từng bước:

```bash
cd poc/backend
uv run python -m scripts.import_registry      # tạo bảng + import registry
uv run python -m scripts.import_seed          # nhập file dữ liệu chuẩn của Cục (data/seed/), không cần Internet
uv run python -m scripts.generate_templates   # sinh template + dữ liệu giả lập
uv run python -m scripts.run_connectors       # thu thập từ 7 nguồn (cần Internet)
uv run python -m scripts.create_demo_case     # tạo case demo (cần Internet – OpenAlex)
uv run uvicorn app.main:app --port 8000       # mở http://localhost:8000
```

Chạy test:

```bash
uv run --group dev pytest -q
```

## Chạy bằng Docker (Postgres)

```bash
cd poc
docker compose up --build
```

- Ứng dụng: http://localhost:8000 · API docs: http://localhost:8000/docs
- Trong Docker, connector tự chạy 3h sáng thứ Hai (`ENABLE_SCHEDULER=true`).
- Mật khẩu trong compose là giá trị dev mặc định; đổi qua biến môi trường / file `.env` khi triển khai thật.
- ⚠️ Chưa chạy thử được bằng Docker trên máy dev (Docker Desktop đang tắt) – mới kiểm chứng với SQLite.

## Luồng dữ liệu

```
Đơn vị upload .xlsx ──► validate (lỗi → trả về theo dòng, không nhập) ──┐
Tài liệu PDF/HTML ──► Doc-ETL (luật + từ khoá, kèm đoạn trích) ─────────┤
Connector (7 nguồn) ──► snapshot nguồn ──► parse ──► kiểm tra ──────────┤
                                                                        ▼
                        data_points (lịch sử phiên bản theo nguồn gốc)
                 nguồn A ──► công bố ngay │ còn lại ──► hàng đợi duyệt
                                          ▼
                      người duyệt: công bố / từ chối (có lý do, audit log)
                                          ▼
                 tự tính chỉ số dẫn xuất (tỷ lệ, tăng trưởng) từ dữ liệu đã công bố
```

## Kết quả Sprint 2

| Hạng mục | Kết quả |
|---|---|
| Upload template 0101/0102: kiểm tra 9 loại lỗi theo dòng/cột, cảnh báo biến động > 50%, lệch tổng thành phần > 2%, lệch nguồn độc lập > 25% | ✅ File mẫu lỗi bị chặn với đúng 9 dòng lỗi |
| Nộp lại cùng đơn vị: giữ lịch sử phiên bản, chỉ ghi giá trị thay đổi | ✅ |
| Hàng đợi duyệt: lọc theo chỉ tiêu/nguồn/địa bàn/lượt nộp/lần chạy, đối chiếu nguồn khác, đoạn trích + file minh chứng, duyệt hàng loạt, từ chối bắt buộc ghi lý do | ✅ |
| Tự tính: tỷ lệ tiến sĩ, tỷ lệ nữ (0101); cơ cấu nguồn chi (0102); tăng trưởng (0201–0203); tỷ trọng chứng thư mới (0425). Tự thu hồi khi đầu vào bị từ chối | ✅ |
| Doc-ETL: PDF/HTML/TXT → ứng viên có đoạn trích, luôn qua duyệt | ✅ (luật cho 0425, 0405 + dự phòng theo từ khoá) |
| 7 connector chạy thật thành công, có snapshot minh chứng, chạy lại không trùng | ✅ |
| ≥ 10 chỉ tiêu có dữ liệu trong DB | ✅ 10 chỉ tiêu: 0101, 0102, 0201, 0202, 0203, 0405, 0425, 0426, 0428, 0429 |

### Connector

| Connector | Chỉ tiêu | Nguồn | Tin cậy | Ghi chú |
|---|---|---|---|---|
| `gii` | 0428 | CSV trang GII Ranking (WIPO) | A – tự công bố | Điểm + thứ hạng tổng, Đầu vào, Đầu ra 2020–2026 |
| `egdi` | 0426 | Hồ sơ quốc gia UN EGOVKB | A – tự công bố | EGDI, thứ hạng, EPI các kỳ 2016–2024 |
| `hdi` | 0429 | CSV Composite indices (UNDP HDR) | A – tự công bố | HDI 1990–2023, thứ hạng |
| `ipvn` | 0202, 0203 | Excel thống kê năm của Cục SHTT | A/B – cần duyệt | Sáng chế + GPHI theo 63 tỉnh, toàn quốc = tổng tỉnh; xử lý được 2 bố cục file khác nhau |
| `openalex` | 0201 | OpenAlex API | B – cần duyệt | **Proxy** cho Scopus/WoS, độ phủ rộng hơn nên số cao hơn |
| `worldbank` | 0101, 0102, 0405 | World Bank API (UNESCO UIS) | A/B – cần duyệt | Nguồn đối chiếu độc lập; 0405 là **proxy** (mẫu số là hàng chế tạo) |
| `neac` | 0425 | Bài công bố CA-Index trên neac.gov.vn | B/C – cần duyệt | Doc-ETL: 26,45 triệu chứng thư lũy kế, 12,56 triệu cấp mới 2025 |

### Sự cố thực tế khi crawl & cách xử lý

- **ipvietnam.gov.vn** không gửi chứng chỉ SSL trung gian → kèm chứng chỉ trung gian công khai Sectigo DV R36 (`app/connectors/certs/`, đã xác minh chain lên root có sẵn). **Không** tắt kiểm tra SSL.
- **UN EGOVKB** trả header HTTP sai chuẩn → tự động chuyển sang `http.client` (dễ dãi hơn) khi httpx từ chối.
- **WIPO GII** là ứng dụng JavaScript → dùng thẳng file CSV mà trang đó tải về.

### API mới

| Method | Endpoint | Mô tả |
|---|---|---|
| POST | `/api/submissions` | Nộp file .xlsx theo template |
| POST | `/api/documents` | Nộp tài liệu PDF/HTML/TXT cho Doc-ETL (`indicator_code`, `period`, `source_url`) |
| GET | `/api/submissions[/{id}]` | Lượt nộp, lỗi, cảnh báo, điểm dữ liệu |
| GET / POST | `/api/connectors`, `/api/connectors/{name}/run` | Danh sách, chạy connector |
| GET | `/api/crawl-runs` | Lịch sử chạy |
| GET | `/api/review`, `/api/review/summary` | Hàng đợi duyệt, thống kê |
| POST | `/api/review/actions` | `{ids, action: approve\|reject, reviewer, note}` |
| GET | `/api/indicators/{code}/data` | Dữ liệu của chỉ tiêu |
| GET | `/api/data-points/{id}/history` | Lịch sử duyệt + các phiên bản |
| GET | `/api/evidence/{id}` | Tải file minh chứng (HTML ngoài luôn tải về, không hiển thị trực tiếp) |

## Quy ước & giả định cần nghiệp vụ xác nhận

1. **Mã chuẩn** là mã QĐ 2244. Mã khác lệch được lưu ở `indicator_aliases`.
2. **Trụ cột**: QĐ 2244 nhóm I→Đầu vào, II→Kết quả, III→Hiệu quả, IV→Tác động. Tiêu chí chương trình: I→Đầu vào, II–III→Kết quả, IV–V→Tác động.
3. **Phân tổ trong template 0101/0102** là đề xuất của nhóm PoC (xem `app/template_spec.py`).
4. **Ngưỡng cảnh báo** (biến động 50%, lệch nguồn 25%, lệch tổng 2%) và **mức tin cậy được tự công bố** (chỉ A) là giá trị đề xuất.
5. Số liệu đơn vị tự báo cáo mặc định tin cậy **C**; Doc-ETL **B/C**.
6. Toàn bộ số liệu trong `sample_data/` là **giả lập**.
7. Chưa có đăng nhập/phân quyền: người duyệt tự nhập tên (lưu vào audit log).
8. Schema vẫn tạo bằng `create_all` (chưa có dữ liệu thật cần giữ). Cần chuyển sang Alembic trước khi có dữ liệu thật.

## Chưa làm trong Sprint 2

- Trích xuất bằng LLM cho Doc-ETL (chưa có API key) – hiện dùng luật + từ khoá.
- OCR cho PDF scan.
- MinIO/S3 – đang lưu file vào thư mục local.
- Thông báo email/nhắc hạn nộp cho đơn vị.

## Kết quả Sprint 3

| Hạng mục | Kết quả |
|---|---|
| **Tổng quan** (`/`): số chỉ tiêu có số liệu, độ phủ 4 trụ cột, thẻ giá trị tiêu biểu (xu hướng, so kỳ trước, % đạt mục tiêu), GII/EGDI/HDI, ma trận 46 chỉ tiêu × 8 năm, tiến độ theo cơ quan chủ trì | ✅ |
| **Chi tiết chỉ tiêu** (`/indicator?code=`): biểu đồ chuỗi thời gian có đường mục tiêu, so sánh 2 chuỗi (chặn khi khác đơn vị), chọn địa bàn, bảng mọi phân tổ × nguồn với trạng thái + minh chứng | ✅ |
| **Quy tắc giá trị chính thức** khi nhiều nguồn: đơn vị chủ trì > nguồn công khai/quốc tế > tài liệu > tự tính | ✅ |
| **Báo cáo**: Excel 3 sheet (Tổng hợp 5 năm, Chi tiết, Giải thích) + trang in/PDF khổ A4 ngang | ✅ |
| **Đánh giá case** (`/cases`): tạo case (DOI, tác giả OpenAlex, kinh phí, mục tiêu, văn bằng); tự tính SCI-01/04/06/07/08 từ OpenAlex; TECH-02/07 kê khai; TECH-01 TRL có gợi ý tự động; nhập tay các tiêu chí khác; duyệt/loại từng điểm | ✅ |
| **Scorecard**: điểm 0–100 so với mục tiêu đăng ký, điểm theo 5 nhóm, kết luận + điểm mạnh/yếu, cảnh báo "tạm tính" và "độ phủ thấp" | ✅ Case demo: 84,8/100, 12/50 tiêu chí |

### Cách chấm điểm case

- Điểm tiêu chí = mức đạt so với **mục tiêu đăng ký** của case (hoặc mức chuẩn mặc định), chặn ở 100. Với tiêu chí "càng thấp càng tốt" (kinh phí/bài) điểm = mục tiêu ÷ thực tế.
- Điểm nhóm = trung bình các tiêu chí có điểm; điểm tổng = trung bình các nhóm.
- Kết luận: ≥ 80 tốt · 60–80 khá · 40–60 trung bình · < 40 yếu; < 5 tiêu chí → "chưa đủ dữ liệu"; < 30% tiêu chí → ghi rõ "độ phủ thấp".
- Gợi ý TRL dò từ khoá trong mô tả và **bỏ qua cụm bị phủ định** ("chưa thử nghiệm thực tế" không tính là TRL 7). Hội đồng luôn là người quyết định.
- Tính lại với cùng dữ liệu thì giữ trạng thái đã xác nhận; dữ liệu đổi thì chuyển về "chờ duyệt".

> **Case demo là giả lập**: 20 DOI và 12 tác giả được lấy mẫu từ OpenAlex (bài có tác giả Việt Nam về pin lithium 2021–2024) chỉ để minh hoạ cách tính, không phải kết quả của nhiệm vụ thật nào. Kinh phí, mục tiêu, văn bằng, TRL, tiêu chí nhập tay đều giả lập. Giao diện chỉ hiện số liệu tổng hợp, không hiện tên nhà khoa học.

### API mới

| Method | Endpoint | Mô tả |
|---|---|---|
| GET | `/api/dashboard` | Toàn bộ dữ liệu trang Tổng quan |
| GET | `/api/indicators/{code}/series` | Chuỗi thời gian theo phân tổ × nguồn, giá trị tiêu biểu |
| GET | `/api/reports/indicators.xlsx?year=` | Báo cáo Excel |
| GET / POST / PUT | `/api/cases`, `/api/cases/{id}` | Danh sách, tạo, sửa, scorecard |
| POST | `/api/cases/{id}/compute` | Tính lại từ OpenAlex |
| GET / POST | `/api/cases/{id}/trl-suggestion`, `/api/cases/{id}/trl` | Gợi ý và chấm TRL |
| POST | `/api/cases/{id}/manual` | Nhập tiêu chí khác |
| POST | `/api/cases/{id}/scores/{code}/review` | Xác nhận / loại điểm |

## Chưa làm trong Sprint 3

- Upload file "tự do" + LLM gợi ý ánh xạ vào chỉ tiêu (cần API key) – Sprint 4 nếu có key.
- Chỉ số SCI-03 (tạp chí Q1/top 25%) cần dữ liệu xếp hạng tạp chí (Scopus/JCR) – hiện nhập tay.
- Đối chiếu tự động văn bằng SHTT kê khai với Công báo/WIPO Publish.

## Kết quả Sprint 4

| Hạng mục | Kết quả |
|---|---|
| 6 bộ thu thập dữ liệu ngoài: số nhà khoa học theo h-index, 560 tổ chức nghiên cứu VN, công bố có đồng tác giả doanh nghiệp, công bố theo lĩnh vực, sáng chế trong nước/nước ngoài + doanh nghiệp mới (World Bank), tin tuyển dụng (CSV) | ✅ Chạy thật thành công |
| Chỉ lưu số liệu **tổng hợp** và thực thể cấp **tổ chức** – không lưu hồ sơ cá nhân nhà khoa học | ✅ |
| 8 đề xuất tiêu chí mới, mỗi đề xuất có định nghĩa, công thức, nguồn, tin cậy dự kiến, lý do, số liệu tính thử, điểm độ mới / khả thi / ưu tiên | ✅ |
| Sàng lọc trùng với 130 chỉ tiêu hiện có (so khớp từ có trọng số độ hiếm) + hiện chỉ tiêu gần nhất để chuyên gia so sánh | ✅ (có báo nhầm – xem dưới) |
| Chuyên gia chấp nhận → chỉ tiêu `DX-xx` trong registry + số liệu tính thử vào hàng đợi duyệt; từ chối bắt buộc ghi lý do | ✅ |
| Script dựng lại toàn bộ demo (~1 phút), kịch bản demo 7 bước, kịch bản UAT, báo cáo đánh giá PoC | ✅ |
| Kiểm thử với 2–3 người dùng thật | ❌ Chưa làm được – đã có kịch bản |

**8 đề xuất (giá trị tính thử từ dữ liệu thật trừ tuyển dụng):**

| Đề xuất | Giá trị gần nhất | Ghi chú |
|---|---|---|
| Tỷ lệ đơn sáng chế của người nộp đơn trong nước | 12,4% (2024) | Mức làm chủ công nghệ |
| Tỷ trọng công bố thuộc lĩnh vực công nghệ chiến lược | 23,0% (2025) | CNTT, Kỹ thuật, Vật liệu, Năng lượng |
| Số doanh nghiệp VN có công bố khoa học | 8 (2025) | OpenAlex phân loại DN còn rất thiếu |
| Tỷ lệ công bố có đồng tác giả doanh nghiệp | 0,9% (2025) | ⚠ bị báo nhầm "có thể trùng SCI-04" |
| Số tỉnh có ≥ 10 đơn sáng chế + GPHI | 21 (2025) | Lan toả vùng |
| Số nhà khoa học tại VN có h-index ≥ 20 | 1.587 (2026) | Ảnh chụp 1 kỳ |
| Tỷ trọng tin tuyển dụng R&D/AI/bán dẫn | 10,5% (2025) | **Dữ liệu giả lập** |
| Số doanh nghiệp mới thành lập | 136.757 (2024) | ⚠ "Có thể trùng ECO-06" – đúng là trùng |

**Hạn chế của bước sàng lọc trùng:** so khớp theo từ bị nhiễu bởi âm tiết tiếng Việt ("đồng **tác** giả" và "hợp **tác**") nên báo nhầm SCI-04. Hệ thống chỉ cảnh báo, chuyên gia quyết định; khi có API, thay bằng so khớp ngữ nghĩa (embedding/LLM).

### API mới

| Method | Endpoint | Mô tả |
|---|---|---|
| GET / POST | `/api/external/collectors`, `/api/external/collectors/{name}/run` | Bộ thu thập dữ liệu ngoài |
| GET | `/api/external/signals` | Số liệu tổng hợp đã thu |
| GET | `/api/external/institutions?type=&limit=` | Tổ chức nghiên cứu tại VN |
| GET / POST | `/api/suggestions`, `/api/suggestions/generate` | Danh sách / sinh lại đề xuất |
| POST | `/api/suggestions/{id}/review` | `{action: accept\|reject, reviewer, note}` |

Kết luận đánh giá và khuyến nghị cho MVP: xem [docs/PoC_Evaluation.md](docs/PoC_Evaluation.md).

## Giao diện mới & video giới thiệu

- Giao diện đã chuyển sang design system "tech-art, ít chữ" theo [UI_Redesign_Plan.md](../UI_Redesign_Plan.md):
  - sidebar 3 nhóm, tìm kiếm `Ctrl K`, icon SVG thống nhất;
  - hộp thoại thay `prompt()`; Hàng chờ duyệt có panel chi tiết, thao tác hàng loạt, phím tắt `J/K/X/A/R` và **Hoàn tác** (đưa số liệu về chờ duyệt, có ghi nhật ký);
  - không tràn ngang trên điện thoại (375px).
- Bản mẫu thiết kế: [docs/ui-mockup/index.html](docs/ui-mockup/index.html).
- **Video giới thiệu (~1 phút 16 giây, kiểu website promo, có thuyết minh):** [docs/demo-video/index.html](docs/demo-video/index.html).
  - Không nhắc tới số hiệu quyết định trên hình hay trong lời đọc.
  - Nội dung: ảnh chụp giao diện thật (`img/p_*.webp`) trong khung laptop, cửa sổ trình duyệt, điện thoại; tường ảnh 3D; chuyển cảnh liền mạch. Chữ trên hình chỉ còn tiêu đề ngắn, phần giải thích do lời thuyết minh đảm nhận.
  - Không có thanh tiến trình, không đánh số cảnh. Thanh điều khiển chỉ hiện khi rê chuột hoặc khi dừng.
  - Mở đầu bằng 3 cảnh hiện trạng dùng số liệu thật của Cục: số liệu rời rạc; cùng chỉ tiêu nhưng hai con số (0101: 2.260.019 ↔ 2.499.736, 12 chỉ tiêu lệch); thiếu và chậm (18/34 tỉnh, 15/46 chỉ tiêu thiếu thông tin).
  - Âm thanh `audio/thuyetminh.m4a` (dài đúng bằng video):
    - Lời thuyết minh kể chuyện liền mạch (vấn đề → giải pháp → lợi ích), bổ sung cho chữ trên hình chứ không đọc lại. Giọng AI tiếng Việt Microsoft HoaiMy, tạo bằng `edge-tts`, nhanh hơn mặc định 12%. Mỗi cảnh chuyển đúng lúc lời nói tới ý đó, theo mốc thời gian từng từ do `edge-tts` trả về.
    - Nhạc nền tự tổng hợp, 120 nhịp/phút: mở đầu nhẹ, phần hiện trạng dồn dần, bùng lên đúng lúc vào phần giải pháp. Nhạc tự nhỏ đi khi có lời.
    - Hình bám theo đồng hồ của tiếng nên không lệch. Video mở ra ở trạng thái dừng và chờ bấm nút phát, vì trình duyệt chặn tự phát khi có tiếng (`?autoplay` để thử tự phát).
  - Video nền trong `vid/` (`paperwork.mp4`, `stress.mp4`, `hanoi.mp4`; 720p, không tiếng): clip miễn phí từ Pexels (8478951, 6100900, 32934303), giấy phép Pexels không bắt buộc ghi công. Thiếu tệp thì tự ẩn.
  - Mở bằng trình duyệt, không cần server. Font Montserrat tải từ Google Fonts; không có Internet thì dùng font hệ thống.
  - Phím: `Space` phát/dừng, `←/→` chuyển cảnh, `M` tắt/bật tiếng, `F` toàn màn hình. Muốn ra file MP4 thì quay màn hình khi phát toàn màn hình.
  - Khi giao diện đổi, chụp lại ảnh bằng headless Chrome ở độ rộng 1440px rồi chuyển sang `.webp`.

## Kế hoạch v2 – GĐ 1: dữ liệu chuẩn của Cục

Theo [PoC_Plan_v2_CSIRO2244.md](../PoC_Plan_v2_CSIRO2244.md). Số liệu 46 chỉ tiêu QĐ 2244 lấy từ file `data/seed/seed_data_2244.xlsx` (repo CSIRO-2244-Documents). Không còn dùng file toàn quốc giả lập.

- **Nhập file:** `uv run python -m scripts.import_seed [--file …] [--dry-run]`. Chạy lại an toàn. Giá trị đổi thì bản cũ thành lịch sử; giá trị không còn trong file thì gỡ khỏi bản hiện hành. Mỗi lần nhập ghi một bản ghi `data_releases`.
- **Hai loại trạng thái:**
  - *trạng thái dữ liệu* (`data_status`: chính thức, ước tính, đang cập nhật…) theo phân loại của Cục;
  - *trạng thái duyệt* (chờ duyệt / đã công bố) giữ như cũ.
- **Số giả lập** (`is_simulated`): số quý minh hoạ trong file seed và file mẫu của đơn vị ghi "giả lập". Giao diện gắn nhãn "Dữ liệu minh hoạ". Giá trị tiêu biểu chỉ dùng số năm, và bỏ số giả lập khi chỉ tiêu đã có số thật.
- **Thứ tự ưu tiên nguồn:** số của Cục → đơn vị chủ trì → nguồn thu thập → tài liệu → tự tính. Số OpenAlex hiển thị là "Số đối chiếu".
- **Bảng phụ đã nhập** cho các giai đoạn sau: vùng (34 tỉnh), mức sẵn sàng 46 × 8, dữ liệu 21 biểu đồ, 15 thẻ KPI, scorecard, tóm tắt trạng thái, độ phủ tỉnh, đối soát Excel ↔ báo cáo, ánh xạ 2244 ↔ 137.
- **Bản demo Vercel:** `poc/deploy/demo.db` đã dựng lại từ CSDL mới.

## Kế hoạch v2 – GĐ 2: trang chủ và chi tiết chỉ tiêu

- **Trang chủ** (`/`, API `GET /api/home`). Toàn bộ nội dung đọc từ dữ liệu đã nhập, không ghi cứng số:
  - 15 thẻ KPI theo sheet `kpi_cards` (trạng thái dữ liệu, thông điệp, sparkline khi chỉ tiêu có ≥ 2 kỳ);
  - hai thanh trạng thái 46 chỉ tiêu (Bảng 1.4, Annex B);
  - khung I-O-O-I tô màu mã chỉ tiêu theo trạng thái dữ liệu;
  - "Phát hiện chính": 4 đoạn tiếng Việt tóm tắt từ scorecard của báo cáo, tạo một lần khi nhập file và không bị ghi đè khi nhập lại. Admin sẽ sửa được ở GĐ 5.
- **Trang chi tiết chỉ tiêu:**
  - kết quả, hạn chế, khuyến nghị theo Annex A (nguyên văn tiếng Anh);
  - mức sẵn sàng 8 chiều chất lượng;
  - chọn Năm/Quý (Quý chỉ bật khi có số quý; chuỗi minh hoạ vẽ nét đứt);
  - số của Cục từ báo cáo và từ bảng Excel gộp thành một chuỗi (cùng kỳ thì ưu tiên báo cáo);
  - số từ nguồn khác tách sang bảng "Số liệu đối chiếu";
  - nút tải CSV.

## Kế hoạch v2 – GĐ 3: theo quý, bộ 137, đối soát

- **Chuỗi theo kỳ** (`app/timeseries.py`, `app/indicator_ts.py`):
  - mã kỳ năm / quý / tháng;
  - gộp tháng → quý → năm theo quy tắc của chỉ tiêu (tổng, trung bình, kỳ cuối); kỳ cha thiếu kỳ con thì không tính;
  - cửa sổ N kỳ giữ chỗ trống, không nội suy;
  - mức thay đổi MoM / QoQ / YoY, và luỹ kế từ đầu năm cho chỉ tiêu cộng dồn được.
- **Adapter API hệ thống thống kê** (`connectors/api_dinh.py`, bản mô phỏng):
  - đọc 8 chỉ tiêu và 192 số tháng mẫu trong file seed, không cần Internet;
  - khi có đặc tả API thật chỉ cần thay `fetch()`;
  - số liệu gắn nhãn "Dữ liệu minh hoạ".
- **Ánh xạ và đối soát 2244 ↔ 137** (`app/reconcile.py`):
  - sau mỗi lần đồng bộ, tính lại chỉ tiêu 2244 trùng (nguồn `calc:137`) rồi so với số của Cục cùng kỳ;
  - lệch quá 0,5% thì gắn cảnh báo và đưa vào hàng chờ duyệt. Dữ liệu mẫu cho ra đúng 2 kỳ lệch có chủ đích: 0209 quý 4/2025 và năm 2025.
- **Trang mới:**
  - `/s2244`: theo quý hoặc năm, cửa sổ 4/6/8, QoQ / YoY / luỹ kế;
  - `/s137`: tìm kiếm, lọc chỉ tiêu trùng 2244, theo tháng / quý / năm;
  - `/compare`: 2–4 chỉ tiêu, mỗi chỉ tiêu một trục;
  - `/reconcile`: đối soát 2244 ↔ 137, và xác nhận 12 chỉ tiêu lệch giữa bảng Excel và báo cáo (bắt buộc ghi căn cứ).
- **Trang chi tiết chỉ tiêu:** thêm khối "Diễn biến theo kỳ" (độ phân giải, cửa sổ, thẻ thay đổi, bảng so với cùng kỳ năm trước).
- **Menu** sắp xếp lại theo spec: Tổng quan, Chỉ tiêu 2244, Chỉ tiêu thống kê; nhóm Dữ liệu; nhóm Phân tích.
- **API mới:**
  - `GET /api/indicators/{code}/timeseries`;
  - `GET /api/sets/{2244|137}/indicators`;
  - `GET /api/reconciliation`, `POST /api/reconciliation/excel/{code}/confirm`.

## Kế hoạch v2 – GĐ 4: phân tích theo báo cáo

- **Phân tích** (`/analysis`, `app/analysis.py`):
  - 21 biểu đồ dựng lại từ sheet `chart_data`, nhóm theo Đầu vào – Đầu ra – Hiệu quả – Tác động;
  - tiêu đề dạng thông điệp **tính từ số liệu** (ví dụ "Điện tái tạo chiếm 13,1%…"). Cục đổi số thì câu đổi theo; cấu trúc lạ thì dùng tiêu đề gốc;
  - mỗi biểu đồ có dòng nguồn (hình, bảng của báo cáo), chỉ tiêu liên quan, nút "Bảng số liệu" và tải CSV;
  - biểu đồ mới trong `charts.js`: thanh ngang, dot plot, cột (xếp chồng có giá trị âm + điểm tổng), thanh phân đoạn, slope, bong bóng, chuỗi các bước, thẻ số, thẻ xếp hạng;
  - màu theo thứ tự cố định, đã kiểm định cho người mù màu; không dùng biểu đồ hai trục.
- **Đánh giá tổng hợp** (`/scorecard`): 4 chiều, gồm chẩn đoán, mức bằng chứng (thang 4 bậc) và hàm ý chính sách:
  - bản tiếng Việt nằm trong `app/report_vi.py`, khoá theo nguyên văn tiếng Anh;
  - khi nội dung đổi, phần chưa dịch hiển thị nguyên văn kèm nhãn;
  - có nút xem nguyên văn (EN).
- **Sẵn sàng dữ liệu** (`/readiness`):
  - hai thanh trạng thái, dùng chung với trang chủ;
  - heatmap 46 × 8 với 3 mức;
  - sắp xếp theo nhóm hoặc tổng điểm, lọc theo nhóm;
  - bấm vào ô để xem định nghĩa chiều và hạn chế của chỉ tiêu.
- **Địa phương** (`/provinces`):
  - bản đồ lưới ô 34 tỉnh, thành phố, không dùng ranh giới hành chính;
  - mặc định hiển thị tỉnh đã nộp và chưa nộp (18/34);
  - khi chọn chỉ tiêu, ô hiển thị giá trị và **không tô màu theo độ lớn**;
  - bảng giá trị sắp theo tên tỉnh, kèm khối độ phủ;
  - cảnh báo cố định "không dùng để xếp hạng";
  - API không có tham số sắp xếp theo giá trị.
- **API mới:** `GET /api/charts`, `GET /api/charts/{chart_id}`, `GET /api/scorecard`, `GET /api/readiness`, `GET /api/provinces?indicator=`.
- GĐ 4 không đổi cấu trúc CSDL nên không cần chạy `reset_demo`.

## Kế hoạch v2 – GĐ 5: phân quyền và quản trị dữ liệu

- **3 vai trò** (`app/auth.py`):
  - **Công chúng:** không đăng nhập; chỉ thấy chỉ tiêu `public` và số liệu đã công bố;
  - **Chuyên viên phân tích:** thêm khu Nội bộ (Bộ chỉ tiêu, Đánh giá chương trình, Đề xuất tiêu chí, Báo cáo, So sánh), vẫn chỉ thấy số đã công bố;
  - **Quản trị dữ liệu:** toàn quyền.
- **Lọc dữ liệu tại một chỗ:** sự kiện `do_orm_execute` của SQLAlchemy thêm điều kiện vào mọi câu truy vấn `Indicator` / `DataPoint` theo vai trò của request, nên endpoint phụ cũng không lộ dữ liệu. Script, tác vụ nền và Admin không bị lọc.
- **Phiên đăng nhập:**
  - cookie ký HMAC-SHA256 (`hub_session`, HttpOnly, SameSite=Lax), dùng thư viện chuẩn, không thêm phụ thuộc;
  - cookie `hub_ui` chỉ để giao diện hiện đúng menu; máy chủ không dùng cookie này để phân quyền;
  - người duyệt / người sửa lấy từ phiên đăng nhập; tên do trình duyệt gửi lên bị bỏ qua;
  - trang cần quyền chuyển về `/login?next=…`.
- **Cấu hình** (`poc/backend/.env.example`):
  - `SESSION_SECRET`;
  - `ADMIN_PASSWORD` / `ANALYST_PASSWORD` (tài khoản `admin`, `analyst`; để trống = tắt);
  - `DEMO_MODE`. Ở chế độ demo có nút "Xem với vai trò…" để chuyển vai trò không cần mật khẩu. Bản Vercel tự bật khi không có `DATABASE_URL`.
- **Quản trị dữ liệu:**
  - **Nhập dữ liệu → File tổng hợp của Cục:** tải file, kiểm tra cấu trúc, xem trước khác biệt so với bản đang dùng (mới / thay đổi / bỏ, giá trị cũ → mới), rồi bấm Công bố;
  - **Sửa giá trị** (trang chỉ tiêu, nút bút chì khi là Admin): bắt buộc lý do; tạo phiên bản mới, bản cũ giữ trong lịch sử;
  - **Quản trị** (`/admin`): cờ public / internal và trạng thái dữ liệu từng chỉ tiêu; thêm, sửa, xoá ánh xạ 2244 ↔ 137 (tự tính lại); biên tập "Phát hiện chính";
  - **Nhật ký** (`/audit`): gộp thao tác quản trị (`audit_events`) và lịch sử duyệt; lọc theo người, chỉ tiêu, thời gian, loại thao tác; tải CSV.
- **Kiểm thử tiêu chí 3** (`tests/test_auth.py`):
  - quét **mọi** route GET dưới vai trò Công chúng, không lộ mã chỉ tiêu nội bộ, giá trị hay trạng thái chưa công bố;
  - API ghi trả 401 với Công chúng, 403 với Chuyên viên;
  - sửa giá trị thiếu lý do trả 422;
  - kiểm tra đủ các trường lưu vết.
- Bảng mới `audit_events` được tạo tự động khi khởi động, không cần `reset_demo`.
