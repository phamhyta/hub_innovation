# Dữ liệu chuẩn cho PoC (file seed)

| | |
|---|---|
| Tệp | `seed_data_2244.xlsx` |
| Nguồn | Repo `GriffithBigDataVisualizationLab/CSIRO-2244-Documents`, thư mục `data/` (bản ngày 12/11/2026) |
| Dựng bởi | `scripts/build_seed_data.py` trong repo trên, từ báo cáo 2244 (bản 15/09), bảng kết quả 2244 (bản 01/09/2026) và `indicator_survey.xlsx` |

## Quy ước (theo sheet README trong tệp)

- Số năm (`period_type = Y`) là **số thật**. Ưu tiên số trong báo cáo 15/09. Chênh lệch với file Excel 01/09 ghi ở sheet `reconciliation`, chờ Cục xác nhận.
- Số quý (`fact_sim_quarterly`) là **số giả lập** (`is_simulated = 1`). Giao diện bắt buộc gắn nhãn "Dữ liệu minh hoạ".
- Số liệu tỉnh (`fact_province`) do tỉnh tự báo cáo, chưa kiểm chứng. **Không dùng để xếp hạng.**
- Bộ 137 (`mock_137_*`) và bảng ánh xạ `mapping_2244_137` là dữ liệu mẫu.

## Nhập vào hệ thống

```bash
cd poc/backend
uv run python -m scripts.import_seed --dry-run   # xem số dòng mới / thay đổi / bỏ, không ghi
uv run python -m scripts.import_seed             # nhập (chạy lại an toàn)
```

Khi Cục gửi bản mới, thay tệp này (giữ nguyên cấu trúc sheet và cột) rồi chạy lại lệnh nhập.
