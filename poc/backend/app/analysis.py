"""Phân tích theo báo cáo 2244 (GĐ 4): biểu đồ, scorecard, mức sẵn sàng dữ liệu, số liệu tỉnh.

Số liệu đọc từ các bảng đã nhập từ file seed (chart_series, scorecard_rows, readiness_scores,
provincial_coverage, data_points của tỉnh). Ở đây chỉ có:
- cách vẽ và nhóm I-O-O-I của từng biểu đồ (CHART_SPEC);
- tiêu đề dạng thông điệp, TÍNH TỪ SỐ LIỆU (đổi số → đổi câu). Nếu cấu trúc số liệu khác dự kiến,
  dùng tiêu đề gốc trong file.
"""

from __future__ import annotations

import logging
from collections import OrderedDict
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.home import READINESS_ORDER, READINESS_VI, status_groups
from app.models import (
    ChartSeries,
    DataPoint,
    DataStatus,
    Indicator,
    ProvincialCoverage,
    ReadinessScore,
    Region,
    ScorecardRow,
)
from app.report_vi import SCORECARD_DIMENSION, parse_evidence, vi

log = logging.getLogger(__name__)

PILLARS = OrderedDict([("input", "Đầu vào"), ("output", "Đầu ra"), ("efficiency", "Hiệu quả"), ("impact", "Tác động")])
SOURCE_PREFIX = "Báo cáo 2244"
MIXED_UNIT = "hỗn hợp"


def vnum(v: float | None, d: int = 2) -> str:
    """Định dạng số kiểu Việt Nam: 1.983.625 · 16,51."""
    if v is None:
        return "–"
    s = f"{v:,.{d}f}"
    if d:
        s = s.rstrip("0").rstrip(".")
    return s.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def _pct(a: float, b: float, d: int = 1) -> str:
    return vnum(a / b * 100, d)


def _by(rows, key):
    out: OrderedDict = OrderedDict()
    for r in rows:
        out.setdefault(r[key], []).append(r)
    return out


def _lower1(s: str) -> str:
    """Viết thường chữ đầu, giữ chữ viết tắt (DN, FDI…)."""
    w = s.split(" ", 1)
    return s if w[0].isupper() and len(w[0]) > 1 else s[:1].lower() + s[1:]


def _strip_unit(label: str) -> str:
    return label.split(" (")[0].strip()


# ---------- tiêu đề thông điệp (mỗi hàm nhận danh sách dòng của biểu đồ) ----------
def _m_top_share(subject: str) -> Callable:
    def f(rows):
        top = max(rows, key=lambda r: r["value"] or 0)
        total = sum(r["value"] or 0 for r in rows)
        return f"{top['category']} chiếm {_pct(top['value'], total)}% {subject}"
    return f


def _m_invest(rows):
    a, b = rows[0], rows[1]
    return f"{_strip_unit(a['category'])} bằng {vnum(a['value'])}% GDP; {_strip_unit(b['category'])} {vnum(b['value'])}%, hai thước đo không cộng dồn"


def _m_gerd(rows):
    first, last = rows[0], rows[-1]
    peak = max(rows, key=lambda r: r["value"])
    s = f"GERD/GDP tăng từ {vnum(first['value'])}% ({first['category']}) lên {vnum(last['value'])}% ({last['category']})"
    if peak is not last and peak["value"] > last["value"]:
        s += f", thấp hơn mức {vnum(peak['value'])}% năm {peak['category']}"
    return s


def _m_pub(rows):
    top = max(rows, key=lambda r: r["value"])
    total = sum(r["value"] for r in rows)
    return f"Công bố {_lower1(top['category'])} chiếm {_pct(top['value'], total)}% trong {vnum(total, 0)} bài báo năm {top['series']}"


