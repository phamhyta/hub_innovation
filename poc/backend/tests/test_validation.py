import io

from openpyxl import load_workbook

from app import catalog as C
from app import template_spec as T
from app.validation import validate_workbook
from tests.conftest import VALID_HANOI, VALID_NATIONAL, WITH_ERRORS


def test_valid_national_file():
    res = validate_workbook(VALID_NATIONAL.read_bytes())
    assert res.errors == []
    assert len(res.rows) == 7 * 3 + 6 * 3
    assert res.info["name"].startswith("Cục Thông tin, Thống kê")
    r = next(r for r in res.rows if r.breakdown == C.HR_PER_10K and r.period == "2025")
    assert (r.value, r.unit, r.geography) == (8.9, "FTE/10.000 dân", "Toàn quốc")


def test_valid_province_file():
    res = validate_workbook(VALID_HANOI.read_bytes())
    assert res.errors == [] and len(res.rows) == 6
    assert {r.geography for r in res.rows} == {"Hà Nội"}


def test_error_file_reports_each_bad_row():
    res = validate_workbook(WITH_ERRORS.read_bytes())
    assert len(res.error_rows) == 9
    msgs = " | ".join(e.message for e in res.errors)
    for expected in ["Thiếu giá trị", "phải là số", "ngoài khoảng", "không có trong danh mục", "Trùng với dòng 4",
                     "không được âm", "vượt ngưỡng hợp lý", "http://", "Thiếu kỳ báo cáo"]:
        assert expected in msgs, expected
    assert len(res.rows) == 1  # chỉ dòng hợp lệ duy nhất
    assert any("Email" in w.message for w in res.warnings)


def test_changed_header_is_rejected():
    wb = load_workbook(VALID_NATIONAL)
    wb["0101_NhanLuc"]["D3"] = "Số liệu"
    buf = io.BytesIO()
    wb.save(buf)
    res = validate_workbook(buf.getvalue())
    assert any("Tiêu đề cột" in e.message for e in res.errors)


def test_not_an_excel_file():
    res = validate_workbook(b"hello")
    assert res.errors and "Không đọc được file" in res.errors[0].message


def test_component_sum_warning():
    wb = load_workbook(VALID_NATIONAL)
    ws = wb["0102_DauTu"]
    for row in ws.iter_rows(min_row=4):
        if row[1].value == "Toàn quốc" and row[2].value == C.INV_TOTAL and row[0].value == 2025:
            row[3].value = 100_000  # tổng 3 nguồn = 81.500
    buf = io.BytesIO()
    wb.save(buf)
    res = validate_workbook(buf.getvalue())
    assert not res.errors
    assert any("Tổng 3 nguồn chi" in w.message for w in res.warnings)


def test_catalog_names_match_template():
    labels = {b.label for s in T.SHEETS for b in s.breakdowns}
    for name in [C.HR_TOTAL, C.HR_FTE, C.HR_PER_10K, C.HR_PHD, C.HR_FEMALE,
                 C.INV_TOTAL, C.INV_STATE, C.INV_BUSINESS, C.INV_OTHER, C.INV_RD_GDP]:
        assert name in labels
