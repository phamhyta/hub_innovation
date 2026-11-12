"""Chuỗi theo kỳ của MỘT chỉ tiêu (giá trị tiêu biểu, toàn quốc) – dùng cho Tab 2244, Tab 137, trang chi tiết, so sánh.

Chọn số liệu: điểm đã công bố, hiện hành, cùng phân tổ tiêu biểu; mỗi kỳ lấy nguồn ưu tiên cao nhất
(số của Cục → đơn vị → thu thập → tài liệu → tự tính). Nếu không có số ở độ phân giải yêu cầu thì gộp từ
độ phân giải mịn hơn theo quy tắc gộp của chỉ tiêu.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import timeseries as T
from app.analytics import best_by_period, effective_data_status, headline_breakdown, origin_label
from app.datapoints import NATIONAL
from app.models import DataPoint, DataStatus, Indicator

RES_LABEL = {"M": "tháng", "Q": "quý", "Y": "năm"}
POP_LABEL = {"M": "MoM", "Q": "QoQ", "Y": "YoY"}


def _published(session: Session, ind: Indicator, geography: str) -> list[DataPoint]:
    return session.scalars(select(DataPoint).where(
        DataPoint.indicator_id == ind.id, DataPoint.is_current.is_(True), DataPoint.status == DataStatus.PUBLISHED,
        DataPoint.geography == geography, DataPoint.value.is_not(None))).all()


def native_series(points: list[DataPoint], breakdown) -> dict[str, dict[str, DataPoint]]:
    """{loại kỳ: {kỳ: điểm tốt nhất}} cho phân tổ đã chọn."""
    out: dict[str, dict[str, DataPoint]] = {}
    for t in ("M", "Q", "Y"):
        pts = [p for p in points if p.breakdown == breakdown and (p.period_type or "Y") == t]
        if pts:
            out[t] = best_by_period(pts)
    return out


def available_resolutions(native: dict, rule: str | None) -> list[str]:
    have = set(native)
    if rule in T.RULES:
        for t in list(native):
            have |= {to for to in ("Q", "Y") if T.ORDER[to] > T.ORDER[t]}
    return [t for t in ("M", "Q", "Y") if t in have]


def default_resolution(ind: Indicator, avail: list[str]) -> str | None:
    if not avail:
        return None
    if ind.frequency in avail:
        return ind.frequency
    return avail[0]


def indicator_timeseries(session: Session, ind: Indicator, res: str | None = None, n: int | None = None,
                         geography: str = NATIONAL) -> dict:
    points = _published(session, ind, geography)
    bd = headline_breakdown(ind.code, points) if points else None
    if bd is None and points and not any(p.breakdown is None for p in points):
        bd = points[0].breakdown
    native = native_series(points, bd)
    rule = ind.aggregation_rule
    avail = available_resolutions(native, rule)
    res = res if res in avail else default_resolution(ind, avail)
    base = {"code": ind.code, "name": ind.name, "name_en": ind.name_en, "indicator_set": ind.indicator_set,
            "unit": ind.unit, "breakdown": bd, "rule": rule, "available": avail, "res": res,
            "res_label": RES_LABEL.get(res), "pop_label": POP_LABEL.get(res), "data_status": ind.data_status}
    if res is None:
        return {**base, "derived_from": None, "points": [], "changes": T.changes({}), "simulated": False}

    meta: dict[str, dict] = {}
    if res in native:
        values = {p: dp.value for p, dp in native[res].items()}
        unit = next(iter(native[res].values())).unit
        for p, dp in native[res].items():
            meta[p] = {"simulated": bool(dp.is_simulated), "data_status": effective_data_status(dp),
                       "origin_label": origin_label(dp.origin)}
        derived_from = None
    else:  # gộp từ độ phân giải mịn nhất có số liệu
        derived_from = next(t for t in ("M", "Q") if t in native and T.ORDER[t] < T.ORDER[res])
        src = native[derived_from]
        values = T.aggregate({p: dp.value for p, dp in src.items()}, rule, res)
        unit = next(iter(src.values())).unit
        for p in values:
            kids = [dp for k, dp in src.items() if T.parent_of(k, res) == p]
            sim = any(dp.is_simulated for dp in kids)
            meta[p] = {"simulated": sim, "data_status": "simulated" if sim else "estimate",
                       "origin_label": f"Gộp từ số liệu {RES_LABEL[derived_from]} ({rule})"}

    win = T.window(values, n)
    rows = []
    for p, v in win:
        ly = T.same_period_last_year(p)
        rows.append({"period": p, "value": v, "same_period_last_year": ly, "value_last_year": values.get(ly),
                     "yoy": T.pct(v, values.get(ly)), **meta.get(p, {"simulated": False, "data_status": None,
                                                                       "origin_label": None})})
    ch = T.changes(values, rule)
    return {**base, "unit": unit or ind.unit, "derived_from": derived_from, "points": rows, "changes": ch,
            "simulated": any(r["simulated"] for r in rows if r["value"] is not None)}
