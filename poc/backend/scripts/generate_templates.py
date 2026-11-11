"""Sinh template Excel nộp số liệu (0101 + 0102) và các file dữ liệu GIẢ LẬP.

    uv run python -m scripts.generate_templates

Kết quả:
- poc/templates/TPL-0101-0102_v0.1.xlsx       : file mẫu trống cho đơn vị điền
- poc/sample_data/*_GIA_LAP.xlsx                : file đã điền số liệu giả lập (hợp lệ)
- poc/sample_data/*_CO_LOI.xlsx                 : file cố tình có lỗi để demo validate (Sprint 2)
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter, quote_sheetname
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation

from app import template_spec as T
from app.config import POC_DIR, settings

HEADER_ROW = 3
FIRST_DATA_ROW = 4
DATA_ROWS = 300  # số dòng được gắn validation sẵn

BLUE = PatternFill("solid", fgColor="1F5FBF")
LIGHT = PatternFill("solid", fgColor="E8F0FC")
REQ = PatternFill("solid", fgColor="FFF4E5")
THIN = Border(*(Side(style="thin", color="C9CED6"),) * 4)


def _danh_muc(wb: Workbook) -> None:
    ws = wb.create_sheet("DanhMuc")
    lists = {"DiaBan": [(p, "") for p in T.PROVINCES]}
    for sheet in T.SHEETS:
        lists[f"PhanTo_{sheet.indicator_code}"] = [(b.label, b.unit) for b in sheet.breakdowns]
    col = 1
    for name, items in lists.items():
        ws.cell(1, col, name).font = Font(bold=True)
        ws.cell(1, col + 1, "Đơn vị").font = Font(bold=True)
        for i, (label, unit) in enumerate(items, start=2):
            ws.cell(i, col, label)
            ws.cell(i, col + 1, unit)
        letter = get_column_letter(col)
        ref = f"{quote_sheetname(ws.title)}!${letter}$2:${letter}${len(items) + 1}"
        wb.defined_names[name] = DefinedName(name, attr_text=ref)
        unit_ref = f"{quote_sheetname(ws.title)}!${letter}$2:${get_column_letter(col + 1)}${len(items) + 1}"
        wb.defined_names[f"{name}_DonVi"] = DefinedName(f"{name}_DonVi", attr_text=unit_ref)
        ws.column_dimensions[letter].width = 55
        col += 3
    ws.sheet_state = "hidden"


def _meta(wb: Workbook) -> None:
    ws = wb.create_sheet("_meta")
    rows = [
        ("template_code", T.TEMPLATE_CODE),
        ("template_version", T.TEMPLATE_VERSION),
        ("generated_at", date.today().isoformat()),
        ("header_row", HEADER_ROW),
        ("first_data_row", FIRST_DATA_ROW),
    ] + [(f"sheet:{s.sheet_name}", s.indicator_code) for s in T.SHEETS]
    for r in rows:
        ws.append(r)
    ws.sheet_state = "hidden"


def _huong_dan(ws) -> None:
    ws.title = "HuongDan"
    ws["A1"] = T.TEMPLATE_TITLE
    ws["A1"].font = Font(bold=True, size=14)
    ws["A2"] = f"Mã mẫu: {T.TEMPLATE_CODE} · Phiên bản {T.TEMPLATE_VERSION} · KHÔNG đổi tên sheet, không xoá/chèn cột."
    ws["A2"].font = Font(italic=True, color="5D6673")

    ws["A4"] = "THÔNG TIN ĐƠN VỊ NỘP"
    ws["A4"].font = Font(bold=True)
    for i, label in enumerate(["Tên đơn vị", "Người lập biểu", "Email liên hệ", "Số điện thoại", "Ngày lập"], start=5):
        ws.cell(i, 1, label).font = Font(bold=True)
        c = ws.cell(i, 2)
        c.fill, c.border = REQ, THIN

    steps = [
        "HƯỚNG DẪN",
        "1. Điền thông tin đơn vị ở trên (ô màu cam).",
        "2. Mở từng sheet chỉ tiêu (0101_NhanLuc, 0102_DauTu). Mỗi dòng = 1 giá trị của 1 phân tổ, 1 năm, 1 địa bàn.",
        "3. Cột 'Địa bàn' và 'Phân tổ' chọn từ danh sách thả xuống. Cột 'Đơn vị' tự điền theo phân tổ.",
        "4. Cột 'Giá trị' chỉ nhập số (dấu thập phân theo cài đặt Excel), không nhập chữ hay đơn vị.",
        "5. Không có số liệu thì để trống dòng — KHÔNG nhập 0 nếu thực tế là chưa thu thập được.",
        "6. Nếu có, ghi nguồn/phương pháp và link minh chứng để rút ngắn thời gian thẩm định.",
        "7. Lưu file .xlsx và tải lên Innovation Hub. Hệ thống sẽ kiểm tra và báo lỗi theo từng dòng.",
        "",
        "Lưu ý: danh sách phân tổ hiện là đề xuất của nhóm PoC, sẽ được điều chỉnh theo hướng dẫn chính thức của QĐ 2244.",
    ]
    for i, s in enumerate(steps, start=12):
        ws.cell(i, 1, s).font = Font(bold=(i == 12))
    ws.column_dimensions["A"].width = 24
    ws.column_dimensions["B"].width = 60


def _indicator_sheet(wb: Workbook, spec: T.IndicatorSheet) -> None:
    ws = wb.create_sheet(spec.sheet_name)
    ncol = len(spec.columns)
    ws.cell(1, 1, spec.title).font = Font(bold=True, size=13)
    ws.cell(2, 1, "Ô tiêu đề màu xanh đậm = bắt buộc. Di chuột vào tiêu đề cột để xem hướng dẫn.").font = Font(
        italic=True, color="5D6673"
    )
    for j, col in enumerate(spec.columns, start=1):
        c = ws.cell(HEADER_ROW, j, col.header + (" *" if col.required else ""))
        c.font = Font(bold=True, color="FFFFFF" if col.required else "1B1F24")
        c.fill = BLUE if col.required else LIGHT
        c.alignment = Alignment(wrap_text=True, vertical="center")
        c.border = THIN
        if col.help:
            c.comment = Comment(col.help, "Innovation Hub")
        ws.column_dimensions[get_column_letter(j)].width = col.width
    ws.row_dimensions[HEADER_ROW].height = 32
    ws.freeze_panes = ws.cell(FIRST_DATA_ROW, 1)

    last = FIRST_DATA_ROW + DATA_ROWS - 1
    keys = [c.key for c in spec.columns]

    def rng(key):
        letter = get_column_letter(keys.index(key) + 1)
        return f"{letter}{FIRST_DATA_ROW}:{letter}{last}"

    dvs = [
        DataValidation(type="whole", operator="between", formula1="2015", formula2="2035",
                       errorTitle="Kỳ báo cáo", error="Nhập năm từ 2015 đến 2035", showErrorMessage=True),
        DataValidation(type="list", formula1="DiaBan", showErrorMessage=True,
                       errorTitle="Địa bàn", error="Chọn từ danh sách"),
        DataValidation(type="list", formula1=f"PhanTo_{spec.indicator_code}", showErrorMessage=True,
                       errorTitle="Phân tổ", error="Chọn từ danh sách phân tổ"),
        DataValidation(type="decimal", operator="greaterThanOrEqual", formula1="0", showErrorMessage=True,
                       errorTitle="Giá trị", error="Chỉ nhập số ≥ 0"),
    ]
    for dv, key in zip(dvs, ["period", "geography", "breakdown", "value"]):
        ws.add_data_validation(dv)
        dv.add(rng(key))

    b_letter = get_column_letter(keys.index("breakdown") + 1)
    u_col = keys.index("unit") + 1
    for r in range(FIRST_DATA_ROW, last + 1):
        ws.cell(r, u_col, f'=IFERROR(VLOOKUP({b_letter}{r},PhanTo_{spec.indicator_code}_DonVi,2,FALSE),"")')
        for j in range(1, ncol + 1):
            ws.cell(r, j).border = THIN


def build_template(path: Path) -> Path:
    wb = Workbook()
    _huong_dan(wb.active)
    for spec in T.SHEETS:
        _indicator_sheet(wb, spec)
    _danh_muc(wb)
    _meta(wb)
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return path


# ---------------------------------------------------------------- dữ liệu giả lập
def _unit(code: str, label: str) -> str:
    spec = next(s for s in T.SHEETS if s.indicator_code == code)
    return next((b.unit for b in spec.breakdowns if b.label == label), "")


def fill(template: Path, out: Path, info: dict, rows: dict[str, list[tuple]]) -> Path:
    """rows: {sheet_name: [(period, geography, breakdown, value, source_note, evidence_url, note), ...]}"""
    wb = load_workbook(template)
    hd = wb["HuongDan"]
    for i, key in enumerate(["name", "preparer", "email", "phone", "date"], start=5):
        hd.cell(i, 2, info.get(key))
    for spec in T.SHEETS:
        ws = wb[spec.sheet_name]
        for r, row in enumerate(rows.get(spec.sheet_name, []), start=FIRST_DATA_ROW):
            period, geo, breakdown, value, *rest = row
            values = [period, geo, breakdown, value, _unit(spec.indicator_code, breakdown), *rest]
            for j, v in enumerate(values, start=1):
                ws.cell(r, j, v)
    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)
    return out


NATIONAL_0101 = {
    # breakdown: (2023, 2024, 2025) – SỐ LIỆU GIẢ LẬP
    "Tổng số nhân lực nghiên cứu và phát triển (R&D)": (172_000, 181_500, 194_300),
    "Nhân lực R&D quy đổi toàn thời gian (FTE)": (78_400, 83_100, 90_200),
    "Số nhà nghiên cứu quy đổi toàn thời gian trên 1 vạn dân": (7.9, 8.3, 8.9),
    "Nhân lực nghiên cứu có trình độ tiến sĩ": (29_800, 31_900, 34_600),
    "Nhân lực nghiên cứu là nữ": (78_100, 83_200, 89_900),
    "Nhân lực làm việc trong doanh nghiệp công nghệ số": (1_550_000, 1_640_000, 1_780_000),
    "Nhân lực chuyển đổi số trong khu vực công": (52_000, 58_500, 67_000),
}
NATIONAL_0102 = {
    "Tổng chi cho KH,CN, ĐMST và CĐS": (54_200, 62_800, 81_500),
    "Chi từ ngân sách nhà nước": (19_300, 22_600, 33_400),
    "Chi từ khu vực doanh nghiệp": (29_700, 34_500, 41_200),
    "Chi từ nguồn khác (quỹ, nước ngoài, xã hội hóa)": (5_200, 5_700, 6_900),
    "Tổng chi cho R&D so với GDP": (0.43, 0.46, 0.52),
    "Tỷ trọng chi ngân sách cho KH,CN, ĐMST và CĐS trên tổng chi NSNN": (1.1, 1.2, 2.0),
}
YEARS = (2023, 2024, 2025)
NOTE = "SỐ LIỆU GIẢ LẬP – chỉ dùng cho PoC"


def _national_rows(table: dict, src: str, url: str) -> list[tuple]:
    return [
        (year, "Toàn quốc", label, values[i], src, url, NOTE)
        for i, year in enumerate(YEARS)
        for label, values in table.items()
    ]


def main() -> None:
    template = build_template(settings.templates_dir / T.TEMPLATE_FILE)
    print(f"Template: {template}")
    samples = POC_DIR / "sample_data"

    f1 = fill(
        template,
        samples / "TPL-0101-0102_CucThongTinThongKe_2023-2025_GIA_LAP.xlsx",
        {"name": "Cục Thông tin, Thống kê (giả lập)", "preparer": "Nguyễn Văn A (giả lập)",
         "email": "demo@example.com", "phone": "0000000000", "date": "2026-01-15"},
        {
            "0101_NhanLuc": _national_rows(NATIONAL_0101, "Điều tra nghiên cứu và phát triển (giả lập)",
                                           "https://mst.gov.vn/so-lieu-thong-ke/khoa-hoc-va-cong-nghe.htm"),
            "0102_DauTu": _national_rows(NATIONAL_0102, "Tổng hợp báo cáo chi KH&CN (giả lập)", None),
        },
    )
    print(f"Mẫu hợp lệ (toàn quốc): {f1}")

    f2 = fill(
        template,
        samples / "TPL-0101-0102_SoKHCN_HaNoi_2025_GIA_LAP.xlsx",
        {"name": "Sở KH&CN Hà Nội (giả lập)", "preparer": "Trần Thị B (giả lập)",
         "email": "demo@example.com", "phone": "0000000000", "date": "2026-01-20"},
        {
            "0101_NhanLuc": [
                (2025, "Hà Nội", "Tổng số nhân lực nghiên cứu và phát triển (R&D)", 71_200, "Báo cáo Sở (giả lập)", None, NOTE),
                (2025, "Hà Nội", "Nhân lực R&D quy đổi toàn thời gian (FTE)", 33_800, "Báo cáo Sở (giả lập)", None, NOTE),
                (2025, "Hà Nội", "Nhân lực nghiên cứu có trình độ tiến sĩ", 15_100, "Báo cáo Sở (giả lập)", None, NOTE),
            ],
            "0102_DauTu": [
                (2025, "Hà Nội", "Tổng chi cho KH,CN, ĐMST và CĐS", 12_400, "Báo cáo Sở (giả lập)", None, NOTE),
                (2025, "Hà Nội", "Chi từ ngân sách nhà nước", 4_900, "Báo cáo Sở (giả lập)", None, NOTE),
                (2025, "Hà Nội", "Chi từ khu vực doanh nghiệp", 6_700, "Báo cáo Sở (giả lập)", None, NOTE),
            ],
        },
    )
    print(f"Mẫu hợp lệ (cấp tỉnh): {f2}")

    # File cố tình sai – mỗi dòng ghi chú lỗi mong đợi để Sprint 2 kiểm thử validator
    f3 = fill(
        template,
        samples / "TPL-0101-0102_DonViX_2025_CO_LOI.xlsx",
        {"name": "Đơn vị X (giả lập)", "preparer": None, "email": "khong-phai-email", "date": "2026-01-25"},
        {
            "0101_NhanLuc": [
                (2025, "Toàn quốc", "Tổng số nhân lực nghiên cứu và phát triển (R&D)", 190_000, None, None, "HỢP LỆ"),
                (2025, "Toàn quốc", "Nhân lực R&D quy đổi toàn thời gian (FTE)", None, None, None, "LỖI: thiếu giá trị"),
                (2025, "Toàn quốc", "Nhân lực nghiên cứu có trình độ tiến sĩ", "khoảng 30 nghìn", None, None, "LỖI: giá trị là chữ"),
                (2050, "Toàn quốc", "Nhân lực nghiên cứu là nữ", 80_000, None, None, "LỖI: năm ngoài khoảng"),
                (2025, "Toàn quốc", "Số kỹ sư AI", 5_000, None, None, "LỖI: phân tổ không có trong danh mục"),
                (2025, "Toàn quốc", "Tổng số nhân lực nghiên cứu và phát triển (R&D)", 191_000, None, None, "LỖI: trùng dòng 1 (cùng năm/địa bàn/phân tổ)"),
            ],
            "0102_DauTu": [
                (2025, "Toàn quốc", "Chi từ ngân sách nhà nước", -500, None, None, "LỖI: giá trị âm"),
                (2025, "Toàn quốc", "Tổng chi cho R&D so với GDP", 52, None, None, "LỖI: % > ngưỡng hợp lý (nhầm 0.52)"),
                (2025, "Đà Nẵng", "Chi từ khu vực doanh nghiệp", 1_200, None, "not-a-url", "LỖI: link minh chứng sai định dạng"),
                (None, "Toàn quốc", "Tổng chi cho KH,CN, ĐMST và CĐS", 80_000, None, None, "LỖI: thiếu kỳ báo cáo"),
            ],
        },
    )
    print(f"Mẫu có lỗi (demo validate): {f3}")


if __name__ == "__main__":
    main()