def _m_asean(rows):
    series = _by(rows, "series")
    above = None
    vn_vals = []
    for s, rs in series.items():
        vn = next(r for r in rs if r["category"].startswith("Việt Nam"))
        vn_vals.append(vnum(vn["value"]))
        higher = {r["category"] for r in rs if r["value"] > vn["value"]}
        above = higher if above is None else above & higher
    names = [r["category"] for r in rows if r["category"] in (above or set())]
    names = list(dict.fromkeys(names))
    msg = f"Việt Nam: {vn_vals[0]} bài báo và {vn_vals[1]} đơn sáng chế trên 1 triệu dân"
    return msg + (f", thấp hơn {' và '.join(names)} ở cả hai thước đo" if names else "")


def _m_tt(rows):
    rs = next(iter(_by(rows, "series").values()))
    total = sum(r["value"] for r in rs)
    top = max(rs, key=lambda r: r["value"])
    return f"{_pct(top['value'], total)}% hợp đồng chuyển giao công nghệ đi theo chiều {_lower1(top['category'])}"


def _m_knowledge(rows):
    a, b, c = rows[0], rows[1], rows[2]
    return f"Từ {vnum(a['value'], 0)} đơn đăng ký đến {vnum(b['value'], 0)} văn bằng; tỷ lệ chuyển giao, ứng dụng {vnum(c['value'])}%"


def _m_trend(label: str, unit: str = "") -> Callable:
    def f(rows):
        rs = next(iter(_by(rows, "series").values()))
        a, b = rs[0], rs[-1]
        verb, prep = ("tăng", "lên") if b["value"] >= a["value"] else ("giảm", "xuống")
        return f"{label} {verb} từ {vnum(a['value'])}%{unit} ({a['category']}) {prep} {vnum(b['value'])}% ({b['category']})"
    return f


def _m_lp(rows):
    parts = [r for r in rows if not r["series"].startswith("Tổng")]
    periods = _by(parts, "category")
    tops = [max(rs, key=lambda r: r["value"])["series"] for rs in periods.values()]
    lead = max(set(tops), key=tops.count)
    return f"{lead} là nguồn đóng góp lớn nhất vào tăng năng suất lao động ở {tops.count(lead)}/{len(tops)} giai đoạn"


def _m_new_product(rows):
    s = list(_by(rows, "series").items())
    (_, subj), (_, bench) = s[0], s[1]
    ratios = [a["value"] / b["value"] * 100 for a, b in zip(subj, bench)]
    lo, hi = min(ratios), max(ratios)
    rng = f"{vnum(lo, 0)}–{vnum(hi, 0)}%" if round(lo) != round(hi) else f"{vnum(lo, 0)}%"
    return f"Tỷ lệ doanh nghiệp Việt Nam giới thiệu sản phẩm mới chỉ bằng {rng} mức trung bình nhóm so sánh"


def _m_efficiency(rows):
    first, last = rows[0], rows[-1]
    if first["value"] < 0 < last["value"]:
        return f"Hiệu quả vận hành chuyển từ đóng góp âm sang dương ({last['category']}: +{vnum(last['value'])} điểm %)"
    return f"Đóng góp của hiệu quả vận hành giai đoạn {last['category']}: {vnum(last['value'])} điểm %"


def _m_region(rows):
    vn = next(r for r in rows if r["category"].startswith("Việt Nam"))
    return f"Kinh tế số bằng {vnum(vn['value'])}% GDP; định nghĩa khác nhau giữa các nước nên chỉ dùng để tham chiếu"


def _m_slope(rows):
    diffs = []
    for s, rs in _by(rows, "series").items():
        diffs.append((rs[-1]["value"] - rs[0]["value"], s, rs[0]["category"], rs[-1]["category"]))
    up, down = max(diffs), min(diffs)
    msg = f"Tỷ trọng {_lower1(up[1])} tăng {vnum(up[0])} điểm %"
    if down[0] < 0:
        msg += f"; tỷ trọng {_lower1(down[1])} giảm {vnum(-down[0])} điểm %"
    return msg + f" ({up[2]}–{up[3]})"


