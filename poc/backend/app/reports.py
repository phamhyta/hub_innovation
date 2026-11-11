"""Xuất báo cáo Excel từ dữ liệu ĐÃ CÔNG BỐ."""

from __future__ import annotations

import io
from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from sqlalchemy.orm import Session

from app.analytics import PILLAR_LABEL, detail_rows, headlines, origin_label

HEAD = PatternFill("solid", fgColor="1F5FBF")
YEARS_IN_REPORT = 5


def _header(ws, row: int, values: list[str], widths: list[int]) -> None:
    for j, (v, w) in enumerate(zip(values, widths), start=1):
        c = ws.cell(row, j, v)
        c.font, c.fill = Font(bold=True, color="FFFFFF"), HEAD
        c.alignment = Alignment(wrap_text=True, vertical="center")
        ws.column_dimensions[get_column_letter(j)].width = w
    ws.freeze_panes = ws.cell(row + 1, 1)


def build_report(session: Session, year: int) -> bytes:
    years = [str(y) for y in range(year - YEARS_IN_REPORT + 1, year + 1)]
    wb = Workbook()

    # 1) Tổng hợp: mỗi chỉ tiêu QĐ 2244 có dữ liệu = 1 dòng giá trị tiêu biểu theo năm
    ws = wb.active
    ws.title = "TongHop"
    ws["A1"] = f"BÁO CÁO CHỈ TIÊU KH,CN, ĐMST & CĐS (QĐ 2244) – năm {year}"
    ws["A1"].font = Font(bold=True, size=13)
    ws["A2"] = (f"Xuất lúc {datetime.now():%d/%m/%Y %H:%M} từ Innovation Hub (PoC). Chỉ gồm số liệu ĐÃ CÔNG BỐ. "
                "Ô trống = chưa có số liệu được duyệt.")
    ws["A2"].font = Font(italic=True, color="5D6673")
    cols = ["Mã", "Chỉ tiêu", "Trụ cột", "Giá trị tiêu biểu (phân tổ)", "Đơn vị", *years,
            "Mục tiêu", "Năm MT", "Nguồn năm gần nhất", "Tin cậy"]
    _header(ws, 4, cols, [8, 48, 11, 40, 14, *[12] * len(years), 11, 9, 34, 8])
    r = 5
    for h in headlines(session):
        ind = h.indicator
        latest = list(h.series.values())[-1]
        row = [ind.code, ind.name, PILLAR_LABEL.get(ind.pillar, ""), h.breakdown, latest.unit,
               *[h.series[y].value if y in h.series else None for y in years],
               ind.target_value, ind.target_year, origin_label(latest.origin), latest.confidence]
        for j, v in enumerate(row, start=1):
            c = ws.cell(r, j, v)
            if isinstance(v, float):
                c.number_format = "#,##0.####"
        r += 1
    if r == 5:
        ws.cell(5, 1, "Chưa có chỉ tiêu nào có số liệu được công bố.")

    # 2) Chi tiết: mọi điểm dữ liệu đã công bố (mọi phân tổ, địa bàn, nguồn)
    ws2 = wb.create_sheet("ChiTiet")
    _header(ws2, 1, ["Mã", "Chỉ tiêu", "Kỳ", "Địa bàn", "Phân tổ", "Giá trị", "Đơn vị", "Nguồn gốc", "Tin cậy",
                     "Cách thu thập", "Đoạn trích nguồn", "Link nguồn"],
            [8, 40, 8, 18, 42, 14, 14, 34, 8, 12, 60, 50])
    for i, p in enumerate(detail_rows(session), start=2):
        vals = [p.indicator.code, p.indicator.name, p.period, p.geography, p.breakdown, p.value, p.unit,
                origin_label(p.origin), p.confidence, p.extracted_by, p.excerpt,
                (p.meta or {}).get("doc_url") or (p.meta or {}).get("evidence_url") or (p.source.url if p.source else None)]
        for j, v in enumerate(vals, start=1):
            ws2.cell(i, j, v)

    # 3) Giải thích
    ws3 = wb.create_sheet("GiaiThich")
    notes = [
        "Quy tắc chọn giá trị tiêu biểu khi nhiều nguồn: đơn vị chủ trì báo cáo > nguồn công khai/quốc tế > trích từ tài liệu > tự tính.",
        "Mức tin cậy: A nguồn chuẩn quốc tế/chính thức; B chính thức cần ETL; C dữ liệu hành chính; D khảo sát/đánh giá.",
        "Thứ hạng: số càng nhỏ càng tốt.",
        "OpenAlex (0201) là nguồn thay thế cho Scopus/WoS; World Bank 0405 là proxy (mẫu số là hàng chế tạo).",
        "Số liệu của đơn vị trong PoC là GIẢ LẬP.",
    ]
    ws3.column_dimensions["A"].width = 120
    for i, n in enumerate(notes, start=1):
        ws3.cell(i, 1, n)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
