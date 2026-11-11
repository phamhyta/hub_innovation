"""Kiểm tra file Excel nộp theo template (dùng chung định nghĩa trong template_spec).

- Lỗi (error): chặn import toàn bộ file, báo theo từng dòng/cột để đơn vị sửa.
- Cảnh báo (warning): vẫn import nhưng gắn cờ cho người duyệt (vd. biến động bất thường).
"""

from __future__ import annotations

import io
import re
from dataclasses import asdict, dataclass, field
from urllib.parse import urlparse

from openpyxl import load_workbook
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import catalog as C
from app import template_spec as T
from app.models import DataPoint, DataStatus, Indicator

HEADER_ROW = 3
FIRST_DATA_ROW = 4
INFO_FIELDS = {5: "name", 6: "preparer", 7: "email", 8: "phone", 9: "date"}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

YOY_WARN = 0.5  # biến động > 50% so với kỳ trước
CROSS_WARN = 0.25  # lệch > 25% so với nguồn độc lập
SUM_WARN = 0.02  # tổng thành phần lệch > 2% so với tổng


@dataclass
class Issue:
    level: str  # error | warning
    message: str
    sheet: str | None = None
    row: int | None = None
    column: str | None = None
    value: str | None = None


@dataclass
class ParsedRow:
    sheet: str
    row: int
    indicator_code: str
    period: str
    geography: str
    breakdown: str
    value: float
    unit: str
    source_note: str | None
    evidence_url: str | None
    note: str | None
    warnings: list[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    template_code: str | None = None
    template_version: str | None = None
    info: dict = field(default_factory=dict)
    rows: list[ParsedRow] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.level == "error"]

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.level == "warning"]

    @property
    def error_rows(self) -> set[tuple[str, int]]:
        return {(i.sheet, i.row) for i in self.errors if i.row}

    def issues_as_dicts(self, level: str) -> list[dict]:
        return [asdict(i) for i in self.issues if i.level == level]


def _blank(v) -> bool:
    return v is None or (isinstance(v, str) and not v.strip())


def _num(v) -> float | None:
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.strip().replace(" ", "")
        if re.fullmatch(r"-?\d+(\.\d+)?", s):
            return float(s)
        if re.fullmatch(r"-?\d+,\d+", s):  # dấu phẩy thập phân kiểu VN
            return float(s.replace(",", "."))
    return None


def _str(v) -> str | None:
    return None if _blank(v) else str(v).strip()


def validate_workbook(data: bytes) -> ValidationResult:
    res = ValidationResult()
    try:
        wb = load_workbook(io.BytesIO(data), data_only=True)
    except Exception:  # noqa: BLE001 – file hỏng/không phải xlsx
        res.issues.append(Issue("error", "Không đọc được file. Hãy lưu lại dưới dạng Excel .xlsx"))
        return res

    # 1) nhận diện template
    if "_meta" in wb.sheetnames:
        meta = {r[0]: r[1] for r in wb["_meta"].iter_rows(values_only=True) if r and r[0]}
        res.template_code, res.template_version = meta.get("template_code"), str(meta.get("template_version"))
    if res.template_code != T.TEMPLATE_CODE:
        missing = [s.sheet_name for s in T.SHEETS if s.sheet_name not in wb.sheetnames]
        if missing:
            res.issues.append(Issue("error", f"File không đúng mẫu {T.TEMPLATE_CODE}: thiếu sheet {', '.join(missing)}. "
                                             "Hãy tải template mới nhất và điền lại."))
            return res
        res.issues.append(Issue("warning", "Không tìm thấy thông tin phiên bản mẫu – có thể là bản sao cũ"))
    elif res.template_version != T.TEMPLATE_VERSION:
        res.issues.append(Issue("warning", f"Mẫu phiên bản {res.template_version}, bản hiện hành {T.TEMPLATE_VERSION}"))

    # 2) thông tin đơn vị
    if "HuongDan" in wb.sheetnames:
        hd = wb["HuongDan"]
        res.info = {k: _str(hd.cell(r, 2).value) for r, k in INFO_FIELDS.items()}
    if not res.info.get("name"):
        res.issues.append(Issue("error", "Chưa điền 'Tên đơn vị' ở sheet HuongDan", "HuongDan", 5, "B"))
    if res.info.get("email") and not EMAIL_RE.match(res.info["email"]):
        res.issues.append(Issue("warning", "Email liên hệ không đúng định dạng", "HuongDan", 7, "B", res.info["email"]))
    if not res.info.get("preparer"):
        res.issues.append(Issue("warning", "Chưa ghi người lập biểu", "HuongDan", 6, "B"))

    # 3) từng sheet chỉ tiêu
    for spec in T.SHEETS:
        _validate_sheet(wb[spec.sheet_name], spec, res)

    _check_component_sums(res)
    return res