def _m_scale_depth(rows):
    depth = [r for r in rows if r["series"].startswith("Độ sâu")]
    pick = next((r for r in depth if "mua từ DN Việt" in r["category"]), min(depth, key=lambda r: r["value"]))
    return f"Quy mô xuất khẩu công nghệ lớn, nhưng chỉ {vnum(pick['value'])}% {_lower1(_strip_unit(pick['category']))}"


def _m_growth(rows):
    sc = _by(rows, "series")
    def get(rs, key):
        return next(r["value"] for r in rs if key in r["category"])
    gdp = {s: get(rs, "GDP") for s, rs in sc.items()}
    elec = {s: get(rs, "Điện") for s, rs in sc.items()}
    top = max(gdp, key=gdp.get)
    if top == max(elec, key=elec.get):
        return f"Kịch bản {_lower1(top)} tăng GDP nhiều nhất (+{vnum(gdp[top])} tỷ USD) và cũng cần thêm điện nhiều nhất (+{vnum(elec[top])} TWh)"
    return f"Kịch bản {_lower1(top)} tăng GDP nhiều nhất (+{vnum(gdp[top])} tỷ USD)"


def _m_renewable(rows):
    a, b = rows[0], rows[1]
    return f"Điện tái tạo chiếm {_pct(a['value'], b['value'])}% sản lượng hệ thống năm {a['series']} (không gồm thuỷ điện)"


def _m_chain(rows):
    steps = _by(rows, "series")
    missing = [s.split(". ", 1)[-1] for s, rs in steps.items() if all(r["value"] is None for r in rs)]
    msg = f"{len(steps) - len(missing)}/{len(steps)} bước đã có số đo"
    return msg + (f"; chưa đo: {', '.join(_lower1(m) for m in missing)}" if missing else "")


def _m_inclusion(rows):
    r = rows[0]
    return f"{_strip_unit(r['category'])}: {vnum(r['value'])}% ({r['series']})"


def _m_intl(rows):
    best = None
    for r in rows:
        if r["series"] != "Hạng" or "(/" not in r["category"]:
            continue
        total = float(r["category"].split("(/")[1].rstrip(")"))
        ratio = r["value"] / total
        if best is None or ratio < best[0]:
            best = (ratio, r["category"].split(" (")[0], r["value"], total)
    return f"Thứ hạng cao nhất: {best[1]}, hạng {vnum(best[2], 0)}/{vnum(best[3], 0)}"


# chart_id → (nhóm, cách vẽ, chỉ tiêu liên quan, hàm tiêu đề)
CHART_SPEC: dict[str, tuple[str, str, list[str], Callable | None]] = {
    "C_WORKFORCE_MIX": ("input", "hbar", ["0101"], _m_top_share("nhân lực STID")),
    "C_DIGITAL_ENT": ("input", "hbar", ["0101"], _m_top_share("lao động trong doanh nghiệp công nghệ số")),
    "C_INVEST_HEADLINE": ("input", "tiles", ["0102"], _m_invest),
    "C_GERD": ("input", "column", ["0102"], _m_gerd),
    "C_PUB_SPLIT": ("output", "segbar", ["0201"], _m_pub),
    "C_ASEAN_BENCH": ("output", "dot_facet", ["0201", "0202"], _m_asean),
    "C_TT_DIRECTION": ("output", "hbar_facet", ["0209", "0210"], _m_tt),
    "C_KNOWLEDGE_VALUE": ("output", "chain", ["0202", "0203", "0207", "0208"], _m_knowledge),
    "C_STID_GDP": ("efficiency", "line", ["0301", "0402"], _m_trend("Tỷ trọng STID trong GDP")),
    "C_LP_DECOMP": ("efficiency", "stack", ["0302", "0303"], _m_lp),
    "C_NEW_PRODUCT": ("efficiency", "dot", ["0304"], _m_new_product),
    "C_EFFICIENCY": ("efficiency", "column", ["0305"], _m_efficiency),
    "C_DIGITAL_VA": ("impact", "line", ["0402"], _m_trend("Giá trị tăng thêm kinh tế số", " GDP")),
    "C_DIGITAL_VA_REGION": ("impact", "dot", ["0401", "0402"], _m_region),
    "C_SECTOR_SLOPE": ("impact", "slope", ["0403"], _m_slope),
    "C_SCALE_DEPTH": ("impact", "contrast", ["0405", "0406"], _m_scale_depth),
    "C_GROWTH_ENERGY": ("impact", "bubble", [], _m_growth),
    "C_RENEWABLE": ("impact", "part", ["0416"], _m_renewable),
    "C_DIGITAL_GOV_CHAIN": ("impact", "chain", ["0414", "0418", "0425", "0424", "0415", "0423", "0422"], _m_chain),
    "C_INCLUSION": ("impact", "tiles", ["0408"], _m_inclusion),
    "C_INTL_INDEX": ("impact", "rank", ["0426", "0427", "0428", "0429"], _m_intl),
}


