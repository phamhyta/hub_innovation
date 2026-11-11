# Kế hoạch PoC – Innovation Hub (Số hoá & tự động hoá bộ chỉ tiêu ĐMST)

> Nguồn đầu vào: `Tài liệu mô tả.docx` và `indicator_survey.xlsx` (Dashboard, Indicators_2244, QD3994_BKHCN, Program_Criteria, Legend_Steps).
> Ngày lập: 11/11/2026

---

## 1. Bối cảnh & vấn đề

- Các bộ, ban, ngành đang báo cáo **thủ công**: mỗi đơn vị nộp 1 file Excel/Word, chưa có mẫu (sample) chuẩn.
- Bộ chỉ tiêu cần theo dõi khá lớn: **130 chỉ số** (46 chỉ tiêu QĐ 2244/QĐ-TTg, 34 chỉ tiêu phân công QĐ 3994/BKHCN, 50 tiêu chí đánh giá chương trình KH,CN&ĐMST).
- Theo phân loại trong workbook: 52 chỉ số crawl/ETL được một phần, 51 bán tự động, 63 cần manual/survey; chỉ 22 chỉ số có độ tin cậy cao (A hoặc A/B).
- Mong muốn: chuyển từ **manual → automatic**. Các đơn vị upload số liệu thô, hệ thống tự tính toán và hiển thị dashboard. Ngoài ra hệ thống tự thu thập thêm dữ liệu bên ngoài (nhà khoa học, việc làm, công ty…) để **đề xuất bổ sung tiêu chí** đánh giá ĐMST.

## 2. Mục tiêu PoC

PoC cần chứng minh được **5 điều**, chạy end-to-end trên một tập chỉ số nhỏ nhưng đủ đại diện:

| # | Giả thuyết cần chứng minh | Tiêu chí thành công |
|---|---|---|
| H1 | Có thể chuẩn hoá 130 chỉ số thành một **Indicator Registry** dùng chung | 100% chỉ số trong workbook được import, có mã, nhóm, cơ quan, phương án thu thập, mức tin cậy |
| H2 | Đơn vị có thể **upload file theo mẫu** và hệ thống tự validate, tự tính | Upload mẫu → validate → tính → hiện trên dashboard trong < 5 phút, không cần can thiệp kỹ thuật |
| H3 | Một phần chỉ số có thể **tự động crawl/API** định kỳ | ≥ 6 chỉ số MVP-1 được cập nhật tự động, có nguồn và thời điểm thu thập |
| H4 | Có thể **đánh giá một case/chương trình** theo bộ Program_Criteria | 1 case demo được chấm điểm, có minh chứng gắn kèm từng tiêu chí |
| H5 | Dữ liệu ngoài có thể giúp **đề xuất tiêu chí mới** | ≥ 5 tiêu chí đề xuất có định nghĩa, công thức, nguồn dữ liệu, được chuyên gia đánh giá "hữu ích" |

**Ngoài phạm vi PoC:** tích hợp thật với hệ thống nội bộ của các bộ (NDXP, LGSP), SSO/VNeID, phân quyền đầy đủ cho mọi đơn vị, survey builder hoàn chỉnh, triển khai production/hạ tầng chính phủ.

## 3. Phạm vi chỉ số cho PoC

Chọn **~14 chỉ số** phủ đủ 4 phương án thu thập (Crawl/API, Doc-ETL, Manual/Admin, Survey/Assessment) và đủ 4 mức tin cậy (A–D):