def _validate_sheet(ws, spec: T.IndicatorSheet, res: ValidationResult) -> None:
    headers = [_str(c.value) for c in ws[HEADER_ROW]][: len(spec.columns)]
    expected = [c.header for c in spec.columns]
    if [(h or "").rstrip(" *") for h in headers] != expected:
        res.issues.append(Issue("error", "Tiêu đề cột đã bị thay đổi – không được xoá/chèn/đổi tên cột",
                                spec.sheet_name, HEADER_ROW))
        return

    keys = [c.key for c in spec.columns]
    letters = {k: chr(ord("A") + i) for i, k in enumerate(keys)}
    breakdowns = {b.label: b for b in spec.breakdowns}
    provinces = set(T.PROVINCES)
    seen: dict[tuple, int] = {}

    for r_idx, cells in enumerate(ws.iter_rows(min_row=FIRST_DATA_ROW, values_only=True), start=FIRST_DATA_ROW):
        row = dict(zip(keys, cells))
        if all(_blank(row.get(k)) for k in ("period", "geography", "breakdown", "value")):
            continue  # dòng trống (cột Đơn vị có công thức sẵn)

        def err(col: str, msg: str, val=None):
            res.issues.append(Issue("error", msg, spec.sheet_name, r_idx, letters[col],
                                    None if val is None else str(val)))

        ok = True
        # Kỳ báo cáo
        period_raw = row.get("period")
        period = _num(period_raw)
        if _blank(period_raw):
            err("period", "Thiếu kỳ báo cáo"); ok = False
        elif period is None or period != int(period):
            err("period", "Kỳ báo cáo phải là năm (số nguyên)", period_raw); ok = False
        elif not (2015 <= period <= 2035):
            err("period", "Năm ngoài khoảng 2015–2035", period_raw); ok = False
        # Địa bàn
        geo = _str(row.get("geography"))
        if not geo:
            err("geography", "Thiếu địa bàn"); ok = False
        elif geo not in provinces:
            err("geography", "Địa bàn không có trong danh mục", geo); ok = False
        # Phân tổ
        bd_label = _str(row.get("breakdown"))
        bd = breakdowns.get(bd_label or "")
        if not bd_label:
            err("breakdown", "Thiếu phân tổ"); ok = False
        elif bd is None:
            err("breakdown", "Phân tổ không có trong danh mục của chỉ tiêu", bd_label); ok = False
        # Giá trị
        raw = row.get("value")
        value = _num(raw)
        if _blank(raw):
            err("value", "Thiếu giá trị"); ok = False
        elif value is None:
            err("value", "Giá trị phải là số (không nhập chữ/đơn vị)", raw); ok = False
        elif value < 0:
            err("value", "Giá trị không được âm", raw); ok = False
        elif bd is not None and bd.max_value is not None and value > bd.max_value:
            err("value", f"Giá trị vượt ngưỡng hợp lý ({bd.max_value:g} {bd.unit}) – kiểm tra lại đơn vị", raw); ok = False
        # Link minh chứng
        url = _str(row.get("evidence_url"))
        if url:
            p = urlparse(url)
            if p.scheme not in ("http", "https") or not p.netloc:
                err("evidence_url", "Link minh chứng phải bắt đầu bằng http:// hoặc https://", url); ok = False
        # Trùng dòng
        if ok:
            key = (int(period), geo, bd_label)
            if key in seen:
                err("breakdown", f"Trùng với dòng {seen[key]} (cùng năm, địa bàn, phân tổ)", bd_label); ok = False
            else:
                seen[key] = r_idx
        if ok:
            res.rows.append(ParsedRow(
                sheet=spec.sheet_name, row=r_idx, indicator_code=spec.indicator_code, period=str(int(period)),
                geography=geo, breakdown=bd_label, value=value, unit=bd.unit,
                source_note=_str(row.get("source_note")), evidence_url=url, note=_str(row.get("note")),
            ))