def _source(ref: str | None) -> str:
    if not ref:
        return SOURCE_PREFIX
    return f"{SOURCE_PREFIX}, {ref.replace('Fig', 'Hình')}"


def build_charts(session: Session) -> list[dict]:
    rows = session.scalars(select(ChartSeries).order_by(ChartSeries.order_no, ChartSeries.id)).all()
    groups: OrderedDict[str, list[ChartSeries]] = OrderedDict()
    for r in rows:
        groups.setdefault(r.chart_id, []).append(r)
    names = {i.code: i.name for i in session.scalars(select(Indicator).where(Indicator.indicator_set == "2244"))}
    out = []
    for cid, rs in groups.items():
        pillar, kind, codes, msg_fn = CHART_SPEC.get(cid, ("other", "table", [], None))
        data = [{"series": r.series, "category": r.category, "value": r.value, "unit": r.unit, "note": r.note} for r in rs]
        units = {r.unit for r in rs if r.unit}
        notes = list(dict.fromkeys(r.note for r in rs if r.note))
        available = any(r.value is not None for r in rs)
        message = None
        if msg_fn and available:
            try:
                message = msg_fn(data)
            except Exception:  # cấu trúc khác dự kiến: dùng tiêu đề gốc
                log.warning("Không dựng được tiêu đề thông điệp cho %s", cid, exc_info=True)
        title = rs[0].title_vi or cid
        out.append({
            "chart_id": cid, "pillar": pillar, "pillar_label": PILLARS.get(pillar, "Khác"), "kind": kind if available else "na",
            "title": title, "message": message or title, "figure_ref": rs[0].figure_ref, "source": _source(rs[0].figure_ref),
            "unit": units.pop() if len(units) == 1 else (MIXED_UNIT if units else None), "notes": notes,
            "indicators": [{"code": c, "name": names.get(c)} for c in codes if c in names],
            "available": available, "rows": data,
        })
    order = {p: i for i, p in enumerate(list(PILLARS) + ["other"])}
    spec_order = {c: i for i, c in enumerate(CHART_SPEC)}
    out.sort(key=lambda c: (order[c["pillar"]], spec_order.get(c["chart_id"], 999)))
    return out


# ---------- scorecard ----------
def build_scorecard(session: Session) -> dict:
    rows = []
    for r in session.scalars(select(ScorecardRow).order_by(ScorecardRow.order_no)):
        ev = parse_evidence(r.evidence_status)
        rows.append({
            "dimension": r.dimension, "dimension_vi": SCORECARD_DIMENSION.get(r.dimension, r.dimension),
            "diagnosis": vi(r.diagnosis), "evidence_levels": ev["levels"], "evidence_detail": ev["detail"],
            "policy_implication": vi(r.policy_implication),
            "original": {"diagnosis": r.diagnosis, "evidence_status": r.evidence_status, "policy_implication": r.policy_implication},
        })
    from app.report_vi import EVIDENCE_LEVELS
    levels = [{"key": k, "rank": v[0], "label": v[1]} for k, v in sorted(EVIDENCE_LEVELS.items(), key=lambda x: -x[1][0])]
    return {"rows": rows, "levels": levels, "source": "Báo cáo 2244, Hình 3.11 và Bảng 3.7"}