| Mã | Chỉ số | Phương án | Tin cậy | Nguồn đề xuất |
|---|---|---|---|---|
| 0428 | Chỉ số Đổi mới sáng tạo toàn cầu (GII) | Crawl/API | A | WIPO GII country profile |
| 0426 | Chỉ số Phát triển Chính phủ điện tử (EGDI) | Crawl/API | A | UN E-Government Knowledgebase |
| 0429 | Chỉ số Phát triển con người (HDI) | Crawl/API | A | UNDP HDR data |
| 0202 | Số đơn đăng ký sáng chế, GPHI | Crawl | A/B | ipvietnam.gov.vn/so-lieu-thong-ke |
| 0203 | Số bằng độc quyền sáng chế, GPHI | Crawl | A/B | ipvietnam.gov.vn/so-lieu-thong-ke |
| 0201 | Số bài báo KH&CN của Việt Nam | Crawl/API + Doc-ETL | A/B | OpenAlex (miễn phí) để demo; Scopus/WoS nếu có license; đối chiếu mst.gov.vn |
| 0405 | Tỷ trọng xuất khẩu sản phẩm công nghệ cao | Doc-ETL | A/B | Niên giám NSO / Hải quan (PDF/Excel) |
| 0425 | Số chứng thư chữ ký số đã cấp | Doc-ETL | B/C | neac.gov.vn |
| 0101 | Nhân lực KH,CN, ĐMST và CĐS | Manual upload | B/C | Mẫu Excel, Cục Thông tin, Thống kê |
| 0102 | Đầu tư cho KH,CN, ĐMST và CĐS | Manual upload | B/C | Mẫu Excel, Cục TT-TK + Bộ Tài chính |
| SCI-01 / SCI-04 / SCI-06 | Bài báo quốc tế / tỷ lệ hợp tác quốc tế / trích dẫn TB của **1 chương trình** | Crawl/API + mapping | A/B | OpenAlex theo danh sách nhà khoa học/DOI của chương trình |
| TECH-01 | Mức độ sẵn sàng công nghệ (TRL) | Assessment | D | Form chấm theo rubric TRL 1–9 + minh chứng |

> ⚠️ **Lưu ý dữ liệu:** sheet QD3994 ghi GII là mã `0427`, còn QĐ 2244 gốc ghi GII là `0428` và Chỉ số An toàn thông tin mạng toàn cầu (GCI) là `0427`. Cần thống nhất trước khi import registry. PoC dùng mã theo QĐ 2244 làm chuẩn và lưu mã QĐ 3994 dưới dạng alias.

## 4. Kiến trúc đề xuất

```
                  ┌──────────────────────── Nguồn dữ liệu ─────────────────────────┐
                  │ Web/API quốc tế │ Web/PDF chính thức VN │ File đơn vị upload │ Form đánh giá │
                  └───────┬─────────┴──────────┬────────────┴─────────┬──────────┴──────┬────────┘
                          ▼                    ▼                      ▼                 ▼
                    Crawler/API          Doc-ETL (PDF/Excel     Upload + Validate    Assessment
                    connectors           → bảng, LLM hỗ trợ)    theo template        (rubric)
                          └──────────────┬─────┴──────────────────────┴─────────────────┘
                                         ▼
                         Chuẩn hoá → bảng data_points (indicator_code, year, value,
                         unit, geography, source_id, confidence, status)
                                         ▼
                 Review queue: collected → parsed → needs_review → verified/rejected → published
                                         ▼
          Calculation engine (công thức, chuẩn hoá điểm, điểm theo nhóm Đầu vào/Kết quả/Hiệu quả/Tác động)
                                         ▼
          Dashboard │ Indicator detail │ Evidence library │ Case scoring │ Đề xuất tiêu chí mới
                                         ▲
          External enrichment (nhà khoa học, công ty, việc làm, sáng chế) → LLM phân tích → đề xuất tiêu chí
```

### Stack kỹ thuật (đề xuất cho PoC, ưu tiên nhanh)

| Lớp | Công nghệ | Lý do |
|---|---|---|
| Backend / API | Python + FastAPI | Hệ sinh thái crawl/ETL/xử lý dữ liệu mạnh |
| Database | PostgreSQL (+ JSONB cho metadata) | Đủ cho registry, data_points, audit |
| Lưu file minh chứng | MinIO / S3-compatible | File upload, PDF nguồn, snapshot trang crawl |
| Crawl & lịch chạy | httpx + BeautifulSoup / Playwright; APScheduler hoặc Prefect | Crawl định kỳ theo Source Catalog |
| Doc-ETL | pdfplumber / Camelot cho bảng PDF; pandas cho Excel; LLM (Claude API) cho trích xuất bảng khó | Kết hợp rule-based + LLM, luôn qua reviewer |
| Frontend | Next.js + shadcn/ui + Recharts (hoặc Streamlit nếu muốn demo nhanh hơn) | Web cho đơn vị upload + dashboard |
| LLM | Claude API | Trích xuất tài liệu, chấm rubric hỗ trợ, đề xuất tiêu chí |
| Triển khai PoC | Docker Compose trên 1 VM | Đơn giản, dễ chuyển sang on-prem |

### Mô hình dữ liệu tối thiểu

