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
uv run python -m scripts.reset_demo --yes
uv run uvicorn app.main:app --port 8000
```

Hoặc từng bước:

```bash
cd poc/backend
uv run python -m scripts.import_registry      # tạo bảng + import registry
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