# ---------- mức sẵn sàng dữ liệu ----------
READINESS_HELP = {
    "Completeness": "Số liệu bao quát đủ các thành phần theo định nghĩa chỉ tiêu.",
    "Consistency": "Số liệu thống nhất giữa các nguồn và giữa các kỳ.",
    "Coverage": "Phạm vi đơn vị, địa bàn đã báo cáo so với tổng thể.",
    "Denominator": "Có mẫu số phù hợp để tính tỷ lệ.",
    "Time-series depth": "Số kỳ có số liệu so sánh được theo thời gian.",
    "Disaggregation": "Có số liệu theo các phân tổ cần thiết (ngành, địa bàn, giới tính…).",
    "Independent validation": "Có nguồn độc lập để đối chiếu, kiểm chứng.",
    "International comparability": "Phương pháp tương thích với chuẩn quốc tế, so sánh được giữa các nước.",
}
READINESS_LEVELS = [{"score": 0, "label": "Không đủ"}, {"score": 1, "label": "Một phần"}, {"score": 2, "label": "Đạt"}]


def build_readiness(session: Session) -> dict:
    inds = session.scalars(select(Indicator).where(Indicator.indicator_set == "2244").order_by(Indicator.code)).all()
    cells: dict[str, dict[str, ReadinessScore]] = {}
    for r in session.scalars(select(ReadinessScore)):
        cells.setdefault(r.indicator_code, {})[r.dimension] = r
    dims = [d for d in READINESS_ORDER if any(d in c for c in cells.values())]
    dims += sorted({d for c in cells.values() for d in c} - set(dims))
    rows = []
    for i in inds:
        c = cells.get(i.code, {})
        scores = [c[d].score for d in dims if d in c and c[d].score is not None]
        rows.append({
            "code": i.code, "name": i.name, "name_en": i.name_en, "pillar": i.pillar.value if i.pillar else None,
            "pillar_label": PILLARS.get(i.pillar.value) if i.pillar else None, "data_status": i.data_status,
            "limitation": i.limitation, "total": sum(scores) if scores else None, "max": 2 * len(dims),
            "cells": [{"dimension": d, "score": c[d].score, "level_vi": c[d].level_vi} if d in c else
                      {"dimension": d, "score": None, "level_vi": None} for d in dims],
        })
    dim_info = [{"key": d, "label": READINESS_VI.get(d, d), "help": READINESS_HELP.get(d),
                 "adequate": sum(1 for r in rows for c in r["cells"] if c["dimension"] == d and c["score"] == 2)} for d in dims]
    return {"dimensions": dim_info, "levels": READINESS_LEVELS, "rows": rows, "status_summary": status_groups(session),
            "pillars": [{"key": k, "label": v} for k, v in PILLARS.items()],
            "source": "Báo cáo 2244, Phụ lục B (ma trận mức sẵn sàng dữ liệu)"}