- `indicators` – mã, alias, tên, nhóm, định nghĩa, công thức, đơn vị, tần suất, cơ quan chủ trì/phối hợp, phương án thu thập, mức tin cậy mặc định, ưu tiên MVP, bộ chỉ tiêu (2244 / 3994 / Program).
- `agencies` – bộ/ngành/cục/sở, đầu mối.
- `sources` – URL/API/loại file, parser dùng, lịch chạy, trạng thái được duyệt.
- `submissions` – file upload của đơn vị, kỳ báo cáo, người nộp, trạng thái.
- `data_points` – indicator_code, year/period, value, unit, geography, source_id, submission_id, confidence, status.
- `evidence_files` – file/ảnh chụp/snapshot gắn với data_point hoặc tiêu chí của case.
- `review_logs` – ai duyệt, khi nào, quyết định, ghi chú (audit trail).
- `cases` + `case_scores` – chương trình/nhiệm vụ được đánh giá, điểm từng tiêu chí, minh chứng.
- `external_entities` – nhà khoa học, tổ chức, công ty, tin tuyển dụng, sáng chế thu thập từ ngoài.
- `criteria_suggestions` – tiêu chí đề xuất: tên, định nghĩa, công thức, nguồn, độ khả thi, lý do, trạng thái (proposed / accepted / rejected).

## 5. Các module & phạm vi trong PoC

### M1. Indicator Registry
- Script import tự động 3 sheet trong `indicator_survey.xlsx` → bảng `indicators` (xử lý alias mã, gộp chỉ tiêu trùng giữa 2244 và 3994).
- Trang tra cứu: lọc theo nhóm, cơ quan, phương án thu thập, mức tin cậy, MVP.
- Cho phép admin sửa định nghĩa/công thức/chỉ tiêu mục tiêu.

### M2. Upload & tự tính (trọng tâm "manual → automatic")
- Vì **chưa có file mẫu**, PoC sẽ **tự thiết kế template Excel** cho 0101 và 0102 (mỗi sheet = 1 chỉ tiêu, cột: kỳ, địa bàn, phân tổ, giá trị, đơn vị, ghi chú, link minh chứng), kèm dữ liệu giả lập hợp lý.
- Luồng: đơn vị tải template → điền → upload → hệ thống validate (thiếu cột, sai kiểu, ngoài khoảng, lệch kỳ trước > X%) → báo lỗi theo dòng → lưu data_points → tự tính chỉ số tổng hợp → hiện dashboard.
- Hỗ trợ thêm: upload file "tự do" (Excel/Word/PDF không theo mẫu) → LLM đề xuất mapping cột/giá trị vào chỉ tiêu → người dùng xác nhận. Đây là điểm thể hiện giá trị lớn nhất trong lúc chưa có mẫu chuẩn.

### M3. Crawler & Doc-ETL
- Connector cho: WIPO GII, UN EGDI, UNDP HDI, IP Vietnam (sáng chế), OpenAlex (công bố), NSO niên giám (PDF/Excel), NEAC (chữ ký số).
- Mỗi lần chạy lưu snapshot nguồn (HTML/PDF) làm minh chứng, ghi timestamp, hash để phát hiện thay đổi.
- Nguồn A → auto-publish sau validation nhẹ; nguồn B/C → vào review queue.

### M4. Review & kiểm soát chất lượng
- Hàng đợi duyệt theo trạng thái `collected → parsed → needs_review → verified/rejected → published`.
- Hiển thị cạnh nhau: giá trị trích xuất ↔ đoạn tài liệu/ảnh nguồn.
- Audit trail đầy đủ.

### M5. Dashboard
- Tổng quan: số chỉ tiêu đã có dữ liệu / tổng, theo mức tin cậy, theo cơ quan (đơn vị nào đã nộp, chậm hạn).
- Indicator matrix: 4 nhóm (Đầu vào – Kết quả – Hiệu quả – Tác động) × năm.
- Trang chi tiết chỉ tiêu: chuỗi thời gian, so với mục tiêu, nguồn, mức tin cậy, lịch sử xác nhận.
- Xếp hạng quốc tế: GII, EGDI, HDI qua các năm.
- Export báo cáo (Excel/PDF) theo kỳ.

### M6. Đánh giá case/chương trình
- Chọn 1 chương trình/nhiệm vụ KH&CN thật hoặc giả lập (danh sách nhà khoa học, DOI, sáng chế, sản phẩm).
- Tự tính SCI-01/04/06 từ OpenAlex, TECH-02/07 từ dữ liệu sáng chế; TECH-01 chấm theo rubric TRL, LLM gợi ý mức TRL dựa trên tài liệu nghiệm thu, người đánh giá chốt.
- Kết quả: scorecard của case + điểm mạnh/yếu + minh chứng từng tiêu chí → trả lời câu hỏi "case này có thể hiện innovation tốt không".