def _check_component_sums(res: ValidationResult) -> None:
    """0102: tổng các nguồn chi phải xấp xỉ tổng chi (khi đủ cả 3 thành phần)."""
    idx = {(r.indicator_code, r.period, r.geography, r.breakdown): r for r in res.rows}
    for (code, period, geo, bd), total in idx.items():
        if code != "0102" or bd != C.INV_TOTAL:
            continue
        parts = [idx.get((code, period, geo, b)) for b in (C.INV_STATE, C.INV_BUSINESS, C.INV_OTHER)]
        if all(parts) and total.value:
            s = sum(p.value for p in parts)
            if abs(s - total.value) / total.value > SUM_WARN:
                msg = f"Tổng 3 nguồn chi ({s:,.0f}) lệch {abs(s - total.value) / total.value:.0%} so với tổng chi ({total.value:,.0f})"
                total.warnings.append(msg)
                res.issues.append(Issue("warning", msg, total.sheet, total.row, "D"))


def contextual_warnings(session: Session, res: ValidationResult, origin: str) -> None:
    """Cảnh báo dựa trên dữ liệu đã có: biến động so với kỳ trước, lệch so với nguồn độc lập."""
    codes = {r.indicator_code for r in res.rows}
    ind_ids = {i.code: i.id for i in session.scalars(select(Indicator).where(Indicator.code.in_(codes)))}
    published = session.scalars(
        select(DataPoint).where(
            DataPoint.indicator_id.in_(ind_ids.values()),
            DataPoint.is_current.is_(True),
            DataPoint.status == DataStatus.PUBLISHED,
        )
    ).all()
    by_key: dict[tuple, list[DataPoint]] = {}
    for p in published:
        by_key.setdefault((p.indicator_id, p.period, p.geography, p.breakdown), []).append(p)
    in_file = {(r.indicator_code, r.period, r.geography, r.breakdown): r for r in res.rows}

    for r in res.rows:
        iid = ind_ids.get(r.indicator_code)
        # kỳ trước: ưu tiên trong chính file, sau đó dữ liệu đã công bố cùng đơn vị
        prev_p = str(int(r.period) - 1)
        prev_row = in_file.get((r.indicator_code, prev_p, r.geography, r.breakdown))
        prev_val = prev_row.value if prev_row else next(
            (p.value for p in by_key.get((iid, prev_p, r.geography, r.breakdown), []) if p.origin == origin), None
        )
        if prev_val and abs(r.value - prev_val) / prev_val > YOY_WARN:
            msg = f"Biến động {(r.value / prev_val - 1):+.0%} so với năm {prev_p} ({prev_val:,.2f})"
            r.warnings.append(msg)
            res.issues.append(Issue("warning", msg, r.sheet, r.row, "D", str(r.value)))
        # nguồn độc lập (vd. World Bank) cùng năm/địa bàn/phân tổ
        for p in by_key.get((iid, r.period, r.geography, r.breakdown), []):
            if p.origin != origin and not p.origin.startswith("calc:") and p.value:
                diff = abs(r.value - p.value) / abs(p.value)
                if diff > CROSS_WARN:
                    msg = f"Lệch {diff:.0%} so với nguồn {p.origin} ({p.value:,.2f})"
                    r.warnings.append(msg)
                    res.issues.append(Issue("warning", msg, r.sheet, r.row, "D", str(r.value)))