# ---------- địa phương ----------
# Bản đồ lưới ô (D3): mỗi tỉnh, thành phố (sau sắp xếp 2025) một ô, đặt theo vị trí tương đối (cột, hàng).
# Không dùng ranh giới hành chính nên không phụ thuộc dữ liệu bản đồ.
TILE_GRID = {
    "LCU": (1, 0), "LCI": (2, 0), "TQG": (3, 0), "CBG": (4, 0),
    "DBN": (0, 1), "SLA": (1, 1), "PTO": (2, 1), "TNN": (3, 1), "LSN": (4, 1),
    "HNI": (2, 2), "BNH": (3, 2), "QNH": (4, 2),
    "NBH": (2, 3), "HYN": (3, 3), "HPG": (4, 3),
    "THA": (1, 4), "NAN": (1, 5), "HTH": (2, 6), "QTI": (2, 7), "HUE": (3, 8), "DNG": (3, 9),
    "QNI": (3, 10), "GLI": (3, 11), "DLK": (3, 12), "LDG": (2, 13), "KHA": (3, 13),
    "TNH": (1, 14), "DNI": (2, 14), "AGG": (0, 15), "DTP": (1, 15), "HCM": (2, 15),
    "CTO": (1, 16), "VLG": (2, 16), "CMU": (0, 17),
}
PROVINCE_NOTE = "Số liệu do tỉnh tự báo cáo, chưa chuẩn hoá; không dùng để xếp hạng."


def build_provinces(session: Session, indicator: str | None = None) -> dict:
    regions = [r for r in session.scalars(select(Region)) if r.code != "VN"]
    codes = {r.code for r in regions}
    pts = session.scalars(select(DataPoint).where(
        DataPoint.is_current.is_(True), DataPoint.status == DataStatus.PUBLISHED,
        DataPoint.region_code.in_(codes))).all()
    by_ind: dict[int, list[DataPoint]] = {}
    for p in pts:
        by_ind.setdefault(p.indicator_id, []).append(p)
    inds = {i.id: i for i in session.scalars(select(Indicator).where(Indicator.id.in_(by_ind)))} if by_ind else {}
    seen = set(session.scalars(select(Indicator.code)))  # đã lọc theo vai trò
    cov = {c.indicator_code: c for c in session.scalars(select(ProvincialCoverage)) if c.indicator_code in seen}
    indicators = sorted(({"code": i.code, "name": i.name, "unit": i.unit,
                          "reporting": len({p.region_code for p in by_ind[iid] if p.value is not None}),
                          "total": len(regions)} for iid, i in inds.items()), key=lambda x: x["code"])
    sel = next((i for i in inds.values() if i.code == indicator), None)
    values = {}
    period = None
    if sel:
        latest: dict[str, DataPoint] = {}
        for p in by_ind[sel.id]:
            if p.region_code not in latest or p.period > latest[p.region_code].period:
                latest[p.region_code] = p
        values = {rc: {"value": p.value, "value_text": p.value_text, "unit": p.unit or sel.unit,
                       "data_status": p.data_status, "period": p.period} for rc, p in latest.items()}
        period = max((p.period for p in latest.values()), default=None)
    coverage = [{
        "indicator_code": c.indicator_code, "indicator_name": next((i["name"] for i in indicators if i["code"] == c.indicator_code), c.indicator_en),
        "provinces_reporting": c.provinces_reporting, "provinces_total": c.provinces_total, "reporting_text": c.reporting_text,
        "usable_coverage": vi(c.usable_coverage), "main_issue": vi(c.main_issue),
    } for c in sorted(cov.values(), key=lambda c: c.indicator_code)]
    return {
        "note": PROVINCE_NOTE,
        "regions": [{"code": r.code, "name": r.name_vi, "name_en": r.name_en, "reported_2025": r.reported_2025,
                     "indicators_with_value": len({p.indicator_id for p in pts if p.region_code == r.code and p.value is not None}),
                     "col": TILE_GRID.get(r.code, (None, None))[0], "row": TILE_GRID.get(r.code, (None, None))[1]}
                    for r in regions],
        "reported": sum(1 for r in regions if r.reported_2025), "total": len(regions),
        "indicators": indicators,
        "indicator": {"code": sel.code, "name": sel.name, "unit": sel.unit, "period": period,
                      "coverage": next((c for c in coverage if c["indicator_code"] == sel.code), None)} if sel else None,
        "values": values, "coverage": coverage,
    }