### M7. Thu thập dữ liệu ngoài & đề xuất tiêu chí mới
- Nguồn thử nghiệm (ưu tiên nguồn mở, có API, không vi phạm điều khoản):
  - **Nhà khoa học / tổ chức:** OpenAlex (tác giả, h-index, lĩnh vực, hợp tác quốc tế của tổ chức VN).
  - **Sáng chế:** WIPO PATENTSCOPE / Google Patents (đơn có người nộp/tác giả VN).
  - **Công ty / startup:** dữ liệu công khai (danh sách DN KH&CN, startup được hỗ trợ, tin gọi vốn).
  - **Việc làm:** mẫu nhỏ tin tuyển dụng R&D/AI/bán dẫn từ nguồn cho phép (hoặc dataset mở) để đo nhu cầu nhân lực ĐMST.
- Pipeline: thu thập → chuẩn hoá thực thể → so sánh với registry hiện có (tìm "khoảng trống" chưa được đo) → LLM đề xuất tiêu chí mới.
- Mỗi tiêu chí đề xuất gồm: tên, định nghĩa, công thức, đơn vị, nguồn dữ liệu, tần suất, mức tin cậy dự kiến, nhóm (Đầu vào/Kết quả/…), lý do, ví dụ giá trị tính thử.
- Ví dụ tiêu chí có thể nảy ra: số nhà khoa học VN có h-index ≥ 20; tỷ lệ công bố có đồng tác giả doanh nghiệp; số tin tuyển dụng vị trí R&D/AI trên 10.000 lao động; số startup công nghệ gọi vốn được trong năm; số sáng chế PCT có người nộp VN.
- Chuyên gia duyệt → tiêu chí được chấp nhận vào registry với trạng thái `proposed`.

## 6. Lộ trình (8 tuần, 4 sprint × 2 tuần)

| Sprint | Thời gian | Hạng mục | Kết quả bàn giao |
|---|---|---|---|
| **S0 – Chuẩn bị** | Tuần 0 (song song) | Chốt phạm vi 14 chỉ số, xử lý xung đột mã, chọn case demo, xác nhận nguồn được phép crawl, xin quyền Scopus/WoS (nếu có) | Danh sách chỉ số & nguồn đã duyệt |
| **S1 – Nền tảng** | Tuần 1–2 | Dựng hạ tầng (Docker, DB, storage), schema, import registry 130 chỉ số, thiết kế template Excel + dữ liệu giả lập | Registry tra cứu được; template mẫu |
| **S2 – Thu thập** | Tuần 3–4 | Upload + validate + tính cho 0101/0102; connector GII/EGDI/HDI/IP Vietnam/OpenAlex; Doc-ETL cho 0405/0425; review queue | ≥ 10 chỉ số có dữ liệu thật/giả lập trong DB |
| **S3 – Hiển thị & đánh giá** | Tuần 5–6 | Dashboard, trang chi tiết, export báo cáo; module case scoring (SCI, TECH, TRL rubric); upload file tự do + LLM mapping | Dashboard chạy end-to-end; scorecard 1 case |
| **S4 – Mở rộng & demo** | Tuần 7–8 | External enrichment (OpenAlex, sáng chế, công ty, việc làm); LLM đề xuất tiêu chí; kiểm thử với 2–3 người dùng thật; tài liệu & demo | Danh sách ≥ 5 tiêu chí đề xuất; buổi demo; báo cáo đánh giá PoC |

## 7. Kịch bản demo (cuối PoC)

1. Admin mở **Registry**: 130 chỉ số, lọc chỉ số MVP-1 có thể tự động.
2. Cán bộ một đơn vị **tải template**, điền số liệu 0101/0102, upload → hệ thống báo 2 dòng lỗi → sửa → nộp thành công.
3. Dashboard **tự cập nhật** điểm nhóm "Đầu vào".
4. Bấm **"Chạy crawler"**: GII, EGDI, HDI, số đơn sáng chế được cập nhật, có link nguồn và ảnh snapshot.
5. Upload một **PDF niên giám** → hệ thống trích bảng xuất khẩu công nghệ cao → reviewer xác nhận → published.
6. Mở **case "Chương trình X"** → scorecard Khoa học/Công nghệ/TRL kèm minh chứng → kết luận mức innovation.
7. Mở **"Đề xuất tiêu chí"** → hệ thống trình bày 5+ tiêu chí mới từ dữ liệu ngoài, có số liệu tính thử → chuyên gia chấp nhận 1 tiêu chí → tiêu chí xuất hiện trong registry.

## 8. Nhân sự đề xuất

| Vai trò | Số lượng | Ghi chú |
|---|---|---|
| Product owner / chuyên gia nghiệp vụ KH&CN | 1 (part-time) | Chốt định nghĩa, công thức, rubric, duyệt tiêu chí đề xuất |
| Tech lead / backend + data engineer | 1 | Schema, pipeline, crawler, ETL |
| Fullstack / frontend | 1 | Upload, review, dashboard |
| AI/LLM engineer | 0.5 | Doc-ETL bằng LLM, mapping file tự do, đề xuất tiêu chí |
| Người dùng thử (đại diện đơn vị) | 2–3 | Thử luồng upload ở S4 |

## 9. Rủi ro & cách giảm thiểu

| Rủi ro | Ảnh hưởng | Giảm thiểu |
|---|---|---|
| Chưa có file mẫu thực tế từ các bộ | Template có thể không khớp thực tế | Tự thiết kế template + module LLM mapping file tự do; xin 1–2 file thật (ẩn danh) càng sớm càng tốt |
| Nguồn web thay đổi cấu trúc / chặn crawl | Crawler hỏng | Lưu snapshot, cảnh báo khi parse lỗi, fallback upload thủ công; ưu tiên API chính thức |
| Scopus/WoS cần license | Không lấy được số bài báo chuẩn | Dùng OpenAlex cho PoC, ghi rõ chênh lệch phương pháp |
| Điều khoản sử dụng khi crawl (việc làm, công ty) | Rủi ro pháp lý | Chỉ dùng nguồn mở/API cho phép, mẫu nhỏ, tôn trọng robots.txt |
| Dữ liệu cá nhân nhà khoa học | Tuân thủ NĐ 13/2023 về bảo vệ dữ liệu cá nhân | Chỉ dùng thông tin công khai học thuật, tổng hợp ở mức thống kê trên dashboard |
| LLM trích xuất sai số liệu | Sai số liệu báo cáo | Không auto-publish dữ liệu do LLM trích xuất; bắt buộc qua reviewer, hiển thị nguồn đối chiếu |
| Xung đột mã chỉ tiêu giữa các văn bản | Gộp sai dữ liệu | Registry có bảng alias, mã QĐ 2244 làm chuẩn |
| Dữ liệu nhà nước nhạy cảm, yêu cầu hạ tầng trong nước | Không dùng được cloud nước ngoài | Thiết kế để chạy on-prem; với LLM, chỉ gửi dữ liệu công khai hoặc dùng mô hình triển khai nội bộ khi lên production |

## 10. Câu hỏi cần chốt trước khi bắt đầu

1. Ai là người dùng chính của PoC (Bộ KH&CN / Cục Thông tin, Thống kê / đơn vị khác)?
2. Có thể xin 1–2 file báo cáo thực tế (đã ẩn danh) từ một đơn vị không?
3. Có giá trị **mục tiêu** (target) cho từng chỉ tiêu theo QĐ 2244 để dashboard so sánh không?
4. Case/chương trình nào dùng để demo module đánh giá?
5. Có quyền truy cập Scopus / Web of Science không?
6. Yêu cầu hạ tầng: có được dùng cloud / LLM API bên ngoài trong giai đoạn PoC không?
7. Tiêu chí đề xuất mới ưu tiên lĩnh vực nào (nhân lực, doanh nghiệp, sáng chế, AI/bán dẫn…)?

## 11. Bước tiếp theo sau PoC (định hướng MVP)

- Mở rộng lần lượt theo nhóm MVP-1 (25 chỉ số) → MVP-2 (42) → MVP-3 (63) như phân loại trong workbook.
- Phân quyền theo đơn vị chủ trì/phối hợp (QĐ 3994), deadline và nhắc hạn nộp.
- Survey builder cho nhóm chỉ số mức D.
- Tích hợp hệ thống nội bộ (cổng dịch vụ công, NDXP) và SSO.
- Chuyển sang hạ tầng đáp ứng yêu cầu an toàn thông tin cấp độ phù hợp.
